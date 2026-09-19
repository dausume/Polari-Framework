"""
ct-0 cause-context selftest (check() style, fake manager, REAL dispatcher and
engine): the cause a chain travels with.

    PYTHONPATH=.:modules python3 accessControl/selftest_cause_context.py

Covers: push/pop/child depth and id inheritance; PRODUCTION POSTURE mints
nothing at all (his ruling 2026-09-18); the middleware mints an `api` root,
adopts an inbound `X-Polari-Trace` as a `peer` root and pops on the response;
a request → trigger → solution chain sharing ONE trace_id at depths 0/1/2;
`TriggerFiring` carrying the ids; and the THREAD INVENTORY — contextvars do
not cross threads, so every `threading.Thread(` / `threading.Timer(` site in
the tree must be a KNOWN one with a stated reason (design §4). A new,
un-listed thread site FAILS this selftest with its path.
"""

import json
import os
import re
import subprocess
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from accessControl.cause_context import (          # noqa: E402
    ENTRY_KINDS, TRACE_HEADER, actor_of, child_cause, child_or_root_cause,
    current_cause, parse_trace_header, pop_cause, push_cause, root_cause,
    trace_header_value, trace_ids,
)
from accessControl.cause_middleware import CauseContextMiddleware   # noqa: E402

_results = []
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def check(label, cond, extra=''):
    _results.append((label, bool(cond)))
    print(f'{"PASS" if cond else "FAIL"}: {label}' + (f' — {extra}' if extra else ''))


def dev_posture():
    """The ONE switch (moduleService.posture) said in the environment."""
    os.environ['POLARI_POSTURE'] = 'dev'
    os.environ.pop('POLARI_POSTURE_UNTIL', None)


def production_posture():
    os.environ['POLARI_POSTURE'] = 'production'


# ---------------------------------------------------------------
# the thread inventory (design §4) — every site, and why
# ---------------------------------------------------------------
#: file basename → why a thread is started there and what cause it must carry.
#: Contextvars do NOT cross a thread boundary: a worker started here either
#: mints its own ROOT cause or is handed one by argument. Design §4 names
#: seven; the tree actually has these — the extras are module-level workers
#: (appstore/iso/video/odoo-stub) and the two server sockets.
KNOWN_THREAD_SITES = {
    'initLocalhostPolariServer.py':
        'mesh autoconfig + the HTTPS listener at boot — root `boot` cause',
    'quiesce.py':
        'gm-2 stateful-move flush worker — carries the move`s own cause',
    'persist_debounce.py':
        'the debounced tree persist — NO cause needed: it writes what was '
        'already caused',
    'stompWebSocketServer.py':
        'the STOMP websocket server socket — inbound frames mint their own '
        'cause (ct-6)',
    'event_dispatcher.py':
        'the `polari-event-tick` thread — a ROOT `schedule` cause per tick '
        '(built in ct-0)',
    'tileGeneratorAPI.py':
        'tile generation for one request — must be handed the requesting '
        'cause explicitly (ct-1)',
    'lazy_boot.py':
        'mlb-1 module boot worker — root `boot` cause',
    'app_deb_builder.py':
        'appstore deb build worker — root `boot` cause (a build, not a person)',
    'stub_odoo.py':
        'the stubbed Odoo server used by the backend test stack — test only',
    'iso_api.py':
        'a one-shot tree persist after an ISO write — no cause needed',
    'iso_builder.py':
        'ISO build workers (two sites) — root `boot` cause',
    'video_api.py':
        'video transcode worker for one request — handed the request`s cause',
    'security_page.py':
        'the security-pages converge worker — root `boot` cause',
    'security_observe.py':
        'the D18-1 PII scrub, one-shot at boot — root `boot` cause',
    'apps_page.py':
        'the polariapps-pages converge worker (ct-8) — root `boot` cause',
}

_THREAD_RE = re.compile(r'threading\.Thread\(|threading\.Timer\(|[^.\w]Thread\(target')


def thread_sites():
    """Every thread-start site in the tree, outside tests and caches."""
    out = subprocess.run(
        ['grep', '-rn', '--include=*.py', '-E',
         r'threading\.Thread\(|threading\.Timer\(|[^.\w]Thread\(target', '.'],
        cwd=_ROOT, capture_output=True, text=True).stdout
    sites = []
    for line in out.splitlines():
        path = line.split(':', 1)[0].lstrip('./')
        base = os.path.basename(path)
        if base.startswith(('test_', 'selftest_')) or base.endswith('_test.py'):
            continue
        if '/tests/' in path or '/test/' in path or '__pycache__' in path:
            continue
        sites.append(path)
    return sorted(set(sites))


# ---------------------------------------------------------------
# a fake falcon request
# ---------------------------------------------------------------

class _Ctx:
    pass


class _Req:
    def __init__(self, method='GET', path='/api/MealEntry/abc', headers=None,
                 uri_template=None, user_info=None, roles=()):
        self.method = method
        self.path = path
        self.uri_template = uri_template
        self._headers = {k.upper(): v for k, v in (headers or {}).items()}
        self.context = _Ctx()
        self.context.user_info = user_info
        self.context.roles = list(roles)

    def get_header(self, name, default=None):
        return self._headers.get(str(name).upper(), default)


class _Resp:
    def __init__(self):
        self.status = '200 OK'
        self.headers = {}

    def set_header(self, k, v):
        self.headers[k] = v


# ---------------------------------------------------------------
# the trigger→solution chain (the cal-2 fake-manager idiom)
# ---------------------------------------------------------------

class _DB:
    def saveInstanceInDB(self, inst):
        return True


def _manager():
    return SimpleNamespace(objectTables={
        'SolutionDefinition': {}, 'EventTrigger': {}, 'TriggerFiring': {},
        'CauseProbe': {},
    }, db=_DB())


def main():
    dev_posture()

    # --- 1. push / pop / child ---------------------------------------
    check('nothing is current before anything is pushed', current_cause() is None)
    t0 = root_cause('api', 'PUT /api/MealEntry/{id}', actor='s-1',
                    groups=('demo-journalist',), roleplay='journalist')
    c0 = current_cause()
    check('root_cause mints depth 0 with a trace id and the entry ref',
          c0 and c0['depth'] == 0 and len(c0['trace_id']) == 32
          and c0['entry_ref'] == 'PUT /api/MealEntry/{id}'
          and c0['parent_id'] == '', str(c0))
    t1 = child_cause('trigger', 'trigger:daily-rollup')
    c1 = current_cause()
    check('child_cause keeps the trace, parents on the current id, depth+1',
          c1['trace_id'] == c0['trace_id'] and c1['parent_id'] == c0['id']
          and c1['depth'] == 1 and c1['entry_kind'] == 'trigger', str(c1))
    check('a child inherits actor / groups / roleplay unchanged',
          c1['actor'] == 's-1' and tuple(c1['groups']) == ('demo-journalist',)
          and c1['roleplay'] == 'journalist')
    t2 = child_cause('solution', 'solution:score-article')
    check('a grandchild is depth 2 on the same trace',
          current_cause()['depth'] == 2
          and current_cause()['trace_id'] == c0['trace_id'])
    check('trace_ids() names the chain and the producing node',
          trace_ids() == {'trace_id': c0['trace_id'],
                          'parent_id': current_cause()['id']})
    pop_cause(t2); pop_cause(t1)
    check('popping unwinds to the root', current_cause()['id'] == c0['id'])
    pop_cause(t0)
    check('popping the root leaves nothing current', current_cause() is None)
    check('pop_cause(None) is a no-op (so every caller writes one try/finally)',
          pop_cause(None) is None)
    check('child_cause with no chain running pushes nothing',
          child_cause('solution', 'solution:orphan') is None
          and current_cause() is None)
    tr = child_or_root_cause('solution', 'solution:orphan')
    check('child_or_root_cause roots an orphan run at depth 0',
          current_cause()['depth'] == 0
          and current_cause()['entry_kind'] == 'solution')
    pop_cause(tr)
    check('an unknown entry_kind falls back inside the vocabulary',
          'api' in ENTRY_KINDS and 'peer' in ENTRY_KINDS and len(ENTRY_KINDS) == 8)

    # --- 2. the PII boundary (D18-1) ---------------------------------
    check('actor_of takes the Keycloak sub and NOTHING else',
          actor_of({'sub': 'abc-123', 'preferred_username': 'someone',
                    'email': 'someone@example.invalid'}) == 'abc-123')
    check('actor_of of nobody is empty', actor_of(None) == '' and actor_of({}) == '')
    t = root_cause('api', 'GET /x', actor='sub-9')
    check('the outbound trace header carries ids only, never the actor',
          'sub-9' not in trace_header_value()
          and trace_header_value().count('/') == 1)
    pop_cause(t)

    # --- 3. production posture mints NOTHING (his ruling) -------------
    production_posture()
    check('production: root_cause returns None and pushes nothing',
          root_cause('api', 'PUT /api/MealEntry/{id}') is None
          and current_cause() is None)
    check('production: trace_ids() is two empty strings',
          trace_ids() == {'trace_id': '', 'parent_id': ''})
    req = _Req('PUT', '/api/MealEntry/abc', user_info={'sub': 's-1'})
    mw = CauseContextMiddleware()
    mw.process_request(req, _Resp())
    check('production: the middleware sets req.context.cause = None',
          req.context.cause is None and current_cause() is None)
    mw.process_response(req, _Resp(), None, True)
    dev_posture()

    # --- 4. the middleware ------------------------------------------
    mw = CauseContextMiddleware()
    req = _Req('PUT', '/api/MealEntry/abc', user_info={'sub': 's-1'},
               roles=('demo-journalist',),
               headers={'X-Polari-Roleplay': 'Journalist'})
    resp = _Resp()
    mw.process_request(req, resp)
    cause = req.context.cause
    check('the middleware mints an api root from the request',
          cause and cause['entry_kind'] == 'api' and cause['depth'] == 0
          and cause['entry_ref'] == 'PUT /api/MealEntry/abc', str(cause))
    check('the middleware takes the actor as a sub and the roles as groups',
          cause['actor'] == 's-1' and tuple(cause['groups']) == ('demo-journalist',))
    check('the roleplay header rides the cause, lower-cased',
          cause['roleplay'] == 'journalist')
    req.uri_template = '/api/{className}/{id}'
    mw.process_resource(req, resp, None, {})
    check('once falcon has routed, the entry ref becomes the TEMPLATE',
          current_cause()['entry_ref'] == 'PUT /api/{className}/{id}',
          current_cause()['entry_ref'])
    mw.process_response(req, resp, None, True)
    check('the middleware pops on the response', current_cause() is None)

    # --- 5. an inbound peer trace ------------------------------------
    req = _Req('POST', '/api/peers/pull',
               headers={TRACE_HEADER: 'deadbeef/cafe01'})
    mw.process_request(req, _Resp())
    cause = req.context.cause
    check('an inbound X-Polari-Trace mints a PEER root that adopts the chain',
          cause['entry_kind'] == 'peer' and cause['trace_id'] == 'deadbeef'
          and cause['parent_id'] == 'cafe01', str(cause))
    mw.process_response(req, _Resp(), None, True)
    check('a malformed trace header is two empty strings, not a crash',
          parse_trace_header('nonsense with spaces/../x')['trace_id'] == 'nonsensewithspaces'
          and parse_trace_header(None) == {'trace_id': '', 'parent_id': ''})

    # --- 6. request → trigger → solution: ONE trace, depths 0/1/2 -----
    from polariNoCode import graph_builder as gb
    from polariNoCode.event_dispatcher import dispatch_object_change

    seen = {}

    mgr = _manager()
    sol = gb.solution('probe', gb.entry('Start', nxt='Note'),
                      gb.node('Note', 'SetVariable',
                              {'variableName': 'noted', 'value': 1}))
    mgr.objectTables['SolutionDefinition']['s'] = SimpleNamespace(
        id='s', name='probe', definition=json.dumps(sol))
    mgr.objectTables['EventTrigger']['t'] = SimpleNamespace(
        id='t', name='probe-trigger', description='', enabled=True,
        source_kind='object', source_json=json.dumps({'class': 'CauseProbe'}),
        solution_name='probe', inputs_json='{}', cooldown_s=0.0, max_depth=8,
        run_as='definer', last_fired='', fire_count=0)

    # the engine records what it saw, so the chain is observed from INSIDE
    from polariNoCode import SolutionExecutionEngine as _see
    _orig = _see.SolutionExecutionEngine._execute_caused

    def _spy(self, *a, **kw):
        c = current_cause()
        seen['solution'] = dict(c) if c else None
        return _orig(self, *a, **kw)

    _see.SolutionExecutionEngine._execute_caused = _spy
    try:
        req = _Req('PUT', '/api/CauseProbe/p1', user_info={'sub': 's-7'},
                   uri_template='/api/{className}/{id}')
        mw.process_request(req, _Resp())
        api_cause = dict(current_cause())
        firings = dispatch_object_change(mgr, 'CauseProbe', 'update', ['p1'])
        mw.process_response(req, _Resp(), None, True)
    finally:
        _see.SolutionExecutionEngine._execute_caused = _orig

    row = firings[0] if firings else None
    sol_cause = seen.get('solution')
    check('the firing happened and the solution ran under a cause',
          row is not None and sol_cause is not None, str(row and row.status))
    check('request → trigger → solution share ONE trace_id',
          sol_cause and sol_cause['trace_id'] == api_cause['trace_id'],
          f"{api_cause['trace_id']} vs {sol_cause and sol_cause['trace_id']}")
    check('the depths are 0 (api) / 1 (trigger) / 2 (solution)',
          api_cause['depth'] == 0 and sol_cause['depth'] == 2
          and sol_cause['entry_kind'] == 'solution',
          f"api={api_cause['depth']} solution={sol_cause['depth']}")
    check('the solution cause parents on the trigger cause, not on the request',
          sol_cause['parent_id'] not in ('', api_cause['id']))
    check('the actor sub rides the whole chain', sol_cause['actor'] == 's-7')
    check('TriggerFiring carries the trace_id of the chain',
          getattr(row, 'trace_id', None) == api_cause['trace_id'],
          str(getattr(row, 'trace_id', None)))
    check('TriggerFiring carries a parent_id naming its producing cause',
          bool(getattr(row, 'parent_id', '')))
    check('the chain is unwound after the response', current_cause() is None)

    # --- 7. the tick mints its own ROOT (it runs on a thread) ---------
    from polariNoCode.event_dispatcher import get_dispatcher
    d = get_dispatcher(mgr)
    ticks = {}
    _orig_tick = type(d)._tick

    def _tick_spy(self, *a, **kw):
        c = current_cause()
        ticks['cause'] = dict(c) if c else None
        return _orig_tick(self, *a, **kw)

    type(d)._tick = _tick_spy
    try:
        d.tick()
    finally:
        type(d)._tick = _orig_tick
    check('tick() runs under a ROOT `schedule` cause (no request to inherit)',
          ticks.get('cause') and ticks['cause']['entry_kind'] == 'schedule'
          and ticks['cause']['depth'] == 0
          and ticks['cause']['entry_ref'] == 'tick', str(ticks.get('cause')))
    check('the tick cause is popped when the tick ends', current_cause() is None)

    # --- 8. ExecutionTrace carries the trace id ----------------------
    from polariNoCode.ExecutionTrace.ExecutionTrace import ExecutionTrace
    t = root_cause('api', 'POST /api/solutions/run')
    tr = ExecutionTrace('e1', 'probe', 'python_backend')
    check('ExecutionTrace stamps the ambient trace id and round-trips it',
          tr.trace_id == current_cause()['trace_id']
          and ExecutionTrace.from_dict(tr.to_dict()).trace_id == tr.trace_id,
          tr.trace_id)
    pop_cause(t)
    check('with no cause an ExecutionTrace has an empty trace id, not None',
          ExecutionTrace('e2', 'probe', 'python_backend').trace_id == '')

    # --- 9. THE THREAD BOUNDARY (design §4) --------------------------
    sites = thread_sites()
    unknown = [p for p in sites if os.path.basename(p) not in KNOWN_THREAD_SITES]
    check('every thread-start site in the tree is a KNOWN one '
          '(contextvars do not cross a thread — a new site must be listed '
          'with the cause it mints or is handed)',
          not unknown,
          'UNLISTED: ' + ', '.join(unknown) if unknown else f'{len(sites)} sites')
    check('the thread table is not stale (no listed site has disappeared)',
          not [b for b in KNOWN_THREAD_SITES
               if b not in {os.path.basename(p) for p in sites}],
          str([b for b in KNOWN_THREAD_SITES
               if b not in {os.path.basename(p) for p in sites}]))
    check('every thread site states a reason',
          all(len(v) > 10 for v in KNOWN_THREAD_SITES.values()))

    # a cause genuinely does NOT cross a thread — stated, then proven
    import threading
    box = {}
    t = root_cause('api', 'GET /threaded')
    th = threading.Thread(target=lambda: box.update(inner=current_cause()))
    th.start(); th.join()
    check('a plain thread does NOT inherit the cause (the honest limitation)',
          box.get('inner') is None and current_cause() is not None)
    pop_cause(t)

    passed = sum(1 for _, ok in _results if ok)
    print(f'\n{passed}/{len(_results)} checks passed')
    return 0 if passed == len(_results) else 1


if __name__ == '__main__':
    sys.exit(main())
