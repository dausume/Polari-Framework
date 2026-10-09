"""
@module hwnocode.hwnocode_page

/display/hardware-solutions — CONFIGURED tables + ONE configured graph, no new component, no raw JSON (HARDWARE_NOCODE_PLAN.md §1c,
§4 h): the HardwareSolutions (subgraph, interface, the runtime knob and why, the placement summary, the split + glue shas, the
proof), the placement of every node (where it runs and why — refusals named), the derived temperature state (the backend half's
moving average + threshold flag), and the chart of temp_c and its moving average — a GraphDefinition row rendered by the generic
`named-graph-panel` (the graphs design; sci-xy-chart is the lower-level data-in component and is not a display component), its
data from GET /api/hwnocode/solutions/uno-temp-split/chart ({ok, rows}).
"""
import json

from polariApiServer.module_pages_seed import _page, _row, _table
from hwnocode.custom.solutions import SOLUTION, GRAPH, DISPLAY, CGRAPH, BC_SOLUTION, BC_DISPLAY


def _graph_panel(item_id, index, segments, title, graph_name, data_path, description=''):
    return {'id': item_id, 'index': index, 'type': 'component', 'rowSegmentsUsed': segments, 'gridColumnStart': None, 'title': title,
            'description': description,
            'visible': True, 'collapsed': False, 'cssClass': '',
            'componentProps': {'componentName': 'named-graph-panel', 'inputs': {'graphName': graph_name, 'dataPath': data_path}},
            'item': None, 'nestedRows': []}


def _graph_config():
    """One GraphConfigData blob — the frontend model's keys exactly (climate_page precedent): WIDE rows, x = uptime (s), two y
    dimensions; colours given so no series label is ever read as a field name (the long-form gotcha)."""
    return {'renderStyle': 'lineY', 'xDimension': 'uptime_s', 'yDimensions': ['temp_c', 'temp_avg'],
            'seriesColors': ['#e65100', '#1565c0'],
            'options': {'width': 800, 'height': 320, 'marginTop': 20, 'marginRight': 30, 'marginBottom': 40, 'marginLeft': 60,
                        'showLegend': True, 'showGrid': True, 'xLabel': 'firmware uptime (s)', 'yLabel': 'temperature (°C)'},
            'aggregation': {'enabled': False, 'strategy': 'average'}}


SEED_HWNOCODE_GRAPHS = [{
    'name': GRAPH, 'source_class': 'SimRigTempSample',
    'description': ('uno-temp-split: temp_c as the UNO firmware reported it (TMP36 on A0, 10 Hz frames through the bridge) and the '
                    'moving average the backend half computed per frame (AnalysisCall hwnocode-temp-derive; window = the trigger\'s '
                    'knob). The threshold flag is SimRigTempDerived.over_threshold.'),
    'definition': json.dumps({'graphConfig': _graph_config()})}]

# ucd-1: uno-button-clock's own sci-xy-chart — x = uptime_ms (the device's own monotonic clock, always valid even
# unsynced), y = three RUNNING CUMULATIVE counters (presses, D3-sensed rises, D3-sensed falls) over time, the plan's
# own accepted alternative to a numeric-lane encoding (UNO_CORE_DEMO_PLAN.md §3). Data: GET /api/hwnocode/button-clock/chart.
BC_GRAPH = 'hwnocode-uno-button-clock-events'


def _bc_graph_config():
    return {'renderStyle': 'lineY', 'xDimension': 'uptime_s', 'yDimensions': ['presses_cum', 'rises_cum', 'falls_cum'],
            'seriesColors': ['#e65100', '#1565c0', '#6a1b9a'],
            'options': {'width': 800, 'height': 320, 'marginTop': 20, 'marginRight': 30, 'marginBottom': 40, 'marginLeft': 60,
                        'showLegend': True, 'showGrid': True, 'xLabel': 'firmware uptime (s)', 'yLabel': 'events, cumulative'},
            'aggregation': {'enabled': False, 'strategy': 'average'}}


SEED_HWNOCODE_GRAPHS += [{
    'name': BC_GRAPH, 'source_class': 'ButtonClockEvent',
    'description': ('uno-button-clock (ucd-1): every ButtonClockEvent (press, sense_rise, sense_fall, led_on/off, sync) plotted as '
                    'three running totals against the device\'s own uptime — presses_cum (D2, debounced), rises_cum/falls_cum (D3, '
                    'the independent witness of the LED line). The invariant button-clock-ledger checks is presses_cum == '
                    'rises_cum + falls_cum at any point in time; a divergence is visible as the lines drifting apart.'),
    'definition': json.dumps({'graphConfig': _bc_graph_config()})}]

def _canvas_solution(item_id, index, segments, title, graph, solution, description=''):
    """demo-4b: the canvas opened on the SOLUTION itself (its real SolutionDefinition — sim-rig/uno-digital-twin/backend
    nodes), not a synthetic one-node wrapper, so every runtime (c-device/java-bridge/python-backend) is visible as a lane."""
    return {'id': item_id, 'index': index, 'type': 'component', 'rowSegmentsUsed': segments, 'gridColumnStart': None,
            'title': title, 'description': description, 'visible': True, 'collapsed': False, 'cssClass': '',
            'componentProps': {'componentName': 'c-graph-canvas-panel', 'inputs': {'graph': graph, 'solution': solution}},
            'item': None, 'nestedRows': []}


SEED_HWNOCODE_PAGE_DISPLAYS = [
    _page(DISPLAY, DISPLAY,
          'Hardware solutions — one no-code graph across a board, the bridge, the backend and this screen (hn arc): where each node '
          'runs and why, the board half rendered by cmod-glue (byte-identical firmware), the backend half run per frame, the chart '
          '(`pol hwnocode place | render | build | suggest uno-temp-split`). Today\'s one solution targets arduino-uno-r3 — see '
          '/display/boards for which boards are usable at all; the board half\'s C graph is the SAME CGraph shown at /display/c-atoms, '
          'and installing it onto real hardware is /display/firmware-installer. demo-4b (his ruling): C-on-hardware and the Java/JavaFX '
          'native bridge are each their OWN runtime (see the Runtime table below) — the canvas opens FIRST, below, grouping this '
          'solution\'s nodes into one lane per runtime present.',
          'HardwareSolution', [
              _row(0, [_canvas_solution('hwnocode-canvas', 0, 12, '%s opened on the no-code canvas — ALL its runtimes as lanes '
                                        '(demonstrable first)' % SOLUTION, CGRAPH, SOLUTION,
                               description="What this is for: THE DEMONSTRABLE, first on the page — this solution's REAL drawing (sim-rig, "
                                           'the hw-interface split point, the backend chain), coloured and grouped into one lane per '
                                           'runtime (c-device: the sim-rig subgraph; java-bridge: uno-digital-twin, the split point; '
                                           'python-backend: the moving-average chain). Expand the Hardware Subgraph node in place to see its C atoms, still '
                                           'in the c-device lane — never a second canvas, the SAME `c-graph-canvas-panel` /display/c-canvas '
                                           "uses. The REVERSE link ('used by') is shown on /display/c-atoms and /display/c-canvas.")],
                   min_height=640),
              _row(1, [_table('hwnocode-capabilities', 0, 12, 'Capabilities — hw priorities P1: the GOAL each group of tasks across '
                              'runtimes achieves over this same graph ("data is retrieved from a temp sensor and gets sent back over USB '
                              'to the OS"; "the OS turns the board\'s LED on and off on command"), its status DERIVED from its acceptance '
                              'proof', 'CapabilityDefinition',
                              description='What this is for: THE THREAD that runs through this solution\'s own board/bridge/backend split '
                                          '— one row a person reads to ask "is this goal actually working" without opening either canvas '
                                          'separately (HARDWARE_DEV_PRIORITIES.md §1). One row = one CapabilityDefinition. Columns: '
                                          'goal (the one-sentence claim, his words), status (planned | proven-on-twin | proven-on-hardware | '
                                          'failing — DERIVED from the latest ScenarioRun of acceptance_scenario, never hand-set), last_proof, '
                                          'tasks_by_runtime_json (c-device/java-bridge/python-backend/typescript-browser task refs).',
                              columns='name,title,goal,status,last_proof,acceptance_scenario,required_targets,exposes_fields,'
                                      'tasks_by_runtime_json',
                              column_formats='graph:ref:CGraph,acceptance_scenario:ref:Scenario')], min_height=200),
              _row(2, [_table('hwnocode-solutions', 0, 12, 'Hardware solutions — the subgraph (a cmod CGraph), the hw-interface (the split '
                              'point), the firmware_runtime knob (yours; hn-0 renders bare-c and refuses the rest with the reason), the '
                              'placement summary, the split and the glue shas, the proof', 'HardwareSolution',
                              description='What this is for: ONE no-code solution end to end — a drawing that spans a board, the bridge, the '
                                          'server and this screen. One row = one HardwareSolution. Columns: cgraph (the cmod CGraph that IS '
                                          'the hardware half), interface (the HardwareInterfaceBinding where it crosses device <-> backend), '
                                          'firmware_runtime/runtime_status (the knob — yours to pick; bare-c works today, others refuse with '
                                          'why), hardware_mode/route_report (the configuration knob — HWNOCODE_HARDWARE_MODE env var, '
                                          'digital-twin | hardware — and which route the hw-interface actually took, derived; digital-twin '
                                          'attaches to the twin\'s pty, hardware attaches to the detected board\'s serial port or refuses to '
                                          'the twin\'s pty, named, if nothing is detected), placement_summary/node_count (derived: how many '
                                          'nodes run where), split_sha256/glue_files_sha256/glue_hex_sha256 (the board half\'s build, proven '
                                          'byte-identical by cmod), proof (the twin-equivalence verdict in words).',
                              columns='name,title,variant_kind,status,cgraph,interface,board_definition,board_instance,firmware_runtime,'
                                      'runtime_status,hardware_mode,route_report,placement_summary,node_count,refused,split_sha256,'
                                      'glue_files_sha256,glue_hex_sha256,backend_solution,displays,proof,costs',
                              column_formats='name:ref:HardwareSolution,cgraph:ref:CGraph,interface:ref:HardwareInterfaceBinding')],
                   min_height=160),
              _row(3, [_graph_panel('hwnocode-temp-chart', 0, 12, 'uno-temp-split — temp_c and its moving average (the backend half)',
                                    GRAPH, '/api/hwnocode/solutions/%s/chart' % SOLUTION,
                                    description='What this is for: the demonstrable — the UNO\'s own TMP36 reading (10 Hz, through the bridge) '
                                                'plotted against the backend\'s moving average of the same signal, so the no-code split is '
                                                'something you can SEE, not just a table of node placements. One line per series: temp_c (raw '
                                                'firmware reading), temp_avg (the backend\'s AnalysisCall over the trigger\'s window). This '
                                                'IS the typescript-browser runtime\'s own view of the data (the browser lane has no canvas '
                                                'node today — it is this chart, read the same rows).')],
                   min_height=380),
              _row(4, [_table('hwnocode-derived', 0, 12, 'Derived temperature state — the backend half\'s moving average and the '
                              'threshold flag (ConditionalChain → StateChangeCommit), per SimRigState row', 'SimRigTempDerived',
                              description='What this is for: the BACKEND half\'s own running state for this solution — what the chart above '
                                          'is plotting, as rows. One row = one SimRigTempDerived (per rig). Columns: temp_avg (the moving '
                                          'average over `window` samples), over_threshold/threshold_c (the flag a ConditionalChain -> '
                                          'StateChangeCommit watches), last_temp_c/last_uptime_ms (the latest frame it saw).',
                              columns='name,temp_avg,over_threshold,threshold_c,window,samples,last_temp_c,last_uptime_ms,updated_at,solution')],
                   min_height=120),
              _row(5, [_table('hwnocode-placement', 0, 12, 'Placement / Nodes by runtime — WHAT EACH STATE DOES (the `purpose` column, '
                              'solution-layer rows) and where it runs: board / twin (C on the device), bridge (the split point), backend '
                              '(the Python engine), browser (displays); a Python node on the device side is refused, named', 'HardwareNodePlacement',
                              description='What this is for: WHERE every node of every solution actually runs, and why — placement is '
                                          'derived, never typed in — AND, for this solution\'s own 8 canvas states (layer=solution), what '
                                          'each one actually does in plain words (his question: "it is not clear what the backend state '
                                          'change is for... not sure what the analysis call is"): sim-rig is the firmware reading the '
                                          'TMP36; uno-digital-twin is the bridge (the split point); on-temp is the backend event a frame '
                                          'arrived; moving-avg is the backend analysis (the moving average); over?/flag-on/flag-off are the '
                                          'threshold check and the LED command; commit sends that command back through the bridge. One row '
                                          '= one node\'s placement. Columns: purpose (plain words, solution-layer rows only), layer/placement '
                                          '(board/twin | bridge | backend | browser), kind/language (what the node is and what it compiles '
                                          'to there), runtime (demo-4b: the Runtime row this node resolved to — c-device/java-bridge/'
                                          'python-backend/typescript-browser; blank when refused), refused/why (a node that cannot run where '
                                          'it was drawn — e.g. Python on the device — named, not silently moved; for uno-digital-twin, why '
                                          'also carries the HARDWARE_MODE route report).',
                              columns='solution,layer,node,purpose,kind,placement,runtime,language,refused,why',
                              column_formats='solution:ref:HardwareSolution')], min_height=320),
              _row(6, [_table('hwnocode-runtimes', 0, 12, 'Runtimes — the six execution environments a no-code node can be placed into '
                              '(his ruling: C-on-hardware and the Java/JavaFX native bridge are each their own runtime)', 'Runtime',
                              description='What this is for: the CATALOG every node\'s `runtime` column above names one row of. One row '
                                          '= one runtime. Columns: kind/language (what it is and what it runs), executes_on (the instance '
                                          'kind or device), entered_via (process | browser | firmware image | JVM), description (plain '
                                          'words — his C-hardware / Java-JavaFX-native-bridge split).',
                              columns='name,kind,language,executes_on,entered_via,description')], min_height=220),
          ]),
]

# =============================================================================================================
# /display/uno-core-demo (ucd-1, UNO_CORE_DEMO_PLAN.md §3): the UNO core demo's OWN page — CONFIGURED tables + ONE
# sci-xy-chart, nothing custom (his rule: no raw JSON on screens, no api-json-panel). Links back to /display/firmware
# (the Firmware Run's detail — the canvas + export table) and /display/hardware-chain (the Bridge/wire-contract detail)
# are named in the description rows below (the existing idiom every other hwnocode page uses — prose, not a component).
# =============================================================================================================
SEED_HWNOCODE_PAGE_DISPLAYS += [
    _page(BC_DISPLAY, BC_DISPLAY,
          'The UNO core demo (ucd arc): a pushbutton on D2 toggles an LED on D6; a jumper from D6 to D3 lets the firmware '
          'independently WITNESS its own LED line switching (sense_rises/sense_falls); a software wall clock is kept on the '
          'device and synced from the host (SET_TIME) at attach and periodically. The board\'s latest state and every '
          'button/LED/sense/sync edge arrive as rows (ButtonClockState upserted, ButtonClockEvent appended, bounded by a '
          'retention knob); button-clock-ledger computes presses per minute and checks that sense_rises + sense_falls == '
          'button_presses and led_on == (sense_rises > sense_falls) — the proof this demo exists to show. The Cross-Domain '
          'canvas composing all of this (Firmware Run → Bridge → Relay in → call button-clock-ledger → Relay out → this '
          'screen) opens at /display/firmware?solution=%s; the pin-level register chain behind the Bridge is at '
          '/display/hardware-chain.' % BC_SOLUTION,
          'ButtonClockState', [
              _row(0, [_table('ucd-state', 0, 12, 'Latest board state — one row per bound board instance, the wire\'s own '
                              'telemetry (ButtonClockState is UPSERTED by the bridge, never appended)', 'ButtonClockState',
                              description='What this is for: the board AS IT IS RIGHT NOW. One row = one board instance. Columns: '
                                          'seq/boot_session (the wire\'s own frame + reset counters), uptime_ms (monotonic, always '
                                          'valid), epoch_s/clock_synced/sync_generation/drift_ms (the SET_TIME-synced wall clock and '
                                          'how well it is synced), button_presses/led_on/sense_rises/sense_falls (the demo\'s own '
                                          'counts — button-clock-ledger\'s invariant checks these), dropped_events (the device\'s own '
                                          'queue-overflow count), status (idle | commanded | synced | snapshot).',
                              columns='name,seq,boot_session,uptime_ms,epoch_s,clock_synced,sync_generation,drift_ms,button_presses,'
                                      'led_on,sense_rises,sense_falls,dropped_events,status')], min_height=160),
              _row(1, [_table('ucd-derived', 0, 12, 'The ledger — presses/min and the sense/press/LED invariant, computed by '
                              'button-clock-ledger per frame', 'ButtonClockDerived',
                              description='What this is for: THE PROOF, as a row — does the board\'s own count of presses agree '
                                          'with the independent D3 witness, and how fast is the button actually being pressed. One '
                                          'row = one board instance. Columns: presses_per_min (over the last minute of the device\'s '
                                          'own clock), invariant_ok/invariant_why (the verdict, ALWAYS said in plain words, not only '
                                          'on a break), events_seen (ButtonClockEvent rows at computation time, before any prune), '
                                          'dropped_events_total/last_sync_generation/drift_ms (mirrored from the wire for one-stop '
                                          'reading), received_at/computed_at (the SERVER\'s own clock — never a device/host fact).',
                              columns='name,board_instance,presses_per_min,invariant_ok,invariant_why,events_seen,'
                                      'dropped_events_total,last_sync_generation,drift_ms,received_at,computed_at')], min_height=160),
              _row(2, [_graph_panel('ucd-chart', 0, 12, 'Button presses and sensed LED edges over time (cumulative)',
                                    BC_GRAPH, '/api/hwnocode/button-clock/chart',
                                    description='What this is for: the demonstrable — every press (D2) and every independently '
                                                'sensed LED edge (D3) as running totals against the firmware\'s own uptime, so the '
                                                'invariant is something you can SEE: presses_cum should always equal rises_cum + '
                                                'falls_cum. Three series: presses_cum, rises_cum, falls_cum.')], min_height=380),
              _row(3, [_table('ucd-events', 0, 12, 'Event ledger — the last 200 ButtonClockEvent rows (press · led_on · led_off · '
                              'sense_rise · sense_fall · sync), oldest first', 'ButtonClockEvent', max_rows=200,
                              description='What this is for: the RAW edge-by-edge ledger the chart above and the invariant both '
                                          'read — one row = one transition, never converged/reused (ButtonClockEvent\'s own rule). '
                                          'Columns: seq/boot_session (this event stream\'s own counters, independent of '
                                          'ButtonClockState\'s), kind, uptime_ms/epoch_s/ms (the device\'s clock at the moment it '
                                          'happened). Bounded by a retention knob (default 10 000, oldest pruned first) — a pure '
                                          'function plus a door, never run on the frame-push path (UNO_CORE_DEMO_PLAN.md §5 D-ucd-5).',
                              columns='name,seq,kind,uptime_ms,epoch_s,ms,boot_session')], min_height=320),
          ]),
]
