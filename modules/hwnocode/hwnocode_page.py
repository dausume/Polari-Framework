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


def _graph_panel(item_id, index, segments, title, graph_name, data_path):
    return {'id': item_id, 'index': index, 'type': 'component', 'rowSegmentsUsed': segments, 'gridColumnStart': None, 'title': title,
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
          '(`pol hwnocode place | render | build | suggest uno-temp-split`)',
          'HardwareSolution', [
              _row(0, [_table('hwnocode-solutions', 0, 12, 'Hardware solutions — the subgraph (a cmod CGraph), the hw-interface (the split '
                              'point), the firmware_runtime knob (yours; hn-0 renders bare-c and refuses the rest with the reason), the '
                              'placement summary, the split and the glue shas, the proof', 'HardwareSolution',
                              columns='name,title,variant_kind,status,cgraph,interface,board_definition,board_instance,firmware_runtime,'
                                      'runtime_status,placement_summary,node_count,refused,split_sha256,glue_files_sha256,glue_hex_sha256,'
                                      'backend_solution,displays,proof,costs',
                              column_formats='name:ref:HardwareSolution,cgraph:ref:CGraph,interface:ref:HardwareInterfaceBinding')],
                   min_height=160),
              _row(1, [_graph_panel('hwnocode-temp-chart', 0, 12, 'uno-temp-split — temp_c and its moving average (the backend half)',
                                    GRAPH, '/api/hwnocode/solutions/%s/chart' % SOLUTION)], min_height=380),
              _row(2, [_table('hwnocode-derived', 0, 12, 'Derived temperature state — the backend half\'s moving average and the '
                              'threshold flag (ConditionalChain → StateChangeCommit), per SimRigState row', 'SimRigTempDerived',
                              columns='name,temp_avg,over_threshold,threshold_c,window,samples,last_temp_c,last_uptime_ms,updated_at,solution')],
                   min_height=120),
              _row(3, [_table('hwnocode-placement', 0, 12, 'Placement — every node of every solution: board / twin (C on the device), '
                              'bridge (the split point), backend (the Python engine), browser (displays); a Python node on the device '
                              'side is refused, named', 'HardwareNodePlacement',
                              columns='solution,layer,node,kind,placement,language,refused,why',
                              column_formats='solution:ref:HardwareSolution')], min_height=320),
          ]),
]
