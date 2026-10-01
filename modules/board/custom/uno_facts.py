"""
@module board.custom.uno_facts

THE UNO's DATASHEET FACTS (plan §3, §8a derive-or-cite) — the only DatasheetFact rows brd-0 seeds. The boards.txt
facts were READ on 2026-10-01 from the file the plan cites, at the commit master pointed to that day
(11b9130371e8447920edb65a75706a6c951e51fc, file sha256 e49283dc…0a5d); each row cites its line. The remaining rows cite
the pages the plan cites (not re-fetched this session — the revision says so).
"""
BOARD = 'arduino-uno-r3'
BOARDS_TXT_SHA = '11b9130371e8447920edb65a75706a6c951e51fc'
BOARDS_TXT = 'https://github.com/arduino/ArduinoCore-avr/blob/%s/boards.txt' % BOARDS_TXT_SHA
BOARDS_TXT_REV = 'ArduinoCore-avr @ %s (master on 2026-10-01; file sha256 e49283dc7a276291e24e91d04b883ea4e884ea2375ed80ede0d69cbf25d40a5d)' % BOARDS_TXT_SHA
UNO_DOC = 'https://docs.arduino.cc/hardware/uno-rev3/'
DOUBLE_DOC = 'https://docs.arduino.cc/language-reference/en/variables/data-types/double'
OPTIBOOT = 'https://github.com/Optiboot/optiboot'

#: the five upload VID:PIDs, as boards.txt lists them (uno.vid.N / uno.pid.N, lines 63-72)
UNO_USB_IDS = ['2341:0043', '2341:0001', '2a03:0043', '2341:0243', '2341:006a']


def _f(key, value, unit, document, revision, where, url, notes=''):
    return {'name': '%s:%s' % (BOARD, key), 'board': BOARD, 'fact_key': key, 'value': str(value), 'unit': unit,
            'document': document, 'revision': revision, 'page_table': where, 'url': url, 'notes': notes}


def _bt(key, value, unit, line, notes=''):
    return _f(key, value, unit, 'ArduinoCore-avr boards.txt (uno entry)', BOARDS_TXT_REV, 'line %s' % line, '%s#L%s' % (BOARDS_TXT, line), notes)


SEED_UNO_FACTS = [
    _bt('upload.maximum_size', 32256, 'bytes', 89, 'flash for the application = 32768 minus the 512-byte Optiboot; a build past it is refused'),
    _bt('upload.maximum_data_size', 2048, 'bytes', 90, 'SRAM; a build past it is refused'),
    _bt('upload.speed', 115200, 'baud', 91, 'the Optiboot upload rate (avrdude -b)'),
    _bt('upload.protocol', 'arduino', '', 88, 'avrdude -c arduino'),
    _bt('upload.tool', 'avrdude', '', 85),
    _bt('bootloader.file', 'optiboot/optiboot_atmega328.hex', '', 100),
    _bt('build.mcu', 'atmega328p', '', 102, 'avr-gcc -mmcu / avrdude -p'),
    _bt('build.f_cpu', '16000000L', 'Hz', 103, 'F_CPU'),
] + [_bt('usb_id.%d' % i, vp, 'vid:pid', 63 + 2 * i, 'uno.vid.%d / uno.pid.%d' % (i, i)) for i, vp in enumerate(UNO_USB_IDS)] + [
    _f('flash', 32, 'KB', 'Arduino UNO R3 product page', 'as cited by plan §3 (not re-fetched 2026-10-01)', 'tech specs', UNO_DOC),
    _f('sram', 2, 'KB', 'Arduino UNO R3 product page', 'as cited by plan §3 (not re-fetched 2026-10-01)', 'tech specs', UNO_DOC),
    _f('eeprom', 1, 'KB', 'Arduino UNO R3 product page', 'as cited by plan §3 (not re-fetched 2026-10-01)', 'tech specs', UNO_DOC),
    _f('usb_serial_chip', 'ATmega16U2', '', 'Arduino UNO R3 product page', 'as cited by plan §3 (not re-fetched 2026-10-01)', 'tech specs', UNO_DOC,
       'opening the port resets the board via DTR'),
    _f('sizeof_double', 4, 'bytes', 'Arduino language reference: double', 'as cited by plan §1 (not re-fetched 2026-10-01)', 'data types / double', DOUBLE_DOC,
       'why c_twin needs its AVR mode (target=avr)'),
    _f('optiboot_size', 512, 'bytes', 'Optiboot README', 'as cited by plan §3 (not re-fetched 2026-10-01)', 'README', OPTIBOOT),
]
