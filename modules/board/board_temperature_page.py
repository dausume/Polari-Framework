"""
@module board.board_temperature_page

tmp-1 / tmp-2 (AI-Notes/plans/TEMPERATURE_PLAN.md): the Board Details page's two TEMPERATURE tabs - configured tables and named graphs only,
every one reading the door GET /api/board/details/{kind}/{definition}/{part} (board.custom.board_temperature) or posting to the temperature doors
(pcb.pcb_temperature_api). board.board_details_page puts them on the page.
"""
import json

from polariApiServer.module_pages_seed import _row, _tab, _table

DOOR = '/api/board/details/{scope:board}'
TREND_GRAPH = 'pcb-temperature-trend'
OVERLAY_GRAPH = 'pcb-temperature-overlay'
_TEMP_INPUT = '/api/pcb/{board}/temperature-inputs/{ref}/{quantity}'


def _graph_config(x_label, y_label):
    return {'renderStyle': 'lineY', 'xDimension': 'x', 'yDimensions': ['y'], 'seriesDimension': 'series', 'seriesColors': [],
            'options': {'width': 900, 'height': 360, 'marginTop': 20, 'marginRight': 30, 'marginBottom': 40, 'marginLeft': 70, 'showLegend': True,
                        'showGrid': True, 'xLabel': x_label, 'yLabel': y_label},
            'aggregation': {'enabled': False, 'strategy': 'average'}}


SEED_TEMPERATURE_GRAPHS = [{
    'name': TREND_GRAPH, 'source_class': 'SpiceRun',
    'description': ('A PCB\'s circuit across temperature (tmp-1): each net\'s peak - the highest value of a transient, the largest |V| of an AC '
                    'sweep - at every temperature of the newest sweep. Data: GET /api/board/details/layers/{board}/temperature-trend.'),
    'definition': json.dumps({'graphConfig': _graph_config('the board\'s temperature (C)', 'the net\'s peak (V, or |V| for an AC sweep)')})}, {
    'name': OVERLAY_GRAPH, 'source_class': 'SpiceVector',
    'description': ('The same circuit at each temperature of the newest sweep, drawn over each other: every node vector against the run\'s scale, '
                    'one line per vector per temperature (values as ngspice returned them, thinned by a stride). Data: '
                    'GET /api/board/details/layers/{board}/temperature-overlay.'),
    'definition': json.dumps({'graphConfig': _graph_config('the run\'s scale: time (s) or frequency (Hz)', 'V, or |V| for an AC sweep')})}]


def _chart(item_id, title, what, graph, part):
    return {'id': item_id, 'index': 0, 'type': 'component', 'rowSegmentsUsed': 12, 'gridColumnStart': None, 'title': title, 'description': what,
            'visible': True, 'collapsed': False, 'cssClass': '',
            'componentProps': {'componentName': 'named-graph-panel', 'inputs': {'graphName': graph, 'dataPath': '%s/%s?rev=r{scope:rev}' % (DOOR, part)}},
            'item': None, 'nestedRows': []}


def temperature_tab():
    """tmp-1: the board's (background) temperature - one run at a temperature, a sweep over a rated range, what responds, each part's ratings."""
    return _tab('temperature', 'Temperature', [
        _row(0, [_table('bd-temp-at', 0, 5, 'Run at one temperature', '', data_path='%s/temperature-at?rev=r{scope:rev}' % DOOR,
                        empty_text='Only a PCB from KiCad has a circuit to run.', edit_fields='temp_c', edit_signed_field='signed',
                        edit_action={'method': 'POST', 'path': '/api/pcb/{board}/simulate-at', 'body_template': {'temp_c': '{value}'}},
                        description='What this is for: the whole board at one temperature - the room, a cold start, a hot box. Type a temperature in C '
                                    'and press Enter: the circuit runs once with every part at it (a SPICE .temp), and the run is kept on the Simulation '
                                    'tab. Without a temperature ngspice runs at 27 C.', columns='temp_c,last_run,how', max_height=140),
                 _table('bd-temp-grades', 0, 7, 'Sweep a rated range', '', data_path='%s/temperature-grades' % DOOR,
                        row_action={'label': 'Sweep', 'method': 'POST', 'path': '/api/pcb/{board}/temperature-sweep/{grade}'},
                        description='What this is for: checking the circuit across the range its parts are rated for. Sweep runs it at the low end, '
                                    '25 C and the high end. Commercial and industrial are vendors\' conventions; the automotive grades are AEC-Q100\'s.',
                        columns='grade,t_min_c,t_max_c,temperatures,basis', max_height=260)], min_height=200),
        _row(1, [_table('bd-temp-reach', 0, 12, 'What temperature changes in this circuit', '', data_path='%s/temperature-reach?rev=r{scope:rev}' % DOOR,
                        empty_text='Only a PCB from KiCad has a circuit.',
                        description='What this is for: knowing which parts actually respond before trusting a sweep. One row per part of the circuit: '
                                    'acts says whether temperature changes it, through what - a diode or transistor through its own model\'s temperature '
                                    'terms (or ngspice\'s defaults), a resistor / capacitor / inductor only through a temperature coefficient (none given = '
                                    'an ideal part that never changes); own_temperature says whether the part can be given a temperature of its own (the '
                                    'next tab).', columns='ref,kind,model,acts,through,own_temperature', max_height=320)], min_height=200),
        _row(2, [_table('bd-temp-sweep', 0, 12, 'Each net across the newest sweep', '', data_path='%s/temperature-sweep?rev=r{scope:rev}' % DOOR,
                        empty_text='Run a sweep above.',
                        description='What this is for: how each net\'s voltage moves with temperature. One row per net per temperature: its lowest, '
                                    'highest and last value (a transient) or peak |V| and where (an AC sweep), and how much the peak moved from the run '
                                    'at 25 C - in total and per kelvin. A temperature that did not run says why.',
                        columns='net,temp_c,unit,min,max,final,at,peak_change,peak_change_per_k,basis', max_height=360)], min_height=220),
        _row(3, [_chart('bd-temp-trend', 'Each net\'s peak against temperature', 'One line per net: its peak at every temperature of the sweep.',
                        TREND_GRAPH, 'temperature-trend')], min_height=420),
        _row(4, [_chart('bd-temp-overlay', 'The circuit at each temperature, overlaid', 'Every node vector at every temperature of the sweep - '
                        'one line per vector per temperature.', OVERLAY_GRAPH, 'temperature-overlay')], min_height=420),
        _row(5, [_table('bd-temp-parts', 0, 6, 'Parts - click one to give its rated range or coefficients', '',
                        data_path='%s/temperature-parts?rev=r{scope:rev}' % DOOR, select_field='ref', select_scope='tpart', selected_value='{scope:tpart}',
                        empty_text='Only a PCB from KiCad has parts with simulation models.',
                        description='What this is for: the temperatures each part is rated for and how much its value drifts, from its datasheet. '
                                    'rated_range is its operating range; tc1 / tc2 are a resistor\'s, capacitor\'s or inductor\'s temperature '
                                    'coefficients (ppm/K, ppm/K2); coefficient_use says what the circuit does with them.',
                        columns='ref,value,rated_range,tc1_ppm_k,tc2_ppm_k2,coefficient_use,source', max_height=360),
                 _table('bd-temp-inputs', 0, 6, 'Numbers for part {scope:tpart} - type a value and press Enter', '',
                        data_path='%s/temperature-inputs?ref={scope:tpart}&rev=r{scope:rev}' % DOOR, empty_text='Click a part on the left.',
                        edit_fields='value', edit_signed_field='signed',
                        edit_action={'method': 'PUT', 'path': _TEMP_INPUT, 'body_template': {'value': '{value}'}},
                        row_action={'label': 'Clear', 'method': 'DELETE', 'path': _TEMP_INPUT, 'show_when_field': 'given'},
                        description='What this is for: telling Polari what the datasheet says. Operating range in C (negative values allowed); '
                                    'tc1 in ppm/K and tc2 in ppm/K2 (value(T) = value(27 C) x (1 + tc1 dT + tc2 dT^2) - ngspice\'s form). Clear puts a '
                                    'number back to not given. To keep the document and page it came from, post it with its citation '
                                    '(POST /api/pcb/<board>/temperature-behaviours/<ref>).',
                        columns='quantity,value,unit,meaning,given,origin', max_height=360)], min_height=240),
        _row(6, [_table('bd-temp-ratings', 0, 12, 'Parts against their rated range', '', data_path='%s/temperature-ratings?rev=r{scope:rev}' % DOOR,
                        empty_text='Give a part its rated range and run a sweep.',
                        description='What this is for: catching a part simulated outside the temperatures it is made for. One row per part with a '
                                    'rated range: the temperatures it was simulated at, the margin at each end (negative = outside) and the verdict.',
                        columns='ref,value,rated_min_c,rated_max_c,simulated_c,low_margin_c,high_margin_c,verdict,basis', max_height=300)],
             min_height=180)],
        'Temperature: the circuit with the whole board at a temperature, or swept over a rated range, and each part against its ratings.')


def part_temperature_tab():
    """tmp-2: each part at its own temperature - the background plus its rise from the board over time."""
    return _tab('part-temperatures', 'Parts at their own temperature', [
        _row(0, [_table('bd-part-run', 0, 12, 'Run with every part at its own temperature', '', data_path='%s/part-run?rev=r{scope:rev}' % DOOR,
                        empty_text='Only a PCB with a layout and a circuit has this.', edit_fields='ambient_c', edit_signed_field='signed',
                        edit_action={'method': 'POST', 'path': '/api/pcb/{board}/simulate-parts', 'body_template': {'ambient_c': '{value}', 'mode': '{mode}'}},
                        description='What this is for: a board is not one temperature - parts near a hot one run warmer. Type the background (room) '
                                    'temperature in C and press Enter on a row: the board over time (the Thermal over time tab\'s solve, with every '
                                    'part\'s position probed) gives each part its rise, and the circuit runs with the board at the background and each '
                                    'part at its own temperature. One way: the run\'s powers do not change the temperatures back.',
                        columns='mode,ambient_c,meaning,last_run', max_height=160)], min_height=140),
        _row(1, [_table('bd-part-temps', 0, 12, 'Each part\'s own temperature', '', data_path='%s/part-temperatures?rev=r{scope:rev}' % DOOR,
                        empty_text='Only a PCB with a layout and a powered part has this.',
                        description='What this is for: where each part\'s temperature comes from. temp_c = the background + its rise: its junction when '
                                    'its datasheet thermal model is given, else the board under its pads (a part that takes no power warms from its '
                                    'neighbours). The circuit can only give a part its own temperature where ngspice allows it - the Temperature tab\'s '
                                    'own_temperature column says which.', columns='ref,power_w,temp_c,rise_c,mode,from,basis', max_height=400)], min_height=220)],
        'Each part at its own temperature: the background plus its rise from the board over time, then the circuit run that way.')
