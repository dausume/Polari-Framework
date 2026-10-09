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
    """fs-1 migration: uno-temp-split is now a 5-state Cross-Domain canvas (Firmware Run, Bridge, Relay in, call
    temp-analysis, Relay out) — no embedded HardwareSubgraph. The HardwareSolution row's `cgraph` field is UNCHANGED
    (it still feeds the firmware_runtime suggestion/knob machinery below, unaffected by the migration), so the 18
    uno-sim-rig-graph CGraph nodes are still expanded into the report's `subgraph` layer (unconditional on cgraph_rows,
    not on a canvas HardwareSubgraph state) — but the CANVAS itself no longer places anything on the device: the
    device_side set (what rule 3's crossing-edge check cuts off) is now EMPTY."""
    from hwnocode.custom import placement as PL
    from hwnocode.custom import split as SP
    r = SP.place_solution('uno-temp-split')
    check('uno-temp-split placed: twin 18 (uno-sim-rig-graph\'s CGraph nodes, still expanded from HardwareSolution.cgraph), '
          'bridge 2 (Firmware Run + the hw-interface), backend 3 (Relay in, call-temp-analysis, Relay out), browser 1 — no refusal',
          r['counts'] == {'twin': 18, 'bridge': 2, 'backend': 3, 'browser': 1} and not r['refusals'], (r['counts'], r['refusals']))
    check('every node carries a placement from the rule\'s set and a why', all(n['placement'] in PL.PLACEMENTS and n['why'] for n in r['nodes']))
    br = [n for n in r['nodes'] if n['placement'] == 'bridge']
    check('the bridge nodes are Firmware Run (orchestrates cmod FirmwareSolution uno-sim-rig) then the hw-interface '
          '`uno-digital-twin` (binding uno-temp-split/SimRigState/0) — the split point',
          [(n['node'], n['kind']) for n in br] == [('firmware-run', 'firmware-run'), ('uno-digital-twin', 'hw-interface')]
          and 'uno-sim-rig' in br[0]['why'] and 'uno-temp-split/SimRigState/0' in br[1]['why'], br)
    check('the device is the TWIN (no BoardInstance attached: twin:arduino-uno-r3#0) and every subgraph node is C',
          r['target'] == 'twin' and all(n['language'] == 'C' for n in r['nodes'] if n['layer'] == 'subgraph'))
    check('the backend nodes are bridging/relay only (D-fs-3): BackendStateChange (Relay in), SolutionInvocation '
          '(call temp-analysis), BackendStateChange (Relay out) — never a compute kind',
          [n['kind'] for n in r['nodes'] if n['placement'] == 'backend'] == ['BackendStateChange', 'SolutionInvocation', 'BackendStateChange'])
    check('the device side (what rule 3\'s crossing-edge check cuts off) is EMPTY — the canvas itself places nothing '
          'on the device anymore (the firmware lives in cmod\'s FirmwareSolution, named by reference only)',
          r['device_side'] == [], r['device_side'])


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
    check('hw-interface -> java-bridge; firmware-run (fs-1: orchestrates in the framework host process) -> python-backend; '
          'the backend chain -> python-backend',
          by_kind.get('hw-interface') == 'java-bridge' and by_kind.get('firmware-run') == 'python-backend'
          and by_kind.get('BackendStateChange') == 'python-backend', by_kind)
    sub_runtimes = {n['runtime'] for n in r['nodes'] if n['layer'] == 'subgraph'}
    check('every CGraph node inside the subgraph (c-atom + the glue kinds) resolves to c-device', sub_runtimes == {'c-device'}, sub_runtimes)


def refusals():
    """hn-split's device/backend placement-refusal mechanism (placement.py, unchanged code) — exercised against a
    SYNTHETIC fixture built by hand, not the live uno-temp-split: fs-1's migration retired uno-temp-split's own
    embedded HardwareSubgraph (the firmware moved to cmod's FirmwareSolution uno-sim-rig), so it is no longer a
    fitting fixture for RULE 2/3's device-side enforcement — that is still real, general-purpose code, worth proving
    on its own terms. A Cross-Domain solution's OWN compute refusal (D-fs-3) is proven separately below
    (`cross_domain_validator`), against the real uno-temp-split."""
    from hwnocode.custom import placement as PL
    from hwnocode.custom import split as SP
    from polariNoCode import graph_builder as GB
    board = {'name': 'esp32-c3', 'device_class': 'MCU-M', 'ram_kb': 400}
    cgraph = {'graph': {'name': 'fixture-graph', 'class_name': 'FixtureState'},
             'nodes': [{'instance': 'read', 'kind': 'c-atom', 'atom': 'fixture:hal.read', 'stage': 'loop', 'order': 0}], 'edges': []}
    sub = GB.node('rig', 'HardwareSubgraph', {'cgraph': 'fixture-graph', 'board_definition': 'esp32-c3'}, outs=[['bridge']])
    hwi = GB.node('bridge', 'HardwareInterface', {'binding': 'fixture/FixtureState/0'}, outs=[['entry']])
    entry = GB.node('entry', 'BackendStateChange', {'modelName': 'FixtureState', 'fieldName': 'value'}, outs=[['commit']])
    commit = GB.node('commit', 'StateChangeCommit', {'targetClassName': 'FixtureState'}, outs=[[]])
    base = GB.solution('fixture', sub, hwi, entry, commit)
    hs = {'name': 'fixture-hs', 'solution': 'fixture', 'cgraph': 'fixture-graph', 'board_definition': 'esp32-c3',
         'board_instance': 'twin:esp32-c3#0', 'displays': '', 'firmware_runtime': 'bare-c', 'backend_solution': 'fixture.backend'}
    p = {'solution': hs, 'definition': base, 'cgraph': cgraph, 'board': board}
    # 1. a Python node dropped on the board side: rig → smooth (AnalysisCall) → bridge
    d = copy.deepcopy(base)
    GB.wire(_state(d, 'rig'), 0, 'smooth-on-board')
    d['stateInstances'].append(GB.node('smooth-on-board', 'AnalysisCall', {'analysis': 'hwnocode-temp-derive'}, outs=[['bridge']]))
    r = PL.place(d, cgraph, 'twin:esp32-c3#0')
    msg = ' '.join(r['refusals'])
    check('a Python node (AnalysisCall) wired on the DEVICE side is REFUSED naming it and RULE 2, with the alternative (move it across '
          'the hw-interface)', 'smooth-on-board' in msg and 'RULE 2' in msg and 'move it across the hw-interface' in msg
          and any(n['node'] == 'smooth-on-board' and n['refused'] for n in r['nodes']), msg[:300])
    check('…and rule 3 names the crossing edge (rig → smooth-on-board, no hw-interface on it)',
          'edge rig → smooth-on-board crosses board ⇄ backend without a hw-interface' in msg)
    try:
        SP.compile_parts(dict(p, definition=d))
        check('hn-split refuses to compile it', False)
    except SP.SplitRefused as e:
        check('hn-split refuses to compile it (SplitRefused, the same words)', 'smooth-on-board' in str(e))
    # 2. the hw-interface removed: rig wired straight to the BackendStateChange
    d2 = copy.deepcopy(base)
    GB.wire(_state(d2, 'rig'), 0, 'entry')
    d2['stateInstances'] = [s for s in d2['stateInstances'] if s['stateName'] != 'bridge']
    r2 = PL.place(d2, cgraph, 'twin:esp32-c3#0')
    m2 = ' '.join(r2['refusals'])
    check('no hw-interface on the crossing: edge rig → entry refused (rule 3) and the whole backend chain lands on the device side',
          'edge rig → entry crosses board ⇄ backend' in m2 and {'entry', 'commit'} <= set(r2['device_side']), m2[:200])
    # 3. a Python node INSIDE the referenced CGraph
    cg3 = copy.deepcopy(cgraph)
    cg3['nodes'].append({'name': 'fixture-graph:smooth', 'graph': cg3['graph']['name'], 'instance': 'smooth', 'kind': 'AnalysisCall',
                         'atom': 'hwnocode.custom.derive:temp_derive', 'stage': 'loop', 'order': 30, 'bindings': '', 'params': ''})
    r3 = PL.place(base, cg3, 'twin:esp32-c3#0')
    m3 = ' '.join(r3['refusals'])
    check('a Python node inside the CGraph (kind AnalysisCall) is refused ON THE BOARD, named, RULE 2',
          "node 'smooth' (kind AnalysisCall) is a Python/engine node on the BOARD" in m3 and 'RULE 2' in m3, m3[:200])
    # 4. a loose c-atom on the solution canvas
    d4 = copy.deepcopy(base)
    d4['stateInstances'].append(GB.node('blink', 'CAtom', {'atom': 'uno:hal.hal_led'}, outs=[[]]))
    GB.wire(_state(d4, 'rig'), 0, 'bridge', 'blink')
    r4 = PL.place(d4, cgraph, 'twin:esp32-c3#0')
    try:
        SP.compile_parts(dict(p, definition=d4))
        check('a loose c-atom is refused at render', False)
    except SP.SplitRefused as e:
        check('a loose c-atom on the canvas is PLACED on the device (C, twin) but refused at render: in hn-0 a c-atom renders only '
              'inside a HardwareSubgraph', any(n['node'] == 'blink' and n['placement'] == 'twin' for n in r4['nodes'])
              and 'blink' in str(e) and 'inside a HardwareSubgraph' in str(e), str(e)[:200])


def cross_domain_validator():
    """fs-1's OWN new checks (DEMONSTRABLES_PLAN.md §9 migration): the Cross-Domain validator passes on the real,
    migrated uno-temp-split; it REFUSES the retired (pre-migration) 8-state shape — naming the first compute kind it
    finds — proving the migration actually changed what is enforced, not just what is drawn."""
    from hwnocode.custom import cross_domain as CD
    from hwnocode.custom import solutions as S
    from hwnocode.custom import temp_analysis as TA
    d = S.split_app_definition()
    ok, why = CD.validate(d)
    check('the Cross-Domain validator passes on the migrated uno-temp-split (Firmware Run, Bridge, Relay in, call '
          'temp-analysis, Relay out — bridging/relay only)', ok, why)
    kinds = {s['stateName']: s['stateClass'] for s in d['stateInstances']}
    check('uno-temp-split\'s 5 states are exactly Firmware Run / Bridge / Relay in / call-temp-analysis / Relay out',
          kinds == {'firmware-run': 'FirmwareRunState', 'uno-digital-twin': 'HardwareInterface',
                    'relay-in': 'BackendStateChange', 'call-temp-analysis': 'SolutionInvocation',
                    'relay-out': 'BackendStateChange'}, kinds)
    # the RETIRED pre-migration shape (reconstructed): the inline moving-avg/over?/flag-on/flag-off compute that used
    # to sit directly on this canvas — the validator must refuse it, naming the first compute-kind state.
    from polariNoCode import graph_builder as GB
    old = GB.solution('uno-temp-split',
                      GB.node('on-temp', 'BackendStateChange', {}, outs=[['moving-avg']]),
                      GB.node('moving-avg', 'AnalysisCall', {'analysis': TA.ANALYSIS}, outs=[['over?']]),
                      GB.cond('over?', [], 'flag-on', 'flag-off'),
                      GB.node('flag-on', 'VariableAssignment', {}, outs=[['commit']]),
                      GB.node('flag-off', 'VariableAssignment', {}, outs=[['commit']]),
                      GB.node('commit', 'StateChangeCommit', {}, outs=[[]]))
    ok2, why2 = CD.validate(old)
    check('…and REFUSES the retired pre-migration shape (inline compute) — naming the first offending state (over?, '
          'a ConditionalChain)', not ok2 and "state 'over?'" in why2 and 'ConditionalChain' in why2, why2)
    # the three seeded solutions exist, named plainly
    from hwnocode.custom import seed_rows as SR
    names = {r['name'] for r in SR.solution_definitions()}
    check('the three seeded solutions: uno-temp-split (cross-domain), uno-temp-split.backend (its derived backend '
          'half), temp-analysis (plain backend, called out to)',
          {S.SOLUTION, '%s.backend' % S.SOLUTION, TA.NAME} <= names, names)
    cats = {r['name']: r.get('category', '') for r in SR.solution_definitions()}
    check('uno-temp-split carries category=cross-domain; temp-analysis and the derived backend half do not',
          cats.get(S.SOLUTION) == 'cross-domain' and cats.get(TA.NAME, '') == '' and cats.get('%s.backend' % S.SOLUTION, '') == '', cats)
    from cmod.custom import firmware as FW
    ok3, why3, _d = FW.validate({'name': 'uno-sim-rig', 'graph': S.CGRAPH, 'board_definition': S.BOARD, 'board_variable': ''})
    check('uno-sim-rig (cmod\'s FirmwareSolution, fs-0, unchanged) still validates — the firmware itself is untouched '
          'by this migration', ok3, why3)


def subgraph_reference():
    """fs-1 migration: the HardwareSubgraph-on-this-canvas proof (D-hn-1) moved — the firmware is now cmod's OWN
    FirmwareSolution `uno-sim-rig` (fs-0, already built and tested by cmod's own selftest/selftest_firmwaresol.py),
    named by Firmware Run's `firmware_solution` field reference, never embedded on THIS canvas. hn-split still
    compiles the SAME referenced CGraph through cmod-glue for a Cross-Domain canvas (only the "exactly one
    HardwareSubgraph state on this canvas" requirement is skipped) — the board half stays byte-identical to cmod-1's
    committed record, proven below by sha equality, same as before the migration."""
    from cmod.custom import glue as GL
    from cmod.custom import graph as GR
    from cmod.custom.graph_seed import seed_graph
    from hwnocode.custom import split as SP
    from hwnocode.custom import solutions as S
    from polariNoCode.graph_compilers import SEED_GRAPH_COMPILERS, GraphCompilerDefinition, compile_with
    p = _parts()
    hs = p['solution']
    run = _state(p['definition'], 'firmware-run')
    rec = GL.load_record('uno-sim-rig-graph')
    check('Firmware Run REFERENCES cmod FirmwareSolution uno-sim-rig (fs-0, unchanged); its graph is still '
          'uno-sim-rig-graph = HardwareSolution.cgraph; the cmod rows are cmod\'s seeds, unchanged (graph sha = cmod-1\'s record)',
          run['boundObjectFieldValues']['firmware_solution'] == S.FIRMWARE_SOLUTION and hs['cgraph'] == 'uno-sim-rig-graph'
          and GR.graph_sha(seed_graph('uno-sim-rig-graph')) == rec['graph_sha256'])
    r = SP.compile_parts(p)
    pv = r['provenance']
    check('hn-split\'s board half for a Cross-Domain canvas is STILL cmod-glue\'s output: files_sha256 %s… = cmod-1\'s '
          'committed record (every file\'s sha equal — unchanged, just no longer embedded as a canvas state)'
          % pv['glue_files_sha256'][:12], pv['glue_files_sha256'] == rec['files_sha256'] and pv['glue_files'] == rec['files'])
    check('the backend half = the 3 bridging/relay-only backend states, no connector to a hardware node, stamped compiledBy hn-split',
          [s['stateName'] for s in r['definition']['stateInstances']] == ['relay-in', 'call-temp-analysis', 'relay-out']
          and all(c['targetStateName'] in {'call-temp-analysis', 'relay-out'}
                  for s in r['definition']['stateInstances'] for sl in s['slots'] for c in sl['connectors'])
          and r['definition']['compiledBy']['compiler'] == 'hn-split')
    row = next(x for x in SEED_GRAPH_COMPILERS if x['name'] == 'hn-split')
    g = GraphCompilerDefinition(**row)
    out = compile_with(g, {'HardwareSolution': [hs], 'SolutionDefinition': [{'definition': json.dumps(p['definition'])}],
                           'CGraph': [p['cgraph']['graph']], 'CGraphNode': p['cgraph']['nodes'], 'CGraphEdge': p['cgraph']['edges']})
    check('the GraphCompilerDefinition row `hn-split` (domain hwnocode) compiles through compile_with: artifacts = cmod-glue\'s '
          '(unchanged, %d files — read live from cmod-1\'s committed record, not a literal: ucd-0b added pin_config.h/.c), '
          'the definition = the backend half' % len(rec['files']), out['provenance']['glue_files_sha256'] == rec['files_sha256']
          and out['definition']['solutionName'] == 'uno-temp-split.backend' and len(out['artifacts']) == len(rec['files']))
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
    from cmod.custom import glue as GL
    from hwnocode.custom import suggest as SG
    p = _parts()
    r = SG.suggest('uno-temp-split', parts=p)
    ev = [e for ru in r['rules'] if ru['rule'] == 1 for e in ru['evidence']]
    # read cmod-1's committed glue-build record LIVE (never a literal sha/flash-size: ucd-0b's pin_config.h/.c moved both)
    crec = GL.load_record('uno-sim-rig-graph') or {}
    cbuild = crec.get('build') or {}
    glue_tag = 'CGlueBuild uno-sim-rig-graph@%s' % (crec.get('files_sha256') or '')[:12]
    flash_b = '%s B' % cbuild.get('flash_bytes', '?')
    ram_b = '%s B' % (int(cbuild.get('size_data') or 0) + int(cbuild.get('size_bss') or 0))
    check('UNO: suggested bare-c by rule 1 (memory class S); evidence = the BoardDefinition row + the CGlueBuild\'s measured flash/RAM',
          r['suggested'] == 'bare-c' and r['decisive_rule'] == 1 and any(e.startswith('BoardDefinition arduino-uno-r3') and 'ram_kb 2' in e for e in ev)
          and any(e.startswith(glue_tag) and flash_b in e and ram_b in e for e in ev), ev)
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
    """The backend half through the REAL engine (graph_builder.execute) on a fake manager — fs-1: the backend half is
    now 3 bridging states (Relay in -> call-temp-analysis -> Relay out); the moving average/flag/ring compute runs
    INSIDE the invoked `temp-analysis` solution (a nested SolutionInvocation execution, the engine's own P3 seam) —
    same math, same result, proving the migration changed WHERE the compute runs, never WHAT it computes."""
    from types import SimpleNamespace
    from hwnocode.custom import split as SP
    from hwnocode.custom import temp_analysis as TA
    from polariNoCode.graph_builder import execute
    from polariNoCode.graph_compilers import final_context_of
    backend = SP.compile_parts(_parts())['definition']
    check('the backend half invoked by the trigger is now 3 bridging states (Relay in, call-temp-analysis, Relay out)',
          [s['stateName'] for s in backend['stateInstances']] == ['relay-in', 'call-temp-analysis', 'relay-out'])
    mgr = SimpleNamespace(objectTables={'AnalysisDefinition': {}, 'SolutionDefinition': {}}, objectTypingDict={}, db=None, idList=[])
    from polariNoCode.analysis_calls import AnalysisDefinition
    from polariApiServer.solutionDefinition import SolutionDefinition
    from hwnocode.custom.seed_rows import ANALYSES
    a = AnalysisDefinition(manager=mgr, **ANALYSES[0])
    mgr.objectTables['AnalysisDefinition'] = {a.id: a}
    ta = SolutionDefinition(manager=mgr, name=TA.NAME, function_name=TA.NAME.replace('-', '_'), target_runtime='python_backend',
                            definition=json.dumps(TA.definition()), contract_json=json.dumps(TA.contract()), category='')
    mgr.objectTables['SolutionDefinition'] = {ta.id: ta}
    temps = [24.0, 24.0, 24.5, 25.0, 26.0, 27.0, 27.0, 23.0]
    flags, avgs, statuses = [], [], []
    for i, t in enumerate(temps):
        params = {'instance.name': 'uno-digital-twin', 'instance.temp_c': t, 'instance.uptime_ms': 100 * i, 'window': 3, 'threshold_c': 25.0, 'keep': 4}
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
    rows = chart_rows(mgr, 'uno-digital-twin')
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
    check('four node kinds carry palette metadata: HardwareSubgraph (hardware-subgraph), HardwareInterface (hw-interface), CAtom (c-atom), '
          'FirmwareRunState (firmware-run, fs-0/fs-2); category Hardware + Cross-Domain; overlay c-atom / hw-interface / firmware-run',
          {k: v['nodeKind'] for k, v in kinds.items()}
          == {'HardwareSubgraph': 'hardware-subgraph', 'HardwareInterface': 'hw-interface', 'CAtom': 'c-atom', 'FirmwareRunState': 'firmware-run'}
          and {v['category'] for v in kinds.values()} == {'Hardware', 'Cross-Domain'}
          and {v['overlay'] for v in kinds.values()} == {'c-atom', 'hw-interface', 'firmware-run'})
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
          '/stateSpaceClasses returns)', sorted(done) == ['CAtom', 'FirmwareRunState', 'HardwareInterface', 'HardwareSubgraph']
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
    check('seeds (fs-1 migration + ucd-1): 2 HardwareSolutions (uno-temp-split + uno-button-clock — the latter\'s own '
          'Firmware Run is backed by uno-button-clock-graph since 0e2b, so it contributes its own placements), 58 placements '
          '(uno-temp-split\'s 24 = 18 twin + 2 bridge + 3 backend + 1 browser, + uno-button-clock\'s), 6 SolutionDefinitions (uno-temp-split\'s '
          'canvas + its derived backend half + temp-analysis + uno-button-clock\'s canvas + button-clock-ledger + its '
          'own hand-built backend half + the 0e2b button-clock graph\'s own), 2 AnalysisDefinitions, 2 EventTriggers, 2 HardwareInterfaceBindings, '
          '2 GraphDefinitions, 6 Runtimes (demo-4b)', counts == {
              'HardwareSolution': 2, 'HardwareNodePlacement': 58, 'SolutionDefinition': 7, 'AnalysisDefinition': 2, 'EventTrigger': 2,
              'HardwareInterfaceBinding': 2, 'GraphDefinition': 2, 'Runtime': 6}, counts)
    # selfix 2026-10-05 (prf-urgent): the live canvas showed Object `AdditionTester` + Solution
    # `uno-temp-split` with an EMPTY canvas. Root cause (his steer): the seed's states carried NO
    # canvas position/shape — graph_builder.node() deliberately emits none (shared, parity-pinned
    # DSL) — so the Angular NoCodeState constructor (no fallback) landed every one at NaN. Every
    # seeded canvas SolutionDefinition's states must carry a real position from here on.
    sol_defs = [r for n, _c, rows in HWNOCODE_SEED_PAIRS if n == 'SolutionDefinition' for r in rows]
    no_position = []
    no_render_fields = []
    for row in sol_defs:
        d = json.loads(row['definition'])
        for s in d.get('stateInstances') or []:
            tag = '%s:%s' % (d['solutionName'], s.get('stateName'))
            if s.get('stateLocationX') is None or s.get('stateLocationY') is None or not s.get('shapeType'):
                no_position.append(tag)
            # selfix round 3 (2026-10-05): a position + shapeType alone is NOT enough — his
            # evidence from the live canvas: 7 of 8 uno-temp-split states drew as a bare 20×20
            # stub (RectangleStateLayer.ts falls back to stateSvgWidth ?? stateSvgRadius ?? 20;
            # the first pass set stateSvgSizeX/Y, a field that layer never reads). Every rendered
            # shape needs: a real size (rectangle: stateSvgWidth/stateSvgHeight; diamond/circle:
            # stateSvgRadius), a backgroundColor (the lane colour), and a displayName (the label).
            size_ok = (s.get('stateSvgRadius') is not None if s['shapeType'] in ('diamond', 'circle')
                       else s.get('stateSvgWidth') is not None and s.get('stateSvgHeight') is not None)
            if not size_ok or not s.get('backgroundColor') or not (s.get('boundObjectFieldValues') or {}).get('displayName'):
                no_render_fields.append(tag)
    check('every state of every seeded canvas SolutionDefinition (the whole solution + its backend '
          'half) carries a real stateLocationX/Y + shapeType — never left for the canvas to land at NaN',
          not no_position, no_position)
    check('every seeded state has the fields the canvas renders: a real size for its OWN shape kind '
          '(stateSvgWidth/Height for rectangle, stateSvgRadius for diamond/circle — not the unread '
          'stateSvgSizeX/Y), a lane backgroundColor, and a displayName label',
          not no_render_fields, no_render_fields)

    trig = [r for n, _c, rows in HWNOCODE_SEED_PAIRS if n == 'EventTrigger' for r in rows][0]
    check('the trigger runs the BACKEND half on SimRigState uno-digital-twin updates; its knobs (window, threshold_c, keep) on inputs_json stay '
          'the instance\'s', trig['solution_name'] == 'uno-temp-split.backend' and json.loads(trig['source_json'])['fieldFilter'] == {'name': 'uno-digital-twin'}
          and 'inputs_json' not in trig['_converge'])
    hs = [r for n, _c, rows in HWNOCODE_SEED_PAIRS if n == 'HardwareSolution' for r in rows][0]
    check('firmware_runtime is NOT converged by a re-seed (the person\'s knob)', 'firmware_runtime' not in hs['_converge'])
    page = SEED_HWNOCODE_PAGE_DISPLAYS[0]
    items = [it for row in json.loads(page['definition'])['rows'] for it in row['items']]
    comps = [it['componentProps']['componentName'] for it in items]
    check('/display/hardware-solutions = the canvas FIRST (demo-4b: opened on the whole solution, every runtime a lane) + 5 '
          'configured tables (hw priorities P1: Capabilities, solutions, derived, placement-by-runtime, the Runtime catalog) + '
          '1 named-graph-panel',
          page['pageRoute'] == 'hardware-solutions' and items[0]['componentProps']['componentName'] == 'c-graph-canvas-panel'
          and items[0]['componentProps']['inputs'].get('solution') == 'uno-temp-split'
          and sorted(comps) == ['c-graph-canvas-panel', 'class-rows-table', 'class-rows-table', 'class-rows-table',
                                'class-rows-table', 'class-rows-table', 'named-graph-panel'], comps)
    gc = json.loads(SEED_HWNOCODE_GRAPHS[0]['definition'])['graphConfig']
    check('the chart = a GraphDefinition (x uptime_s; y temp_c + temp_avg; colours set, showLegend) fed by the chart endpoint',
          gc['xDimension'] == 'uptime_s' and gc['yDimensions'] == ['temp_c', 'temp_avg'] and len(gc['seriesColors']) == 2
          and any(it['componentProps']['inputs'].get('dataPath') == '/api/hwnocode/solutions/uno-temp-split/chart' for it in items))
    from hwnocode.hwnocode_basis import HWNOCODE_CLASSES
    from cmod.cmod_basis import CMOD_CLASSES  # hw priorities P1: the Capabilities table names cmod's own CapabilityDefinition
    known = {c.__name__: c for c in list(HWNOCODE_CLASSES) + list(CMOD_CLASSES)}
    bad = []
    for it in items:
        cn = it['componentProps']['inputs'].get('className')
        if cn:
            if cn not in known:
                bad.append('%s.<unknown class>' % cn)
                continue
            params = set(inspect.signature(known[cn].__init__).parameters)
            bad += ['%s.%s' % (cn, c) for c in it['componentProps']['inputs']['columns'].split(',') if c not in params]
    check('…every table names an hwnocode (or, for the Capabilities table, cmod) class and only columns it has', not bad, bad)
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
    check('GET /api/hwnocode → uno-temp-split + uno-button-clock (ucd-1, sorted by name) + the four node kinds (fs-0/fs-2 adds FirmwareRunState)',
          r.status_code == 200 and {s['name'] for s in r.json['solutions']} == {'uno-temp-split', 'uno-button-clock'}
          and len(r.json['node_kinds']) == 4, r.text[:200])
    r = c.simulate_get('/api/hwnocode/solutions/uno-temp-split/placement')
    check('GET …/placement → computed now: twin 18, bridge 2, backend 3, browser 1', r.status_code == 200 and r.json['summary'] == 'twin 18, bridge 2, backend 3, browser 1', r.text[:200])
    r = c.simulate_get('/api/hwnocode/solutions/uno-temp-split/render')
    check('GET …/render → the board half unchanged vs cmod-1 (in memory, nothing written)', r.status_code == 200 and r.json['board_half']['unchanged_output'], r.text[:200])
    r = c.simulate_get('/api/hwnocode/solutions/uno-temp-split/suggest')
    check('GET …/suggest → bare-c, applied false', r.status_code == 200 and r.json['suggested'] == 'bare-c' and r.json['applied'] is False)
    r = c.simulate_get('/api/hwnocode/solutions/uno-temp-split/chart')
    check('GET …/chart with no samples → ok false + a plain refusal (named-graph-panel renders it verbatim)', r.status_code == 200
          and r.json['ok'] is False and 'no samples yet' in r.json['refusal'])
    r = c.simulate_get('/api/hwnocode/interface', params={'binding': 'uno-temp-split/SimRigState/0'})
    check('GET /api/hwnocode/interface?binding=… → the binding (row uno-digital-twin, the twin\'s pty), placement bridge', r.status_code == 200
          and r.json['binding']['object_name'] == 'uno-digital-twin' and r.json['placement'] == 'bridge', r.text[:200])
    r = c.simulate_get('/api/hwnocode/solutions/nope')
    check('an unknown solution → 404 in plain words', r.status_code == 404 and 'no HardwareSolution' in r.json['error'])


def connectors_and_hardware_mode():
    """selfix 2026-10-05: (1) every seeded edge of uno-temp-split's canvas resolves BOTH endpoints and carries the
    fields RectangleStateLayer/DiamondStateLayer's renderCachedConnectors actually reads (slot.index, connector.id/
    sourceSlot/sinkSlot) — the AdditionTester-seed convention hn-0's own seed now matches (_wire_connectors); (2) the
    HARDWARE_MODE knob: default digital-twin, the one route a person can read back on the HardwareSolution row and in
    the hw-interface node's own fields/why."""
    from hwnocode.custom import solutions as S
    from hwnocode.custom import knobs as K
    d = S.split_app_definition()
    names = {s['stateName'] for s in d['stateInstances']}
    unresolved, missing_fields = [], []
    n_edges = 0
    for s in d['stateInstances']:
        for slot in s['slots']:
            if 'index' not in slot:
                missing_fields.append('%s: slot missing index' % s['stateName'])
            for c in slot.get('connectors') or []:
                n_edges += 1
                if c.get('targetStateName') not in names:
                    unresolved.append('%s -> %s' % (s['stateName'], c.get('targetStateName')))
                if 'id' not in c or 'sourceSlot' not in c or 'sinkSlot' not in c:
                    missing_fields.append('%s -> %s: connector missing id/sourceSlot/sinkSlot' % (s['stateName'], c.get('targetStateName')))
    check('uno-temp-split has 4 seeded edges (fs-1: 5 states, a straight bridging/relay chain), every one with BOTH '
          'endpoints resolvable', n_edges == 4 and not unresolved, (n_edges, unresolved))
    check('…and every slot/connector carries the renderer fields the canvas actually reads (index/id/sourceSlot/sinkSlot) '
          '— not just the first edge', not missing_fields, missing_fields)
    check('every one of the 5 states has a non-empty purpose (his question: "not clear what the backend state change is '
          'for... not sure what the analysis call is")',
          all((s.get('boundObjectFieldValues') or {}).get('purpose') for s in d['stateInstances']),
          [s['stateName'] for s in d['stateInstances'] if not (s.get('boundObjectFieldValues') or {}).get('purpose')])
    hwi = _state(d, 'uno-digital-twin')
    check('the state `uno-digital-twin` (renamed from uno-twin) is the hw-interface, bound to the TWIN by default',
          hwi['boundObjectClass'] == 'HardwareInterface' and hwi['boundObjectFieldValues']['hardware_mode'] == 'digital-twin'
          and hwi['boundObjectFieldValues']['board_instance'] == S.TWIN_INSTANCE)
    check('HWNOCODE_HARDWARE_MODE knob: default digital-twin; an unrecognized value never raises, falls back to digital-twin',
          K.hardware_mode() == 'digital-twin')
    import os
    old = os.environ.get('HWNOCODE_HARDWARE_MODE')
    try:
        os.environ['HWNOCODE_HARDWARE_MODE'] = 'hardware'
        check('…set to hardware, the knob reads it back', K.hardware_mode() == 'hardware')
        os.environ['HWNOCODE_HARDWARE_MODE'] = 'not-a-mode'
        check('…an unknown value refuses silently to the default, never crashes', K.hardware_mode() == 'digital-twin')
    finally:
        if old is None:
            os.environ.pop('HWNOCODE_HARDWARE_MODE', None)
        else:
            os.environ['HWNOCODE_HARDWARE_MODE'] = old
    from hwnocode.hwnocode_seed import HWNOCODE_SEED_PAIRS
    hs = [r for n, _c, rows in HWNOCODE_SEED_PAIRS if n == 'HardwareSolution' for r in rows][0]
    check('the HardwareSolution row shows the knob + which route it took (a described row on the page)',
          hs['hardware_mode'] == 'digital-twin' and 'twin' in hs['route_report'] and 'pty' in hs['route_report'])


def button_clock_compute():
    """ucd-1 (UNO_CORE_DEMO_PLAN.md §5 D-ucd-5): hwnocode.custom.button_clock — the invariant (valid + a broken case
    naming the actual numbers), presses_per_min over the device's own clock, button_clock_derive's upsert of
    ButtonClockDerived, and retention pruning (oldest-first by boot_session/seq, newest kept) — all on synthetic rows
    through a fake manager (the derive.py idiom: SimpleNamespace objectTables, no real DB)."""
    from types import SimpleNamespace
    from hwnocode.custom import button_clock as BC

    def _mgr():
        return SimpleNamespace(objectTables={}, objectTypingDict={}, db=None)

    def _state(mgr, name='uno-button-clock', **f):
        base = dict(uptime_ms=120000, sense_rises=5, sense_falls=4, button_presses=9, led_on=True,
                    dropped_events=0, sync_generation=1, drift_ms=12)
        base.update(f)
        inst = SimpleNamespace(name=name, id=name, **base)
        mgr.objectTables.setdefault('ButtonClockState', {})[name] = inst
        return inst

    def _event(mgr, i, kind='press', uptime_ms=0, boot_session=1, seq=None):
        seq = i if seq is None else seq
        nm = 'evt-%04d' % i
        inst = SimpleNamespace(name=nm, id=nm, seq=seq, boot_session=boot_session, kind=kind, uptime_ms=uptime_ms, epoch_s=0, ms=0)
        mgr.objectTables.setdefault('ButtonClockEvent', {})[nm] = inst
        return inst

    ok, why = BC.invariant(sense_rises=5, sense_falls=4, button_presses=9, led_on=True)
    check('invariant: 5+4==9 and led_on==(5>4) -> ok', ok and why.startswith('ok:'), why)
    ok, why = BC.invariant(sense_rises=5, sense_falls=4, button_presses=9, led_on=False)
    check('invariant: led_on False but sense_rises>sense_falls -> broken, names the mismatch', not ok and 'led_on' in why, why)
    ok, why = BC.invariant(sense_rises=3, sense_falls=2, button_presses=4, led_on=True)
    check('invariant: 3+2=5 != button_presses(4) -> broken, names the actual numbers', not ok and '5' in why and '4' in why, why)

    mgr = _mgr()
    _state(mgr, uptime_ms=90000, sense_rises=3, sense_falls=2, button_presses=5, led_on=True,
          dropped_events=1, sync_generation=2, drift_ms=-7)
    for i in range(4):
        _event(mgr, i, kind='press', uptime_ms=40000 + i * 10000)   # within the last 60s of uptime 90000
    _event(mgr, 10, kind='press', uptime_ms=10000)                  # outside the window (90000-60000=30000)
    r = BC.button_clock_derive(mgr, board_instance='uno-button-clock')
    check('button_clock_derive: ok, invariant_ok True (3+2==5, led_on==(3>2))', r['ok'] and r['invariant_ok'] is True, r)
    check('button_clock_derive: presses_per_min counts only the 4 in-window presses (the 5th at uptime 10000 is outside the last minute)',
          r['presses_per_min'] == 4.0, r)
    check('button_clock_derive: dropped_events_total/last_sync_generation/drift_ms mirrored straight from the wire',
          r['dropped_events_total'] == 1 and r['last_sync_generation'] == 2 and r['drift_ms'] == -7, r)
    derived_rows = list(mgr.objectTables.get('ButtonClockDerived', {}).values())
    check('button_clock_derive upserts exactly one ButtonClockDerived row, name == board_instance',
          len(derived_rows) == 1 and derived_rows[0].name == 'uno-button-clock' and derived_rows[0].board_instance == 'uno-button-clock'
          and derived_rows[0].invariant_ok is True, [getattr(r, 'name', '?') for r in derived_rows])

    mgr2 = _mgr()
    _state(mgr2, uptime_ms=5000, sense_rises=1, sense_falls=0, button_presses=3, led_on=True)
    r2 = BC.button_clock_derive(mgr2, board_instance='uno-button-clock')
    check('button_clock_derive: a broken wire (1+0=1 != 3) -> invariant_ok False, why names 1 and 3',
          r2['ok'] and r2['invariant_ok'] is False and '1' in r2['invariant_why'] and '3' in r2['invariant_why'], r2)

    mgr3 = _mgr()
    r3 = BC.button_clock_derive(mgr3, board_instance='nope')
    check('button_clock_derive: no ButtonClockState row yet -> ok False, named', r3['ok'] is False and 'no ButtonClockState' in r3['error'], r3)

    mgr4 = _mgr()
    for i in range(12):
        _event(mgr4, i, kind='press', uptime_ms=i * 1000, boot_session=1, seq=i)
    doomed = BC.rows_to_prune(mgr4, retention=5)
    check('rows_to_prune (pure, deletes nothing): 12 events, retention 5 -> 7 doomed, the OLDEST 7 (seq 0..6)',
          sorted(int(getattr(r, 'seq')) for r in doomed) == list(range(7)), [getattr(r, 'seq') for r in doomed])
    check('…and the 12 events are all still there (pure function)', len(BC._rows(mgr4, 'ButtonClockEvent')) == 12)
    res = BC.prune_events(mgr4, retention=5)
    kept_seqs = sorted(int(getattr(r, 'seq')) for r in BC._rows(mgr4, 'ButtonClockEvent'))
    check('prune_events: removed 7, kept 5 (the NEWEST, seq 7..11)',
          res['removed'] == 7 and res['kept'] == 5 and kept_seqs == list(range(7, 12)), (res, kept_seqs))
    res2 = BC.prune_events(mgr4, retention=5)
    check('prune_events: idempotent — nothing left to prune once at the bound', res2['removed'] == 0 and res2['kept'] == 5, res2)


def button_clock_cross_domain():
    """ucd-1 (UNO_CORE_DEMO_PLAN.md §3): uno-button-clock's own Cross-Domain canvas — the SAME validator accepts it
    (no compute states, beside uno-temp-split), every state carries a detail_ref whose `class` is a REGISTERED Polari
    class (his fourth message's traversal rule), and the one state whose named row does not exist yet (Firmware Run,
    its FirmwareSolution is ucd-0e2b's) says `planned` plainly rather than pretending it ran."""
    from hwnocode.custom import solutions as S
    from hwnocode.custom import cross_domain as CD
    d = S.button_clock_definition()
    ok, why = CD.validate(d)
    check('uno-button-clock validates as a Cross-Domain Solution (bridging/relay states only, no compute)', ok, why)
    names = {s['stateName'] for s in d['stateInstances']}
    check('6 states: firmware-run, the bridge, relay-in, call-button-clock-ledger, relay-out, frontend-emit',
          names == {'firmware-run', 'uno-button-clock-bridge', 'relay-in', 'call-button-clock-ledger', 'relay-out', 'frontend-emit'}, names)

    from hwnocode.hwnocode_basis import HWNOCODE_CLASSES
    from grpcbridge.mapping_basis import MAPPING_CLASSES
    from cmod.cmod_basis import CMOD_CLASSES
    known = {c.__name__ for c in list(HWNOCODE_CLASSES) + list(MAPPING_CLASSES) + list(CMOD_CLASSES)} | {'SolutionDefinition', 'DisplayDefinition'}
    bad, missing_ref, planned_states = [], [], []
    for s in d['stateInstances']:
        ref = (s.get('boundObjectFieldValues') or {}).get('detail_ref')
        if not ref or not ref.get('class') or not ref.get('name'):
            missing_ref.append(s['stateName'])
            continue
        if ref['class'] not in known:
            bad.append('%s: detail_ref.class %r unknown' % (s['stateName'], ref['class']))
        if ref.get('planned'):
            planned_states.append(s['stateName'])
    check('every state carries a detail_ref {class, name}', not missing_ref, missing_ref)
    check('every detail_ref names a REGISTERED Polari class', not bad, bad)
    check('exactly Firmware Run is planned (its FirmwareSolution does not exist yet, ucd-0e2b) — said, never hidden',
          planned_states == ['firmware-run'], planned_states)
    fr = _state(d, 'firmware-run')
    check('Firmware Run: route_taken == planned, route_why names ucd-0e2b', fr['boundObjectFieldValues']['route_taken'] == 'planned'
          and 'ucd-0e2b' in fr['boundObjectFieldValues']['route_why'])
    check('Firmware Run\'s own detail_ref also carries planned=True + a why', fr['boundObjectFieldValues']['detail_ref']['planned'] is True
          and bool(fr['boundObjectFieldValues']['detail_ref'].get('why')))

    bdef = S.button_clock_backend_definition()
    bnames = [s['stateName'] for s in bdef['stateInstances']]
    check('the executable backend half keeps only relay-in/call/relay-out/frontend-emit (Firmware Run / Bridge dropped — '
          'no SolutionExecutionEngine handler exists for FirmwareRunState/HardwareInterface, the same fact hn-split\'s own '
          'backend_partition relies on)', bnames == ['relay-in', 'call-button-clock-ledger', 'relay-out', 'frontend-emit'], bnames)


def button_clock_page():
    """ucd-1: /display/uno-core-demo — CONFIGURED tables + exactly ONE sci-xy-chart (named-graph-panel), never a raw
    api-json-panel or any custom component; every table names a class that exists (ButtonClockState/ButtonClockEvent,
    board module; ButtonClockDerived, hwnocode) and only columns those classes actually have."""
    import inspect
    from hwnocode.hwnocode_page import SEED_HWNOCODE_PAGE_DISPLAYS, SEED_HWNOCODE_GRAPHS
    from hwnocode.hwnocode_basis import HWNOCODE_CLASSES
    from board.board_basis import BOARD_CLASSES
    page = next(p for p in SEED_HWNOCODE_PAGE_DISPLAYS if p['name'] == 'uno-core-demo')
    check('page route == uno-core-demo, a non-empty one-paragraph description (the bench, what moves)',
          page['pageRoute'] == 'uno-core-demo' and len(page['description']) > 80)
    items = [it for row in json.loads(page['definition'])['rows'] for it in row['items']]
    comps = [it['componentProps']['componentName'] for it in items]
    check('ONLY configured tables (class-rows-table) + exactly ONE named-graph-panel — never api-json-panel, never a '
          'custom component', comps.count('named-graph-panel') == 1 and set(comps) == {'class-rows-table', 'named-graph-panel'}, comps)
    check('every item (tables + the chart) carries a non-empty description',
          all(it.get('description') for it in items), [it['id'] for it in items if not it.get('description')])
    known = {c.__name__: c for c in list(HWNOCODE_CLASSES) + list(BOARD_CLASSES)}
    bad, tables_classes = [], []
    for it in items:
        cn = it['componentProps']['inputs'].get('className')
        if cn:
            tables_classes.append(cn)
            if cn not in known:
                bad.append('%s.<unknown class>' % cn)
                continue
            params = set(inspect.signature(known[cn].__init__).parameters)
            bad += ['%s.%s' % (cn, c) for c in it['componentProps']['inputs']['columns'].split(',') if c not in params]
    check('tables name ButtonClockState, ButtonClockDerived, ButtonClockEvent — the three classes the demo writes/reads, '
          'all REGISTERED (board + hwnocode)', sorted(tables_classes) == ['ButtonClockDerived', 'ButtonClockEvent', 'ButtonClockState'], tables_classes)
    check('…every column named is a real field of its class', not bad, bad)
    chart_item = next(it for it in items if it['componentProps']['componentName'] == 'named-graph-panel')
    check('the chart reads GET /api/hwnocode/button-clock/chart',
          chart_item['componentProps']['inputs']['dataPath'] == '/api/hwnocode/button-clock/chart')
    g = next(g for g in SEED_HWNOCODE_GRAPHS if g['name'] == chart_item['componentProps']['inputs']['graphName'])
    gc = json.loads(g['definition'])['graphConfig']
    check('the chart: x=uptime_s, 3 cumulative series (presses/rises/falls), one colour each',
          gc['xDimension'] == 'uptime_s' and gc['yDimensions'] == ['presses_cum', 'rises_cum', 'falls_cum'] and len(gc['seriesColors']) == 3)


def button_clock_registration():
    """ucd-1: ButtonClockDerived is wired everywhere a module row must be (basis, objects __init__, polari-app.json,
    feature_imports, polariServer defClassList) — never only half-registered."""
    from hwnocode.hwnocode_basis import HWNOCODE_CLASSES
    from hwnocode.objects.hwnocode import ButtonClockDerived
    check('ButtonClockDerived is importable from hwnocode.objects.hwnocode (the __init__ re-export)', ButtonClockDerived is not None)
    check('ButtonClockDerived is in HWNOCODE_CLASSES (the basis class list the server registers)',
          any(c.__name__ == 'ButtonClockDerived' for c in HWNOCODE_CLASSES))
    from moduleService import manifests as M
    m = M.load('hwnocode')
    check('polari-app.json: ButtonClockDerived in files.objects, classes, and the hwnocode_basis import tuple',
          'objects/hwnocode/ButtonClockDerived' in m['files']['objects'] and 'ButtonClockDerived' in m['classes']
          and 'ButtonClockDerived' in dict(m['imports'])['hwnocode.hwnocode_basis'])


def manifest_conform():
    from moduleService import manifests as M
    r = M.conform('hwnocode')
    check('manifests conform hwnocode: no drift', r['ok'], r['findings'])
    m = M.load('hwnocode')
    check('polari-app.json requires board, cmod, grpcbridge; engines declared honestly (make for build, the avr twin for the proof)',
          sorted(m['requires']['modules']) == ['board', 'cmod', 'grpcbridge'] and {'make', 'avr-twin'} <= {e['name'] for e in m['requires']['engines']})


def main():
    print('hwnocode selftest (hn-0)')
    for part in (placement_on_seed, runtimes_demo_4b, refusals, cross_domain_validator, subgraph_reference, knob_refusals,
                 suggestion_fixtures, backend_half_in_engine, palette_metadata, seeds_page_api, connectors_and_hardware_mode,
                 button_clock_compute, button_clock_cross_domain, button_clock_page, button_clock_registration,
                 manifest_conform):
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
