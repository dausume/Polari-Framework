"""
@module board.custom.gen_c3

`pol board gen c3 [--variant <name>]` (sc-3): render an ESP-IDF C project for the ESP32-C3 AROUND the generated SimRigState
header — the template `board/custom/firmware/esp32c3/` (CMakeLists.txt, sdkconfig.defaults, partitions.csv, main/: the
common layer, the trace ring, the variant's app `apps/<app>.c` copied as main/app.c) + main/board_config.h from the
variant's knobs (board.custom.variants_c3) + (brd-bo) main/board_pins.h and sdkconfig.defaults' board-owned lines from THE
BOARD OBJECT's rows (board.custom.views.esp_idf; the template's polari_c3.h keeps sc-3's line layout, so the image of every
variant stays byte-identical — the ESP_ERROR_CHECK __LINE__ immediates and the ELF sha esptool patches into the app descriptor
both move with a shifted line) + main/simrigstate_packets.h rendered with c_twin **target=host** (riscv32's
double is 8 bytes, little-endian: no software conversion — the UNO's target=avr is not needed), wire v2, so the frames are
byte-for-byte the UNO's and the SAME bridge parses them:

  * live from `GET <api>/api/grpc/exposures/SimRigState/c-header?target=host&wire=2` when --api is given,
  * from THIS server's own exposure when a `manager` is passed (in-process),
  * else from the pinned contract snapshot (custom/contracts/SimRigState.v2.json).

RULE 2 on the result: C sources and headers, plus ESP-IDF's build-system files (CMakeLists.txt, sdkconfig.defaults,
partitions.csv) — ESP-IDF requires CMake; the firmware's language is C. Anything else is refused.

Work dir layout as the UNO's (gen.py): <work>/project, <work>/out, <work>/firmware_build.json, <work>/builds/<build>/.
Default work: gen.default_work('esp32-c3') — /app/data/board/esp32-c3/ inside a backend container, ~/.cache/polari-board/esp32-c3/ on a bare host.

    python3 -m board.custom.gen_c3 c3 [--variant V] [--out DIR] [--api URL] [--rig-name N] [--device-id N] [--knob NAME=VALUE ...]

`--knob` sets any knob the variant has (the light's pads and `pin_shim`: 0 = the chip HAL, which the pin model needs; 1 = the RAM pin shim).
A knob the variant does not have is refused, never dropped.
"""
import datetime
import json
import os
import re
import shutil
import ssl
import sys

from board.custom import compat, gen
from board.custom import variants_c3 as V

HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATE = os.path.join(HERE, 'firmware', 'esp32c3')
TEMPLATE_REL = 'board/custom/firmware/esp32c3'
BOARD = V.BOARD
ALIASES = ('c3', 'esp32c3', 'esp32-c3')
TEMPLATE_FILES = ('CMakeLists.txt', 'sdkconfig.defaults', 'partitions.csv', 'main/CMakeLists.txt', 'main/polari_c3.c',
                  'main/polari_c3.h', 'main/polari_trace.c', 'main/polari_trace.h')
RULE2_EXT = ('.c', '.h')
RULE2_BUILD_FILES = ('CMakeLists.txt', 'sdkconfig.defaults', 'partitions.csv')
TARGET = 'host'


def is_c3(alias):
    return str(alias).lower() in ALIASES


def default_work():
    return gen.default_work(BOARD)


def header(cls='SimRigState', api='', manager=None, msg_type=1):
    """(text, provenance) of the class header rendered target=host, wire v2."""
    if api:
        url = '%s/api/grpc/exposures/%s/c-header?msg_type=%d&target=%s&wire=2' % (api.rstrip('/'), cls, msg_type, TARGET)
        from polariApiServer import outbound
        with outbound.http_request('self', 'board', 'GET', url, means='rest', timeout=30, lib='urllib') as r:
            text = r.read().decode()
        if '%s_MSG_TYPE' % cls.upper() not in text:
            raise gen.GenRefused('the server returned no header for %s (exposure enabled?)' % cls)
        m = re.search(r'contract v(\d+)\s+hash (\w*)', text)
        w2 = re.search(r'hash2 (\w+)', text)
        return text, {'source': 'live', 'url': url, 'contract_version': int(m.group(1)) if m else 0, 'contract_hash': m.group(2) if m else '',
                      'hash_v2': w2.group(1) if w2 else '', 'tag_order': gen._order_from_header(text, cls)}
    if manager is not None:
        now = compat.server_header(manager, cls, msg_type, TARGET, bridge='')
        if now is None:
            raise gen.GenRefused('this server knows no contract for %s' % cls)
        prov = {k: now[k] for k in ('source', 'contract_version', 'contract_hash', 'tag_order', 'hash_v2', 'path', 'sha256') if k in now}
        return now['text'], prov
    from grpcbridge.custom.c_twin import render_c_header
    c, path = gen.pinned_contract(cls)
    spec = compat.wire_spec(None, cls, c['field_map'], '')
    text = render_c_header(cls, c['field_map'], msg_type, version=c['contract_version'], contract_hash=c['contract_hash'], target=TARGET, wire=spec)
    return text, {'source': 'pinned', 'path': os.path.relpath(path, os.path.dirname(os.path.dirname(HERE))), 'sha256': gen.sha256(open(path, 'rb').read()),
                  'contract_version': c['contract_version'], 'contract_hash': c['contract_hash'], 'tag_order': compat.tag_order(c['field_map']),
                  'hash_v2': spec['hash_v2']}


def project_files(project):
    out = []
    for root, _, files in os.walk(project):
        for fn in files:
            out.append(os.path.relpath(os.path.join(root, fn), project))
    return sorted(out)


def rule2_violations(project):
    return [f for f in project_files(project) if not (f.endswith(RULE2_EXT) or os.path.basename(f) in RULE2_BUILD_FILES)]


def source_sha(project):
    h = __import__('hashlib').sha256()
    for f in project_files(project):
        h.update(f.encode() + b'\0' + open(os.path.join(project, f), 'rb').read() + b'\0')
    return h.hexdigest()


def board_files(manager=None, board_tables=None):
    """brd-bo: (board_pins.h text, {sdkconfig key: line}, board sha) rendered from THE BOARD OBJECT's rows (this server's when it
    holds them, the given tables, else the seeds) — board.custom.views.esp_idf."""
    from board.custom import board_object as bo
    from board.custom.views import esp_idf, ViewRefused
    tables = board_tables
    if tables is None and manager is not None:
        t = bo.tables_from_manager(manager)
        tables = t if any(p.get('board') == BOARD for p in t.get('BoardPin', [])) else None
    try:
        r = bo.rows_for(BOARD, tables)
        files = esp_idf.render(r, bo.board_sha(r))
        lines = esp_idf.sdk_lines(r)
    except (bo.BoardObjectRefused, ViewRefused) as e:
        raise gen.GenRefused(str(e))
    return files[esp_idf.PINS_FILE], {ln.split('=', 1)[0]: ln for ln, _ in lines}, bo.board_sha(r)


def apply_sdkconfig(text, board_lines):
    """The template's sdkconfig.defaults with every BOARD-OWNED line taken from the rows, IN PLACE (same position; a line the
    template lacks is appended). The app's own lines are untouched. → (text, [keys replaced], [keys appended])."""
    out, seen, changed = [], set(), []
    for ln in text.splitlines():
        key = ln.split('=', 1)[0].strip() if ln.startswith('CONFIG_') else ''
        if key in board_lines:
            seen.add(key)
            if ln != board_lines[key]:
                changed.append(key)
            out.append(board_lines[key])
        else:
            out.append(ln)
    added = [k for k in board_lines if k not in seen]
    out += [board_lines[k] for k in added]
    return '\n'.join(out) + ('\n' if text.endswith('\n') else ''), changed, added


def light_roles(r):
    """hal-3b step 2: what apps/light_hal.h's chip half (PIN_SHIM 0) asks of the HAL, per role, on THIS variant's pins (the light knobs are
    GPIO numbers). The same three pins ESP-IDF's gpio_config configured before: the LED a push-pull output with no pulls, the sense line an
    input with the pull-down, the button an input with the pull-up. The button's falling-edge interrupt stays on ESP-IDF's gpio driver
    (gpio_set_intr_type / gpio_intr_enable / the ISR service): the C3 has no int family in the HAL yet - said, not hidden."""
    k = r['knobs']
    init_all = lambda ops: tuple(o for o in ops if o not in ('gpio.set_high', 'gpio.set_low', 'gpio.read'))
    roles = [('LED', 'led_pin', ['gpio.output', 'gpio.pull_none', 'gpio.set_high', 'gpio.set_low']),
             ('SENSE', 'sense_pin', ['gpio.input', 'gpio.pull_none', 'gpio.pull_down', 'gpio.read']),
             ('BUTTON', 'button_pin', ['gpio.input', 'gpio.pull_none', 'gpio.pull_up'])]
    return [{'role': role, 'variable': var, 'pin': 'GPIO%d' % int(k[var]), 'ops': ops, 'init': init_all(ops)} for role, var, ops in roles]


def c3_reserved(r):
    """every name this C3 build already gives a meaning (its board_config.h #defines and build flags) -> why (hal-3b 2b's guard)"""
    out = {n: 'a build flag of variant %s' % r['name'] for n, _ in r['flags']}
    for n in re.findall(r'^#define\s+(\w+)', V.render_config(r), re.M):
        out.setdefault(n, 'a board_config.h #define')
    return out


def c3_hal_header(r):
    """-> the merged project header (hal.custom.project) with each unit also under its role name (HAL_LED_SET_HIGH ...), init forms for
    the setup ops (hal_pins_init runs before the button ISR is attached)."""
    from hal.custom import project as HP
    roles = light_roles(r)
    try:
        base = HP.project_header('esp32c3', {x['variable']: x['ops'] for x in roles}, {x['variable']: x['pin'] for x in roles})
        aliases = [{'name': 'HAL_%s_%s' % (x['role'], gen._role_suffix(op, x['role'])), 'key': base['macros_keys'][(x['variable'], op)],
                    'form': 'init' if op in x['init'] else 'call'} for x in roles for op in x['ops']]
        return HP.merged_header('esp32c3', [base], ['apps/light_hal.h'], aliases=aliases, always=True, reserved=c3_reserved(r))
    except Exception as e:   # HalRefused / HalNameRefused: in words, never a half-written project
        raise gen.GenRefused('the C3 light pins through the generated HAL: %s' % e)


def gen_c3(variant=None, work=None, api='', manager=None, variant_rows=None, board_tables=None, **knobs):
    try:
        v = V.find(variant or V.DEFAULT_VARIANT, variant_rows)
        r = V.resolve(v, knobs)
    except V.VariantRefused as e:
        raise gen.GenRefused(str(e))
    hal = gen.hal_check(r['name'], r['knobs'], manager)
    work = work or default_work()
    project = os.path.join(work, 'project')
    shutil.rmtree(project, ignore_errors=True)
    shutil.rmtree(os.path.join(work, 'out'), ignore_errors=True)
    os.makedirs(os.path.join(project, 'main'))
    for f in TEMPLATE_FILES:
        shutil.copy(os.path.join(TEMPLATE, f), os.path.join(project, f))
    # brd-bo: the board's own lines come from the rows — main/board_pins.h generated, sdkconfig.defaults' board-owned lines in place
    pins_h, sdk_board, bsha = board_files(manager, board_tables)
    open(os.path.join(project, 'main', 'board_pins.h'), 'w').write(pins_h)
    sdk, sdk_changed, sdk_added = apply_sdkconfig(open(os.path.join(TEMPLATE, 'sdkconfig.defaults')).read(), sdk_board)
    open(os.path.join(project, 'sdkconfig.defaults'), 'w').write(sdk)
    app_src = os.path.join(TEMPLATE, 'apps', '%s.c' % r['app'])
    shutil.copy(app_src, os.path.join(project, 'main', 'app.c'))
    text, prov = header('SimRigState', api, manager)
    open(os.path.join(project, 'main', 'simrigstate_packets.h'), 'w').write(text)
    # smp S5: an app that speaks other classes (the light: ButtonClockState + ButtonClockEvent) gets their headers too (msg_type = position + 1, as the UNO), its extra files, and its components
    # on the main component's REQUIRES; SimRigState stays (the common layer, polari_c3.c, includes it). Apps that speak only SimRigState are untouched, byte for byte.
    extra_cls = []
    for i, cls in enumerate(c for c in V.APP_CLASSES[r['app']] if c != 'SimRigState'):
        t2, p2 = header(cls, api, manager, msg_type=V.APP_CLASSES[r['app']].index(cls) + 1)
        fn = '%s_packets.h' % cls.lower()
        open(os.path.join(project, 'main', fn), 'w').write(t2)
        extra_cls.append(dict(p2, **{'class': cls, 'header': 'main/' + fn, 'header_sha256': gen.sha256(t2), 'target': TARGET, 'msg_type': V.APP_CLASSES[r['app']].index(cls) + 1,
                                     'tag_order': p2.pop('tag_order', None) or gen._order_from_header(t2, cls), 'wire': 2, 'bridge': ''}))
    extra_files = []
    for f in V.APP_EXTRA_FILES.get(r['app'], ()):
        shutil.copy(os.path.join(TEMPLATE, 'apps', f), os.path.join(project, 'main', f))
        extra_files.append(f)
    if V.APP_REQUIRES.get(r['app']):
        cm = os.path.join(project, 'main', 'CMakeLists.txt')
        txt = open(cm).read()
        assert 'REQUIRES esp_driver_uart esp_partition esp_timer freertos' in txt, 'the template main/CMakeLists.txt moved: update gen_c3'
        open(cm, 'w').write(txt.replace('REQUIRES esp_driver_uart esp_partition esp_timer freertos', 'REQUIRES esp_driver_uart esp_partition esp_timer freertos ' + ' '.join(V.APP_REQUIRES[r['app']])))
    open(os.path.join(project, 'main', 'board_config.h'), 'w').write(V.render_config(r))
    # hal-3b step 2: the light app's pin layer (apps/light_hal.h, PIN_SHIM 0) calls the GENERATED HAL for its three pins; the header is
    # written for every light build (the PIN_SHIM 1 half never includes it, so the twin's binary is unchanged) and for no other app.
    hal_hdr = None
    if r['app'] == 'light':
        hal_hdr = c3_hal_header(r)
        open(os.path.join(project, 'main', hal_hdr['file']), 'w').write(hal_hdr['text'])
    viol = rule2_violations(project)
    if viol:
        raise gen.GenRefused('RULE 2: a generated C3 project holds only .c/.h + ESP-IDF\'s CMakeLists.txt / sdkconfig.defaults / partitions.csv — found %s' % viol)
    ssha = source_sha(project)
    order = prov.pop('tag_order', None) or gen._order_from_header(text, 'SimRigState')
    cls_row = dict(prov, **{'class': 'SimRigState', 'header': 'main/simrigstate_packets.h', 'header_sha256': gen.sha256(text), 'target': TARGET,
                            'msg_type': 1, 'tag_order': order, 'wire': 2, 'bridge': ''})
    tfiles = [('template ' + f, '%s/%s' % (TEMPLATE_REL, f), os.path.join(TEMPLATE, f)) for f in TEMPLATE_FILES] + \
        [('template app %s (main/app.c)' % r['app'], '%s/apps/%s.c' % (TEMPLATE_REL, r['app']), app_src)] + \
        [('template app file %s' % f, '%s/apps/%s' % (TEMPLATE_REL, f), os.path.join(TEMPLATE, 'apps', f)) for f in extra_files]
    row = {'name': '%s-%s' % (r['name'], ssha[:12]), 'board_definition': BOARD, 'state': 'generated', 'variant': r['name'],
           'classes_json': json.dumps([cls_row] + extra_cls), 'template': TEMPLATE_REL, 'source_sha': ssha,
           'header_sha256': compat.combined_sha([cls_row] + extra_cls),
           'tag_order_json': json.dumps(dict({'SimRigState': order}, **{c['class']: c['tag_order'] for c in extra_cls})),
           'contract_hash_v2': cls_row.get('hash_v2', ''), 'bridge_name': '', 'instance_index': 0,
           'artifact_sha256': '', 'engines_json': '{}', 'size_text': 0, 'size_data': 0, 'size_bss': 0, 'built_at': '', 'flashed_to': '',
           'flash_log': '', 'generated_at': datetime.datetime.now().isoformat(timespec='seconds'), 'hex_path': '',
           'repro_json': json.dumps({'inputs': [{'label': lab, 'path': p, 'sha256': gen.sha256(open(fp, 'rb').read())} for lab, p, fp in tfiles]
                                    + [{'label': 'contract SimRigState', 'path': cls_row.get('path', cls_row.get('url', '')), 'sha256': cls_row.get('sha256', cls_row['header_sha256'])}],
                                    'knobs': dict(r['knobs'], variant=r['name'], app=r['app'], build_flags=['%s=%d' % f for f in r['flags']]),
                                    'board_object': {'board': BOARD, 'board_sha': bsha, 'board_pins_h_sha256': gen.sha256(pins_h),
                                                     'sdkconfig_board_lines': sorted(sdk_board.values()), 'sdkconfig_changed': sdk_changed,
                                                     'sdkconfig_added': sdk_added},
                                    **({'catom_hal': hal} if hal else {}),
                                    **({'generated_hal': {'file': 'main/' + hal_hdr['file'], 'sha256': hal_hdr['sha256'], 'units': hal_hdr['keys'],
                                                          'roles': [{k: x[k] for k in ('role', 'pin', 'ops')} for x in light_roles(r)]}} if hal_hdr else {})}),
           'notes': 'generated (variant %s, ESP-IDF project); `pol board build c3` compiles it' % r['name'], 'project_dir': project, 'work_dir': work}
    gen.write_record(work, row)
    return row


def cli_knobs(variant, words):
    """`--knob NAME=VALUE` words -> {name: value} for the variant; a word that is not NAME=VALUE, a knob the variant does not have and a knob named twice
    are refused (V.resolve drops a name it does not know, which on a command line would read as done)."""
    try:
        v = V.find(variant or V.DEFAULT_VARIANT, None)
    except V.VariantRefused as e:
        raise gen.GenRefused(str(e))
    has = sorted(set(V.DEFAULT_KNOBS) | (set(V.LIGHT_KNOBS) if v.get('app') == 'light' else set()))
    out = {}
    for word in words:
        name, mark, value = word.partition('=')
        if not mark or not value:
            raise gen.GenRefused('--knob wants NAME=VALUE, not %r' % word)
        if name not in has:
            raise gen.GenRefused('variant %s has no knob %s; it has %s' % (v.get('name'), name, ', '.join(has)))
        if name in out:
            raise gen.GenRefused('--knob names %s twice' % name)
        out[name] = value
    return out


def main(argv):
    import argparse
    ap = argparse.ArgumentParser(prog='pol board gen c3')
    ap.add_argument('board')
    ap.add_argument('--variant', default='')
    ap.add_argument('--out')
    ap.add_argument('--api', default='')
    ap.add_argument('--rig-name')
    ap.add_argument('--device-id', type=int)
    ap.add_argument('--knob', action='append', default=[], metavar='NAME=VALUE')
    a = ap.parse_args(argv)
    try:
        knobs = cli_knobs(a.variant, a.knob)
        for name, value in (('rig_name', a.rig_name), ('device_id', a.device_id)):      # the two older options: the same knobs by their own flag
            if value is not None:
                if name in knobs:
                    raise gen.GenRefused('%s is given twice: by its own option and by --knob' % name)
                knobs[name] = value
        row = gen_c3(a.variant or None, a.out, a.api, **knobs)
    except gen.GenRefused as e:
        print('[REFUSED] %s' % e)
        return 1
    c = json.loads(row['classes_json'])[0]
    print('[ OK ] %s  variant=%s  state=%s' % (row['name'], row['variant'], row['state']))
    print('       project  %s  (%s)' % (row['project_dir'], ', '.join(project_files(row['project_dir']))))
    print('       header   %s  contract v%s hash %s  (%s, target=%s)  sha256 %s' % (c['header'], c['contract_version'], c['contract_hash'], c['source'],
                                                                              TARGET, c['header_sha256'][:16]))
    print('       wire v2  hash2 %s  order %s' % (c.get('hash_v2'), ', '.join(c['tag_order'])))
    k = json.loads(row['repro_json'])['knobs']
    print('       knobs    %s' % '  '.join('%s=%s' % (n, k[n]) for n in sorted(k) if n not in ('variant', 'app', 'build_flags')))
    print('       next     pol board build c3')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
