"""
@module hwnocode.custom.solutions

THE CROSS-DOMAIN SPLIT-APP GRAPH (fs-1, DEMONSTRABLES_PLAN.md §9 migration; HARDWARE_NOCODE_PLAN.md §4 variant h over
the EXISTING peripheral, variant b): `uno-temp-split` drawn on the ONE canvas as a SolutionDefinition, `category`
'cross-domain' (D-fs-3: bridging/relay ONLY, no compute — validated by `hwnocode.custom.cross_domain.validate`) —
graph_builder shapes, the exact dicts both engines and the canvas read:

    firmware-run     FirmwareRunState     → cmod FirmwareSolution `uno-sim-rig` (board arduino-uno-r3, mode from the
                                           HARDWARE_MODE knob) — the firmware ITSELF (tasks, schedule, register map) is
                                           fs-0's row, unchanged; this state only orchestrates validate -> build -> run
       │ frames
    uno-digital-twin HardwareInterface   → HardwareInterfaceBinding `uno-temp-split/SimRigState/0` (the split point; the
                                           twin's pty, or the detected board's serial port in hardware mode)
       │ the row changes (10 Hz)
    relay-in         BackendStateChange   SimRigState · update · temp_c — frame → event (bridging only, no compute)
       │
    call-temp-analysis  SolutionInvocation → the backend solution `temp-analysis` (moving average + threshold + commit —
                                             ALL the compute, moved OUT per D-fs-3; same math, see temp_analysis.py)
       │ temp_avg, over_threshold bound back
    relay-out        BackendStateChange   SimRigTempDerived · update · over_threshold — command → bridge (the bridge
                                           reads the committed row and relays the command down to the device)

Every node kind below the split already exists in the engine (no new arm beyond fs-0's FirmwareRunState). The knobs
(window, threshold) ride the trigger's inputs_json — the person's, on the EventTrigger row. The display half is
/display/hardware-solutions (hwnocode_page) + /display/firmware-solutions (fs-0/fs-1, cmod_page).

Migrated 2026-10-05 (DEMONSTRABLES_PLAN.md §9, RULED "go with your picks" — D-fs-1..3): the OLD 8-state shape (a
`HardwareSubgraph` node `sim-rig` embedding the CGraph directly, with the moving-average/threshold/commit compute
INLINE on this same canvas) is RETIRED. The firmware half is now its own `FirmwareSolution` (cmod, fs-0, already
built — `uno-sim-rig`); the compute half is now its own plain backend `SolutionDefinition` (`temp-analysis`, called
by `call-temp-analysis`); this canvas keeps ONLY the bridging/relay states his message named. `uno-digital-twin`'s own
name/binding/route-report fields are UNCHANGED by the migration (same split point, same twin-or-hardware routing).

THE CONFIGURATION-BASED ROUTE (his message: "a configuration based conditional... digital twin route when the
configuration is in one mode, and [hardware] route in the other case"): `hwnocode.custom.knobs.hardware_mode()` — read
ONCE here, at import, same idiom as every other env-var knob in this forest. `_hardware_route()` is the ONE place that
branches on it: digital-twin -> the twin's pty link; hardware -> the detected arduino-uno-r3 BoardInstance's serial port
(board.custom.installer.detected(), best-effort — a hardware mode with nothing detected refuses to the twin's pty rather
than leaving the interface unattached, and SAYS SO in `route_report`, read back in the hw-interface node's `why` and in
the HardwareSolution row). No other branching exists on this knob. (fs-2, not yet built, will move this read into
FirmwareRunState itself per DEMONSTRABLES_PLAN.md §9 — fs-1 keeps the knob read here, unchanged, and only passes the
resolved `mode` string into the Firmware Run state's fields.)
"""
from polariNoCode import graph_builder as GB
from hwnocode.custom import knobs as K

SOLUTION = 'uno-temp-split'
CGRAPH = 'uno-sim-rig-graph'
FIRMWARE_SOLUTION = 'uno-sim-rig'          # cmod's FirmwareSolution (fs-0) — the firmware itself lives there now
ANALYSIS_SOLUTION = 'temp-analysis'        # the backend SolutionDefinition the compute half moved into (fs-1)
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

#: fs-1's 5 cross-domain canvas states, one plain-words sentence each (his message: "it is not clear what the backend
#: state change is for... not sure what the analysis call is" — shown in the state's tooltip/body AND in the "What
#: each state does" table on /display/hardware-solutions; HardwareNodePlacement.purpose, layer=='solution' rows only).
#: Bridging/relay ONLY (D-fs-3) — the compute these purposes used to describe inline now lives in temp_analysis.py.
STATE_PURPOSES = {
    'firmware-run': 'Takes the cmod FirmwareSolution uno-sim-rig (the C task graph + board), validates it still '
                    'resolves, and runs it (flash or digital twin, by the HARDWARE_MODE knob) — the firmware ITSELF '
                    'lives there now, not on this canvas.',
    'uno-digital-twin': 'The Java gRPC bridge attached to the twin\'s UART (or the real port in hardware mode): the split '
                        'point between the device and the backend.',
    'relay-in': 'Bridging only: a frame arrived with a new temp_c on the SimRigState row — turned into a backend event, '
               'no computation here.',
    'call-temp-analysis': 'Calls OUT to the backend solution temp-analysis (a SolutionInvocation) — the moving average, '
                          'the threshold check and the commit all run THERE, never inline on this cross-domain canvas.',
    'relay-out': 'Bridging only: once temp-analysis commits a new verdict, this fires so the bridge relays the command '
                '(over_threshold) down to the device.',
}


#: selfix 2026-10-05 (prf-urgent, dev-selfix), carried forward by fs-1's migration: canvas layout for each node of
#: split_app_definition()'s now-5-state bridging/relay pipeline. graph_builder.node() deliberately emits NO
#: position/shape/svg fields (it's the shared parity-pinned DSL other domains build on too — never add canvas-only
#: fields there), but the Angular canvas's NoCodeState constructor passes stateLocationX/Y, shapeType, stateSvgName
#: and stateSvgRadius/SizeX/Y straight through with no fallback: left undefined, every state lands at NaN and the
#: canvas renders nothing, even though stateInstances is non-empty. Shapes/sizes mirror the AdditionTester seed
#: convention (polariApiServer/solutionSeedData.py): circle/diamond for decision points, rectangle otherwise; a
#: rectangle reads stateSvgWidth/stateSvgHeight/cornerRadius (RectangleStateLayer.ts), never stateSvgSizeX/Y. Every
#: node also gets a plain-words `displayName` in boundObjectFieldValues, matching every other seed's convention.
_LAYOUT = {
    'firmware-run':     {'x': 80,   'y': 280, 'shape': 'rectangle', 'color': '#4527A0', 'label': 'Firmware Run (uno-sim-rig)'},
    'uno-digital-twin': {'x': 320,  'y': 280, 'shape': 'rectangle', 'color': '#6D4C41', 'label': 'uno-digital-twin (split point)'},
    'relay-in':         {'x': 560,  'y': 280, 'shape': 'rectangle', 'color': '#1565C0', 'label': 'Relay in: frame → event'},
    'call-temp-analysis': {'x': 800, 'y': 280, 'shape': 'rectangle', 'color': '#00695C', 'label': 'call temp-analysis'},
    'relay-out':        {'x': 1040, 'y': 280, 'shape': 'rectangle', 'color': '#FF9800', 'label': 'Relay out: command → bridge'},
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
    """The cross-domain canvas — Firmware Run, Bridge, Relay in, call temp-analysis, Relay out — as ONE
    SolutionDefinition definition dict (D-fs-3: bridging/relay states ONLY, validated by hwnocode.custom.cross_domain;
    `category='cross-domain'` is set where this definition is wrapped into a SolutionDefinition ROW, in seed_rows.py —
    this dict itself is just the graph_builder shape both engines + the canvas read)."""
    n = GB.node
    run = n('firmware-run', 'FirmwareRunState', {'firmware_solution': FIRMWARE_SOLUTION, 'board_variable': BOARD,
                                                 'mode': ROUTE['mode']}, outs=[['uno-digital-twin']])
    hwi = n('uno-digital-twin', 'HardwareInterface', {'binding': BINDING, 'object_class': OBJECT_CLASS, 'object_name': OBJECT_NAME,
                                              'bridge_name': BRIDGE, 'board_instance': ROUTE['board_instance'], 'port': ROUTE['port'],
                                              'interface_kind': ROUTE['interface_kind'], 'hardware_mode': ROUTE['mode'],
                                              'route_report': ROUTE['route_report']}, outs=[['relay-in']])
    relay_in = n('relay-in', 'BackendStateChange', {'displayName': 'Relay in: SimRigState temp_c changed', 'modelName': OBJECT_CLASS,
                                                    'fieldName': 'temp_c', 'changeType': 'update',
                                                    'description': 'fires on every frame the bridge applies to the row — '
                                                                   'bridging only, turns it into a backend event'},
                 outs=[['call-temp-analysis']])
    call = GB.invoke('call-temp-analysis', ANALYSIS_SOLUTION,
                      mappings=[{'param': 'object', 'valueSource': GB.var_src('instance.name')},
                                {'param': 'temp_c', 'valueSource': GB.var_src('instance.temp_c')},
                                {'param': 'uptime_ms', 'valueSource': GB.var_src('instance.uptime_ms')},
                                {'param': 'window', 'valueSource': GB.var_src('window')},
                                {'param': 'threshold_c', 'valueSource': GB.var_src('threshold_c')},
                                {'param': 'keep', 'valueSource': GB.var_src('keep')},
                                {'param': 'solution', 'valueSource': GB.lit_src(name)}],
                      bindings=[{'output': 'temp_avg', 'contextVar': 'temp_avg'},
                                {'output': 'over_threshold', 'contextVar': 'over_threshold'}],
                      nxt='relay-out')
    relay_out = n('relay-out', 'BackendStateChange', {'displayName': 'Relay out: command ready for the bridge',
                                                      'modelName': 'SimRigTempDerived', 'fieldName': 'over_threshold',
                                                      'changeType': 'update',
                                                      'description': 'fires once temp-analysis commits a new verdict — '
                                                                     'bridging only: the bridge relays over_threshold '
                                                                     'down to the device as a command'}, outs=[[]])
    return _lay_out(GB.solution(name, run, hwi, relay_in, call, relay_out))


def contract():
    return {'description': 'uno-temp-split (fs-1, Cross-Domain): Firmware Run (uno-sim-rig) → Bridge (uno-digital-twin) → '
                           'Relay in → call temp-analysis → Relay out. Bridging/relay only (D-fs-3) — the moving '
                           'average + threshold + commit run inside temp-analysis, called out to.',
            'inputs': [{'name': 'instance.name', 'required': True, 'description': 'the SimRigState row (the trigger payload)'},
                       {'name': 'instance.temp_c', 'required': True, 'description': '°C from the TMP36 frame'},
                       {'name': 'instance.uptime_ms', 'required': True, 'description': 'the firmware clock'},
                       {'name': 'window', 'required': False, 'description': 'samples in the moving average (knob)'},
                       {'name': 'threshold_c', 'required': False, 'description': 'the flag threshold in °C (knob)'}],
            'returns': [], 'executionRights': 'definer'}
