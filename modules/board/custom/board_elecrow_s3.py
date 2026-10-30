"""
@module board.custom.board_elecrow_s3

THE ELECROW "EVAL BOARD FOR ESP32" (DIE01237S001) AS A BOARD SPEC (bob-5, 2026-10-30): one of the four dev boards on his home bench that had no pins. It is
the CrowPanel ESP32 E-Paper HMI 3.7-inch display (240 x 416, UC8253), PCB "ESP32 Display-3.7(E) inch" V1.0, an ESP32-S3-WROOM-1-N8R8 - identified by SKU in
three Elecrow sources (the wiki "Model: DIE01237S001", the board silk "SKU:DIE01237S", the user manual p.9); every other size has another SKU.
Read from Elecrow's Eagle schematic + board (XML, nets and pads read directly; byte-identical to the Elecrow-RD GitHub copy), cross-checked against the wiki
pin table, the silk, the Arduino examples and the factory firmware; chip facts from Espressif's ESP32-S3 datasheet v2.2 and the WROOM-1 datasheet v1.8;
the 3V3 regulator from the RY3420 datasheet. Elecrow states no licence for any of it: cited, never stored.
His bench note says the unit has a UART0 connector; the V1.0 schematic, board file and photos have none (UART0 reaches only the CH340C on USB-C) - check
the unit (recorded, not resolved).
"""
BOARD = 'elecrow-esp32-eval'
SOC = 'esp32s3'
_ZIP = 'https://www.elecrow.com/download/product/CrowPanel/E-paper/3.7-DIE01237S/CrowPanel-ESP32-Display-3.7E-Inch.zip'
DOCS = {
    'sch': ('CrowPanel ESP32 Display-3.7(E) Inch schematic (Eagle 9.6.2 XML)', 'V1.0 (zip entry 2024-10-16), sha256 ab3b491ecae88f89...; = Elecrow-RD GitHub @3ee5cbac', _ZIP),
    'brd': ('CrowPanel ESP32 Display-3.7(E) Inch board (Eagle 9.6.2 XML)', 'V1.0 (silk), zip entry 2024-09-11', _ZIP),
    'wiki': ('CrowPanel ESP32 E-Paper HMI 3.7-inch Display - Elecrow Wiki', 'no revision shown; fetched 2026-10-30',
             'https://www.elecrow.com/wiki/CrowPanel_ESP32_E-paper_3.7-inch_HMI_Display.html'),
    'examples': ('Elecrow Arduino examples for the 3.7-inch board (Examples.zip)', 'zip entries 2024-10-16; fetched 2026-10-30',
                 'https://www.elecrow.com/download/product/CrowPanel/E-paper/3.7-DIE01237S/Arduino/Examples.zip'),
    's3ds': ('Espressif ESP32-S3 Series Datasheet', 'v2.2 (revision history 2026-03-05)', 'https://www.espressif.com/sites/default/files/documentation/esp32-s3_datasheet_en.pdf'),
    'wroom': ('Espressif ESP32-S3-WROOM-1 & WROOM-1U Datasheet', 'v1.8 (2026-03-02)',
              'https://www.espressif.com/sites/default/files/documentation/esp32-s3-wroom-1_wroom-1u_datasheet_en.pdf'),
    'ry3420': ('RYCHIP RY3420 5.5V 2A 1.2MHz Synchronous Step-Down Regulator', 'no revision printed; PDF 2018-12-13 (distributor mirror)',
               'https://static.chipdip.ru/lib/402/DOC014402816.pdf'),
}

#: the 2x10 GPIO header U5, pins numbered AROUND the part like a DIP (pin 1 faces pin 20) - schematic nets -> U5 P$n, board silk (wiki pin table agrees)
HEADER = ['IO3', 'IO9', 'IO15', 'IO17', 'IO19', 'IO21', 'GND', 'GND', 'GND', 'GND', '3V3', '3V3', '3V3', '3V3', 'IO38', 'IO20', 'IO18', 'IO16', 'IO14', 'IO8']
#: per-pin notes the datasheets give for the header GPIOs
HEADER_NOTES = {3: 'STRAPPING pin (JTAG source select; floating at reset) - S3 datasheet Table 3-1 p.32', 17: 'default drive strength 10 mA (Table 2-1 note 5, p.18)',
                18: 'default drive strength 10 mA (Table 2-1 note 5, p.18)', 19: 'native USB D- (USB Serial/JTAG by default); default drive 40 mA',
                20: 'native USB D+ (USB_PU pull-up at reset); default drive 40 mA'}
#: on-board GPIOs (no header pin): function, signal, notes - schematic + the examples' EPD_SPI.h / 3.7_key.ino / 3.7_TF.ino
ONBOARD = {0: ('boot', 'BOOT', 'the BOOT button K1 (and the CH340 auto-boot transistor); STRAPPING'), 1: ('button', 'EXIT', 'EXIT key K4, 4.7k pull-up, active low'),
           2: ('button', 'MENU', 'MENU key K3, 4.7k pull-up, active low'), 4: ('button', 'ROTARY_DOWN', 'rotary K5 down, active low'),
           5: ('button', 'ROTARY_PRESS', 'rotary K5 press, active low'), 6: ('button', 'ROTARY_UP', 'rotary K5 up, active low'),
           7: ('power-switch', 'EPD_POWER', 'e-paper power enable (Q9 2N7002 switches the panel ground), active high'),
           10: ('spi', 'TF_CS', 'microSD CS, 10k pull-up'), 11: ('spi', 'EPD_MOSI', 'e-paper SDA (MOSI)'), 12: ('spi', 'EPD_SCK', 'e-paper SCL (SCK)'),
           13: ('spi', 'TF_MISO', 'microSD MISO, 10k pull-up'), 39: ('spi', 'TF_CLK', 'microSD CLK'), 40: ('spi', 'TF_MOSI', 'microSD MOSI, 10k pull-up'),
           41: ('led', 'POWER_LED', 'the red POWER LED through R16 4.7k'), 42: ('power-switch', 'TF_POWER', 'microSD power enable, active high (an example comment '
           'calls it a backlight pin; the schematic says TF power)'), 43: ('uart', 'U0TXD', 'UART0 TX to the CH340C (level-shifted)'),
           44: ('uart', 'U0RXD', 'UART0 RX from the CH340C'), 45: ('spi', 'EPD_CS', 'e-paper CS; STRAPPING (VDD_SPI select)'),
           46: ('spi', 'EPD_DC', 'e-paper D/C; STRAPPING (boot mode / ROM print)'), 47: ('gpio', 'EPD_RST', 'e-paper reset'), 48: ('gpio', 'EPD_BUSY', 'e-paper busy (input)')}


def _spec():
    pins = []
    for i, lab in enumerate(HEADER, 1):
        if lab.startswith('IO'):
            n = int(lab[2:])
            pins.append({'canonical': 'GPIO%d' % n, 'number': n, 'soc_pin': 'GPIO%d' % n, 'function': 'usb' if n in (19, 20) else 'gpio',
                         'facts': ['%s:header.U5' % BOARD], 'origin': 'read:schematic net %s -> U5 P$%d; board silk %s' % (lab, i, lab), 'notes': HEADER_NOTES.get(n, '')})
    for n, (fn, sig, why) in sorted(ONBOARD.items()):
        pins.append({'canonical': 'GPIO%d' % n, 'number': n, 'soc_pin': 'GPIO%d' % n, 'function': fn, 'signal': sig, 'facts': ['%s:onboard' % BOARD],
                     'origin': 'read:schematic (on-board, no header pin)', 'notes': why})
    label_pin = {lab: 'GPIO%s' % lab[2:] for lab in HEADER if lab.startswith('IO')}
    f = [('header.U5', ', '.join('%d %s' % (i, lab) for i, lab in enumerate(HEADER, 1)), '', 'schematic U5 (2x10, deviceset 2x10PIN_2.54_WOTIE) + board silk',
          'pins numbered around the part (pin 1 faces 20); 12 GPIO + 4 GND + 4 3V3, no 5 V pin; the wiki pin table and the GPIO example agree', 'sch', 'board'),
         ('onboard', '; '.join('GPIO%d %s' % (n, s) for n, (_f, s, _w) in sorted(ONBOARD.items())), '', 'schematic; EPD_SPI.h l.7-12, 3.7_key.ino, 3.7_TF.ino',
          'the GPIOs the board uses itself (e-paper, keys, microSD, LED, UART0)', 'sch', 'board'),
         ('power.3v3', 3.318, 'V', 'RY3420 p.7 Setting the Output Voltage; schematic R13 45.3k / R14 10k',
          'DERIVED: 0.600 V x (45.3k + 10k) / 10k = 3.318 V typ (3.252-3.384 V over VFB 0.588-0.612 V; resistor tolerance not stated)', 'ry3420', 'board'),
         ('power.regulator', 'U2 RY3420 synchronous buck, 2 A continuous, VIN 2.5-5.5 V', '', 'p.1 Features', 'what the header 3V3 shares with the board\'s own loads '
          '(e-paper, microSD, the module) is not stated', 'ry3420', 'board'),
         ('power.vdd', 3.3, 'V', 'Table 5-2 Recommended Operating Conditions, p.64', 'VDDA / VDD3P3 / VDD3P3_RTC / VDD3P3_CPU: 3.0 min, 3.3 typ, 3.6 max V', 's3ds', 'soc'),
         ('io.ioh_drive3', 40, 'mA', 'Table 5-4 DC Characteristics (3.3 V, 25 C), p.65', 'IOH TYPICAL (no min / max printed) at VDD 3.3 V, VOH >= 2.64 V, PAD_DRIVER = 3 - '
          'not an absolute maximum; the DEFAULT drive is 20 mA (10 mA on GPIO17/18, 40 mA on GPIO19/20; Table 2-1 note 5, p.18)', 's3ds', 'soc'),
         ('io.iol_drive3', 28, 'mA', 'Table 5-4, p.65', 'IOL TYPICAL at VDD 3.3 V, VOL 0.495 V, PAD_DRIVER = 3', 's3ds', 'soc'),
         ('strapping', 'GPIO0, GPIO3, GPIO45, GPIO46', '', 'Section 3, Table 3-1, p.32', 'GPIO3 is header pin 1; GPIO45 / GPIO46 drive the e-paper CS / DC', 's3ds', 'soc'),
         ('psram.pins', 'GPIO35, GPIO36, GPIO37 (octal PSRAM on N8R8)', '', 'WROOM-1 Table 3-1 note b, p.12', 'not available for other use; none is on the header', 'wroom', 'soc')]
    soc = [{'pin': p['soc_pin'], 'functions': [], 'default': 'GPIO', 'fact': '%s:%s' % (BOARD, 'header.U5' if p['canonical'] in label_pin.values() else 'onboard'),
            'notes': 'the IO MUX functions of the S3 are not read here (only the GPIOs this board names)'} for p in pins]
    return {
        'board': BOARD, 'soc': SOC, 'soc_title': 'Espressif ESP32-S3 (ESP32-S3R8 in an ESP32-S3-WROOM-1-N8R8)', 'vendor': 'Espressif',
        'package': 'QFN56 in the WROOM-1 module (N8R8: 8 MB quad flash + 8 MB octal PSRAM)', 'isa': 'Xtensa LX7 (dual core)', 'cpu_clock_hz': 240000000,
        'soc_source': 'ESP32-S3 Series Datasheet v2.2 + WROOM-1 datasheet v1.8 (only the facts the board uses)', 'vendor_target': 'IDF_TARGET=esp32s3',
        'soc_undetermined': 'the IO MUX function table per GPIO is not read; the 240 MHz clock is the chip read over USB 2026-10-24 (esptool), not a datasheet row here',
        'logic': (3.3, 'fact %s:power.vdd = 3.3 V typical (ESP32-S3 datasheet v2.2 Table 5-2, p.64; 3.0-3.6 V recommended)' % SOC),
        'docs': DOCS, 'facts': f, 'soc_pins': soc, 'pins': pins, 'label_pin': label_pin,
        'headers': [{'connector': 'U5', 'labels': HEADER, 'fact': '%s:header.U5' % BOARD, 'footprint': '2x10, 2.54 mm, SMD right-angle (pads 5.00 mm row to row)',
                     'order_note': 'pins numbered around the part like a DIP: 1-10 one row, 11-20 back along the other (pin 1 faces 20)',
                     'notes': 'which pad row is the upper row at the case opening is undetermined (an SMD right-angle header)'}],
        'power': {'GND': ('GND', 'ground', 0.0, 'GND (U5 7-10)', '%s:header.U5' % BOARD),
                  '3V3': ('3V3', 'power', 3.318, 'the RY3420 buck output, 3.318 V derived from its feedback divider', '%s:power.3v3' % BOARD)},
        'electrical': {'max_ma': 40, 'fact': '%s:io.ioh_drive3' % SOC, 'kind': 'typical IOH at PAD_DRIVER 3 (not an absolute maximum; the default drive is 20 mA)'},
        'rails': [{'net': '3V3', 'volts': 3.318, 'fact': '%s:power.3v3' % BOARD}],
        'position_basis': 'undetermined: the header is a right-angle SMD part and which pad row faces up at the case opening is not stated',
        'components': [{'ref': 'U3', 'value': 'ESP32-S3-WROOM-1-N8R8', 'role': 'mcu', 'soc': SOC, 'fact': '%s:header.U5' % BOARD},
                       {'ref': 'U2', 'value': 'RY3420', 'role': 'regulator', 'fact': '%s:power.regulator' % BOARD},
                       {'ref': 'U1', 'value': 'CH340C', 'role': 'usb-uart', 'fact': '%s:onboard' % BOARD},
                       {'ref': 'U4', 'value': '3.7" e-paper 240x416 (UC8253)', 'role': 'display', 'fact': '%s:onboard' % BOARD},
                       {'ref': 'U5', 'value': 'U5', 'role': 'connector', 'connector': 'U5', 'fact': '%s:header.U5' % BOARD}],
        'hardware': {'crystal': '40 MHz (read over USB by esptool 2026-10-24)', 'usb_bridge_chip': 'CH340C (U1) on UART0 via level shifters; USB-C',
                     'source': 'board.custom.board_elecrow_s3 (Elecrow Eagle files V1.0 + wiki + examples; Espressif + RYCHIP datasheets)',
                     'undetermined': 'the 3V3 current left for the header; the charger\'s exact part ("4054" symbol, no value) and current; whether the unit in hand is '
                                     'PCB V1.0; the UART0 connector his note records (absent from V1.0)',
                     'notes': 'battery: SH1.0 2-pin (pad 1 = B+); VBUS -> D2 -> VIN, BAT -> PMOS Q3 -> VIN (off while USB is present)'},
    }


SPEC = _spec()
