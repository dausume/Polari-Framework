"""
@module board.custom.board_c3

THE ESP32-C3 AS A BOARD OBJECT (brd-bo, PCB_FROM_SCRATCH_PLAN §2b): the board pins are INGESTED from Zephyr's upstream
`esp32c3_devkitm` board directory (stored verbatim under custom/upstream/zephyr-v4.4.2/, Apache-2.0, SOURCE.json carries every
file's sha256) — never retyped. Three layers sit on the ingested rows, each said:

  ingested   board.custom.ingest_zephyr.upstream(): UART0 (GPIO21 TX / GPIO20 RX, the console), SPI2 (GPIO2/6/7/10), I2C0
             (GPIO1/3), the user button GPIO9 (alias sw0), the SoC's clock / memories / flash size / peripheral nodes
  cited      the ESP32-C3 datasheet v2.4 (fetched 2026-10-03, sha256 833fc000…f968): every SocPin's IO MUX functions (Table 2-4,
             pp.19–20) + analog functions (Table 2-6, p.21) — and the USB Serial/JTAG's GPIO18 (USB_D-) / GPIO19 (USB_D+), which
             the devicetree cannot say (a fixed function, no pinctrl)
  polari     the sc-3 template's own assignment: UART1 TX on GPIO4 = the FreeRTOS trace (main/polari_c3.h POLARI_TRACE_TX_GPIO),
             and the C identifiers of the frame UART's pins (the template uses UART0's IO MUX default pins)

The reference board is the DevKitM (Zephyr's); which C3 board he buys is undetermined (register: "no C3 on hand"). Its dts says
of `usb_serial`: "requires resoldering of resistors on the board" — on that devkit the USB connector reaches the C3 through a
USB-UART bridge on UART0 by default; recorded on the BoardHardware row, not smoothed over.
"""
import json
import os

from board.custom import ingest_zephyr

BOARD = 'esp32-c3'
SOC = 'esp32c3'
TAG = 'v4.4.2'
HERE = os.path.dirname(os.path.abspath(__file__))
UPSTREAM = os.path.join(HERE, 'upstream', 'zephyr-%s' % TAG)
BOARD_DIR = 'boards/espressif/esp32c3_devkitm'
DS_DOC = 'Espressif ESP32-C3 Series Datasheet'
DS_REV = 'v2.4 — fetched 2026-10-03, file sha256 833fc000b4b3c3d39c496fcbd597fed5806956503ce7390b19cc8ae82f19f968'
DS_URL = 'https://www.espressif.com/sites/default/files/documentation/esp32-c3_datasheet_en.pdf'
#: GPIOn → (QFN32 pin, IO MUX F0, F2, analog functions) — Table 2-4 pp.19–20, Table 2-6 p.21 (F1 is GPIOn for every pin)
PINS = {0: ('4', 'GPIO0', '', ['XTAL_32K_P', 'ADC1_CH0']), 1: ('5', 'GPIO1', '', ['XTAL_32K_N', 'ADC1_CH1']), 2: ('6', 'GPIO2', 'FSPIQ', ['ADC1_CH2']),
        3: ('8', 'GPIO3', '', ['ADC1_CH3']), 4: ('9', 'MTMS', 'FSPIHD', ['ADC1_CH4']), 5: ('10', 'MTDI', 'FSPIWP', ['ADC2_CH0']),
        6: ('12', 'MTCK', 'FSPICLK', []), 7: ('13', 'MTDO', 'FSPID', []), 8: ('14', 'GPIO8', '', []), 9: ('15', 'GPIO9', '', []),
        10: ('16', 'GPIO10', 'FSPICS0', []), 11: ('18', 'GPIO11', '', []), 12: ('19', 'SPIHD', '', []), 13: ('20', 'SPIWP', '', []),
        14: ('21', 'SPICS0', '', []), 15: ('22', 'SPICLK', '', []), 16: ('23', 'SPID', '', []), 17: ('24', 'SPIQ', '', []),
        18: ('25', 'GPIO18', '', ['USB_D-']), 19: ('26', 'GPIO19', '', ['USB_D+']), 20: ('27', 'U0RXD', '', []), 21: ('28', 'U0TXD', '', [])}
#: the polari layer: (canonical) → fields set on the row (a new row when the pin was not ingested)
POLARI = {'GPIO4': {'net': 'UART1_TX', 'function': 'uart', 'peripheral': 'UART1', 'signal': 'UART1_TX', 'firmware_symbol': 'POLARI_TRACE_TX_GPIO',
                    'origin': 'polari:sc-3 template — main/polari_c3.h POLARI_TRACE_TX_GPIO 4 (UART1 TX = the FreeRTOS trace on silicon)'},
          'GPIO21': {'firmware_symbol': 'POLARI_FRAME_TX_GPIO'}, 'GPIO20': {'firmware_symbol': 'POLARI_FRAME_RX_GPIO'}}
CITED_USB = {'GPIO18': ('USB_D-', 'USB_D-'), 'GPIO19': ('USB_D+', 'USB_D+')}
#: c3-pv (2026-10-29): THE DEVKITM-1 HEADERS, from the user guide's Header Block tables (J1, J3; "the numbering is the same as in the ESP32-C3-DevKitM-1 Schematic").
#: The guide breaks out GPIO0-10, 18-21 and no flash pad ("All available GPIO pins (except for the SPI bus for flash) are broken out"). A label -> its BoardPin
#: (GPIOn) or its power net; RST = CHIP_PU (the chip enable).
UG_DOC = 'Espressif ESP32-C3-DevKitM-1 User Guide'
UG_REV = 'esp-dev-kits latest, read 2026-10-29 (the guide lists no previous versions)'
UG_URL = 'https://docs.espressif.com/projects/esp-dev-kits/en/latest/esp32c3/esp32-c3-devkitm-1/user_guide.html'
HEADERS = {'J1': ['GND', '3V3', '3V3', 'IO2', 'IO3', 'GND', 'RST', 'GND', 'IO0', 'IO1', 'IO10', 'GND', '5V', '5V', 'GND'],
           'J3': ['GND', 'TX', 'RX', 'GND', 'IO9', 'IO8', 'GND', 'IO7', 'IO6', 'IO5', 'IO4', 'GND', 'IO18', 'IO19', 'GND']}
HEADER_GPIO = {'TX': 'GPIO21', 'RX': 'GPIO20'}   # the guide's Function column: TX = GPIO21, U0TXD; RX = GPIO20, U0RXD; IOn = GPIOn
#: kxc-0 (2026-10-30): the names in KiCad 10's own libraries (kicad-symbols 10.0.7 on econ-core, read with kicad-cli 10.0.6). MCU_Espressif:ESP32-C3's
#: pin numbers = our SocPin package pins (all 15 header GPIOs); RF_Module:ESP32-C3-DevKitM-1 = the whole devkit as one part, its pins 1-15 = J1 in order
#: and 16-30 = J3 reversed (KiCad pin = 31 - J3 pin) - the part a breadboard circuit uses when it carries the devkit.
KICAD_LIB_DOC = 'KiCad 10 symbol library (kicad-symbols 10.0.7)'
KICAD_LIB_REV = 'MCU_Espressif.kicad_sym sha256 2d1d0a92f834237371a21faa57a762afd43e185f183d80c35f71966499a4e27b; RF_Module.kicad_sym sha256 5caaa848e888e9f5491edc765fef0e2eee53c4fe5aa4fe1520c01e4b0f840f2b'
KICAD_LIB_URL = 'https://gitlab.com/kicad/libraries/kicad-symbols'
KICAD_CHIP_FOOTPRINT = 'Package_DFN_QFN:QFN-32-1EP_5x5mm_P0.5mm_EP3.7x3.7mm'   # the footprint field on KiCad's ESP32-C3 symbol
KICAD_HEADER_FOOTPRINT = 'Connector_PinHeader_2.54mm:PinHeader_1x15_P2.54mm_Vertical'
KICAD_DEVKIT = ('RF_Module', 'ESP32-C3-DevKitM-1', 'RF_Module:ESP32-C3-DevKitM-1')   # (lib, part, footprint)


def kicad_devkit_pin(conn, number):
    """The pin number on KiCad's ESP32-C3-DevKitM-1 symbol for header pin (J1|J3, 1-15)."""
    return number if conn == 'J1' else 2 * len(HEADERS['J3']) + 1 - number
#: the power labels -> (net, class, volts, why). 3V3 / 5V are the guide's own words ("3.3 V power supply", "5 V power supply"); RST is an input, CHIP_PU
POWER = {'GND': ('GND', 'ground', 0.0, 'Ground'), '3V3': ('3V3', 'power', 3.3, '3.3 V power supply'), '5V': ('5V', 'power', 5.0, '5 V power supply'),
         'RST': ('CHIP_PU', 'signal', 0.0, 'CHIP_PU (the chip enable; the board\'s Reset button SW2)')}
#: header GPIOs the Zephyr devicetree does not use: (silk, why) - each gets a BoardPin row so its header pin has a board pin to name
DEVKIT_PINS = {'GPIO0': ('IO0', ''), 'GPIO5': ('IO5', ''), 'GPIO8': ('IO8', 'also the RGB LED')}


def header_gpio(label):
    return HEADER_GPIO.get(label) or ('GPIO%s' % label[2:] if label.startswith('IO') else '')


def header_of():
    """{GPIOn: 'J1:9'} - the first header pin each GPIO sits on."""
    out = {}
    for conn, labels in HEADERS.items():
        for i, lab in enumerate(labels, 1):
            g = header_gpio(lab)
            if g:
                out.setdefault(g, '%s:%d' % (conn, i))
    return out
_CACHE = {}


def ingested():
    if 'r' not in _CACHE:
        _CACHE['r'] = ingest_zephyr.upstream(UPSTREAM, BOARD_DIR, BOARD, TAG)
    return _CACHE['r']


def _f(key, value, unit, where, notes='', doc=DS_DOC, rev=DS_REV, url=DS_URL, board=SOC):
    return {'name': '%s:%s' % (board, key), 'board': board, 'fact_key': key, 'value': str(value), 'unit': unit, 'document': doc,
            'revision': rev, 'page_table': where, 'url': url, 'notes': notes}


def _functions(n):
    """F0, F1 (= GPIOn), F2, then the analog functions — datasheet order, each once."""
    _, f0, f2, analog = PINS[n]
    out = []
    for f in [f0, 'GPIO%d' % n, f2] + analog:
        if f and f not in out:
            out.append(f)
    return out


def facts():
    out = [_f('pin.GPIO%d' % n, 'QFN32 pin %s; %s' % (PINS[n][0], '/'.join(_functions(n))), '',
              'Table 2-4 IO MUX Pin Functions, pp.19-20' + ('; Table 2-6 Analog Functions, p.21' if PINS[n][3] else '')) for n in sorted(PINS)]
    r = ingested()
    zdoc, zrev = 'Zephyr RTOS (Apache-2.0)', '%s (commit dccb0959…ce90), stored under board/custom/upstream/zephyr-%s' % (TAG, TAG)
    zurl = 'https://github.com/zephyrproject-rtos/zephyr/tree/%s/' % TAG
    clk, where = r['soc']['cpu_clock_hz']
    out.append(_f('cpu_clock_hz', clk, 'Hz', where, 'cpu0 clock-frequency', zdoc, zrev, zurl + where.split(':')[0]))
    for m in r['memory']:
        out.append(_f('memory.%s' % m['region'], '%s +%s' % (m['start'], m['size']), 'bytes', m['cite'], '', zdoc, zrev, zurl + m['cite'].split(':')[0]))
    ng, where = r['soc']['ngpios']
    out.append(_f('gpio.ngpios', ng, 'pins', where, 'the GPIO controller counts 0..25; the QFN32 table bonds GPIO0..21 (22 SocPin rows)', zdoc, zrev, zurl + where.split(':')[0]))
    out.append(_f('usb_serial_jtag.pins', 'GPIO18 USB_D-, GPIO19 USB_D+', '', 'Table 2-6 Analog Functions, p.21; §2.3.3 (USB pins default to the USB Serial/JTAG controller)'))
    # 2026-10-29 (the C3 light design's electrical check): the chip's own numbers, read from the same datasheet file (sha256 re-verified)
    out.append(_f('power.vdd', 3.3, 'V', 'Table 5-2 Recommended Operating Conditions, p.54', 'VDDA / VDD3P3 / VDD3P3_RTC / VDD3P3_CPU: min 3.0, typ 3.3, max 3.6 V - the typical value is '
                  'the logic level the electrical check uses (one chip, one IO supply class)'))
    out.append(_f('io.ioh_drive3', 40, 'mA', 'Table 5-4 DC Characteristics (3.3 V, 25 °C), p.55', 'IOH high-level source current, TYPICAL (no min / max printed), at VDD = 3.3 V, '
                  'VOH >= 2.64 V, PAD_DRIVER = 3 - a typical drive figure, NOT an absolute maximum rating'))
    out.append(_f('io.iol_drive3', 28, 'mA', 'Table 5-4 DC Characteristics (3.3 V, 25 °C), p.55', 'IOL low-level sink current, TYPICAL, at VDD = 3.3 V, VOL = 0.495 V, PAD_DRIVER = 3'))
    out += header_facts()
    for f in r['files']:
        out.append(_f('zephyr.%s' % os.path.basename(f['path']), f['sha256'], 'sha256', f['path'], 'ingested verbatim', zdoc, zrev, zurl + f['path'], board=BOARD))
    return out


def soc_pins():
    return [{'name': '%s:GPIO%d' % (SOC, n), 'soc': SOC, 'pin': 'GPIO%d' % n, 'port': 'GPIO', 'bit': n, 'package_pin': PINS[n][0],
             'functions_json': json.dumps(_functions(n)), 'default_function': PINS[n][1], 'fact': '%s:pin.GPIO%d' % (SOC, n),
             'notes': 'default = IO MUX F0 (the PDF\'s bold default marks were not readable from the text extraction)'
             + ('; the in-package flash pad on SPI0/1 (datasheet Table 2-12 p.29; ESP32-C3-MINI-1 datasheet p.4 note 4) - reserved, see lifecycle_c3 (which chip variant is on his board is undetermined)' if 12 <= n <= 17 else '')}
            for n in sorted(PINS)]


def soc_definition():
    r = ingested()
    k = lambda key: '%s:%s' % (SOC, key)  # noqa: E731
    return {'name': SOC, 'title': 'Espressif ESP32-C3', 'vendor': 'Espressif', 'package': 'QFN32 (in the ESP32-C3-MINI-1 N4 module — Zephyr SOC_ESP32C3_MINI_N4)',
            'isa': 'RV32IMC', 'cpu_clock_hz': r['soc']['cpu_clock_hz'][0],
            'memory_map_json': json.dumps([{'region': m['region'], 'start': m['start'], 'size': m['size'], 'fact': k('memory.%s' % m['region'])} for m in r['memory']]),
            'peripherals_json': json.dumps([{'name': p['name'], 'compatible': p['compatible'], 'reg': p['reg'], 'status_soc_or_board': p['status'], 'cite': p['cite']}
                                            for p in r['peripherals']]),
            'clocks_json': json.dumps([{'name': 'cpu0', 'hz': r['soc']['cpu_clock_hz'][0], 'fact': k('cpu_clock_hz')}]),
            'pin_count': len(PINS), 'facts_json': json.dumps([f['name'] for f in facts() if f['board'] == SOC]),
            'source': 'zephyr-ingest:%s (esp32c3_common.dtsi, esp32c3_mini_n4.dtsi) + %s %s' % (TAG, DS_DOC, DS_REV.split(' —')[0]),
            'zephyr_soc': ingested()['identity']['socs'][0], 'vendor_target': 'IDF_TARGET=esp32c3',
            'undetermined': 'the datasheet\'s 400 KB SRAM total vs the dtsi\'s sram0 16 KB + sram1 384 KB (= 400 KB, consistent) is not re-derived per region; '
                            'the GPIO count differs by source (controller 26, QFN32 bonded 22)', 'notes': ''}


def board_pins():
    r = ingested()
    rows = {p['canonical']: dict(p) for p in r['pins']}
    for c, (net, sig) in CITED_USB.items():
        rows[c] = {'name': '%s:%s' % (BOARD, c), 'board': BOARD, 'canonical': c, 'number': int(c[4:]), 'soc_pin': c, 'net': net, 'connector_pin': '',
                   'function': 'usb', 'peripheral': 'USB_SERIAL', 'signal': '', 'firmware_symbol': '', 'alias': '', 'electrical_json': '{}',
                   'facts_json': json.dumps(['%s:usb_serial_jtag.pins' % SOC, '%s:pin.%s' % (SOC, c)]),
                   'origin': 'cited:%s Table 2-6 p.21 (the dts enables usb_serial but cannot name its pins: no pinctrl)' % DS_DOC,
                   'undetermined': 'not carried by the Zephyr view (a fixed function has no pinctrl)', 'notes': ''}
    for c, fields in POLARI.items():
        if c not in rows:
            rows[c] = {'name': '%s:%s' % (BOARD, c), 'board': BOARD, 'canonical': c, 'number': int(c[4:]), 'soc_pin': c, 'net': '', 'connector_pin': '',
                       'function': 'gpio', 'peripheral': '', 'signal': '', 'firmware_symbol': '', 'alias': '', 'electrical_json': '{}',
                       'facts_json': '[]', 'origin': '', 'undetermined': '', 'notes': ''}
        rows[c].update(fields)
        if 'origin' not in fields:
            rows[c]['notes'] = (rows[c].get('notes', '') + ' C identifier from the polari layer (sc-3 template)').strip()
    where = header_of()
    for c, (silk, why) in DEVKIT_PINS.items():
        if c not in rows:
            rows[c] = {'name': '%s:%s' % (BOARD, c), 'board': BOARD, 'canonical': c, 'number': int(c[4:]), 'soc_pin': c, 'net': silk, 'connector_pin': '',
                       'function': 'gpio', 'peripheral': '', 'signal': '', 'firmware_symbol': '', 'alias': '', 'electrical_json': '{}',
                       'facts_json': json.dumps(['%s:devkit.header.%s' % (BOARD, where[c].split(':')[0])]),
                       'origin': 'cited:ESP32-C3-DevKitM-1 user guide, Header Block (J1/J3): %s = %s pin %s' % (silk, *where[c].split(':')), 'undetermined': '', 'notes': why}
    for c, row in rows.items():
        if c in where:
            row['connector_pin'] = where[c]
            row['facts_json'] = json.dumps(sorted(set(json.loads(row['facts_json'] or '[]')) | {'%s:devkit.header.%s' % (BOARD, where[c].split(':')[0])}))
    for c, row in rows.items():
        row['facts_json'] = json.dumps(sorted(set(json.loads(row['facts_json'] or '[]')) | {'%s:pin.%s' % (SOC, c)}))
        if row.get('function') != 'usb' and row.get('electrical_json', '{}') == '{}':
            # the chip's TYPICAL source current at drive strength 3 (datasheet Table 5-4 p.55) - the electrical check names it as typical, not a maximum
            row['electrical_json'] = json.dumps({'max_ma': 40, 'fact': '%s:io.ioh_drive3' % SOC, 'kind': 'typical IOH at PAD_DRIVER 3 (not an absolute maximum)'}, sort_keys=True)
    return [rows[c] for c in sorted(rows, key=lambda c: int(c[4:]))]


def nets():
    out = [{'name': '%s:%s' % (BOARD, p['net']), 'board': BOARD, 'net': p['net'], 'net_class': 'signal', 'volts': 0.0, 'circuit_net': '',
            'fact': '', 'notes': 'derived: the pinctrl macro stem (no net names in a devicetree)' if p['signal'] else ''} for p in board_pins()]
    for net, cls, volts, why in sorted(set(POWER.values())):
        out.append({'name': '%s:%s' % (BOARD, net), 'board': BOARD, 'net': net, 'net_class': cls, 'volts': volts, 'circuit_net': '',
                    'fact': '%s:devkit.header.J1' % BOARD, 'notes': 'the header label\'s function in the user guide: %s' % why})
    return out


def header_facts():
    return [_f('devkit.header.%s' % conn, ', '.join('%d %s' % (i, lab) for i, lab in enumerate(labels, 1)), '', 'Header Block, table %s (No. / Name / Function)' % conn,
               'TX = GPIO21 (U0TXD), RX = GPIO20 (U0RXD), IOn = GPIOn, RST = CHIP_PU; GPIO2 / GPIO8 / GPIO9 are marked strapping pins', UG_DOC, UG_REV, UG_URL, board=BOARD)
            for conn, labels in sorted(HEADERS.items())] + [
        _f('devkit.dimensions', '25.40 x 38.91; J1-J3 22.86; pitch 2.54', 'mm', 'the dimensions drawing (one page)',
           'outline width x length, the two header rows\' pin-centre spacing and the pin pitch - the only four numbers the drawing gives', 'Espressif ESP32-C3-DevKitM-1 dimensions drawing',
           'V1 20200915AA, sha256 284d7b4060098e252feafac8a412902b7c51d116b5df49111f4489fc84c92d92', 'https://dl.espressif.com/dl/schematics/DIMENSION_ESP32-C3-DEVKITM-1_V1_20200915AA.pdf',
           board=BOARD),
        _f('devkit.schematic', 'GPIO8 RGB LED (R17) + R20 pull-up; GPIO9 Boot SW1 + Q2; CHIP_PU Reset SW2 + R5/C6 + Q1; U0TXD/U0RXD -> CP2102N (R22/R21); GPIO18/19 USB links NC',
           '', 'sheet 2 (rendered, read 2026-10-29)', 'the parts on the C3\'s lines besides the headers (board.custom.exposure_e2_c3.PATHS)', 'Espressif ESP32-C3-DevKitM-1 schematic',
           'V1.0, sha256 d2ac6d649cbea3ce4b2295a261f78823bf61e536f69fe4bee2b6e4142bd86542', 'https://dl.espressif.com/dl/schematics/SCH_ESP32-C3-DEVKITM-1_V1_20200915A.pdf', board=BOARD),
        _f('kicad.symbols', 'MCU_Espressif:ESP32-C3 (%s); %s (pins 1-15 = J1, 16-30 = J3 reversed)' % (KICAD_CHIP_FOOTPRINT, KICAD_DEVKIT[2]), '',
           'the two .kicad_sym files (pin numbers, names, footprint fields)', 'KiCad\'s parts for the chip and for the whole devkit; the chip symbol names some pins by '
           'their primary function (9 MTMS = GPIO4, 27 U0RXD = GPIO20) - the importer goes by pin number', KICAD_LIB_DOC, KICAD_LIB_REV, KICAD_LIB_URL, board=BOARD)]


def connectors():
    """(Connector rows, ConnectorPin rows) of J1 and J3 - the user guide's Header Block, each pin naming its BoardPin (a GPIO) or its power net."""
    bp = {p['canonical']: p for p in board_pins()}
    conns, pins = [], []
    for conn, labels in sorted(HEADERS.items()):
        conns.append({'name': '%s:%s' % (BOARD, conn), 'board': BOARD, 'connector': conn, 'ref': conn, 'kind': 'header', 'pin_count': len(labels),
                      'footprint': '%s (the schematic\'s own name: CON15X1_2P54)' % KICAD_HEADER_FOOTPRINT,'order_note': 'pin 1 = GND at the antenna end, pin 15 at the micro-USB end (the dimensions drawing)',
                      'fact': '%s:devkit.header.%s' % (BOARD, conn), 'notes': 'J1 = the left row, J3 = the right row, front view'})
        for i, lab in enumerate(labels, 1):
            g = header_gpio(lab)
            net = bp[g]['net'] if g in bp else POWER[lab][0]
            pins.append({'name': '%s:%s:%d' % (BOARD, conn, i), 'board': BOARD, 'connector': conn, 'number': i, 'label': lab, 'net': net,
                         'board_pin': g if g in bp else '', 'fact': '%s:devkit.header.%s' % (BOARD, conn), 'notes': ''})
    return conns, pins


def hardware(usb_ids_json):
    r = ingested()
    return {'name': BOARD, 'board': BOARD,
            'components_json': json.dumps([
                {'ref': 'U1', 'value': 'ESP32-C3', 'lib': 'MCU_Espressif', 'part': 'ESP32-C3', 'footprint': KICAD_CHIP_FOOTPRINT, 'role': 'mcu', 'soc': SOC,
                 'fact': '%s:kicad.symbols' % BOARD,
                 'undetermined': 'the ESP32-C3-MINI-1 module between the chip and the headers: KiCad 10\'s RF_Module library has no MINI-1 symbol; '
                                 'pin numbers are the chip\'s QFN32 (Table 2-4), which KiCad\'s ESP32-C3 symbol shares'},
                {'ref': 'SW1', 'value': 'User SW1', 'lib': '', 'part': '', 'footprint': '', 'role': 'button', 'pin': 'GPIO9',
                 'fact': '%s:zephyr.esp32c3_devkitm.dts' % BOARD}]
                + [{'ref': c, 'value': c, 'lib': 'Connector', 'part': '', 'footprint': KICAD_HEADER_FOOTPRINT, 'role': 'connector', 'connector': c,
                    'fact': '%s:devkit.header.%s' % (BOARD, c)} for c in sorted(HEADERS)]),
            'power_rails_json': '[]', 'crystal': '40 MHz main crystal: not in the files read (undetermined)',
            'usb_bridge_chip': 'the ESP32-C3 itself (USB Serial/JTAG, GPIO18/19) — but see notes',
            'usb_ids_json': usb_ids_json, 'facts_json': json.dumps(['%s:usb_serial_jtag.pins' % SOC]),
            'source': 'zephyr-ingest:%s %s (%s) + %s' % (TAG, r['identity']['full_name'], ', '.join(f['path'] for f in r['files']), DS_DOC),
            'undetermined': 'the USB-UART bridge chip on UART0 (the DevKitM-1 schematic names a CP2102N; not yet a row); power rails; the crystal',
            'notes': 'upstream esp32c3_devkitm.dts on &usb_serial: "requires resoldering of resistors on the board" — the DevKitM\'s USB connector reaches '
                     'UART0 through a USB-UART bridge by default; the native USB Serial/JTAG the register names needs that rework on THIS devkit'}


def runtime_profiles():
    r = ingested()
    clk = r['soc']['cpu_clock_hz'][0]
    idf = {'board': BOARD, 'supported': True, 'refusal': '', 'clock_hz': clk, 'tick_hz': 1000, 'console_uart': 'none', 'stack_bytes': 0, 'heap_bytes': 0,
           'peripherals_json': json.dumps([{'name': 'UART0', 'use': 'the SimRigState frames, 115200 Bd'}, {'name': 'UART1', 'use': 'the FreeRTOS trace (TX only)'}]),
           'config_json': '[]', 'twin': 'qemu:esp32c3',
           'origin': 'sc-3 template (sdkconfig.defaults: CONFIG_FREERTOS_HZ=1000, CONFIG_ESP_CONSOLE_NONE=y)',
           'notes': 'clock = the SoC row\'s 160 MHz (Zephyr dtsi); ESP-IDF\'s own CPU-frequency default was not re-read; stacks are per task (the app\'s xTaskCreate)'}
    return [dict(idf, name='%s:esp-idf' % BOARD, runtime='esp-idf'),
            dict(idf, name='%s:freertos' % BOARD, runtime='freertos', notes='FreeRTOS on the C3 = ESP-IDF\'s FreeRTOS (sc-3) — the same profile as esp-idf'),
            {'name': '%s:zephyr' % BOARD, 'board': BOARD, 'runtime': 'zephyr', 'supported': True, 'refusal': '', 'clock_hz': clk, 'tick_hz': 0,
             'console_uart': r['console'], 'stack_bytes': 0, 'heap_bytes': r['heap_add'],
             'peripherals_json': json.dumps(sorted({p['peripheral'].lower() for p in board_pins() if p['signal']} | {'usb_serial', 'gpio0'})),
             'config_json': json.dumps(r['defconfig']), 'twin': '',
             'origin': 'ingested: %s_defconfig, Kconfig (HEAP_MEM_POOL_ADD_SIZE_BOARD default %d), chosen zephyr,console @zephyr %s' % (r['identity']['name'], r['heap_add'], TAG),
             'notes': 'renders an overlay + .conf; NOT built — no Zephyr toolchain worker exists (hn-5); tick = the Zephyr default (CONFIG_SYS_CLOCK_TICKS_PER_SEC not read)'},
            {'name': '%s:bare-c' % BOARD, 'board': BOARD, 'runtime': 'bare-c', 'supported': False,
             'refusal': 'no bare-C template for the C3 — sc-3 is ESP-IDF (FreeRTOS); a bare-metal C3 build is not a road step', 'clock_hz': clk, 'tick_hz': 0,
             'console_uart': '', 'stack_bytes': 0, 'heap_bytes': 0, 'peripherals_json': '[]', 'config_json': '[]', 'twin': '', 'origin': '', 'notes': ''}]
