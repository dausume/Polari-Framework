"""hwnocode_solve_selftest — cb-3 (AI-Notes/plans/COMPONENT_BINDING_PLAN.md §5): THE SCHEMATIC SOLVER over the proven HardwareSolution
uno-light-system, and the same code on a second chip. Checks:
  - the record (custom/solved/uno-light-system.json) equals a fresh solve: not stale, same rows
  - the UNO: two components cut from the circuit uno-button-clock (the light on D6 with its D3 sense line, the button on D2); both
    solved; R1 220 ohm placed as the light's series resistor; the chip's own pull-up placed on D2 from the firmware's PinClaim; guard and
    filter not needed, each with its reason (one board, one logic level; debounce_ms in the firmware)
  - every finding of the board's electrical check lands exactly once: on a component, or on the whole solution
  - two HardwareFeature rows, every column filled from the HAL variables, the catom assertions and the twin kinds, bound to
    uno-light-system, its device and its simulator pair; both complete
  - each rule is LIVE: take the PinClaim away (pull needed), the debounce knob (filter needed), R1 (series needed), add another board on the
    button's net (guard needed): each blocks the component and says why; a changed input changes the inputs sha (stale)
  - the C3 design (c3-light on esp32-c3, esp32c3-light) solves through the same code: the light solved, the button blocked (its firmware
    binding is not resolved, so the pull is not seen) and named; its features are not complete (no HardwareSolution)
  - the seed carries the record's rows, and every row constructs its class

    PYTHONPATH=.:modules python3 -m hwnocode.hwnocode_solve_selftest      # from polari-framework/ (about a minute: the solver runs 7 times)
"""
import inspect
import sys

passed = total = 0
SOL = 'uno-light-system'


def check(label, cond, extra=''):
    global passed, total
    total += 1
    passed += bool(cond)
    print('  [%s] %s %s' % ('\033[0;32mPASS\033[0m' if cond else '\033[0;31mFAIL\033[0m', label, extra if not cond else ''))


def _by(res, cls, **kw):
    return [r for r in res[cls] if all(r.get(k) == v for k, v in kw.items())]


def _check_of(res, comp, rule):
    return [c for c in res['SchematicComponentCheck'] if c['component'] == comp and c['rule'] == rule]


def record_and_uno(tables):
    from hwnocode.custom import schematic_solve as S
    fresh, rec, same, why = S.compare(SOL, tables)
    check('the record equals a fresh solve (not stale): %s' % why, same and rec is not None, why)
    comps = {c['name']: c for c in fresh['SchematicComponent']}
    light, button = '%s:ubc-led1' % SOL, '%s:ubc-sw1' % SOL
    check('two components cut from uno-button-clock: the light and the button', sorted(comps) == [light, button], sorted(comps))
    check('both are solved by the solver, bound to the solution and its circuit',
          all(c['solve_state'] == 'solved' and c['solved_by'] == S.SOLVER and c['hardware_solution'] == SOL and c['circuit'] == 'uno-button-clock'
              for c in comps.values()), [(c['name'], c['solve_state'], c['findings']) for c in comps.values()])
    pins = {n: [p['pin'] for p in sorted(_by(fresh, 'SchematicComponentPort', component=n, kind='signal'), key=lambda p: p['order'])] for n in comps}
    check('the light lands on D6 (its output) and D3 (the sense line), the button on D2', pins == {light: ['D6', 'D3'], button: ['D2']}, pins)
    r1 = _by(fresh, 'SchematicComponentPart', component=light, role='series')
    check('R1 220 ohm is the light\'s series resistor, on D6, from the circuit', [(p['ref'], p['value'], p['port']) for p in r1] == [('R1', '220 ohm', 'D6')], r1)
    pu = _by(fresh, 'SchematicComponentPart', component=button, role='pull')
    check('the chip\'s own pull-up on D2 is a part, placed by the firmware\'s PinClaim',
          [(p['part_kind'], p['port'], p['placed_by']) for p in pu] == [('internal-pull-up', 'D2', 'firmware')] and 'uno-light:D2' in pu[0]['rule'], pu)
    st = {(c['component'], c['rule']): c['status'] for c in fresh['SchematicComponentCheck'] if c['rule'] in ('pull', 'series', 'guard', 'filter')}
    check('the four rules: light pull/guard/filter not needed, series placed; button pull placed, series/guard/filter not needed', st == {
        (light, 'pull'): 'not-needed', (light, 'series'): 'placed', (light, 'guard'): 'not-needed', (light, 'filter'): 'not-needed',
        (button, 'pull'): 'placed', (button, 'series'): 'not-needed', (button, 'guard'): 'not-needed', (button, 'filter'): 'not-needed'}, st)
    f = _check_of(fresh, button, 'filter')[0]['detail']
    g = _check_of(fresh, button, 'guard')[0]['detail']
    check('each "not needed" says why: the debounce knob, one board on the net', 'debounce_ms 30' in f and 'one board, one logic level' in g, (f, g))
    from board.custom import electrical_check as EC
    findings = EC.check('uno-button-clock', 'uno-light', tables)
    keyed = [(c['rule'], c['subject']) for c in fresh['SchematicComponentCheck'] if c['rule'] not in ('pull', 'series', 'guard', 'filter')]
    check('every electrical finding lands exactly once (%d findings)' % len(findings),
          sorted(keyed) == sorted((x['rule'], x.get('subject', '')) for x in findings), (len(keyed), len(findings)))
    und = [c for c in fresh['SchematicComponentCheck'] if c['status'] == 'undetermined']
    check('an undetermined number is kept and named, never turned into a value (the LED forward voltage, the switch resistance)',
          und and all(c['detail'] for c in und) and any('forward voltage' in c['detail'] for c in und))
    return fresh


def features(fresh):
    from hwnocode.custom import feature_columns as FC
    feats = {f['name']: f for f in fresh['HardwareFeature']}
    check('one HardwareFeature per component', sorted(feats) == ['%s:button' % SOL, '%s:light' % SOL], sorted(feats))
    b, l = feats['%s:button' % SOL], feats['%s:light' % SOL]
    check('the button: BUTTON_PIN int.ext on D2 (PD2), LightState_t fields it changes, falling edge, active-low, debounced',
          b['nocode_variable'] == 'BUTTON_PIN' and b['pins'] == 'D2 (PD2)' and 'toggles' in b['struct_field']
          and b['struct_instance'] == 'LightState_t->LightState' and 'falling edge' in b['protocol'] and 'active-low' in b['protocol']
          and 'debounced' in b['protocol'], b)
    check('the light: LED_PIN and SENSE_PIN on D6 (PD6) and D3 (PD3), field led_on, active-high',
          l['nocode_variable'] == 'LED_PIN, SENSE_PIN' and l['pins'] == 'D6 (PD6), D3 (PD3)' and l['struct_field'] == 'led_on'
          and 'active-high' in l['protocol'], l)
    check('both are bound to uno-light-system, the real UNO and its simavr twin pair, and run uno-light',
          all(f['hardware_solution'] == SOL and f['device'] == 'arduino-uno-r3' and f['firmware_variant'] == 'uno-light'
              and 'atmega328p twin' in f['simulator'] for f in feats.values()), [f['simulator'] for f in feats.values()])
    check('the screen side: a bridge input (apply_command) and a bridge output (telemetry_send)',
          all(f['ui_direction'] == 'bridge input + bridge output' and 'apply_command' in f['ui_control'] for f in feats.values()))
    states = {n: FC.state(f, fresh['SchematicComponent']) for n, f in feats.items()}
    check('both features are complete: every required column filled, the component solved, the device paired with a simulator',
          all(s['complete'] for s in states.values()), {n: s['words'] for n, s in states.items()})
    check('pins are chosen (the bench wiring, the variant\'s knobs); every other column suggested (derived)',
          all({c['key']: c['source'] for c in s['columns']}['pins'] == 'chosen' and {c['key']: c['source'] for c in s['columns']}['protocol'] == 'suggested'
              for s in states.values()))
    check('each component carries the protocol its feature derived', all(
        next(c for c in fresh['SchematicComponent'] if c['name'] == f['schematic_component'])['protocol'] == f['protocol'] for f in feats.values()))


def _mutated(tables, **cls_rows):
    t = dict(tables)
    t.update(cls_rows)
    return t


def live_rules(tables, fresh):
    from hwnocode.custom import schematic_solve as S
    from cmod.custom import catom_variables as CV
    light, button = '%s:ubc-led1' % SOL, '%s:ubc-sw1' % SOL
    state = lambda res, n: next(c for c in res['SchematicComponent'] if c['name'] == n)   # noqa: E731
    # 1. no PinClaim pull: the binding resolves with no claims
    t = _mutated(tables, _resolved={'uno-light': ('arduino-uno-r3', [])})
    res = S.solve('uno-light', 'arduino-uno-r3', 'uno-button-clock', SOL, t)
    c = state(res, button)
    check('no PinClaim pull on D2: the button is blocked, pull needed, said in words',
          c['solve_state'] == 'blocked' and _check_of(res, button, 'pull')[0]['status'] == 'needed' and 'floating' in _check_of(res, button, 'pull')[0]['detail'],
          c['findings'])
    check('... and a changed input changes the inputs sha (the record would read stale)', res['inputs_sha256'] != fresh['inputs_sha256'])
    # 2. no debounce in the firmware
    real = CV.variant_knobs
    CV.variant_knobs = lambda v, soc, rows=None: dict(real(v, soc, rows), debounce_ms=0)
    try:
        res = S.solve('uno-light', 'arduino-uno-r3', 'uno-button-clock', SOL, tables)
    finally:
        CV.variant_knobs = real
    check('debounce_ms 0: a filter capacitor at D2 is needed (its value undetermined), the button blocked',
          state(res, button)['solve_state'] == 'blocked' and _check_of(res, button, 'filter')[0]['status'] == 'needed'
          and 'undetermined' in _check_of(res, button, 'filter')[0]['detail'], _check_of(res, button, 'filter'))
    # 3. no R1: the LED straight on the pin
    comps = [dict(x, pins_json='["LED_CONTROL", "GND"]') if x['name'] == 'ubc-led1' else x
             for x in tables['CircuitComponentDefinition'] if x['name'] != 'ubc-r1']
    res = S.solve('uno-light', 'arduino-uno-r3', 'uno-button-clock', SOL, _mutated(tables, CircuitComponentDefinition=comps))
    check('no R1: the light needs a series resistor and is blocked', state(res, light)['solve_state'] == 'blocked'
          and _check_of(res, light, 'series')[0]['status'] == 'needed', _check_of(res, light, 'series'))
    # 4. another board drives the button's net
    other = {'name': 'other-board:IO1@uno-button-clock:BUTTON_INPUT', 'board': 'other-board', 'board_pin': 'other-board:IO1',
             'circuit': 'uno-button-clock', 'circuit_net': 'ubc-net-button-input', 'role': 'output', 'provenance': 'test'}
    res = S.solve('uno-light', 'arduino-uno-r3', 'uno-button-clock', SOL, _mutated(tables, BoardPinNet=list(tables['BoardPinNet']) + [other]))
    g = _check_of(res, button, 'guard')[0]
    check('another board on BUTTON_INPUT: a guard diode is needed, naming it', state(res, button)['solve_state'] == 'blocked'
          and g['status'] == 'needed' and 'other-board' in g['detail'], g)


def second_chip(tables):
    from hwnocode.custom import schematic_solve as S
    from hwnocode.custom import feature_columns as FC
    res = S.solve('esp32c3-light', 'esp32-c3', 'c3-light', '', tables)
    st = {c['title']: c['solve_state'] for c in res['SchematicComponent']}
    check('the C3 design through the same code: the light solved, the button blocked', st == {'Light LED1': 'solved', 'Button SW1': 'blocked'}, st)
    b = [c for c in res['SchematicComponentCheck'] if c['rule'] == 'binding']
    check('... the reason named: esp32c3-light resolves to no firmware binding, so its pull claim is not read', b and b[0]['status'] == 'undetermined', b)
    feats = res['HardwareFeature']
    check('the C3 features fill from the C3 HAL (GPIO0/GPIO1, GPIO3) and the C3 twin', sorted(f['pins'] for f in feats) == ['GPIO0, GPIO1', 'GPIO3']
          and all('esp32c3 twin' in f['simulator'] for f in feats), [(f['pins'], f['simulator']) for f in feats])
    check('... and are not complete: no HardwareSolution binds them', all(not FC.state(f, res['SchematicComponent'])['complete']
                                                                          and 'Hardware solution' in FC.state(f, res['SchematicComponent'])['missing'] for f in feats))


def seeded(fresh):
    from hwnocode.hwnocode_seed import HWNOCODE_SEED_PAIRS
    from hwnocode.custom import schematic_solve as S
    pairs = {n: (c, rows) for n, c, rows in HWNOCODE_SEED_PAIRS if n in S.CLASSES}
    missing = [(n, r['name']) for n in S.CLASSES for r in fresh[n] if r['name'] not in {x['name'] for x in pairs[n][1]}]
    check('the seed carries every solved row of the record', not missing, missing[:5])
    stray = []
    for n, (cls, rows) in pairs.items():
        params = set(inspect.signature(cls.__init__).parameters)
        for r in rows:
            bad = [k for k in r if k not in params and k != '_converge']
            if bad:
                stray.append((n, r['name'], bad))
            cls(**{k: v for k, v in r.items() if k != '_converge'})
    check('every seeded row constructs its class with no stray field', not stray, stray[:5])
    from hwnocode.objects.hwnocode.SchematicComponentCheck import SchematicComponentCheck as K
    check('every check status is from the class\'s own list', all(r['status'] in K.STATUSES for r in pairs['SchematicComponentCheck'][1]))


def kicad(tables):
    """cb-6: the whole solution as one KiCad sheet. The design needs no engine; the render does (skipped, said, when none is reachable)."""
    from hwnocode.custom import schematic_kicad as K
    from hwnocode.custom import schematic_solve as S
    rec = S.load(SOL)
    d = K.design(rec, tables)
    parts = {c['ref']: c for c in d['components'] if c['role'] != 'header'}
    check('the sheet carries the physical parts: LED1, R1, SW1 (the chip\'s own pull-up is not a part on it, and is listed as inside the chip)',
          sorted(parts) == ['LED1', 'R1', 'SW1'] and any('internal-pull-up on D2' in x for x in d['inside_chip']), (sorted(parts), d['inside_chip']))
    circuit = {c['name']: c for c in tables['CircuitComponentDefinition'] if c.get('circuit_name') == 'uno-button-clock'}
    from board.custom import electrical_check as EC
    same = all(sorted(parts[r]['pins'].values()) == sorted(EC._pins(circuit[n])) for r, n in (('LED1', 'ubc-led1'), ('R1', 'ubc-r1'), ('SW1', 'ubc-sw1')))
    check('every part pin is on the net its circuit row names (LED anode/cathode, R1, SW1)', same and parts['LED1']['pins'] == {'A': 'LED_ANODE', 'K': 'GND'},
          {r: c['pins'] for r, c in parts.items()})
    hdr = {(c['value'], pin): net for c in d['components'] if c['role'] == 'header' for pin, net in c['pins'].items()}
    check('the UNO headers are wired by the board\'s own rows: D2 -> BUTTON_INPUT, D3 and D6 -> LED_CONTROL (the jumper), GND pins -> GND',
          hdr.get(('DIGITAL_L', '3')) == 'BUTTON_INPUT' and hdr.get(('DIGITAL_L', '4')) == 'LED_CONTROL' and hdr.get(('DIGITAL_L', '7')) == 'LED_CONTROL'
          and hdr.get(('POWER', '6')) == 'GND' and set(hdr.values()) == {'BUTTON_INPUT', 'LED_CONTROL', 'GND'}, hdr)
    libs = {'Device:LED': '(symbol "LED" (pin passive line (name "K") (number "1")) (pin passive line (name "A") (number "2")))'}
    libs.update({k: '(symbol "x")' for k in K.libs_needed(d) if k not in libs})
    want = {}
    for c in d['components']:
        for pin, net in c['pins'].items():
            want.setdefault(net, []).append((c['ref'], {'A': '2', 'K': '1'}.get(pin, pin) if c['ref'] == 'LED1' else pin))
    net = '(export (nets %s))' % ' '.join('(net (code "%d") (name "/%s") %s)' % (i, n, ' '.join('(node (ref "%s") (pin "%s"))' % x for x in v))
                                          for i, (n, v) in enumerate(sorted(want.items())))
    ok, diff = K.parity(d, libs, net)
    bad = net.replace('(node (ref "R1") (pin "1"))', '')
    ok2, diff2 = K.parity(d, libs, bad)
    check('the netlist check: KiCad\'s nets equal to the rows pass; a pin KiCad does not see on its net is named', ok and not ok2 and 'R1.1' in diff2[0],
          (diff, diff2))
    from pcb.custom import pcb_engines as E
    r = E.resolve()
    if r['how'] == 'refused':
        print('  [SKIP] the KiCad render (sheet, check, netlist, drawing): no pcb engine here - %s' % r['why'][:90])
        return
    res = K.render(rec, tables)
    check('rendered by KiCad: its own netlist has the same nets as the rows; the only errors are the header pins left unconnected on purpose',
          res['parity'][0] and set(res['erc']['by_type']) <= {'error pin_not_connected', 'warning lib_symbol_issues'} and res['svg'], (res['parity'], res['erc']))


def main():
    from board.custom import electrical_check as EC
    tables = EC.tables_for(None)
    tables['_resolved'] = {}
    print('hwnocode solve selftest (cb-3): the schematic solver on %s' % SOL)
    fresh = record_and_uno(tables)
    features(fresh)
    live_rules(tables, fresh)
    second_chip(tables)
    seeded(fresh)
    kicad(tables)
    print('hwnocode solve selftest: %d/%d passed' % (passed, total))
    return 0 if passed == total else 1


if __name__ == '__main__':
    sys.exit(main())
