"""pcb_kicad_connect_selftest - kxc-2 (AI-Notes/plans/KICAD_INTERCHANGE_PLAN.md): THE SCHEMATIC'S OWN ELECTRICAL GRAPH. Polari works out the nets from the
.kicad_sch itself (pins, wires, junctions, labels, power symbols, sheet instances - pcb.custom.kicad_connect); KiCad's exported netlist is only the cross-check.
References: custom/reference/kicad10_nets_*.tsv = `kicad-cli sch export netlist` (KiCad 10.0.6 on econ-core) of the three kicad-demos 9.0.2 fixtures and the four
polari-uno-light projects (custom/upstream/polari-uno-light/SOURCE.json: the uno-light bench, its analog harness and two negative controls).
Run by pcb_selftest.main().
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
DEMOS = os.path.join(HERE, 'custom', 'upstream', 'kicad-demos-9.0.2')
FIXTURES = (('ecc83', 'ecc83-pp'), (os.path.join('simulation', 'rectifier'), 'rectifier'), ('complex_hierarchy', 'complex_hierarchy'))
UNO = os.path.join(HERE, 'custom', 'upstream', 'polari-uno-light')
UNO_FIXTURES = ('uno-light', 'uno-light-no-sense', 'uno-light-simulation', 'uno-light-led-reversed')
# The uno-light S1 bench contract (was electronics/kicad/check_uno_light.py on econ, 2026-10-29): D2 = A1 pin 17 input, D6 = pin 21 output, D3 = pin 18 the
# polled sense jumpered to D6, the three UNO GND contacts 6 / 7 / 29.
UNO_CONTRACT = {'/BUTTON_INPUT': {('A1', '17'), ('SW1', '1')}, '/LED_CONTROL': {('A1', '18'), ('A1', '21'), ('R1', '1')},
                '/LED_ANODE': {('R1', '2'), ('D1', '2')}, 'GND': {('A1', '6'), ('A1', '7'), ('A1', '29'), ('D1', '1'), ('SW1', '2')}}


def uno_contract(rows):
    """The contract's breaches on an ingested uno-light: a contract net whose pins differ, or a contract pin found on some other net."""
    got = {}
    for e in rows['NetEndpoint']:
        if not e['ref'].startswith('#'):
            got.setdefault(e['net'], set()).add((e['ref'], e['pin']))
    bad = [(n, sorted(want - got.get(n, set())), sorted(got.get(n, set()) - want)) for n, want in UNO_CONTRACT.items() if got.get(n, set()) != want]
    pins = set().union(*UNO_CONTRACT.values())
    return bad + [(n, 'stray', sorted(v & pins)) for n, v in got.items() if n not in UNO_CONTRACT and v & pins]


def _ref(board):
    return [tuple(line.rstrip('\n').split('\t')) for line in open(os.path.join(HERE, 'custom', 'reference', 'kicad10_nets_%s.tsv' % board)) if not line.startswith('#')]


def run_kicad_connect(check):
    from pcb.custom import kicad_connect as N
    from pcb.custom import kicad_read as K

    res = {}
    for sub, board in FIXTURES:
        rows = K.read_project(K.read_dir(os.path.join(DEMOS, sub)), board)
        by = {}
        for e in rows['NetEndpoint']:
            by.setdefault(e['net'], []).append({'ref': e['ref'], 'pin': e['pin']})
        nets = [{'name': n['net'], 'endpoints': by.get(n['net'], [])} for n in rows['SchematicNet']]
        res[board] = (rows, N.compare(nets, _ref(board)))
    summary = {b: (c['same_groups'], c['names_equal'], len(c['ours_only']), len(c['kicad_only'])) for b, (_, c) in res.items()}
    check('KXC-2 OUR NETS = KiCad\'s: every net of the three demo schematics groups exactly the pins KiCad\'s own netlist groups (ecc83 13, rectifier 4, '
          'complex_hierarchy 52 - across both instances of its reused sheet) and carries KiCad\'s name (power / global names, /sheet/label, Net-(R1-Pad2), '
          'unconnected-(P5-Pad1))', summary == {'ecc83-pp': (13, 13, 0, 0), 'rectifier': (4, 4, 0, 0), 'complex_hierarchy': (52, 52, 0, 0)}, summary)
    rows = res['complex_hierarchy'][0]
    eps = {e['name']: e for e in rows['NetEndpoint']}
    u = [e for e in rows['NetEndpoint'] if e['ref'] in ('U201', 'U301') and e['pin'] == '8']
    check('KXC-2 ENDPOINTS: each pin on a net is a NetEndpoint with its ERC type from the library (U102 pin LV unconnected as KiCad says), its unit letter for a '
          'multi-unit part (U201B), its sheet instance; the op-amp supply pin 8 of BOTH instances lands on +12V (power symbols are global)',
          len(rows['NetEndpoint']) == 164 and {e['net'] for e in u} == {'+12V'} and len({e['instance_path'] for e in u}) == 2
          and all(e['pintype'] for e in rows['NetEndpoint']) and any(e['unit'] == 'B' for e in rows['NetEndpoint'] if e['ref'] == 'U201'), sorted(e['net'] for e in u))
    pwr = {n['net']: json.loads(n['pintypes_json']) for n in rows['SchematicNet']}
    check('KXC-2 NETS KNOW THEIR ERC TYPES: +12V counts its power_in pins; a PWR_FLAG marks a net driven without joining other nets by name (the old mistake: '
          'every flag was one global net)', pwr.get('+12V', {}).get('power_in', 0) >= 2 and len(rows['SchematicNet']) == 52, pwr.get('+12V'))
    from pcb.custom import ingest as I
    fake = {'blobs': {'assembly/rectifier.net': open(os.path.join(HERE, 'custom', 'reference', 'kicad10_nets_rectifier.tsv')).read().encode()}}
    r = res['rectifier'][0]
    net_text = '(export (version "E") (nets %s))' % ' '.join('(net (code "%d") (name "%s") %s)' % (i, n, ' '.join('(node (ref "%s") (pin "%s") (pintype "%s"))' % (a, b, c)
               for nn, a, b, c in _ref('rectifier') if nn == n)) for i, n in enumerate(sorted({x[0] for x in _ref('rectifier')}), 1))
    fake['blobs']['assembly/rectifier.net'] = net_text.encode()
    s = I.ours_vs_kicad(r, fake, 'rectifier')
    check('KXC-2 THE INGEST CROSS-CHECK: with the engine\'s netlist in the record, every SchematicNet row is marked "same" and the record says 4 of 4',
          s.get('same_groups') == 4 and s.get('ours_only') == 0 and all(n['kicad_check'] == 'same' for n in r['SchematicNet']), (s, [n['kicad_check'] for n in r['SchematicNet']]))

    uno = {}
    for b in UNO_FIXTURES:
        rows = K.read_project(K.read_dir(os.path.join(UNO, b)), b)
        by = {}
        for e in rows['NetEndpoint']:
            by.setdefault(e['net'], []).append({'ref': e['ref'], 'pin': e['pin']})
        c = N.compare([{'name': n['net'], 'endpoints': by.get(n['net'], [])} for n in rows['SchematicNet']], _ref(b))
        uno[b] = (rows, (c['same_groups'], c['names_equal'], len(c['ours_only']), len(c['kicad_only'])))
    summary = {b: v[1] for b, v in uno.items()}
    check('KXC-2 POLARI\'S OWN BENCH = KiCad\'s NETLIST: the uno-light projects (a whole-module UNO A1 with deliberate no-connects, its analog harness, '
          'two negative controls) group exactly KiCad\'s pins under KiCad\'s names - including the lone UNO pins named with a "/" (D0/RX), which KiCad '
          'writes unconnected-(A1-D0{slash}RX-Pad15)', summary == {'uno-light': (30, 30, 0, 0), 'uno-light-no-sense': (31, 31, 0, 0),
                                                                    'uno-light-simulation': (3, 3, 0, 0), 'uno-light-led-reversed': (3, 3, 0, 0)}, summary)
    good, cut = uno_contract(uno['uno-light'][0]), uno_contract(uno['uno-light-no-sense'][0])
    check('KXC-2 THE BENCH CONTRACT FROM OUR OWN GRAPH: uno-light keeps D2 -> SW1 -> GND, D6 -> R1 -> D1 -> GND with D3 jumpered to D6 and all three UNO '
          'grounds; the no-sense control (A1 D3 relabelled, ERC still quiet but for the lone label) is caught - D3 missing from /LED_CONTROL and stray on '
          '/SENSE_DISCONNECTED', good == [] and ('/LED_CONTROL', [('A1', '18')], []) in cut and ('/SENSE_DISCONNECTED', 'stray', [('A1', '18')]) in cut,
          (good, cut))
