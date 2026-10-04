"""
@module pcb.custom.uno_shield

THE UNO SHIELD's schematic DESIGN from brd-bo's rows (plan §3 step 7, D-pcb-4: the first board; pcb-0 = the schematic skeleton,
no PCB — that is pcb-2). Nothing about the UNO is typed here: the shield's headers are the UNO's five Connector rows minus ICSP
(a shield mates the four Arduino headers), each shield header pin i is the UNO ConnectorPin i (same order, the UNO row's name on
the symbol), and a header pin is WIRED only when its UNO net is one the shield uses — so +5V (POWER:5), GND (POWER:6, POWER:7,
DIGITAL_H:7), TEMP_SENSE (= BoardPin A0's net, ANALOG:1) and PWM_LED (= BoardPin D6's net, DIGITAL_L:7) come from the rows.
Every other header pin is left unconnected ON PURPOSE (the shield passes them through untouched) — ERC lists them; they are
never hidden behind no-connect flags.

The parts (D-pcb-5: all through-hole, hand-soldered; the kit's):
  U1  TMP36 (TO-92) on +5V / TEMP_SENSE / GND — symbol Sensor_Temperature:LM35-LP: KiCad 9's library has no TO-92 TMP36 symbol
      (only TMP36xS, the SOIC-8 part); LM35-LP is a TO-92 sensor with pin 1 +Vs, 2 Vout, 3 GND. That this is the TMP36 TO-92's
      order is NOT cited (the TMP36 datasheet was not fetched — analog.com timed out again on 2026-10-03; board.custom.uno_facts
      says the same) → `undetermined` on the Part row; re-read before pcb-2 places it.
  R1  220 Ω on PWM_LED (the kit's LED resistor; brd-fi's uno-sim-rig drives D6 = Timer0 OC0A) — Device:R, DIN0207 axial
  D1  LED (5 mm) R1 → anode, cathode → GND — Device:LED (pin 1 K, pin 2 A in KiCad's symbol)
  J1–J4 the four headers — Connector_Generic:Conn_01xNN, footprints PinHeader_1xNN_P2.54mm_Vertical (male: they plug into the
      UNO's sockets, whose rows name PinSocket_1xNN)
  power symbols +5V and GND on every power pin, a PWR_FLAG on each (the nets are fed through a connector, which ERC cannot see)
"""
import json

from board.custom import board_object as bo

BOARD = 'uno-shield'
HOST = 'arduino-uno-r3'
SHIELD_NETS_FROM_PINS = {'A0': 'the TMP36 output', 'D6': 'the LED through 220 Ω'}
POWER_NETS = ('+5V', 'GND')
LED_NET = 'LED_A'   # ours: R1 → D1 anode

PARTS = [
    {'ref': 'U1', 'lib_id': 'Sensor_Temperature:LM35-LP', 'value': 'TMP36GT9Z', 'footprint': 'Package_TO_SOT_THT:TO-92_Inline', 'role': 'sensor',
     'manufacturer': 'Analog Devices', 'mpn': 'TMP36GT9Z', 'package': 'TO-92',
     'pins': {'1': '+5V', '2': '<A0>', '3': 'GND'},
     'undetermined': 'TO-92 pin order 1 +Vs / 2 Vout / 3 GND taken from the LM35-LP symbol — NOT cited from the TMP36 datasheet (not fetched); the MPN suffix '
                     'GT9Z (TO-92) is the kit part as commonly sold, not read from the kit'},
    {'ref': 'R1', 'lib_id': 'Device:R', 'value': '220', 'footprint': 'Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P7.62mm_Horizontal', 'role': 'resistor',
     'manufacturer': '', 'mpn': '', 'package': 'DIN0207 axial', 'pins': {'1': '<D6>', '2': LED_NET},
     'undetermined': 'manufacturer / MPN / power rating: the kit\'s resistor is unspecified'},
    {'ref': 'D1', 'lib_id': 'Device:LED', 'value': 'LED', 'footprint': 'LED_THT:LED_D5.0mm', 'role': 'led', 'manufacturer': '', 'mpn': '',
     'package': '5 mm round', 'pins': {'A': LED_NET, 'K': 'GND'},
     'undetermined': 'colour, forward voltage and MPN: the kit\'s LED is unspecified (SPICE at pcb-1 needs them cited)'},
]


def _header_lib(n):
    return 'Connector_Generic:Conn_01x%02d' % n, 'Connector_PinHeader_2.54mm:PinHeader_1x%02d_P2.54mm_Vertical' % n


def design(tables=None):
    """→ {'board', 'host', 'host_sha', 'components': [...], 'nets': {net: [(ref, pin)]}, 'unconnected': [(ref, pin, uno pin)]}."""
    r = bo.rows_for(HOST, tables)
    pins = {p['canonical']: p for p in r['pins']}
    sig = {('<%s>' % c): pins[c]['net'] for c in SHIELD_NETS_FROM_PINS}
    used = set(sig.values()) | set(POWER_NETS)
    comps, nets, unconnected = [], {}, []
    by_conn = {}
    for cp in r['connector_pins']:
        by_conn.setdefault(cp['connector'], []).append(cp)
    jn = 0
    for c in sorted(r['connectors'], key=lambda c: c['ref']):
        if c['kind'] != 'header':
            continue
        jn += 1
        lib_id, fp = _header_lib(int(c['pin_count']))
        ref = 'J%d' % jn
        conn = {}
        for cp in sorted(by_conn.get(c['connector'], []), key=lambda x: int(x['number'])):
            if cp['net'] in used:
                conn[str(cp['number'])] = cp['net']
            else:
                unconnected.append((ref, str(cp['number']), '%s:%s %s' % (c['connector'], cp['number'], cp['label'])))
        comps.append({'ref': ref, 'lib_id': lib_id, 'value': c['connector'], 'footprint': fp, 'role': 'header', 'manufacturer': '', 'mpn': '',
                      'package': '1x%02d 2.54 mm' % int(c['pin_count']), 'pins': conn, 'uno_connector': c['name'],
                      'labels': {str(cp['number']): cp['label'] for cp in by_conn.get(c['connector'], [])},
                      'undetermined': 'header pin numbers follow the UNO rows, whose numbering is OURS except ICSP (brd-bo); the non-0.1" gap '
                                      'between the digital headers is geometry for pcb-2 (cite Arduino\'s drawing)'})
    for p in PARTS:
        comps.append(dict(p, pins={k: sig.get(v, v) for k, v in p['pins'].items()}))
    for c in comps:
        for pin, net in c['pins'].items():
            nets.setdefault(net, []).append((c['ref'], pin))
    return {'board': BOARD, 'host': HOST, 'host_sha': bo.board_sha(r), 'components': comps, 'nets': nets, 'unconnected': unconnected,
            'signals': {c: pins[c]['net'] for c in SHIELD_NETS_FROM_PINS}}


def part_rows(d, symbols=None, footprints=None):
    """Part rows (one per component — every shield part is its own BOM line)."""
    out = []
    for c in d['components']:
        prov = ('brd-bo: the UNO connector row %s (pins wired where the UNO net is one the shield uses)' % c['uno_connector']
                if c['role'] == 'header' else 'kit part (pcb-0 UNO shield, D-pcb-4)')
        out.append({'name': '%s:%s' % (d['board'], c['ref']), 'board': d['board'], 'value': c['value'], 'manufacturer': c['manufacturer'], 'mpn': c['mpn'],
                    'package': c['package'], 'mount': 'tht', 'symbol': c['lib_id'], 'footprint': c['footprint'], 'refs_json': json.dumps([c['ref']]),
                    'qty': 1, 'device_definition': '', 'lifecycle': '', 'lifecycle_source': '', 'datasheet': '', 'provenance': prov,
                    'licence_notes': 'our design (GPL-3.0 with the project); the KiCad library symbols/footprints it uses are CC-BY-SA-4.0 with the design '
                                     'exception — the generated schematic is free of the share-alike',
                    'undetermined': c.get('undetermined', ''), 'notes': 'nets: %s' % ', '.join('%s=%s' % (k, v) for k, v in sorted(c['pins'].items()))})
    return out
