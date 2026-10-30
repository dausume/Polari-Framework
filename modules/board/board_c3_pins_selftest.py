"""board_c3_pins_selftest - c3pf (FIRMWARE_GENERATION_MODULE_PLAN.md section 11): the ESP32-C3's pin functions as CITED rows - Peripheral / PeripheralSignal / PinFunction
(routing matrix | fixed), the lifecycle rows (strapping, USB, UART0, JTAG, flash), the QFN32 package, and what the availability ladder, target_compat, the iso-0 eligibility and the
sol-0 attempt engine now say about the ESP32-C3 (the second board).

    PYTHONPATH=.:modules python3 -m board.board_c3_pins_selftest
"""
import json
import re

C3, SOC = 'esp32-c3', 'esp32c3'


def run_c3_pins(check):
    from board.custom import board_object as BO
    from board.custom import esp32c3_evidence as EV
    from board.custom import esp32c3_tables as T
    from board.custom import ladder as L
    from board.custom import target_compat as TC
    tables = BO.seed_tables()
    from board.custom import soc_functions as SF
    pf = SF.pin_functions(tables, SOC)   # c3-derive: the 72 stored fixed rows + the 2 640 derived matrix rows
    sig = [s for s in tables['PeripheralSignal'] if s['soc'] == SOC]
    per = [p for p in tables['Peripheral'] if p['soc'] == SOC]
    socpins = [s for s in tables['SocPin'] if s['soc'] == SOC]
    facts = {f['name']: f for f in tables['DatasheetFact']}
    by_pin = {}
    for f in pf:
        by_pin.setdefault(f['soc_pin'], []).append(f)

    # ---- the documents
    check('c3pf DOCS: the datasheet is the SAME file board_c3 cites (sha256 833fc000...f968); the TRM, the MINI-1 datasheet and the DevKitM-1 guide carry a 64-hex sha256, a revision and a url',
          '833fc000b4b3c3d39c496fcbd597fed5806956503ce7390b19cc8ae82f19f968' in EV.DS_REV
          and all(re.search(r'sha256 [0-9a-f]{64}', EV.DOCS[k][1]) and EV.DOCS[k][2].startswith('https://') for k in ('trm', 'mini', 'kit')), EV.DOCS['trm'][1])

    fixed_expected = {sp['pin']: {f for f in json.loads(sp['functions_json']) if f != sp['pin']} for sp in socpins}
    # ---- the signal table (TRM Table 5.11-1)
    named_in = [r for r in T.SIGNALS if r[1]]
    named_out = [r for r in T.SIGNALS if r[4]]
    check('c3pf SIGNALS: Table 5.11-1 read as the TRM counts it - 128 signal numbers, 42 valid input signals and 78 valid output signals (TRM §5.2 p.159)',
          len(T.SIGNALS) == 128 and len(named_in) == 42 and len(named_out) == 78, (len(T.SIGNALS), len(named_in), len(named_out)))
    check('c3pf SIGNALS: spot checks against the table - signal 6 = U0RXD_in / U0TXD_out, 45-50 = ledc_ls_sig_out0..5, 53/54 = I2CEXT0 SCL/SDA, 63 = FSPICLK',
          T.SIGNALS[6][1:5] == ('U0RXD_in', '0', 'yes', 'U0TXD_out') and [T.SIGNALS[i][4] for i in range(45, 51)] == ['ledc_ls_sig_out%d' % i for i in range(6)]
          and T.SIGNALS[53][1] == 'I2CEXT0_SCL_in' and T.SIGNALS[54][1] == 'I2CEXT0_SDA_in' and T.SIGNALS[63][1] == 'FSPICLK_in', T.SIGNALS[6])
    check('c3pf ROWS (rm-2b: + 4 register-only blocks SYSTIMER / SYSTEM / RTC_CNTL / INTMTX): %d Peripheral, %d PeripheralSignal (120 matrix + JTAG 4 + ADC/USB/XTAL 10 + per pad GPIO and GPIO_INT 44), %d PinFunction' % (len(per), len(sig), len(pf)),
          len(per) == 26 and len(sig) == 120 + 4 + 10 + 44 and len(pf) == 22 * (2 + 120) + sum(len(v) for v in fixed_expected.values()), (len(per), len(sig), len(pf)))

    # ---- every SocPin has GPIO + its cited functions, and every matrix signal
    matrix_names = {r[1] for r in named_in} | {r[4] for r in named_out}
    ok_all = True
    detail = []
    for sp in socpins:
        fs = by_pin.get(sp['name'], [])
        names = {f['function'] for f in fs}
        mx = {f['function'] for f in fs if f['routing'] == 'matrix'}
        fx = {f['function'] for f in fs if f['routing'] == 'fixed'} - {'GPIO', 'GPIO_INT'}
        good = 'GPIO' in names and 'GPIO_INT' in names and mx == matrix_names and fx == fixed_expected[sp['pin']]
        ok_all &= good
        if not good:
            detail.append((sp['pin'], sorted(fixed_expected[sp['pin']] ^ fx)[:5], len(mx)))
    check('c3pf PINS: every one of the 22 SocPins has GPIO, GPIO_INT, all 120 GPIO-matrix signals (routing matrix) and exactly the IO MUX / analog functions its SocPin fact cites (routing fixed)',
          ok_all and len(socpins) == 22, detail)
    adc = {sp['pin']: [f['function'] for f in by_pin[sp['name']] if f['function'].startswith('ADC')] for sp in socpins}
    check('c3pf PINS: ADC channels are on GPIO0-GPIO5 only (ADC1_CH0-4, ADC2_CH0 on GPIO5), USB_D-/USB_D+ on GPIO18/19, U0RXD/U0TXD on GPIO20/21, MTMS/MTDI/MTCK/MTDO on GPIO4-7',
          {p: v for p, v in adc.items() if v} == {'GPIO0': ['ADC1_CH0'], 'GPIO1': ['ADC1_CH1'], 'GPIO2': ['ADC1_CH2'], 'GPIO3': ['ADC1_CH3'], 'GPIO4': ['ADC1_CH4'], 'GPIO5': ['ADC2_CH0']}
          and 'USB_D-' in {f['function'] for f in by_pin['esp32c3:GPIO18']} and 'USB_D+' in {f['function'] for f in by_pin['esp32c3:GPIO19']}
          and {'U0RXD'} <= {f['function'] for f in by_pin['esp32c3:GPIO20']} and {'U0TXD'} <= {f['function'] for f in by_pin['esp32c3:GPIO21']}
          and all(any(f['function'] == j and f['routing'] == 'fixed' for f in by_pin['esp32c3:GPIO%d' % n]) for n, j in ((4, 'MTMS'), (5, 'MTDI'), (6, 'MTCK'), (7, 'MTDO'))), adc)
    pri = {int(sp['pin'][4:]): max(int(re.search(r'priority P(\d)', f['notes']).group(1)) for f in by_pin[sp['name']] if f['routing'] == 'matrix' and 'priority P' in f['notes']) for sp in socpins}
    check('c3pf PINS: Table 2-7 priorities are in the rows - GPIO0, 1, 3, 10 are P2 (free), GPIO2/4-9/11/18-21 are P3 (caution), GPIO12-17 are P4 (the flash pads)',
          [n for n, p in pri.items() if p == 2] == [0, 1, 3, 10] and all(pri[n] == 4 for n in range(12, 18)) and all(pri[n] == 3 for n in (2, 4, 5, 6, 7, 8, 9, 11, 18, 19, 20, 21)), pri)

    # ---- exclusive_group only where cited
    grouped = [f for f in pf if f['exclusive_group']]
    check('c3pf GROUPS: exclusive_group is set only where a source says so - F0, F2, GPIO and the matrix OUTPUT signals of one pad share ONE group (datasheet §2.3.1 p.19, TRM §5.5.2 p.164); inputs, GPIO_INT and analog functions have none',
          grouped and all(f['exclusive_group'] == '%s:%s:pad-output' % (SOC, f['soc_pin'].split(':')[1]) for f in grouped)
          and not any(f['exclusive_group'] for f in pf if f['routing'] == 'matrix' and not f['overrides_gpio'])
          and all(f['exclusive_group'] for f in pf if f['routing'] == 'matrix' and f['overrides_gpio'])
          and not any(f['exclusive_group'] for f in pf if f['function'] == 'GPIO_INT' or f['function'].startswith(('ADC', 'USB_', 'XTAL_'))), len(grouped))

    # ---- every fact cites document + page
    def cited(f):
        return all(f.get(k) for k in ('document', 'revision', 'url', 'page_table')) and re.search(r'p\.?\s?\d|pp\.\s?\d|Header Block|component list', f['page_table'])
    bad = [r['name'] for r in sig + pf + per if not r['fact'] or r['fact'] not in facts or not cited(facts[r['fact']])]
    check('c3pf CITES: every C3 Peripheral, PeripheralSignal and PinFunction row names a DatasheetFact that carries document, revision (with sha256), url and a page/table', not bad, bad[:5])
    check('c3pf CITES: every PinFunction says where it comes from (origin cites a table and page) and what the sources leave open (undetermined / notes)',
          all(f['origin'].startswith('cited:') and re.search(r'p\.\d|pp\.\d', f['origin']) for f in pf), [f['name'] for f in pf if not f['origin'].startswith('cited:')][:3])

    # ---- the package
    contacts = [c for c in tables['PackageContact'] if c['package'] == 'esp32c3-32-qfn']
    pins_on = {c['soc_pin'] for c in contacts if c['kind'] == 'io'}
    check('c3pf PACKAGE: the QFN32 has 33 contacts (32 legs + the centre GND pad), 22 I/O legs - one per SocPin, leg 18 (VDD_SPI) is GPIO11 - and the board has U1 (mcu) on it',
          len(contacts) == 33 and len(pins_on) == 22 and next(c for c in contacts if c['number'] == 18)['soc_pin'] == 'esp32c3:GPIO11'
          and next(c for c in contacts if c['number'] == 33)['kind'] == 'ground'
          and any(c['board'] == C3 and c['role'] == 'mcu' and c['package'] == 'esp32c3-32-qfn' for c in tables['BoardComponent']), len(contacts))
    enc = [e for e in tables['HardwareEnclosure'] if e['board'] == C3]
    check('c3pf PACKAGE: the C3 has its chip package enclosure (E1) and the E1 exposure map; c3-pv: + its board enclosure (E2) and E2 crossings, now that J1 / J3 are modelled',
          sorted(e['level'] for e in enc) == ['E1', 'E2'] and any(c['level'] == 'E2' and C3 in c['enclosure'] for c in tables['EnclosureContact'])
          and any(c['level'] == 'E1' and C3 in c['enclosure'] for c in tables['EnclosureContact']), [e['name'] for e in enc])

    # ---- lifecycle
    lc = [x for x in tables['PinLifecycleConstraint'] if x['board'] == C3]
    key = {(x['pin'], x['phase'], x['policy'], x['condition']) for x in lc}
    check('c3pf LIFECYCLE: the strapping pins GPIO2/8/9 carry a reset-phase row; the USB pads GPIO18/19 are conditional (reconfigure) and reserved when the USB link is the transport; GPIO20/21 are reserved under transport=usb-serial; GPIO4-7 are conditional while debugging over JTAG pins',
          all((g, 'reset', 'conditional', '') in key for g in ('GPIO2', 'GPIO8', 'GPIO9'))
          and all((g, 'runtime', 'conditional', '') in key and (g, 'runtime', 'reserved', 'transport=usb-serial-jtag') in key for g in ('GPIO18', 'GPIO19'))
          and all((g, ph, 'reserved', 'transport=usb-serial') in key for g in ('GPIO20', 'GPIO21') for ph in ('init', 'runtime'))
          and all((g, 'debug', 'conditional', 'debug=jtag-pins') in key for g in ('GPIO4', 'GPIO5', 'GPIO6', 'GPIO7')), len(lc))
    check('c3pf LIFECYCLE: the flash pads GPIO12-17 and the VDD_SPI pin GPIO11 are reserved at init and runtime; the rows cite the in-package flash (Table 2-12 p.29; MINI-1 p.4 note 4)',
          all((g, ph, 'reserved', '') in key for g in ['GPIO%d' % n for n in range(11, 18)] for ph in ('init', 'runtime'))
          and all('p.29' in x['page_table'] for x in lc if x['pin'] in ('GPIO13', 'GPIO15') and x['phase'] == 'init'), len(lc))
    check('c3pf LIFECYCLE: every row cites document + page/table + url, has a plain-words reason, and a partial / unverified row says what is undetermined',
          all(x['document'] and x['page_table'] and x['url'].startswith('http') and x['reason'] for x in lc) and all(x['undetermined'] for x in lc if x['verification'] != 'verified'), [x['name'] for x in lc if not x['page_table']][:3])

    # ---- the ladder: rungs 1 / 2 / 6 / 8 on a sample
    def rungs(pin, fn, **ctx):
        r = L.availability(pin, fn, dict({'board': C3, 'transport': 'usb-serial'}, **ctx), tables)['results'][0]
        return {x['rung']: x for x in r['rungs']}, r
    r1, res1 = rungs('GPIO3', 'ledc_ls_sig_out0')
    check('c3pf LADDER: PWM (ledc_ls_sig_out0) on GPIO3 - rung 1 ok (the PinFunction row), rung 2 ok (leg 8), rung 6 ok (through the GPIO matrix), rung 8 ok; c3-pv: rung 3 ok (J1 pin 5, the header map) and rung 4 ok (the schematic puts no part on GPIO3)',
          [r1[i]['verdict'] for i in (1, 2, 6, 8)] == ['ok'] * 4 and 'PinFunction esp32c3:GPIO3:ledc_ls_sig_out0' in r1[1]['detail'] and 'leg 8' in r1[2]['detail'] and 'GPIO matrix' in r1[6]['detail']
          and r1[3]['verdict'] == 'ok' and 'esp32-c3:J1:5' in r1[3]['detail'] and r1[4]['verdict'] == 'ok' and res1['blocked_at'] == 0, [r1[i]['verdict'] for i in sorted(r1)])
    r2, _ = rungs('GPIO8', 'ADC1_CH0')
    check('c3pf LADDER: an ADC channel on GPIO8 is refused at rung 1 by name (GPIO8 has no ADC function) - only GPIO0-5 do', r2[1]['verdict'] == 'blocked' and 'no function ADC1_CH0' in r2[1]['detail'], r2[1]['detail'])
    r3, res3 = rungs('GPIO12', 'GPIO', phase='runtime')
    check('c3pf LADDER: GPIO12 (the in-package flash pad) is a pad and a leg (rung 1, 2 ok) but is refused at rung 8 by the lifecycle row, with the datasheet page',
          r3[1]['verdict'] == 'ok' and r3[2]['verdict'] == 'ok' and r3[8]['verdict'] == 'blocked' and 'RESERVED' in r3[8]['detail'] and res3['blocked_at'] == 8, r3[8]['detail'][:120])
    r4, _ = rungs('GPIO9', 'GPIO_INT')
    check('c3pf LADDER: an interrupt on GPIO9 is possible (rung 1 ok: every pad can interrupt, TRM Register 5.14) but rung 6 is conditional (strapping pad, Table 2-7 P3) and rung 8 is conditional - the boot button must be acknowledged',
          r4[1]['verdict'] == 'ok' and r4[6]['verdict'] == 'conditional' and 'every pad can interrupt' in r4[6]['detail'] and r4[8]['verdict'] == 'conditional' and 'boot-button' in r4[8]['detail'], r4[6]['detail'][:100])
    r5, _ = rungs('GPIO21', 'U0TXD', purpose=True)
    r6, _ = rungs('GPIO21', 'GPIO', purpose=False)
    check('c3pf LADDER: UART0 TX on GPIO21 as the transport is native (rung 8 ok); the same pad claimed as plain GPIO is refused (reserved while the USB-UART bridge is the transport)',
          r5[8]['verdict'] == 'ok' and r6[8]['verdict'] == 'blocked' and 'RESERVED' in r6[8]['detail'], (r5[8]['detail'][:80], r6[8]['detail'][:80]))
    r7, _ = rungs('GPIO2', 'GPIO')
    check('c3pf LADDER: a plain GPIO on the strapping pad GPIO2 is conditional at rung 6 (datasheet §2.3.3: extra caution when used as GPIO; Table 2-7 priority P3) while GPIO10 (P2) is plain ok',
          r7[6]['verdict'] == 'conditional' and 'P3' in r7[6]['detail'] and rungs('GPIO10', 'GPIO')[0][6]['verdict'] == 'ok', r7[6]['detail'][:120])

    # ---- target_compat on the C3
    r = BO.rows_for(C3, tables)
    soc_by = {s['pin']: s for s in r['soc_pins']}

    def tc(kind, pin):
        p = next(x for x in r['pins'] if x['canonical'] == pin)
        return TC.compatible(kind, p, soc_by[p['soc_pin']], tables)
    vt = lambda kind: sorted(v['pin'] for v in TC.valid_targets(kind, r) if v['verdict'] == 'ok')   # noqa: E731
    check('c3pf COMPAT: analog-in is valid on exactly the board pins with an ADC channel (GPIO0-5); pwm-out, uart, I2C, SPI and interrupt-in are valid on every board pin through the matrix; uart-tx on GPIO21 is the IO MUX pad',
          vt('analog-in') == ['GPIO0', 'GPIO1', 'GPIO2', 'GPIO3', 'GPIO4', 'GPIO5'] and len(vt('pwm-out')) == len(r['pins']) == len(vt('interrupt-in')) == len(vt('uart-tx')) == len(vt('i2c-sda'))
          and tc('uart-tx', 'GPIO21')[0] == 'ok' and 'IO MUX' in tc('uart-tx', 'GPIO21')[1] and tc('analog-in', 'GPIO8')[0] == 'no', (vt('analog-in'), len(r['pins'])))

    # ---- iso-0 eligibility on the C3
    from cmod.custom import isotope_variants as IV
    from cmod.custom import isotope_variants_eligibility as E
    ctx = E.context(C3, tables)
    el = {v['name']: E.eligible(v, ctx, tier='freertos') for v in IV.variants(None)}
    check('c3pf ELIGIBILITY: on FreeRTOS the INT / PCINT / PWM / UART / GPIO / ADC / TMP36 routes that were undetermined are now OK from the rows; the analog-comparator route is BLOCKED by name with the datasheet\'s peripheral list as the basis',
          all(el[n]['state'] == 'ok' for n in ('read-button:gpio-poll', 'read-button:ext-interrupt', 'read-button:pin-change-interrupt', 'read-button:analog-threshold', 'drive-led:gpio-out', 'drive-led:pwm',
                                               'sense-led-line:ext-interrupt', 'sense-led-line:pin-change-interrupt', 'sense-led-line:gpio-poll', 'sense-led-line:analog-read', 'report-state:uart-tx',
                                               'receive-command:uart-rx-interrupt', 'read-temperature:analog-sensor'))
          and el['read-button:analog-comparator']['state'] == 'blocked' and 'no analog comparator is among them' in el['read-button:analog-comparator']['summary'] and 'p.4' in el['read-button:analog-comparator']['summary'],
          {n: e['state'] for n, e in el.items() if e['state'] != 'ok'})
    bare = E.eligible(next(v for v in IV.variants(None) if v['name'] == 'drive-led:gpio-out'), ctx, tier='bare-c')
    check('c3pf ELIGIBILITY: the bare-c tier stays blocked on the C3 BY NAME (no bare-C template; FreeRTOS is the lowest tier); the routes that need a part the bench lacks stay blocked by that part, not by the pins',
          bare['state'] == 'blocked' and 'no bare-C template' in bare['summary'] and el['drive-led:i2c-expander']['blocked_by'] == ['part:PCF8574-class I2C I/O expander']
          and el['read-button:spi-shift-register']['blocked_by'] == ['part:74HC165-class parallel-in shift register'], el['drive-led:i2c-expander']['blocked_by'])
    uno = E.context('arduino-uno-r3', tables)
    check('c3pf ELIGIBILITY: the UNO is unchanged - INT0, comparator and PWM routes ok on bare-c; FreeRTOS refused for 2 KB SRAM',
          all(E.eligible(v, uno, tier='bare-c')['state'] == 'ok' for v in IV.variants(None) if v['name'] in ('read-button:ext-interrupt', 'read-button:analog-comparator', 'drive-led:pwm'))
          and 'S-class' in E.eligible(next(v for v in IV.variants(None) if v['name'] == 'drive-led:pwm'), uno, tier='freertos')['summary'], '')

    # ---- sol-0 on the C3 for the light Mission
    from cmod.custom import solve as S
    res = S.solve('uno-light-mission', boards=[C3])
    w = res['chosen_candidate']
    pins = {a['role']: (a['pin'], a['function']) for a in w['assignment'] if a['part'] == a['role'] or a['role'] != 'the transport'}
    trans = {a['part']: (a['pin'], a['function']) for a in w['assignment'] if a['role'] == 'the transport'}
    check('c3pf SOL-0: the ESP32-C3 light Mission is now PLACED (rank class 0, not undetermined) on the FreeRTOS tier - the lowest the C3 offers - with the five Purposes\' pins; bare-c is pruned by name',
          res['hardware'][0]['placeable'] is True and w['rank_class'] == 0 and w['placement'] == 'placed' and w['tier'] == 'freertos' and not w['lost'] and len(w['assignment']) == 5
          and any('bare-c' in x['where'] and 'no bare-C template' in x['reason'] for x in res['pruned']['by_kind']['tier-blocked']['first']), (w['tier'], w['placement']))
    check('c3pf SOL-0: the transport sits on the UART0 pads GPIO20 (U0RXD) / GPIO21 (U0TXD) - every GPIO-matrix option for the reserved line is refused by name (the fixed wire to the USB-UART bridge)',
          set(trans.values()) == {('GPIO20', 'U0RXD'), ('GPIO21', 'U0TXD')} and any(x['kind'] == 'pin-refused' and 'transport-wire' in x['reason'] for x in res['pruned']['by_kind']['pin-refused']['first']),
          trans)
    free = {'GPIO0', 'GPIO1', 'GPIO3', 'GPIO10'}
    check('c3pf SOL-0: the LED and the button take the least specialised pads (P2 pads: no strapping, JTAG, USB or UART0 function); the sense line, third, takes the cheapest left and carries its cautions as listed risks (c3-pv: on GPIO8 the board\'s RGB LED + pull-up share the line - rung 4 conditional, named)',
          pins['the LED'][0] in free and pins['the button'][0] in free and any('rung' in x['text'] for x in w['risks'])
          and (pins['the sense line'][0] != 'GPIO8' or any('rung 4 (connected-components) conditional' in x['text'] and 'GPIO8' in x['text'] for x in w['risks'])), pins)
    check('c3pf SOL-0: what is still open is stated, not hidden - rungs 7 and 9 (no circuit / binding) and 10, undetermined costs scored at stand-ins, and the comparator route '
          'pruned as ineligible; c3-pv: rung 3 is no longer open (J1 / J3 are modelled)',
          {7, 9, 10} <= {x.get('rung') for x in w['risks'] if x['kind'] == 'ladder'} and 3 not in {x.get('rung') for x in w['risks'] if x['kind'] == 'ladder'} and res['pruned']['by_kind']['variant-ineligible']['count'] >= 2
          and any('analog-comparator' in x['where'] for x in res['pruned']['by_kind']['variant-ineligible']['first']), [x['text'][:60] for x in w['risks']][:5])
    return res


if __name__ == '__main__':
    import sys
    _passed = _total = 0

    def _check(name, cond, detail=None):
        global _passed, _total
        _total += 1
        ok = bool(cond)
        _passed += ok
        print('  [%s] %s' % ('PASS' if ok else 'FAIL', name))
        if not ok and detail is not None:
            print('         detail:', str(detail)[:600])
    run_c3_pins(_check)
    print('\n%d/%d checks passed' % (_passed, _total))
    sys.exit(0 if _passed == _total else 1)
