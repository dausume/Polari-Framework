"""
@module cmod.bench_views_page

hsp-3b + hsp-3c (HARDWARE_SYSTEM_PINS_PLAN.md §7): `/display/bench-views` - the bench's Structs, Polari Hardware Bridges and HAL views as ONE page of configured
tables (no raw JSON; no new component). The bench picker sits above the tabs and is shared by all three; every click sets a page scope the next table reads.

  Structs   struct instances on the bench (click one) -> its fields (click one) -> the signal paths that change it, hop by hop, from the Catom assertions
  Bridges   the bench's bridges (click one; "Switch mode" flips serial <-> simulated) -> its hops as that mode gives them -> the structs that cross it (a click
            opens the Structs tab at that instance)
  HAL       the bridge's firmware (click one) -> its HAL values (click one) -> the pins that value may use, each with "Use this pin" (THE slot-choice write,
            POST /api/cmod/catom-variables/{variant}/set: checked, then written to the firmware recipe's knob); a door-form for a typed value (F_CPU)
Linkable: /display/bench-views?bench=home-bench&instance=...&bridge=...&variant=uno-light (scope_query).
"""
from polariApiServer.module_pages_seed import _page, _row, _table, _tab, _component

_B = '{scope:bench}'
_REV = 'rev=r{scope:rev}'
_BENCHES = '/api/board/benches'
_STRUCTS = '/api/cmod/bench-structs/%s' % _B
_BRIDGES = '/api/grpc/bench-bridges/%s' % _B
_HAL = '/api/cmod/catom-variables/{scope:variant}'
_PICK = 'Pick a bench above first.'


def _bench_row():
    return _row(0, [_table('bv-benches', 0, 12, 'Benches - click one', '',
                           description='One row per bench. Click a row to make it THE bench of every tab below (click again to clear).',
                           columns='name,title,boards,breadboards,notes', data_path=_BENCHES + '?' + _REV,
                           select_field='name', select_scope='bench', selected_value=_B)], min_height=200)


def _structs_tab():
    return _tab('structs', 'Structs', [
        _row(0, [_table('bv-struct-instances', 0, 12, 'Struct instances on this bench - click one', '',
                        description='One row per struct INSTANCE on the bench: a firmware struct type and its index on one board, the bridge it crosses and the Polari object it '
                                    'becomes there. Two lights on one board are two rows. fields / asserted_fields = how many of its fields a catom asserts it changes or reads; '
                                    'verified = assertions a twin record confirms. state bound = a HardwareInterfaceBinding gives it its object.',
                        columns='name,struct,index,polari_class,object,bridge,hardware_id,pins,fields,asserted_fields,verified,state',
                        data_path=_STRUCTS + '?view=instances&bench=%s&%s' % (_B, _REV), empty_text=_PICK,
                        select_field='name', select_scope='instance', selected_value='{scope:instance}')], min_height=220),
        _row(1, [_table('bv-struct-fields', 0, 12, 'Its fields - click one', '',
                        description='One row per field of the chosen instance: the Polari attribute it becomes, the catoms that CHANGE it and the ones that READ it (from the '
                                    'Catom assertions), the pins on those paths and the verdict - verified, unverified (declared, not yet confirmed by a frame-decoding run), '
                                    'false, or gap (nothing asserts it).',
                        columns='field,attribute,changed_by,read_by,pins,verdict,why', data_path=_STRUCTS + '?view=fields&instance={scope:instance}&' + _REV,
                        empty_text='Pick a struct instance above.', select_field='field', select_scope='field', selected_value='{scope:field}')], min_height=260),
        _row(2, [_table('bv-struct-path', 0, 12, 'The signals that change it', '',
                        description='One row per hop of each route that changes (or reads) the chosen field, in order: the pin and its event, the catom (its lane and who it '
                                    'says changed it: HW the board, US the user through Polari), the field, the catom that sends the struct, the bridge, the Polari object\'s '
                                    'attribute. A route from the UI starts at the object and comes in through the bridge. status is the assertion\'s own.',
                        columns='route,step,kind,direction,what,status,why', data_path=_STRUCTS + '?view=path&instance={scope:instance}&field={scope:field}&' + _REV,
                        empty_text='Pick a field above.')], min_height=300)],
        description='Every struct instance on the bench, its fields, and the signal paths that change each field - drawn from the Catom assertions.')


def _bridges_tab():
    return _tab('bridges', 'Bridges', [
        _row(0, [_table('bv-bridges', 0, 12, 'Polari Hardware Bridges on this bench - click one', '',
                        description='One row per bridge: the hardware it reads, the mode (serial = the real board over its cable; simulated = its twin on the board engine '
                                    'worker), the Polari node it is bound to and its address on the isle, and whether it is bound. "Switch mode" flips serial and simulated.',
                        columns='name,hardware_id,mode,polari_node,polari_node_url,bridge_definition,status,status_why', data_path=_BRIDGES + '?view=bridges&bench=%s&%s' % (_B, _REV),
                        empty_text=_PICK, select_field='name', select_scope='bridge', selected_value='{scope:bridge}',
                        row_action={'label': 'Switch mode', 'method': 'POST', 'path': _BRIDGES + '/mode', 'body_template': {'bridge': '{name}'}})], min_height=200),
        _row(1, [_table('bv-bridge-hops', 0, 12, 'Where its signal goes', '',
                        description='One row per hop of the chosen bridge as its mode gives it: serial = chip pins, the USB-serial converter, the connector, the host port and the '
                                    'bridge program; simulated = the twin\'s pins, the twin and the board engine worker on the isle. signal_level is cited or -1.',
                        columns='n,kind,what,signal_level,mode,basis', data_path=_BRIDGES + '?view=hops&bridge={scope:bridge}&' + _REV,
                        empty_text='Pick a bridge above.')], min_height=240),
        _row(2, [_table('bv-bridge-structs', 0, 12, 'The structs that cross it - click one to open it in Structs', '',
                        description='One row per struct instance that crosses the chosen bridge and the Polari object it becomes. A click opens the Structs tab at that instance.',
                        columns='name,struct,index,polari_class,object,state', data_path=_STRUCTS + '?view=instances&bridge={scope:bridge}&' + _REV,
                        empty_text='Pick a bridge above.', select_field='name', select_scope='instance', selected_value='{scope:instance}', row_link_tab_field='tab')],
             min_height=200)],
        description='Every Polari Hardware Bridge on the bench, the path its signal takes, and the structs that cross it.')


def _typed_form():
    return {'fields': [{'name': 'variable', 'label': 'HAL value (e.g. F_CPU)', 'required': True}, {'name': 'value', 'label': 'Value', 'required': True}],
            'action': {'label': 'Set', 'method': 'POST', 'path': _HAL + '/set', 'body_template': {'variable': '{variable}', 'value': '{value}'}},
            'submit_label': 'Check and set', 'success_text': 'Checked and set - the tables show the new value. A refusal says every reason and nothing is written.'}


def _hal_tab():
    return _tab('hal', 'HAL', [
        _row(0, [_table('bv-hal-firmware', 0, 12, 'The firmware on each bridge - click one', '',
                        description='One row per bridge on the bench and the firmware variant its board runs (bridge_definition). Click one to see that firmware\'s HAL values.',
                        columns='name,hardware_id,bridge_definition,mode', data_path=_BRIDGES + '?view=bridges&bench=%s&%s' % (_B, _REV), empty_text=_PICK,
                        select_field='bridge_definition', select_scope='variant', selected_value='{scope:variant}')], min_height=180),
        _row(1, [_table('bv-hal-values', 0, 12, 'Its HAL values - click one to choose its pin', '',
                        description='One row per named value the firmware is built with (the LED pin, the UART pins, the clock): its role, its value, which scope set it (chip '
                                    'datasheet, board, or the bench - a bench pin lives in the firmware recipe\'s knob) and the check\'s verdict with every reason.',
                        columns='variable,role,value,scope,status,value_basis,status_why', data_path=_HAL + '?view=variables&variant={scope:variant}&' + _REV,
                        empty_text='Pick a firmware above.', select_field='variable', select_scope='variable', selected_value='{scope:variable}')], min_height=260),
        _row(2, [_table('bv-hal-slots', 0, 8, 'The pins it may use', '',
                        description='One row per pin the chosen value may take on this chip that ALSO passes the firmware recipe\'s own rules: accepted first, then warnings (the '
                                    'reason says what to mind). "Use this pin" checks it again and writes it; the firmware is generated with it.',
                        columns='pin,verdict,why', data_path=_HAL + '?view=slots&variable={scope:variable}&' + _REV, empty_text='Pick a HAL value above.',
                        row_action={'label': 'Use this pin', 'method': 'POST', 'path': _HAL + '/set', 'body_template': {'variable': '{scope:variable}', 'value': '{pin}'}}),
                 _component('bv-hal-typed', 1, 4, 'A typed value', 'door-form', _typed_form(),
                            description='For a value that is a number (F_CPU) or to type a pin by name. The same check runs; a refusal names every reason.')],
             min_height=300)],
        description='The firmware\'s HAL: its named values, the pins each may use, and the choice - checked against what the pin can do, what the board does with it '
                    'while it starts up, the other values and the recipe\'s rules.')


BENCH_VIEWS_PAGES = [
    _page('bench-views', 'bench-views',
          'The bench\'s Structs, Polari Hardware Bridges and HAL: struct instances and the signal paths that change their fields (Catom assertions), the bridges and where '
          'their signal goes in each mode, and the firmware\'s named values with the pins each may use. Doors: /api/board/benches, /api/cmod/bench-structs/{bench}, '
          '/api/grpc/bench-bridges/{bench}[/mode], /api/cmod/catom-variables/{variant}[/set].',
          'Bench', [_bench_row()], title='Bench views', tabs=[_structs_tab(), _bridges_tab(), _hal_tab()], scope_query=['bench', 'instance', 'bridge', 'variant']),
]
