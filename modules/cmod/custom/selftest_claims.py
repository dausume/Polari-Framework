"""selftest_claims — ucd-0b (UNO_CORE_DEMO_PLAN.md §5f/§5g): PinClaim/PeripheralClaim derivation and the generated
GPIO + external-interrupt/pin-change register config over uno-sim-rig. Run by cmod_selftest.main() (claims_parts),
same shape as selftest_export.py's export_parts.
"""
import json


def claims_parts(check):
    def pin_and_peripheral_claims():
        _pin_and_peripheral_claims(check)

    def register_generation():
        _register_generation(check)

    def overrides_and_conflicts():
        _overrides_and_conflicts(check)

    def refs_and_validate():
        _refs_and_validate(check)

    def live_api():
        _live_api(check)

    def button_clock():
        _button_clock(check)

    return (pin_and_peripheral_claims, register_generation, overrides_and_conflicts, refs_and_validate, live_api, button_clock)


SOLUTION, GRAPH = 'uno-sim-rig', 'uno-sim-rig-graph'


def _by_canonical(pins):
    return {p['name'].split(':', 1)[1]: p for p in pins}


def _pin_and_peripheral_claims(check):
    from cmod.custom import claims as C
    pins = C.pin_claims(SOLUTION, GRAPH)
    check('pin_claims(uno-sim-rig): exactly the 5 bound pins (A0, D6, D13, D0, D1)',
          {p['name'] for p in pins} == {'%s:%s' % (SOLUTION, c) for c in ('A0', 'D6', 'D13', 'D0', 'D1')}, sorted(p['name'] for p in pins))
    by = _by_canonical(pins)
    check('A0 -> analog-in, mode alt, pin_function ADC0 (from the board pin\'s OWN known signal, never guessed)',
          by['A0']['requirement_kind'] == 'analog-in' and by['A0']['mode'] == 'alt' and by['A0']['pin_function'] == 'atmega328p:PC0:ADC0', by['A0'])
    check('D6 -> pwm-out, mode alt, pin_function OC0A', by['D6']['requirement_kind'] == 'pwm-out' and by['D6']['mode'] == 'alt'
          and by['D6']['pin_function'] == 'atmega328p:PD6:OC0A', by['D6'])
    check('D13 -> digital-out, mode out, initial low (the default — no override)',
          by['D13']['requirement_kind'] == 'digital-out' and by['D13']['mode'] == 'out' and by['D13']['initial'] == 'low'
          and by['D13']['pin_function'] == '', by['D13'])
    check('D0 -> uart-rx alt RXD; D1 -> uart-tx alt TXD (settled from the BOARD PIN\'s own signal — the shared usart_init '
          'atom alone cannot tell RX from TX by port shape)',
          by['D0']['requirement_kind'] == 'uart-rx' and by['D0']['pin_function'] == 'atmega328p:PD0:RXD'
          and by['D1']['requirement_kind'] == 'uart-tx' and by['D1']['pin_function'] == 'atmega328p:PD1:TXD', (by['D0'], by['D1']))
    check('every claim is provenance derived (no override applied) and status ok (no conflict, no incomplete)',
          all(p['provenance'] == 'derived' and p['status'] == 'ok' for p in pins), pins)
    check('D6\'s representative task is pwm_init (the setup atom, not the dispatcher "apply" or the bare "pwm" use)',
          by['D6']['task'] == 'pwm_init' and 'pwm' in by['D6']['notes'], by['D6'])

    periph = C.peripheral_claims(SOLUTION, GRAPH)
    pby = {p['name'].split(':', 1)[1]: p for p in periph}
    check('TIMER2 is ONE whole-peripheral exclusive claim (hal_tick/hal_millis — never split by channel in this demo)',
          pby['TIMER2']['usage'] == 'exclusive' and pby['TIMER2']['status'] == 'ok'
          and json.loads(pby['TIMER2']['tasks_json']) == ['tick_init'], pby['TIMER2'])
    check('USART0 is ONE exclusive claim (usart_init + send — cooperating init/use, not a conflict)',
          pby['USART0']['usage'] == 'exclusive' and pby['USART0']['status'] == 'ok'
          and set(json.loads(pby['USART0']['tasks_json'])) == {'usart_init', 'send'}, pby['USART0'])
    check('TIMER0:A is exclusive (pwm_init + pwm); TIMER0 (channel-less) is the shared-config prescaler (TCCR0B)',
          pby['TIMER0:A']['usage'] == 'exclusive' and pby['TIMER0']['usage'] == 'shared-config'
          and pby['TIMER0']['registers_json'] == '["TCCR0B"]', (pby['TIMER0:A'], pby['TIMER0']))
    check('ADC:0 is shared-read (the channel number 0 comes from A0\'s own PinClaim, never guessed)',
          pby['ADC:0']['usage'] == 'shared-read' and pby['ADC:0']['status'] == 'ok', pby.get('ADC:0', pby))
    check('GPIO PORTB / GPIO PORTD are shared-config (plain DDR/PORT touches, several tasks legitimately share them)',
          pby['GPIO PORTB']['usage'] == 'shared-config' and pby['GPIO PORTD']['usage'] == 'shared-config')
    check('no peripheral claim conflicts in the real seeded graph', not any(p['status'] == 'conflict' for p in periph), periph)


def _register_generation(check):
    from cmod.custom import claims as C
    gen = C.register_settings(SOLUTION, GRAPH)
    by_reg = {r['register'].rsplit(':', 1)[-1]: r for r in gen['RegisterSetting']}
    check('register_settings(uno-sim-rig): EXACTLY DDRB and DDRD — GPIO direction only (timer/USART config stays in '
          'the HAL this slice, named, never silently generated)', set(by_reg) == {'DDRB', 'DDRD'}, sorted(by_reg))
    check('EICRA/EIFR/EIMSK/PCMSK/PCICR are ABSENT (no interrupt-in claim exists in uno-sim-rig today)',
          not ({'EICRA', 'EIFR', 'EIMSK', 'PCICR'} & set(by_reg)) and not any(r.startswith('PCMSK') for r in by_reg), sorted(by_reg))

    from board.custom import board_object as BO
    r = BO.rows_for('arduino-uno-r3')
    d13_pin = BO.pin_by_canonical(r, 'D13')['soc_pin']   # PB5 — derived from the SocPin, never assumed
    d6_pin = BO.pin_by_canonical(r, 'D6')['soc_pin']     # PD6
    check('DDRB: derived from D13\'s own SocPin (PB5) -> bit 5 set, value 0x20, 8-char value_bits, write_mask == value',
          d13_pin == 'PB5' and by_reg['DDRB']['value'] == '0x20' and by_reg['DDRB']['value_bits'] == '00100000'
          and by_reg['DDRB']['write_mask'] == '0x20' and by_reg['DDRB']['status'] == 'planned', by_reg['DDRB'])
    check('DDRD: derived from D6\'s own SocPin (PD6) -> bit 6 set, value 0x40',
          d6_pin == 'PD6' and by_reg['DDRD']['value'] == '0x40' and by_reg['DDRD']['status'] == 'planned', by_reg['DDRD'])

    fs_by_reg = {}
    for f in gen['RegisterFieldSetting']:
        fs_by_reg.setdefault(f['register_setting'].rsplit(':', 2)[-2], []).append(f)
    ddb5 = next(f for f in gen['RegisterFieldSetting'] if f['register_field'] == 'atmega328p:DDRB.DDB5')
    # ucd-0b2d (§5h, the HardwareBinding fix): hal_led_init now derives its own D13 row (bound like `led` is — one
    # pin, two tasks of one Purpose) and, same convention as pwm_init/D6 and usart_init/D0-D1 below, the '_init'
    # task that actually calls the DDR write is representative — never 'led' (which only ever wrote PORTB).
    check('the DDRB.DDB5 field setting NAMES its PinClaim (uno-sim-rig:D13), its task (led_init) and its rule — the row '
          'a novice reads to see WHY', ddb5['pin_claim'] == 'uno-sim-rig:D13' and ddb5['task'] == 'led_init' and ddb5['rule'] == 'ddr-from-digital-out'
          and ddb5['value'] == '1' and 'output' in ddb5['meaning'], ddb5)
    ddd6 = next(f for f in gen['RegisterFieldSetting'] if f['register_field'] == 'atmega328p:DDRD.DDD6')
    check('the DDRD.DDD6 field setting names its PinClaim (D6) and task (pwm_init)',
          ddd6['pin_claim'] == 'uno-sim-rig:D6' and ddd6['task'] == 'pwm_init', ddd6)

    routes = {r['name']: r for r in gen['SignalRoute']}
    check('one SignalRoute per alt-mode PinClaim (A0/ADC0, D6/OC0A, D0/RXD, D1/TXD) — all PLANNED (their enabling '
          'bits live in the HAL, not generated this slice, so never silently marked active)',
          {r.split(':', 1)[1] for r in routes} == {'A0:ADC0', 'D6:OC0A', 'D0:RXD', 'D1:TXD'}
          and all(r['status'] == 'planned' for r in routes.values()), routes)


def _overrides_and_conflicts(check):
    from cmod.custom import claims as C
    ov = {'D13': {'mode': 'in', 'pull': 'up', 'edge': 'any'}}
    pins = C.pin_claims(SOLUTION, GRAPH, overrides=ov)
    d13 = next(p for p in pins if p['name'].endswith(':D13'))
    check('an override {mode:in, pull:up, edge:any} on D13 (a digital-out by default) is APPLIED and marked canvas',
          d13['mode'] == 'in' and d13['pull'] == 'up' and d13['edge'] == 'any' and d13['provenance'] == 'canvas', d13)

    gen = C.register_settings(SOLUTION, GRAPH, overrides=ov)
    by_reg = {r['register'].rsplit(':', 1)[-1]: r for r in gen['RegisterSetting']}
    check('the override FLIPS DDRB to input (bit 5 -> 0) — the generated direction follows the EFFECTIVE mode, not '
          'the static requirement_kind', by_reg['DDRB']['value'] == '0x00', by_reg['DDRB'])
    check('…and makes a PORTB pull-up setting (bit 5 -> 1, no PORT write existed before the override)',
          'PORTB' in by_reg and by_reg['PORTB']['value'] == '0x20', by_reg.get('PORTB'))
    # D13 = PB5 has no EXINT alternate function (only INT0/INT1 on PD2/PD3 do — datasheet Table 14-9) — so an edge
    # override on D13 takes the PCINT path (PCMSK0/PCICR0), not EICRA/EIMSK. Proved directly: the SAME detector that
    # register_settings uses correctly finds the EXINT path on PD2/PD3, where the datasheet DOES put it.
    check('…and enables it via the PIN-CHANGE path (PCMSK0.PCINT5 + PCICR.PCIE0) — D13/PB5 has no INTn function',
          by_reg.get('PCICR') is not None and by_reg.get('PCMSK0') is not None and by_reg['PCMSK0']['value'] == '0x20', by_reg)
    route = next(r for r in gen['SignalRoute'] if r['name'] == 'uno-sim-rig:D13:PCINT5')
    check('…and the D13:PCINT5 SignalRoute is now ACTIVE (its enabling field settings exist)', route['status'] == 'active', route)

    from cmod.custom import claims as C2
    from board.custom import soc_atmega328p as S
    tables = C2._chain_tables(None)
    soc_pins = C2._index(tables, 'SocPin')
    check('the EXINT detector itself: PD2 -> INT0, PD3 -> INT1 (the real path, proved directly since uno-sim-rig '
          'binds neither pin today)', C2._int_capable(soc_pins['%s:PD2' % S.SOC]) == ('EXINT', 'INT0')
          and C2._int_capable(soc_pins['%s:PD3' % S.SOC]) == ('EXINT', 'INT1'), None)
    check('…and a plain GPIO pin with no INTn (PD4) falls back to PCINT (PCINT20)',
          C2._int_capable(soc_pins['%s:PD4' % S.SOC]) == ('PCINT', 'PCINT20'))

    # overlapping fields -> conflict, the generic combine primitive tested directly (two distinct pins can never
    # naturally collide on one bit — this proves the DETECTOR, the thing a future multi-claim bug would trip)
    f = C2._index(tables, 'RegisterField')['atmega328p:DDRB.DDB5']
    specs = [(f, 1, 'uno-sim-rig:D13', '', 'led', 'rule-a'), (f, 0, 'uno-sim-rig:other', '', 'other-task', 'rule-b')]
    rs, fss = C2._combine('uno-sim-rig', 'DDRB', 'init', specs, tables)
    check('two field settings whose bits overlap -> BOTH conflict + the RegisterSetting conflicts (never last-write-wins)',
          rs['status'] == 'conflict' and all(x['status'] == 'conflict' for x in fss) and len(fss) == 2, (rs, fss))
    check('…and the conflict names both colliding field settings', 'uno-sim-rig:DDRB.DDB5:init' in rs['notes'], rs['notes'])


def _refs_and_validate(check):
    from cmod.custom import claims as C
    tables = C._chain_tables(None)
    names = {cls: {r['name'] for r in tables.get(cls, [])} for cls in ('PinFunction', 'RegisterField', 'BoardPin', 'SocPin', 'Register')}
    from cmod.custom import firmware as FW
    assign_names = {r['name'] for r in FW.assignments_for(GRAPH, SOLUTION)}

    pins = C.pin_claims(SOLUTION, GRAPH)
    bad = []
    for p in pins:
        if p['board_pin'] not in names['BoardPin']:
            bad.append('board_pin %s' % p['board_pin'])
        if p['soc_pin'] not in names['SocPin']:
            bad.append('soc_pin %s' % p['soc_pin'])
        if p['pin_function'] and p['pin_function'] not in names['PinFunction']:
            bad.append('pin_function %s' % p['pin_function'])
        if p['assignment'] not in assign_names:
            bad.append('assignment %s' % p['assignment'])
    check('every PinClaim reference (board_pin, soc_pin, pin_function, assignment) resolves to a real row', not bad, bad)

    gen = C.register_settings(SOLUTION, GRAPH)
    bad2 = []
    rs_names = {r['name'] for r in gen['RegisterSetting']}
    for rs in gen['RegisterSetting']:
        if rs['register'] not in names['Register']:
            bad2.append('register %s' % rs['register'])
    for fs in gen['RegisterFieldSetting']:
        if fs['register_field'] not in names['RegisterField']:
            bad2.append('register_field %s' % fs['register_field'])
        if fs['register_setting'] not in rs_names:
            bad2.append('register_setting %s' % fs['register_setting'])
    for rt in gen['SignalRoute']:
        if rt['pin_function'] not in names['PinFunction']:
            bad2.append('pin_function %s' % rt['pin_function'])
    check('every RegisterSetting/RegisterFieldSetting/SignalRoute reference resolves to a real row', not bad2, bad2)

    from cmod.custom import firmware as FW2
    fs = {'name': SOLUTION, 'graph': GRAPH, 'board_definition': 'arduino-uno-r3', 'board_variable': ''}
    ok, why, details = FW2.validate(fs, manager=None)
    check('validate(uno-sim-rig) is STILL ok with the claims wired in (no conflict, nothing incomplete today)',
          ok and 'incomplete' not in why, why)
    check('…and validate()\'s details now carry the claims/peripheral_claims rows too',
          len(details.get('claims', [])) == 5 and len(details.get('peripheral_claims', [])) >= 6, details.keys())


def _live_api(check):
    """The live doors: GET /api/firmware/solutions/{name} materializes the claims chain into the manager's own
    tables (PinClaim/PeripheralClaim/RegisterSetting/RegisterFieldSetting/SignalRoute — upsert by name), POST
    .../assign persists a canvas `config` onto RegisterAssignment.config_json (merged, never clobbering an earlier
    choice), and GET .../pins/{canonical}/chain reuses board.custom.hardware_chain.chain_for over the SAME tables."""
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

    r = c.simulate_get('/api/firmware/solutions/%s' % SOLUTION)
    check('GET /api/firmware/solutions/<name> carries claims/peripheral_claims/register_settings/field_settings/routes',
          r.status_code == 200 and len(r.json['claims']) == 5 and len(r.json['register_settings']) == 2
          and len(r.json['field_settings']) == 2 and len(r.json['routes']) == 4, r.text[:300])
    check('…and MATERIALIZES them into the manager\'s own tables (upsert by name — the object pages read these)',
          len(tables.get('PinClaim', {})) == 5 and len(tables.get('RegisterSetting', {})) == 2
          and len(tables.get('SignalRoute', {})) == 4, {k: len(v) for k, v in tables.items() if k in
                                                         ('PinClaim', 'PeripheralClaim', 'RegisterSetting', 'RegisterFieldSetting', 'SignalRoute')})

    r2 = c.simulate_post('/api/firmware/solutions/%s/assign' % SOLUTION,
                         json={'task': 'led', 'port': 'on', 'lives_on': 'arduino-uno-r3:D13',
                              'config': {'mode': 'in', 'pull': 'up', 'edge': 'any'}})
    check('POST .../assign with a `config` body PERSISTS it onto the RegisterAssignment (fs-1\'s drag + the pin page\'s choice, one door)',
          r2.status_code == 200 and r2.json['ok'], r2.text[:300])
    r3 = c.simulate_get('/api/firmware/solutions/%s' % SOLUTION)
    d13 = next(x for x in r3.json['claims'] if x['name'].endswith(':D13'))
    check('…re-GET re-derives D13\'s PinClaim WITH the persisted override (mode in, pull up, edge any, canvas)',
          d13['mode'] == 'in' and d13['pull'] == 'up' and d13['edge'] == 'any' and d13['provenance'] == 'canvas', d13)
    check('…and the register settings now include the pin-change enable (PCMSK0/PCICR), persisted across the re-GET',
          any(x['register'].endswith('PCMSK0') for x in r3.json['register_settings'])
          and any(x['register'].endswith('PCICR') for x in r3.json['register_settings']), [x['register'] for x in r3.json['register_settings']])

    r4 = c.simulate_get('/api/firmware/solutions/%s/pins/D6/chain' % SOLUTION)
    check('GET .../pins/D6/chain -> the PinClaim + its route + the board\'s own hardware-chain hops (BoardPin..RegisterField)',
          r4.status_code == 200 and r4.json['claim']['pin_function'] == 'atmega328p:PD6:OC0A'
          and r4.json['hops'][0]['kind'] == 'BoardPin' and len(r4.json['hops']) > 5, r4.text[:300])
    r5 = c.simulate_get('/api/firmware/solutions/%s/pins/NOPE/chain' % SOLUTION)
    check('…an unclaimed/unknown pin is refused by name, 404', r5.status_code == 404, r5.text[:200])


#: ucd-0e2b: the SAME chain over the second solution (uno-button-clock), its AUTHORED D2/D3 edge/pull (never
#: derivable from a register name, §5f point 1 — PURE_CONFIG_SEED is the pure-mode stand-in for a live canvas
#: edit) read back through claims.py's own pure fallback.
BC_SOLUTION, BC_GRAPH = 'uno-button-clock', 'uno-button-clock-graph'


def _button_clock(check):
    from cmod.custom import claims as C
    pins = C.pin_claims(BC_SOLUTION, BC_GRAPH)
    by = _by_canonical(pins)
    check('pin_claims(uno-button-clock) binds D0, D1, D2, D3, D6, D13 — 6 pins',
          set(by) == {'D0', 'D1', 'D2', 'D3', 'D6', 'D13'}, sorted(by))
    check('D2: interrupt-in, mode alt, pull up, edge falling, provenance canvas (the button, debounced, internal pull-up)',
          by['D2']['requirement_kind'] == 'interrupt-in' and by['D2']['mode'] == 'alt' and by['D2']['pull'] == 'up'
          and by['D2']['edge'] == 'falling' and by['D2']['provenance'] == 'canvas' and by['D2']['status'] == 'ok', by['D2'])
    check('D3: interrupt-in, mode alt, pull none, edge any, provenance canvas (the witness pin — driven by D6, no pull needed)',
          by['D3']['requirement_kind'] == 'interrupt-in' and by['D3']['mode'] == 'alt' and by['D3']['pull'] == 'none'
          and by['D3']['edge'] == 'any' and by['D3']['provenance'] == 'canvas' and by['D3']['status'] == 'ok', by['D3'])
    check('D6/D13: digital-out, mode out, initial low, provenance canvas (the LED lines, authored explicitly though they '
          'restate the default)', all(by[p]['requirement_kind'] == 'digital-out' and by[p]['mode'] == 'out'
          and by[p]['initial'] == 'low' and by[p]['provenance'] == 'canvas' for p in ('D6', 'D13')), (by['D6'], by['D13']))
    check('D2\'s representative task is button_init (the setup atom), D3\'s is sense_init — never the "called"/"button"/"sense" '
          'runtime readers', by['D2']['task'] == 'button_init' and by['D3']['task'] == 'sense_init', (by['D2'], by['D3']))

    gen = C.register_settings(BC_SOLUTION, BC_GRAPH)
    rs = {r['register'].rsplit(':', 1)[1]: r for r in gen['RegisterSetting']}
    check('RegisterSetting: DDRD = 0x40 mask 0x4C (DDD6=1, DDD2=0, DDD3=0), DDRB = 0x20 mask 0x20 (DDB5=1)',
          rs['DDRD']['value'] == '0x40' and rs['DDRD']['write_mask'] == '0x4C'
          and rs['DDRB']['value'] == '0x20' and rs['DDRB']['write_mask'] == '0x20', (rs['DDRD'], rs['DDRB']))
    check('PORTD = 0x04 mask 0x04 (PORTD2=1, the pull-up; D6\'s initial=low needs no PORT write — the reset value is already 0)',
          rs['PORTD']['value'] == '0x04' and rs['PORTD']['write_mask'] == '0x04', rs['PORTD'])
    check('EICRA = 0x06 mask 0x0F (ISC01:00=10 falling for INT0, ISC11:10=01 any for INT1)',
          rs['EICRA']['value'] == '0x06' and rs['EICRA']['write_mask'] == '0x0F', rs['EICRA'])
    check('EIFR = 0x03 mask 0x03, a PLAIN write (access w1c — clearing INTF0/INTF1 never read-modify-writes)',
          rs['EIFR']['value'] == '0x03' and rs['EIFR']['write_mask'] == '0x03', rs['EIFR'])
    check('EIMSK = 0x03 mask 0x03 (INT0 + INT1 both enabled)',
          rs['EIMSK']['value'] == '0x03' and rs['EIMSK']['write_mask'] == '0x03', rs['EIMSK'])

    routes = {r['name'].rsplit(':', 1)[1]: r for r in gen['SignalRoute']}
    check('SignalRoute D2:INT0 and D3:INT1 are ACTIVE (a RegisterFieldSetting that actually enables the interrupt exists '
          'for each — never merely "planned")',
          routes['INT0']['status'] == 'active' and routes['INT0']['pin_function'] == 'atmega328p:PD2:INT0'
          and routes['INT1']['status'] == 'active' and routes['INT1']['pin_function'] == 'atmega328p:PD3:INT1', routes)

    from cmod.custom import firmware as FW
    fs = {'name': BC_SOLUTION, 'graph': BC_GRAPH, 'board_definition': 'arduino-uno-r3', 'board_variable': ''}
    ok, why, details = FW.validate(fs, manager=None)
    check('validate(uno-button-clock) over the pure PURE_CONFIG_SEED path: ok, 0 incomplete claims', ok and 'incomplete' not in why, why)
