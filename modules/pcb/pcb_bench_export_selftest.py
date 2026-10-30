"""pcb_bench_export_selftest - kxc-5 (AI-Notes/plans/KICAD_INTERCHANGE_PLAN.md): EXPORT WHAT WE CAN - a Bench (Boards on the Bench + their connections,
BENCH_BOARDS_PLAN bob-2) written as a KiCad schematic from our rows. Reference (custom/reference/kicad10_bench_export.json): KiCad 10.0.6 on econ-core read
the exported schematic of this exact scenario, re-exported its netlist and ran ERC (2026-10-30); the symbols written with are KiCad's own
(kicad10_symbols_bench_export.txt, CC-BY-SA-4.0 with the design exception).
Run by pcb_selftest.main().
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
REF = os.path.join(HERE, 'custom', 'reference')


def scenario():
    """The C3's J1 mated into a half breadboard from row 1; UNO D6 wired to strip 9 (C3 IO0), UNO GND to strip 1 (the C3's GND)."""
    from board.custom import bench_nets as BN
    from board.custom import footholds as FH
    uno, c3, bb = (FH.for_definition(*k)[0] for k in (('datasheet', 'arduino-uno-r3'), ('datasheet', 'esp32-c3'), ('geometry', 'breadboard-half')))
    boards = {'uno': {'label': 'UNO', 'footholds': uno}, 'c3': {'label': 'C3', 'footholds': c3}, 'bb': {'label': 'half breadboard', 'footholds': bb}}
    conns = BN.mate_header('c3', [f['foothold'] for f in c3 if f['foothold'].startswith('J1:')], 'bb', 'a', 1)
    conns += [{'from_board': 'uno', 'from_foothold': 'DIGITAL_L:7', 'to_board': 'bb', 'to_foothold': 'r9e'},
              {'from_board': 'uno', 'from_foothold': 'POWER:6', 'to_board': 'bb', 'to_foothold': 'r1c'}]
    return boards, conns


def run_bench_export(check):
    from pcb.custom import bench_export as X
    from pcb.custom import schematic_writer as W
    from pcb.custom import sexpr as S
    boards, conns = scenario()
    d, mapping, rep = X.design(boards, conns, 'polari-bench')   # the ICSP's 2 x 3 is read off its footholds' positions
    refs = {(r['board'], r['connector']): r for r in rep['boards']}
    check('KXC-5 THE BENCH AS PARTS: every header of the dev boards is ONE generic KiCad header pinned as its footholds (UNO POWER 1x08, ICSP 2x03 - read off its '
          'footholds\' 2 x 3 positions - C3 J1 / J3 1x15); the breadboard has no symbol (its strips are nets only) and says so',
          refs[('uno', 'POWER')]['symbol'] == 'Connector_Generic:Conn_01x08' and refs[('uno', 'ICSP')]['symbol'] == 'Connector_Generic:Conn_02x03_Odd_Even'
          and refs[('c3', 'J1')]['symbol'] == 'Connector_Generic:Conn_01x15' and any(s.startswith('bb ') for s in rep['skipped']) and len(rep['boards']) == 7, rep)
    gnd = sorted(d['nets'].get('GND', []))
    check('KXC-5 NETS = THE BENCH\'s: the UNO\'s and the C3\'s grounds are ONE GND (wired through the breadboard strip); UNO D6 and C3 IO0 share a net; the C3\'s '
          '5V is NOT merged with the UNO\'s (a power name is global in KiCad: the second, unjoined rail gets a numbered label)',
          (refs[('uno', 'POWER')]['ref'], '6') in gnd and (refs[('c3', 'J1')]['ref'], '1') in gnd
          and any({(refs[('uno', 'DIGITAL_L')]['ref'], '7'), (refs[('c3', 'J1')]['ref'], '9')} <= set(v) for v in d['nets'].values()) and '+5V_2' in d['nets'],
          sorted(d['nets'])[:12])
    libs = {}
    for line in open(os.path.join(REF, 'kicad10_symbols_bench_export.txt')):
        if not line.startswith(';'):
            lid, _, text = line.rstrip('\n').split('\t')
            libs[lid] = text
    text, report = W.write(d, libs, title='polari bench')
    ref = json.load(open(os.path.join(REF, 'kicad10_bench_export.json')))
    cmp = X.compare(d, [tuple(r) for r in ref['netlist']])
    check('KXC-5 KiCad READS IT THE SAME: written with KiCad\'s own symbols, the schematic passes our check; KiCad\'s re-exported netlist of it groups exactly '
          'our pins (11 of 11 multi-pin nets, none extra either way); KiCad\'s ERC: 29 unconnected pins (the footholds nothing lands on - the writer lists '
          'the same 29) + 5 single-pin labels (a C3 pin whose breadboard strip holds nothing else KiCad can draw)',
          not S.check_kicad(S.parse(text), 'kicad_sch') and cmp == {'same': 11, 'ours_only': [], 'kicad_only': []}
          and len(report['unconnected_pins']) == ref['erc']['error/pin_not_connected'] == 29 and ref['erc'].get('warning/isolated_pin_label') == 5,
          (cmp, len(report['unconnected_pins']), ref['erc']))

    for bid, defn in (('uno', 'arduino-uno-r3'), ('c3', 'esp32-c3')):
        boards[bid]['definition'] = defn
    d2, mapping2, rep2 = X.design(boards, conns, 'polari-bench')
    text2, report2 = W.write(d2, libs, title='polari bench')
    v = ref['devkit_variant']
    cmp2 = X.compare(d2, [tuple(r) for r in v['netlist']])
    c3 = next(r for r in rep2['boards'] if r['board'] == 'c3')
    check('KXC-5 THE C3 AS KiCad\'s OWN PART: with its definition known, the C3 is written as RF_Module:ESP32-C3-DevKitM-1 (J1 n -> pin n, J3 n -> 31 - n, the '
          'cited map) - KiCad\'s netlist still groups exactly our pins (11 of 11), and its ERC now reads the part\'s pin types: no power-flag clash (the writer '
          'no longer flags a net a power_out pin drives), two inputs not driven (RST - the board\'s own pull-up is not a foothold fact yet - and RX, unwired)',
          c3['symbol'] == 'RF_Module:ESP32-C3-DevKitM-1' and mapping2[('c3', 'J3:2')] == (c3['ref'], '29') and cmp2 == {'same': 11, 'ours_only': [], 'kicad_only': []}
          and 'error/pin_to_pin' not in v['erc'] and v['erc'].get('error/pin_not_driven') == 2 and any('RST' in s for s in v['not_driven'])
          and not S.check_kicad(S.parse(text2), 'kicad_sch'), (cmp2, v['erc']))


def run_polari_fields(check):
    """kxc-5b (his addition 2026-10-30): critical Polari data with no KiCad equivalent rides in hidden Polari.* properties and comes back on ingest.
    Reference: custom/reference/kicad10_resaved_bench_export.kicad_sch = our export of the scenario RE-SAVED by KiCad 10.0.6 (`kicad-cli sch upgrade`,
    econ-core 2026-10-30, format 20260306)."""
    from board.custom import bench_pins as BP
    from pcb.custom import bench_export as X
    from pcb.custom import kicad_read as K
    from pcb.custom import schematic_writer as W
    boards, conns = scenario()
    for bid, defn in (('uno', 'arduino-uno-r3'), ('c3', 'esp32-c3')):
        boards[bid]['definition'] = defn
    d, _, _ = X.design(boards, conns, 'polari-bench', firmware=BP.firmware_uses(boards, running={'uno': 'uno-light', 'c3': 'esp32c3-light'}))
    cand, _, _ = X.design(boards, conns, 'polari-bench', firmware=BP.firmware_uses(boards))   # nothing recorded as running: every use a candidate
    libs = {}
    for line in open(os.path.join(REF, 'kicad10_symbols_bench_export.txt')):
        if not line.startswith(';'):
            lid, _, text = line.rstrip('\n').split('\t')
            libs[lid] = text
    text, _ = W.write(d, libs, title='polari bench')
    ours = {s['ref']: json.loads(s['polari_json']) for s in K.read_project({'x.kicad_sch': text}, 'x')['SchematicSymbol'] if s['polari_json'] != '{}'}
    back = K.read_project({'x.kicad_sch': open(os.path.join(REF, 'kicad10_resaved_bench_export.kicad_sch')).read()}, 'x')
    theirs = {s['ref']: json.loads(s['polari_json']) for s in back['SchematicSymbol'] if s['polari_json'] != '{}'}
    c3 = next(v for v in ours.values() if v.get('Polari.Board') == 'c3')
    check('KXC-5b CRITICAL DATA RIDES IN KiCad FIELDS: every written part (the boards recorded as running uno-light / esp32c3-light; with nothing recorded a use is tagged :if-flashed) carries hidden Polari.Board / Definition / Connector / Drive (per pin: direction, '
          'volts, source / sink mA) / Firmware (per pin: variable + role) - the C3 part says pin 9 = esp32c3-light LED_PIN gpio.out and pin 2 = a 3.3 V '
          'supply; after KiCad 10 RE-SAVED the file (its own format 20260306) our ingest reads back the SAME fields for all six parts, with no problems',
          len(ours) == 6 and ours == theirs and not back['problems'] and '9=esp32c3-light:LED_PIN:gpio.out' in c3.get('Polari.Firmware', '')
          and '2=supply 3.3V' in c3.get('Polari.Drive', '') and back['Schematic'][0]['format_version'] == '20260306'
          and '9=esp32c3-light:LED_PIN:gpio.out:if-flashed' in dict(next(c for c in cand['components'] if c.get('polari_board') == 'c3')['polari_fields'])['Polari.Firmware'],
          (len(ours), len(theirs), back['problems'][:2]))
