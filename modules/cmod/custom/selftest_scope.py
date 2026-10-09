"""cmod.custom.selftest_scope — ucd-scope (UNO_CORE_DEMO_PLAN.md §5f, his ruling 2026-10-09, verbatim: "when we have
a page we only want to be concerned about pins and properties we know belong to just the board, chip, and firmware
we are using. We do not want a page with everything possible on it ... those should be object specific pages").

Proves `cmod.custom.scope.scope_for` (the door GET /api/firmware/solutions/{name}/hardware calls) answers EXACTLY
the rows uno-button-clock@arduino-uno-r3 claims/activates/sets — never "everything possible" — and that a DIFFERENT
binding (uno-sim-rig, the analog one) scopes to a DIFFERENT set (A0/ADC0 in, EICRA out). Run by cmod_selftest.main()
(scope_parts), same shape as selftest_binding.py/selftest_claims.py.
"""
import json

BC_SOLUTION, BC_GRAPH, BOARD = 'uno-button-clock', 'uno-button-clock-graph', 'arduino-uno-r3'
BC_BINDING = '%s@%s' % (BC_SOLUTION, BOARD)
SR_SOLUTION, SR_GRAPH = 'uno-sim-rig', 'uno-sim-rig-graph'


def scope_parts(check):
    def button_clock_pins():
        _button_clock_pins(check)

    def button_clock_functions_peripherals():
        _button_clock_functions_peripherals(check)

    def button_clock_registers_fields():
        _button_clock_registers_fields(check)

    def every_ref_resolves():
        _every_ref_resolves(check)

    def sim_rig_differs():
        _sim_rig_differs(check)

    def page_has_no_all_rows_table():
        _page_has_no_all_rows_table(check)

    def live_door():
        _live_door(check)

    return (button_clock_pins, button_clock_functions_peripherals, button_clock_registers_fields,
            every_ref_resolves, sim_rig_differs, page_has_no_all_rows_table, live_door)


def _scope(solution, graph, manager=None):
    from cmod.custom import binding as BND
    from cmod.custom import scope as SCOPE
    b = BND.derive(solution, manager=manager)
    return SCOPE.scope_for(b, graph, manager=manager)


# ---------------------------------------------------------------- part 1: the scoped pins, exactly
def _button_clock_pins(check):
    r = _scope(BC_SOLUTION, BC_GRAPH)
    check('binding/board/soc are named', r['binding'] == BC_BINDING and r['board'] == BOARD and r['soc'] == 'atmega328p', r)
    canon = sorted(p['canonical'] for p in r['rows']['pins'])
    check('the scoped pins are exactly D2, D3, D6, D13 + D0/D1 (usart_init DOES claim them — asserted, never guessed)',
          canon == ['D0', 'D1', 'D13', 'D2', 'D3', 'D6'], canon)
    by_canon = {p['canonical']: p for p in r['rows']['pins']}
    check('every pin row carries the claim that put it here (mode/pull/edge/initial/task), not just the BoardPin',
          all({'claim', 'claim_mode', 'claim_pull', 'claim_edge', 'claim_initial', 'task'} <= set(p) for p in r['rows']['pins']))
    check('D2: claimed alt (INT0), pull up, edge falling, task button_init',
          by_canon['D2']['claim_mode'] == 'alt' and by_canon['D2']['claim_pull'] == 'up'
          and by_canon['D2']['claim_edge'] == 'falling' and by_canon['D2']['task'] == 'button_init', by_canon['D2'])
    check('D3: claimed alt (INT1), edge any, task sense_init',
          by_canon['D3']['claim_mode'] == 'alt' and by_canon['D3']['claim_edge'] == 'any'
          and by_canon['D3']['task'] == 'sense_init', by_canon['D3'])
    check('D6/D13: claimed out, initial low (the two LEDs)',
          by_canon['D6']['claim_mode'] == 'out' and by_canon['D6']['claim_initial'] == 'low'
          and by_canon['D13']['claim_mode'] == 'out' and by_canon['D13']['claim_initial'] == 'low')
    soc_canon = sorted(sp['pin'] for sp in r['rows']['soc_pins'])
    check('soc_pins are exactly the SocPins behind those six BoardPins (PD0/PD1/PD2/PD3/PD6/PB5), never every SocPin',
          soc_canon == ['PB5', 'PD0', 'PD1', 'PD2', 'PD3', 'PD6'], soc_canon)


# ---------------------------------------------------------------- part 2: functions + peripherals, exactly
def _button_clock_functions_peripherals(check):
    r = _scope(BC_SOLUTION, BC_GRAPH)
    fns = {p['function'] for p in r['rows']['pin_functions']}
    check('functions include PD2:INT0, PD3:INT1 and the GPIO functions of D6 (PD6) / D13 (PB5)',
          {'INT0', 'INT1', 'GPIO'} <= fns, fns)
    names = {p['name'] for p in r['rows']['pin_functions']}
    check('functions: PD2:INT0, PD3:INT1, PD6:GPIO, PB5:GPIO all present (+ D0/D1\'s own RXD/TXD, since they are claimed too)',
          {'atmega328p:PD2:INT0', 'atmega328p:PD3:INT1', 'atmega328p:PD6:GPIO', 'atmega328p:PB5:GPIO'} <= names, names)
    check('nothing of other pins: no ADC0, no OC0A (uno-button-clock claims neither A0 nor D6-as-PWM)',
          not any(p['function'] in ('ADC0', 'OC0A') for p in r['rows']['pin_functions']), names)
    peri = {p['peripheral'] for p in r['rows']['peripherals']}
    check('peripherals: EXINT, GPIO PORTB, GPIO PORTD, TIMER2 (the tick), USART0 (the telemetry) — and NOT ADC/SPI/TWI',
          peri == {'EXINT', 'GPIO PORTB', 'GPIO PORTD', 'TIMER2', 'USART0'}, peri)
    tick = next(p for p in r['rows']['peripherals'] if p['peripheral'] == 'TIMER2')
    check('TIMER2\'s own usage/tasks carry (exclusive, tick_init)', tick['usage'] == 'exclusive' and tick['tasks'] == 'tick_init', tick)


# ---------------------------------------------------------------- part 3: registers + fields, exactly
def _button_clock_registers_fields(check):
    r = _scope(BC_SOLUTION, BC_GRAPH)
    set_at_init = sorted(g['register'] for g in r['rows']['registers'] if g['why'] == 'set at init')
    check('registers set = DDRB, DDRD, EICRA, EIFR, EIMSK, PORTD, why "set at init"',
          set_at_init == ['DDRB', 'DDRD', 'EICRA', 'EIFR', 'EIMSK', 'PORTD'], set_at_init)
    claimed_only = sorted(g['register'] for g in r['rows']['registers'] if g['why'] == 'claimed peripheral')
    check('the OTHER registers of the claimed peripherals (TIMER2/USART0/PORTB) are present too, why "claimed peripheral", never written',
          {'OCR2A', 'TCCR2A', 'TCCR2B', 'TIMSK2', 'UBRR0H', 'UBRR0L', 'UCSR0A', 'UCSR0B', 'UCSR0C', 'UDR0', 'PORTB'} <= set(claimed_only), claimed_only)
    check('every register row carries a `why` of exactly one of the two kinds (never both, never neither)',
          all(g['why'] in ('set at init', 'claimed peripheral') for g in r['rows']['registers']))
    check('a "set at init" register carries its value/mask; a "claimed peripheral" one does not',
          all(bool(g['value']) and bool(g['mask']) for g in r['rows']['registers'] if g['why'] == 'set at init')
          and all(g['value'] == '' and g['mask'] == '' for g in r['rows']['registers'] if g['why'] == 'claimed peripheral'))
    fields = r['rows']['fields']
    check('the ten-ish RegisterFieldSettings are the scoped fields (11: DDRB.DDB5, DDRD.DDD2/3/6, EICRA.ISC0/1, '
          'EIFR.INTF0/1, EIMSK.INT0/1, PORTD.PORTD2)', len(fields) == 11, sorted(f['field'] for f in fields))
    check('every field row carries value/meaning/claim/task/rule (the setting that produced it, not just the field)',
          all({'value', 'meaning', 'claim', 'task', 'rule'} <= set(f) for f in fields))


# ---------------------------------------------------------------- part 4: every ref resolves
def _every_ref_resolves(check):
    r = _scope(BC_SOLUTION, BC_GRAPH)
    known_classes = {'BoardPin', 'SocPin', 'PinFunction', 'PeripheralSignal', 'Peripheral', 'Register',
                     'RegisterField', 'RegisterSetting', 'RegisterFieldSetting', 'SignalRoute'}
    bad = []
    for key, rows in r['rows'].items():
        for row in rows:
            cls, sep, nm = row['ref'].partition(':')
            if not sep or cls not in known_classes or nm != row['name']:
                bad.append((key, row.get('name'), row.get('ref')))
    check('every row carries a ref of shape "<its own Class>:<its own name>"', not bad, bad)
    # the forward refs a scoped row itself carries (soc_pin/peripheral/signal/register columns) resolve to another
    # row in the SAME scoped payload for every list that is supposed to carry its own chain behind it
    sig_names = {s['name'] for s in r['rows']['signals']}
    per_names = {p['name'] for p in r['rows']['peripherals']}   # Peripheral.name is the FULL id; .peripheral is bare
    bad_sig = [p['name'] for p in r['rows']['pin_functions'] if p.get('signal') and p['signal'] not in sig_names]
    bad_per = [p['name'] for p in r['rows']['pin_functions'] if p.get('peripheral') and p['peripheral'] not in per_names]
    check('every pin_function\'s own signal resolves to a scoped PeripheralSignal row', not bad_sig, bad_sig)
    check('every pin_function\'s own peripheral resolves to a scoped Peripheral row', not bad_per, bad_per)
    reg_names = {g['name'] for g in r['rows']['registers']}   # Register.name is the FULL id; .register is bare
    bad_set_reg = [s['name'] for s in r['rows']['settings'] if s['register'] not in reg_names]
    check('every RegisterSetting\'s own register resolves to a scoped Register row', not bad_set_reg, bad_set_reg)
    field_names = {f['name'] for f in r['rows']['fields']}
    bad_fs_field = [fs['name'] for fs in r['rows']['field_settings'] if fs['register_field'] not in field_names]
    check('every RegisterFieldSetting\'s own register_field resolves to a scoped RegisterField row', not bad_fs_field, bad_fs_field)


# ---------------------------------------------------------------- part 5: a different binding, a different scope
def _sim_rig_differs(check):
    r = _scope(SR_SOLUTION, SR_GRAPH)
    canon = sorted(p['canonical'] for p in r['rows']['pins'])
    check('uno-sim-rig claims A0 (analog-in) — uno-button-clock never does', 'A0' in canon, canon)
    fns = {p['function'] for p in r['rows']['pin_functions']}
    check('uno-sim-rig\'s scope carries ADC0 (A0\'s own alt function)', 'ADC0' in fns, fns)
    regs = {g['register'] for g in r['rows']['registers']}
    check('uno-sim-rig never configures an external interrupt (no button/sense task) — EICRA is OUT of its scope',
          'EICRA' not in regs, regs)
    check('the two bindings scope DIFFERENTLY (never the same list for two different firmwares)',
          canon != sorted(p['canonical'] for p in _scope(BC_SOLUTION, BC_GRAPH)['rows']['pins']))


# ---------------------------------------------------------------- part 6: the page carries no all-rows table
def _page_has_no_all_rows_table(check):
    from board.board_page import SEED_BOARD_PAGE_DISPLAYS as P
    chain_page = next(p for p in P if p['pageRoute'] == 'hardware-chain')
    rows = json.loads(chain_page['definition'])['rows']
    items = [it for row in rows for it in row['items']]
    ids = {it['id'] for it in items}
    check('/display/hardware-chain no longer carries the all-rows Peripheral/PeripheralSignal/Register/RegisterField/'
          'address-space/register-block tables (those moved to the class pages)',
          not ({'boards-peripherals', 'boards-peripheral-signals', 'boards-registers', 'boards-register-fields',
                'boards-address-mappings', 'boards-register-blocks'} & ids), ids)
    check('/display/hardware-chain still carries the D3 walk (one pin\'s chain, scoped by nature)',
          'boards-chain-d3' in ids, ids)
    scoped_ids = {'scope-pins', 'scope-functions', 'scope-peripherals', 'scope-registers', 'scope-fields'}
    check('/display/hardware-chain carries the five SCOPED tables, each reading the scoped door with a `list` param',
          scoped_ids <= ids, ids)
    scoped_items = [it for it in items if it['id'] in scoped_ids]
    check('every scoped table reads GET /api/firmware/solutions/uno-button-clock@arduino-uno-r3/hardware?list=<key> '
          '(the demo binding, named in its own description since a configured table has no binding picker)',
          all(it['componentProps']['inputs']['dataPath'].startswith(
              '/api/firmware/solutions/%s/hardware?list=' % BC_BINDING) for it in scoped_items), scoped_items)
    check('every table on /display/hardware-chain carries a non-empty description', all(it.get('description') for it in items))
    boards_page = next(p for p in P if p['pageRoute'] == 'boards')
    check('/display/boards names "dedicated Board pages for going through all possible boards" (his words) in its own description',
          'all possible boards' in boards_page['description'])
    boards_rows = json.loads(boards_page['definition'])['rows']
    check('/display/boards gained no new tables (still the pre-existing 18 items)',
          sum(len(row['items']) for row in boards_rows) == 18)


# ---------------------------------------------------------------- part 7: the live door
def _live_door(check):
    from types import SimpleNamespace
    from falcon import testing
    import falcon
    from cmod.cmod_seed import CMOD_SEED_PAIRS
    from board.board_seed import BOARD_SEED_PAIRS
    from cmod.cmod_firmware_api import FirmwareAPI
    tables = {}
    mgr = SimpleNamespace(objectTables=tables, idList=[], db=None, saveObjToDB=lambda o: None)
    for _mid, pairs in (('board', BOARD_SEED_PAIRS), ('cmod', CMOD_SEED_PAIRS)):
        for name, cls, seed_rows in pairs:
            for row in seed_rows:
                o = cls(manager=mgr, **{k: v for k, v in row.items() if k != '_converge'})
                tables.setdefault(name, {})[o.id] = o
    app = falcon.App()
    FirmwareAPI(polServer=SimpleNamespace(falconServer=app, manager=mgr, idList=[]), manager=mgr)
    c = testing.TestClient(app)

    r = c.simulate_get('/api/firmware/solutions/%s/hardware' % BC_BINDING)
    check('GET /api/firmware/solutions/<binding>/hardware answers {ok, binding, board, soc, rows: {...}}',
          r.status_code == 200 and r.json['ok'] and r.json['binding'] == BC_BINDING and r.json['board'] == BOARD
          and set(r.json['rows']) == {'pins', 'soc_pins', 'pin_functions', 'signals', 'peripherals', 'registers',
                                      'fields', 'settings', 'field_settings', 'routes'}, r.text[:300])
    check('… and matches the pure derivation (same door, same rows, live or pure)',
          sorted(p['canonical'] for p in r.json['rows']['pins']) == sorted(p['canonical'] for p in _scope(BC_SOLUTION, BC_GRAPH, manager=None)['rows']['pins']))

    r2 = c.simulate_get('/api/firmware/solutions/%s/hardware?list=pins' % BC_BINDING)
    check('?list=pins narrows to {ok, rows: [...]} (class-rows-table\'s dataPath contract)',
          r2.status_code == 200 and r2.json['ok'] and isinstance(r2.json['rows'], list) and 'binding' not in r2.json, r2.text[:200])
    check('… and it is the SAME six pins as the full door\'s rows.pins',
          sorted(p['canonical'] for p in r2.json['rows']) == sorted(p['canonical'] for p in r.json['rows']['pins']))

    r3 = c.simulate_get('/api/firmware/solutions/%s/hardware?list=no-such-list' % BC_BINDING)
    check('an unknown ?list= is refused by name (never a silent empty list)',
          r3.status_code == 404 and not r3.json['ok'] and 'no-such-list' in r3.json['error'], r3.text[:200])

    r4 = c.simulate_get('/api/firmware/solutions/no-such-solution/hardware')
    check('an unknown solution 404s (the same _solution() guard every other door in this file already has)',
          r4.status_code == 404 and not r4.json['ok'])
