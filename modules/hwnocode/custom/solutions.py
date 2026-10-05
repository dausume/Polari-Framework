"""
@module hwnocode.custom.solutions

THE SPLIT-APP GRAPH (HARDWARE_NOCODE_PLAN.md §4 variant h, over the EXISTING peripheral, variant b): `uno-temp-split` drawn on the
ONE canvas as a SolutionDefinition — graph_builder shapes, the exact dicts both engines and the canvas read:

    sim-rig          HardwareSubgraph   → cmod CGraph `uno-sim-rig-graph` (UNCHANGED; byte-identical to the shipped firmware)
       │ frames
    uno-digital-twin HardwareInterface  → HardwareInterfaceBinding `uno-temp-split/SimRigState/0` (the split point; the twin's pty,
                                         or the detected board's serial port in hardware mode — the HARDWARE_MODE knob, below)
       │ the row changes (10 Hz)
    on-temp          BackendStateChange   SimRigState · update · temp_c
    moving-avg       AnalysisCall         `hwnocode-temp-derive`: keep the sample (ring), the moving average over `window` samples
    over?            ConditionalChain     temp_avg > threshold_c
    flag-on/-off     VariableAssignment   over_threshold = true | false
    commit           StateChangeCommit    SimRigTempDerived[uno-digital-twin] ← temp_avg, over_threshold, last_temp_c, last_uptime_ms

Every node kind below the split already exists in the engine (no new arm). The knobs (window, threshold) ride the trigger's
inputs_json — the person's, on the EventTrigger row. The display half is /display/hardware-solutions (hwnocode_page).

Renamed 2026-10-05 (his message: "rather than just calling it twin which is confusing, call it uno-digital-twin so it is
clear"): the state `uno-twin` -> `uno-digital-twin` everywhere a person sees it (the canvas, the tables, the probes). The
Runtime row name `c-twin` is UNCHANGED (a runtime/process identity, not this state) — only its display label changed
(hwnocode.custom.runtimes / custom-no-code.ts).

THE CONFIGURATION-BASED ROUTE (his message: "a configuration based conditional... digital twin route when the
configuration is in one mode, and [hardware] route in the other case"): `hwnocode.custom.knobs.hardware_mode()` — read
ONCE here, at import, same idiom as every other env-var knob in this forest. `_hardware_route()` is the ONE place that
branches on it: digital-twin -> the twin's pty link; hardware -> the detected arduino-uno-r3 BoardInstance's serial port
(board.custom.installer.detected(), best-effort — a hardware mode with nothing detected refuses to the twin's pty rather
than leaving the interface unattached, and SAYS SO in `route_report`, read back in the hw-interface node's `why` and in
the HardwareSolution row). No other branching exists on this knob.
"""
from polariNoCode import graph_builder as GB
from hwnocode.custom import knobs as K

SOLUTION = 'uno-temp-split'
CGRAPH = 'uno-sim-rig-graph'
BOARD = 'arduino-uno-r3'
TWIN_INSTANCE = 'twin:arduino-uno-r3#0'
BRIDGE = 'uno-temp-split'
OBJECT_CLASS = 'SimRigState'
OBJECT_NAME = 'uno-digital-twin'
BINDING = '%s/%s/0' % (BRIDGE, OBJECT_CLASS)
TWIN_LINK = '/tmp/polari-uno-twin-uart'
ANALYSIS = 'hwnocode-temp-derive'
TRIGGER = 'uno-temp-split-on-temp'
DISPLAY = 'hardware-solutions'
GRAPH = 'hwnocode-uno-temp-split-temp'
KNOBS = {'window': 5, 'threshold_c': 25.0, 'keep': 600}


def _hardware_route(manager=None):
    """(dict) the ONE branch on the HARDWARE_MODE knob — digital-twin's pty, or hardware's detected serial port. Never
    raises: a hardware-mode miss refuses to the twin's pty and says why in `route_report`."""
    mode = K.hardware_mode()
    if mode == 'hardware':
        try:
            from board.custom import installer as INST
            det = INST.detected(manager=manager)
            inst = next((i for i in (det.get('instances') or []) if i.get('definition') == BOARD), None)
        except Exception as e:  # noqa: BLE001 — a knob never breaks the seed; it reports why
            inst, det = None, {'error': str(e)}
        if inst is not None:
            port = inst.get('by_id_path') or inst.get('port') or ''
            return {'mode': mode, 'board_instance': inst.get('name', ''), 'port': port, 'interface_kind': 'serial',
                    'route_report': 'hardware mode: attached to the detected %s %s at %s' % (BOARD, inst.get('name', ''), port or '?')}
        why = det.get('error') if isinstance(det, dict) and det.get('error') else 'no %s detected on this host' % BOARD
        return {'mode': mode, 'board_instance': TWIN_INSTANCE, 'port': TWIN_LINK, 'interface_kind': 'twin-pty',
                'route_report': ('hardware mode requested but %s — refused to the twin\'s pty (%s) so the solution still runs; '
                                 '`pol board detect --push` once it is plugged in' % (why, TWIN_LINK))}
    return {'mode': mode, 'board_instance': TWIN_INSTANCE, 'port': TWIN_LINK, 'interface_kind': 'twin-pty',
            'route_report': 'digital-twin mode: attached to the twin\'s pty link (%s)' % TWIN_LINK}


#: read once at import (the env-var-knob idiom) — split_app_definition()'s hw-interface node and seed_rows' BINDINGS/
#: HardwareSolution rows all read this ONE snapshot so the state and the row it describes never disagree.
ROUTE = _hardware_route()

#: hn-0's 8 canvas states, one plain-words sentence each (his message: "it is not clear what the backend state change is
#: for... not sure what the analysis call is" — shown in the state's tooltip/body AND in the "What each state does"
#: table on /display/hardware-solutions; HardwareNodePlacement.purpose, layer=='solution' rows only).
STATE_PURPOSES = {
    'sim-rig': 'The C firmware app on the board: reads the TMP36 on A0 and sends SimRigState frames over UART.',
    'uno-digital-twin': 'The Java gRPC bridge attached to the twin\'s UART (or the real port in hardware mode): the split '
                        'point between the device and the backend.',
    'on-temp': 'The backend state change: a frame arrived with a new temp_c on the SimRigState row.',
    'moving-avg': 'The backend analysis: the moving average of temp_c over the trigger\'s window.',
    'over?': 'The threshold check: is the moving average over threshold_c?',
    'flag-on': 'Sets the LED command on, because the average is over the threshold.',
    'flag-off': 'Sets the LED command off, because the average is at or under the threshold.',
    'commit': 'Sends the command back through the bridge: commits temp_avg and over_threshold onto SimRigTempDerived.',
}


#: selfix 2026-10-05 (prf-urgent, dev-selfix): canvas layout for each node of split_app_definition()'s
#: linear pipeline (one branch at `over?`, converging at `commit`). graph_builder.node() deliberately
#: emits NO position/shape/svg fields (it's the shared parity-pinned DSL other domains build on too —
#: never add canvas-only fields there), but the Angular canvas's NoCodeState constructor passes
#: stateLocationX/Y, shapeType, stateSvgName and stateSvgRadius/SizeX/Y straight through with no
#: fallback: left undefined, every state lands at NaN and the canvas renders nothing, even though
#: stateInstances is non-empty (this is what "an empty canvas, Solution uno-temp-split" actually was —
#: a seed-shape gap, not a rendering bug). Shapes/sizes mirror the AdditionTester seed convention
#: (polariApiServer/solutionSeedData.py): circle/diamond for decision points, rectangle otherwise.
#:
#: selfix round 3 (2026-10-05): the FIRST pass used stateSvgSizeX/stateSvgSizeY for rectangles —
#: a field RectangleStateLayer.ts never reads. It reads stateSvgWidth/stateSvgHeight/cornerRadius
#: (falling back to stateSvgRadius, then a hard-coded 20px) — exactly AdditionTester's own
#: rectangle states' fields (`"stateSvgWidth": 120, "stateSvgHeight": 80, "cornerRadius": 8`). That
#: gap is why 7 of 8 states drew as a bare 20×20 stub (only the slot dots) — only `over?`
#: (diamond, which DOES read stateSvgRadius) drew correctly. Every node also gets a plain-words
#: `displayName` in boundObjectFieldValues, matching every other seed's convention.
_LAYOUT = {
    'sim-rig':          {'x': 80,   'y': 280, 'shape': 'rectangle', 'color': '#5D4037', 'label': 'UNO sim-rig (C, on-device)'},
    'uno-digital-twin': {'x': 320,  'y': 280, 'shape': 'rectangle', 'color': '#6D4C41', 'label': 'uno-digital-twin (split point)'},
    'on-temp':          {'x': 560,  'y': 280, 'shape': 'rectangle', 'color': '#1565C0', 'label': 'SimRigState.temp_c changed'},
    'moving-avg':       {'x': 800,  'y': 280, 'shape': 'rectangle', 'color': '#1565C0', 'label': 'Moving average (temp_avg)'},
    'over?':            {'x': 1040, 'y': 280, 'shape': 'diamond',   'color': '#4CAF50', 'label': 'Over threshold?'},
    'flag-on':          {'x': 1280, 'y': 180, 'shape': 'rectangle', 'color': '#4CAF50', 'label': 'Flag on'},
    'flag-off':         {'x': 1280, 'y': 380, 'shape': 'rectangle', 'color': '#F44336', 'label': 'Flag off'},
    'commit':           {'x': 1520, 'y': 280, 'shape': 'rectangle', 'color': '#FF9800', 'label': 'Commit SimRigTempDerived'},
}


def _lay_out(definition):
    """Decorate every stateInstance with the canvas fields the Angular NoCodeState/RectangleStateLayer/
    DiamondStateLayer rendering actually reads (positions, shape, the RIGHT size fields per shape,
    a lane colour, a display label, a one-sentence purpose) — see _LAYOUT's docstring above."""
    for s in definition.get('stateInstances') or []:
        name = s.get('stateName')
        spot = _LAYOUT.get(name, {'x': 80, 'y': 80, 'shape': 'rectangle', 'color': '#9E9E9E', 'label': name or ''})
        s['stateLocationX'], s['stateLocationY'] = spot['x'], spot['y']
        s['shapeType'] = s['stateSvgName'] = spot['shape']
        s['layerName'] = '%s-layer' % spot['shape']
        s['backgroundColor'] = spot['color']
        s['slotRadius'] = 5
        if spot['shape'] == 'diamond':
            s['stateSvgRadius'] = 70
            s['stateSvgSizeX'] = s['stateSvgSizeY'] = None
        else:
            s['stateSvgWidth'], s['stateSvgHeight'], s['cornerRadius'] = 160, 90, 8
            s['stateSvgRadius'] = None
            s['stateSvgSizeX'] = s['stateSvgSizeY'] = None
        fields = dict(s.get('boundObjectFieldValues') or {})
        fields.setdefault('displayName', spot['label'])
        fields.setdefault('purpose', STATE_PURPOSES.get(name, ''))
        s['boundObjectFieldValues'] = fields
    return _wire_connectors(definition)


def _wire_connectors(definition):
    """selfix 2026-10-05: graph_builder.node()'s connectors carry only `targetStateName` (the shared, engine-parity DSL
    deliberately emits nothing canvas-only — see graph_builder.py's docstring); the Angular canvas's connector
    renderer (RectangleStateLayer/DiamondStateLayer.renderCachedConnectors) ALSO needs, per AdditionTester's own seed
    convention (polariApiServer/solutionSeedData.py): every slot's own `index` (used to find its
    `circle.slot-marker[slot-index=...]`), and every connector's `id` + `sourceSlot` + `sinkSlot` (the target's INPUT
    slot — always index 0, by graph_builder's own convention: slots[0] is always the single input slot). Without
    these, `slot.index` and `connector.sinkSlot` are `undefined` for every state hwnocode seeds, `connector.id` is
    `undefined` too, and `connector.id.toString()` throws partway through the FIRST connector it draws — aborting the
    renderer's forEach before any further edge is ever appended. Hence "only the first edge draws"."""
    next_id = 1
    for s in definition.get('stateInstances') or []:
        for i, slot in enumerate(s.get('slots') or []):
            slot['index'] = i
            for c in slot.get('connectors') or []:
                c['id'] = next_id
                c['sourceSlot'] = i
                c['sinkSlot'] = 0
                next_id += 1
    return definition


def split_app_definition(name=SOLUTION):
    """The whole graph — hardware subgraph, the split, the backend nodes — as ONE SolutionDefinition definition dict."""
    n = GB.node
    sim = n('sim-rig', 'HardwareSubgraph', {'cgraph': CGRAPH, 'board_definition': BOARD, 'board_instance': TWIN_INSTANCE,
                                            'firmware_runtime': 'bare-c'}, outs=[['uno-digital-twin']])
    hwi = n('uno-digital-twin', 'HardwareInterface', {'binding': BINDING, 'object_class': OBJECT_CLASS, 'object_name': OBJECT_NAME,
                                              'bridge_name': BRIDGE, 'board_instance': ROUTE['board_instance'], 'port': ROUTE['port'],
                                              'interface_kind': ROUTE['interface_kind'], 'hardware_mode': ROUTE['mode'],
                                              'route_report': ROUTE['route_report']}, outs=[['on-temp']])
    entry = n('on-temp', 'BackendStateChange', {'displayName': 'SimRigState temp_c changed', 'modelName': OBJECT_CLASS,
                                                'fieldName': 'temp_c', 'changeType': 'update',
                                                'description': 'fires on every frame the bridge applies to the row'},
              outs=[['moving-avg']])
    avg = n('moving-avg', 'AnalysisCall', {
        'analysis': ANALYSIS, 'resultVariable': 'temp_avg', 'pick': 'temp_avg',
        'params': {'object': GB.var_src('instance.name'), 'uptime_ms': GB.var_src('instance.uptime_ms'),
                   'temp_c': GB.var_src('instance.temp_c'), 'window': GB.var_src('window'), 'keep': GB.var_src('keep'),
                   'solution': name}}, outs=[['over?']])
    over = GB.cond('over?', [GB.link(GB.var_src('temp_avg'), '>', GB.var_src('threshold_c'), display_name='average above the threshold')],
                   'flag-on', 'flag-off')
    on = n('flag-on', 'VariableAssignment', {'variableName': 'over_threshold', 'value': '',
                                            'assignmentConfig': {'valueSource': GB.lit_src(True)}}, outs=[['commit']])
    off = n('flag-off', 'VariableAssignment', {'variableName': 'over_threshold', 'value': '',
                                              'assignmentConfig': {'valueSource': GB.lit_src(False)}}, outs=[['commit']])
    commit = n('commit', 'StateChangeCommit', {
        'changeType': 'update', 'targetClassName': 'SimRigTempDerived', 'instanceRef': GB.var_src('instance.name'),
        'fields': {'temp_avg': GB.var_src('temp_avg'), 'over_threshold': GB.var_src('over_threshold'),
                   'threshold_c': GB.var_src('threshold_c'), 'window': GB.var_src('window'),
                   'last_temp_c': GB.var_src('instance.temp_c'), 'last_uptime_ms': GB.var_src('instance.uptime_ms')}}, outs=[[]])
    return _lay_out(GB.solution(name, sim, hwi, entry, avg, over, on, off, commit))


def contract():
    return {'description': 'uno-temp-split (hn-0, variant h): the UNO sim-rig subgraph → the bridge → a moving average of temp_c and '
                           'a threshold flag on SimRigTempDerived → a configured chart. The backend half runs per frame.',
            'inputs': [{'name': 'instance.name', 'required': True, 'description': 'the SimRigState row (the trigger payload)'},
                       {'name': 'instance.temp_c', 'required': True, 'description': '°C from the TMP36 frame'},
                       {'name': 'instance.uptime_ms', 'required': True, 'description': 'the firmware clock'},
                       {'name': 'window', 'required': False, 'description': 'samples in the moving average (knob)'},
                       {'name': 'threshold_c', 'required': False, 'description': 'the flag threshold in °C (knob)'}],
            'returns': [], 'executionRights': 'definer'}
