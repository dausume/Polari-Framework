"""
@module board.workbench_page

wb-2 (WORKBENCH_WALKTHROUGH_PLAN.md section 2): `/display/workbench` - the step-by-step walkthrough: name a Bench, put breadboards and dev / eval boards on it, attempt a Mission on it.
Pure page data built from the three generic wb-1 kinds (`steps`, `picker-button`, `cards`) plus configured tables; `bench_page.py` (/display/bench) is untouched.

  steps strip  1 Name the bench (done when scope `bench` is set) - 2 Breadboards - 3 Dev / eval boards - 4 Mission (done when scope `attempt` is set); each step's `target` is its tab key
  name         the benches table (GET /api/board/benches); clicking a row sets scope `bench`
  breadboards  picker-button "Breadboards" (cards from bench-options/breadboards) + the bench's breadboards table with Remove one
  boards       picker-button "Boards" (cards from bench-options/boards, facets arch / radio / level) + the bench's boards table with Remove
  mission      picker-button "Missions" (cards from /api/missions) whose action POSTs the attempt and sets scope `attempt` from the response's `verdict`; below, the last attempt as
               three tables (summary / candidates / gap + pruned) from the per-process attempts doors

Page-mechanism limits met (and what was done instead):
  * A `form` item runs a linked no-code SOLUTION, not a plain POST door - so wb-3 added the generic `door-form` kind (typed inputs -> one RowActionConfig through the shared
    action runner): step 1 carries one that POSTs `/api/board/benches` {name, title, notes} and sets scope `bench` from the response's `bench`, beside the benches table.
  * A table's row-select sets exactly ONE scope key (`select_scope`), so scope `bench` is all a selection can set. Steps 2 and 3 therefore cannot read `breadboard_count` /
    `board_count` scopes (the bench rows do carry both fields); they are derived with done_when on `{scope:bench}` (set) - "a bench is chosen so the step is open to do" - and the real
    counts arrive in wb-3 when a bench-detail scope exists.
  * `then_scope` = {key, from} reads a RESPONSE field, so the attempt action sets scope `attempt` from the response's `verdict` (meets|closest|none).
"""
from polariApiServer.module_pages_seed import _page, _row, _table, _tab, _component

_B = '{scope:bench}'
_REV = 'rev=r{scope:rev}'
_BENCHES = '/api/board/benches'
_REMOVE = '/api/board/benches/%s/remove' % _B
_BOARDS = '/api/board/benches/%s/boards' % _B
_BBS = '/api/board/benches/%s/breadboards' % _B
_ATTEMPT = '/api/board/benches/%s/attempt' % _B
_ATT = '/api/board/benches/%s/attempts' % _B
_PICK = 'Pick a bench in step 1 first.'

_STEPS = [('Name the bench', 'name', {'scope_key': '{scope:bench}', 'op': 'set'}),
          ('Breadboards', 'breadboards', {'scope_key': '{scope:bench}', 'op': 'set'}),
          ('Dev / eval boards', 'boards', {'scope_key': '{scope:bench}', 'op': 'set'}),
          ('Mission', 'mission', {'scope_key': '{scope:attempt}', 'op': 'set'})]

_FAMILIES = [('RISC-V', 'riscv'), ('Not RISC-V', 'not-riscv'), ('AVR', 'AVR'), ('ARM Cortex-M0+', 'ARM Cortex-M0+'), ('Xtensa LX7', 'Xtensa LX7'), ('FPGA', 'FPGA')]
_RADIOS = [('Wi-Fi', 'wifi'), ('BLE', 'ble'), ('802.15.4', '802.15.4'), ('Thread', 'thread'), ('LoRa', 'lora'), ('No radio', 'none'), ('Unverified', 'unverified')]
_LEVELS = [('Bare-C', 'bare_c'), ('FreeRTOS', 'freertos'), ('Zephyr', 'zephyr')]


def _opts(pairs):
    return [{'label': a, 'value': b} for a, b in pairs]


def _steps_row():
    steps = [{'label': l, 'done_when': dw, 'target': t} for l, t, dw in _STEPS]
    return _row(0, [_component('workbench-steps', 0, 12, 'Where you are', 'steps', {'steps': steps},
                               description='Four steps: name the bench, put breadboards on it, put dev / eval boards on it, attempt a Mission. Click a step to open it; steps are not locked.')], min_height=90)


def _create_form():
    """wb-3: the create-bench form (generic `door-form`): name required, title + notes optional; success sets scope `bench` to the new name and reloads the table."""
    return {'fields': [{'name': 'name', 'label': 'Bench name (a short key, e.g. lab-bench)', 'required': True},
                       {'name': 'title', 'label': 'Title'},
                       {'name': 'notes', 'label': 'Notes', 'type': 'textarea'}],
            'action': {'label': 'Create', 'method': 'POST', 'path': _BENCHES, 'body_template': {'name': '{name}', 'title': '{title}', 'notes': '{notes}'},
                       'then_scope': {'key': 'bench', 'from': 'bench'}},
            'submit_label': 'Create the bench', 'success_text': 'Created - it is now the bench of the next steps.'}


def _name_tab():
    return _tab('name', 'Name the bench', [
        _row(0, [_component('wb-create-bench', 0, 4, 'New bench', 'door-form', _create_form(),
                            description='Name a new, empty bench; it becomes the bench of the next steps. A duplicate name is refused by the door.'),
                 _table('wb-benches', 1, 8, 'Benches - click one to work on it', '',
                        description='One row per bench: its boards and breadboards. Click a row to make it THE bench of the next steps (click again to clear).',
                        columns='name,title,boards,breadboards,hardware_only_boards,notes', data_path=_BENCHES + '?' + _REV,
                        select_field='name', select_scope='bench', selected_value='{scope:bench}')], min_height=260)],
        description='Create a bench or pick an existing one.')


def _breadboard_cards():
    return {'dataPath': '/api/board/bench-options/breadboards?bench=%s&%s' % (_B, _REV), 'title_field': 'title', 'subtitle_field': 'part_number', 'group_by': 'kind',
            'badge_fields': ['kind', 'geometry'],
            'fields': {'Vendor': 'vendor', 'Tie points': 'tie_points', 'Rows': 'rows', 'Rails': 'rails', 'Rail holes': 'rail_holes', 'Rail power': 'rail_power',
                       'Outline': 'outline', 'Fits': 'fits', 'On the bench': 'on_bench'},
            'action': {'label': 'Add', 'method': 'POST', 'path': _BBS, 'body_template': {'model': '{name}', 'count': 1}, 'show_when_field': 'can_add'},
            'empty_text': _PICK}


def _breadboards_tab():
    return _tab('breadboards', 'Breadboards', [
        _row(0, [_component('wb-pick-breadboards', 0, 12, '', 'picker-button',
                            {'label': 'Breadboards', 'title': 'Pick breadboards for the bench', 'popup': _breadboard_cards()},
                            description='Opens the breadboard cards: tie points, rails, rail power (unverified unless a vendor rating is cited), outline, and how each dev board on the bench fits.')],
             min_height=90),
        _row(1, [_table('wb-bench-breadboards', 0, 12, 'Breadboards on this bench', '',
                        description='One row per breadboard model on the chosen bench with its count. geometry says whether the layout engine can draw it. Remove one takes one off.',
                        columns='title,kind,count,tie_points,rows,geometry,basis,note', data_path=_BBS + '?' + _REV, empty_text=_PICK,
                        row_action={'label': 'Remove one', 'method': 'POST', 'path': _REMOVE, 'body_template': {'kind': 'breadboard', 'key': '{model}'}})], min_height=260)],
        description='Choose the breadboards on the bench.')


def _board_cards():
    return {'dataPath': '/api/board/bench-options/boards?bench=%s&%s' % (_B, _REV), 'title_field': 'title', 'subtitle_field': 'chip',
            'badge_fields': ['family', 'testing', 'on_hand'],
            'fields': {'Core': 'core', 'Levels': 'levels', 'Radios': 'radios', 'Footprint': 'footprint', 'Price (USD)': 'price_usd', 'On the bench': 'on_bench'},
            'facets': [{'label': 'Architecture', 'query_param': 'arch', 'options': _opts(_FAMILIES)},
                       {'label': 'Wireless', 'query_param': 'radio', 'options': _opts(_RADIOS)},
                       {'label': 'Level', 'query_param': 'level', 'options': _opts(_LEVELS)}],
            'action': {'label': 'Add', 'method': 'POST', 'path': _BOARDS, 'body_template': {'board': '{board}'}, 'show_when_field': 'can_add'},
            'empty_text': 'No board matches those facets.'}


def _boards_tab():
    return _tab('boards', 'Dev / eval boards', [
        _row(0, [_component('wb-pick-boards', 0, 12, '', 'picker-button',
                            {'label': 'Boards', 'title': 'Pick dev / eval boards for the bench', 'popup': _board_cards()},
                            description='Opens the board cards with facets: architecture (RISC-V first), wireless, and the software level (Bare-C, FreeRTOS, Zephyr).')], min_height=90),
        _row(1, [_table('wb-bench-boards', 0, 12, 'Boards on this bench', '',
                        description='One row per physical board on the chosen bench with its testing word (simulated with real pins, stub pins, or HARDWARE ONLY). Remove takes it off.',
                        columns='label,title,chip,family,testing,software,added,note', data_path=_BOARDS + '?' + _REV, empty_text=_PICK,
                        row_action={'label': 'Remove', 'method': 'POST', 'path': _REMOVE, 'body_template': {'kind': 'board', 'key': '{label}'}})], min_height=260)],
        description='Choose the dev and eval boards on the bench.')


def _mission_cards():
    return {'dataPath': '/api/missions', 'title_field': 'title', 'subtitle_field': 'name', 'badge_fields': ['lifecycle', 'objective', 'stage'],
            'fields': {'Goal': 'goal', 'Purposes': 'purposes_text', 'Resolution today': 'resolution'},
            'action': {'label': 'Attempt on this bench', 'method': 'POST', 'path': _ATTEMPT, 'body_template': {'mission': '{name}'}, 'then_scope': {'key': 'attempt', 'from': 'verdict'}},
            'empty_text': 'No Missions yet.'}


def _mission_tab():
    return _tab('mission', 'Mission', [
        _row(0, [_component('wb-pick-missions', 0, 12, '', 'picker-button',
                            {'label': 'Missions', 'title': 'Attempt a Mission on this bench', 'popup': _mission_cards()},
                            description='Opens the Mission cards; "Attempt on this bench" asks whether the boards chosen can do it.')], min_height=90),
        _row(1, [_table('wb-attempt', 0, 12, 'The verdict - last attempt on this bench', '',
                        description='ONE row: verdict (meets / closest / none), the Mission, the boards the engine could model (boards_used), the boards it could not (not_modelled), how many '
                                    'candidates, and the run sha. Held in memory by the server process only - it is forgotten on a restart (wb-3 / mis-1 persist runs).',
                        columns='verdict,mission,boards_used,not_modelled,candidates,run_sha,why', data_path=_ATT + '?' + _REV, empty_text=_PICK)], min_height=160),
        _row(2, [_table('wb-attempt-candidates', 0, 12, 'Candidates', '',
                        description='One row per candidate design the attempt found, best first: the board, its tier, whether it is complete and meets the criteria, the routes chosen, the pins used and what is unmet.',
                        columns='rank,board,tier,complete,meets_criteria,buildable_on_bench,routes,pins_used,unmet,parts_missing', data_path=_ATT + '/candidates?' + _REV, empty_text=_PICK)], min_height=260),
        _row(3, [_table('wb-attempt-pruned', 0, 12, 'The gap and the pruned branches', '',
                        description='What is unmet (gap) and every branch the search discarded with the reason (pruned) - e.g. a pin refused because it is reserved.',
                        columns='what,count,where,reason', data_path=_ATT + '/pruned?' + _REV, empty_text=_PICK)], min_height=260)],
        description='Attempt a Mission on the bench and read the verdict.')


WORKBENCH_PAGES = [
    _page('workbench', 'workbench',
          'The workbench walkthrough: name a bench, add breadboards and dev / eval boards from card pickers, then attempt a Mission on it. Doors: /api/board/benches, '
          '/api/board/bench-options/breadboards|boards, /api/board/benches/{bench}/boards|breadboards|remove|attempt|attempts, /api/missions.',
          'Bench', [_steps_row()], title='The workbench',
          tabs=[_name_tab(), _breadboards_tab(), _boards_tab(), _mission_tab()]),
]
