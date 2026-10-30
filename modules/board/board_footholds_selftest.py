"""board_footholds_selftest - bob-0 (AI-Notes/plans/BENCH_BOARDS_PLAN.md section 3): THE BENCH CONTRACT. Dev boards, breadboards and PCBs are equally
Boards on the Bench (his ruling 2026-10-30); each definition kind yields BoardFoothold rows through its own adapter - datasheet (UNO, ESP32-C3-DevKitM-1),
geometry (the breadboards), layers (an ingested KiCad PCB) - with the joined nodes and the abstracted drive / signal data, every number cited or -1.
Run by board_selftest.run().
"""
import json
import os


def run_footholds(check):
    from board.custom import footholds as FH

    uno, why = FH.for_definition('datasheet', 'arduino-uno-r3')
    by = {r['foothold']: r for r in uno}
    gnd = sorted(r['foothold'] for r in uno if r['node'] == 'net:GND')
    check('BOB-0 UNO (datasheet): one foothold per header pin (38: POWER 8, ANALOG 6, DIGITAL_L 8, DIGITAL_H 10, ICSP 6); the four GND pins share ONE node; '
          'SDA rides A4\'s node (the same net), NC is its own node',
          not why and len(uno) == 38 and gnd == ['DIGITAL_H:7', 'ICSP:6', 'POWER:6', 'POWER:7'] and by['DIGITAL_H:9']['node'] == by['ANALOG:5']['node']
          and by['POWER:1']['node'] == 'pin:POWER:1' and by['POWER:1']['direction'] == 'passive', (len(uno), gnd))
    d6, v33, vin = by['DIGITAL_L:7'], by['POWER:4'], by['POWER:8']
    check('BOB-0 UNO DRIVE + SIGNAL: D6 = chip pin PD6, inout, logic 5 V, 20 mA source and sink (the cited per-pin limit), families gpio + pwm-timer; +3V3 a 3.3 V '
          'supply limited to 50 mA (cited); VIN\'s voltage is a 6-20 V RANGE so its rail_volts stays -1 and says why - never an invented number',
          d6['chip_pin'] == 'PD6' and d6['direction'] == 'inout' and d6['logic_volts'] == 5.0 and d6['source_ma'] == d6['sink_ma'] == 20.0
          and {'gpio', 'pwm-timer'} <= set(json.loads(d6['families_json'])) and 'max_current_io' in d6['drive_basis']
          and v33['rail_volts'] == 3.3 and v33['source_ma'] == 50.0 and v33['direction'] == 'supply'
          and vin['rail_volts'] == -1.0 and '6-20' in vin['undetermined'], (d6['families_json'], v33['rail_volts'], vin['undetermined']))
    c3, _ = FH.for_definition('datasheet', 'esp32-c3')
    cb = {r['foothold']: r for r in c3}
    check('BOB-0 C3 (datasheet): 30 header pins (J1 + J3); 3V3 = 3.3 V from its cited BoardNet row; IO0 logic 3.3 V with 40 mA as a TYPICAL source and the sink '
          'not cited (-1); the I2C pins carry no limit and say so; J3 runs 22.86 mm right of J1 (the cited row spacing)',
          len(c3) == 30 and cb['J1:2']['rail_volts'] == 3.3 and cb['J1:9']['logic_volts'] == 3.3 and cb['J1:9']['source_ma'] == 40.0 and cb['J1:9']['sink_ma'] == -1.0
          and 'typical' in cb['J1:9']['drive_basis'] and cb['J1:5']['source_ma'] == -1.0 and 'no current limit' in cb['J1:5']['undetermined']
          and abs(cb['J3:1']['x_mm'] - cb['J1:1']['x_mm'] - 22.86) < 1e-6, (cb['J1:9']['drive_basis'][:80], cb['J1:5']['undetermined'][:80]))
    half, _ = FH.for_definition('geometry', 'breadboard-half')
    hb = {r['foothold']: r for r in half}
    check('BOB-0 BREADBOARD (geometry): the half board = 400 footholds (300 tie points + 100 rail holes, its nominal ties); strip 17 holes a-e are ONE node and '
          'f-j another (the centre trench); each rail is one node (64 nodes in all); every tie point passive; the contact rating not cited -> -1, said',
          len(half) == 400 and hb['r17a']['node'] == hb['r17e']['node'] != hb['r17f']['node'] == hb['r17j']['node']
          and hb['rail:top:+:1']['node'] == hb['rail:top:+:25']['node'] != hb['rail:top:-:1']['node'] and len({r['node'] for r in half}) == 64
          and all(r['direction'] == 'passive' for r in half) and hb['r1a']['source_ma'] == -1.0 and 'contact rating' in hb['r1a']['undetermined'],
          (len(half), len({r['node'] for r in half})))
    bud, _ = FH.for_definition('geometry', 'bud-bb-32650-w')
    check('BOB-0 A BREADBOARD NOT YET DRAWABLE: the BUD BB-32650-W keeps its 170 footholds and 34 nodes (from its cited counts) but no positions - its stated outline '
          'disagrees with the generated one, so x/y are -1 and the basis says why',
          len(bud) == 170 and len({r['node'] for r in bud}) == 34 and all(r['x_mm'] == -1.0 for r in bud) and bud[0]['position_basis'].startswith('not drawable'))
    none = [FH.for_definition(*a)[1] for a in (('geometry', 'pcb'), ('datasheet', 'no-such-board'), ('layers', 'never-ingested'), ('physics', 'x'))]
    check('BOB-0 REFUSALS IN WORDS: the reserved pcb BoardModel has no geometry, an unknown board, a PCB never ingested, an unknown kind - each a reason, no rows',
          all(none) and 'ingest' in none[2] and 'datasheet | geometry | layers' in none[3], none)

    from pcb.custom import kicad_footholds as KF
    from pcb.custom import kicad_read as K
    from pcb.custom import sexpr as S
    here = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'pcb', 'custom')
    bad, total = 0, 0
    for proj, pcb, ref in (('complex_hierarchy', 'complex_hierarchy.kicad_pcb', 'pcbnew_pads_complex_hierarchy.tsv'), ('ecc83', 'ecc83-pp.kicad_pcb', 'pcbnew_pads_ecc83.tsv')):
        tree = S.parse(open(os.path.join(here, 'upstream', 'kicad-demos-9.0.2', proj, pcb)).read())
        ours = {}
        for fp in S.find(tree, 'footprint'):
            for n, x, y, net in KF.pad_positions(fp):
                ours.setdefault((S.prop(fp, 'Reference'), n), []).append((x, y, net or '-'))
        for line in open(os.path.join(here, 'reference', ref)):
            if line.startswith('#'):
                continue
            r, n, x, y, net = line.rstrip('\n').split('\t')
            total += 1
            bad += not any(abs(a - float(x)) < 1e-3 and abs(b - float(y)) < 1e-3 and c == net for a, b, c in ours.get((r, n), []))
    check('BOB-0 PCB PAD POSITIONS = KiCad\'s: every pad of both demo boards (198) lands where pcbnew\'s GetPosition() puts it (footprint at + pad at, rotated by the '
          'footprint angle) with the same net', total == 198 and bad == 0, '%d of %d differ' % (bad, total))
    d = os.path.join(here, 'upstream', 'kicad-demos-9.0.2', 'ecc83')
    rows = K.read_project(K.read_dir(d), 'ecc83-pp')['BoardFoothold']
    gnd = [r for r in rows if r['net'] == 'GND']
    check('BOB-0 PCB (layers): the ingested ecc83 board\'s footholds are its connector pads (P1..P8: 12 pads, from the ingest); pads on one net share a node; GND '
          'reads 0 V by name, every other voltage -1 with the reason (the simulation, kxc-3)',
          len(rows) == 12 and {r['foothold'].split(':')[0] for r in rows} == {'P%d' % i for i in range(1, 9)} and all(r['definition_kind'] == 'layers' for r in rows)
          and len({r['node'] for r in gnd}) == 1 and all(r['rail_volts'] == 0.0 for r in gnd)
          and all(r['rail_volts'] == -1.0 and 'kxc-3' in r['undetermined'] for r in rows if r['net'] != 'GND' and not json.loads(r['families_json'])),
          sorted(r['foothold'] for r in rows))
    p4 = next(r for r in rows if r['foothold'] == 'P4:1')
    check('KXC-2 x BOB-0: a PCB foothold knows what is behind its pad from the schematic\'s own nets - P4 pin 1 joins U1 pin 9, an INPUT, so the pad is an input '
          'to the board (must be driven from outside); the unconnected pads P5..P8 say so',
          p4['direction'] == 'in' and 'U1:9 (input)' in p4['signal_basis'] and all('no other pin' in r['signal_basis'] for r in rows if r['foothold'].split(':')[0] in ('P5', 'P6', 'P7', 'P8')),
          (p4['direction'], p4['signal_basis']))


def run_bench_boards(check):
    from board.custom import bench_boards as BB
    from board.custom import bench as B
    rows = BB.boards_on_bench('home-bench')
    b = B.bench('home-bench')
    want_dev = len(json.loads(b.get('boards_json') or '[]'))
    want_bb = sum(int(e.get('count') or 1) for e in json.loads(b.get('breadboards_json') or '[]'))
    kinds = [(r['board_kind'], r['definition']) for r in rows]
    uno = next(r for r in rows if r['definition'] == 'arduino-uno-r3')
    bud = next(r for r in rows if r['definition'] == 'bud-bb-32650-w')
    zero = next(r for r in rows if r['definition'] == 'arduino-zero')
    check('BOB-1 ONE LIST: home-bench as Boards on the Bench - every dev board entry (datasheet) and every breadboard (geometry; a count of 2 = two entries) '
          'in one shape, each with its definition, a foothold summary and its Board Details route; a board with no pin rows says so instead of a number',
          len(rows) == want_dev + want_bb and [k for k, _ in kinds].count('dev-board') == want_dev and [k for k, _ in kinds].count('breadboard') == want_bb
          and uno['footholds'] == 38 and bud['footholds'] == 170 and zero['footholds'] == -1 and 'no BoardPin rows' in zero['footholds_note']
          and uno['details'] == '/display/board-details?board=datasheet/arduino-uno-r3' and uno['board'] == 'datasheet/arduino-uno-r3', kinds)
    check('BOB-1 a missing bench is None (the door answers 404)', BB.boards_on_bench('no-such-bench') is None)


def run_board_details(check):
    from board.board_details_page import BOARD_DETAILS_PAGES
    from board.custom import board_details as BD
    page = BOARD_DETAILS_PAGES[0]
    d = json.loads(page['definition'])
    tables = [it for r in d['rows'] for it in r.get('items', r.get('components', []))] if d.get('rows') else []
    tabs = [tb['key'] for tb in d.get('tabs', [])]
    blob = page['definition']
    check('BOB-3 THE PAGE: /display/board-details is bound by ?board=<kind>/<definition> (scope_from_query board), picks from the Boards on the Bench, and has '
          'Summary / Footholds / Nets / Parts / Layers / KiCad coverage + (bob-3b, a PCB\'s design) Pads / Copper / Zones / Drawings / Rules tabs, each reading '
          'GET /api/board/details/{kind}/{definition}/{part}',
          page['pageRoute'] == 'board-details' and d.get('scope_from_query') == ['board']
          and tabs == ['summary', 'footholds', 'nets', 'parts', 'layers', 'coverage', 'pads', 'copper', 'zones', 'drawings', 'rules']
          and '/api/board/benches/home-bench/all-boards' in blob and all(('/api/board/details/{scope:board}/%s' % p) in blob for p in BD.PARTS), tabs)
    s = BD.part('datasheet', 'arduino-uno-r3', 'summary')[0][0]
    lay = BD.part('datasheet', 'esp32-c3', 'layers')[0]
    none = BD.part('geometry', 'breadboard-half', 'layers')
    check('BOB-3 THE DOOR: the UNO\'s summary counts its 38 footholds and 7 parts; the C3\'s layers are its enclosure chain (package -> board); a breadboard\'s '
          'layers are empty WITH the reason (no layers at its definition level) - an answer, not an error',
          s['footholds'] == 38 and s['parts'] == 7 and any(r['kind'] == 'E1:qfn' for r in lay) and none[0] == [] and 'no layers' in none[1], (s, none[1]))


def run_bench_nets(check):
    from board.custom import bench_nets as BN
    from board.custom import footholds as FH
    uno, c3, bb = (FH.for_definition(*k)[0] for k in (('datasheet', 'arduino-uno-r3'), ('datasheet', 'esp32-c3'), ('geometry', 'breadboard-half')))
    boards = {'uno': uno, 'c3': c3, 'bb': bb}
    mated = BN.mate_header('c3', [f['foothold'] for f in c3 if f['foothold'].startswith('J1:')], 'bb', 'a', 1)
    check('BOB-2 MATING: the C3\'s J1 pushed into breadboard column a from row 1 = 15 mated connections, pin k -> hole r<k>a (J1:9 -> r9a)',
          len(mated) == 15 and {(c['from_foothold'], c['to_foothold']) for c in mated} >= {('J1:1', 'r1a'), ('J1:9', 'r9a'), ('J1:15', 'r15a')}
          and all(c['kind'] == 'mated' for c in mated), [(c['from_foothold'], c['to_foothold']) for c in mated][:3])
    wires = [{'from_board': 'uno', 'from_foothold': 'DIGITAL_L:7', 'to_board': 'bb', 'to_foothold': 'r9e'},   # UNO D6 (5 V logic) -> strip 9 = C3 IO0
             {'from_board': 'uno', 'from_foothold': 'POWER:6', 'to_board': 'bb', 'to_foothold': 'r1c'}]       # UNO GND -> the C3 GND strip
    nets, problems = BN.nets(boards, mated + wires)
    by = {n['net']: n for n in nets}
    io0 = by.get('IO0 / PWM_LED', {})
    check('BOB-2 ACROSS BOARDS: a C3 on a breadboard wired to an UNO is ONE graph - the GND strip joins both boards\' grounds, and UNO D6 (5 V logic) wired to '
          'the strip of C3 IO0 is flagged over-voltage (a 3.3 V pin on a net that carries 5 V), read off the foothold data alone',
          not problems and set(by['GND']['boards']) == {'bb', 'c3', 'uno'} and not by['GND']['findings']
          and [f['kind'] for f in io0.get('findings', [])] == ['over-voltage'] and 'c3 J1:9' in io0['findings'][0]['words'], sorted(by))
    bad, _ = BN.nets(boards, mated + [{'from_board': 'uno', 'from_foothold': 'POWER:5', 'to_board': 'bb', 'to_foothold': 'r2c'},     # UNO +5V -> the C3 3V3 strip
                                      {'from_board': 'uno', 'from_foothold': 'POWER:4', 'to_board': 'bb', 'to_foothold': 'r1d'}])    # UNO +3V3 -> the GND strip
    kinds = sorted(f['kind'] for n in bad for f in n['findings'])
    check('BOB-2 RAIL MISTAKES: the UNO\'s 5 V wired onto the C3\'s 3V3 strip = supply-conflict (two rails joined); the UNO\'s 3V3 onto the GND strip = '
          'supply-to-ground', 'supply-conflict' in kinds and 'supply-to-ground' in kinds, kinds)
    _, probs = BN.nets(boards, [{'from_board': 'uno', 'from_foothold': 'NOPE:1', 'to_board': 'bb', 'to_foothold': 'r1a'}])
    check('BOB-2 a connection to a foothold that does not exist is a problem in words, never silently dropped', probs and 'no such foothold' in probs[0], probs)


def run_board_details_copper(check):
    import types
    from board.custom import board_details as BD
    seg = types.SimpleNamespace(net='N', segments=1, arcs=0, vias=0, length_mm=29.1338, layers_json='["B.Cu"]',
                                segments_json=json.dumps([[0.0, 0.0, 29.1338, 0.0, 0.8, 'B.Cu']]))
    row = BD.copper_rows([seg], {'B.Cu': {'thickness': 0.035}})[0]
    none = BD.copper_rows([seg], {})[0]
    check('BOB-3b COPPER RESISTANCE from the copper itself: a 29.13 mm x 0.8 mm track in 35 um copper = rho L / (w t) = 0.01794 ohm with rho = 1/58 ohm mm2/m '
          '(IEC 60028, annealed copper by definition); with no copper thickness in the stackup the resistance is -1 and the basis says why',
          abs(row['dc_ohm_upper_bound'] - 0.01794) < 1e-5 and 'IEC 60028' in row['basis'] and none['dc_ohm_upper_bound'] == -1.0 and 'no copper thickness' in none['basis'],
          (row['dc_ohm_upper_bound'], none['basis']))


def run_bench_pins(check):
    """bob-2b: his correction 2026-10-30 - the Bench is pins + connections + firmware + drive checks, not a netlist."""
    from board.custom import bench_nets as BN
    from board.custom import bench_pins as BP
    from board.custom import footholds as FH
    uno, c3, bb = (FH.for_definition(*k)[0] for k in (('datasheet', 'arduino-uno-r3'), ('datasheet', 'esp32-c3'), ('geometry', 'breadboard-half')))
    boards = {'uno': {'label': 'UNO', 'footholds': uno, 'definition': 'arduino-uno-r3'}, 'c3': {'label': 'C3', 'footholds': c3, 'definition': 'esp32-c3'},
              'bb': {'label': 'half breadboard', 'footholds': bb, 'definition': 'breadboard-half'}}
    wiring = BN.mate_header('c3', [f['foothold'] for f in c3 if f['foothold'].startswith('J1:')], 'bb', 'a', 1)
    wiring += [{'from_board': 'uno', 'from_foothold': 'DIGITAL_L:7', 'to_board': 'bb', 'to_foothold': 'r9e'},
               {'from_board': 'uno', 'from_foothold': 'POWER:6', 'to_board': 'bb', 'to_foothold': 'r1c'}]
    rows, problems = BP.pin_rows(boards, wiring)
    by = {r['pin']: r for r in rows}
    check('BOB-2b THE BENCH IS PINS: the C3 on a breadboard wired to the UNO reads as FOUR rows, not a netlist - UNO D6, C3 IO0, and each board\'s grounds as '
          'ONE row ("UNO GND (4 pins)" <-> "C3 GND (10 pins)"); no breadboard hole is a row (holes are the board-level wiring, said in via)',
          not problems and sorted(by) == ['C3 GND (10 pins)', 'C3 IO0', 'UNO D6', 'UNO GND (4 pins)'] and by['UNO D6']['via'] == 'half breadboard'
          and by['UNO GND (4 pins)']['connections'] == 'C3 GND (10 pins)' and by['UNO GND (4 pins)']['status'] == 'ok', sorted(by))
    io0, d6 = by['C3 IO0'], by['UNO D6']
    check('BOB-2b FIRMWARE + DRIVE: both firmwares drive their LED pin (uno-light LED_PIN = D6, esp32c3-light LED_PIN = GPIO0, gpio.out) and the wire joins them -> '
          'contention on both; the C3 pin also gets over-voltage (the UNO drives 5 V, the C3 pin works at 3.3 V); the load note says no board-level circuit '
          'defines a load yet (the 20 / 40 mA limits wait for one)',
          'uno-light LED_PIN gpio.out' in d6['firmware'] and 'esp32c3-light LED_PIN gpio.out' in io0['firmware'] and 'contention' in d6['checks']
          and 'contention' in io0['checks'] and 'over-voltage' in io0['checks'] and 'over-voltage' not in d6['checks'] and 'no board-level circuit' in d6['notes'],
          (d6['checks'], io0['checks']))
    rows2, _ = BP.pin_rows(boards, wiring[:15] + [{'from_board': 'uno', 'from_foothold': 'POWER:5', 'to_board': 'bb', 'to_foothold': 'r1e'}])
    v5 = next(r for r in rows2 if r['pin'].startswith('UNO +5V'))
    check('BOB-2b SAFETY: the UNO\'s 5 V wired onto the C3\'s GND strip is a short on the UNO +5V row (its two +5V pins are one row; a supply connected to ground)',
          v5['status'] == 'finding' and 'connected to ground' in v5['checks'], v5['checks'])
