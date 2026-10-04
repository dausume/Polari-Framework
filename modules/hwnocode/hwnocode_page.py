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
from hwnocode.custom.solutions import SOLUTION, GRAPH, DISPLAY


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

SEED_HWNOCODE_PAGE_DISPLAYS = [
    _page(DISPLAY, DISPLAY,
          'Hardware solutions — one no-code graph across a board, the bridge, the backend and this screen (hn arc): where each node '
          'runs and why, the board half rendered by cmod-glue (byte-identical firmware), the backend half run per frame, the chart '
          '(`pol hwnocode place | render | build | suggest uno-temp-split`). Today\'s one solution targets arduino-uno-r3 — see '
          '/display/boards for which boards are usable at all; the board half\'s C graph is the SAME CGraph shown at /display/c-atoms, '
          'and installing it onto real hardware is /display/firmware-installer.',
          'HardwareSolution', [
              _row(0, [_table('hwnocode-solutions', 0, 12, 'Hardware solutions — the subgraph (a cmod CGraph), the hw-interface (the split '
                              'point), the firmware_runtime knob (yours; hn-0 renders bare-c and refuses the rest with the reason), the '
                              'placement summary, the split and the glue shas, the proof', 'HardwareSolution',
                              description='What this is for: ONE no-code solution end to end — a drawing that spans a board, the bridge, the '
                                          'server and this screen. One row = one HardwareSolution. Columns: cgraph (the cmod CGraph that IS '
                                          'the hardware half), interface (the HardwareInterfaceBinding where it crosses device <-> backend), '
                                          'firmware_runtime/runtime_status (the knob — yours to pick; bare-c works today, others refuse with '
                                          'why), placement_summary/node_count (derived: how many nodes run where), split_sha256/'
                                          'glue_files_sha256/glue_hex_sha256 (the board half\'s build, proven byte-identical by cmod), proof '
                                          '(the twin-equivalence verdict in words).',
                              columns='name,title,variant_kind,status,cgraph,interface,board_definition,board_instance,firmware_runtime,'
                                      'runtime_status,placement_summary,node_count,refused,split_sha256,glue_files_sha256,glue_hex_sha256,'
                                      'backend_solution,displays,proof,costs',
                              column_formats='name:ref:HardwareSolution,cgraph:ref:CGraph,interface:ref:HardwareInterfaceBinding')],
                   min_height=160),
              _row(1, [_graph_panel('hwnocode-temp-chart', 0, 12, 'uno-temp-split — temp_c and its moving average (the backend half)',
                                    GRAPH, '/api/hwnocode/solutions/%s/chart' % SOLUTION,
                                    description='What this is for: the demonstrable — the UNO\'s own TMP36 reading (10 Hz, through the bridge) '
                                                'plotted against the backend\'s moving average of the same signal, so the no-code split is '
                                                'something you can SEE, not just a table of node placements. One line per series: temp_c (raw '
                                                'firmware reading), temp_avg (the backend\'s AnalysisCall over the trigger\'s window).')],
                   min_height=380),
              _row(2, [_table('hwnocode-derived', 0, 12, 'Derived temperature state — the backend half\'s moving average and the '
                              'threshold flag (ConditionalChain → StateChangeCommit), per SimRigState row', 'SimRigTempDerived',
                              description='What this is for: the BACKEND half\'s own running state for this solution — what the chart above '
                                          'is plotting, as rows. One row = one SimRigTempDerived (per rig). Columns: temp_avg (the moving '
                                          'average over `window` samples), over_threshold/threshold_c (the flag a ConditionalChain -> '
                                          'StateChangeCommit watches), last_temp_c/last_uptime_ms (the latest frame it saw).',
                              columns='name,temp_avg,over_threshold,threshold_c,window,samples,last_temp_c,last_uptime_ms,updated_at,solution')],
                   min_height=120),
              _row(3, [_table('hwnocode-placement', 0, 12, 'Placement — every node of every solution: board / twin (C on the device), '
                              'bridge (the split point), backend (the Python engine), browser (displays); a Python node on the device '
                              'side is refused, named', 'HardwareNodePlacement',
                              description='What this is for: WHERE every node of every solution actually runs, and why — placement is '
                                          'derived, never typed in. One row = one node\'s placement. Columns: layer/placement (board/twin | '
                                          'bridge | backend | browser), kind/language (what the node is and what it compiles to there), '
                                          'refused/why (a node that cannot run where it was drawn — e.g. Python on the device — named, not '
                                          'silently moved).',
                              columns='solution,layer,node,kind,placement,language,refused,why',
                              column_formats='solution:ref:HardwareSolution')], min_height=320),
          ]),
]
