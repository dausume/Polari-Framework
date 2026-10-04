"""
@module board.custom.views.esp_idf

THE ESP-IDF VIEW (brd-bo): from the C3's rows,
  board_pins.h      one `#define <firmware_symbol> <GPIO number>` per BoardPin that carries a C identifier (the template's
                    POLARI_TRACE_TX_GPIO, POLARI_FRAME_TX_GPIO / _RX_GPIO), each commented with its canonical pin, net, signal;
  sdkconfig.board   the sdkconfig lines the BOARD owns, each derived from a row field: CONFIG_IDF_TARGET (SocDefinition
                    vendor_target), CONFIG_ESPTOOLPY_FLASHSIZE_<n>MB (the SoC row's flash0 region — the module's flash, ingested
                    from esp32c3_mini_n4.dtsi), CONFIG_ESP_CONSOLE_NONE (RuntimeProfile esp-idf console_uart 'none'),
                    CONFIG_FREERTOS_HZ (its tick_hz) + the profile's own config_json lines.
gen_c3 writes board_pins.h into every C3 project and applies the sdkconfig.board lines IN PLACE in the template's
sdkconfig.defaults (the template keeps the app's own choices: watchdogs, reproducible build, partitions, log levels, -Os).
"""
import json
import re

from board.custom.views import ViewRefused, banner

PINS_FILE, SDK_FILE = 'board_pins.h', 'sdkconfig.board'


def sdk_lines(r):
    """[(line, the row field it came from)] — the board-owned sdkconfig lines."""
    prof = r['profiles'].get('esp-idf') or {}
    soc = r['soc'] or {}
    out = []
    t = re.match(r'IDF_TARGET=(\w+)', soc.get('vendor_target') or '')
    if not t:
        raise ViewRefused('SocDefinition %s names no IDF_TARGET' % soc.get('name'))
    out.append(('CONFIG_IDF_TARGET="%s"' % t.group(1), 'SocDefinition.vendor_target'))
    flash = next((m for m in json.loads(soc.get('memory_map_json') or '[]') if m.get('region') == 'flash0'), None)
    if flash:
        mb = int(flash['size']) // 1048576
        out.append(('CONFIG_ESPTOOLPY_FLASHSIZE_%dMB=y' % mb, 'SocDefinition.memory_map flash0 (%s)' % flash.get('fact', '')))
    con = prof.get('console_uart') or ''
    if con == 'none':
        out.append(('CONFIG_ESP_CONSOLE_NONE=y', 'RuntimeProfile esp-idf console_uart'))
    elif con:
        raise ViewRefused('console %r: only "none" maps to an sdkconfig line here (UART0 carries the frames)' % con)
    if int(prof.get('tick_hz') or 0):
        out.append(('CONFIG_FREERTOS_HZ=%d' % int(prof['tick_hz']), 'RuntimeProfile esp-idf tick_hz'))
    out += [(ln, 'RuntimeProfile esp-idf config_json') for ln in json.loads(prof.get('config_json') or '[]')]
    return out


def render(r, bsha):
    prof = r['profiles'].get('esp-idf') or {}
    if not prof.get('supported'):
        raise ViewRefused('no ESP-IDF view for %s: %s' % (r['board'], prof.get('refusal') or 'no esp-idf RuntimeProfile row'))
    syms = sorted((p for p in r['pins'] if p.get('firmware_symbol')), key=lambda p: p['firmware_symbol'])
    lines = ['/* board_pins.h — %s */' % banner('esp-idf', r, bsha), '#ifndef POLARI_BOARD_PINS_H', '#define POLARI_BOARD_PINS_H', '']
    for p in syms:
        lines.append('#define %-22s %-3d /* %s — net %s%s */' % (p['firmware_symbol'], int(p['number']), p['canonical'], p['net'],
                                                               (', ' + p['signal']) if p.get('signal') else ''))
    lines += ['', '#endif /* POLARI_BOARD_PINS_H */', '']
    sdk = ['# sdkconfig.board — %s' % banner('esp-idf', r, bsha)] + ['%s' % ln for ln, _ in sdk_lines(r)]
    return {PINS_FILE: '\n'.join(lines), SDK_FILE: '\n'.join(sdk) + '\n'}


def parse_pins(text):
    return {m.group(1): int(m.group(2)) for m in re.finditer(r'^\s*#define\s+(POLARI_[A-Z0-9_]+_GPIO)\s+(\d+)', text, re.M)}


def parse_sdk(text):
    out = {}
    for ln in text.splitlines():
        m = re.match(r'^(CONFIG_[A-Z0-9_]+)=(.*)$', ln.strip())
        if m:
            out[m.group(1)] = m.group(2)
    return out


def ingest(files, r):
    """→ pins [{canonical, firmware_symbol}] + the profile fields the sdkconfig lines say (tick_hz, console_uart, flash, target)."""
    pins_text = files.get(PINS_FILE) or next((t for n, t in files.items() if n.endswith('.h')), '')
    sdk_text = files.get(SDK_FILE) or next((t for n, t in files.items() if 'sdkconfig' in n), '')
    pins = [{'canonical': 'GPIO%d' % n, 'firmware_symbol': s} for s, n in sorted(parse_pins(pins_text).items())]
    sdk = parse_sdk(sdk_text)
    prof = {}
    if 'CONFIG_FREERTOS_HZ' in sdk:
        prof['tick_hz'] = int(sdk['CONFIG_FREERTOS_HZ'])
    if sdk.get('CONFIG_ESP_CONSOLE_NONE') == 'y':
        prof['console_uart'] = 'none'
    for k in sdk:
        m = re.match(r'CONFIG_ESPTOOLPY_FLASHSIZE_(\d+)MB$', k)
        if m and sdk[k] == 'y':
            prof['flash_mb'] = int(m.group(1))
    if 'CONFIG_IDF_TARGET' in sdk:
        prof['target'] = sdk['CONFIG_IDF_TARGET'].strip('"')
    return {'pins': pins, 'profile': prof, 'notes': ''}


def profile_now(r):
    """The same profile fields as ingest() reads, from the rows (what a conflict is judged against)."""
    out = {}
    for ln, _ in sdk_lines(r):
        m = re.match(r'CONFIG_FREERTOS_HZ=(\d+)', ln)
        if m:
            out['tick_hz'] = int(m.group(1))
        if ln == 'CONFIG_ESP_CONSOLE_NONE=y':
            out['console_uart'] = 'none'
        m = re.match(r'CONFIG_ESPTOOLPY_FLASHSIZE_(\d+)MB=y', ln)
        if m:
            out['flash_mb'] = int(m.group(1))
        m = re.match(r'CONFIG_IDF_TARGET="(\w+)"', ln)
        if m:
            out['target'] = m.group(1)
    return out
