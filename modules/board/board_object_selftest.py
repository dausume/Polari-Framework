"""board_object_selftest — brd-bo, THE BOARD OBJECT (PCB_FROM_SCRATCH_PLAN §2b): the rows (UNO cited, C3 ingested from Zephyr upstream),
the rules (pins named once; a SoC pin assigned twice refused), the four views (deterministic by hash), ingest round trips, the conflict
path (rows unchanged), the UNO byte-identity on fixtures (every variant's board_config.h = dev-hn-0's), the C3 template reconciled, and the
"flip between them" proof (one assignment moved → every view changes the same identifier). The real builds are tests/board_object_probe.py.

    PYTHONPATH=.:modules python3 -m board.board_selftest      # runs this as part of the board selftest
"""
import copy
import hashlib
import json
import os
import re
import shutil
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
FIX = os.path.join(HERE, 'custom', 'fixtures', 'brd_bo_baseline.json')


def rows_and_rules(check):
    from board.board_seed import BOARD_SEED_PAIRS
    from board.custom import board_object as bo
    from board.custom.soc_atmega328p import PINS as M328, PWM_FUNCTIONS
    pairs = {n: rows for n, _, rows in BOARD_SEED_PAIRS}
    check('the board object\'s eight layer classes are seeded (code-owned) and its views / conflicts are observed, never seeded',
          all(pairs.get(c) for c in bo.LAYER_CLASSES) and not pairs['BoardView'] and not pairs['BoardConflict'])
    uno, c3 = bo.rows_for('uno'), bo.rows_for('c3')
    check('the Identity layer is brd-0\'s BoardDefinition, extended (soc_definition, revision, upstream_board) — no second board class',
          uno['identity'].get('soc_definition') == 'atmega328p' and c3['identity'].get('upstream_board') == 'zephyr:esp32c3_devkitm@v4.4.2')
    names = [p['canonical'] for p in uno['pins']]
    check('the UNO\'s 20 board pins D0–D13 + A0–A5 (Arduino\'s pinout, cited per pin)',
          sorted(names) == sorted(['D%d' % i for i in range(14)] + ['A%d' % i for i in range(6)])
          and all('arduino-uno-r3:pinout.%s' % p['canonical'] in json.loads(p['facts_json']) for p in uno['pins']))
    check('the ATmega328P SoC: all 23 I/O pins of the 28-SPDIP with the datasheet\'s alternate functions (Fig 1-1, Tables 14-3/6/9)',
          len(uno['soc_pins']) == 23 == len(M328) and next(s for s in uno['soc_pins'] if s['pin'] == 'PD6')['package_pin'] == '12'
          and 'OC0A' in next(s for s in uno['soc_pins'] if s['pin'] == 'PD6')['functions_json'])
    pin = {p['canonical']: p for p in uno['pins']}
    check('the pinout agrees with the datasheet: D13 = PB5 (LED_BUILTIN), D6 = PD6 TIMER0 OC0A (PWM_PIN), A0 = PC0 ADC0 (ADC_CHANNEL), D0/D1 = USART0',
          pin['D13']['soc_pin'] == 'PB5' and pin['D13']['firmware_symbol'] == 'LED_PIN' and (pin['D6']['peripheral'], pin['D6']['signal']) == ('TIMER0', 'OC0A')
          and pin['A0']['signal'] == 'ADC0' and pin['A0']['firmware_symbol'] == 'ADC_CHANNEL' and pin['D0']['peripheral'] == pin['D1']['peripheral'] == 'USART0')
    from board.custom import variants as V
    check('the PWM-capable pins are DERIVED from the SocPin rows minus the runtime\'s reserved Timer2: (5, 6, 9, 10) — brd-fi\'s literal, now from rows',
          V.PWM_PINS == (5, 6, 9, 10) and all(any(f in PWM_FUNCTIONS for f in json.loads(s['functions_json'])) for s in uno['soc_pins'] if s['pin'] in ('PD3', 'PB3')))
    check('the UNO headers carry their pin order (POWER 8, ANALOG 6, DIGITAL_L 8, DIGITAL_H 10, ICSP 6) and SDA/SCL/ICSP share the A4/A5/D11–D13 nets',
          {c['connector']: c['pin_count'] for c in uno['connectors']} == {'POWER': 8, 'ANALOG': 6, 'DIGITAL_L': 8, 'DIGITAL_H': 10, 'ICSP': 6}
          and next(c for c in uno['connector_pins'] if c['label'] == 'SCK')['net'] == 'LED_BUILTIN')
    check('the 16U2 is the UNO\'s USB identity: BoardHardware.usb_bridge_chip ATmega16U2, its usb ids COPIED from the Identity row (never typed twice)',
          uno['hardware']['usb_bridge_chip'] == 'ATmega16U2' and uno['hardware']['usb_ids_json'] == uno['identity']['usb_ids_json'] and '2341:0043' in uno['hardware']['usb_ids_json'])
    check('pins named once + a SoC pin assigned once + every net/connector/SoC pin a row — both boards hold', not bo.validate(uno) and not bo.validate(c3),
          bo.validate(uno) + bo.validate(c3))
    bad = copy.deepcopy(uno)
    next(p for p in bad['pins'] if p['canonical'] == 'D5')['soc_pin'] = 'PD6'
    w1 = bo.validate(bad)
    dup = copy.deepcopy(uno)
    dup['pins'].append(dict(next(p for p in dup['pins'] if p['canonical'] == 'D7')))
    w2 = bo.validate(dup)
    check('a SoC pin assigned twice is REFUSED (D5 → PD6: "SoC pin PD6 is assigned twice") and a pin named twice is REFUSED',
          any('PD6 is assigned twice' in w for w in w1) and any('named twice' in w for w in w2), w1 + w2)
    return uno, c3


def c3_ingest(check, c3):
    from board.custom import board_c3 as C
    src = json.load(open(os.path.join(C.UPSTREAM, 'SOURCE.json')))
    shas = {f['path']: f['sha256'] for f in src['files']}
    ok = all(hashlib.sha256(open(os.path.join(C.UPSTREAM, p), 'rb').read()).hexdigest() == s for p, s in shas.items())
    check('Zephyr v4.4.2\'s esp32c3_devkitm board dir is stored verbatim with its licence (Apache-2.0) and every file\'s sha256 (SOURCE.json)',
          ok and src['tag'] == 'v4.4.2' and 'Apache-2.0' in src['licence'] and 'LICENSE' in shas)
    r = C.ingested()
    by = {p['canonical']: p for p in r['pins']}
    check('INGESTED, not retyped: the console UART0 GPIO21 TX / GPIO20 RX, SPI2, I2C0, the button GPIO9 (alias sw0), each citing file:line',
          by['GPIO21']['signal'] == 'UART0_TX' and by['GPIO20']['signal'] == 'UART0_RX' and by['GPIO9']['alias'] == 'sw0' and r['console'] == 'uart0'
          and {'GPIO1', 'GPIO2', 'GPIO3', 'GPIO6', 'GPIO7', 'GPIO10'} <= set(by) and by['GPIO21']['origin'].startswith('ingested:boards/espressif/esp32c3_devkitm/esp32c3_devkitm-pinctrl.dtsi:L14'))
    check('a DISABLED node\'s pins are not an assignment: i2s (GPIO19/6/7/8/18) and twai (GPIO4/5) skipped, so no SoC pin is claimed twice',
          {s['node'] for s in r['skipped']} == {'i2s', 'twai'} and r['twice'] == [])
    pins = {p['canonical']: p for p in c3['pins']}
    check('the three layers on the C3 rows, each said: 9 ingested + GPIO18/19 USB (cited, datasheet Table 2-6) + GPIO4 UART1 TX (polari: the sc-3 trace)',
          len(c3['pins']) == 12 and pins['GPIO18']['origin'].startswith('cited:') and pins['GPIO4']['firmware_symbol'] == 'POLARI_TRACE_TX_GPIO'
          and pins['GPIO4']['origin'].startswith('polari:'))
    check('the SoC from the ingested dtsi: cpu0 160 MHz, sram1 384 KB @ 0x3fc80000, the module\'s 4 MB flash (esp32c3_mini_n4.dtsi); 22 bonded SocPins',
          c3['soc']['cpu_clock_hz'] == 160000000 and '4194304' in c3['soc']['memory_map_json'] and len(c3['soc_pins']) == 22
          and r['missing_includes'] == ['espressif/partitions_0x0_default.dtsi'])


def views_and_roundtrips(check, uno, c3):
    from board.custom import board_object as bo, ingest as I, views as V
    from board.custom import ingest_zephyr, sexpr
    out = {}
    for b, r in (('uno', uno), ('c3', c3)):
        for k in V.KINDS:
            try:
                a, a2 = V.render(r, k), V.render(copy.deepcopy(r), k)
                out[(b, k)] = a
                assert a['sha256'] == a2['sha256']
            except V.ViewRefused as e:
                out[(b, k)] = str(e)
    rendered = {k: v for k, v in out.items() if isinstance(v, dict)}
    check('views are deterministic by hash (two renders, one sha) and every view names the board sha it came from (UNO kicad + bare-c, C3 kicad + zephyr + esp-idf)',
          set(rendered) == {('uno', 'kicad'), ('uno', 'bare-c'), ('c3', 'kicad'), ('c3', 'zephyr'), ('c3', 'esp-idf')}
          and all(v['board_sha'] in ''.join(v['files'].values()) for v in rendered.values()))
    check('the UNO\'s Zephyr render REFUSES honestly ("no Zephyr target for the ATmega328P" — Zephyr v4.4.2 has no AVR arch); ESP-IDF on the UNO and bare-C on the C3 refuse too',
          'no Zephyr target for the ATmega328P' in out[('uno', 'zephyr')] and 'no AVR architecture' in out[('uno', 'zephyr')]
          and 'Espressif SoCs only' in out[('uno', 'esp-idf')] and 'no bare-C template for the C3' in out[('c3', 'bare-c')])
    net = rendered[('uno', 'kicad')]['files']['arduino-uno-r3.net']
    check('the KiCad netlist parses as a KiCad 6+ netlist (export / version E / design / components / nets; refs and codes unique; every node a component)',
          sexpr.check_netlist(sexpr.parse(net)) == [] and sexpr.write(sexpr.parse(net)) + '\n' == net)
    check('…and carries the same pin names as the C side: net PWM_LED = U1 pin 12 (PD6) + J3 pin 7 (D6); TEMP_SENSE on A0; LED_BUILTIN on D13 + ICSP SCK',
          re.search(r'\(name "PWM_LED"\)\s+\(node \(ref "J3"\) \(pin "7"\) \(pinfunction "D6"\)\)\s+\(node \(ref "U1"\) \(pin "12"\) \(pinfunction "PD6"\)\)', net) is not None
          and '(pinfunction "A0")' in net and '(pinfunction "SCK")' in net)
    rt = {}
    for (b, k), v in rendered.items():
        r = uno if b == 'uno' else c3
        res = I.ingest(r['board'], v['files'], k, r=r)
        rt[(b, k)] = len(res['conflicts'])
    check('every rendered view ingests back with ZERO conflicts (the round trip of each kind: %s)' % rt, set(rt.values()) == {0})
    ov = rendered[('c3', 'zephyr')]['files']['esp32-c3.overlay']
    d = ingest_zephyr.overlay(ov, c3['board'], 'esp32-c3.overlay')
    r2 = copy.deepcopy(c3)
    from board.custom.views.zephyr import carried
    keep = [p for p in r2['pins'] if not carried(p)]
    old = {p['canonical']: p for p in r2['pins']}
    rebuilt = keep + [dict(old.get(p['canonical'], {}), **{f: p[f] for f in V.CARRIES['zephyr'] + ('canonical', 'number')}) for p in d['pins']]
    r2['pins'] = rebuilt
    again = V.render(r2, 'zephyr')
    check('the C3 Zephyr ROUND TRIP: the overlay rendered from the ingested rows re-ingests to the SAME rows, and re-renders to the SAME sha (%s)'
          % rendered[('c3', 'zephyr')]['sha256'][:12], again['sha256'] == rendered[('c3', 'zephyr')]['sha256']
          and bo.board_sha(r2) == bo.board_sha(c3))
    return rendered


def conflict_path(check, c3, rendered):
    from board.custom import board_object as bo, ingest as I
    before = bo.board_sha(c3)
    files = dict(rendered[('c3', 'zephyr')]['files'])
    files['esp32-c3.overlay'] = files['esp32-c3.overlay'].replace('<UART1_TX_GPIO4>', '<UART1_TX_GPIO5>')
    res = I.ingest(c3['board'], files, 'zephyr', r=c3)
    got = {(c['pin'], c['field']) for c in res['conflicts']}
    check('a DELIBERATE conflict (a copy of the overlay with UART1_TX moved to GPIO5, ingested) → BoardConflict rows (GPIO4 absent from the view, GPIO5 '
          'not in the rows), state open, and the rows UNCHANGED (board sha before = after)',
          got == {('GPIO4', 'presence'), ('GPIO5', 'presence')} and all(c['state'] == 'open' for c in res['conflicts'])
          and bo.board_sha(bo.rows_for('c3')) == before == res['board_sha'] and res['view']['conflicts'] == 2, sorted(got))
    bc = rendered[('uno', 'bare-c')]['files']['board_config.h'].replace('#define LED_PIN      13', '#define LED_PIN      12')
    res2 = I.ingest('arduino-uno-r3', {'board_config.h': bc}, 'bare-c')
    check('…and on the bare-C side: a board_config.h saying LED_PIN 12 → one conflict (LED_PIN on D13 in the rows, on D12 in the view)',
          [(c['pin'], c['field'], c['rows_value'], c['view_value']) for c in res2['conflicts']] == [('D12', 'firmware_symbol', 'LED_PIN on D13', 'LED_PIN on D12')])


def uno_byte_identity(check):
    from board.custom import gen, variants as V
    from firmwarefaults.custom.scenarios import scenario_variants
    base = json.load(open(FIX))['uno']
    rows = V.SEED_FIRMWARE_VARIANTS + scenario_variants()
    same, keys = 0, []
    tmp = tempfile.mkdtemp(prefix='brdbo-st-')
    try:
        for name, kn in [(v['name'], {}) for v in rows] + [('uno-pair', {'instance_index': 1})]:
            key = name + ('#1' if kn else '')
            row = gen.gen('uno', None, os.path.join(tmp, key.replace('#', '_')), variant=name, variant_rows=rows, **kn)
            text = open(os.path.join(row['project_dir'], 'board_config.h')).read()
            same += hashlib.sha256(text.encode()).hexdigest() == base[key]['board_config_sha256']
            keys.append(key)
            if name == 'uno-sim-rig' and not kn:
                prov = json.loads(row['repro_json'])['board_object']
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    check('UNO BYTE-IDENTITY (fixtures): the pin constants now come from BoardPin rows and every variant\'s board_config.h is byte-identical to dev-hn-0\'s '
          '(%d/%d — the .hex follows; tests/board_object_probe.py rebuilds them on the board worker)' % (same, len(base)), same == len(base) == len(keys) == 17)
    check('…the build\'s repro block names where each pin constant came from (BoardPin D13 / D6 / A0) and the board sha',
          prov['pins'] == {'led_pin': {'from': 'BoardPin', 'pin': 'D13'}, 'pwm_pin': {'from': 'BoardPin', 'pin': 'D6'}, 'adc_channel': {'from': 'BoardPin', 'pin': 'A0'}}
          and len(prov['board_sha']) == 64)


def c3_template(check, rendered):
    from board.custom import gen_c3
    tmp = tempfile.mkdtemp(prefix='brdbo-c3-')
    try:
        row = gen_c3.gen_c3('c3-sim-rig', tmp)
        p = row['project_dir']
        pins_h = open(os.path.join(p, 'main', 'board_pins.h')).read()
        sdk = open(os.path.join(p, 'sdkconfig.defaults')).read()
        bo_prov = json.loads(row['repro_json'])['board_object']
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    tpl_h = open(os.path.join(gen_c3.TEMPLATE, 'main', 'polari_c3.h')).read()
    check('sc-3\'s template RECONCILED: main/board_pins.h is GENERATED from the rows (= the esp-idf view) and replaces the hand-written '
          '`#define POLARI_TRACE_TX_GPIO 4`; polari_c3.h keeps sc-3\'s line layout (92 lines, the include on line 23 — the image stays byte-identical)',
          pins_h == rendered[('c3', 'esp-idf')]['files']['board_pins.h'] and '#define POLARI_TRACE_TX_GPIO   4' in pins_h
          and tpl_h.count('\n') == 92 and tpl_h.splitlines()[22].startswith('#include "board_pins.h"') and not re.search(r'^#define POLARI_TRACE_TX_GPIO', tpl_h, re.M))
    check('…sdkconfig.defaults\' four board-owned lines (target, 4 MB flash, console none, FreeRTOS 1000 Hz) come from the rows IN PLACE — the rows '
          'agreed with the template (nothing changed, nothing added), so the file is the template\'s byte for byte',
          sdk == open(os.path.join(gen_c3.TEMPLATE, 'sdkconfig.defaults')).read() and bo_prov['sdkconfig_changed'] == [] == bo_prov['sdkconfig_added']
          and len(bo_prov['sdkconfig_board_lines']) == 4)
    edited, changed, added = gen_c3.apply_sdkconfig(sdk, {'CONFIG_FREERTOS_HZ': 'CONFIG_FREERTOS_HZ=100'})
    check('…a row change rewrites ITS line in place (FREERTOS_HZ 1000 → 100 at the same position), the app\'s own lines untouched',
          changed == ['CONFIG_FREERTOS_HZ'] and not added and edited.splitlines().index('CONFIG_FREERTOS_HZ=100') == sdk.splitlines().index('CONFIG_FREERTOS_HZ=1000'))


def flip(check, uno, c3):
    from board.custom import board_object as bo, gen, views as V
    u2, touched = bo.assign(uno, 'PWM_LED', 'D5')
    bc0, bc1 = V.render(uno, 'bare-c')['files']['board_config.h'], V.render(u2, 'bare-c')['files']['board_config.h']
    k1 = V.render(u2, 'kicad')['files']['arduino-uno-r3.net']
    check('THE FLIP (UNO): one assignment moved (net PWM_LED D6 → D5; rows touched D5, D6) → bare-C PWM_PIN 6 → 5 and the KiCad net PWM_LED now on '
          'U1 pin 11 (PD5) + J3 pin 6 (D5) — the same identifier in both views; D5 became TIMER0 OC0B (derived from PD5\'s functions)',
          touched == ['D5', 'D6'] and '#define PWM_PIN      6' in bc0 and '#define PWM_PIN      5' in bc1
          and re.search(r'\(name "PWM_LED"\)\s+\(node \(ref "J3"\) \(pin "6"\) \(pinfunction "D5"\)\)\s+\(node \(ref "U1"\) \(pin "11"\) \(pinfunction "PD5"\)\)', k1) is not None
          and (bo.pin_by_canonical(u2, 'D5')['peripheral'], bo.pin_by_canonical(u2, 'D5')['signal']) == ('TIMER0', 'OC0B'))
    tables = bo.to_tables(u2, bo.seed_tables())
    tmp = tempfile.mkdtemp(prefix='brdbo-flip-')
    try:
        row = gen.gen('uno', None, tmp, variant='uno-sim-rig', board_tables=tables)
        cfg = open(os.path.join(row['project_dir'], 'board_config.h')).read()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    check('…and `pol board gen` FROM the edited rows writes PWM_PIN 5 into the firmware\'s board_config.h (the pin source is the rows)',
          '#define PWM_PIN      5' in cfg and json.loads(row['repro_json'])['board_object']['pins']['pwm_pin'] == {'from': 'BoardPin', 'pin': 'D5'})
    c2, t2 = bo.assign(c3, 'UART1_TX', 'GPIO5')
    z0, z1 = V.render(c3, 'zephyr')['files']['esp32-c3.overlay'], V.render(c2, 'zephyr')['files']['esp32-c3.overlay']
    e1 = V.render(c2, 'esp-idf')['files']['board_pins.h']
    k2 = V.render(c2, 'kicad')['files']['esp32-c3.net']
    check('THE FLIP (C3 analogue): UART1_TX GPIO4 → GPIO5 → Zephyr <UART1_TX_GPIO4> → <UART1_TX_GPIO5>, ESP-IDF POLARI_TRACE_TX_GPIO 4 → 5, KiCad U1 pin 9 → 10',
          t2 == ['GPIO4', 'GPIO5'] and '<UART1_TX_GPIO4>' in z0 and '<UART1_TX_GPIO5>' in z1 and '<UART1_TX_GPIO4>' not in z1
          and '#define POLARI_TRACE_TX_GPIO   5' in e1 and '(pin "10") (pinfunction "GPIO5")' in k2)
    refused = []
    for net, to in (('PWM_LED', 'D3'), ('PWM_LED', 'D4'), ('PWM_LED', 'D13')):
        try:
            bo.assign(uno, net, to)
        except bo.BoardObjectRefused as e:
            refused.append(str(e))
    check('a move the board cannot honour is REFUSED with the reason: D3 (TIMER2 is the 1 ms tick), D4 (no Output Compare), D13 (already carries LED_BUILTIN)',
          len(refused) == 3 and 'TIMER2 is reserved' in refused[0] and 'no Output Compare' in refused[1] and 'already carries net LED_BUILTIN' in refused[2], refused)
    try:
        bo.assign(c3, 'UART1_TX', 'GPIO22')
        z = 'not refused'
    except bo.BoardObjectRefused as e:
        z = str(e)
    check('…and a C3 pin that is not on the package (GPIO22) is refused (no BoardPin, no SocPin)', 'no pin GPIO22' in z, z)


def api_and_page(check):
    from board.board_page import SEED_BOARD_PAGE_DISPLAYS as P
    text = P[0]['definition']
    check('/display/boards carries the board object as CONFIGURED tables (SocDefinition, BoardPin, RuntimeProfile, BoardView, BoardConflict) — no new component',
          all("'%s'" % c in text or '"%s"' % c in text for c in ('SocDefinition', 'BoardPin', 'RuntimeProfile', 'BoardView', 'BoardConflict')))

    class _Mgr:
        def __init__(self):
            from board.custom import board_object as bo
            from board import board_basis
            self.objectTables = {}
            for cls, rows in bo.seed_tables().items():
                if hasattr(board_basis, cls) and cls in bo.LAYER_CLASSES + ('BoardDefinition',):
                    self.objectTables[cls] = {i: type('R', (), dict(r)) for i, r in enumerate(rows)}

            class _DB:
                def saveInstanceInDB(self, o):
                    return True
            self.db = _DB()

    class _Resp:
        status, media = '200 OK', None

    class _Req:
        def __init__(self, body=b''):
            import io
            self.bounded_stream = io.BytesIO(body)

    from board.board_object_api import BoardObjectAPI
    api = BoardObjectAPI.__new__(BoardObjectAPI)
    api.manager, api.polServer = _Mgr(), None
    r1 = _Resp()
    api.on_get_pins(_Req(), r1, 'uno')
    r2 = _Resp()
    api.on_get_pins(_Req(), r2, 'longan-nano')
    check('GET /api/board/<board>/pins over a server\'s rows: the UNO\'s 20 pins + board sha + rules ok; an unmodelled board → 404 naming the modelled ones',
          r1.media['ok'] and len(r1.media['pins']) == 20 and r1.media['rules'] == ['ok'] and r2.status == '404 Not Found' and 'arduino-uno-r3' in r2.media['error'])


def run_board_object(check):
    print('\n== brd-bo: THE BOARD OBJECT ==')
    uno, c3 = rows_and_rules(check)
    c3_ingest(check, c3)
    rendered = views_and_roundtrips(check, uno, c3)
    conflict_path(check, c3, rendered)
    uno_byte_identity(check)
    c3_template(check, rendered)
    flip(check, uno, c3)
    api_and_page(check)
