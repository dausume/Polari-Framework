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
    for f in r['files']:
        out.append(_f('zephyr.%s' % os.path.basename(f['path']), f['sha256'], 'sha256', f['path'], 'ingested verbatim', zdoc, zrev, zurl + f['path'], board=BOARD))
    return out


def soc_pins():
    return [{'name': '%s:GPIO%d' % (SOC, n), 'soc': SOC, 'pin': 'GPIO%d' % n, 'port': 'GPIO', 'bit': n, 'package_pin': PINS[n][0],
             'functions_json': json.dumps(_functions(n)), 'default_function': PINS[n][1], 'fact': '%s:pin.GPIO%d' % (SOC, n),
             'notes': 'default = IO MUX F0 (the PDF\'s bold default marks were not readable from the text extraction)'
             + ('; connected to the module\'s flash on SPI0/1 (SPI* function) — not a free GPIO on a MINI-1 module (unverified for his board)' if 12 <= n <= 17 else '')}
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
    for c, row in rows.items():
        row['facts_json'] = json.dumps(sorted(set(json.loads(row['facts_json'] or '[]')) | {'%s:pin.%s' % (SOC, c)}))
    return [rows[c] for c in sorted(rows, key=lambda c: int(c[4:]))]


def nets():
    return [{'name': '%s:%s' % (BOARD, p['net']), 'board': BOARD, 'net': p['net'], 'net_class': 'signal', 'volts': 0.0, 'circuit_net': '',
             'fact': '', 'notes': 'derived: the pinctrl macro stem (no net names in a devicetree)' if p['signal'] else ''} for p in board_pins()]


def hardware(usb_ids_json):
    r = ingested()
    return {'name': BOARD, 'board': BOARD,
            'components_json': json.dumps([
                {'ref': 'U1', 'value': 'ESP32-C3', 'lib': '', 'part': '', 'footprint': '', 'role': 'mcu', 'soc': SOC,
                 'undetermined': 'the module footprint (ESP32-C3-MINI-1) is not in KiCad\'s cited libraries here; pin numbers are the chip\'s QFN32 (Table 2-4)'},
                {'ref': 'SW1', 'value': 'User SW1', 'lib': '', 'part': '', 'footprint': '', 'role': 'button', 'pin': 'GPIO9',
                 'fact': '%s:zephyr.esp32c3_devkitm.dts' % BOARD}]),
            'power_rails_json': '[]', 'crystal': '40 MHz main crystal: not in the files read (undetermined)',
            'usb_bridge_chip': 'the ESP32-C3 itself (USB Serial/JTAG, GPIO18/19) — but see notes',
            'usb_ids_json': usb_ids_json, 'facts_json': json.dumps(['%s:usb_serial_jtag.pins' % SOC]),
            'source': 'zephyr-ingest:%s %s (%s) + %s' % (TAG, r['identity']['full_name'], ', '.join(f['path'] for f in r['files']), DS_DOC),
            'undetermined': 'headers / connector pin order (Zephyr\'s dts describes none); the USB-UART bridge chip on UART0; power rails; the crystal',
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
