"""
@module moduleService.module_registrar

The module registrar (his ask 2026-09-09): ONE record per module on
this instance that every loading path updates as the module moves

    declared → loading → (pieces confirmed) → online | degraded
                                             | failed | blocked | invalid
    disabled / put-away

and one unified health check reads. Two ideas make it honest:

* EXPECTED pieces come from the module's declaration — its
  polari-app.json (classes, endpoints, routes, seeds, pages, selftests),
  or the core tables for a module without a manifest — never from what
  a loader says it did.
* CONFIRMATION is checked against the LIVE server: the class is typed
  and tabled, its CRUDE route is in the router (walked, not trusted —
  falcon's App is read-only, so nothing wraps add_route), the endpoint
  constructor ran and the routes it declares are in the router, seed
  rows and pages are present by name. `verify()` recomputes that any
  time; a module whose expected pieces are not all live is DEGRADED,
  not online. `invalid` = the declaration itself does not hold
  (manifest unreadable, a declared class no file defines, an endpoint
  reference that does not resolve).

The registrar is in-memory truth for this process, mirrored to
ModuleRegistration rows (one per module per instance) once the DB is up,
so the state survives a restart and shows on /display/module-health
without raw JSON. Selftests are not run by the registrar; `pol modules
selftest` (or anyone) POSTs their result to
/api/modules/health/<module>/confirm and it lands on the same record.
"""
import importlib
import json
import os
import re
import threading
import time

from objectTreeDecorators import treeObject, treeObjectInit

STATES = ('declared', 'disabled', 'loading', 'online', 'degraded',
          'failed', 'blocked', 'invalid', 'put-away')
# structural pieces (all must be live for `online`); selftest is
# informational — reported, never a reason to call a module degraded.
STRUCTURAL = ('classes', 'crude', 'endpoints', 'routes', 'seeds', 'pages')
PIECES = STRUCTURAL + ('selftest',)
# treeObject subclasses a module's endpoint constructor INSTANTIATES rather
# than tables: API resources and server-rendered page classes. Named by
# suffix (the standard's postfix rule) — never expected as tables.
ENDPOINT_SUFFIXES = ('API', 'Page', 'Endpoint', 'Server')


def is_endpoint_class(name):
    return any(name.endswith(s) for s in ENDPOINT_SUFFIXES)


def norm_route(path):
    """falcon stores templates without a trailing slash; compare alike."""
    p = (path or '').rstrip('/')
    return p or '/'
# the first argument of add_route as one or more ADJACENT string literals
# (Python joins '/a/' 'b' at compile time — the source may split a long route)
_ROUTE_RE = re.compile(r"""add_route\(\s*((?:['"][^'"]*['"]\s*)+)""")
_LIT_RE = re.compile(r"""['"]([^'"]*)['"]""")


class ModuleRegistration(treeObject):
    """One module's registrar record on one instance (durable mirror)."""

    @treeObjectInit
    def __init__(self, name: str = '', module_name: str = '',
                 instance_name: str = '', state: str = 'declared',
                 # 'manifest' | 'core-tables' | 'core' | 'manifest+tables'
                 source: str = '', app_kind: str = '', version: str = '',
                 phase: str = '', phase_started_at: float = 0.0,
                 verified_at: float = 0.0, boot_id: str = '',
                 # per piece: expected count / confirmed count / missing names
                 expected_json: str = '{}', confirmed_json: str = '{}',
                 missing_json: str = '{}', error: str = '',
                 selftest_status: str = 'not-run',
                 selftest_detail: str = '', notes: str = '',
                 manager=None):
        self.name = name
        self.module_name = module_name
        self.instance_name = instance_name
        self.state = state
        self.source = source
        self.app_kind = app_kind
        self.version = version
        self.phase = phase
        self.phase_started_at = phase_started_at
        self.verified_at = verified_at
        self.boot_id = boot_id
        self.expected_json = expected_json
        self.confirmed_json = confirmed_json
        self.missing_json = missing_json
        self.error = error
        self.selftest_status = selftest_status
        self.selftest_detail = selftest_detail
        self.notes = notes


# ------------------------------------------------------------ expected

def _resolve(ref):
    mod, _, name = ref.partition(':')
    return getattr(importlib.import_module(mod), name)


def _routes_in_sources(module_dir, stems):
    """Route literals the module's api/endpoints files pass to
    add_route — the routes it DECLARES (f-strings are not literals and
    are simply not expected)."""
    found = []
    for stem in stems:
        path = os.path.join(module_dir, stem + '.py')
        if not os.path.isfile(path):
            continue
        with open(path, encoding='utf-8') as fh:
            for group in _ROUTE_RE.findall(fh.read()):
                uri = ''.join(_LIT_RE.findall(group))
                if uri.startswith('/') and uri not in found:
                    found.append(uri)
    return found


def expected_from_manifest(module, manifest, module_dir):
    """{piece: {...}} — what the manifest says must be live."""
    files = manifest.get('files') or {}
    classes = [c for c in (manifest.get('classes') or [])
               if not is_endpoint_class(c)]
    expected = {
        'classes': {'names': classes},
        'crude': {'names': classes},
    }
    endpoints = manifest.get('endpoints')
    if endpoints:
        expected['endpoints'] = {'ref': endpoints}
    routes = _routes_in_sources(
        module_dir, list(files.get('api') or []) + list(files.get('endpoints') or []))
    if routes:
        expected['routes'] = {'paths': routes}
    if manifest.get('seedPairs'):
        expected['seeds'] = {'ref': manifest['seedPairs']}
    if manifest.get('pages'):
        expected['pages'] = {'refs': list(manifest['pages'])}
    if manifest.get('selftests'):
        expected['selftest'] = {'files': list(manifest['selftests'])}
    return expected


def expected_from_tables(module, polServer):
    """A module without a manifest: what the core tables thread for it."""
    from polariApiServer.lazy_boot import top_module
    from polariApiServer.module_endpoints import MODULE_ENDPOINT_CONSTRUCTORS
    classes = sorted(c.__name__ for c in getattr(polServer, 'allDefClassList', [])
                     if top_module(c) == module)
    expected = {'classes': {'names': classes}, 'crude': {'names': classes}}
    if module in MODULE_ENDPOINT_CONSTRUCTORS:
        expected['endpoints'] = {
            'ref': 'polariApiServer.module_endpoints:construct_%s_endpoints' % module}
    return expected


# ------------------------------------------------------------ registrar

class ModuleRegistrar:
    def __init__(self, polServer):
        self.polServer = polServer
        self._lock = threading.Lock()
        self.rows = {}            # module → record dict
        self._current = None      # module being loaded right now

    # -- records ----------------------------------------------------
    def _blank(self, module):
        return {'module': module, 'state': 'declared', 'source': '',
                'appKind': '', 'version': '', 'phase': '',
                'phaseStartedAt': None, 'verifiedAt': None,
                'expected': {}, 'confirmed': {}, 'missing': {},
                'error': '', 'selftest': {'status': 'not-run', 'detail': ''},
                'history': []}

    def _row(self, module):
        return self.rows.setdefault(module, self._blank(module))

    def _set(self, module, state, phase='', error=None, **extra):
        with self._lock:
            row = self._row(module)
            row['state'] = state
            row['phase'] = phase or row.get('phase', '')
            if phase:
                row['phaseStartedAt'] = time.time()
            if error is not None:
                row['error'] = error
            row.update(extra)
            row['history'].append((round(time.time(), 3), state, phase))
            row['history'] = row['history'][-20:]
        self._mirror(module)
        return self.get(module)

    def get(self, module):
        with self._lock:
            row = self.rows.get(module)
            return json.loads(json.dumps(row)) if row else None

    # -- declaration ------------------------------------------------
    def declare(self, module, manifest=None, source=None):
        """Record what the module MUST bring online. Reads the manifest
        (polari-app.json) when present, else the core tables. A manifest
        that does not hold marks the module invalid."""
        from moduleService.module_loading import module_code_dir
        from polariApiServer.module_gating import CORE_PACKAGES
        module_dir = module_code_dir(module)
        expected, err = {}, ''
        if manifest is None and module_dir:
            path = os.path.join(module_dir, 'polari-app.json')
            if os.path.isfile(path):
                try:
                    with open(path, encoding='utf-8') as fh:
                        manifest = json.load(fh)
                except Exception as exc:
                    err = 'polari-app.json unreadable: %s' % exc
        if manifest is not None and not err:
            source = source or 'manifest'
            try:
                expected = expected_from_manifest(module, manifest, module_dir or '')
            except Exception as exc:
                err = 'manifest does not hold: %s: %s' % (type(exc).__name__, exc)
        elif not err:
            source = source or ('core' if module in CORE_PACKAGES else 'core-tables')
            expected = expected_from_tables(module, self.polServer)
        with self._lock:
            row = self._row(module)
            row['expected'] = expected
            row['source'] = source or row['source']
            if manifest:
                row['appKind'] = (manifest.get('app') or {}).get('kind', '')
                row['version'] = manifest.get('version', '')
            keep = row['state'] in ('online', 'degraded', 'loading', 'put-away', 'disabled')
        if err:
            return self._set(module, 'invalid', error=err)
        if not keep:
            return self._set(module, 'declared')
        self._mirror(module)
        return self.get(module)

    def declare_all(self, modules, disabled=(), include_core=True):
        """Declare every module that should be on this instance; `disabled`
        are known modules gated off here (declared as such, so the health
        view shows them); core packages are declared too — one view."""
        if include_core:
            from polariApiServer.module_gating import CORE_PACKAGES
            modules = set(modules) | (set(CORE_PACKAGES) - {'__main__'})
        for m in sorted(set(disabled)):
            try:
                self.declare(m)
            except Exception:
                pass
            self.disabled(m, 'not enabled on this instance')
        for m in sorted(set(modules)):
            try:
                self.declare(m)
            except Exception as exc:
                self._set(m, 'invalid', error='declaration failed: %s: %s'
                          % (type(exc).__name__, exc))

    # -- transitions the loaders call ---------------------------------
    def begin(self, module, phase='loading'):
        self._current = module
        return self._set(module, 'loading', phase=phase, error='')

    def confirm(self, module, piece, ok=True, detail=''):
        """An external confirmation (selftest results, an operator)."""
        with self._lock:
            row = self._row(module)
            if piece == 'selftest':
                row['selftest'] = {'status': 'passed' if ok else 'failed',
                                   'detail': str(detail)[:2000],
                                   'at': time.time()}
            else:
                row['confirmed'].setdefault(piece, {})['external'] = {
                    'ok': bool(ok), 'detail': str(detail)[:2000]}
        self._mirror(module)
        return self.get(module)

    def fail(self, module, error, phase='failed'):
        self._current = None
        return self._set(module, 'failed', phase=phase, error=str(error))

    def block(self, module, error):
        return self._set(module, 'blocked', phase='blocked', error=str(error))

    def invalid(self, module, reason):
        self._current = None
        return self._set(module, 'invalid', phase='declaration', error=str(reason))

    def disabled(self, module, reason=''):
        return self._set(module, 'disabled', phase='gate', error=reason)

    def put_away(self, module):
        return self._set(module, 'put-away', phase='put-away', error='',
                         confirmed={}, missing={})

    def on_transition(self, module, status, row=None):
        """The boot/admission worker's status words, mapped."""
        row = row or {}
        if status == 'loading':
            self.begin(module)
        elif status == 'online':
            self.verify(module)
        elif status == 'failed':
            self.fail(module, row.get('error', ''))
        elif status == 'blocked':
            self.block(module, row.get('error', ''))
        elif status == 'disabled':
            self.disabled(module, row.get('error', ''))

    # -- verification against the live server -------------------------
    def _router_templates(self):
        app = self.polServer.falconServer
        out = set()

        def walk(node):
            if getattr(node, 'resource', None) is not None:
                out.add(node.uri_template)
            for child in getattr(node, 'children', []) or []:
                walk(child)
        for root in getattr(app._router, '_roots', []) or []:
            walk(root)
        return {norm_route(t) for t in out}

    def verify(self, module):
        """Recompute confirmed/missing per expected piece from the live
        server; state → online (all structural pieces live) or degraded."""
        polServer = self.polServer
        manager = polServer.manager
        with self._lock:
            expected = json.loads(json.dumps(self._row(module)['expected']))
            state_before = self._row(module)['state']
        if state_before == 'invalid':
            return self.get(module)
        self._current = None
        confirmed, missing = {}, {}
        typing = getattr(manager, 'objectTypingDict', {}) or {}
        tables = getattr(manager, 'objectTables', {}) or {}
        templates = self._router_templates()

        names = (expected.get('classes') or {}).get('names') or []
        if names:
            # typed = the class is a definition class here; the table
            # dict only appears once a row exists, so it is not required
            live = [n for n in names if n in typing]
            confirmed['classes'] = {'count': len(live), 'of': len(names)}
            gone = [n for n in names if n not in live]
            if gone:
                missing['classes'] = gone
            crude_live = [n for n in names if norm_route('/' + n) in templates]
            confirmed['crude'] = {'count': len(crude_live), 'of': len(names)}
            gone = [n for n in names if n not in crude_live]
            if gone:
                missing['crude'] = ['/' + n for n in gone]

        if expected.get('endpoints'):
            ran = module in (getattr(polServer, 'endpointConstructed', []) or [])
            confirmed['endpoints'] = {'count': int(ran), 'of': 1}
            if not ran:
                missing['endpoints'] = [expected['endpoints']['ref']]

        paths = (expected.get('routes') or {}).get('paths') or []
        if paths:
            live = [p for p in paths if norm_route(p) in templates]
            confirmed['routes'] = {'count': len(live), 'of': len(paths)}
            gone = [p for p in paths if p not in live]
            if gone:
                missing['routes'] = gone

        if expected.get('seeds'):
            try:
                want = have = 0
                gone = []
                for triple in _resolve(expected['seeds']['ref']) or []:
                    if not isinstance(triple, (tuple, list)) or len(triple) != 3:
                        continue
                    cname, _cls, rows = triple
                    present = {getattr(o, 'name', None)
                               for o in (tables.get(cname, {}) or {}).values()}
                    for r in rows or []:
                        n = r.get('name') if isinstance(r, dict) else None
                        if not n:
                            continue
                        want += 1
                        if n in present:
                            have += 1
                        else:
                            gone.append('%s:%s' % (cname, n))
                confirmed['seeds'] = {'count': have, 'of': want}
                if gone:
                    missing['seeds'] = gone[:50]
            except Exception as exc:
                missing['seeds'] = ['unresolvable %s (%s)' % (expected['seeds']['ref'], exc)]

        refs = (expected.get('pages') or {}).get('refs') or []
        if refs:
            present = {getattr(o, 'name', None)
                       for o in (tables.get('DisplayDefinition', {}) or {}).values()}
            want = have = 0
            gone = []
            for ref in refs:
                try:
                    for page in _resolve(ref) or []:
                        n = page.get('name') if isinstance(page, dict) else None
                        if not n:
                            continue
                        want += 1
                        if n in present:
                            have += 1
                        else:
                            gone.append(n)
                except Exception as exc:
                    gone.append('unresolvable %s (%s)' % (ref, exc))
            confirmed['pages'] = {'count': have, 'of': want}
            if gone:
                missing['pages'] = gone

        structural_missing = [p for p in STRUCTURAL if p in missing]
        state = 'online' if not structural_missing else 'degraded'
        error = '' if state == 'online' else 'not live: ' + ', '.join(
            '%s (%s)' % (p, ', '.join(map(str, missing[p][:3]))) for p in structural_missing)
        return self._set(module, state, phase='verified', error=error,
                         confirmed=confirmed, missing=missing,
                         verifiedAt=time.time())

    def verify_all(self):
        with self._lock:
            names = [m for m, r in self.rows.items()
                     if r['state'] not in ('disabled', 'put-away', 'invalid',
                                           'failed', 'blocked')]
        for m in names:
            try:
                self.verify(m)
            except Exception as exc:
                self._set(m, 'degraded', error='verify raised: %s: %s'
                          % (type(exc).__name__, exc))

    # -- the health view -----------------------------------------------
    def snapshot(self):
        with self._lock:
            rows = json.loads(json.dumps(self.rows))
        counts = {s: 0 for s in STATES}
        for r in rows.values():
            counts[r['state']] = counts.get(r['state'], 0) + 1
        unhealthy = sorted(m for m, r in rows.items()
                           if r['state'] in ('degraded', 'failed', 'blocked', 'invalid'))
        return {'ok': not unhealthy,
                'counts': {k: v for k, v in counts.items() if v},
                'moduleCount': len(rows),
                'unhealthy': unhealthy,
                'modules': rows}

    # -- durable mirror ---------------------------------------------------
    def _mirror(self, module):
        manager = getattr(self.polServer, 'manager', None)
        if manager is None or getattr(manager, 'db', None) is None:
            return
        if 'ModuleRegistration' not in (getattr(manager, 'objectTypingDict', {}) or {}):
            return
        try:
            row = self.get(module)
            instance = os.environ.get('POLARI_INSTANCE_NAME') or os.environ.get('HOSTNAME') or 'local'
            table = manager.objectTables.get('ModuleRegistration', {}) or {}
            found = next((o for o in table.values()
                          if getattr(o, 'module_name', None) == module), None)
            fields = dict(
                module_name=module, instance_name=instance, state=row['state'],
                source=row['source'], app_kind=row['appKind'], version=row['version'],
                phase=row['phase'], phase_started_at=row['phaseStartedAt'] or 0.0,
                verified_at=row['verifiedAt'] or 0.0,
                boot_id=getattr(getattr(self.polServer, 'bootRegistry', None), 'boot_id', ''),
                expected_json=json.dumps(row['expected'], sort_keys=True),
                confirmed_json=json.dumps(row['confirmed'], sort_keys=True),
                missing_json=json.dumps(row['missing'], sort_keys=True),
                error=row['error'][:2000],
                selftest_status=row['selftest'].get('status', 'not-run'),
                selftest_detail=str(row['selftest'].get('detail', ''))[:2000])
            if found is None:
                ModuleRegistration(name='%s@%s' % (module, instance), manager=manager, **fields)
            else:
                changed = False
                for k, v in fields.items():
                    if getattr(found, k, None) != v:
                        setattr(found, k, v)
                        changed = True
                if changed:
                    manager.db.saveInstanceInDB(found)
        except Exception as exc:
            print('[Registrar] mirror failed for %s: %s' % (module, exc), flush=True)

    def mirror_all(self):
        for m in list(self.rows):
            self._mirror(m)
