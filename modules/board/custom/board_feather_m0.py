"""
@module board.custom.board_feather_m0

THE ADAFRUIT FEATHER M0 EXPRESS (PID 3403) AS A BOARD SPEC (bob-5, 2026-10-30): one of the four dev boards on his home bench that had no pins. Read from:

  Adafruit's Eagle files (adafruit/Adafruit-Feather-M0-Express-PCB @5017ef4, CC BY-SA 3.0): the schematic's JP1 / JP3 nets and the board file's pad
  positions - JP1 = the 16-pin long side (pin 1 = GND at the TX end), JP3 = the 12-pin short side (pin 1 = BAT); there is no JP2
  adafruit/ArduinoCore-samd variants/feather_m0_express (LGPL-2.1+): Arduino pin -> port pin, the cross-check of every header pin
  the learn guide (Pinouts, Power Management): "All logic is 3.3V", the 3V pin "can supply 500mA peak", EN turns the regulator off
  the AP2112 datasheet (U2, AP2112-3.3) and the SAM D21 datasheet (board.custom.soc_samd21: the per-pin drive maxima by DRVSTR)
Every header pin agreed across the schematic, the board file, variant.cpp, the pinout PDF and the datasheet pinout. Recorded disagreements (none on a header
pin): the guide calls the flash CS Arduino #38 (the schematic and variant say PA13 = #39); "USB" carries the battery through D1 when no USB is present.
"""
from board.custom import soc_samd21 as S21

BOARD = 'adafruit-feather-m0-express'
SOC = S21.SOC
_REPO = 'https://raw.githubusercontent.com/adafruit/Adafruit-Feather-M0-Express-PCB/5017ef41885371f8a26ba1b8ab9dd700bd7ce655/'
DOCS = {
    'sch': ('Adafruit Feather M0 Express schematic (Eagle 6.6.0)', 'git 5017ef41 (2021-05-18), sha256 8eb1e5986ade72c1...', _REPO + 'Adafruit%20Feather%20M0%20Express.sch'),
    'brd': ('Adafruit Feather M0 Express board (Eagle 6.6.0)', 'git 5017ef41 (2021-05-18), sha256 0fb666534da006fb...', _REPO + 'Adafruit%20Feather%20M0%20Express.brd'),
    'variant': ('adafruit/ArduinoCore-samd variant feather_m0_express (variant.cpp)', 'git 3b19e648 (identical to master 2026-10-30), sha256 913704dab0045803...',
                'https://github.com/adafruit/ArduinoCore-samd/blob/3b19e64860944dbd54780e738c4749af14539fec/variants/feather_m0_express/variant.cpp'),
    'pinouts': ('Adafruit Feather M0 Express learn guide - Pinouts', 'guide last major update 2022-07-26; fetched 2026-10-30, sha256 1fe79749e1fdec4a...',
                'https://learn.adafruit.com/adafruit-feather-m0-express-designed-for-circuit-python-circuitpython/adafruit2-pinouts'),
    'power': ('Adafruit Feather M0 Express learn guide - Power Management', 'fetched 2026-10-30, sha256 ced674d52674d9ef...',
              'https://learn.adafruit.com/adafruit-feather-m0-express-designed-for-circuit-python-circuitpython/power-management-2'),
    'ap2112': ('Diodes Inc. AP2112 600mA CMOS LDO Regulator with Enable', 'DS39724 Rev. 2-2, June 2017, sha256 ef8d376f2ec356e2...', 'https://www.diodes.com/assets/Datasheets/AP2112.pdf'),
    'ds': S21.DOC,
}

#: (silk label, port pin, Arduino pin, BRD pad centre x, y mm) in pin order - SCH JP1 / JP3 nets (sch lines 4636 / 4642), BRD pads (brd lines ~4614 / 4623)
JP1 = [('GND', '', None, 44.45), ('TX', 'PA10', 1, 41.91), ('RX', 'PA11', 0, 39.37), ('MI', 'PA12', 28, 36.83), ('MO', 'PB10', 29, 34.29), ('SCK', 'PB11', 30, 31.75),
       ('A5', 'PB02', 19, 29.21), ('A4', 'PA05', 18, 26.67), ('A3', 'PA04', 17, 24.13), ('A2', 'PB09', 16, 21.59), ('A1', 'PB08', 15, 19.05), ('A0', 'PA02', 14, 16.51),
       ('GND', '', None, 13.97), ('AREF', 'PA03', 41, 11.43), ('3V', '', None, 8.89), ('RST', '', None, 6.35)]
JP3 = [('BAT', '', None, 16.51), ('EN', '', None, 19.05), ('USB', '', None, 21.59), ('13', 'PA17', 13, 24.13), ('12', 'PA19', 12, 26.67), ('11', 'PA16', 11, 29.21),
       ('10', 'PA18', 10, 31.75), ('9', 'PA07', 9, 34.29), ('6', 'PA20', 6, 36.83), ('5', 'PA15', 5, 39.37), ('SCL', 'PA23', 27, 41.91), ('SDA', 'PA22', 26, 44.45)]
JP_Y = {'JP1': 1.27, 'JP3': 21.59}
#: the silk label -> the BoardPin canonical (Arduino names, as the Zero: D<n>, A<n>, SDA, SCL, AREF, MISO / MOSI / SCK)
CANON = {'TX': 'D1', 'RX': 'D0', 'MI': 'MISO', 'MO': 'MOSI', 'SCK': 'SCK', 'AREF': 'AREF', 'SCL': 'SCL', 'SDA': 'SDA'}
NOTES = {'D13': 'the red L LED through R7 2.2K to GND (the LED loads the pin: (3.3 V - Vf) / 2.2K)', 'D9': 'also the battery divider R3/R6 100k/100k from BAT: it idles '
         'near half the battery voltage', 'D0': 'Serial1 RX (SERCOM0)', 'D1': 'Serial1 TX (SERCOM0)'}


def _canon(label):
    return CANON.get(label) or (label if label.startswith('A') and label[1:].isdigit() else 'D%s' % label)


def _spec():
    pins, positions, headers = [], {}, []
    for conn, rows in (('JP1', JP1), ('JP3', JP3)):
        labels = []
        for n, (silk, port, ard, x) in enumerate(rows, 1):
            labels.append(_canon(silk) if port else silk)
            positions[(conn, n)] = (x, JP_Y[conn])
            if port:
                c = _canon(silk)
                fn = 'adc' if c.startswith('A') and c != 'AREF' else 'i2c' if c in ('SDA', 'SCL') else 'spi' if c in ('MISO', 'MOSI', 'SCK') else \
                     'analog-ref' if c == 'AREF' else 'uart' if c in ('D0', 'D1') else 'gpio'
                pins.append({'canonical': c, 'number': ard, 'soc_pin': port, 'function': fn, 'facts': ['%s:header.%s' % (BOARD, conn)],
                             'origin': 'read:Eagle schematic %s pin %d (silk %s) -> %s; variant.cpp Arduino %d' % (conn, n, silk, port, ard), 'notes': NOTES.get(c, '')})
        headers.append({'connector': conn, 'labels': labels, 'fact': '%s:header.%s' % (BOARD, conn), 'footprint': 'HEADER-1X%d, 2.54 mm' % len(rows),
                        'order_note': {'JP1': 'pin 1 = GND at the TX end; pin 16 = RST at the USB end', 'JP3': 'pin 1 = BAT at the USB end; pin 12 = SDA'}[conn]})
    f = [('header.%s' % h['connector'], ', '.join('%d %s' % (i, lab) for i, lab in enumerate(h['labels'], 1)), '', 'Eagle %s nets (sch) + pad positions (brd)' % h['connector'],
          'cross-checked against variant.cpp, the pinout PDF and the datasheet pinout: no disagreement', 'sch', 'board') for h in headers]
    f += [('io.logic', 3.3, 'V', 'Pinouts, line 26', '"All logic is 3.3V"', 'pinouts', 'board'),
          ('power.3v_peak', 500, 'mA', 'Pinouts, line 20', '"3V - this is the output from the 3.3V regulator, it can supply 500mA peak"; Power Management line 30: '
           '"you can\'t do it continuously from 5V as it will overheat the regulator"', 'pinouts', 'board'),
          ('power.regulator', 'U2 AP2112-3.3: 3.3 V typ (98.5-101.5 %), IOUT(MAX) min 600 mA', '', 'p.8 AP2112-3.3 Electrical Characteristics',
           'the schematic\'s U2 (IN = VBUS, OUT = +3V3, EN = EN)', 'ap2112', 'board'),
          ('power.en', 'tie to GND -> the 3.3 V regulator off; 100k pull-up R1 to VBUS', '', 'Power Management line 64; schematic R1',
           '"The BAT and USB pins will still be powered."', 'power', 'board'),
          ('power.usb', 'VBUS: +5V from USB when connected; on battery alone VBAT through D1 (MBR120)', '', 'Power Management line 30; schematic D1',
           'the guide says "+5V from USB if connected"; the schematic adds the battery path', 'power', 'board')] + list(S21.FACTS)
    power = {'GND': ('GND', 'ground', 0.0, 'GND (JP1 1, 13)', '%s:header.JP1' % BOARD),
             '3V': ('+3V3', 'power', 3.3, 'the AP2112-3.3 output', '%s:power.regulator' % BOARD),
             'USB': ('VBUS', 'power', 5.0, '+5V from USB when connected; on battery alone it carries VBAT less a diode drop', '%s:power.usb' % BOARD),
             'BAT': ('VBAT', 'power', 0.0, 'the LiPo JST connector: a battery\'s voltage, not one rail voltage', '%s:header.JP3' % BOARD),
             'EN': ('EN', 'signal', 0.0, 'the 3.3 V regulator enable (100k pull-up to VBUS; to GND = off)', '%s:power.en' % BOARD),
             'RST': ('RESET', 'signal', 0.0, 'the reset line (the reset switch SW1 to GND)', '%s:header.JP1' % BOARD)}
    return {
        'board': BOARD, 'soc': SOC, 'soc_title': 'Microchip ATSAMD21G18A', 'vendor': 'Microchip (Atmel)', 'package': 'QFN48 (TQFN48_7MM on the board file)',
        'isa': 'ARMv6-M (Cortex-M0+)', 'cpu_clock_hz': 48000000, 'soc_source': 'board.custom.soc_samd21 (DS40001882L)',
        'logic': (3.3, 'fact %s:io.logic = 3.3 V (learn guide Pinouts: "All logic is 3.3V")' % BOARD),
        'docs': DOCS, 'facts': f, 'soc_pins': [], 'pins': pins, 'headers': headers, 'label_pin': {p['canonical']: p['canonical'] for p in pins}, 'power': power,
        'inputs': {'EN': 'the 3.3 V regulator enable input (100k pull-up to USB; tie to GND to turn the regulator off)', 'RST': 'the reset input (SW1 to GND)'},
        'electrical': dict(S21.ELECTRICAL),
        'rails': [{'net': '+3V3', 'volts': 3.3, 'max_ma': 500, 'fact': '%s:power.3v_peak' % BOARD}],
        'positions': positions, 'position_basis': 'cited: pad centres from the Eagle board file (brd @5017ef4) - Eagle\'s frame, origin bottom-left, y UP',
        'components': [{'ref': 'U$4', 'value': 'ATSAMD21G18', 'role': 'mcu', 'soc': SOC, 'fact': '%s:header.JP1' % BOARD},
                       {'ref': 'U2', 'value': 'AP2112-3.3', 'role': 'regulator', 'fact': '%s:power.regulator' % BOARD},
                       {'ref': 'LED1', 'value': 'WS2812B', 'role': 'neopixel', 'pin': 'PA06', 'fact': '%s:header.JP3' % BOARD, 'notes': 'not on a header'},
                       {'ref': 'U1', 'value': '2MB SPI flash (GD25Q16C per variant.h)', 'role': 'flash', 'fact': '%s:header.JP3' % BOARD,
                        'notes': 'PA14 MISO, PA09 SCK, PA08 MOSI, PA13 CS - none on the headers'}]
                      + [{'ref': c, 'value': c, 'role': 'connector', 'connector': c, 'fact': '%s:header.%s' % (BOARD, c)} for c in ('JP1', 'JP3')],
        'hardware': {'crystal': '32.768 kHz (X2) on PA00/PA01', 'usb_bridge_chip': 'none: native USB on PA24 / PA25 (micro-USB X3)',
                     'source': 'board.custom.board_feather_m0 (Eagle files + variant + learn guide + datasheets)',
                     'undetermined': 'the 3V rail\'s continuous current (only the 500 mA peak is stated); USB / BAT pin limits; the charger\'s exact current; the chip '
                                     'suffix (no Adafruit source prints the A of ATSAMD21G18A)',
                     'notes': 'charger U3 MCP73831 (README: 100 mA); no I2C pull-ups on SDA / SCL'},
    }


SPEC = _spec()
