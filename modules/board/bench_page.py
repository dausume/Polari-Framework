"""
@module board.bench_page

bench-0 (MISSION_GENERIC_PLAN.md section 13.1): `/display/bench` - the Bench and its two SELECTION panels, configured tables only (no raw JSON,
no new component; "Add to bench" and "Remove" are row actions). Three tabs:

  On the bench      the boards on it (each with its TESTING word: simulated with real pins / simulated, pins STUB / HARDWARE ONLY) and the
                    breadboards on it (each with its geometry state), with Remove
  Add a board       the dev / eval board selection list: every board the chips-and-levels ladder knows, RISC-V first, with testing + on_bench
  Add a breadboard  the breadboard selection list: every BreadboardModel with its tie points and geometry state

Fixed to the bench `home-bench` the way /display/pin-view is fixed to the UNO; the doors take any bench name.
"""
from polariApiServer.module_pages_seed import _page, _row, _table, _tab
from board.custom.bench_seed import HOME_BENCH

BENCH = HOME_BENCH
_BOARDS = '/api/board/benches/%s/boards' % BENCH
_BBS = '/api/board/benches/%s/breadboards' % BENCH
_REMOVE = '/api/board/benches/%s/remove' % BENCH
_OPT_BOARDS = '/api/board/bench-options/boards?bench=' + BENCH
_OPT_BBS = '/api/board/bench-options/breadboards?bench=' + BENCH

_TESTING_TEXT = ('testing says how a board on this bench can be tested - "simulated: pins real" (its twin drives and reads real pins), "simulated: pins STUB" (its twin runs the '
                 'firmware but the pins are a stub, so pin-level claims still need the real board), or "HARDWARE ONLY" (no emulator known: every proof is on the real board). '
                 'software and how say which emulator and what it emulates; inputs_driven_by says what presses the button in the twin.')


def _on_bench_tab():
    return _tab('bench', 'On the bench', [
        _row(0, [_table('bench-boards', 0, 12, 'Dev and eval boards on the bench', '',
                        description='One row per physical board on the bench. ' + _TESTING_TEXT + ' Press Remove to take a board off the bench (the row is kept nowhere else).',
                        columns='label,title,chip,family,section,testing,software,how,inputs_driven_by,added,note', data_path=_BOARDS,
                        row_action={'label': 'Remove', 'method': 'POST', 'path': _REMOVE, 'body_template': {'kind': 'board', 'key': '{label}'}})], min_height=320),
        _row(1, [_table('bench-breadboards', 0, 12, 'Breadboards on the bench', '',
                        description='One row per breadboard model on the bench with its count. geometry says whether the layout engine can draw it and place parts on it: known (derived from '
                                    'its rows and holes at the 2.54 mm pitch) or UNVERIFIED (only a label is known; the datasheet is needed). Remove takes one off.',
                        columns='title,kind,count,tie_points,rows,geometry,basis,note', data_path=_BBS,
                        row_action={'label': 'Remove one', 'method': 'POST', 'path': _REMOVE, 'body_template': {'kind': 'breadboard', 'key': '{model}'}})], min_height=280),
    ], description='What is on the bench right now, and how each board can be tested.')


def _add_board_tab():
    return _tab('add-board', 'Add a dev or eval board', [
        _row(0, [_table('bench-options-boards', 0, 12, 'Every dev and eval board Polari knows - pick one to add', '',
                        description='The selection list: one row per board from the chips-and-levels ladder, RISC-V boards first, then the convenience boards, the simulatable ones before '
                                    'the HARDWARE ONLY ones. ' + _TESTING_TEXT + ' on_bench = how many of it are already on the bench; on_hand = whether the ladder says one is on hand. '
                                    'Press Add to bench; the board appears on the first tab with its testing word.',
                        columns='section,title,chip,family,testing,software,on_hand,on_bench,price_usd,note', data_path=_OPT_BOARDS,
                        row_action={'label': 'Add to bench', 'method': 'POST', 'path': _BOARDS, 'show_when_field': 'can_add',
                                    'body_template': {'board': '{board}'}})], min_height=420),
    ], description='The dev / eval board selection panel.')


def _add_breadboard_tab():
    return _tab('add-breadboard', 'Add a breadboard', [
        _row(0, [_table('bench-options-breadboards', 0, 12, 'Every breadboard model - pick one to add', '',
                        description='The selection list: one row per breadboard model with its tie points, rows, rail holes and geometry state (known = drawable and placeable; UNVERIFIED = '
                                    'only a vendor label is known). on_bench = how many are on the bench. Press Add to bench to add one more.',
                        columns='title,vendor,part_number,kind,tie_points,rows,rail_holes,geometry,basis,on_bench', data_path=_OPT_BBS,
                        row_action={'label': 'Add to bench', 'method': 'POST', 'path': _BBS, 'show_when_field': 'can_add',
                                    'body_template': {'model': '{name}', 'count': 1}})], min_height=360),
    ], description='The breadboard selection panel.')


BENCH_PAGES = [
    _page('bench', 'bench',
          'The bench - the dev and eval boards and the breadboards on the table, added from two selection lists. Every board says how it can be tested: simulated with real pins, '
          'simulated with stub pins, or HARDWARE ONLY, with the emulator software named. The Mission search reads the bench as what is on hand. The doors: GET /api/board/benches, '
          '/api/board/benches/{bench}/boards|breadboards, /api/board/bench-options/boards|breadboards; POST .../boards, .../breadboards, .../remove.',
          'Bench', [
              _row(0, [_table('bench-summary', 0, 12, 'The benches', '',
                              description='One row per bench: how many boards and breadboards, how many boards are simulated with real pins, with stub pins, or HARDWARE ONLY - and which.',
                              columns='title,boards,breadboards,simulated_real_pins,simulated_stub_pins,hardware_only,hardware_only_boards,notes', data_path='/api/board/benches')],
                   min_height=200),
          ],
          title='The bench',
          tabs=[_on_bench_tab(), _add_board_tab(), _add_breadboard_tab()]),
]
