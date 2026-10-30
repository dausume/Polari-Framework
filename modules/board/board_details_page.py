"""
@module board.board_details_page

bob-3 (AI-Notes/plans/BENCH_BOARDS_PLAN.md): `/display/board-details?board=<kind>/<definition>` - THE BOARD DETAILS PAGE. His words (2026-10-30): "We should
have an option to dive into a page about the Board Details from the Bench, but the abstracted drive and signal data centered around pins and footholds are
our main concern at the Bench level" and "a seperate simulation view for the breakdown of a single Board and it's design". Configured tables only (no new
component), bound by the page scope `board` = '<definition kind>/<definition>' (datasheet/arduino-uno-r3, geometry/breadboard-half, layers/<an ingested
PCB>), seeded from the URL or picked in the first table (the Boards on a Bench). Every tab reads one door: GET /api/board/details/{kind}/{definition}/{part}
(board.custom.board_details). The design-simulation parts (copper layers, circuits in the layers, thermal, silkscreen, footprints) grow on this page as
kxc-4 brings the PCB geometry.
"""
import json

from polariApiServer.module_pages_seed import _page, _row, _tab, _table

ROUTE = 'board-details'
DOOR = '/api/board/details/{scope:board}'

_TEXT = ('Board details - the definition of ONE board: how it is known and everything that definition holds. On the Bench every board - a dev board, a '
         'breadboard, a PCB - is the same kind of thing: places where wires land (footholds) with their voltage, current and signal. This page is the level '
         'below: for a dev board, its documents, nets, parts and its chip-package-board levels; for a breadboard, its strips and rails; for a PCB from KiCad, '
         'its files, its own nets (worked out by Polari and checked against KiCad), its parts with their simulation settings and its copper layers - pads, '
         'copper per net with its DC resistance, zones, silkscreen and drawings, net classes and rules. Thermal behaviour is not shown yet: it needs each '
         'part\'s power from the circuit simulation and a heat-spreading model. Pick a '
         'board in the first table, or open the page with ?board=<kind>/<definition>.')


def _picker():
    return _row(0, [_table('bd-boards', 0, 12, 'Boards on the home bench - click one to open its details', '', data_path='/api/board/benches/home-bench/all-boards',
                           select_field='board', select_scope='board', selected_value='{scope:board}',
                           description='What this is for: which board to open. One row = one Board on the Bench (dev boards, breadboards and PCBs alike). board_kind '
                                       'is what it is, definition_kind how it is known (datasheet / geometry / layers), footholds how many places a wire can land on it '
                                       '(-1 with the reason when its definition yields none). Click a row to bind every tab to it; click again or press Escape to unbind.',
                           columns='n,board_kind,label,definition_kind,definition,footholds,nodes,footholds_note', max_height=300)], min_height=220)


def _one(key, title, which, cols, what, empty):
    return [_row(0, [_table('bd-%s' % key, 0, 12, '%s of {scope:board}' % title, '', data_path='%s/%s' % (DOOR, which), empty_text=empty,
                            description='What this is for: %s' % what, columns=cols, max_height=720)], min_height=360)]


#: kxc-3b: the run chart - long form (x, y, series): one line per result vector, labelled with its own name and unit
RUN_GRAPH = 'pcb-spice-run'


def _run_graph_config():
    return {'renderStyle': 'lineY', 'xDimension': 'x', 'yDimensions': ['y'], 'seriesDimension': 'series', 'seriesColors': [],
            'options': {'width': 900, 'height': 360, 'marginTop': 20, 'marginRight': 30, 'marginBottom': 40, 'marginLeft': 70, 'showLegend': True, 'showGrid': True,
                        'xLabel': 'the run\'s scale: time (s) for a transient, frequency (Hz) for an AC sweep', 'yLabel': 'V, A for a #branch current; |V| for AC'},
            'aggregation': {'enabled': False, 'strategy': 'average'}}


SEED_BOARD_DETAILS_GRAPHS = [{
    'name': RUN_GRAPH, 'source_class': 'SpiceVector',
    'description': ('One simulation run of a PCB\'s schematic: every result vector against the run\'s scale, values exactly as ngspice returned them (thinned by '
                    'a plain stride for the screen - every drawn point is a solver point). Data: GET /api/pcb/runs/{run}/chart.'),
    'definition': json.dumps({'graphConfig': _run_graph_config()})}]


def _simulation_tab():
    return _tab('simulation', 'Simulation', [
        _row(0, [_table('bd-runs', 0, 12, 'Simulation runs of {scope:board} - click one to chart it', '', data_path='%s/runs' % DOOR,
                        select_field='name', select_scope='run', selected_value='{scope:run}', empty_text='No runs kept for this board (only a PCB from KiCad has a '
                        'deck; run it on a host with ngspice - econ-core - or post a worker\'s result).',
                        description='What this is for: every time this PCB\'s schematic was simulated. The deck is built from Polari\'s own rows (its sha256 says which); '
                                    'analysis is what ngspice ran (transient, AC sweep); status says whether it ran or why not; source / host: this host, a worker, or a '
                                    'recorded reference.', columns='ran_at,analysis,points,vectors,status,source,host,engine,deck_sha256', max_height=260)], min_height=200),
        _row(1, [_table('bd-run-vectors', 0, 12, 'Vectors of the selected run', '', data_path='/api/pcb/runs/{scope:run}/vectors', empty_text='Pick a run above.',
                        description='What this is for: what the run measured - each node voltage, branch current and the scale, with its unit (derived from the name the '
                                    'way ngspice names them), point count and range.', columns='vector,role,unit,complex_values,points,min_value,max_value', max_height=220)],
             min_height=160),
        _row(2, [{'id': 'bd-run-chart', 'index': 0, 'type': 'component', 'rowSegmentsUsed': 12, 'gridColumnStart': None, 'title': 'The selected run',
                  'description': 'Every result vector of the selected run against its scale - one line per vector, labelled with its name and unit.',
                  'visible': True, 'collapsed': False, 'cssClass': '',
                  'componentProps': {'componentName': 'named-graph-panel', 'inputs': {'graphName': RUN_GRAPH, 'dataPath': '/api/pcb/runs/{scope:run}/chart?max=2000'}},
                  'item': None, 'nestedRows': []}], min_height=420)],
        'For a PCB from KiCad: the simulation runs kept, their vectors and the chart of one run.')


BOARD_DETAILS_PAGES = [
    _page(ROUTE, ROUTE, _TEXT, 'BoardFoothold', [_picker()], title='Board details', scope_query=['board', 'run'],
          tabs=[_tab('summary', 'Summary', _one('summary', 'What defines', 'summary', 'board,defined_by,footholds,nodes,nets,parts,layers,coverage_rows,footholds_note',
                                                'how this board is known and how much each tab holds for it.', 'Pick a board above.'),
                     'How the board is defined and what each tab holds.'),
                _tab('footholds', 'Footholds', _one('footholds', 'Footholds', 'footholds',
                                                    'foothold,kind,label,node,net,rail_volts,logic_volts,source_ma,sink_ma,direction,families_json,chip_pin,drive_basis,signal_basis,undetermined',
                                                    'every place a wire can land, as the Bench sees it. node: footholds with the same node are joined inside the board. -1 = not '
                                                    'cited (the reason is in undetermined); drive_basis / signal_basis name where each number came from.', 'Pick a board above.'),
                     'What the Bench sees: every landing point with its drive and signal data.'),
                _tab('nets', 'Nets', _one('nets', 'Nets', 'nets', 'net,class,volts,scope,endpoints,pintypes_json,kicad_check,node,footholds,first,last,fact,notes',
                                          'the board\'s inside wiring. Dev board: its nets (cited). Breadboard: its joined groups (a strip half, a rail). PCB: the nets '
                                          'Polari worked out from the schematic, each checked against KiCad\'s own netlist (kicad_check).', 'Nothing to show for this board.'),
                     'The inside wiring at the definition level.'),
                _tab('parts', 'Parts', _one('parts', 'Parts', 'parts', 'ref,unit,value,role,lib_id,kicad_part,footprint,sheet,sim_device,sim_type,sim_params,sim_library,dnp,undetermined',
                                            'the parts that make up the board. A PCB\'s placed symbols carry their simulation settings (Sim.*) - the inputs of its '
                                            'simulation deck.', 'A breadboard has no parts of its own.'),
                     'The parts of the board.'),
                _tab('layers', 'Layers', _one('layers', 'Layers', 'layers', 'layer,id,type,user_name,stackup_type,thickness_mm,material,level,enclosure,kind,parent,notes',
                                              'the board\'s levels. Dev board: chip die -> package -> board (the enclosure chain behind each header pin). PCB: its copper, '
                                              'mask, silkscreen and fab layers with the stackup (thickness, material).', 'A breadboard has no layers.'),
                     'Chip-to-board levels, or a PCB\'s layer stack.'),
                _tab('coverage', 'KiCad coverage', _one('coverage', 'What the KiCad import understood', 'coverage', 'file,element,count,handling,polari_class,next_slice,notes',
                                                        'for a PCB from KiCad: every kind of element in every file, and whether it became Polari rows (typed), a summary, a '
                                                        'count, or is only kept in the stored file - nothing is dropped silently.', 'Only a PCB imported from KiCad has this.'),
                     'For a KiCad import: what became rows and what is only kept.'),
                # bob-3b: the single-Board design view's data (kxc-4) - a PCB's footprints, the circuits in its layers, its copper areas, its drawings, its rules
                _tab('pads', 'Pads', _one('pads', 'Pads (footprints)', 'pads', 'ref,number,pad_type,shape,x_mm,y_mm,angle,side,size_w_mm,size_h_mm,drill_mm,layers_json,net,pintype,pinfunction',
                                          'every pad of every footprint on a PCB: type (through-hole, SMD), shape, size, drill, the copper and mask layers it is on, its net and '
                                          'the pin type, and where it sits on the board.', 'Only a PCB has pads here.'),
                     'Every pad of every footprint.'),
                _tab('copper', 'Copper', _one('copper', 'Copper per net (the circuits in the layers)', 'copper',
                                              'net,segments,arcs,vias,length_mm,narrowest_mm,layers_json,dc_ohm_upper_bound,basis',
                                              'one row per net: how much track it has, its narrowest track, and the DC resistance of that copper - each segment rho x length / '
                                              '(width x thickness), the thickness from the board\'s own stackup and rho by definition (IEC 60028 annealed copper). The sum is an '
                                              'UPPER BOUND on any single path: a net that branches is not one series track.', 'Only a PCB has copper here.'),
                     'Each net\'s copper and its DC resistance.'),
                _tab('zones', 'Zones', _one('zones', 'Copper zones', 'zones', 'net,kind,zone_name,layers_json,priority,outline_area_mm2,filled_area_mm2,min_thickness_mm,thermal_gap_mm,thermal_bridge_mm',
                                            'the copper pours (and keep-outs, teardrops): the outline drawn and the copper area actually filled - where heat can spread.',
                                            'Only a PCB has zones.'),
                     'Copper pours, keep-outs and teardrops.'),
                _tab('drawings', 'Silkscreen + drawings', _one('drawings', 'Drawings per layer', 'drawings', 'layer,item,count,bbox_json',
                                                               'what is drawn on each layer - silkscreen, fab, courtyard, board edge, user layers - how many items of each kind '
                                                               'and the area they cover.', 'Only a PCB has layer drawings.'),
                     'Silkscreen, fab, courtyard and edge drawings.'),
                _tab('rules', 'Net classes + rules', _one('rules', 'Net classes and design rules', 'rules',
                                                         'what,netclass,clearance,track_width,via_diameter,via_drill,diff_pair_width,diff_pair_gap,net_count,rule,condition,layer,constraints_json',
                                                         'the project\'s net classes (clearance, track width, via sizes) with how many nets each holds, and its custom design rules.',
                                                         'Only a KiCad project has these.'),
                     'Net classes and custom rules.'),
                _simulation_tab()]),
]
