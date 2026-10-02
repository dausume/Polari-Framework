"""
@module cmod.cmod_api

GET /api/cmod                           the summary: projects with their counts, the parser, where the cost engines WOULD run
GET /api/cmod/projects                  every CProject row
GET /api/cmod/atoms?project=&kind=      the CFunctionAtom rows (filter by project / kind function|isr|entry)
GET /api/cmod/atoms/{atom}              one atom + its ports (`uno:hal.hal_millis`, or `hal_millis` when it is unique)
GET /api/cmod/ports?atom=               the CPort rows
GET /api/cmod/engines                   avr-gcc / avr-nm / make placement through the board engines seam (nothing is run)
GET /api/cmod/projects/{project}/drift  parse the project NOW (no engine, nothing written) and compare with its committed
                                        manifest: atoms added / removed / changed — a stale manifest is reported, never fixed here
Writing a manifest is `pol cmod conform <project>` (it measures with the engines and writes a file in the project).
"""
import inspect

from objectTreeDecorators import treeObject, treeObjectInit


class CModAPI(treeObject):
    @treeObjectInit
    def __init__(self, polServer=None, manager=None):
        self.polServer = polServer
        self.manager = manager
        if polServer is not None and getattr(polServer, 'falconServer', None) is not None:
            add = polServer.falconServer.add_route
            add('/api/cmod', self, suffix='summary')
            add('/api/cmod/projects', self, suffix='projects')
            add('/api/cmod/atoms', self, suffix='atoms')
            add('/api/cmod/atoms/{atom}', self, suffix='atom_one')
            add('/api/cmod/ports', self, suffix='ports')
            add('/api/cmod/engines', self, suffix='engines')
            add('/api/cmod/projects/{project}/drift', self, suffix='drift')

    def _rows(self, cls):
        return list(((self.manager.objectTables or {}).get(cls, {}) or {}).values()) if self.manager is not None else []

    @staticmethod
    def _d(row):
        keys = [k for k in inspect.signature(type(row).__init__).parameters if k not in ('self', 'manager')]
        return {k: getattr(row, k, None) for k in keys}

    def on_get_summary(self, request, response):
        import pycparser
        projects = sorted(self._rows('CProject'), key=lambda r: r.name)
        response.media = {'ok': True, 'parser': {'engine': 'pycparser', 'version': pycparser.__version__, 'runs': 'in this process'},
                          'projects': [{k: getattr(p, k, '') for k in ('name', 'kind', 'root', 'atoms', 'annotated', 'isr_atoms', 'pure_atoms',
                                                                         'not_isr_safe', 'configurations', 'conformed_at')} for p in projects],
                          'atoms': len(self._rows('CFunctionAtom')), 'ports': len(self._rows('CPort')), 'graphs': len(self._rows('CGraph'))}

    def on_get_projects(self, request, response):
        response.media = {'ok': True, 'projects': [self._d(r) for r in sorted(self._rows('CProject'), key=lambda r: r.name)]}

    def on_get_atoms(self, request, response):
        proj, kind = request.get_param('project') or '', request.get_param('kind') or ''
        rows = [r for r in self._rows('CFunctionAtom') if (not proj or r.project == proj) and (not kind or r.kind == kind)]
        response.media = {'ok': True, 'atoms': [self._d(r) for r in sorted(rows, key=lambda r: r.name)]}

    def _find(self, name):
        rows = self._rows('CFunctionAtom')
        exact = [r for r in rows if r.name == name]
        if exact:
            return exact, []
        hits = [r for r in rows if r.function == name or r.name.split(':', 1)[-1] == name]
        return (hits, []) if len(hits) == 1 else ([], sorted(r.name for r in hits))

    def on_get_atom_one(self, request, response, atom):
        import falcon
        hits, many = self._find(atom)
        if not hits:
            response.status = falcon.HTTP_404
            response.media = {'ok': False, 'error': ('%r names several atoms: %s — use the full name' % (atom, ', '.join(many))) if many
                              else 'no atom named %r (GET /api/cmod/atoms lists them)' % atom}
            return
        a = hits[0]
        ports = sorted((p for p in self._rows('CPort') if p.atom == a.name), key=lambda p: p.position)
        response.media = {'ok': True, 'atom': self._d(a), 'ports': [self._d(p) for p in ports]}

    def on_get_ports(self, request, response):
        atom = request.get_param('atom') or ''
        rows = [r for r in self._rows('CPort') if not atom or r.atom == atom]
        response.media = {'ok': True, 'ports': [self._d(r) for r in sorted(rows, key=lambda r: (r.atom, r.position))]}

    def on_get_engines(self, request, response):
        from cmod.custom import cmod_engines
        response.media = {'ok': True, 'engines': cmod_engines.placement(),
                          'note': 'parsing needs no engine (pycparser in this process); only the cost and the make-alone proof do'}

    def on_get_drift(self, request, response, project):
        import falcon
        from cmod.custom import manifest as MF
        from cmod.custom import projects as P
        if project not in P.TEMPLATES:
            response.status = falcon.HTTP_404
            response.media = {'ok': False, 'error': 'no template project %r here (known: %s); a plain directory is checked with '
                                                    '`pol cmod conform <dir>`' % (project, ', '.join(sorted(P.TEMPLATES)))}
            return
        try:
            r = MF.conform(project, measure=False, write=False)
        except Exception as e:   # a malformed annotation or an unparsable file: the refusal, in plain words
            response.status = falcon.HTTP_422
            response.media = {'ok': False, 'error': str(e)}
            return
        response.media = {'ok': True, 'project': project, 'stale': r['changed'], 'added': r['added'], 'removed': r['removed'],
                          'edited': r['edited'], 'atoms': r['manifest']['counts']['atoms'],
                          'how': 'parsed now with pycparser, compared with the committed manifest (cost blocks kept: nothing was measured)'}
