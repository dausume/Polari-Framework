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
import json

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


# =============================================================================================================
# ucd-1: uno-button-clock — THE UNO CORE DEMO'S own Cross-Domain Solution (UNO_CORE_DEMO_PLAN.md §3), drawn beside
# uno-temp-split on the SAME canvas kind (category='cross-domain'), the SAME template (Firmware Run → Bridge →
# Relay-in → call <backend solution> → Relay-out → Frontend emit). Two differences from uno-temp-split, both named
# in the plan: (1) the Firmware Run names a cmod FirmwareSolution (`uno-button-clock`) that DOES NOT EXIST YET
# (ucd-0e2b builds it) — referenced by NAME only; cross_domain.validate() never resolves a FirmwareRunState's
# `firmware_solution` field to a live row (it only checks the STATE KIND), so this is accepted structurally and the
# node's own `route_taken`/`route_why` SAY "planned" in plain words (never silently pretend it ran); (2) a sixth
# state, Frontend emit (EmitFrontendEvent), closes the loop onto /display/uno-core-demo — uno-temp-split's own canvas
# predates that state kind's use here and stops at Relay-out, D-fs-3 never required a Frontend-emit state, this demo
# adds one because his message named the display as part of the composition (UNO_CORE_DEMO_PLAN.md §3's fifth bullet).
#
# detail_ref (his fourth message, §3's "Traversal rule"): every state's boundObjectFieldValues carries one, a plain
# {'class', 'name', 'route'} dict — never a parsed composite string, the Polari ref idiom (:ref:<Class> columns are
# typed by the COLUMN, this is typed by the dict itself since a no-code state has no column schema). `class` is always
# a REGISTERED Polari class name (so a reader can always resolve "what kind of thing is this"); `name` is the row (or
# page) it names, which may not exist yet (Firmware Run — `planned: True` + `why` SAYS so, never silently omitted).
# =============================================================================================================
BC_SOLUTION = 'uno-button-clock'
BC_LEDGER_SOLUTION = 'button-clock-ledger'          # hwnocode.custom.button_clock_ledger — the backend compute half
BC_BACKEND_SOLUTION = '%s.backend' % BC_SOLUTION    # the executable subset an EventTrigger runs (relay-in.. frontend-emit)
BC_FIRMWARE_SOLUTION = 'uno-button-clock'           # cmod FirmwareSolution — NOT YET BUILT (ucd-0e2b); named only
BC_BRIDGE = 'button-clock'                          # grpcbridge.mapping_basis.BUTTON_CLOCK_BRIDGE
BC_OBJECT_CLASS = 'ButtonClockState'
BC_OBJECT_NAME = 'uno-button-clock'                 # the Push match key: one row, the board instance's latest state
BC_BINDING = '%s/%s/0' % (BC_BRIDGE, BC_OBJECT_CLASS)
BC_TWIN_LINK = '/tmp/polari-uno-button-clock-twin-uart'   # its OWN pty — never shares uno-temp-split's twin link
BC_DISPLAY = 'uno-core-demo'
BC_KNOBS = {'retention': 10000, 'sync_every_s': 300}


def _bc_route():
    """Reuses the ONE hardware-mode read this module already did at import (`ROUTE`) rather than probing the board a
    second time — same board, same knob, same digital-twin-or-hardware decision; only the twin's OWN pty differs."""
    r = dict(ROUTE)
    if r.get('interface_kind') == 'twin-pty':
        r = dict(r, board_instance='twin:arduino-uno-r3#0', port=BC_TWIN_LINK)
    return r


BC_ROUTE = _bc_route()

#: plain-words purpose per state (shown the same way uno-temp-split's STATE_PURPOSES are) — his rule: every state says
#: what it does, in words a person reads without opening the detail.
BC_STATE_PURPOSES = {
    'firmware-run': 'Takes the cmod FirmwareSolution uno-button-clock (clock.tick/set, button.isr, led.toggle, '
                   'sense.isr, events.queue, telemetry.send) and runs it — PLANNED: that Firmware Solution is not '
                   'built yet (ucd-0e2b); referenced by name, resolved at run time, never silently assumed to exist.',
    'uno-button-clock-bridge': 'The Java gRPC bridge attached to the button-clock UNO\'s UART (or the twin\'s pty in '
                              'digital-twin mode): the split point between the device and the backend.',
    'relay-in': 'Bridging only: a new ButtonClockState frame arrived (seq advanced) — turned into a backend event, '
               'no computation here.',
    'call-button-clock-ledger': 'Calls OUT to the backend solution button-clock-ledger (a SolutionInvocation) — '
                                'presses_per_min and the sense/press/LED invariant are computed THERE, never inline here.',
    'relay-out': 'Bridging only: SET_TIME (set_epoch_s/set_ms/set_sync_generation from the server clock, at attach and '
                'every sync_every_s) and SET_LED on demand — both ride the SAME presence-masked command-field PUT '
                'uno-temp-split\'s led_on uses, relayed down to the device through this bridge.',
    'frontend-emit': 'Tells the browser a new ButtonClockDerived/ButtonClockState frame is ready — /display/'
                     'uno-core-demo\'s tables and chart read the rows directly; this just signals "there is something new".',
}

_BC_LAYOUT = {
    'firmware-run':             {'x': 80,   'y': 560, 'shape': 'rectangle', 'color': '#4527A0', 'label': 'Firmware Run (uno-button-clock, planned)'},
    'uno-button-clock-bridge':  {'x': 320,  'y': 560, 'shape': 'rectangle', 'color': '#6D4C41', 'label': 'uno-button-clock-bridge (split point)'},
    'relay-in':                 {'x': 560,  'y': 560, 'shape': 'rectangle', 'color': '#1565C0', 'label': 'Relay in: frame → event'},
    'call-button-clock-ledger': {'x': 800,  'y': 560, 'shape': 'rectangle', 'color': '#00695C', 'label': 'call button-clock-ledger'},
    'relay-out':                {'x': 1040, 'y': 560, 'shape': 'rectangle', 'color': '#FF9800', 'label': 'Relay out: SET_TIME / SET_LED'},
    'frontend-emit':            {'x': 1280, 'y': 560, 'shape': 'rectangle', 'color': '#2E7D32', 'label': 'Frontend emit → uno-core-demo'},
}


def _bc_detail_refs():
    """One {'class', 'name', 'route'} dict per state (his fourth message's traversal rule) — `planned`/`why` on the
    one state whose named row does not exist yet (Firmware Run)."""
    return {
        'firmware-run': {'class': 'FirmwareSolution', 'name': BC_FIRMWARE_SOLUTION, 'route': '/display/firmware?solution=%s' % BC_FIRMWARE_SOLUTION,
                        'planned': True, 'why': 'FirmwareSolution %r is not built yet (ucd-0e2b) — named here, resolved at run time' % BC_FIRMWARE_SOLUTION},
        'uno-button-clock-bridge': {'class': 'HardwareInterfaceBinding', 'name': BC_BINDING, 'route': '/display/hardware-chain'},
        'relay-in': {'class': 'SolutionDefinition', 'name': BC_LEDGER_SOLUTION, 'route': '/display/hardware-solutions'},
        'call-button-clock-ledger': {'class': 'SolutionDefinition', 'name': BC_LEDGER_SOLUTION, 'route': '/display/hardware-solutions'},
        'relay-out': {'class': 'WireContract', 'name': '%s@%s' % (BC_OBJECT_CLASS, BC_BRIDGE), 'route': '/display/hardware-chain',
                     'why': 'the SET_TIME/SET_LED command fields of ButtonClockState\'s own wire contract'},
        'frontend-emit': {'class': 'DisplayDefinition', 'name': BC_DISPLAY, 'route': '/display/%s' % BC_DISPLAY},
    }


def _bc_lay_out(definition):
    """Same canvas-field convention as `_lay_out` (uno-temp-split) — duplicated rather than shared because this
    graph's layout row (_BC_LAYOUT) and detail_ref table (_bc_detail_refs) are its own; also stamps `detail_ref`."""
    refs = _bc_detail_refs()
    for s in definition.get('stateInstances') or []:
        name = s.get('stateName')
        spot = _BC_LAYOUT.get(name, {'x': 80, 'y': 80, 'shape': 'rectangle', 'color': '#9E9E9E', 'label': name or ''})
        s['stateLocationX'], s['stateLocationY'] = spot['x'], spot['y']
        s['shapeType'] = s['stateSvgName'] = spot['shape']
        s['layerName'] = '%s-layer' % spot['shape']
        s['backgroundColor'] = spot['color']
        s['slotRadius'] = 5
        s['stateSvgWidth'], s['stateSvgHeight'], s['cornerRadius'] = 170, 90, 8
        s['stateSvgRadius'] = None
        s['stateSvgSizeX'] = s['stateSvgSizeY'] = None
        fields = dict(s.get('boundObjectFieldValues') or {})
        fields.setdefault('displayName', spot['label'])
        fields.setdefault('purpose', BC_STATE_PURPOSES.get(name, ''))
        fields['detail_ref'] = refs.get(name, {})
        s['boundObjectFieldValues'] = fields
    return _wire_connectors(definition)


def button_clock_definition(name=BC_SOLUTION):
    """The uno-button-clock cross-domain canvas — Firmware Run, Bridge, Relay-in, call button-clock-ledger, Relay-out,
    Frontend emit — as ONE SolutionDefinition definition dict (category='cross-domain' set where this is wrapped into
    a row, hwnocode_seed.py, same as uno-temp-split)."""
    n = GB.node
    r = BC_ROUTE
    run = n('firmware-run', 'FirmwareRunState', {'firmware_solution': BC_FIRMWARE_SOLUTION, 'board_variable': BOARD,
                                                 'mode': r['mode'], 'route_taken': 'planned',
                                                 'route_why': 'FirmwareSolution %r not built yet (ucd-0e2b)' % BC_FIRMWARE_SOLUTION},
            outs=[['uno-button-clock-bridge']])
    hwi = n('uno-button-clock-bridge', 'HardwareInterface', {'binding': BC_BINDING, 'object_class': BC_OBJECT_CLASS,
                                                             'object_name': BC_OBJECT_NAME, 'bridge_name': BC_BRIDGE,
                                                             'board_instance': r['board_instance'], 'port': r['port'],
                                                             'interface_kind': r['interface_kind']},
            outs=[['relay-in']])
    relay_in = n('relay-in', 'BackendStateChange', {'displayName': 'Relay in: ButtonClockState seq advanced',
                                                     'modelName': BC_OBJECT_CLASS, 'fieldName': 'seq', 'changeType': 'update',
                                                     'description': 'fires on every frame the bridge applies to the row — '
                                                                    'bridging only, turns it into a backend event'},
                 outs=[['call-button-clock-ledger']])
    call = GB.invoke('call-button-clock-ledger', BC_LEDGER_SOLUTION,
                      mappings=[{'param': 'board_instance', 'valueSource': GB.var_src('instance.name')},
                                {'param': 'object', 'valueSource': GB.var_src('instance.name')},
                                {'param': 'solution', 'valueSource': GB.lit_src(name)}],
                      bindings=[{'output': 'presses_per_min', 'contextVar': 'presses_per_min'},
                                {'output': 'invariant_ok', 'contextVar': 'invariant_ok'},
                                {'output': 'invariant_why', 'contextVar': 'invariant_why'},
                                {'output': 'events_seen', 'contextVar': 'events_seen'},
                                {'output': 'dropped_events_total', 'contextVar': 'dropped_events_total'},
                                {'output': 'last_sync_generation', 'contextVar': 'last_sync_generation'},
                                {'output': 'drift_ms', 'contextVar': 'drift_ms'}],
                      nxt='relay-out')
    relay_out = n('relay-out', 'BackendStateChange', {'displayName': 'Relay out: SET_TIME / SET_LED',
                                                      'modelName': BC_OBJECT_CLASS, 'fieldName': 'clock_synced', 'changeType': 'update',
                                                      'description': 'bridging only: set_epoch_s/set_ms/set_sync_generation (SET_TIME, '
                                                                     'at attach + every sync_every_s=%ds, server clock) and set_led '
                                                                     '(on demand) ride the existing presence-masked command PUT down '
                                                                     'to the device — the same path uno-temp-split\'s led_on uses' % BC_KNOBS['sync_every_s']},
                   outs=[['frontend-emit']])
    emit = n('frontend-emit', 'EmitFrontendEvent', {'targetSolutionName': BC_DISPLAY,
                                                    'eventPayload': {'board_instance': BC_OBJECT_NAME}}, outs=[[]])
    return _bc_lay_out(GB.solution(name, run, hwi, relay_in, call, relay_out, emit))


def button_clock_backend_definition(name=BC_BACKEND_SOLUTION):
    """The EXECUTABLE subset of the canvas above: only the engine-runnable states (relay-in -> call -> relay-out ->
    frontend-emit — FirmwareRunState/HardwareInterface are descriptive-only, no SolutionExecutionEngine handler exists
    for them, same fact uno-temp-split's own hn-split `backend_partition` relies on). Deep-copied straight OUT of the
    already-laid-out full canvas (`button_clock_definition`) — the SAME shape `placement.backend_partition` builds for
    uno-temp-split — rather than hand-built fresh, so these states keep their canvas fields (position/shape/size/
    detail_ref) too; connectors to a dropped state are cut, exactly as backend_partition does."""
    keep = {'relay-in', 'call-button-clock-ledger', 'relay-out', 'frontend-emit'}
    full = button_clock_definition(BC_SOLUTION)
    states = []
    for s in full['stateInstances']:
        if s.get('stateName') not in keep:
            continue
        c = json.loads(json.dumps(s))
        for slot in c.get('slots') or []:
            slot['connectors'] = [x for x in slot.get('connectors') or [] if x.get('targetStateName') in keep]
        states.append(c)
    return {'solutionName': name, 'stateInstances': [dict(s, index=i) for i, s in enumerate(states)]}


def button_clock_contract():
    return {'description': 'uno-button-clock (ucd-1, Cross-Domain): Firmware Run (uno-button-clock, planned) → Bridge '
                           '(uno-button-clock-bridge) → Relay in → call button-clock-ledger → Relay out (SET_TIME/SET_LED) '
                           '→ Frontend emit (uno-core-demo). Bridging/relay only (D-fs-3) — presses_per_min + the sense/'
                           'press/LED invariant run inside button-clock-ledger, called out to.',
            'inputs': [{'name': 'instance.name', 'required': True, 'description': 'the ButtonClockState row (the trigger payload)'}],
            'returns': [], 'executionRights': 'definer'}
