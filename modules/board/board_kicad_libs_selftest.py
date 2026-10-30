"""board_kicad_libs_selftest - kxc-0 (2026-10-30): the board netlists against KiCad 10's OWN symbol libraries. The tables below were read on econ-core
(kicad-symbols 10.0.7, kicad-cli 10.0.6; sha256 of each .kicad_sym in board_c3.KICAD_LIB_REV): pin number -> pin name. The UNO's ATmega328P-P and the
C3's ESP32-C3 share our SocPin package pin numbers; KiCad names some C3 pins by their primary function, so the importer goes by number. The whole devkit
is RF_Module:ESP32-C3-DevKitM-1: pins 1-15 = J1, 16-30 = J3 reversed.
Run by board_selftest.run().
"""
import re

#: MCU_Espressif:ESP32-C3, the header GPIOs' pins (number -> KiCad's name)
KICAD_ESP32C3 = {'4': 'XTAL_32K_P', '5': 'XTAL_32K_N', '6': 'GPIO2', '8': 'GPIO3', '9': 'MTMS', '10': 'MTDI', '12': 'MTCK', '13': 'MTDO', '14': 'GPIO8',
                 '15': 'GPIO9', '16': 'GPIO10', '25': 'GPIO18', '26': 'GPIO19', '27': 'U0RXD', '28': 'U0TXD'}
#: the datasheet's primary-function names for those GPIOs (ESP32-C3 datasheet Table 2-1)
C3_ALIAS = {'XTAL_32K_P': 'GPIO0', 'XTAL_32K_N': 'GPIO1', 'MTMS': 'GPIO4', 'MTDI': 'GPIO5', 'MTCK': 'GPIO6', 'MTDO': 'GPIO7', 'U0RXD': 'GPIO20', 'U0TXD': 'GPIO21'}
#: MCU_Microchip_ATmega:ATmega328P-P, the port pins
KICAD_328P = {'2': 'PD0', '3': 'PD1', '4': 'PD2', '5': 'PD3', '6': 'PD4', '11': 'PD5', '12': 'PD6', '13': 'PD7', '14': 'PB0', '15': 'PB1', '16': 'PB2',
              '17': 'PB3', '18': 'PB4', '19': 'PB5', '23': 'PC0', '24': 'PC1', '25': 'PC2', '26': 'PC3', '27': 'PC4', '28': 'PC5'}
#: RF_Module:ESP32-C3-DevKitM-1, pins 1-30
KICAD_DEVKIT = ['GND', '3V3', '3V3', 'IO2', 'IO3', 'GND', 'RST', 'GND', 'IO0', 'IO1', 'IO10', 'GND', '5V', '5V', 'GND',
                'GND', 'IO19', 'IO18', 'GND', 'IO4', 'IO5', 'IO6', 'IO7', 'GND', 'IO8', 'IO9', 'GND', 'RX', 'TX', 'GND']


def _u1(text):
    return set(re.findall(r'\(node \(ref "U1"\) \(pin "([^"]*)"\) \(pinfunction "([^"]*)"\)', text))


def _libsource(text, ref):
    m = re.search(r'\(ref "%s"\).*?(?:\(footprint "([^"]*)"\))?\s*\(libsource \(lib "([^"]*)"\) \(part "([^"]*)"\)' % ref, text, re.S)
    return m and (m.group(2), m.group(3), m.group(1))


def run_kicad_libs(check):
    from board.custom import board_c3 as C
    from board.custom import board_object as bo
    from board.custom import views as V

    c3, uno = bo.rows_for('c3'), bo.rows_for('uno')
    kc, ku = V.render(c3, 'kicad')['files']['esp32-c3.net'], V.render(uno, 'kicad')['files']['arduino-uno-r3.net']
    check('KICAD PARTS: the C3\'s U1 = MCU_Espressif:ESP32-C3 on its QFN-32 footprint and J1/J3 = 1x15 2.54 mm pin headers (KiCad library names); the UNO\'s U1 = '
          'MCU_Microchip_ATmega:ATmega328P-P on DIP-28',
          _libsource(kc, 'U1') == ('MCU_Espressif', 'ESP32-C3', C.KICAD_CHIP_FOOTPRINT) and _libsource(kc, 'J1')[2] == _libsource(kc, 'J3')[2] == C.KICAD_HEADER_FOOTPRINT
          and _libsource(ku, 'U1') == ('MCU_Microchip_ATmega', 'ATmega328P-P', 'Package_DIP:DIP-28_W7.62mm'), (_libsource(kc, 'U1'), _libsource(ku, 'U1')))
    c3n, unon = _u1(kc), _u1(ku)
    check('KICAD PIN NUMBERS: every U1 node in both netlists sits on the KiCad symbol pin of the same function - 20/20 ATmega328P port pins by name, 15/15 C3 '
          'GPIOs by name or by the datasheet\'s primary-function alias (pin 9 MTMS = GPIO4, 27 U0RXD = GPIO20)',
          len(unon) == 20 and all(KICAD_328P.get(p) == f for p, f in unon) and len(c3n) == 15
          and all(C3_ALIAS.get(KICAD_ESP32C3.get(p), KICAD_ESP32C3.get(p)) == f for p, f in c3n),
          sorted(x for x in c3n if C3_ALIAS.get(KICAD_ESP32C3.get(x[0]), KICAD_ESP32C3.get(x[0])) != x[1]))
    kicad_style = re.sub(r'\(node \(ref "U1"\) \(pin "([^"]*)"\) \(pinfunction "[^"]*"\)',
                         lambda m: '(node (ref "U1") (pin "%s") (pinfunction "%s")' % (m.group(1), KICAD_ESP32C3[m.group(1)]), kc)
    ours, theirs = V.module('kicad').ingest({'esp32-c3.net': kc}, c3), V.module('kicad').ingest({'esp32-c3.net': kicad_style}, c3)
    check('KICAD IMPORT BY NUMBER: the C3 netlist with KiCad\'s own pin names (MTMS, U0RXD ...) reads back to the same pins as ours - GPIO4 stays GPIO4, not "MTMS"',
          'MTMS' in kicad_style and ours == theirs and any(p['soc_pin'] == 'GPIO4' for p in theirs['pins']),
          [p['soc_pin'] for p in theirs['pins']][:6])
    hdr = [(conn, i, lab) for conn, labs in sorted(C.HEADERS.items()) for i, lab in enumerate(labs, 1)]
    check('KICAD DEVKIT PART: every J1/J3 pin maps to the RF_Module:ESP32-C3-DevKitM-1 pin of the same label (J1 n -> n, J3 n -> 31 - n); 30 pins, each used once',
          all(KICAD_DEVKIT[C.kicad_devkit_pin(conn, i) - 1] == lab for conn, i, lab in hdr)
          and sorted(C.kicad_devkit_pin(conn, i) for conn, i, _ in hdr) == list(range(1, 31)) and C.KICAD_DEVKIT[1] == 'ESP32-C3-DevKitM-1',
          [(conn, i, lab, KICAD_DEVKIT[C.kicad_devkit_pin(conn, i) - 1]) for conn, i, lab in hdr if KICAD_DEVKIT[C.kicad_devkit_pin(conn, i) - 1] != lab][:4])
