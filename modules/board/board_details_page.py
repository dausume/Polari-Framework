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
from polariApiServer.module_pages_seed import _page, _row, _tab, _table

ROUTE = 'board-details'
DOOR = '/api/board/details/{scope:board}'

_TEXT = ('Board details - the definition of ONE board: how it is known and everything that definition holds. On the Bench every board - a dev board, a '
         'breadboard, a PCB - is the same kind of thing: places where wires land (footholds) with their voltage, current and signal. This page is the level '
         'below: for a dev board, its documents, nets, parts and its chip-package-board levels; for a breadboard, its strips and rails; for a PCB from KiCad, '
         'its files, its own nets (worked out by Polari and checked against KiCad), its parts with their simulation settings and its copper layers. Pick a '
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


BOARD_DETAILS_PAGES = [
    _page(ROUTE, ROUTE, _TEXT, 'BoardFoothold', [_picker()], title='Board details', scope_query=['board'],
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
                     'For a KiCad import: what became rows and what is only kept.')]),
]
