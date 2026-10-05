"""hwnocode_selftest — hn-0 (HARDWARE_NOCODE_PLAN.md §7): the placement rule on the seeded split app (every node placed, the
hw-interface the only bridge node) and its REFUSALS (a Python node wired on the device side, a device→backend edge without a
hw-interface, a Python node inside the referenced CGraph); the subgraph REFERENCE (cmod's rows untouched, hn-split's board half =
cmod-glue's output = cmod-1's committed record; the GraphCompilerDefinition seam); the firmware_runtime knob's refusals; the
runtime suggestion's evidence rows on fixtures (rule 1 on the UNO, rule 2 on a radio board, rule 3 on a two-period graph with a
blocking atom) and that it never applies anything; the backend half run through the REAL engine on a fake manager (the moving
average, the threshold flag, the ring); the node kinds' palette metadata through /stateSpaceClasses; seeds, page, API;
`manifests conform hwnocode`. No engine runs here (the twin proof is tests/hwnocode_probe.py).

    PYTHONPATH=.:modules python3 -m hwnocode.hwnocode_selftest      # from polari-framework/
"""
import copy
import json
import sys

passed = total = 0


def check(label, cond, extra=''):
    global passed, total
    total += 1
    passed += bool(cond)
    print('  [%s] %s %s' % ('\033[0;32mPASS\033[0m' if cond else '\033[0;31mFAIL\033[0m', label, extra if not cond else ''))


def _parts():
    from hwnocode.custom import split as SP
    return SP.solution_rows('uno-temp-split')


def _state(defn, name):
    return next(s for s in defn['stateInstances'] if s['stateName'] == name)


def placement_on_seed():
    from hwnocode.custom import placement as PL
    from hwnocode.custom import split as SP
    r = SP.place_solution('uno-temp-split')
    check('uno-temp-split placed: twin 19 (the HardwareSubgraph + its 18 CGraph nodes), bridge 1, backend 6, browser 1 — no refusal',
          r['counts'] == {'twin': 19, 'bridge': 1, 'backend': 6, 'browser': 1} and not r['refusals'], (r['counts'], r['refusals']))
    check('every node carries a placement from the rule\'s set and a why', all(n['placement'] in PL.PLACEMENTS and n['why'] for n in r['nodes']))
    br = [n for n in r['nodes'] if n['placement'] == 'bridge']
    check('the ONLY bridge node is the hw-interface `uno-twin` (binding uno-temp-split/SimRigState/0) — the split point',
          [(n['node'], n['kind']) for n in br] == [('uno-twin', 'hw-interface')] and 'uno-temp-split/SimRigState/0' in br[0]['why'])
    check('the device is the TWIN (no BoardInstance attached: twin:arduino-uno-r3#0) and every subgraph node is C',
          r['target'] == 'twin' and all(n['language'] == 'C' for n in r['nodes'] if n['layer'] == 'subgraph'))
    check('the backend nodes are the engine\'s existing kinds, in Python: BackendStateChange, AnalysisCall, ConditionalChain, '
          'VariableAssignment ×2, StateChangeCommit',
          sorted(n['kind'] for n in r['nodes'] if n['placement'] == 'backend') == sorted(
              ['BackendStateChange', 'AnalysisCall', 'ConditionalChain', 'VariableAssignment', 'VariableAssignment', 'StateChangeCommit']))
    check('the device side (what the split cuts off) = the HardwareSubgraph node alone', r['device_side'] == ['sim-rig'], r['device_side'])


def runtimes_demo_4b():
    """demo-4b (his ruling): 6 Runtime rows, described; every placed node of uno-temp-split resolves to one of them."""
    from hwnocode.custom import runtimes as RT
    from hwnocode.custom import split as SP
    check('6 Runtime rows seeded, each described (his ruling: C-hardware + Java/JavaFX native-bridge back/front are their own '
          'runtimes)', len(RT.RUNTIME_ROWS) == 6 and {r['name'] for r in RT.RUNTIME_ROWS} == {
              'python-backend', 'typescript-browser', 'c-device', 'c-twin', 'java-bridge', 'javafx-native'}
          and all(r.get('description') for r in RT.RUNTIME_ROWS))
    r = SP.place_solution('uno-temp-split')
    missing = [n for n in r['nodes'] if not n['refused'] and not n.get('runtime')]
    check('every non-refused node of uno-temp-split carries a runtime (c-device/java-bridge/python-backend)', not missing, missing)
    by_kind = {n['kind']: n['runtime'] for n in r['nodes']}
    check('c-atom/hardware-subgraph -> c-device; hw-interface -> java-bridge; the backend chain -> python-backend',
          by_kind.get('hardware-subgraph') == 'c-device' and by_kind.get('hw-interface') == 'java-bridge'
          and by_kind.get('BackendStateChange') == 'python-backend', by_kind)
    sub_runtimes = {n['runtime'] for n in r['nodes'] if n['layer'] == 'subgraph'}
    check('every CGraph node inside the subgraph (c-atom + the glue kinds) resolves to c-device', sub_runtimes == {'c-device'}, sub_runtimes)


def refusals():
    from hwnocode.custom import placement as PL
    from hwnocode.custom import split as SP
    from polariNoCode import graph_builder as GB
    p = _parts()
    # 1. a Python node dropped on the board side: sim-rig → smooth (AnalysisCall) → uno-twin
    d = copy.deepcopy(p['definition'])
    GB.wire(_state(d, 'sim-rig'), 0, 'smooth-on-board')
    d['stateInstances'].append(GB.node('smooth-on-board', 'AnalysisCall', {'analysis': 'hwnocode-temp-derive'}, outs=[['uno-twin']]))
    r = PL.place(d, p['cgraph'], 'twin:arduino-uno-r3#0')
    msg = ' '.join(r['refusals'])
    check('a Python node (AnalysisCall) wired on the DEVICE side is REFUSED naming it and RULE 2, with the alternative (move it across '
          'the hw-interface)', 'smooth-on-board' in msg and 'RULE 2' in msg and 'move it across the hw-interface' in msg
          and any(n['node'] == 'smooth-on-board' and n['refused'] for n in r['nodes']), msg[:300])
    check('…and rule 3 names the crossing edge (sim-rig → smooth-on-board, no hw-interface on it)',
          'edge sim-rig → smooth-on-board crosses board ⇄ backend without a hw-interface' in msg)
    try:
        SP.compile_parts(dict(p, definition=d))
        check('hn-split refuses to compile it', False)
    except SP.SplitRefused as e:
        check('hn-split refuses to compile it (SplitRefused, the same words)', 'smooth-on-board' in str(e))
    # 2. the hw-interface removed: sim-rig wired straight to the BackendStateChange
    d2 = copy.deepcopy(p['definition'])
    GB.wire(_state(d2, 'sim-rig'), 0, 'on-temp')
    d2['stateInstances'] = [s for s in d2['stateInstances'] if s['stateName'] != 'uno-twin']
    r2 = PL.place(d2, p['cgraph'], 'twin:arduino-uno-r3#0')
    m2 = ' '.join(r2['refusals'])
    check('no hw-interface on the crossing: edge sim-rig → on-temp refused (rule 3) and the whole backend chain lands on the device side',
          'edge sim-rig → on-temp crosses board ⇄ backend' in m2 and {'on-temp', 'moving-avg', 'commit'} <= set(r2['device_side']), m2[:200])
    # 3. a Python node INSIDE the referenced CGraph
    cg = copy.deepcopy(p['cgraph'])
    cg['nodes'].append({'name': 'uno-sim-rig-graph:smooth', 'graph': cg['graph']['name'], 'instance': 'smooth', 'kind': 'AnalysisCall',
                        'atom': 'hwnocode.custom.derive:temp_derive', 'stage': 'loop', 'order': 30, 'bindings': '', 'params': ''})
    r3 = PL.place(p['definition'], cg, 'twin:arduino-uno-r3#0')
    m3 = ' '.join(r3['refusals'])
    check('a Python node inside the CGraph (kind AnalysisCall) is refused ON THE BOARD, named, RULE 2',
          "node 'smooth' (kind AnalysisCall) is a Python/engine node on the BOARD" in m3 and 'RULE 2' in m3, m3[:200])
    # 4. a loose c-atom on the solution canvas
    d4 = copy.deepcopy(p['definition'])
    d4['stateInstances'].append(GB.node('blink', 'CAtom', {'atom': 'uno:hal.hal_led'}, outs=[[]]))
    GB.wire(_state(d4, 'sim-rig'), 0, 'uno-twin', 'blink')
    r4 = PL.place(d4, p['cgraph'], 'twin:arduino-uno-r3#0')
    try:
        SP.compile_parts(dict(p, definition=d4))
        check('a loose c-atom is refused at render', False)
    except SP.SplitRefused as e:
        check('a loose c-atom on the canvas is PLACED on the device (C, twin) but refused at render: in hn-0 a c-atom renders only '
              'inside a HardwareSubgraph', any(n['node'] == 'blink' and n['placement'] == 'twin' for n in r4['nodes'])
              and 'blink' in str(e) and 'inside a HardwareSubgraph' in str(e), str(e)[:200])


def subgraph_reference():
    from cmod.custom import glue as GL
    from cmod.custom import graph as GR
    from cmod.custom.graph_seed import seed_graph
    from hwnocode.custom import split as SP
    from polariNoCode.graph_compilers import SEED_GRAPH_COMPILERS, GraphCompilerDefinition, compile_with
    p = _parts()
    hs = p['solution']
    sub = _state(p['definition'], 'sim-rig')
    rec = GL.load_record('uno-sim-rig-graph')
    check('D-hn-1: the HardwareSubgraph node REFERENCES CGraph uno-sim-rig-graph (= HardwareSolution.cgraph); the cmod rows are cmod\'s '
          'seeds, unchanged (graph sha = cmod-1\'s record)', sub['boundObjectFieldValues']['cgraph'] == hs['cgraph'] == 'uno-sim-rig-graph'
          and GR.graph_sha(seed_graph('uno-sim-rig-graph')) == rec['graph_sha256'])
    r = SP.compile_parts(p)
    pv = r['provenance']
    check('hn-split\'s board half = cmod-glue\'s output: files_sha256 %s… = cmod-1\'s committed record (every file\'s sha equal)'
          % pv['glue_files_sha256'][:12], pv['glue_files_sha256'] == rec['files_sha256'] and pv['glue_files'] == rec['files'])
    check('the backend half = the 6 backend states, no connector to a hardware node, stamped compiledBy hn-split',
          [s['stateName'] for s in r['definition']['stateInstances']] == ['on-temp', 'moving-avg', 'over?', 'flag-on', 'flag-off', 'commit']
          and all(c['targetStateName'] in {'moving-avg', 'over?', 'flag-on', 'flag-off', 'commit'}
                  for s in r['definition']['stateInstances'] for sl in s['slots'] for c in sl['connectors'])
          and r['definition']['compiledBy']['compiler'] == 'hn-split')
    row = next(x for x in SEED_GRAPH_COMPILERS if x['name'] == 'hn-split')
    g = GraphCompilerDefinition(**row)
    out = compile_with(g, {'HardwareSolution': [hs], 'SolutionDefinition': [{'definition': json.dumps(p['definition'])}],
                           'CGraph': [p['cgraph']['graph']], 'CGraphNode': p['cgraph']['nodes'], 'CGraphEdge': p['cgraph']['edges']})
    check('the GraphCompilerDefinition row `hn-split` (domain hwnocode) compiles through compile_with: artifacts = cmod-glue\'s, the '
          'definition = the backend half', out['provenance']['glue_files_sha256'] == rec['files_sha256']
          and out['definition']['solutionName'] == 'uno-temp-split.backend' and len(out['artifacts']) == 7)
    st = json.load(open(SP.record_path('uno-temp-split'))) if SP.load_record('uno-temp-split') else {}
    check('the committed split record names the same split sha and says the board half equals cmod-1\'s record',
          st.get('split_sha256') == pv['split_sha256'] and (st.get('board_half') or {}).get('equal_to_cmod_record') is True,
          (st.get('split_sha256', '')[:12], pv['split_sha256'][:12]))


def knob_refusals():
    from hwnocode.custom import knobs as K
    from hwnocode.custom import split as SP
    p = _parts()
    uno = p['board']
    ok, why = K.check_runtime('bare-c', uno)
    check('firmware_runtime bare-c accepted on the UNO (cmod-glue\'s target)', ok and 'cmod-glue' in why)
    ok, why = K.check_runtime('auto', uno)
    check('auto REFUSED — D-hn-3: suggest only, the person picks', not ok and 'D-hn-3' in why and 'SUGGEST ONLY' in why)
    for rt in ('freertos', 'esp-idf', 'zephyr'):
        ok, why = K.check_runtime(rt, uno)
        check('%s REFUSED on the UNO for the RAM (S class, 32 KB / 2 KB)' % rt, not ok and 'S-class' in why and '2 KB' in why, why)
    m_board = {'name': 'esp32-c3', 'device_class': 'MCU-M', 'ram_kb': 400}
    ok, why = K.check_runtime('zephyr', m_board)
    check('zephyr on an M-class board REFUSED as not-yet-a-graph-target (hn-5, the C3 first — D-hn-5)', not ok and 'hn-5' in why and 'D-hn-5' in why)
    ok, why = K.check_runtime('rtos-x', uno)
    check('an unknown value REFUSED, the values listed', not ok and 'bare-c | freertos | esp-idf | zephyr' in why)
    q = copy.deepcopy(p)
    q['solution']['firmware_runtime'] = 'freertos'
    try:
        SP.compile_parts(q)
        check('hn-split refuses a non-bare-c knob', False)
    except SP.SplitRefused as e:
        check('hn-split refuses the solution while the knob says freertos (the reason, not a silent fallback)', 'freertos' in str(e))


def suggestion_fixtures():
    from hwnocode.custom import suggest as SG
    p = _parts()
    r = SG.suggest('uno-temp-split', parts=p)
    ev = [e for ru in r['rules'] if ru['rule'] == 1 for e in ru['evidence']]
    check('UNO: suggested bare-c by rule 1 (memory class S); evidence = the BoardDefinition row + the CGlueBuild\'s measured flash/RAM',
          r['suggested'] == 'bare-c' and r['decisive_rule'] == 1 and any(e.startswith('BoardDefinition arduino-uno-r3') and 'ram_kb 2' in e for e in ev)
          and any(e.startswith('CGlueBuild uno-sim-rig-graph@926ae056472c') and '4310 B' in e and '491 B' in e for e in ev), ev)
    f = r['features']
    check('features: 1 main loop / 1 tick / no independent periods; blocking atoms read from the annotation (hal_adc_read in the tick); '
          'no radio; nothing shared across priorities', f['activities']['concurrent_activities'] == 1 and f['radios'] == ''
          and any(b['atom'] == 'hal.hal_adc_read' and b['scope'].startswith('tick') for b in f['blocking']) and not f['shared_across_priorities'])
    check('rule 4 holds too, citing the bare-C pairs (S2 lost-ack-hang, sc-0 torn-millis-read) and the FormalCheck',
          any(ru['rule'] == 4 and ru['holds'] and any('lost-ack-hang' in e for e in ru['evidence']) for ru in r['rules']))
    check('SUGGEST ONLY: applied = false, the knob untouched, the policy said', r['applied'] is False and r['knob']['firmware_runtime'] == 'bare-c'
          and 'D-hn-3' in r['policy'] and p['solution']['firmware_runtime'] == 'bare-c')
    q = copy.deepcopy(p)
    q['board'] = {'name': 'esp32-c3', 'device_class': 'MCU-M', 'ram_kb': 400, 'flash_kb': 4096, 'radios': 'Wi-Fi 4, BLE 5'}
    r2 = SG.suggest('uno-temp-split', parts=q)
    check('fixture: an M-class board with Wi-Fi/BLE → rule 2 (radio) decides → esp-idf, the radios column as evidence',
          r2['decisive_rule'] == 2 and r2['suggested'] == 'esp-idf' and any('radios Wi-Fi 4, BLE 5' in e for ru in r2['rules'] if ru['rule'] == 2
                                                                              for e in ru['evidence']), (r2['decisive_rule'], r2['suggested']))
    q3 = copy.deepcopy(q)
    q3['board']['radios'] = 'none'
    q3['cgraph']['nodes'].append({'instance': 'slow', 'kind': 'tick', 'order': 40, 'params': 'period_ms=1000', 'atom': '', 'stage': ''})
    r3 = SG.suggest('uno-temp-split', parts=q3)
    check('fixture: M class, no radio, TWO periods + a blocking atom → rule 3 → freertos, with the priority-inversion + deadlock pairs as '
          'evidence', r3['decisive_rule'] == 3 and r3['suggested'] == 'freertos'
          and any('priority-inversion-mutex' in e for ru in r3['rules'] if ru['rule'] == 3 for e in ru['evidence']), (r3['decisive_rule'], r3['suggested']))


def backend_half_in_engine():
    """The backend half through the REAL engine (graph_builder.execute) on a fake manager — the moving average, the flag, the ring."""
    from types import SimpleNamespace
    from hwnocode.custom import split as SP
    from polariNoCode.graph_builder import execute
    from polariNoCode.graph_compilers import final_context_of
    backend = SP.compile_parts(_parts())['definition']
    mgr = SimpleNamespace(objectTables={'AnalysisDefinition': {}}, objectTypingDict={}, db=None, idList=[])
    from polariNoCode.analysis_calls import AnalysisDefinition
    from hwnocode.custom.seed_rows import ANALYSES
    a = AnalysisDefinition(manager=mgr, **ANALYSES[0])
    mgr.objectTables['AnalysisDefinition'] = {a.id: a}
    temps = [24.0, 24.0, 24.5, 25.0, 26.0, 27.0, 27.0, 23.0]
    flags, avgs, statuses = [], [], []
    for i, t in enumerate(temps):
        params = {'instance.name': 'uno-twin', 'instance.temp_c': t, 'instance.uptime_ms': 100 * i, 'window': 3, 'threshold_c': 25.0, 'keep': 4}
        tr = execute(backend, manager=mgr, params=params)
        statuses.append(tr.status)
        d = next(iter(mgr.objectTables['SimRigTempDerived'].values()))
        flags.append(bool(d.over_threshold))
        avgs.append(round(d.temp_avg, 4))
    want = [24.0, 24.0, round((24 + 24 + 24.5) / 3, 4), round((24 + 24.5 + 25) / 3, 4), round((24.5 + 25 + 26) / 3, 4), 26.0,
            round((26 + 27 + 27) / 3, 4), round((27 + 27 + 23) / 3, 4)]
    check('8 frames through the engine: every run completed; SimRigTempDerived.temp_avg = the 3-sample moving average %s' % avgs,
          all(s == 'completed' for s in statuses) and avgs == want, (statuses, avgs, want))
    check('the flag is the ConditionalChain\'s verdict (avg > 25.0) persisted by StateChangeCommit: %s' % flags,
          flags == [a2 > 25.0 for a2 in want], flags)
    ring = mgr.objectTables['SimRigTempSample']
    check('the ring keeps `keep`=4 sample rows (slots 0..3, the oldest overwritten), seq up to 7, the cursor samples = 8',
          len(ring) == 4 and max(r.seq for r in ring.values()) == 7 and next(iter(mgr.objectTables['SimRigTempDerived'].values())).samples == 8,
          (len(ring), sorted(r.seq for r in ring.values())))
    from hwnocode.custom.derive import chart_rows
    rows = chart_rows(mgr, 'uno-twin')
    check('the chart rows = the ring oldest first (seq 4..7) with uptime_s, temp_c, temp_avg', [r['seq'] for r in rows] == [4, 5, 6, 7]
          and set(rows[0]) >= {'uptime_s', 'temp_c', 'temp_avg'}, rows[:1])
    fc = final_context_of(tr)
    check('the run\'s context holds temp_avg (the AnalysisCall\'s pick) and over_threshold (the VariableAssignment)',
          round(fc.get('temp_avg', 0), 4) == want[-1] and fc.get('over_threshold') is True)


def palette_metadata():
    from types import SimpleNamespace
    from hwnocode.hwnocode_basis import NODE_KIND_CLASSES
    from hwnocode.hwnocode_endpoints import enable_node_kinds
    from polariDataTyping.polyTyping import polyTypedObject
    kinds = {c.__name__: c.statePalette for c in NODE_KIND_CLASSES}
    check('three node kinds carry palette metadata: HardwareSubgraph (hardware-subgraph), HardwareInterface (hw-interface), CAtom (c-atom); '
          'category Hardware; overlay c-atom / hw-interface', {k: v['nodeKind'] for k, v in kinds.items()}
          == {'HardwareSubgraph': 'hardware-subgraph', 'HardwareInterface': 'hw-interface', 'CAtom': 'c-atom'}
          and {v['category'] for v in kinds.values()} == {'Hardware'} and {v['overlay'] for v in kinds.values()} == {'c-atom', 'hw-interface'})
    check('every palette entry declares its slots and variables (what the canvas needs to create the node)',
          all(isinstance(v.get('slots'), dict) and v.get('variables') and v.get('displayName') for v in kinds.values()))

    class T:
        def __init__(self, cls):
            self.className, self.classDefinition = cls.__name__, cls
            self.isStateSpaceObject, self.stateSpaceEventMethods = False, []
            self.stateSpaceDisplayFields, self.stateSpaceFieldLayout, self.stateSpaceFieldsPerRow = [], {}, 1
            self.polyTypedVars, self.variableNameList = [], ['name']
        setStateSpaceDisplayFields = polyTypedObject.setStateSpaceDisplayFields
        getStateSpaceConfig = polyTypedObject.getStateSpaceConfig
    mgr = SimpleNamespace(objectTypingDict={c.__name__: T(c) for c in NODE_KIND_CLASSES})
    done = enable_node_kinds(mgr)
    cfgs = [t.getStateSpaceConfig() for t in mgr.objectTypingDict.values()]
    check('the endpoint constructor marks the node-kind typings state-space; getStateSpaceConfig carries `palette` (what GET '
          '/stateSpaceClasses returns)', sorted(done) == ['CAtom', 'HardwareInterface', 'HardwareSubgraph']
          and all(c['isStateSpaceObject'] and c['palette']['nodeKind'] for c in cfgs))

    class Plain:
        pass
    t = T(Plain)
    check('a class with no statePalette → its config is unchanged (no `palette` key) — the old kinds are untouched',
          'palette' not in t.getStateSpaceConfig())


def seeds_page_api():
    import inspect
    from types import SimpleNamespace
    import falcon
    from falcon import testing
    from hwnocode.hwnocode_seed import HWNOCODE_SEED_PAIRS
    from hwnocode.hwnocode_page import SEED_HWNOCODE_PAGE_DISPLAYS, SEED_HWNOCODE_GRAPHS
    from hwnocode.hwnocode_api import HwNoCodeAPI
    counts = {n: len(r) for n, _c, r in HWNOCODE_SEED_PAIRS}
    check('seeds: 1 HardwareSolution, 27 placements, 2 SolutionDefinitions (the canvas + its backend half), 1 AnalysisDefinition, '
          '1 EventTrigger, 1 HardwareInterfaceBinding, 1 GraphDefinition, 6 Runtimes (demo-4b)', counts == {
              'HardwareSolution': 1, 'HardwareNodePlacement': 27, 'SolutionDefinition': 2, 'AnalysisDefinition': 1, 'EventTrigger': 1,
              'HardwareInterfaceBinding': 1, 'GraphDefinition': 1, 'Runtime': 6}, counts)
    # selfix 2026-10-05 (prf-urgent): the live canvas showed Object `AdditionTester` + Solution
    # `uno-temp-split` with an EMPTY canvas. Root cause (his steer): the seed's states carried NO
    # canvas position/shape — graph_builder.node() deliberately emits none (shared, parity-pinned
    # DSL) — so the Angular NoCodeState constructor (no fallback) landed every one at NaN. Every
    # seeded canvas SolutionDefinition's states must carry a real position from here on.
    sol_defs = [r for n, _c, rows in HWNOCODE_SEED_PAIRS if n == 'SolutionDefinition' for r in rows]
    no_position = []
    for row in sol_defs:
        d = json.loads(row['definition'])
        for s in d.get('stateInstances') or []:
            if s.get('stateLocationX') is None or s.get('stateLocationY') is None or not s.get('shapeType'):
                no_position.append('%s:%s' % (d['solutionName'], s.get('stateName')))
    check('every state of every seeded canvas SolutionDefinition (the whole solution + its backend '
          'half) carries a real stateLocationX/Y + shapeType — never left for the canvas to land at NaN',
          not no_position, no_position)

    trig = [r for n, _c, rows in HWNOCODE_SEED_PAIRS if n == 'EventTrigger' for r in rows][0]
    check('the trigger runs the BACKEND half on SimRigState uno-twin updates; its knobs (window, threshold_c, keep) on inputs_json stay '
          'the instance\'s', trig['solution_name'] == 'uno-temp-split.backend' and json.loads(trig['source_json'])['fieldFilter'] == {'name': 'uno-twin'}
          and 'inputs_json' not in trig['_converge'])
    hs = [r for n, _c, rows in HWNOCODE_SEED_PAIRS if n == 'HardwareSolution' for r in rows][0]
    check('firmware_runtime is NOT converged by a re-seed (the person\'s knob)', 'firmware_runtime' not in hs['_converge'])
    page = SEED_HWNOCODE_PAGE_DISPLAYS[0]
    items = [it for row in json.loads(page['definition'])['rows'] for it in row['items']]
    comps = [it['componentProps']['componentName'] for it in items]
    check('/display/hardware-solutions = the canvas FIRST (demo-4b: opened on the whole solution, every runtime a lane) + 4 '
          'configured tables (solutions, derived, placement-by-runtime, the Runtime catalog) + 1 named-graph-panel',
          page['pageRoute'] == 'hardware-solutions' and items[0]['componentProps']['componentName'] == 'c-graph-canvas-panel'
          and items[0]['componentProps']['inputs'].get('solution') == 'uno-temp-split'
          and sorted(comps) == ['c-graph-canvas-panel', 'class-rows-table', 'class-rows-table', 'class-rows-table',
                                'class-rows-table', 'named-graph-panel'], comps)
    gc = json.loads(SEED_HWNOCODE_GRAPHS[0]['definition'])['graphConfig']
    check('the chart = a GraphDefinition (x uptime_s; y temp_c + temp_avg; colours set, showLegend) fed by the chart endpoint',
          gc['xDimension'] == 'uptime_s' and gc['yDimensions'] == ['temp_c', 'temp_avg'] and len(gc['seriesColors']) == 2
          and any(it['componentProps']['inputs'].get('dataPath') == '/api/hwnocode/solutions/uno-temp-split/chart' for it in items))
    from hwnocode.hwnocode_basis import HWNOCODE_CLASSES
    known = {c.__name__: c for c in HWNOCODE_CLASSES}
    bad = []
    for it in items:
        cn = it['componentProps']['inputs'].get('className')
        if cn:
            params = set(inspect.signature(known[cn].__init__).parameters)
            bad += ['%s.%s' % (cn, c) for c in it['componentProps']['inputs']['columns'].split(',') if c not in params]
    check('…every table names an hwnocode class and only columns it has', not bad, bad)
    check('/display/hardware-solutions: every item (tables + the chart) carries a non-empty description',
          all(it.get('description') for it in items), [it['id'] for it in items if not it.get('description')])
    tables = {}
    mgr = SimpleNamespace(objectTables=tables, idList=[], db=None, objectTypingDict={})
    for name, cls, rows in HWNOCODE_SEED_PAIRS:
        for r in rows:
            o = cls(manager=mgr, **{k: v for k, v in r.items() if k != '_converge'})
            tables.setdefault(name, {})[o.id] = o
    app = falcon.App()
    HwNoCodeAPI(polServer=SimpleNamespace(falconServer=app, manager=mgr, idList=[]), manager=mgr)
    c = testing.TestClient(app)
    r = c.simulate_get('/api/hwnocode')
    check('GET /api/hwnocode → uno-temp-split + the three node kinds', r.status_code == 200 and r.json['solutions'][0]['name'] == 'uno-temp-split'
          and len(r.json['node_kinds']) == 3, r.text[:200])
    r = c.simulate_get('/api/hwnocode/solutions/uno-temp-split/placement')
    check('GET …/placement → computed now: twin 19, bridge 1, backend 6, browser 1', r.status_code == 200 and r.json['summary'] == 'twin 19, bridge 1, backend 6, browser 1', r.text[:200])
    r = c.simulate_get('/api/hwnocode/solutions/uno-temp-split/render')
    check('GET …/render → the board half unchanged vs cmod-1 (in memory, nothing written)', r.status_code == 200 and r.json['board_half']['unchanged_output'], r.text[:200])
    r = c.simulate_get('/api/hwnocode/solutions/uno-temp-split/suggest')
    check('GET …/suggest → bare-c, applied false', r.status_code == 200 and r.json['suggested'] == 'bare-c' and r.json['applied'] is False)
    r = c.simulate_get('/api/hwnocode/solutions/uno-temp-split/chart')
    check('GET …/chart with no samples → ok false + a plain refusal (named-graph-panel renders it verbatim)', r.status_code == 200
          and r.json['ok'] is False and 'no samples yet' in r.json['refusal'])
    r = c.simulate_get('/api/hwnocode/interface', params={'binding': 'uno-temp-split/SimRigState/0'})
    check('GET /api/hwnocode/interface?binding=… → the binding (row uno-twin, the twin\'s pty), placement bridge', r.status_code == 200
          and r.json['binding']['object_name'] == 'uno-twin' and r.json['placement'] == 'bridge', r.text[:200])
    r = c.simulate_get('/api/hwnocode/solutions/nope')
    check('an unknown solution → 404 in plain words', r.status_code == 404 and 'no HardwareSolution' in r.json['error'])


def manifest_conform():
    from moduleService import manifests as M
    r = M.conform('hwnocode')
    check('manifests conform hwnocode: no drift', r['ok'], r['findings'])
    m = M.load('hwnocode')
    check('polari-app.json requires board, cmod, grpcbridge; engines declared honestly (make for build, the avr twin for the proof)',
          sorted(m['requires']['modules']) == ['board', 'cmod', 'grpcbridge'] and {'make', 'avr-twin'} <= {e['name'] for e in m['requires']['engines']})


def main():
    print('hwnocode selftest (hn-0)')
    for part in (placement_on_seed, runtimes_demo_4b, refusals, subgraph_reference, knob_refusals, suggestion_fixtures,
                 backend_half_in_engine, palette_metadata, seeds_page_api, manifest_conform):
        print('-- %s' % part.__name__)
        try:
            part()
        except Exception as e:  # noqa: BLE001 — a crash is a failed check, named
            import traceback
            traceback.print_exc()
            check('%s ran without raising' % part.__name__, False, '%s: %s' % (type(e).__name__, e))
    print('\n%d/%d checks passed' % (passed, total))
    return 0 if passed == total else 1


if __name__ == '__main__':
    sys.exit(main())
