"""
selftest_outbound — the outbound wrapper, the trace header, and the
STRAGGLER GUARD (ct-3, CAUSAL_TRACE_OBJECT_FLOW_DESIGN.md §2/§5/§5a).

    PYTHONPATH=.:modules python3 polariApiServer/selftest_outbound.py

Two jobs in one file, both of them "stated, not silent":

**The guard.** Greps the whole tree for bare `requests.` / `urllib.request.
urlopen` / `http.client.HTTP*Connection` / `httpx.` outside `outbound.py` and
asserts the hit set equals `KNOWN_STRAGGLERS` exactly. A NEW unlisted send
FAILS by path — an unwrapped call is a send the map cannot see and the ct-9
policy cannot govern. A LISTED site that has disappeared fails too, so the
table can never quietly describe a tree that has moved on. Every straggler
carries the REASON it is one; nothing is here because nobody looked.

**The units.** No network is touched: `requests` and `urllib.request` are
monkeypatched, and the recorder is a fake. What is proven is the contract the
migration depends on — the header goes only to peers, recording never changes
a result, and a failed send is still recorded.
"""

import os
import re
import sys
import types

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, 'modules'))

from polariApiServer import outbound          # noqa: E402

PASSED = []
FAILED = []


def check(name, cond, detail=''):
    (PASSED if cond else FAILED).append(name if cond
                                        else f'{name} :: {detail}')


# =====================================================================
# 1. THE STRAGGLER TABLE — file -> why it is not through the wrapper
# =====================================================================

#: Directories the guard does not walk: vendored code we do not own, build
#: output, and the test tree (a test IS allowed to dial a live server).
SKIP_DIRS = {'.git', 'node_modules', 'venv', '.venv', 'site-packages',
             '__pycache__', 'tests', 'dist', 'build', '.angular',
             'target', 'coverage', 'test-results'}

#: Files exempt by name: this guard, the seam itself, and any *selftest*.
SKIP_FILES = {'outbound.py', 'selftest_outbound.py'}

#: The patterns that name a raw send.
PATTERNS = re.compile(
    r'requests\.(get|post|put|patch|delete|head|request|Session)\('
    r'|urllib\.request\.urlopen\('
    r'|http\.client\.HTTPS?Connection\('
    r'|httpx\.')

#: EVERY remaining raw send, with the reason it stayed raw. ct-3 migrated the
#: product sends of design §5; what is left is either owned by another agent
#: this round, a test/proof harness, or a send whose shape the wrapper does
#: not fit yet. Each line is a commitment: it gets migrated or it gets a
#: standing reason, and the guard fails the day one is added without either.
KNOWN_STRAGGLERS = {
    # --- owned elsewhere this round -----------------------------------
    'modules/security/custom/kc_admin.py':
        'owned by ct-1\'s agent this round (modules/security is theirs) — '
        'migrate in the slice that lands security_trace',

    # --- in-tree proof / test harnesses (they dial a LIVE server on '
    #     purpose; wrapping them would record the harness, not the product)
    'moduleService/dyn_proofs/collab_proof.py': 'dyn proof harness',
    'moduleService/dyn_proofs/dyn2_proof.py': 'dyn proof harness',
    'moduleService/dyn_proofs/dyn3_proof.py': 'dyn proof harness',
    'moduleService/dyn_proofs/dyn4_proof.py': 'dyn proof harness',
    'moduleService/dyn_proofs/dyn5_proof.py': 'dyn proof harness',
    'moduleService/dyn_proofs/dyn68_proof.py': 'dyn proof harness',
    'moduleService/dyn_proofs/dyn7_proof.py': 'dyn proof harness',
    'moduleService/dyn_proofs/pub0_sizing.py': 'dyn sizing harness',
    'moduleService/dyn_proofs/reticulum_proof.py': 'dyn proof harness',
    'modules/testing/custom/twin_http.py':
        'the testing module\'s own HTTP probe — it IS the harness',
    'modules/testing/custom/twin_fixtures.py': 'testing-module fixture setup',
    'modules/testing/custom/check_runners.py': 'testing-module check runner',
    'modules/testing/custom/app_benchmark.py': 'testing-module benchmark',
    'topology/topology_testing_api.py':
        'topology self-test probes, not a product send',

    # --- boot / build-time fetches, outside any request's cause --------
    'moduleService/json_seeds.py':
        'boot-time seed fetch — design §3 gives seeds a `boot` root cause, '
        'which is ct-1/ct-2 territory, not this wrapper',
    'modules/iso/custom/iso_builder.py':
        'Ubuntu archive downloads during ISO build (iso arc) — a build step '
        'on the host, not a Polari request',
    'modules/iso/custom/iso_autoinstall.py':
        'the urlopen is inside a TEMPLATE STRING executed on the INSTALLED '
        'machine — it is not code this process ever runs',

    # --- sends whose shape the ct-3 wrapper does not fit yet -----------
    'polariNetworking/managedSink.py':
        'httpx ASYNC client — outbound.send is synchronous; an async seam '
        'is its own slice',
    'polariApiProfiler/apiProfiler.py':
        'the legacy profiler engine; endpoint_fetch.py is the migrated seam '
        'and apiProfiler follows when it is folded into it',
    'polariApiProfiler/api_discovery.py':
        'discovery probe against an API domain — follows apiProfiler',

    # --- product sends not in design §5\'s list; named, not forgotten ---
    'polariApiServer/tileGeneratorAPI.py':
        'map-tile fetch from a tile server, on its own thread (design §4 '
        'thread boundary) — needs the cause handed in first',
    'modules/printing_suite/custom/adapters.py':
        'Moonraker/printer adapters (printing arc) — not in the §5 list',
    'modules/resources/custom/node_resources.py':
        'node resource probe across the swarm — not in the §5 list',
    'modules/resources/custom/profile_analysis.py':
        'node profile probe — not in the §5 list',
    'modules/dmvdata/custom/census_pull.py':
        'US Census pull (dmvdata arc) — not in the §5 list',
    'modules/cntfet/custom/cnt_snapshot.py':
        'snapshot artifact download — not in the §5 list',
}


def _walk_py():
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fn in filenames:
            if not fn.endswith('.py') or fn in SKIP_FILES:
                continue
            if 'selftest' in fn:
                continue
            yield os.path.join(dirpath, fn)


def scan():
    """{relative path: [line numbers]} for every raw send in the tree."""
    hits = {}
    for path in _walk_py():
        try:
            with open(path, encoding='utf-8', errors='replace') as fh:
                lines = fh.readlines()
        except OSError:
            continue
        found = [i for i, line in enumerate(lines, 1)
                 if PATTERNS.search(line)]
        if found:
            hits[os.path.relpath(path, ROOT)] = found
    return hits


def test_straggler_guard():
    hits = scan()
    new = sorted(set(hits) - set(KNOWN_STRAGGLERS))
    gone = sorted(set(KNOWN_STRAGGLERS) - set(hits))
    check('guard: no NEW unwrapped send', not new,
          'these bypass outbound.py — wrap them or list them with a '
          'reason: ' + ', '.join(f'{p}:{hits[p][0]}' for p in new))
    check('guard: every listed straggler still exists', not gone,
          'listed but no longer found (the table must not describe a tree '
          'that moved on): ' + ', '.join(gone))
    check('guard: every straggler carries a reason',
          all(str(v).strip() for v in KNOWN_STRAGGLERS.values()),
          'a straggler with an empty reason is a straggler nobody looked at')
    check('guard: the tree was actually walked', len(list(_walk_py())) > 200,
          'walked too few files — SKIP_DIRS is eating the tree')


# =====================================================================
# 2. THE RECORDER CONTRACT
# =====================================================================

class FakeRecorder:
    """Stands in for ct-1's `security.custom.security_trace`."""

    def __init__(self, raises=False, takes_detail=True):
        self.calls = []
        self.raises = raises
        self.takes_detail = takes_detail

    def install(self):
        mod = types.ModuleType('security.custom.security_trace')
        rec = self

        if self.takes_detail:
            def record_outbound(manager, system_kind, system_name, means,
                                payload_classes, detail=''):
                rec.calls.append((system_kind, system_name, means,
                                  list(payload_classes), detail, manager))
                if rec.raises:
                    raise RuntimeError('recorder exploded')
        else:
            def record_outbound(manager, system_kind, system_name, means,
                                payload_classes):
                rec.calls.append((system_kind, system_name, means,
                                  list(payload_classes), None, manager))
                if rec.raises:
                    raise RuntimeError('recorder exploded')

        mod.record_outbound = record_outbound
        _install_security_module(mod)
        return self


def _install_security_module(trace_mod):
    for name in ('security', 'security.custom'):
        if name not in sys.modules:
            pkg = types.ModuleType(name)
            pkg.__path__ = []
            sys.modules[name] = pkg
    sys.modules['security.custom'].security_trace = trace_mod
    sys.modules['security.custom.security_trace'] = trace_mod


def _uninstall_security_module():
    sys.modules.pop('security.custom.security_trace', None)
    custom = sys.modules.get('security.custom')
    if custom is not None and hasattr(custom, 'security_trace'):
        del custom.security_trace


def test_recorder_contract():
    rec = FakeRecorder().install()
    out = outbound.send('odoo', 'main', 'json-rpc', lambda: 'RESULT',
                        payload_classes=('ProductOrder',), manager='MGR')
    check('send returns fn() unchanged', out == 'RESULT', repr(out))
    check('recorder got kind/name/means/classes on success',
          rec.calls and rec.calls[0][:4] == ('odoo', 'main', 'json-rpc',
                                             ['ProductOrder']),
          repr(rec.calls))
    check('outcome detail is "ok" on success',
          rec.calls and rec.calls[0][4] == 'ok', repr(rec.calls))
    check('the explicit manager is passed through',
          rec.calls and rec.calls[0][5] == 'MGR', repr(rec.calls))

    rec = FakeRecorder().install()

    def boom():
        raise ValueError('nope')

    try:
        outbound.send('peer', 'kitchen-node', 'rest', boom,
                      payload_classes=('MealEntry',))
        raised = None
    except ValueError as exc:
        raised = exc
    check('the send exception propagates unchanged',
          isinstance(raised, ValueError) and str(raised) == 'nope',
          repr(raised))
    check('recorder got the edge on FAILURE too',
          rec.calls and rec.calls[0][:4] == ('peer', 'kitchen-node', 'rest',
                                             ['MealEntry']),
          repr(rec.calls))
    check('outcome detail names the exception type',
          rec.calls and rec.calls[0][4] == 'ValueError', repr(rec.calls))

    rec = FakeRecorder(raises=True).install()
    out = outbound.send('s3', 'artifacts', 's3', lambda: 42)
    check('a RAISING recorder never changes the result', out == 42, repr(out))

    rec = FakeRecorder(takes_detail=False).install()
    out = outbound.send('mqtt', 'broker', 'mqtt', lambda: 7)
    check('a recorder with no detail kwarg is called without it',
          out == 7 and rec.calls and rec.calls[0][4] is None, repr(rec.calls))
    check('no duplicate row when detail is unsupported',
          len(rec.calls) == 1, repr(rec.calls))

    _uninstall_security_module()
    out = outbound.send('other', 'nothing', 'rest', lambda: 'still here')
    check('an ABSENT recorder never changes the result',
          out == 'still here', repr(out))


def test_wrap():
    rec = FakeRecorder().install()
    with outbound.wrap('provider', 'localai', 'sdk', ('Article',)):
        pass
    check('wrap records on clean exit',
          rec.calls and rec.calls[0][:5] == ('provider', 'localai', 'sdk',
                                             ['Article'], 'ok'),
          repr(rec.calls))

    rec = FakeRecorder().install()
    try:
        with outbound.wrap('s3', 'appstore', 's3'):
            raise KeyError('k')
    except KeyError:
        suppressed = False
    else:
        suppressed = True
    check('wrap never suppresses an exception', not suppressed)
    check('wrap records the exception type',
          rec.calls and rec.calls[0][4] == 'KeyError', repr(rec.calls))

    rec = FakeRecorder().install()

    @outbound.wrap('engine', 'msci', 'rest')
    def decorated(x):
        return x * 2

    check('wrap works as a decorator', decorated(21) == 42)
    check('the decorator records', len(rec.calls) == 1, repr(rec.calls))
    _uninstall_security_module()


# =====================================================================
# 3. THE TRACE HEADER — peers only, ids only, never the actor
# =====================================================================

def test_trace_header():
    from accessControl import cause_context

    real_enabled = cause_context.tracing_enabled
    cause_context.tracing_enabled = lambda: True
    token = cause_context.root_cause('api', 'PUT /api/MealEntry/{id}',
                                     actor='sub-abc',
                                     groups=('household',))
    try:
        peer = outbound.trace_headers('peer')
        check('peer sends carry X-Polari-Trace',
              list(peer) == [cause_context.TRACE_HEADER], repr(peer))
        value = peer[cause_context.TRACE_HEADER]
        check('the header is <trace_id>/<parent_id>',
              value.count('/') == 1 and all(value.split('/')), value)
        check('the header NEVER carries the actor',
              'sub-abc' not in value, value)
        check('the header NEVER carries groups',
              'household' not in value, value)
        for kind in ('odoo', 'keycloak', 's3', 'engine', 'self', 'other'):
            check(f'{kind} sends carry NO trace header',
                  outbound.trace_headers(kind) == {},
                  repr(outbound.trace_headers(kind)))
    finally:
        cause_context.pop_cause(token)
        cause_context.tracing_enabled = real_enabled

    check('with NO cause (production posture) even a peer send has no header',
          outbound.trace_headers('peer') == {},
          repr(outbound.trace_headers('peer')))


# =====================================================================
# 4. THE HELPER PATHS — same library, same timeout, no network
# =====================================================================

class _FakeResp:
    status = 200

    def __init__(self, req=None):
        self.req = req

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def read(self):
        return b'{}'


def test_http_request_urllib():
    import urllib.request as ur
    rec = FakeRecorder().install()
    seen = {}

    real = ur.urlopen

    def fake_urlopen(target, timeout=None, **kw):
        seen['target'] = target
        seen['timeout'] = timeout
        seen['kw'] = kw
        return _FakeResp(target)

    ur.urlopen = fake_urlopen
    try:
        with outbound.http_request('engine', 'msci', 'GET',
                                   'http://worker/capability',
                                   means='probe', timeout=5,
                                   lib='urllib') as resp:
            check('urllib path returns a context manager',
                  isinstance(resp, _FakeResp))
        check('urllib path builds a Request from a plain URL',
              isinstance(seen['target'], ur.Request), repr(seen['target']))
        check('urllib path preserves the timeout', seen['timeout'] == 5,
              repr(seen['timeout']))
        check('urllib path preserves the method',
              seen['target'].get_method() == 'GET',
              seen['target'].get_method())
        check('a non-peer urllib send carries no trace header',
              not any(k.lower() == 'x-polari-trace'
                      for k in seen['target'].headers),
              repr(seen['target'].headers))
        check('the engine edge was recorded',
              rec.calls and rec.calls[0][:3] == ('engine', 'msci', 'probe'),
              repr(rec.calls))

        # a pre-built Request keeps its own headers and gains only the trace
        from accessControl import cause_context
        real_enabled = cause_context.tracing_enabled
        cause_context.tracing_enabled = lambda: True
        token = cause_context.root_cause('api', 'POST /api/refs/apply-write')
        try:
            req = ur.Request('http://peer/api/refs/apply-write', data=b'{}',
                             headers={'Content-Type': 'application/json'},
                             method='POST')
            outbound.http_request('peer', 'kitchen-node', 'POST', req,
                                  payload_classes=('MealEntry',),
                                  timeout=6, lib='urllib')
        finally:
            cause_context.pop_cause(token)
            cause_context.tracing_enabled = real_enabled
        sent = seen['target']
        check('a pre-built Request is used as-is, not rebuilt',
              sent is req, repr(sent))
        check('a peer send gains X-Polari-Trace on the Request',
              any(k.lower() == 'x-polari-trace' for k in sent.headers),
              repr(sent.headers))
        check('the site\'s own headers survive',
              any(k.lower() == 'content-type' for k in sent.headers),
              repr(sent.headers))
        check('the peer edge carries the payload CLASS',
              rec.calls[-1][:4] == ('peer', 'kitchen-node', 'rest',
                                    ['MealEntry']),
              repr(rec.calls[-1]))

        # a raising urlopen still records, then propagates
        rec2 = FakeRecorder().install()

        def angry(*a, **k):
            raise OSError('unreachable')

        ur.urlopen = angry
        try:
            outbound.http_request('reticulum', 'sidecar', 'GET',
                                  'http://side/status', timeout=3,
                                  lib='urllib')
            raised = None
        except OSError as exc:
            raised = exc
        check('a urllib failure propagates', isinstance(raised, OSError))
        check('a urllib failure is still recorded',
              rec2.calls and rec2.calls[0][4] == 'OSError', repr(rec2.calls))
    finally:
        ur.urlopen = real
        _uninstall_security_module()


def test_http_request_requests():
    try:
        import requests
    except ImportError:
        check('requests path exercised', True, 'requests not installed')
        return
    rec = FakeRecorder().install()
    seen = {}
    real = requests.request

    def fake_request(method, url, **kw):
        seen.update({'method': method, 'url': url, 'kw': kw})
        return 'RESPONSE'

    requests.request = fake_request
    try:
        out = outbound.http_request('keycloak', 'Polari', 'GET',
                                    'http://kc/admin/realms/Polari/roles',
                                    headers={'Authorization': 'Bearer x'},
                                    timeout=10, lib='requests')
        check('requests path returns the library object', out == 'RESPONSE')
        check('requests path preserves method + timeout',
              seen['method'] == 'GET' and seen['kw']['timeout'] == 10,
              repr(seen))
        check('requests path preserves the site headers',
              seen['kw']['headers'] == {'Authorization': 'Bearer x'},
              repr(seen['kw']['headers']))
        check('the keycloak edge carries NO payload class',
              rec.calls and rec.calls[0][:4] == ('keycloak', 'Polari',
                                                 'rest', []),
              repr(rec.calls))
    finally:
        requests.request = real
        _uninstall_security_module()


def test_unknown_lib():
    try:
        outbound.http_request('other', 'x', 'GET', 'http://x', lib='curl')
        raised = None
    except ValueError as exc:
        raised = exc
    check('an unknown lib is refused by name, not guessed',
          isinstance(raised, ValueError) and 'curl' in str(raised),
          repr(raised))


# =====================================================================
# 5. THE MIGRATED SITES STILL IMPORT
# =====================================================================

MIGRATED = [
    'accessControl.keycloak_client', 'polariApiServer.authMeAPI',
    'odooconnect.custom.odoo_client', 'odooconnect.custom.odoo_sync',
    'collab.livekit_remote', 'reticulum.rns_remote',
    'materialsScience.engines.remote', 'mathshapes.cad_remote',
    'cntfet.cnt_remote', 'topology.provider_registry',
    'polariPeers.peers_api', 'polariPeers.join_flow',
    'polariRefs.remote_api', 'polariApiServer.ai_actions',
    'polariApiServer.ai_tools', 'polariApiServer.reasoning_provider',
    'polariApiServer.voiceAPI', 'polariDBmanagement.managedObjectStore',
    'appstore.custom.appstore_minio', 'mqttbridge.mqtt_api',
    'polariApiProfiler.endpoint_fetch',
]


def test_migrated_sites_import():
    import importlib
    bad = []
    for name in MIGRATED:
        try:
            importlib.import_module(name)
        except Exception as exc:      # noqa: BLE001
            bad.append(f'{name}: {type(exc).__name__}: {exc}')
    check(f'all {len(MIGRATED)} migrated modules still import', not bad,
          '; '.join(bad))


def test_vocabulary():
    check('system kinds are the design §2 vocabulary',
          outbound.SYSTEM_KINDS == ('keycloak', 'odoo', 'livekit',
                                    'reticulum', 'engine', 'provider',
                                    'peer', 'self', 's3', 'mqtt',
                                    'profiler', 'other'),
          repr(outbound.SYSTEM_KINDS))
    check('means are the design §2 wires',
          outbound.MEANS == ('rest', 'json-rpc', 's3', 'grpc', 'mqtt',
                             'sdk', 'probe'),
          repr(outbound.MEANS))


# =====================================================================
# 6. THE ct-9 TRAFFIC POLICY (closed by default, consulted BEFORE the send)
# =====================================================================

def _install_traffic(verdict=None, raises=False):
    """Stand in for ct-9's `security.custom.security_traffic`. The wrapper
    must work with it, without it, and with a broken one."""
    mod = types.ModuleType('security.custom.security_traffic')
    calls = []

    def outbound_verdict(manager, system_kind, system_name, means,
                         payload_classes=()):
        calls.append((system_kind, system_name, means, list(payload_classes)))
        if raises:
            raise RuntimeError('policy exploded')
        return dict(verdict or {})

    mod.outbound_verdict = outbound_verdict
    for name in ('security', 'security.custom'):
        if name not in sys.modules:
            pkg = types.ModuleType(name)
            pkg.__path__ = []
            sys.modules[name] = pkg
    sys.modules['security.custom'].security_traffic = mod
    sys.modules['security.custom.security_traffic'] = mod
    return calls


def _uninstall_traffic():
    sys.modules.pop('security.custom.security_traffic', None)
    custom = sys.modules.get('security.custom')
    if custom is not None and hasattr(custom, 'security_traffic'):
        del custom.security_traffic


REFUSED = {'allowed': False, 'rule': 'suggested', 'knob': 'enforce',
           'name': 'odoo|main|json-rpc', 'state': 'suggested',
           'why': 'closed by default'}


def test_traffic_policy():
    rec = FakeRecorder().install()
    calls = _install_traffic(REFUSED)
    ran = []
    try:
        outbound.send('odoo', 'main', 'json-rpc', lambda: ran.append(1),
                      payload_classes=('ProductOrder',), manager='MGR')
        refused = None
    except outbound.OutboundRefused as exc:
        refused = exc
    check('ENFORCE: an unconfirmed send raises OutboundRefused and the call '
          'never runs', refused is not None and not ran, repr(refused))
    check('the refusal names the policy row and the door that confirms it',
          'odoo|main|json-rpc' in str(refused)
          and '/api/security/traffic/outbound/' in str(refused), str(refused))
    check('the policy saw the same edge the recorder does',
          calls == [('odoo', 'main', 'json-rpc', ['ProductOrder'])],
          repr(calls))
    check('a refused send is still an EDGE, recorded as refused-by-policy '
          '(the map must show the send that did not happen)',
          rec.calls and rec.calls[0][4] == 'refused-by-policy', repr(rec.calls))

    rec = FakeRecorder().install()
    ran = []
    try:
        with outbound.wrap('s3', 'artifacts', 's3', ('Artifact',)):
            ran.append(1)
        refused = None
    except outbound.OutboundRefused as exc:
        refused = exc
    check('ENFORCE at `wrap`: an SDK send is refused on the way IN, so the '
          'library is never reached, and it is recorded ONCE',
          refused is not None and not ran and len(rec.calls) == 1
          and rec.calls[0][4] == 'refused-by-policy', repr(rec.calls))

    _install_traffic(dict(REFUSED, knob='advisory'))
    out = outbound.send('odoo', 'main', 'json-rpc', lambda: 'sent')
    check('ADVISORY: the same refusal proceeds (dev warns, never blocks)',
          out == 'sent', repr(out))

    _install_traffic(dict(REFUSED, knob='off'))
    out = outbound.send('odoo', 'main', 'json-rpc', lambda: 'sent')
    check('OFF: nothing acts on the verdict', out == 'sent', repr(out))

    _install_traffic({'allowed': True, 'rule': 'confirmed', 'knob': 'enforce'})
    out = outbound.send('odoo', 'main', 'json-rpc', lambda: 'sent')
    check('ENFORCE + a CONFIRMED row: the send goes through', out == 'sent',
          repr(out))

    _install_traffic(REFUSED, raises=True)
    out = outbound.send('odoo', 'main', 'json-rpc', lambda: 'sent')
    check('a policy that BLOWS UP never blocks a send (a guard must not be '
          'able to take the outbound path down)', out == 'sent', repr(out))

    _uninstall_traffic()
    out = outbound.send('odoo', 'main', 'json-rpc', lambda: 'sent')
    check('an ABSENT traffic policy never changes the result (ct-3 behaviour '
          'exactly)', out == 'sent', repr(out))
    _uninstall_security_module()


def main():
    for fn in (test_straggler_guard, test_recorder_contract, test_wrap,
               test_trace_header, test_http_request_urllib,
               test_http_request_requests, test_unknown_lib,
               test_migrated_sites_import, test_vocabulary,
               test_traffic_policy):
        try:
            fn()
        except Exception as exc:      # noqa: BLE001
            FAILED.append(f'{fn.__name__} BLEW UP :: '
                          f'{type(exc).__name__}: {exc}')
    total = len(PASSED) + len(FAILED)
    for line in FAILED:
        print('FAIL', line)
    print(f'selftest_outbound: {len(PASSED)}/{total}')
    return 1 if FAILED else 0


if __name__ == '__main__':
    sys.exit(main())
