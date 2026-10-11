"""hwnocode.custom.selftest_light — ucd-light (UNO_CORE_DEMO_PLAN.md §5i): the light test's no-code side.
  * `uno-light` is a valid Cross-Domain Solution (Firmware Run -> Bridge -> Relay in -> Relay out), refuses any compute state,
    and carries no backend ledger / analysis call;
  * `light-toggle` (plain backend solution) run through the REAL engine flips led_on on the bound LightState row, both ways;
  * the run's committed change reaches the hardware Commands leg (POST /executeSolutionStepped -> notify_commands), proven with the real
    PolariGrpcServer registry and a subscribed queue (the twin leg itself — a worker holding the serial link — is proven elsewhere);
  * /display/uno-core-demo is ONE LightState table (no raw JSON, no new component) whose name column links to the row, in plain words.
Run by hwnocode_selftest.main()."""
import json
import re


def light_parts(check):
    return (lambda: _cross_domain(check), lambda: _toggle_engine(check), lambda: _commands_leg(check), lambda: _page(check),
            lambda: _seeds(check))


def _cross_domain(check):
    from hwnocode.custom import light_solutions as LS, cross_domain as CD
    d = LS.light_definition()
    ok, why = CD.validate(d)
    check('uno-light validates as a Cross-Domain Solution (bridging/relay states only)', ok, why)
    names = [s['stateName'] for s in d['stateInstances']]
    check('uno-light = Firmware Run -> Bridge -> Relay in -> Relay out, in that order, and nothing else', names == ['firmware-run', 'uno-light-bridge', 'relay-in', 'relay-out'], names)
    kinds = {s['stateClass'] for s in d['stateInstances']}
    check('no backend ledger, no analysis call, no sub-solution, no frontend emit in uno-light', not (kinds & {'SolutionInvocation', 'AnalysisCall', 'EmitFrontendEvent'}), kinds)
    bad = json.loads(json.dumps(d))
    bad['stateInstances'].append({'stateName': 'sneaky-math', 'stateClass': 'ConditionalChain', 'slots': []})
    ok2, why2 = CD.validate(bad)
    check('the validator REFUSES a compute state added to uno-light, naming it', not ok2 and 'sneaky-math' in why2, why2)
    ok3, _ = CD.validate(LS.toggle_definition())
    check('light-toggle (compute: a ConditionalChain) is NOT a cross-domain canvas — it is the plain backend solution the screen\'s button runs', not ok3)
    fr = next(s for s in d['stateInstances'] if s['stateName'] == 'firmware-run')['boundObjectFieldValues']
    check('Firmware Run names the Firmware Solution uno-light; every state carries a detail_ref',
          fr['firmware_solution'] == 'uno-light' and all((s['boundObjectFieldValues'].get('detail_ref') or {}).get('class') for s in d['stateInstances']))
    from hwnocode.custom import seed_rows as SR
    rows = {r['name']: r for r in SR.solution_definitions()}
    check('seeded: uno-light is category cross-domain, light-toggle category "" (plain backend)',
          rows['uno-light']['category'] == 'cross-domain' and rows['light-toggle']['category'] == '')
    b = next(x for x in SR.BINDINGS if x['name'] == LS.LIGHT_BINDING)
    check('the HardwareInterfaceBinding uno-light/LightState/0 binds the LightState row uno-light on bridge uno-light, its own twin link',
          b['object_class'] == 'LightState' and b['object_name'] == 'uno-light' and b['bridge_name'] == 'uno-light' and b['instance_index'] == 0
          and (b['port'].endswith('uno-light-twin-uart') or b['interface_kind'] == 'serial'), b)


def _mgr():
    from types import SimpleNamespace
    from board.board_basis import LightState
    mgr = SimpleNamespace(objectTables={'AnalysisDefinition': {}, 'SolutionDefinition': {}}, objectTypingDict={}, db=None, idList=[])
    row = LightState(manager=mgr, name='uno-light', led_on=False, toggles=0, source='', status='idle')
    mgr.objectTables['LightState'] = {row.id: row}
    return mgr, row


def _toggle_engine(check):
    from hwnocode.custom import light_solutions as LS
    from polariNoCode.graph_builder import execute
    from polariNoCode.graph_compilers import final_context_of
    mgr, row = _mgr()
    d = LS.toggle_definition()
    seen = []
    for current in (False, True, False):
        tr = execute(d, manager=mgr, params={'object': 'uno-light', 'led_on': current})
        seen.append((tr.status, bool(row.led_on)))
    check('light-toggle through the REAL engine flips led_on on the LightState row: off->on, on->off, off->on', seen == [('completed', True), ('completed', False), ('completed', True)], seen)
    committed = final_context_of(tr).get('_committed_changes') or []
    check('the run records ONE committed change: LightState uno-light, led_on', len(committed) == 1 and committed[0]['className'] == 'LightState'
          and committed[0]['instance'] == 'uno-light' and set(committed[0]['fields']) == {'led_on'}, committed)
    tr2 = execute(d, manager=mgr, params={'object': 'uno-light'})
    check('run without a current value reads the light as off and turns it on (never a crash)', tr2.status == 'completed' and row.led_on is True, (tr2.status, row.led_on))
    tr3 = execute(d, manager=mgr, params={'object': 'no-such-light', 'led_on': False})
    check('a run naming a row that does not exist errors, named (never a silent pass)', tr3.status == 'errored' and 'no-such-light' in (tr3.error_summary or ''), tr3.error_summary)


def _commands_leg(check):
    import queue
    from types import SimpleNamespace
    import falcon
    from falcon import testing
    from grpcbridge.custom import grpc_server as GS
    from polariApiServer.solutionExecutionAPI import SolutionExecutionAPI
    from polariApiServer.solutionDefinition import SolutionDefinition
    from hwnocode.custom import light_solutions as LS
    mgr, row = _mgr()
    for r in LS.definition_rows():
        sd = SolutionDefinition(manager=mgr, **r)
        mgr.objectTables.setdefault('SolutionDefinition', {})[sd.id] = sd
    srv = GS.PolariGrpcServer(mgr)
    srv.runtime = SimpleNamespace(field_maps={'LightState': {}}, instance_to_message=lambda cls, inst: {'name': inst.name, 'led_on': inst.led_on},
                                  overlay_values=lambda cls, msg, vals: msg.update(vals))
    q = queue.Queue()
    srv._subscribe(srv._command_watchers, 'LightState', q)
    prev = GS.get_grpc_server()
    GS.set_grpc_server(srv)
    try:
        app = falcon.App()
        SolutionExecutionAPI(polServer=SimpleNamespace(falconServer=app, manager=mgr), manager=mgr)
        c = testing.TestClient(app)
        r = c.simulate_post('/executeSolutionStepped', json={'solutionName': 'light-toggle', 'inputParams': {'object': 'uno-light', 'led_on': False}})
        ok = r.status_code == 200 and r.json.get('success') and r.json['trace']['status'] == 'completed'
        sent = r.json['displaySummary'].get('commandsRelayed') if ok else None
        msg = q.get_nowait() if not q.empty() else None
        check('running light-toggle (POST /executeSolutionStepped) writes led_on AND hands it to the Commands leg: one message to the subscribed '
              'stream carrying led_on true for uno-light', ok and row.led_on is True and sent == [{'className': 'LightState', 'instance': 'uno-light', 'sent': 1}]
              and msg == {'name': 'uno-light', 'led_on': True}, (r.status_code, sent, msg))
        GS.set_grpc_server(None)
        r = c.simulate_post('/executeSolutionStepped', json={'solutionName': 'light-toggle', 'inputParams': {'object': 'uno-light', 'led_on': True}})
        check('with no gRPC server up the run still completes (the relay is skipped, empty list) and nothing lingers in the pending commands',
              r.status_code == 200 and r.json['displaySummary'].get('commandsRelayed') == [] and row.led_on is False and not GS._PENDING_COMMANDS, r.text[:200])
    finally:
        GS.set_grpc_server(prev)


def _page(check):
    import inspect
    from hwnocode.hwnocode_page import SEED_HWNOCODE_PAGE_DISPLAYS
    from board.board_basis import LightState
    page = next(p for p in SEED_HWNOCODE_PAGE_DISPLAYS if p['name'] == 'uno-core-demo')
    items = [it for row in json.loads(page['definition'])['rows'] for it in row['items']]
    check('/display/uno-core-demo = ONE class-rows-table over LightState (no raw JSON, no chart, no new component)',
          len(items) == 1 and items[0]['componentProps']['componentName'] == 'class-rows-table'
          and items[0]['componentProps']['inputs']['className'] == 'LightState', [i['componentProps']['componentName'] for i in items])
    inp = items[0]['componentProps']['inputs']
    cols = inp['columns'].split(',')
    check('the table shows name, led_on, toggles, source, seq, boot_session, status — all real fields of LightState',
          cols == ['name', 'led_on', 'toggles', 'source', 'seq', 'boot_session', 'status'] and set(cols) <= set(inspect.signature(LightState.__init__).parameters), cols)
    check('the name column links to the row\'s own page (ref:LightState)', inp['columnFormats'] == 'name:ref:LightState', inp['columnFormats'])
    text = page['description'] + ' ' + items[0]['description']
    check('the description says how to switch the light from the screen (light-toggle / led_on) and how the board\'s button shows up (source ... button)',
          'light-toggle' in text and 'led_on' in text and 'source' in text and 'button' in text)
    leaks = re.findall(r'\.md\b|his ruling|ucd-|D-ucd|hn-\d|fs-\d|`', text)
    check('…in plain words: no plan file names, rulings, slice codes or backtick verbs in the page or table text', not leaks, leaks)
    from uno_core_demo.uno_core_demo_page import SEED_UNO_CORE_DEMO_PAGE_DISPLAYS
    ritems = [it for row in json.loads(SEED_UNO_CORE_DEMO_PAGE_DISPLAYS[0]['definition'])['rows'] for it in row['items']]
    rtext = SEED_UNO_CORE_DEMO_PAGE_DISPLAYS[0]['description'] + ' ' + ritems[0]['description']
    check('the readiness table stays on its own page (uno-core-demo-readiness), also in plain words', SEED_UNO_CORE_DEMO_PAGE_DISPLAYS[0]['pageRoute'] == 'uno-core-demo-readiness'
          and not re.findall(r'\.md\b|his ruling|ucd-|D-ucd|`', rtext), re.findall(r'\.md\b|his ruling|ucd-|D-ucd|`', rtext))


def _seeds(check):
    from cmod.custom import capabilities as CAP
    for name, state in (('light-toggle', 'flip'), ('uno-light', 'relay-in'), ('uno-light', 'relay-out')):
        ok, why = CAP._state_task_exists('%s:%s' % (name, state))
        check('the Purposes can name %s:%s (it resolves through the seed definitions)' % (name, state), ok, why)
