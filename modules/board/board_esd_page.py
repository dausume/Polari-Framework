"""
@module board.board_esd_page

esd-0 / esd-1 (AI-Notes/plans/DRIVERS_AND_ESD_PLAN.md): the Board Details page's ESD tab - configured tables and one named graph, every one reading the
door GET /api/board/details/{kind}/{definition}/{part} (board.custom.board_esd) or posting to the ESD doors (board.esd_areas_api, pcb.pcb_esd_api).
"""
import json

from polariApiServer.module_pages_seed import _row, _tab, _table

DOOR = '/api/board/details/{scope:board}'
ESD_GRAPH = 'pcb-esd-event'

SEED_ESD_GRAPHS = [{
    'name': ESD_GRAPH, 'source_class': 'SpiceVector',
    'description': ('An ESD event on a PCB\'s circuit (esd-1): each protected net with the event and without it (the same deck, the discharge network '
                    'charged to 0 V), against time - every solver point near the event, a stride elsewhere. Data: GET /api/pcb/runs/{run}/esd-chart.'),
    'definition': json.dumps({'graphConfig': {
        'renderStyle': 'lineY', 'xDimension': 'x', 'yDimensions': ['y'], 'seriesDimension': 'series', 'seriesColors': [],
        'options': {'width': 900, 'height': 360, 'marginTop': 20, 'marginRight': 30, 'marginBottom': 40, 'marginLeft': 70, 'showLegend': True,
                    'showGrid': True, 'xLabel': 'time (s)', 'yLabel': 'V'},
        'aggregation': {'enabled': False, 'strategy': 'average'}}})}]


def esd_tab():
    return _tab('esd', 'ESD', [
        _row(0, [_table('bd-esd-candidates', 0, 5, 'Pieces of {scope:board} - flag one as an ESD protection area', '',
                        data_path='%s/esd-candidates?rev=r{scope:rev}' % DOOR, empty_text='Pick a board above.',
                        row_action={'label': 'Flag / unflag', 'method': 'POST', 'path': '/api/board/esd-areas/{definition_kind}/{board}/toggle',
                                    'body_template': {'scope': '{scope}', 'target': '{target}'}},
                        description='What this is for: saying what must survive a static shock - a connector\'s net, a pin anyone can touch. A PCB lists '
                                    'its nets, any other board its footholds. The button flags the piece, or unflags it when it is already flagged.',
                        columns='scope,target,flagged', max_height=360),
                 _table('bd-esd-areas', 0, 7, 'ESD protection areas - click one to set its test; Run event shocks it', '',
                        data_path='%s/esd-areas?rev=r{scope:rev}' % DOOR, select_field='name', select_scope='esdarea', selected_value='{scope:esdarea}',
                        empty_text='Nothing flagged yet.',
                        row_action={'label': 'Run event', 'method': 'POST', 'path': '/api/board/esd-areas/run', 'body_template': {'area': '{name}'},
                                    'then_scope': {'key': 'esdrun', 'from': 'run'}},
                        description='What this is for: the test each area must pass. test = the discharge network and level (human body model JS-001, '
                                    'or IEC 61000-4-2 contact); criterion = what passing means - no protected node above its absolute maximum ("do not '
                                    'break"), and back near normal within the recovery time ("handle it smoothly"). Run event shocks it and keeps the '
                                    'result: a PCB on its simulated circuit, any other board on the flagged foothold\'s pin alone.',
                        columns='scope,target,test,criterion,protection_parts,protection_refs,origin', max_height=360)], min_height=240),
        _row(1, [_table('bd-esd-quantities', 0, 6, 'Numbers for area {scope:esdarea} - type a value and press Enter', '',
                        data_path='%s/esd-quantities?area={scope:esdarea}&rev=r{scope:rev}' % DOOR, empty_text='Click an area above.',
                        edit_fields='value', edit_signed_field='signed',
                        edit_action={'method': 'PUT', 'path': '/api/board/esd-areas/quantity',
                                     'body_template': {'area': '{area}', 'quantity': '{quantity}', 'value': '{value}'}},
                        description='What this is for: the level to test at and what counts as passing. abs_max_v comes from the protected pins\' '
                                    'datasheet (-1 = not given: the break check then says undetermined); the recovery numbers are a knob (default: within 5 % '
                                    'or 50 mV of the no-event run by 10 us); pin_cap_pf and hold_ohm are knobs for a board with no circuit (the pin alone).',
                        columns='quantity,value,unit,meaning', max_height=260),
                 _table('bd-esd-models', 0, 6, 'Discharge networks', '', data_path='%s/esd-models' % DOOR,
                        description='What this is for: what an event is. Each is the standard\'s own - a capacitor charged to the level, '
                                    'discharged through a resistor, or IEC 61000-4-2\'s own current equation (its sub-nanosecond first peak) - with its '
                                    'levels; the caveat says what each leaves out.',
                        columns='model,source,capacitance_pf,resistance_ohm,inductance_nh,levels,standard,caveat', max_height=260)], min_height=200),
        _row(2, [_table('bd-esd-protection', 0, 12, 'Protection parts - the button puts one on area {scope:esdarea}, or takes it off', '',
                        data_path='%s/esd-protection?area={scope:esdarea}&rev=r{scope:rev}' % DOOR, empty_text='No protection parts known.',
                        row_action={'label': 'On / off the area', 'method': 'POST', 'path': '/api/board/esd-areas/protection',
                                    'body_template': {'area': '{area}', 'part': '{name}'}},
                        description='What this is for: trying a TVS diode on a net before buying it. Each part\'s ratings are its datasheet\'s; '
                                    'modelled = whether a SPICE model could be derived from them (model_why says how, or why not - a snapback polymer '
                                    'like the UNO\'s CG0603MLC-05E is not a breakdown diode). A part on the area goes from the shocked net to ground in '
                                    'both runs, and its peak current is checked against its rated peak pulse current.',
                        columns='name,part_number,kind,on_area,ratings,modelled,model_why,document', max_height=260)], min_height=160),
        _row(3, [_table('bd-esd-runs', 0, 12, 'ESD events run on this board - click one', '', data_path='%s/esd-runs?rev=r{scope:rev}' % DOOR,
                        select_field='name', select_scope='esdrun', selected_value='{scope:esdrun}', empty_text='No event run yet.',
                        description='What this is for: every shock simulated, kept with its no-event baseline. On a host without ngspice the attempt is '
                                    'kept as refused, with the reason.', columns='ran_at,event,status,points,host', max_height=220)], min_height=160),
        _row(4, [_table('bd-esd-summary', 0, 12, 'The selected event', '', data_path='%s/esd-summary?run={scope:esdrun}' % DOOR,
                        empty_text='Click an event run above.',
                        description='What this is for: the verdict. peak_current_a beside expected_current_a (level / R for a network, Eq. 9 of the '
                                    'loop for CDM, Table 3\'s first peak for the IEC equation: the source did what the standard says); energy_j = the charge\'s energy; verdict = '
                                    'breaks / does not recover in time / survives.',
                        columns='verdict,model,level_v,net,t_event_s,peak_current_a,expected_current_a,energy_j,protection_parts,basis',
                        max_height=160)], min_height=120),
        _row(5, [_table('bd-esd-results', 0, 12, 'Each node through the event', '', data_path='%s/esd-results?run={scope:esdrun}' % DOOR,
                        empty_text='Click an event run above.',
                        description='What this is for: where it hurts. One row per node, protected first: its peak and when, the no-event value then, '
                                    'the largest rise over the no-event run, the break check against the area\'s absolute maximum, and when it came back '
                                    'within the criterion (-1 = not by the end of the run) with the verdict; final_offset_v = how far off it still is at '
                                    'the end.', columns='node,protected,peak_v,peak_at_s,baseline_at_peak_v,rise_v,abs_max_v,breaks,recovered_after_s,'
                                                        'recovered,final_offset_v', max_height=320)], min_height=200),
        _row(6, [_table('bd-esd-protection-results', 0, 12, 'Protection parts through the event', '',
                        data_path='%s/esd-protection-results?run={scope:esdrun}' % DOOR, empty_text='Click an event run above.',
                        description='What this is for: whether the protection survives its own job - each part\'s peak current against its '
                                    'datasheet peak pulse current (I_PP, at its rated pulse). source_peak_a = what the shock itself delivered; the '
                                    'part\'s figure can read a little above it from the solver\'s first step at the edge (on the safe side). in_model = whether '
                                    'the peak stayed inside the cited points the model was derived from (a varistor above its i_c: the law understates '
                                    'the voltage).',
                        columns='part,part_number,peak_current_a,source_peak_a,i_pp_a,pulse,breaks,in_model,source', max_height=200)], min_height=120),
        _row(7, [{'id': 'bd-esd-chart', 'index': 0, 'type': 'component', 'rowSegmentsUsed': 12, 'gridColumnStart': None,
                  'title': 'Protected nets with and without the event', 'description': 'Each protected net with the event and without it.',
                  'visible': True, 'collapsed': False, 'cssClass': '',
                  'componentProps': {'componentName': 'named-graph-panel',
                                     'inputs': {'graphName': ESD_GRAPH, 'dataPath': '%s/esd-chart?run={scope:esdrun}' % DOOR}},
                  'item': None, 'nestedRows': []}], min_height=420)],
        'ESD: flag the pieces that must survive a static shock, set the test, and see whether the circuit breaks or recovers.')
