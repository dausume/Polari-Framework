"""board_pin_view_c3_selftest - c3-pv (2026-10-29): the pin view draws the ESP32-C3-DevKitM-1. Its outline + header rows are CITED from Espressif's dimension drawing
(25.40 x 38.91 mm, J1-J3 22.86 mm, pitch 2.54 mm), its J1 / J3 pins are ConnectorPin rows from the user guide's Header Block, every QFN32 GPIO leg reaches its header
pin (partial: the MINI-1 module between is not traced), and nothing of the UNO is drawn on it. The UNO's own picture is unchanged by any of this.
Run by board_selftest.run().
"""
import json

BOARD = 'esp32-c3'


def run_pin_view_c3(check):
    from board.custom import board_c3 as C
    from board.custom import exposure_view as V
    from board.custom import hardware_system as HS
    from board.custom import pin_view as PV
    from board.custom import pv_shapes as S

    t = HS.default_tables()
    conns = [c for c in t['Connector'] if c['board'] == BOARD]
    cps = {c['name']: c for c in t['ConnectorPin'] if c['board'] == BOARD}
    check('C3 HEADERS: J1 + J3, 15 pins each, in the user guide\'s order (J1 pin 9 = IO0, J3 pin 2 = TX); every IO pin names its BoardPin (TX = GPIO21, RX = GPIO20, IOn = '
          'GPIOn) and every other pin a power net (GND, 3V3, 5V, RST = CHIP_PU); each row carries its Header Block fact',
          sorted((c['connector'], c['pin_count']) for c in conns) == [('J1', 15), ('J3', 15)] and cps['esp32-c3:J1:9']['board_pin'] == 'GPIO0'
          and cps['esp32-c3:J3:2']['board_pin'] == 'GPIO21' and cps['esp32-c3:J3:3']['board_pin'] == 'GPIO20' and cps['esp32-c3:J1:7']['net'] == 'CHIP_PU'
          and all(c['board_pin'] or c['net'] in ('GND', '3V3', '5V', 'CHIP_PU') for c in cps.values()) and all(c['fact'].startswith('esp32-c3:devkit.header.') for c in cps.values()),
          sorted((c['connector'], c['pin_count']) for c in conns))
    bps = {b['canonical']: b for b in t['BoardPin'] if b['board'] == BOARD}
    want = C.header_of()
    check('C3 BOARD PINS: every GPIO the headers break out (GPIO0-10, 18-21) is a BoardPin whose connector_pin is its header pin; the flash pads (GPIO12-17) are on no header',
          sorted(want, key=lambda g: int(g[4:])) == ['GPIO%d' % n for n in list(range(11)) + [18, 19, 20, 21]] and all(bps[g]['connector_pin'] == w for g, w in want.items())
          and not any(('GPIO%d' % n) in want for n in range(12, 18)), {g: bps.get(g, {}).get('connector_pin') for g in want})
    facts = {f['name']: f for f in t['DatasheetFact']}
    dim = facts.get('esp32-c3:devkit.dimensions', {})
    check('C3 FACTS: the Header Block tables (J1, J3) and the dimension drawing are DatasheetFact rows with document, revision (the drawing\'s sha256) and URL',
          'esp32-c3:devkit.header.J1' in facts and 'esp32-c3:devkit.header.J3' in facts and '25.40 x 38.91' in dim.get('value', '')
          and '284d7b4060098e252feafac8a412902b7c51d116b5df49111f4489fc84c92d92' in dim.get('revision', '') and dim.get('url', '').startswith('https://dl.espressif.com/'), dim)
    rows = V.board_rows(t, BOARD)
    from board.custom import exposure_e2_c3 as E3
    mine = {r[1] for r in E3.PATHS if r[1]}
    uno = [c for c in rows if c['enclosure'] == 'esp32-c3:board' and ('atmega' in c['inner_ref'] or 'arduino' in c['outer_ref']
                                                                       or (c['outer_ref'].startswith('SchematicPart:') and c['outer_ref'] not in mine))]
    e2 = [c for c in rows if c['enclosure'] == 'esp32-c3:board']
    paths = {(c['inner_ref'].rsplit(':', 1)[1], c['via_part'] or c['outer_ref']) for c in e2 if 'schematic' in c['document']}
    check('C3 BOARD PARTS from the schematic (sheet 2): GPIO8 -> R17 -> the RGB LED D6 + R20 pull-up, GPIO9 -> Boot SW1 + Q2, CHIP_EN -> Reset SW2 + R5, the UART0 legs -> the '
          'CP2102N through R21 / R22, GPIO18 / 19 -> R2 / R3 not fitted; each carries the schematic\'s sha256', {('14', 'R17'), ('14', 'R20'), ('15', 'SchematicPart:SW1:3'), ('15', 'Q2'),
          ('7', 'SchematicPart:SW2:3'), ('7', 'R5'), ('28', 'R22'), ('27', 'R21'), ('25', 'R2'), ('26', 'R3')} <= paths
          and all('d2ac6d649cbea3ce' in c['document'] for c in e2 if 'schematic' in c['document']), sorted(paths))
    check('C3 E2 MAP is the C3\'s own (the UNO\'s builder never runs for it): no ATmega leg, UNO header or UNO schematic part; every GPIO leg on a header -> its J1/J3 pin, '
          'CHIP_EN -> CHIP_PU, the ground pad -> GND; each PARTIAL, naming the untraced module, cited to the user guide',
          not uno and len([c for c in e2 if c['outer_ref'].startswith('ConnectorPin:')]) == len(want) and all(c['verification'] == 'partial' and 'MINI-1' in c['undetermined']
          and c['document'] == C.UG_DOC for c in e2 if c['document'] == C.UG_DOC) and all('MINI-1' in c['undetermined'] and 'schematic' in c['document'] for c in e2 if c['document'] != C.UG_DOC) and {c['outer_ref'] for c in e2 if c['outer_ref'].startswith('BoardNet:')} == {'BoardNet:esp32-c3:CHIP_PU', 'BoardNet:esp32-c3:GND'},
          [c['name'] for c in uno][:5])
    check('RAIL HEADER PINS are the board\'s own: BoardNet:esp32-c3:GND reaches the C3\'s GND header pins only, BoardNet:arduino-uno-r3:GND the UNO\'s only',
          V.header_pins('BoardNet:esp32-c3:GND', t) and all(n.startswith('esp32-c3:') for n in V.header_pins('BoardNet:esp32-c3:GND', t))
          and all(n.startswith('arduino-uno-r3:') for n in V.header_pins('BoardNet:arduino-uno-r3:GND', t)))
    r = PV.build(BOARD)
    shp = json.loads(next(x for x in S.shape_rows(t, BOARD) if x['name'] == S.shape_name('board', BOARD))['parameters_json'])
    heads = {p['label'] + ':' + str(p['number']): p for p in r['pins'] if p['kind'].startswith('header:') and p['surface'] == 'board:esp32-c3'}
    j1, j3 = sorted((p for p in r['pins'] if p['kind'] == 'header:J1'), key=lambda p: p['number']), sorted((p for p in r['pins'] if p['kind'] == 'header:J3'), key=lambda p: p['number'])
    check('C3 OUTLINE (cited): 25.40 x 38.91 mm from the dimension drawing; J1 and J3 run DOWN the board 2.54 mm apart, 22.86 mm between the rows, pin 1 at the antenna end '
          '(top); the inset, the vertical offset, the corners, the holes (none drawn) and U1\'s place are named knobs',
          r['ok'] and shp['bbox'] == [25.4, 38.91] and 'dimensions drawing' in shp['cited']['bbox']['document'] and len(j1) == len(j3) == 15
          and abs(j3[0]['x'] - j1[0]['x'] - 22.86) < 1e-6 and all(abs(b['y'] - a['y'] - 2.54) < 1e-6 and a['x'] == b['x'] for a, b in zip(j1, j1[1:]))
          and j1[0]['y'] < j1[-1]['y'] and shp['holes'] == [] and len(shp['knobs']) == 4 and heads, (shp.get('bbox'), len(j1), len(j3)))
    lines = [c for c in r['connections'] if c['kind'] == 'to-header']
    gpio0 = [c for c in lines if c['b'] == 'ConnectorPin:esp32-c3:J1:9']
    check('C3 PICTURE: the QFN32 package (U1) + its die + J1/J3 + the c3-light design parts on the bench column right of the board; every header line starts on a C3 leg '
          '(GPIO0 leg 4 -> J1 pin 9); nothing unresolved; no UNO surface or pin', [s['id'] for s in r['surfaces'] if s['level'] in ('board', 'package', 'die')]
          == ['board:esp32-c3', 'package:esp32-c3:U1', 'die:esp32-c3:U1'] and all(c['a'].startswith('PackageContact:esp32c3-32-qfn:') for c in lines)
          and [c['a'] for c in gpio0] == ['PackageContact:esp32c3-32-qfn:4'] and not r['unresolved'] and not any('arduino' in p['id'] or 'atmega' in p['id'] for p in r['pins'])
          and all(s['x'] > 25.4 for s in r['surfaces'] if s['level'] == 'bench'), r['unresolved'][:3])
