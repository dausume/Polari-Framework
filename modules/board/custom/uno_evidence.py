"""
@module board.custom.uno_evidence

fgm-2: THE NEW DOCUMENTS the UNO hardware truth cites, fetched and hashed 2026-10-15 (never typed from memory), and the DatasheetFact rows read
from them. Three documents (all three re-derivable: the sha256 is the file's):
  * Arduino UNO R3 (A000066) SCHEMATIC — 2 pages (A3), https://docs.arduino.cc/resources/schematics/A000066-schematics.pdf — the page was RENDERED and
    read (the PDF's text layer is positional, not netlist): the reset path, the 328P/16U2 serial wires, the L LED buffer, the clock part.
  * Arduino UNO R3 PRODUCT DATASHEET — 8 pages — §2.1 board thermal limits -40..85 C; §2.2 VIN 6-20 V; §3.1 board topology (U3 = ATMEGA16U2 module).
  * Microchip/Atmel ATmega8U2/16U2/32U2 datasheet (doc7799, 7799D-AVR-11/10, 310 pp.) — the U2 chip's own: 16 KB flash (Table 25-7 p.249), 512 B
    EEPROM (Table 25-8 p.249), 512 B SRAM (Features p.1), signature 0x1E9489 (Table 25-6 p.249), packages 32A TQFP / 32M1 QFN (Ordering, p.295).
THE SCHEMATIC'S REFERENCE DESIGNATORS are Arduino's (the 328P is ZU4, the 16U2 is U3 in the product datasheet's list); ours (U1/U2, board_uno.hardware)
are kept — the schematic facts say so. Anything the schematic does not state stays `undetermined`.
"""
BOARD = 'arduino-uno-r3'

SCH_DOC = 'Arduino UNO R3 (A000066) schematics'
SCH_URL = 'https://docs.arduino.cc/resources/schematics/A000066-schematics.pdf'
SCH_SHA = '2c1041200352485393108e03c5117a07d4ea03954654485526c2c56cd01f7a42'
SCH_REV = 'Rev3 schematic, fetched 2026-10-15, file sha256 %s' % SCH_SHA

PD_DOC = 'Arduino UNO R3 product datasheet (A000066)'
PD_URL = 'https://docs.arduino.cc/resources/datasheets/A000066-datasheet.pdf'
PD_SHA = '8094f8908398502e9163b863dbadb5a1804bec7210dd494417b924a1d41900b5'
PD_REV = 'product datasheet, fetched 2026-10-15, file sha256 %s' % PD_SHA

U2_DOC = 'Atmel ATmega8U2/16U2/32U2 datasheet'
U2_URL = 'https://ww1.microchip.com/downloads/en/DeviceDoc/doc7799.pdf'
U2_SHA = '182d44b3834632028e2258ee410b3ad33ee89c692695b6dc3e68cbdd08a5d03a'
U2_REV = '7799D-AVR-11/10 (doc7799), fetched 2026-10-15, file sha256 %s' % U2_SHA
U2 = 'atmega16u2'

BOX_DOC = 'Arduino Starter Kit box (A000066_K7)'
BOX_REV = 'the box, "THIS KIT INCLUDES" panel — his photos 2026-10-15, transcribed in FIRMWARE_GENERATION_MODULE_PLAN.md §7.10 (photos not committed)'
BOX_CITE = 'Arduino Starter Kit box (A000066_K7), THIS KIT INCLUDES panel'


def _f(doc, rev, url, key, value, unit, where, notes='', board=BOARD):
    return {'name': '%s:%s' % (board, key), 'board': board, 'fact_key': key, 'value': str(value), 'unit': unit, 'document': doc, 'revision': rev,
            'page_table': where, 'url': url, 'notes': notes}


def _s(key, value, where, notes=''):
    return _f(SCH_DOC, SCH_REV, SCH_URL, key, value, '', where, notes)


def facts():
    return [
        _s('schematic.dtr_reset', 'ATmega16U2 pin 13 (PD7, net DTR) -> C5 100 nF -> ATmega328P pin 1 (RESET); the solder jumper RESET-EN sits in the RESET path',
           'sheet 1, reset area (labels DTR, C5 100n, RESET-EN, RESET)',
           'a host opening the serial port pulses DTR and resets the 328P; cutting RESET-EN disables it. A 10K network element (RN1D) and a diode (D2) are also drawn on the RESET net — not analysed here'),
        _s('schematic.serial_resistors', '16U2 M8RXD / M8TXD -> 1K RN4B / RN4A -> the 328P RXD (D0) / TXD (D1) header nets IO0 / IO1', 'sheet 1, lower middle (RN4A, RN4B, M8RXD, M8TXD, IO0, IO1)',
           '1 kOhm in series: an external driver on D0/D1 contends with the 16U2 through these resistors'),
        _s('schematic.l_led', 'SCK (328P PB5, pin 19) -> LMV358 buffer U5B (non-inverting input) -> 1K RN2A -> yellow LED "L" -> GND', 'sheet 1, top middle (U5B, RN2A, L13)',
           'the L LED is driven by an op-amp buffer, not by the pin: it follows D13, and the load on D13 is the buffer input (its input current is not cited here: LMV358 datasheet not read)'),
        _s('schematic.clock', 'ATmega328P XTAL1/XTAL2 (pins 9/10) -> the part "CSTCE16M0V53-R0 16MHZ" (3-terminal symbol) with a 1M resistor (R2) across the pins', 'sheet 1, middle (CSTCE16M0V53-R0 16MHZ, R2 1M)',
           'resolves the board_uno note "crystal vs ceramic resonator not in the cited sources": the part named on the schematic is CSTCE16M0V53-R0; its own datasheet was not read, so what kind of device it is stays that part\'s statement'),
        _s('schematic.usb_bridge_part', 'ATMEGA16U2-MU(R)', 'sheet 1, lower left', 'the "-MU" ordering code is package 32M1-A (32-pad QFN) per the ATmega16U2 datasheet ordering table, p.295'),
        _f(PD_DOC, PD_REV, PD_URL, 'board.thermal_limits', '-40 to 85', 'C', '§2.1 Recommended Operating Conditions, p.6 (conservative thermal limits for the whole board)',
           'why the 85 C rows of Table 30-1 are the ones a UNO design reads'),
        _f(PD_DOC, PD_REV, PD_URL, 'board.vin_range', '6-20', 'V', '§2.2 Power Consumption, p.6 (VINMax 6 .. 20 V)'),
        _f(U2_DOC, U2_REV, U2_URL, 'memory.flash', 16384, 'bytes', 'Table 25-7 No. of Words in a Page and No. of Pages in the Flash, p.249 (ATmega16U2: 8K words = 16 Kbytes)', board=U2),
        _f(U2_DOC, U2_REV, U2_URL, 'memory.eeprom', 512, 'bytes', 'Table 25-8, p.249 (ATmega16U2: 512 bytes)', board=U2),
        _f(U2_DOC, U2_REV, U2_URL, 'memory.sram', 512, 'bytes', 'Features, p.1 ("512/512/1024 Internal SRAM" for ATmega8U2/16U2/32U2)', board=U2),
        _f(U2_DOC, U2_REV, U2_URL, 'signature', '0x1E 0x94 0x89', '', 'Table 25-6 Device and JTAG ID, p.249', board=U2),
        _f(U2_DOC, U2_REV, U2_URL, 'packages', '32A (TQFP 32-lead 7x7 mm) / 32M1-A (QFN 32-pad 5x5 mm)', '', 'Ordering Information §30.2, p.295; Features p.1', board=U2),
        _f(U2_DOC, U2_REV, U2_URL, 'usb', 'USB 2.0 full-speed device module, 4 programmable endpoints', '', 'Features, p.1', board=U2),
    ]
