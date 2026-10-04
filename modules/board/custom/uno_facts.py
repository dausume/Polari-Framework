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
M328_DOC = 'Microchip ATmega48A/PA/88A/PA/168A/PA/328/P datasheet'
M328_REV = 'DS40002061B (2020), fetched 2026-10-01, file sha256 b9b9d83cda56a95d999ea8d54fe5a540748ae9020e5e7ae19b913d384ba9320e'
M328_URL = 'https://ww1.microchip.com/downloads/aemDocuments/documents/MCU08/ProductDocuments/DataSheets/ATmega48A-PA-88A-PA-168A-PA-328-P-DS-DS40002061B.pdf'
TMP36_DOC = 'Analog Devices TMP35/TMP36/TMP37 datasheet'
TMP36_REV = 'NOT fetched (analog.com timed out from pol-core 2026-10-01); values as plan §3 states them — re-read before a real-hardware claim'
TMP36_URL = 'https://www.analog.com/media/en/technical-documentation/data-sheets/TMP35_36_37.pdf'

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
    # brd-1: the facts the plain-C firmware (board/custom/firmware/uno/main.c) uses. The ATmega328P datasheet was FETCHED and
    # read on 2026-10-01 (sha256 below); the TMP36 datasheet was NOT (analog.com timed out from pol-core) — its two
    # numbers are the ones plan §3 states and the kit's project 03 uses, said so in the revision.
    _f('usart0.ubrr_115200_u2x1', 16, 'UBRR0', M328_DOC, M328_REV, 'Table 20-7, p.199 (fosc = 16.0000 MHz, 115.2k, U2Xn = 1)', M328_URL,
       'error +2.1 %; the firmware default (USART_U2X 1) — what Optiboot and the 16U2 side use'),
    _f('usart0.ubrr_115200_u2x0', 8, 'UBRR0', M328_DOC, M328_REV, 'Table 20-7, p.199 (fosc = 16.0000 MHz, 115.2k, U2Xn = 0)', M328_URL,
       'error -3.5 %; plan §3 named this value — kept as the USART_U2X 0 knob (fine on the twin, marginal against the 16U2)'),
    _f('adc.conversion_result', 'ADC = Vin * 1024 / Vref', '', M328_DOC, M328_REV, '§24.7 ADC Conversion Result, p.256', M328_URL,
       'single-ended; the firmware reads channel 0 with REFS0 = AVcc (5 V on the UNO)'),
    _f('tmp36.scale', 10, 'mV/degC', TMP36_DOC, TMP36_REV, 'TMP36 specifications (scale factor)', TMP36_URL, 'T = (mV - 500) / 10'),
    _f('tmp36.offset', 500, 'mV', TMP36_DOC, TMP36_REV, 'TMP36 specifications (750 mV at 25 degC)', TMP36_URL, 'the kit\'s TMP36 on A0 (project 03)'),
]
