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
cmod-1 (graphs over atoms → generated glue):
GET /api/cmod/graphs                    every CGraph row
GET /api/cmod/graphs/{graph}            the graph + its nodes, edges and glue builds
GET /api/cmod/graphs/{graph}/render     render NOW into memory (nothing written): the checked model's verdict, what the glue
                                        owns, the cost before building, each file's sha + its text — or the refusal (422)
GET /api/cmod/graphs/{graph}/diff       the committed project vs a fresh render (the graph changed / hand edits / stale files)
Writing the project, building and the twin proof are `pol cmod render | build | prove <graph>` (they write files / run engines).
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
            add('/api/cmod/graphs', self, suffix='graphs')
            add('/api/cmod/graphs/{graph}', self, suffix='graph_one')
            add('/api/cmod/graphs/{graph}/render', self, suffix='graph_render')
            add('/api/cmod/graphs/{graph}/diff', self, suffix='graph_diff')

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

    # ------------------------------------------------------------------ cmod-1
    def on_get_graphs(self, request, response):
        response.media = {'ok': True, 'graphs': [self._d(r) for r in sorted(self._rows('CGraph'), key=lambda r: r.name)]}

    def _graph(self, graph, response):
        import falcon
        g = [r for r in self._rows('CGraph') if r.name == graph]
        if not g:
            response.status = falcon.HTTP_404
            response.media = {'ok': False, 'error': 'no graph %r (GET /api/cmod/graphs lists them)' % graph}
        return g[0] if g else None

    def on_get_graph_one(self, request, response, graph):
        g = self._graph(graph, response)
        if g is None:
            return
        pick = lambda cls, key: [self._d(r) for r in sorted(self._rows(cls), key=key) if r.graph == graph]  # noqa: E731
        response.media = {'ok': True, 'graph': self._d(g), 'nodes': pick('CGraphNode', lambda r: (r.order, r.instance)),
                          'edges': pick('CGraphEdge', lambda r: (r.order, r.name)), 'glue_builds': pick('CGlueBuild', lambda r: r.name)}

    def on_get_graph_render(self, request, response, graph):
        import falcon
        from cmod.custom import glue as GL
        from cmod.custom.graph import GraphRefused
        if self._graph(graph, response) is None:
            return
        try:
            r = GL.render(graph, manager=self.manager, write=False)
        except (GL.GlueRefused, GraphRefused) as e:
            response.status = falcon.HTTP_422
            response.media = {'ok': False, 'refused': str(e)}
            return
        response.media = {'ok': True, 'graph': graph, 'graph_sha256': r['sha'], 'files_sha256': r['files_sha256'], 'unchanged': r['unchanged'],
                          'glue_contains': r['glue_contains'], 'advice': r['advice'],
                          'cost_before_building': {'total_bytes': r['cost']['total_bytes'], 'why': r['cost']['why'],
                                                   'parts': [{'atom': a, 'bytes': b, 'as': w} for a, b, w in r['cost']['parts']]},
                          'files': [{'file': f, 'sha256': r['files'][f], 'bytes': len(r['texts'][f])} for f in sorted(r['files'])],
                          'how': 'rendered in this process from the graph rows + the atoms\' committed manifest; nothing written'}

    def on_get_graph_diff(self, request, response, graph):
        import falcon
        from cmod.custom import glue as GL
        from cmod.custom.graph import GraphRefused
        if self._graph(graph, response) is None:
            return
        try:
            d = GL.diff(graph, manager=self.manager)
        except (GL.GlueRefused, GraphRefused) as e:
            response.status = falcon.HTTP_422
            response.media = {'ok': False, 'refused': str(e)}
            return
        response.media = dict({k: v for k, v in d.items() if k != 'dir'}, ok=True)
