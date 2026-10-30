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
from polariApiServer.module_pages_seed import _component, _page, _row, _table, _tab
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


def _all_boards_tab():
    """bob-1/bob-2 (BENCH_BOARDS_PLAN.md): his ruling 2026-10-30 - dev boards, breadboards and PCBs are equally Boards on the Bench."""
    door = '/api/board/benches/%s' % BENCH
    return _tab('all-boards', 'Boards on the bench (one list)', [
        _row(0, [_table('bench-all-boards', 0, 12, 'Every Board on the bench - dev boards, breadboards and PCBs alike', '',
                        description='One row = one Board on the Bench, whatever it is: a dev board (known from its datasheets), a breadboard (known from its strip and rail '
                                    'counts) or a PCB (known from its KiCad design). id is what a connection names; footholds = how many places a wire can land on it '
                                    '(-1 with the reason when its definition gives none); details opens its Board Details page (the definition level: nets, parts, '
                                    'layers, what the KiCad import understood).',
                        columns='n,id,board_kind,label,definition_kind,definition,footholds,nodes,details,footholds_note',
                        column_formats='details:view:/display/board-details?board={board}', data_path=door + '/all-boards?rev=r{scope:rev}', max_height=420)], min_height=300),
        _row(1, [_table('bench-pins', 0, 12, 'Pins and their connections - is every pin\'s drive met?', '',
                        description='THE BENCH: one row per pin that something is connected to (pins a board joins inside, like its GND pins, are one row). firmware '
                                    'says which firmware variable uses the pin and how (gpio.out = it drives it); connections are the other PINS it reaches and via '
                                    'what (a breadboard\'s strips); checks compare the pin\'s own properties - its logic level, its current limit, whether it drives - '
                                    'with what its connections and firmware need: over-voltage (a 5 V driver on a 3.3 V pin), contention (two outputs driving each '
                                    'other), short (two supplies, or a supply and ground). defined names the board-level circuit a pin is part of (an LED with its '
                                    'resistor...): its real drive behaviour is worked out at board level and its findings land here - the LED current against the '
                                    'pin\'s limit, a missing pull, a firmware that drives a pin the circuit reads. notes say what could not be judged yet.',
                        columns='status,pin,firmware,connections,defined,via,logic_volts,source_ma,checks,notes', data_path=door + '/pins?rev=r{scope:rev}', max_height=520)],
             min_height=320),
        _row(2, [_component('bench-netlist', 0, 3, '', 'picker-button',
                            {'label': 'Bench netlist', 'title': 'The bench netlist - every net that crosses boards',
                             'popup': {'dataPath': door + '/nets?rev=r{scope:rev}', 'title_field': 'net', 'subtitle_field': 'boards',
                                       'fields': {'Boards': 'boards', 'Footholds on it': 'members', 'Findings': 'findings', 'Not judged': 'undetermined'},
                                       'empty_text': 'Nothing on the bench is connected across boards yet.'}},
                            description='The full netlist of the bench, in its own popup (his rule: the main bench view stays pins and connections).'),
                 _table('bench-connections', 3, 9, 'Wiring - wires, jumpers, mated pins', 'BenchConnection',
                        description='One row = one wire, jumper, or mated pin between two footholds on any two Boards - the raw wiring the pins table is worked out '
                                    'from (POST /api/board/benches/<bench>/connections or /mate).',
                        columns='from_board,from_foothold,to_board,to_foothold,kind,colour,label', data_path=door + '/connections?rev=r{scope:rev}', max_height=320)],
             min_height=200),
    ], description='Every Board on the bench in one list, then its pins: what each is connected to, what firmware does with it, and whether its drive is met.')


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


_BUDGET = '/api/benches/home-bench/budget'


def _budget_tab():
    """ipb-2: the polling + interrupt budget of the REAL boards on the bench — two columns per hart (program counter); the full page is /display/budget."""
    return _tab('budget', 'Budget: polls + interrupts per hart', [
        _row(0, [_table('bench-budget-harts', 0, 12, 'One row per hart (program counter) on the bench: two columns each', 'HardwareMission',
                        description='Each board\'s program counters: a board with a Mission gets that Mission\'s plan as its budget (polls / interrupts counted, headroom), '
                                    'any other board shows its cited facts with empty columns. schedule_model = superloop (bare C) | cyclic-executive | preemptive-rtos. '
                                    'The whole budget with its knobs is /display/budget. GET %s?view=harts.' % _BUDGET,
                        columns='hart,label,soc,isa,controller,clock_hz,schedule_model,polls,interrupts,threads,headroom,openness,notes', data_path=_BUDGET + '?view=harts')],
             min_height=260),
        _row(1, [_table('bench-budget-polls', 0, 6, 'POLLS (left column)', 'HardwareMission',
                        description='The atoms the loop runs each pass, with their measured cycles and the tightest response they serve. GET %s?view=polls.' % _BUDGET,
                        columns='hart,atom_short,task,wanted_response_ms,poll_divider,cycles_max,cost_per_scan_cycles,basis', data_path=_BUDGET + '?view=polls',
                        empty_text='No polls: no firmware is assigned to a board on this bench.'),
                 _table('bench-budget-ints', 6, 6, 'INTERRUPTS (right column)', 'HardwareMission',
                        description='The interrupt handlers, their measured length / latency and expected rate. The column exists even when empty: every hart can take interrupts. '
                                    'GET %s?view=interrupts.' % _BUDGET,
                        columns='hart,vector,task,expected_rate_hz,length_mean,latency_max,utilisation,nests,basis', data_path=_BUDGET + '?view=interrupts',
                        empty_text='No interrupts enabled by the firmware on this bench.')], min_height=300),
        _row(2, [_table('bench-budget-derived', 0, 12, 'Scan, deadline, utilisation, headroom per hart', 'HardwareMission',
                        description='scan_cycles (the bound) beside the twin\'s measured worst gap, the scan deadline (knob; default = the shortest wanted response / 2), '
                                    'utilisation and headroom. GET %s?view=derived.' % _BUDGET,
                        columns='hart,polls_per_scan,scan_cycles,measured_worst_gap_cycles,scan_ms,scan_deadline_ms,scan_deadline_basis,scan_utilisation,isr_utilisation,headroom',
                        data_path=_BUDGET + '?view=derived')], min_height=200)],
        description='ANALYSING what is on the bench: two columns (polls, interrupts) per program counter, RISC-V names canonical. Nothing stored; knobs on /display/budget.')


BENCH_PAGES = [
    _page('bench', 'bench',
          'The bench - the dev and eval boards and the breadboards on the table, added from two selection lists. Every board says how it can be tested: simulated with real pins, '
          'simulated with stub pins, or HARDWARE ONLY, with the emulator software named. The Mission search reads the bench as what is on hand. The doors: GET /api/board/benches, '
          '/api/board/benches/{bench}/boards|breadboards, /api/board/bench-options/boards|breadboards; POST .../boards, .../breadboards, .../remove. '
          'Dev boards, breadboards and PCBs are equally Boards on the Bench: the "Boards on the bench" tab lists them in one list with the wires between them '
          '(/api/board/benches/{bench}/all-boards|connections|nets) and links each to its Board Details.',
          'Bench', [
              _row(0, [_table('bench-summary', 0, 12, 'The benches', '',
                              description='One row per bench: how many boards and breadboards, how many boards are simulated with real pins, with stub pins, or HARDWARE ONLY - and which.',
                              columns='title,boards,breadboards,simulated_real_pins,simulated_stub_pins,hardware_only,hardware_only_boards,notes', data_path='/api/board/benches')],
                   min_height=200),
          ],
          title='The bench',
          tabs=[_on_bench_tab(), _all_boards_tab(), _add_board_tab(), _add_breadboard_tab(), _budget_tab()]),
]
