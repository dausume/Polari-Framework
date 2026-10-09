"""board_selftest — brd-0 + brd-1 (board_uno_selftest): the register as rows, THE TWO RULES, simulate-few, cited facts, the engines seam, and
detection (a fake scanner result for the pol-core CP2102 and the UNO; the real host scan when run on the host).

    PYTHONPATH=.:modules python3 -m board.board_selftest      # from polari-framework/
"""
import json
import os
import sys

passed = total = 0


def check(label, cond, extra=''):
    global passed, total
    total += 1
    passed += bool(cond)
    print('  [%s] %s %s' % ('\033[0;32mPASS\033[0m' if cond else '\033[0;31mFAIL\033[0m', label, extra if not cond else ''))


def rows_and_classes():
    from board.board_basis import BOARD_CLASSES, BoardDefinition, AdapterDefinition, ProgrammerKind, DatasheetFact, Road
    from board.board_seed import (SEED_BOARD_DEFINITIONS as B, SEED_ADAPTER_DEFINITIONS as A, SEED_BOARD_ROADS as R,
                                  SEED_BOARD_TECH_NODES as N, BOARD_SEED_PAIRS)
    from board.custom.programmers import SEED_PROGRAMMER_KINDS as P
    from board.custom.uno_facts import SEED_UNO_FACTS as F
    from board.custom.register_import import load
    snap = load()
    check('thirty-seven row classes (brd-0 eight + brd-fi four + brd-bo ten: SocDefinition, SocPin, BoardHardware, BoardNet, Connector, '
          'ConnectorPin, BoardPin, RuntimeProfile, BoardConflict, BoardView; fs-2a one: TargetCompatibilityRule; fs-2d one: KitPart; '
          'ucd-0a nine: Peripheral, PeripheralSignal, PinFunction, SignalRoute, Register, RegisterField, RegisterSetting, RegisterFieldSetting, BoardPinNet; '
          'ucd-0b2a four: AddressSpace, RegisterAddressMapping, RegisterBlock, MemoryRegion)',
          len(BOARD_CLASSES) == 37)
    check('EVERY register §1 device is a BoardDefinition (%d)' % len(snap['devices']), len(B) == len(snap['devices']) == 33)
    check('EVERY register §1a adapter is an AdapterDefinition (%d)' % len(snap['adapters']), len(A) == len(snap['adapters']) == 13)
    reg = '/'.join([os.path.dirname(os.path.abspath(__file__))] + ['..'] * 4 + ['AI-Notes', 'designs', 'HARDWARE_CAPABILITY_REGISTER.md'])
    if os.path.isfile(reg):   # on the host (suite checkout): the committed snapshot is the register's current text
        from board.custom.register_import import read
        check('the committed register snapshot matches the register file (re-run register_import after editing it)',
              read(reg)['source_sha256'] == snap['source_sha256'])
    try:
        built = [BoardDefinition(**b) for b in B] + [AdapterDefinition(**a) for a in A] + [ProgrammerKind(**p) for p in P] \
            + [DatasheetFact(**f) for f in F] + [Road(**r) for r in R]
        check('every seed row constructs its class (no stray field)', len(built) == len(B) + len(A) + len(P) + len(F) + len(R))
    except TypeError as e:
        check('every seed row constructs its class (no stray field)', False, str(e))
    check('a register "?" stays empty and the notes name the column',
          all(v != '?' for b in B for v in b.values()) and any('unknown in the register' in b['notes'] for b in B))
    uno = next(b for b in B if b['name'] == 'arduino-uno-r3')
    check('the register cells are carried verbatim (status, origin, USB route, adapter)',
          uno['register_status'] == 'HIS PICK (bare C)' and uno['board_origin'] == 'Arduino (Italy, OSHW)'
          and 'Optiboot' in uno['usb_route'] and uno['adapter_needed'].startswith('none (native USB'))
    check('the five seed pair classes with rows + the measured BoardSimCost (two rows: brd-1 UNO, sc-3 C3) + two observed classes with none',
          {n for n, _, rows in BOARD_SEED_PAIRS if rows} >= {'BoardDefinition', 'AdapterDefinition', 'ProgrammerKind', 'DatasheetFact', 'Road', 'BoardSimCost'}
          and all(not rows for n, _, rows in BOARD_SEED_PAIRS if n in ('BoardInstance', 'FirmwareBuild', 'InstallPlan', 'InstallRecord', 'UnoAnalogState'))
          and len(next(rows for n, _, rows in BOARD_SEED_PAIRS if n == 'BoardSimCost')) == 2)   # sc-3: + the C3's QEMU twin
    return B, A, P, F, R, N


def rules(B, A, P):
    from board.custom.board_engines import rule2_ok, ENGINES
    prog = {p['name']: p for p in P}
    adapters = {a['name']: a for a in A}
    # RULE 1 (refined): every row the rule admits has a USB programmer or a known USB adapter in its chain
    bad1 = [b['name'] for b in B if b['usb_rule'] == 'ok' and not (
        (b['programmer'] in prog and prog[b['programmer']]['host_side'] == 'usb')
        or any(a in adapters for a in json.loads(b['adapter_ids_json'])))]
    check('RULE 1: every admitted device has a USB programmer or a known USB adapter in its chain', not bad1, str(bad1))
    check('RULE 1: every programmer named by a device is a ProgrammerKind row',
          all(not b['programmer'] or b['programmer'] in prog for b in B))
    check('RULE 1: every adapter named by a device is an AdapterDefinition row',
          all(a in adapters for b in B for a in json.loads(b['adapter_ids_json'])))
    check('RULE 1: every adapter row\'s HOST side is USB', all('usb' in (a['usb_connector'] + a['kind']).lower() for a in A))
    und = [b for b in B if b['usb_rule'] != 'ok']
    check('RULE 1: a row with no established route is never admitted silently — undetermined / not-a-target, with the reason',
          und and all(b['usb_rule'] in ('undetermined', 'not-a-target') and b['usb_rule_citation'] and not b['simulated'] for b in und),
          str([b['name'] for b in und]))
    # RULE 2: C / Verilog / SystemVerilog toolchains and flashers only
    bad2 = [p['name'] for p in P if not rule2_ok(p['engine']) or p['engine_kind'] not in ('flasher', 'c-compiler', 'hdl-toolchain')]
    check('RULE 2: every ProgrammerKind\'s engine is a C/Verilog/SystemVerilog toolchain or a flasher', not bad2, str(bad2))
    bad2b = [(b['name'], e) for b in B for e in json.loads(b['toolchain_engines_json']) if not rule2_ok(e)]
    check('RULE 2: every BoardDefinition.toolchain_engines name passes', not bad2b, str(bad2b))
    check('RULE 2: an Arduino core / MicroPython / VHDL engine would fail the rule',
          not rule2_ok('arduino-cli') and not rule2_ok('micropython') and not rule2_ok('ghdl') and 'arduino-cli' not in ENGINES)
    check('the ProgrammerKinds of plan §7a are all present (+ fpga-usb-jtag)',
          set(prog) == {'avrdude-optiboot', 'esptool', 'uf2', 'dfu', 'swd-probe', 'wch-isp', 'hss-usbdmsc', 'libero-gateware', 'fpga-usb-jtag'})
    from board.custom.programmers import render_dry_run
    argv = render_dry_run('avrdude-optiboot', mcu='atmega328p', port='/dev/serial/by-id/X', baud=115200, artifact='fw.hex')
    check('DRY-RUN renders the plan §3 avrdude argv exactly; a missing placeholder stays visible',
          argv == 'avrdude -p atmega328p -c arduino -P /dev/serial/by-id/X -b 115200 -D -U flash:w:fw.hex:i'
          and '{port}' in render_dry_run('avrdude-optiboot'))


def simulate_few_and_facts(B, F, R, N):
    sim = [b['name'] for b in B if b['simulated']]
    twins = {b['name']: b['twin'] for b in B if b['simulated']}
    check('ONLY the picked boards are simulated (the UNO in simavr; sc-3: the ESP32-C3 in the QEMU fork)',
          sorted(sim) == ['arduino-uno-r3', 'esp32-c3'] and twins == {'arduino-uno-r3': 'simavr:atmega328p', 'esp32-c3': 'qemu:esp32c3'}, str(twins))
    check('the UNO carries the five boards.txt VID:PIDs', json.loads(next(b for b in B if b['name'] == 'arduino-uno-r3')['usb_ids_json'])
          == ['2341:0043', '2341:0001', '2a03:0043', '2341:0243', '2341:006a'])
    check('DatasheetFacts exist for the UNO ONLY', F and all(f['board'] == 'arduino-uno-r3' for f in F))
    check('every UNO fact cites a URL, a document and a revision',
          all(f['url'].startswith('https://') and f['document'] and f['revision'] for f in F))
    facts = {f['fact_key']: f for f in F}
    check('boards.txt facts: max sizes 32256/2048, 115200 baud, pinned to a commit + line',
          facts['upload.maximum_size']['value'] == '32256' and facts['upload.maximum_data_size']['value'] == '2048'
          and facts['upload.speed']['value'] == '115200' and '/blob/11b9130' in facts['upload.maximum_size']['url']
          and facts['upload.maximum_size']['url'].endswith('#L89'))
    st = {r['board']: r for r in R}
    uno_steps = json.loads(st['arduino-uno-r3']['steps_json'])
    others = [r for b, r in st.items() if b not in ('arduino-uno-r3', 'esp32-c3')]
    us = {s['step']: s['status'] for s in uno_steps}
    cs = {s['step']: s['status'] for s in json.loads(st['esp32-c3']['steps_json'])}
    check('one Road per device; all todo except the UNO\'s and (sc-3) the C3\'s: twin + template done, flashed-on-hardware still todo — owed',
          len(R) == len(B) and all(r['status'] == 'todo' and all(s['status'] == 'todo' for s in json.loads(r['steps_json'])) for r in others)
          and us['twin'] == 'done' and us['firmware-template'] == 'done' and us['flashed-on-hardware'] == 'todo'
          and cs['twin'] == 'done' and cs['firmware-template'] == 'done' and cs['flashed-on-hardware'] == 'todo', (us, cs))
    check('every road hangs on the board-roads tree as one concept node', len(N) == len(B)
          and {n['name'] for n in N} == {r['concept_node'] for r in R})
    import inspect
    from board.board_basis import BoardSimCost
    params = set(inspect.signature(BoardSimCost.__init__).parameters)
    check('BoardSimCost carries the §8a yardstick (object_count, state_bytes, cycles_per_s, host_class, measured_at)',
          {'board', 'twin', 'object_count', 'state_bytes', 'cycles_per_s', 'host_class', 'measured_at'} <= params)


def engines():
    from board.custom import board_engines as be
    old = os.environ.pop(be.KNOB, None)
    try:
        r = be.resolve('avr-gcc')
        if r['how'] == 'refused':
            check('engines: a missing avr-gcc is REFUSED naming the knob, the image and the provider', be.KNOB in r['why'] and be.image_name() in r['why'] and 'board.engines' in r['why'])
        else:
            check('engines: avr-gcc resolves on this device (%s: %s)' % (r['how'], r['where']), r['how'] in ('local-binary', be.LOCAL_IMAGE))
        old_img = os.environ.get(be.IMAGE_KNOB)
        os.environ[be.IMAGE_KNOB] = 'polari-no-such-image:never'
        be._IMG_CACHE.clear()
        r = be.resolve('simavr')
        check('engines: with no binary and no image the refusal names %s, the image and docker-compose.board-engines.yml' % be.KNOB,
              r['how'] in ('refused', 'local-binary') and (r['how'] == 'local-binary' or ('polari-no-such-image:never' in r['why'] and 'board-engines.yml' in r['why'])))
        if old_img is None:
            os.environ.pop(be.IMAGE_KNOB, None)
        else:
            os.environ[be.IMAGE_KNOB] = old_img
        be._IMG_CACHE.clear()
        check('engines: the worker image carries the six UNO engines (avr-gcc/objcopy/size, avrdude, simavr, avr-twin), all RULE 2 kinds',
              set(be.IMAGE_ENGINES) == {'avr-gcc', 'avr-objcopy', 'avr-size', 'avrdude', 'simavr', 'avr-twin'} and all(be.rule2_ok(e) for e in be.IMAGE_ENGINES))
        os.environ[be.KNOB] = 'http://127.0.0.1:9'   # a declared worker that is not there
        be._CAP_CACHE.clear()
        r = be.resolve('avrdude')
        check('engines: a declared but unreachable worker refuses (never degrades to local)', r['how'] == 'refused' and 'unreachable' in r['why'])
        r = be.resolve('avrdude', flash=True)
        check('engines: a FLASH is refused on a remote worker (the USB host only)', r['how'] == 'refused' and 'USB port' in r['why'])
        check('engines: an unknown engine is refused by name', be.resolve('arduino-cli')['how'] == 'refused')
        check('engines: the three required engines are known with RULE 2 kinds',
              [be.engine_kind(e) for e in ('avr-gcc', 'avrdude', 'simavr')] == ['c-compiler', 'flasher', 'simulator'])
    finally:
        os.environ.pop(be.KNOB, None)
        if old is not None:
            os.environ[be.KNOB] = old
    m = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'polari-app.json')))
    req = {e['name']: e for e in m['requires']['engines']}
    check('polari-app.json requires.engines: avr-gcc, avrdude, simavr (+ sc-3: esp-idf, qemu-esp32c3) with kind + probe',
          set(req) == {'avr-gcc', 'avrdude', 'simavr', 'esp-idf', 'qemu-esp32c3'} and all(e.get('kind') and e.get('probe') for e in req.values()))


def detection(B, A):
    from board.custom.detect import match
    cp_byid = '/dev/serial/by-id/usb-Silicon_Labs_CP2102_USB_to_UART_Bridge_Controller_0001-if00-port0'
    fake = {'host': 'pol-core', 'observed_at': 'now',
            'usb': [{'bus': '003', 'dev': '003', 'vendor_id': '10c4', 'product_id': 'ea60', 'description': 'Silicon Labs CP210x UART Bridge', 'path': '003-5', 'usb_class': 'Vendor Specific Class'},
                    {'bus': '003', 'dev': '001', 'vendor_id': '1d6b', 'product_id': '0002', 'description': 'root hub', 'path': '003-0', 'usb_class': 'root_hub'},
                    {'bus': '003', 'dev': '025', 'vendor_id': '1a86', 'product_id': '8074', 'description': 'QinHeng hub', 'path': '003-2.4', 'usb_class': 'Hub'},
                    {'bus': '003', 'dev': '005', 'vendor_id': '0e8d', 'product_id': '7610', 'description': 'MediaTek Inc. WiFi', 'path': '003-7', 'usb_class': 'Vendor Specific Class'}],
            'serial': [{'by_id_path': cp_byid, 'device': '/dev/ttyUSB0', 'vendor_id': '10c4', 'product_id': 'ea60', 'serial': '0001', 'bus': '003', 'dev': '003'}]}
    r = match(fake, B, A)
    cp = [i for i in r['instances'] if i['usb_id'] == '10c4:ea60']
    check('detect: the pol-core CP2102 (10c4:ea60) = cp2102-usb-uart-modules, adapter present / target unknown',
          len(cp) == 1 and cp[0]['definition'] == 'cp2102-usb-uart-modules' and cp[0]['definition_kind'] == 'adapter'
          and cp[0]['state'] == 'adapter present, target unknown' and cp[0]['by_id_path'] == cp_byid and cp[0]['port'] == '/dev/ttyUSB0')
    check('detect: the adapter instance names the boards whose chain uses it (a person picks the target)',
          'beaglev-fire' in json.loads(cp[0]['possible_targets_json']) and cp[0]['target_board'] == '')
    check('detect: an unmatched device is listed unadmitted (never guessed, never stored); hubs are skipped',
          [u['usb_id'] for u in r['unadmitted']] == ['0e8d:7610'] and len(r['instances']) == 1)
    uno = dict(fake, usb=[{'bus': '001', 'dev': '009', 'vendor_id': '2341', 'product_id': '0043', 'description': 'Arduino SA Uno R3', 'path': '001-1', 'usb_class': 'Communications'}],
               serial=[{'by_id_path': '/dev/serial/by-id/usb-Arduino__www.arduino.cc__0043_X-if00', 'device': '/dev/ttyACM0', 'vendor_id': '2341', 'product_id': '0043', 'serial': 'X', 'bus': '001', 'dev': '009'}])
    r = match(uno, B, A)
    check('detect: an UNO R3 (2341:0043) is a BoardInstance "board present" with its by-id path (the brd-0 proof, faked)',
          len(r['instances']) == 1 and r['instances'][0]['definition'] == 'arduino-uno-r3' and r['instances'][0]['state'] == 'board present'
          and r['instances'][0]['port'] == '/dev/ttyACM0' and r['instances'][0]['name'] == 'pol-core:arduino-uno-r3@001-1')
    hint = dict(fake, usb=[], serial=[{'by_id_path': '/dev/serial/by-id/usb-Arduino__www.arduino.cc__0043_Y-if00', 'device': '/dev/ttyACM1'}])
    r = match(hint, B, A)
    check('detect: with no sysfs link a by-id name still matches by its hint, said so (matched_by)',
          len(r['instances']) == 1 and r['instances'][0]['matched_by'] == 'by-id-hint' and r['instances'][0]['definition'] == 'arduino-uno-r3')
    from board.board_basis import BoardInstance
    row = BoardInstance(**{k: v for k, v in cp[0].items() if k != 'description'})
    check('detect: an instance dict constructs a BoardInstance row', row.definition == 'cp2102-usb-uart-modules')
    # the real host, when there is one (a container sees no host USB: skipped honestly, not passed)
    try:
        from board.custom.detect import scan_host
        real = match(scan_host(), B, A)
        print('  [info] this host: %d board(s), %d adapter(s), %d unadmitted' % (real['summary']['boards'], real['summary']['adapters'], real['summary']['unadmitted']))
    except Exception as e:  # noqa: BLE001
        print('  [info] host scan skipped: %s' % e)


def page():
    from board.board_page import SEED_BOARD_PAGE_DISPLAYS as P
    rows = json.loads(P[0]['definition'])['rows']
    items = [it for row in rows for it in row['items']]
    names = [it['componentProps']['componentName'] for it in items]
    text = P[0]['definition']
    # demo1b: the pin map draws FIRST (the generic api-svg-panel, now a board SELECTOR over /api/board/pinmaps),
    # the pin-roles table right under it, then the devices tables (demo1: usable/tracked split; brd-wire:
    # + bindings; brd-bo: + SoCs, pins, runtime, views, conflicts; ucd-0a's six chain tables live on /display/hardware-chain)
    check('/display/boards is the pin-map drawing + configured tables only (no JSON panel)', P[0]['pageRoute'] == 'boards'
          and len(names) == 17 and set(names) == {'api-svg-panel', 'class-rows-table'}, str(names))
    check('/display/boards: the FIRST item is the pin-map drawing (api-svg-panel)', names[0] == 'api-svg-panel', str(names))
    check('the usable/tracked tables carry class, status, chip, ISA, USB route, adapter, simulated, road status',
          all(c in text for c in ('device_class', 'register_status', 'soc', 'isa', 'usb_route', 'adapter_needed', 'simulated', 'road_status')))
    # demo1: his ask — a clear usable-vs-tracked split, derived (readiness never hand-flagged), fed by GET /api/board/boards/readiness
    check('the devices table is split into "usable now" and "tracked for later", both fed by the derived readiness door',
          all(it['componentProps']['inputs'].get('dataPath') == '/api/board/boards/readiness'
              for it in items if it['id'] in ('boards-usable', 'boards-tracked')))
    check('usable reads readiness=usable; tracked reads readiness=partial,tracked (never the same set)',
          next(it['componentProps']['inputs']['filterValue'] for it in items if it['id'] == 'boards-usable') == 'usable'
          and next(it['componentProps']['inputs']['filterValue'] for it in items if it['id'] == 'boards-tracked') == 'partial,tracked')
    check('every table on /display/boards carries a non-empty description (what it is for / one row = / columns)',
          all(it.get('description') for it in items))
    # brd-bo generality (his 2026-10-04 ask): the pin map is a board SELECTOR (GET /api/board/pinmaps), never one
    # board wired into the page — and the pin-roles table under it is a described, cited, link-bearing table
    svg_item = next(it for it in items if it['id'] == 'boards-pinmap-svg')
    check('boards-pinmap-svg reads the board selector /api/board/pinmaps, not one hardcoded board',
          svg_item['componentProps']['inputs']['dataPath'] == '/api/board/pinmaps', svg_item['componentProps']['inputs'])
    roles_item = next(it for it in items if it['id'] == 'boards-pin-roles')
    check('boards-pin-roles reads GET /api/board/<board>/pin-roles with a cited link column',
          roles_item['componentProps']['inputs']['dataPath'] == '/api/board/arduino-uno-r3/pin-roles'
          and roles_item['componentProps']['inputs']['columnFormats'] == 'learn_more:link', roles_item['componentProps']['inputs'])


def readiness():
    """demo1: compute_readiness is DERIVED, never hand-flagged — a Road flip alone must not change it."""
    from board.custom.readiness import compute_readiness
    from types import SimpleNamespace as NS
    uno = NS(name='arduino-uno-r3', twin='simavr:atmega328p', simulated=True)
    c3 = NS(name='esp32-c3-devkitm-1', twin='renode:esp32c3', simulated=True)
    hazard3 = NS(name='hazard3-ice', twin='', simulated=False)
    variants = [NS(board_definition='arduino-uno-r3'), NS(board_definition='esp32-c3-devkitm-1')]
    solutions = [NS(board_definition='arduino-uno-r3')]
    scenarios = [NS(target_board='arduino-uno-r3'), NS(target_board='esp32-c3-devkitm-1')]

    r, why = compute_readiness(uno, variants, solutions, scenarios)
    check('the UNO (twin + template + a no-code solution + scenarios) is usable', r == 'usable', why)
    r, why = compute_readiness(c3, variants, solutions, scenarios)
    check('the ESP32-C3 (twin + template + scenarios, no solution yet) is usable with that named in readiness_why',
          r == 'usable' and 'no no-code solution yet' in why, why)
    r, why = compute_readiness(hazard3, variants, solutions, scenarios)
    check('a register-only board with no twin/template/run is tracked', r == 'tracked', why)
    partial_board = NS(name='partial-board', twin='renode:x', simulated=True)
    r, why = compute_readiness(partial_board, variants, solutions, scenarios)
    check('a board with only a twin (no template, no run) is partial', r == 'partial', why)
    # the Road is the PLAN, not the proof: flipping its status alone must not move readiness (no Road input exists
    # to compute_readiness at all — the function cannot see it, which IS the guarantee this check names).
    import inspect
    check('compute_readiness takes no Road/road_status argument (a Road step flip cannot change readiness by itself)',
          'road' not in ','.join(inspect.signature(compute_readiness).parameters).lower())


def pinmap():
    """demo1b: GET /api/board/<board>/pinmap.svg draws straight from brd-bo's rows — `pol board assign` moves a
    net to a different pin and the drawing changes with it (the same proof board_object_selftest runs for every
    other view). Reassign PWM_LED D6 -> D5 in a TEMP COPY of the seed rows and check the generated SVG text."""
    import re
    from board.custom import board_object as BO
    from board.custom import pinmap_svg as PM
    tables = BO.seed_tables()
    r = BO.rows_for('arduino-uno-r3', tables)
    before = PM.render(r)

    def row_text(svg, label):
        m = re.search(r'<title>([^<]*)</title><rect[^/]*/><text[^>]*>%s</text><text[^>]*>([^<]*)</text>' % re.escape(label), svg)
        return m.groups() if m else (None, None)

    _, before_d6 = row_text(before, 'D6')
    _, before_d5 = row_text(before, 'D5')
    check('pinmap before assign: D6 (PWM_LED) carries the net', before_d6 and 'PWM_LED' in before_d6, before_d6)
    check('pinmap before assign: D5 is plain gpio, no PWM_LED', before_d5 and 'PWM_LED' not in before_d5, before_d5)

    r2, touched = BO.assign(r, 'PWM_LED', 'D5')
    check('board_object.assign moves PWM_LED from D6 to D5', set(touched) == {'D5', 'D6'}, touched)
    after = PM.render(r2)
    check('pinmap after `pol board assign arduino-uno-r3 PWM_LED D5`: the SVG text changed', after != before)
    _, after_d6 = row_text(after, 'D6')
    _, after_d5 = row_text(after, 'D5')
    check('pinmap after assign: D6 reverts to its own net (no longer PWM_LED)', after_d6 and 'PWM_LED' not in after_d6, after_d6)
    check('pinmap after assign: D5 now carries PWM_LED', after_d5 and 'PWM_LED' in after_d5, after_d5)

    try:
        PM.render(BO.rows_for('no-such-board', tables))
        check('pinmap of an unmodelled board is refused, not silently empty', False)
    except BO.BoardObjectRefused:
        check('pinmap of an unmodelled board is refused, not silently empty', True)


def pin_roles():
    """brd-bo generality (his 2026-10-04 ask): the pin map and its role table work for ANY modelled board, not just
    the UNO — esp32-c3 has BoardPin rows but NO Connector/ConnectorPin header rows (ingested from a Zephyr dts that
    names none, board_object_seed.build() only calls board_uno.connectors()), so pinmap_svg's fallback column must
    still draw its pins by name, and GET .../pin-roles must still report its roles — both from the ONE vocabulary
    (board.custom.pin_roles.ROLE_NAMES) pinmap_svg's legend and `pol board pins` share."""
    from board.custom import board_object as BO
    from board.custom import pinmap_svg as PM
    from board.custom import pin_roles as PR
    tables = BO.seed_tables()

    r = BO.rows_for('arduino-uno-r3', tables)
    rows = PR.rows_for_roles(PM.pins_by_role(r))
    present = {row['role'] for row in rows}
    # the drawing (and so the role table) only walks the FOUR headers (POWER/ANALOG/DIGITAL_L/DIGITAL_H) — ICSP is
    # a separate Connector kind='icsp', excluded by design (render()'s own docstring: "the four headers"), so
    # 'spi' and 'button' (a C3-only role) never appear on the UNO specifically — this is the per-board PRESENT set,
    # not the full vocabulary (board.custom.pin_roles.ROLE_NAMES has all ten)
    check('UNO pin-roles: one row per role actually drawn (adc/gpio/ground/i2c/led/power/pwm/uart)',
          present == {'adc', 'gpio', 'ground', 'i2c', 'led', 'power', 'pwm', 'uart'}, sorted(present))
    check('UNO pin-roles: every row has a non-empty cited learn_more url',
          rows and all(row['learn_more'].startswith('http') for row in rows), [row['learn_more'] for row in rows])
    led = next((row for row in rows if row['role'] == 'led'), None)
    check('UNO pin-roles: the led role lists D13', bool(led) and 'D13' in led['pins'], led)

    rc3 = BO.rows_for('esp32-c3', tables)
    check('esp32-c3 has BoardPin rows but no header Connector rows (the generality case)',
          bool(rc3['pins']) and not [c for c in rc3['connectors'] if c.get('kind') == 'header'],
          len(rc3['pins']))
    svg = PM.render(rc3)
    gpio_names = [p['canonical'] for p in rc3['pins'] if p['canonical'].startswith('GPIO')]
    check('esp32-c3 pinmap.svg draws (no empty legend-only box) and lists its GPIO pins by name',
          bool(gpio_names) and all('>%s<' % name in svg for name in gpio_names), gpio_names[:4])
    rows_c3 = PR.rows_for_roles(PM.pins_by_role(rc3))
    check('esp32-c3 pin-roles table is non-empty too (rows + the shared role map, not a UNO-only table)',
          len(rows_c3) > 0, [row['role'] for row in rows_c3])


def main():
    B, A, P, F, R, N = rows_and_classes()
    rules(B, A, P)
    simulate_few_and_facts(B, F, R, N)
    engines()
    detection(B, A)
    page()
    readiness()
    pinmap()
    pin_roles()
    from board.board_uno_selftest import run_uno   # brd-1: gen / build / flash / twin / cost
    run_uno(check)
    from board.board_installer_selftest import run_installer   # brd-fi: variants / compat / the installer flow / the page
    run_installer(check)
    from board.board_mapping_selftest import run_mapping   # brd-wire: the computer<->firmware mapping
    run_mapping(check)
    from board.board_c3_selftest import run_c3   # sc-3: the ESP32-C3 template, its gen/build/flash/twin, the twin's cost
    run_c3(check)
    from board.board_object_selftest import run_board_object   # brd-bo: THE BOARD OBJECT — rows, views, ingest, conflicts, the flip
    run_board_object(check)
    from board.board_target_compat_selftest import run_target_compat   # fs-2a: task-kind <-> pin-role compatibility
    run_target_compat(check)
    from board.board_kit_parts_selftest import run_kit_parts   # fs-2d: power/reference pin detail + the kit parts register
    run_kit_parts(check)
    from board.board_chain_selftest import run_chain   # ucd-0a: THE HARDWARE CHAIN — rows, links both ways, the D3 walk
    run_chain(check)
    print('\n%d/%d checks passed' % (passed, total))
    return 0 if passed == total else 1


if __name__ == '__main__':
    sys.exit(main())
