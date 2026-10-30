"""
@module board.custom.board_zero

THE ARDUINO ZERO AS A BOARD SPEC (bob-5, 2026-10-30): one of the four dev boards on his home bench that had no pins. Three sources, each said:

  ingested   ArduinoCore-samd 1.8.14 variants/arduino_zero/variant.cpp (stored verbatim under custom/upstream/arduino-samd-1.8.14/, LGPL-2.1+): the
             pin table - Arduino pin number -> SAMD21 port pin, and each pin's peripheral functions (board.custom.ingest_arduino_variant)
  read       the Arduino Zero schematic (ArduinoZeroV4.0, 22/07/2019, CC-BY-SA; rendered - the PDF has no text layer): the PHYSICAL header order
             (sheet 2: J1 18 positions = D0..D13, GND, AREF, SDA, SCL; J2 14 = NC, IOREF, RESET, +3V3, +5V, GND, GND, PWRIN, A0..A5; ICSP; CN2 the
             10-pin SWD header), the SAMD21G18's QFP48 pin numbers, IOREF tied to +3V3, D13 driving its LED through a 2N7002 (TR3)
  cited      Arduino's own tech specs (docs-content tech-specs.yml @dab66ec, CC-BY-SA-4.0): I/O voltage 3.3 V, DC current per I/O pin 7 mA, 48 MHz
Zephyr's arduino_zero board (v4.4.2) was read and NOT used: it carries no Arduino header map (no gpio-map), only LEDs and peripherals.
"""
import os

from board.custom import ingest_arduino_variant as V
from board.custom import soc_samd21 as S21

BOARD = 'arduino-zero'
SOC = 'atsamd21g18a'
HERE = os.path.dirname(os.path.abspath(__file__))
VARIANT = os.path.join(HERE, 'upstream', 'arduino-samd-1.8.14', 'variants', 'arduino_zero', 'variant.cpp')
VARIANT_REL = 'arduino-samd-1.8.14/variants/arduino_zero/variant.cpp'

DOCS = {
    'variant': ('ArduinoCore-samd variant arduino_zero (variant.cpp pin table)', '1.8.14 (commit 993398cb), stored verbatim, sha256 '
                '899edd2a8b4d8dc63f76a696214f0d9d2581c2ea12d1753204c2fd832233dedc', 'https://github.com/arduino/ArduinoCore-samd/blob/1.8.14/variants/arduino_zero/variant.cpp'),
    'sch': ('Arduino Zero schematic', 'ArduinoZeroV4.0 22/07/2019, 3 sheets, sha256 b090511095fb288a9193a14a34dc4458154685a0b282e25048aeb00756f4c713 (read rendered 2026-10-30)',
            'https://docs.arduino.cc/resources/schematics/ABX00003-schematics.pdf'),
    'specs': ('Arduino Zero tech specs', 'docs-content commit dab66ecb (2026-09-22), tech-specs.yml sha256 506f92676159fd189e16f92c83aef4c0d18ad2dcff93689a95ddd508c505c728',
              'https://github.com/arduino/docs-content/blob/dab66ecbd6ad52cd742da6c19c5b6330a7f2caae/content/hardware/hero/boards/zero/tech-specs.yml'),
    'ds': S21.DOC,
}

#: sheet 2 of the schematic: the SAMD21G18 (U1) QFP48 pin number printed beside each port pin used here
PACKAGE_PINS = {'PA02': 3, 'PA03': 4, 'PB08': 7, 'PB09': 8, 'PA04': 9, 'PA05': 10, 'PA06': 11, 'PA07': 12, 'PA08': 13, 'PA09': 14, 'PA10': 15, 'PA11': 16,
                'PB10': 19, 'PB11': 20, 'PA12': 21, 'PA13': 22, 'PA14': 23, 'PA15': 24, 'PA16': 25, 'PA17': 26, 'PA18': 27, 'PA19': 28, 'PA20': 29, 'PA21': 30,
                'PA22': 31, 'PA23': 32, 'PA24': 33, 'PA25': 34, 'PB22': 37, 'PB23': 38, 'PA27': 39, 'PA28': 41, 'PB02': 47, 'PB03': 48, 'PA00': 1}

#: Arduino pin number -> the BoardPin canonical (0-13 = D0..D13, 14-19 = A0..A5, 20/21 = SDA/SCL, 22-24 = the legacy ICSP SPI, 42 = AREF)
CANONICAL = dict([(n, 'D%d' % n) for n in range(14)] + [(14 + i, 'A%d' % i) for i in range(6)] + [(20, 'SDA'), (21, 'SCL'), (22, 'MISO'), (23, 'MOSI'),
                                                                                                   (24, 'SCK'), (42, 'AREF')])
#: the CN2 SWD lines: sheet 2 (PA30_SWCLK -> CN2 4, PA31_SWDIO -> CN2 2); the variant lists them as pins 44 / 45
DEBUG = {'SWCLK': 'PA30', 'SWDIO': 'PA31'}

HEADERS = [
    {'connector': 'J1', 'labels': ['D%d' % n for n in range(14)] + ['GND', 'AREF', 'SDA', 'SCL'], 'fact': '%s:header.J1' % BOARD,
     'footprint': 'one 18-position part spanning the shield\'s DIGITAL_L (1-8) and DIGITAL_H (9-18) rows', 'order_note': 'pin 1 = D0 (PA11), as drawn on sheet 2'},
    {'connector': 'J2', 'labels': ['NC', 'IOREF', 'RESET', '3V3', '5V', 'GND', 'GND', 'VIN', 'A0', 'A1', 'A2', 'A3', 'A4', 'A5'], 'fact': '%s:header.J2' % BOARD,
     'footprint': 'one 14-position part spanning the shield\'s POWER (1-8) and ANALOG (9-14) rows', 'order_note': 'pin 1 = NC, as drawn on sheet 2'},
    {'connector': 'ICSP', 'labels': ['MISO', '5V', 'SCK', 'MOSI', 'RESET', 'GND'], 'fact': '%s:header.ICSP' % BOARD, 'footprint': '2x3, 2.54 mm',
     'order_note': 'odd pins one row (1 MISO, 3 SCK, 5 RESET), even the other (2 +5V, 4 MOSI, 6 GND)', 'notes': 'SPI on SERCOM4 - not the D11-D13 SPI (SERCOM1)'},
    {'connector': 'CN2', 'labels': ['3V3', 'SWDIO', 'GND', 'SWCLK', 'GND', 'NC', 'NC', 'NC', 'GND', 'RESET'], 'fact': '%s:header.CN2' % BOARD, 'kind': 'debug',
     'footprint': '2x5, the 10-pin Cortex debug header', 'order_note': 'as drawn on sheet 2 (upper left)',
     'notes': 'pins 6, 7, 8 carry no wire on sheet 2 (recorded NC); the target reset line passes R4 330R from the EDBG side'},
]


def _variant():
    text = open(VARIANT).read()
    return V.parse(text, VARIANT_REL)


def _pins_and_soc():
    rows = _variant()
    by_port, pins = {}, []
    for r in rows:
        if r['port_pin'] and r['port_pin'] not in by_port:
            by_port[r['port_pin']] = r
    for r in rows:
        c = CANONICAL.get(r['number'])
        if c and r['port_pin'] and all(p['soc_pin'] != r['port_pin'] for p in pins):
            fn = 'adc' if c.startswith('A') and c != 'AREF' else 'i2c' if c in ('SDA', 'SCL') else 'spi' if c in ('MISO', 'MOSI', 'SCK') else \
                 'analog-ref' if c == 'AREF' else 'gpio'
            pins.append({'canonical': c, 'number': r['number'], 'soc_pin': r['port_pin'], 'function': fn, 'signal': r['default'],
                         'peripheral': r['default'].split('/')[0] if r['default'] else '', 'facts': ['%s:variant.pin.%s' % (BOARD, r['port_pin'])],
                         'origin': 'ingested:%s (Arduino pin %d)' % (r['cite'], r['number']),
                         'notes': 'drives the yellow L LED through a 2N7002 (TR3, sheet 2): the LED is not a load on the pin' if c == 'D13' else ''})
    for c, port in DEBUG.items():
        pins.append({'canonical': c, 'number': by_port[port]['number'] or 0, 'soc_pin': port, 'function': 'debug', 'signal': c, 'peripheral': 'SWD',
                     'facts': ['%s:variant.pin.%s' % (BOARD, port)], 'origin': 'read:schematic sheet 2 (%s -> CN2) + %s' % (port, by_port[port]['cite'])})
    soc = [{'pin': p, 'package_pin': PACKAGE_PINS.get(p, ''), 'functions': r['functions'], 'default': r['default'], 'fact': '%s:variant.pin.%s' % (BOARD, p),
            'notes': '' if p in PACKAGE_PINS else 'QFP48 pin number not read from the schematic'} for p, r in sorted(by_port.items())]
    return pins, soc, by_port


def _spec():
    pins, soc, by_port = _pins_and_soc()
    f = []
    for p, r in sorted(by_port.items()):
        f.append(('variant.pin.%s' % p, '%s%s; %s' % ('Arduino pin %s' % r['number'] if r['number'] is not None else 'no Arduino pin', (' ' + r['label']) if r['label'] else '',
                                                      ' '.join(r['functions']) or 'no function listed'), '', r['cite'], 'default peripheral: %s' % (r['default'] or 'none marked'),
                  'variant', 'board'))
    f += [('header.%s' % h['connector'], ', '.join('%d %s' % (i, lab) for i, lab in enumerate(h['labels'], 1)), '', 'sheet 2, %s' % h['connector'], h.get('notes', ''), 'sch', 'board')
          for h in HEADERS]
    f += [('io.voltage', 3.3, 'V', 'Power: I/O Voltage', '"I/O Voltage: 3.3V"', 'specs', 'board'),
          ('io.dc_current_per_pin', 7, 'mA', 'Power: DC Current per I/O Pin', '"DC Current per I/O Pin: 7 mA" - the board vendor\'s per-pin figure', 'specs', 'board'),
          ('power.input', '5-18', 'V', 'Power: Input voltage (nominal)', '"Input voltage (nominal): 5-18V" (the barrel plug, PWRIN on the schematic)', 'specs', 'board'),
          ('power.ioref', '+3V3', '', 'sheet 2, J2 pin 2', 'IOREF is wired to the +3V3 net', 'sch', 'board'),
          ('clock.processor', 48000000, 'Hz', 'Clock speed: Processor', '"Processor: 48 MHz"', 'specs', 'soc')] + list(S21.FACTS)
    power = {'GND': ('GND', 'ground', 0.0, 'GND on J1 15, J2 6/7, ICSP 6, CN2', '%s:header.J2' % BOARD),
             '3V3': ('+3V3', 'power', 3.3, 'the +3V3 net (sheet 2 J2 pin 4); the I/O voltage is 3.3 V', '%s:io.voltage' % BOARD),
             'IOREF': ('+3V3', 'power', 3.3, 'IOREF is wired to +3V3 (sheet 2 J2 pin 2)', '%s:power.ioref' % BOARD),
             '5V': ('+5V', 'power', 5.0, 'the +5V net (sheet 2 J2 pin 5, ICSP pin 2)', '%s:header.J2' % BOARD),
             'RESET': ('RESET', 'signal', 0.0, 'the reset line: J2 3, ICSP 5 and CN2 10 are one net (sheet 2; the RESET button and D2 hang on it)', '%s:header.J2' % BOARD),
             'VIN': ('PWRIN', 'power', 0.0, 'PWRIN: the barrel-plug input, 5-18 V nominal - a range, not one rail voltage', '%s:power.input' % BOARD)}
    return {
        'board': BOARD, 'soc': SOC, 'soc_title': 'Microchip ATSAMD21G18A', 'vendor': 'Microchip (Atmel)', 'package': 'QFP48 (U1 "D21G18" on the schematic)',
        'isa': 'ARMv6-M (Cortex-M0+)', 'cpu_clock_hz': 48000000, 'clock_fact': '%s:clock.processor' % SOC,
        'soc_source': 'ArduinoCore-samd 1.8.14 variant arduino_zero (the per-pin function table) + the Arduino Zero schematic (QFP48 pin numbers)',
        'soc_undetermined': 'which drive strength (DRVSTR) a firmware sets is the firmware\'s; the board\'s 7 mA figure equals the datasheet\'s strong-drive source maximum',
        'logic': (3.3, 'fact %s:io.voltage = 3.3 V (Arduino Zero tech specs, "I/O Voltage: 3.3V")' % BOARD),
        'docs': DOCS, 'facts': f, 'soc_pins': soc, 'pins': pins, 'headers': HEADERS,
        'label_pin': {p['canonical']: p['canonical'] for p in pins}, 'power': power,
        'electrical': {'max_ma': 7, 'fact': '%s:io.dc_current_per_pin' % BOARD, 'kind': 'per-pin DC current (the board vendor\'s figure)'},
        'components': [{'ref': 'U1', 'value': 'ATSAMD21G18A', 'role': 'mcu', 'soc': SOC, 'fact': '%s:header.J1' % BOARD},
                       {'ref': 'TR3', 'value': '2N7002', 'role': 'led-driver', 'pin': 'PA17', 'fact': '%s:header.J1' % BOARD, 'notes': 'D13 -> the L LED'}]
                      + [{'ref': h['connector'], 'value': h['connector'], 'role': 'connector', 'connector': h['connector'], 'fact': h['fact']} for h in HEADERS],
        'rails': [],
        'hardware': {'crystal': '32.768 kHz (XIN32/XOUT32 on PA00/PA01; tech specs "RTC: 32.768 kHz")', 'usb_bridge_chip': 'the EDBG debugger (IC3, sheet 3) on the programming port; '
                     'native USB on PA24/PA25', 'source': 'board.custom.board_zero (variant 1.8.14 + schematic V4.0 + tech specs)',
                     'undetermined': 'regulator current limits (sheet 1 parts are not legible at the rendered size); the SAM D21 datasheet\'s DRVSTR drive figures',
                     'notes': 'two USB ports: Programming (EDBG, SERCOM5 PB22/PB23 as the UART) and Native (PA24/PA25)'},
    }


SPEC = _spec()
