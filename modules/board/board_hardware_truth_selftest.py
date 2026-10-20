"""board_hardware_truth_selftest — fgm-2 (FIRMWARE_GENERATION_MODULE_PLAN.md §7.7 slice 1'): THE UNO HARDWARE TRUTH as rows + the electrical rules (f)-(j).

Model: PackageDefinition/PackageContact (28-SPDIP + 32-TQFP, ADC6/ADC7 only on the TQFP), UsbInterfaceDefinition (independent axis; the bench pair stays PENDING),
BoardComponent (U1 mcu, U2 usb-bridge with its own SoC row), ElectricalCharacteristic per pad class, PinGroupBudget per group, PinLifecycleConstraint, the box counts on
KitPart; every number cited (document + page/table) or `undetermined` naming what is missing.
Rules: deliberately invalid designs are REFUSED BY NAME (an LED on D6 with no resistor; a GPIO claim on D0 while the transport is USB-serial; SPI on D13 without
acknowledging the L LED buffer; a design whose current relies on the absolute maximum) and the light test circuit passes (undetermined only where a number is
genuinely uncited — the LED forward voltage, the pushbutton's closed resistance, the recommended VCC/GND total). The chain door shows the package-contact and lifecycle hops.

    PYTHONPATH=.:modules python3 -m board.board_hardware_truth_selftest
"""
import json

LIGHT = {'loads': [{'pin': 'D6', 'kind': 'led', 'led_variant': 'red', 'series_ohms': 220, 'v_forward': None}],
         'links': [{'output': 'D6', 'input': 'D3'}], 'buttons': [{'pin': 'D2', 'pull': 'up'}],
         'claims': [{'pin': 'D6', 'mode': 'output'}, {'pin': 'D3', 'mode': 'input', 'function': 'INT1'}, {'pin': 'D2', 'mode': 'input', 'function': 'INT0'}]}


def _by(findings, rule):
    return [f for f in findings if f['rule'] == rule]


def _status(findings, rule):
    return sorted({f['status'] for f in _by(findings, rule)})


def run_hardware_truth(check):
    _model(check)
    _numbers(check)
    _kit(check)
    _rules(check)
    _chain_door(check)


def _model(check):
    from board.board_basis import BOARD_CLASSES, BoardInstance
    from board.board_seed import BOARD_SEED_PAIRS
    from board.custom import board_object as BO
    t = BO.seed_tables()
    names = ('PackageDefinition', 'PackageContact', 'UsbInterfaceDefinition', 'BoardComponent', 'ElectricalCharacteristic', 'PinGroupBudget', 'PinLifecycleConstraint')
    check('fgm-2: the seven new classes are BOARD_CLASSES members', {c.__name__ for c in BOARD_CLASSES} >= set(names) and len(BOARD_CLASSES) == 60, len(BOARD_CLASSES))   # hsp-0: 48 + EnclosureKind, HardwareEnclosure, EnclosureContact; hsp-1: + HardwareSystem, SystemLink, SignalPath
    seeded = {c: (cls, rows) for c, cls, rows in BOARD_SEED_PAIRS}
    check('fgm-2: every new class is a seed pair, code-owned (rows converge)', all(c in seeded and seeded[c][1] and all('_converge' in r for r in seeded[c][1]) for c in names))
    try:
        import contextlib
        import io
        with contextlib.redirect_stdout(io.StringIO()):   # the framework prints a manager notice per row built without a server
            built = [cls(**{k: v for k, v in r.items() if k != '_converge'}) for c in names for cls, rows in [seeded[c]] for r in rows]
        check('fgm-2: every seed row constructs its class (no stray field) — %d rows' % len(built), len(built) == sum(len(seeded[c][1]) for c in names))
    except TypeError as e:
        check('fgm-2: every seed row constructs its class (no stray field)', False, str(e))
    check('fgm-2: row counts — 4 packages (hsp-0: + the 16U2 QFN; c3pf: + the ESP32-C3 QFN32), 126 contacts (28 + 32 + 33 + 33), 2 USB interfaces, 3 components (U1, U2 of the UNO; c3pf: U1 of the C3), 7 group budgets',
          [len(t[c]) for c in ('PackageDefinition', 'PackageContact', 'UsbInterfaceDefinition', 'BoardComponent', 'PinGroupBudget')] == [4, 126, 2, 3, 7], {c: len(t[c]) for c in names})

    # ---- packages
    pc = {c['name']: c for c in t['PackageContact']}
    spdip = [c for c in t['PackageContact'] if c['package'] == 'atmega328p-28-spdip']
    tqfp = [c for c in t['PackageContact'] if c['package'] == 'atmega328p-32-tqfp']
    sp = {s['name']: s for s in t['SocPin'] if s['soc'] == 'atmega328p'}
    check('packages: 28 SPDIP contacts + 32 TQFP contacts, numbers 1..N each once', sorted(c['number'] for c in spdip) == list(range(1, 29)) and sorted(c['number'] for c in tqfp) == list(range(1, 33)))
    check('packages: every SPDIP I/O contact number IS the SocPin.package_pin (SocPin keeps working)', all(sp[c['soc_pin']]['package_pin'] == str(c['number']) for c in spdip if c['soc_pin']))
    check('packages: ADC6 (leg 19) and ADC7 (leg 22) exist ONLY on the TQFP; the SPDIP has neither',
          {c['label']: c['number'] for c in tqfp if c['label'] in ('ADC6', 'ADC7')} == {'ADC6': 19, 'ADC7': 22} and not [c for c in spdip if c['label'] in ('ADC6', 'ADC7')])
    check('packages: the same 23 I/O pins appear on both packages (each SocPin lists both contacts), power legs are contacts too (VCC/GND/AVCC/AREF)',
          len([c for c in spdip if c['soc_pin']]) == 23 == len([c for c in tqfp if c['soc_pin']])
          and all(len(json.loads(s['package_contacts_refs_json'])) == 2 for s in sp.values())
          and {c['label'] for c in spdip} >= {'VCC', 'GND', 'AVCC', 'AREF'} and sum(1 for c in tqfp if c['label'] == 'GND') == 3 and sum(1 for c in tqfp if c['label'] == 'VCC') == 2)
    pdef = {p['name']: p for p in t['PackageDefinition']}
    check('packages: adc_channels 6 (SPDIP) vs 8 (TQFP); contacts_refs resolve; every contact cites a figure page',
          pdef['atmega328p-28-spdip']['adc_channels'] == 6 and pdef['atmega328p-32-tqfp']['adc_channels'] == 8
          and all(r.partition(':')[2] in pc for p in pdef.values() for r in json.loads(p['contacts_refs_json'])) and all('p.12' in c['page_table'] for c in pc.values() if c['package'].startswith('atmega328p')))   # hsp-0: the QFN's contacts cite p.2
    check('packages: SocPin rows carry electrical_class (PC6 -> reset, the rest io-standard) and PB6 names the XTAL1 alternate class',
          sp['atmega328p:PC6']['electrical_class'] == 'atmega328p:reset' and sp['atmega328p:PD6']['electrical_class'] == 'atmega328p:io-standard'
          and json.loads(sp['atmega328p:PB6']['electrical_alt_classes_json']) == {'XTAL1': 'atmega328p:xtal1'})
    r = BO.rows_for('arduino-uno-r3', t)
    h0 = BO.board_sha(r)
    r2 = json.loads(json.dumps(r))
    for s in r2['soc_pins']:
        for k in ('electrical_class', 'electrical_alt_classes_json', 'package_contacts_refs_json'):
            s.pop(k, None)
    check('packages: the board sha is independent of the new derived SocPin columns (every existing view stays byte-identical)', BO.board_sha(r2) == h0)

    # ---- USB interfaces + the pending pair
    ui = {u['name']: u for u in t['UsbInterfaceDefinition']}
    ids16 = [i['id'] for i in json.loads(ui['atmega16u2-bridge']['usb_ids_json'])]
    check('usb: the ATmega16U2 bridge carries 2341:0043 / 2341:0001 / 2a03:0043; the CH340 carries 1a86:7523', ids16 == ['2341:0043', '2341:0001', '2a03:0043']
          and [i['id'] for i in json.loads(ui['ch340-bridge']['usb_ids_json'])] == ['1a86:7523'])
    check('usb: dtr_resets_mcu is TRUE for the 16U2 (schematic path cited) and UNDETERMINED for the CH340 (no clone schematic read)',
          ui['atmega16u2-bridge']['dtr_resets_mcu'] == 'true' and 'C5 100 nF' in ui['atmega16u2-bridge']['dtr_path'] and ui['atmega16u2-bridge']['verification'] == 'verified'
          and ui['ch340-bridge']['dtr_resets_mcu'] == 'undetermined' and ui['ch340-bridge']['verification'] == 'unverified' and ui['ch340-bridge']['undetermined'])
    bd = next(b for b in t['BoardDefinition'] if b['name'] == 'arduino-uno-r3')
    check('variants: the board DESIGN allows both packages and both USB interfaces (independent axes) and says PENDING',
          json.loads(bd['allowed_packages_json']) == ['atmega328p-28-spdip', 'atmega328p-32-tqfp'] and json.loads(bd['allowed_usb_interfaces_json']) == ['atmega16u2-bridge', 'ch340-bridge']
          and bd['variant_status'] == 'pending')
    import contextlib
    import io
    with contextlib.redirect_stdout(io.StringIO()):
        inst = BoardInstance(name='probe')
    check('variants: a BoardInstance asserts NEITHER (package_variant/usb_interface empty, variant_status pending) and no instance is seeded',
          inst.package_variant == '' and inst.usb_interface == '' and inst.variant_status == 'pending' and seeded['BoardInstance'][1] == [])

    # ---- components
    comp = {c['ref']: c for c in t['BoardComponent'] if c['board'] == 'arduino-uno-r3'}   # c3pf: the C3 has its own U1
    socs = {s['name']: s for s in t['SocDefinition']}
    check('components: U1 = ATmega328P (mcu, targeted by firmware, package modelled 28-SPDIP with TQFP allowed); U2 = ATmega16U2 (usb-bridge, programmable, its own SoC row)',
          comp['U1']['role'] == 'mcu' and comp['U1']['soc'] == 'atmega328p' and comp['U1']['targeted_by_firmware'] and comp['U1']['package'] in json.loads(comp['U1']['package_options_json'])
          and comp['U2']['role'] == 'usb-bridge' and comp['U2']['soc'] == 'atmega16u2' and comp['U2']['programmable'] and not comp['U2']['targeted_by_firmware']
          and comp['U2']['usb_interface'] == 'atmega16u2-bridge' and comp['U2']['soc'] in socs and ui['atmega16u2-bridge']['programmable_soc'] == 'atmega16u2')
    comps_json = {c['ref']: c for c in json.loads(next(h for h in t['BoardHardware'] if h['board'] == 'arduino-uno-r3')['components_json'])}
    check('components: derived from BoardHardware.components_json (same value strings) — the JSON itself is unchanged', comps_json['U1']['value'] == comp['U1']['value'] and comps_json['U2']['value'] == comp['U2']['value'])
    check('components: U2 SocDefinition cites its own datasheet (16 KB flash / 512 B SRAM) and says its registers / PinFunctions are not modelled (hsp-0: its pins are SocPins)', json.loads(socs['atmega16u2']['memory_map_json'])[0]['size'] == 16384
          and 'PinFunctions are not modelled' in socs['atmega16u2']['undetermined'])


def _numbers(check):
    from board.custom import board_object as BO
    from board.custom import electrical_hw as HW
    t = BO.seed_tables()
    ds = {d['name'] for d in t['Datasheet']}
    EC, GB, LC = t['ElectricalCharacteristic'], t['PinGroupBudget'], t['PinLifecycleConstraint']
    LIMITS, VERIF = ('abs-max', 'recommended', 'guaranteed', 'typical'), ('verified', 'partial', 'unverified', 'conflicted')
    check('numbers: every ElectricalCharacteristic names a limit_class and verification from the enums', all(r['limit_class'] in LIMITS and r['verification'] in VERIF for r in EC))
    check('numbers: every number row cites a document, a page/table and a Datasheet row that exists (or is `undetermined` saying what is missing)',
          all((r['document'] and r['page_table'] and r['datasheet'] in ds) or r['undetermined'] for r in EC + GB + LC), [r['name'] for r in EC + GB + LC if not ((r['document'] and r['page_table'] and r['datasheet'] in ds) or r['undetermined'])])
    check('numbers: an undetermined row carries no number (never a guess)', all(not (r['min_value'] or r['typ_value'] or r['max_value']) for r in EC if r['undetermined']))
    check('numbers: the new documents are Datasheet rows with a sha256 (schematic, product datasheet, ATmega16U2 datasheet)',
          all(any(d['name'] == n and len(d['sha256']) == 64 for d in t['Datasheet']) for n in ('arduino-uno-r3-schematic', 'arduino-uno-r3-product-datasheet', 'atmega16u2-doc7799')))

    def one(param, slug=None, pad='atmega328p:io-standard', lc=None, vcc=5.0):   # vcc=None: ignore the supply filter (IIH/IIL are stated at 5.5 V only)
        return HW.characteristic(t, pad, param, vcc, limit_class=lc, slug=slug)
    check('numbers: VOH min 4.2 V at IOH = -20 mA, VCC 5 V, TA 85 C (Table 30-1 p.323); VOL max 0.9 V at IOL = 20 mA (p.322)',
          one('VOH', '5v-20ma-85c')['min_value'] == '4.2' and 'p.323' in one('VOH', '5v-20ma-85c')['page_table'] and one('VOL', '5v-20ma-85c')['max_value'] == '0.9' and 'p.322' in one('VOL', '5v-20ma-85c')['page_table'])
    check('numbers: VIL max = 0.3 VCC = 1.5 V and VIH min = 0.6 VCC = 3.0 V at 5 V; RPU 20..50 kohm; IIH/IIL <= 1 uA',
          HW.value_of(one('VIL')['max_value']) == 1.5 and abs(HW.value_of(one('VIH')['min_value']) - 3.0) < 1e-9 and (one('RPU')['min_value'], one('RPU')['max_value']) == ('20', '50') and one('IIH', vcc=None)['max_value'] == '1')
    ab = one('I_PIN', lc='abs-max')
    check('numbers: per-pin current — abs-max 40 mA (p.308, class abs-max, verified); guaranteed test current 20 mA; recommended 20 mA is PARTIAL (board vendor figure, no chip sentence)',
          ab['max_value'] == '40.0' and ab['limit_class'] == 'abs-max' and ab['verification'] == 'verified' and 'p.308' in ab['page_table']
          and one('I_PIN', lc='guaranteed')['max_value'] == '20' and one('I_PIN', lc='recommended')['verification'] == 'partial')
    check('numbers: abs-max rows are never classed recommended/guaranteed (current 40 mA, pin voltage VCC+0.5, RESET 13 V, VCC/GND 200 mA)',
          all(r['limit_class'] == 'abs-max' for r in EC if r['name'].endswith(':abs-max')) and all(b['limit_class'] == 'abs-max' for b in GB if b['name'].endswith('abs-max')) and any(r['parameter'] == 'V_PIN' and r['max_value'] == '13.0' for r in EC))
    check('numbers: pad classes — reset (VIH 0.9 VCC), xtal1 (VIL 0.1 VCC), adc-only (ADC6/7: VIN GND..VREF, RAIN 100 Mohm typ)',
          HW.value_of(one('VIH', pad='atmega328p:reset')['min_value'], 5.0) == 4.5 and one('VIL', pad='atmega328p:xtal1')['formula'] == '0.1 VCC' and one('R_AIN', pad='atmega328p:adc-only')['typ_value'] == '100')
    check('numbers: the figures the datasheet does NOT give are rows naming what is missing (a recommended continuous chip per-pin current; ADC6/7 leakage; a recommended VCC/GND total)',
          sum(1 for r in EC if r['undetermined']) == 2 and any(b['undetermined'] for b in GB))
    byn = {b['name']: b for b in GB}
    check('budgets: sourcing groups 150 mA x2, sinking groups 100 mA x3 (Table 30-1 notes 3/4, p.323); ADC6/ADC7 named as package-only members; abs-max supply total 200 mA',
          [byn['atmega328p:%s' % n]['limit_ma'] for n in ('ioh-pc-pd-reset', 'ioh-pb-pd-xtal', 'iol-pc-adc', 'iol-pb-pd-xtal', 'iol-pd-reset')] == [150, 150, 100, 100, 100]
          and json.loads(byn['atmega328p:iol-pc-adc']['package_only_json']) == ['ADC6', 'ADC7'] and byn['atmega328p:vcc-gnd-abs-max']['limit_ma'] == 200.0 and all('p.323' in byn[n]['page_table'] for n in byn if n.split(':')[1].startswith('io')))
    socpins = {s['name'] for s in t['SocPin']}
    members = [m for b in GB for m in json.loads(b['members_json']) if m.startswith('atmega328p:')]
    check('budgets: membership = pins (every member is a SocPin); the sourcing and sinking groups each cover all 23 I/O pins exactly once',
          set(members) <= socpins and all(len({m for b in GB if b['direction'] == d for m in json.loads(b['members_json'])}) == 23 for d in ('source', 'sink'))
          and sorted(m for b in GB if b['direction'] == 'source' for m in json.loads(b['members_json'])) == sorted(s for s in socpins if s.startswith('atmega328p:P')))
    pins = {(r['pin'], r['phase']): r for r in LC}
    check('lifecycle: RESET <- DTR (reset/bootloader), D0/D1 reserved for the USB-serial transport (+ bootloader), D13 conditional on the L LED, ICSP D11-D13, AREF, PB6/PB7 crystal',
          pins[('RESET', 'bootloader')]['condition'] == 'dtr=resets-mcu' and pins[('D0', 'runtime')]['policy'] == 'reserved' and pins[('D1', 'runtime')]['condition'] == 'transport=usb-serial'
          and pins[('D0', 'bootloader')]['policy'] == 'reserved' and pins[('D13', 'runtime')]['acknowledgment'] == 'l-led' and pins[('D13', 'programming')]['condition'] == 'icsp=connected'
          and pins[('D11', 'programming')]['policy'] == 'reserved' and pins[('AREF', 'runtime')]['policy'] == 'conditional' and pins[('PB6', 'runtime')]['policy'] == 'prohibited' and pins[('PB7', 'init')]['policy'] == 'prohibited')
    check('lifecycle: phases and policies are from the enums; no row carries an override policy (overrides are DerivedOverride rows)',
          all(r['phase'] in ('power-up', 'reset', 'bootloader', 'init', 'runtime', 'programming', 'debug') and r['policy'] in ('prohibited', 'conditional', 'reserved', 'preserve', 'free') for r in LC)
          and 'override' not in ' '.join(json.dumps(sorted(LC[0])).split()))
    check('lifecycle: the D13 row says the L LED is driven by a BUFFER (the load on the pin is its input) — the schematic correction, with the buffer input current UNDETERMINED',
          'buffer' in pins[('D13', 'runtime')]['reason'] and 'LMV358' in pins[('D13', 'runtime')]['undetermined'])


def _kit(check):
    from board.custom import kit_parts as KP
    rows = {r['name'].split(':', 1)[1]: r for r in KP.rows()}
    check('kit: 25 rows (23 + mosfet + assembly-base) and NO kit_quantity is undetermined any more', len(rows) == 25 and all(r['kit_quantity'].isdigit() for r in rows.values()))
    q = {k: int(r['kit_quantity']) for k, r in rows.items()}
    check('kit: counts from the box — pushbutton 10, light sensors 6, transistors 5, MOSFETs 2, diodes 7, optocouplers 2, potentiometers 3, gels 3, assembly base 1',
          (q['pushbutton'], q['phototransistor'], q['transistor'], q['mosfet'], q['diode'], q['optocoupler'], q['potentiometer'], q['gels'], q['assembly-base']) == (10, 6, 5, 2, 7, 2, 3, 3, 1))
    var = {k: {v['variant']: v['quantity'] for v in json.loads(r['variants_json'])} for k, r in rows.items() if json.loads(r['variants_json'])}
    check('kit: LED variants red 8 / green 8 / yellow 8 / blue 3 / bright white 1 / rgb 1 (total 29); every colour Vf undetermined',
          var['led'] == {'red': 8, 'green': 8, 'yellow': 8, 'blue': 3, 'bright white': 1, 'rgb': 1} and q['led'] == 29
          and all('undetermined' in v['v_forward'] for v in json.loads(rows['led']['variants_json'])))
    check('kit: resistors 220 ohm x22, 560 x7, 1k x7, 4.7k x7, 10k x22, 1M x7, 10M x7 (79); capacitors 100 uF x3, 100 nF x5, 100 pF x5 (13); jumpers solid 70 + stranded 2 (72); potentiometer 10 kohm',
          var['resistors'] == {'220 ohm': 22, '560 ohm': 7, '1 kohm': 7, '4.7 kohm': 7, '10 kohm': 22, '1 Mohm': 7, '10 Mohm': 7} and q['resistors'] == 79
          and var['capacitors'] == {'100 uF': 3, '100 nF': 5, '100 pF': 5} and q['capacitors'] == 13 and var['jumper-wires'] == {'solid core': 70, 'stranded': 2} and q['jumper-wires'] == 72
          and var['potentiometer'] == {'10 kohm': 3})
    check('kit: every row cites the box ("Arduino Starter Kit box (A000066_K7), THIS KIT INCLUDES panel"); a variants field (not extra rows) keeps the per-part reverse links',
          all('A000066_K7' in r['source'] and 'THIS KIT INCLUDES' in r['source'] for r in rows.values()) and 'arduino-starter-kit:led' in {r['name'] for r in KP.rows()}
          and 'led' in [r['name'].split(':')[1] for r in KP.rows() if 'blink-on-command' in r['sample_capabilities']] and len(KP.parts_without_sample()) == len(rows) - 2)
    check('kit: totals equal the variant sums', all(q[k] == sum(v.values()) for k, v in var.items() if k not in ('potentiometer',)) and q['potentiometer'] == 3)


def _rules(check):
    from board.custom import board_object as BO
    from board.custom import electrical_hw as HW
    t = BO.seed_tables()

    def run(**d):
        base = {'loads': [], 'links': [], 'buttons': [], 'claims': [], 'context': {}}
        base.update(d)
        return HW.check_design('arduino-uno-r3', base, t, overrides=d.get('overrides'))

    # ---- (f) LED on D6 with no resistor
    f = run(loads=[{'pin': 'D6', 'kind': 'led', 'series_ohms': 0}])
    hit = [x for x in f if x['rule'] == 'voh_under_load']
    check('REFUSED by name: an LED on D6 with NO series resistor -> voh_under_load refuse', hit and hit[0]['status'] == 'refuse' and 'NO series resistor' in hit[0]['detail'] and hit[0]['subject'] == 'D6 led', hit)
    print('      REFUSAL (verbatim): [%s] %s: %s' % (hit[0]['rule'], hit[0]['subject'], hit[0]['detail']))
    # ---- (j) GPIO claim on D0 while USB-serial
    f = run(claims=[{'pin': 'D0', 'mode': 'output'}], context={'transport': 'usb-serial'})
    hit = [x for x in f if x['rule'] == 'lifecycle' and x['status'] == 'refuse']
    check('REFUSED by name: a GPIO claim on D0 while the transport is USB-serial -> lifecycle refuse (RESERVED)', hit and 'D0' in hit[0]['subject'] and 'RESERVED while transport=usb-serial' in hit[0]['detail'], hit)
    print('      REFUSAL (verbatim): [%s] %s: %s' % (hit[0]['rule'], hit[0]['subject'], hit[0]['detail']))
    check('  … the same claim is fine when the transport is NOT USB-serial, and a USART0 claim on D0 (the transport itself) is fine',
          _status(run(claims=[{'pin': 'D0', 'mode': 'output'}], context={'transport': 'none'}), 'lifecycle') == ['ok']
          and _status(run(claims=[{'pin': 'D0', 'mode': 'alt', 'function': 'atmega328p:PD0:RXD'}], context={'transport': 'usb-serial'}), 'lifecycle') == ['ok'])
    # ---- (j) SPI on D13 without the L LED acknowledgment
    spi = {'pin': 'D13', 'mode': 'alt', 'function': 'atmega328p:PB5:SCK'}
    f = run(claims=[spi], context={})
    hit = [x for x in f if x['rule'] == 'lifecycle' and x['status'] == 'refuse']
    check('REFUSED by name: SPI on D13 without acknowledging the L LED -> lifecycle refuse (needs acknowledgment l-led)', hit and "needs the design to acknowledge 'l-led'" in hit[0]['detail'] and 'D13' in hit[0]['subject'], hit)
    print('      REFUSAL (verbatim): [%s] %s: %s' % (hit[0]['rule'], hit[0]['subject'], hit[0]['detail'][:230]))
    check('  … acknowledged -> ok; a lifecycle DerivedOverride (who/why) -> warn, never silent',
          _status(run(claims=[spi], context={'acknowledged': ['l-led']}), 'lifecycle') == ['ok']
          and _status(run(claims=[spi], overrides=[{'target_class': 'PinLifecycleConstraint', 'target_name': 'arduino-uno-r3:D13:runtime', 'who': 'a person', 'why': 'SPI display, blink accepted'},
                                                  {'target_class': 'PinLifecycleConstraint', 'target_name': 'arduino-uno-r3:D13:init', 'who': 'a person', 'why': 'same'}]), 'lifecycle') == ['warn'])
    # ---- (i) abs-max relied on
    f = run(loads=[{'pin': 'D5', 'kind': 'motor', 'current_ma': 35}])
    hit = _by(f, 'abs_max_not_target')
    check('REFUSED by name: a design whose current (35 mA) relies on abs-max headroom -> abs_max_not_target refuse', hit and hit[0]['status'] == 'refuse' and 'abs-max headroom' in hit[0]['detail'] and 'not a design target' in hit[0]['detail'], hit)
    print('      REFUSAL (verbatim): [%s] %s: %s' % (hit[0]['rule'], hit[0]['subject'], hit[0]['detail']))
    check('  … a design naming abs-max as its limit basis is refused too; 15 mA is fine; the electrical refusal ignores overrides',
          _status(run(loads=[{'pin': 'D5', 'kind': 'motor', 'current_ma': 15, 'limit_basis': 'abs-max'}]), 'abs_max_not_target') == ['refuse']
          and _status(run(loads=[{'pin': 'D5', 'kind': 'motor', 'current_ma': 15}]), 'abs_max_not_target') == ['ok']
          and _status(run(loads=[{'pin': 'D6', 'kind': 'led', 'series_ohms': 0}], overrides=[{'target_class': 'PinLifecycleConstraint', 'target_name': 'x', 'who': 'p', 'why': 'w'}]), 'voh_under_load') == ['refuse'])
    # ---- (g) group budget
    f = run(loads=[{'pin': p, 'kind': 'motor', 'current_ma': 17} for p in ('D5', 'D6', 'D7', 'D8', 'D9', 'D10', 'D11', 'D12', 'D13')])
    hit = [x for x in _by(f, 'power_budget') if x['status'] == 'refuse']
    check('REFUSED by name: nine pins at 17 mA = 153 mA exceed the 150 mA recommended sourcing group -> power_budget refuse', hit and 'EXCEEDS the recommended 150.0 mA' in hit[0]['detail'], _by(f, 'power_budget'))
    # ---- (h) the D6 -> D3 feedback with a heavier load
    f = run(loads=[{'pin': 'D6', 'kind': 'led', 'current_ma': 25}], links=[{'output': 'D6', 'input': 'D3'}])
    check('(h) D6 -> D3: a 25 mA load is past the 20 mA VOH is guaranteed at -> input_threshold (high) refuse; the same net at 13.6 mA is ok on both levels',
          [x['status'] for x in _by(f, 'input_threshold') if x['subject'].endswith('(high)')] == ['refuse']
          and _status(run(loads=[{'pin': 'D6', 'kind': 'led', 'current_ma': 13.6}], links=[{'output': 'D6', 'input': 'D3'}]), 'input_threshold') == ['ok'])

    # ---- the light test circuit
    f = run(**LIGHT)
    refused = [x for x in f if x['status'] == 'refuse']
    und = sorted({(x['rule'], x['subject']) for x in f if x['status'] == 'undetermined'})
    check('LIGHT TEST (D6 + 220 ohm + red LED, D2 button to GND with the pull-up, D6->D3 jumper): NO refusal', not refused, refused)
    check('LIGHT TEST: lifecycle ok, group budget ok (Vf-free ceiling 22.7 mA <= 150 mA), D3 low level ok, D2 open level ok', _status(f, 'lifecycle') == ['ok']
          and any(x['status'] == 'ok' and 'Sourcing group 2' in x['subject'] for x in _by(f, 'power_budget')) and any(x['status'] == 'ok' and x['subject'] == 'D6 -> D3 (low)' for x in _by(f, 'input_threshold'))
          and any(x['status'] == 'ok' and x['subject'] == 'D2 button to GND (open)' for x in _by(f, 'input_threshold')))
    why = ' '.join(x['detail'] for x in f if x['status'] == 'undetermined')
    check('LIGHT TEST: undetermined ONLY where a number is genuinely uncited — the red LED forward voltage, the pushbutton closed resistance, the recommended VCC/GND total',
          'forward voltage is not cited' in why and 'closed resistance is not cited' in why and 'recommended VCC/GND' not in why and 'no recommended supply-pin total' in why and len(und) == 5, und)
    for u in und:
        print('      undetermined: %s %s' % u)
    # with a CITED Vf the same design resolves (a synthetic cited number, to show the rule needs only that)
    g = run(**dict(LIGHT, loads=[dict(LIGHT['loads'][0], v_forward=2.0)]))
    check('  … with a cited Vf (synthetic 2.0 V) the same circuit is ok on voh_under_load / abs_max_not_target / D3 high', _status(g, 'voh_under_load') == ['ok'] and _status(g, 'abs_max_not_target') == ['ok']
          and [x['status'] for x in _by(g, 'input_threshold') if x['subject'] == 'D6 -> D3 (high)'] == ['ok'])
    # the circuit door (electrical_check.check) carries the same rules and the five keys
    from board.custom import electrical_check as EC
    fc = EC.check('uno-button-clock', 'arduino-uno-r3', EC.tables_for(manager=None))
    check('electrical_check.check(uno-button-clock) now carries rules f-j beside the five Phase-1 rules, every finding with the five keys, none refused',
          {'voh_under_load', 'power_budget', 'input_threshold', 'abs_max_not_target', 'lifecycle'} <= {x['rule'] for x in fc} and all(set(x) == {'rule', 'status', 'subject', 'detail', 'cite'} for x in fc)
          and not [x for x in fc if x['status'] == 'refuse'])


def _chain_door(check):
    import contextlib
    import io
    import types
    from board.custom import board_object as BO
    from board.custom import hardware_chain as HC
    t = BO.seed_tables()
    d13 = HC.chain_for('arduino-uno-r3', 'D13', t)
    kinds = [h['kind'] for h in d13]
    check('chain: D13 shows both package contacts (SPDIP 19, TQFP 17) and its lifecycle hops (init/runtime conditional, programming reserved) right under the SoC pin',
          kinds.index('SocPin') < kinds.index('PackageContact') < kinds.index('PinLifecycleConstraint') < kinds.index('PinFunction') and kinds.count('PackageContact') == 2 and kinds.count('PinLifecycleConstraint') == 3)
    d0 = HC.chain_for('arduino-uno-r3', 'D0', t)
    check('chain: D0 shows the RESERVED USB-serial transport hop', any(h['kind'] == 'PinLifecycleConstraint' and 'RESERVED while transport=usb-serial' in h['what'] for h in d0))
    check('chain: every new hop is a Class:name ref that resolves', all(h['ref'].partition(':')[2] in {r['name'] for r in t[h['kind']]} for h in d0 + d13 if h['kind'] in ('PackageContact', 'PinLifecycleConstraint')))
    # the real door on a real falcon.App (a route conflict crashes at boot: construct it, do not just import it)
    try:
        import falcon
        import falcon.testing
        from board.board_object_api import BoardObjectAPI
    except Exception as e:   # pragma: no cover — falcon absent
        check('chain door: falcon available', False, str(e))
        return
    tables = {c: {r['name']: types.SimpleNamespace(**{f: r.get(f, '') for f in BO._fields(c)}) for r in rows} for c, rows in t.items()}
    mgr = types.SimpleNamespace(objectTables=tables, idList=[])
    app = falcon.App()
    srv = types.SimpleNamespace(falconServer=app)
    with contextlib.redirect_stdout(io.StringIO()):
        BoardObjectAPI(polServer=srv, manager=mgr)
    cli = falcon.testing.TestClient(app)
    res = cli.simulate_get('/api/board/arduino-uno-r3/chain/D13')
    body = res.json
    check('chain door: GET /api/board/arduino-uno-r3/chain/D13 on a real falcon.App -> 200 with the package-contact and lifecycle hops',
          res.status_code == 200 and body.get('ok') and sum(1 for h in body['rows'] if h['kind'] == 'PackageContact') == 2 and sum(1 for h in body['rows'] if h['kind'] == 'PinLifecycleConstraint') == 3, (res.status_code, str(body)[:200]))
    res = cli.simulate_get('/api/board/arduino-uno-r3/chain/D0')
    check('chain door: D0 over the live door carries the reserved transport hop', res.status_code == 200 and any('RESERVED' in h['what'] for h in res.json['rows'] if h['kind'] == 'PinLifecycleConstraint'))


def main():
    import sys
    results = []

    def check(name, ok, detail=''):
        results.append(bool(ok))
        print('  [%s] %s%s' % ('PASS' if ok else 'FAIL', name, '' if ok else '  -> %s' % (str(detail)[:400],)))
    run_hardware_truth(check)
    print('\n%d/%d checks passed' % (sum(results), len(results)))
    sys.exit(0 if all(results) else 1)


if __name__ == '__main__':
    main()
