"""
@module board.custom.gen

`pol board gen uno [--variant <name>]` (brd-1, plan §3 step 2; brd-fi: VARIANTS): render a plain-C avr-libc project
AROUND the generated per-class header(s). The project is the template (`board/custom/firmware/uno/`: the variant's app
`apps/<app>.c` copied as main.c, hal.c/hal.h, the Makefile) + board_config.h rendered from the variant's knobs
(board.custom.variants) + one `<class>_packets.h` per class the variant speaks, rendered with c_twin target=avr —

  * live from `GET <api>/api/grpc/exposures/<class>/c-header?target=avr` when --api is given,
  * from THIS server's own exposure when the installer generates in-process (a `manager`),
  * else from the pinned contract snapshot (custom/contracts/<class>.v<N>.json, which says what it pins).

No --variant = uno-sim-rig (brd-1's firmware, unchanged); `--class X` alone picks the seeded variant written for X.
RULE 2 is checked on the result: a generated project holds only .c/.h/.v/.sv + Makefile/linker script.

brd-bo (THE BOARD OBJECT): the pin constants of board_config.h (LED_PIN, PWM_PIN, ADC_CHANNEL) come from the board's BoardPin
rows (board_pins below — the server's rows, else the seeds); the text rendered is unchanged, so every seeded variant's .hex stays
byte-identical (board_object_selftest + tests/board_object_probe.py prove it); the repro block names the pins and the board sha.

brd-fi: the FirmwareBuild row also carries `header_sha256` + `tag_order_json` (per class, the wire order) captured HERE,
so the installer can judge compatibility on what the board will actually speak (board.custom.compat) — never on
contract_hash alone (brd-1's finding: v1/v2 share a hash yet differ in order).

Layout of a work dir (default module_home.module_home('board')/<board>/ — /app/data/board/<board>/ inside a backend
container, ~/.cache/polari-board/<board>/ on a bare host):
    project/              the buildable tree of the CURRENT variant (nothing else lives in it — RULE 2)
    out/                  firmware.elf / firmware.hex after `pol board build`
    firmware_build.json   the FirmwareBuild row (state generated → built | refused → flashed), its repro block
    builds/<build>/       the build store: every built variant's .hex + record, so any of them can be installed

    python3 -m board.custom.gen uno [--variant V | --class C] [--out DIR] [--api URL] [--rig-name N] [--device-id N] [--u2x 0|1]
"""
import datetime
import hashlib
import json
import os
import re
import shutil
import ssl
import sys

from board.custom import variants as V
from board.custom import compat

HERE = os.path.dirname(os.path.abspath(__file__))
MOD = os.path.dirname(HERE)
TEMPLATES = {'arduino-uno-r3': os.path.join(HERE, 'firmware', 'uno')}
TEMPLATE_FILES = ('hal.c', 'hal.h', 'Makefile')   # + apps/<app>.c → main.c
ALIASES = {'uno': 'arduino-uno-r3', 'arduino-uno': 'arduino-uno-r3', 'arduino-uno-r3': 'arduino-uno-r3'}
#: the classes a template has an app for (another class = a new app, brd-4)
TEMPLATE_CLASSES = {'arduino-uno-r3': tuple(sorted({c for cs in V.APP_CLASSES.values() for c in cs}))}
RULE2_EXT = ('.c', '.h', '.v', '.sv')
RULE2_NAMES = ('Makefile', 'link.ld')
CONTRACTS = compat.CONTRACTS
DEFAULT_KNOBS = {k: V.DEFAULT_KNOBS[k] for k in ('rig_name', 'device_id', 'usart_u2x')}


class GenRefused(ValueError):
    pass


def sha256(data):
    return hashlib.sha256(data if isinstance(data, bytes) else data.encode()).hexdigest()


def board_name(alias):
    b = ALIASES.get(alias)
    if not b and str(alias).lower() in ('c3', 'esp32c3', 'esp32-c3'):
        raise GenRefused('%r: no firmware template in gen.py (the UNO\'s) — the ESP32-C3 has its own generator, board.custom.gen_c3 '
                         '(`pol board gen c3`, sc-3)' % alias)
    if not b:
        raise GenRefused('no firmware template for %r — the UNO and the ESP32-C3 are picked (plan §8a; sc-3); every other device is a Road' % alias)
    return b


def default_work(board):
    from polariApiServer.module_home import module_home
    return os.path.join(module_home('board', os.environ.get('POLARI_BOARD_HOME')), board)


def pinned_contract(cls):
    c, path = compat.pinned_contract(cls)
    if c is None:
        raise GenRefused('no pinned contract for %s — pass --api to fetch the live header' % cls)
    return c, path


def header(cls, api='', msg_type=1, manager=None, bridge='', rx_parser='resync'):
    """(text, provenance) of `<cls>_packets.h` with target=avr — brd-wire: the WIRE V2 header (prelude: instance index in
    the width `bridge`'s bindings imply + presence bits; the EnumMappings as enums). sc-1: `rx_parser` 'keep-tail' renders
    the receiver fix (c_twin_v2.RX_PARSERS) — offline from the pinned contract only (a server's header is its own)."""
    if rx_parser != 'resync' and (api or manager is not None):
        raise GenRefused('rx_parser %s is rendered offline from the pinned contract only — a live or in-process header is the '
                         'server\'s own (drop --api / generate offline)' % rx_parser)
    if api:
        url = '%s/api/grpc/exposures/%s/c-header?msg_type=%d&target=avr&wire=2&bridge=%s' % (api.rstrip('/'), cls, int(msg_type), bridge)
        from polariApiServer import outbound
        with outbound.http_request('self', 'board', 'GET', url, means='rest', timeout=30, lib='urllib', context=ssl._create_unverified_context()) as r:
            text = r.read().decode()
        m = re.search(r'contract v(\d+)\s+hash (\w*)', text)
        if '%s_MSG_TYPE' % cls.upper() not in text or 'target avr' not in text:
            raise GenRefused('the server returned no AVR header for %s (exposure enabled?)' % cls)
        w2 = re.search(r'hash2 (\w+)\s+(?:index width (\d+))?', text)
        return text, {'source': 'live', 'url': url, 'contract_version': int(m.group(1)) if m else 0, 'contract_hash': m.group(2) if m else '',
                      'tag_order': _order_from_header(text, cls), 'hash_v2': w2.group(1) if w2 else '',
                      'index_width': int(w2.group(2)) if w2 and w2.group(2) else 0,
                      'instance_count': int((re.search(r'\((\d+) instance', text) or [0, 1])[1])}
    if manager is not None:
        now = compat.server_header(manager, cls, msg_type, 'avr', bridge=bridge)
        if now is None:
            raise GenRefused('this server knows no contract for %s (no gRPC exposure, no pinned snapshot)' % cls)
        prov = {k: now[k] for k in ('source', 'contract_version', 'contract_hash', 'tag_order', 'where', 'hash_v2', 'index_width', 'instance_count') if k in now}
        prov.update({k: now[k] for k in ('path', 'sha256') if k in now})
        if now['source'] == 'live':
            prov['url'] = 'in-process: %s' % now['where']
        return now['text'], prov
    from grpcbridge.custom.c_twin import render_c_header
    c, path = pinned_contract(cls)
    spec = compat.wire_spec(None, cls, c['field_map'], bridge)
    text = render_c_header(cls, c['field_map'], int(msg_type), version=c['contract_version'], contract_hash=c['contract_hash'], target='avr',
                           wire=spec, rx_parser=rx_parser)
    return text, {'source': 'pinned', 'path': os.path.relpath(path, os.path.dirname(MOD)), 'sha256': sha256(open(path, 'rb').read()),
                  'contract_version': c['contract_version'], 'contract_hash': c['contract_hash'], 'tag_order': compat.tag_order(c['field_map']),
                  'hash_v2': spec['hash_v2'], 'index_width': spec['index_width'], 'instance_count': spec['instance_count']}


def _order_from_header(text, cls):
    """The struct's field order in a generated header (= tag order: c_twin emits fields in tag order)."""
    m = re.search(r'typedef struct\s*\{(.*?)\}\s*%s_t;' % re.escape(cls), text, re.S)
    if not m:
        return []
    return re.findall(r'\s(\w+)(?:\[\d+\])?;', m.group(1))


def render_config(knobs):
    """brd-1's signature, kept: board_config.h for uno-sim-rig with these identity knobs."""
    v = V.find(V.DEFAULT_VARIANT)
    return V.render_config(V.resolve(v, knobs))


def rule2_violations(project):
    return sorted(fn for fn in os.listdir(project) if not (fn.endswith(RULE2_EXT) or fn in RULE2_NAMES))


def source_sha(project):
    h = hashlib.sha256()
    for fn in sorted(os.listdir(project)):
        h.update(fn.encode() + b'\0' + open(os.path.join(project, fn), 'rb').read() + b'\0')
    return h.hexdigest()


def pick_variant(classes, variant, rows=None):
    """--variant wins; else the seeded variant whose app speaks exactly `classes`; no classes = uno-sim-rig."""
    if variant:
        try:
            return V.find(variant, rows)
        except V.VariantRefused as e:
            raise GenRefused(str(e))
    if not classes:
        return V.find(V.DEFAULT_VARIANT)
    for v in V.SEED_FIRMWARE_VARIANTS:
        if json.loads(v['classes_json']) == list(classes):
            return dict(v)
    raise GenRefused('the UNO template has apps for %s; %s needs its own template app (a generated header alone is not firmware)'
                     % (', '.join(TEMPLATE_CLASSES['arduino-uno-r3']), ', '.join(classes)))


def board_pins(board, manager=None, board_tables=None):
    """brd-bo: (pin knobs, {knob: canonical}, board sha) from THE BOARD OBJECT's BoardPin rows — this server's tables when it holds
    them (a `manager`), the given tables (a test's edited copy), else the seed rows. The pin constants of board_config.h
    (LED_PIN, PWM_PIN, ADC_CHANNEL) are these numbers."""
    from board.custom import board_object as bo
    tables = board_tables
    if tables is None and manager is not None:
        t = bo.tables_from_manager(manager)
        tables = t if any(p.get('board') == board for p in t.get('BoardPin', [])) else None
    try:
        r = bo.rows_for(board, tables)
    except bo.BoardObjectRefused as e:
        raise GenRefused(str(e))
    knobs, src = bo.pin_knobs(board, tables)
    return knobs, src, bo.board_sha(r), r


def _check_pins(r, knobs, rows):
    """A pin knob must name a BoardPin of the board (D<n> / A<n>), never a number the board does not have."""
    have = {p['canonical'] for p in rows['pins']}
    why = ['%s %d: the board has no pin %s%d' % (k, r['knobs'][k], 'A' if k == 'adc_channel' else 'D', r['knobs'][k])
           for k in V.PIN_KNOBS if ('A' if k == 'adc_channel' else 'D') + str(r['knobs'][k]) not in have]
    if why:
        raise GenRefused('; '.join(why))


def gen(board='uno', classes=None, work=None, api='', variant=None, manager=None, variant_rows=None, board_tables=None, **knobs):
    board = board_name(board)
    v = pick_variant(list(classes or []), variant, variant_rows)
    pins, pin_src, bsha, brows = board_pins(board, manager, board_tables)
    try:
        r = V.resolve(v, {a: b for a, b in knobs.items() if b is not None}, base=pins)
    except V.VariantRefused as e:
        raise GenRefused(str(e))
    _check_pins(r, pins, brows)
    own = set(V._j(v.get('knobs_json'), {})) | {a for a, b in knobs.items() if b is not None}
    pin_prov = {k: ({'from': 'BoardPin', 'pin': pin_src.get(k, '')} if k not in own else {'from': 'variant knob', 'value': r['knobs'][k]})
                for k in V.PIN_KNOBS}
    if classes and list(classes) != r['classes']:
        raise GenRefused('variant %s speaks %s, not %s' % (r['name'], ', '.join(r['classes']), ', '.join(classes)))
    work = work or default_work(board)
    project = os.path.join(work, 'project')
    if os.path.isdir(project):
        shutil.rmtree(project)
    shutil.rmtree(os.path.join(work, 'out'), ignore_errors=True)
    os.makedirs(project)
    tpl = TEMPLATES[board]
    for fn in TEMPLATE_FILES:
        shutil.copy(os.path.join(tpl, fn), os.path.join(project, fn))
    app_src = os.path.join(tpl, 'apps', '%s.c' % r['app'])
    shutil.copy(app_src, os.path.join(project, 'main.c'))
    class_rows, orders = [], {}
    bridge = str(r['knobs'].get('bridge') or '')
    rx_parser = str(r['knobs'].get('rx_parser') or 'resync')
    for i, cls in enumerate(r['classes']):
        text, prov = header(cls, api, i + 1, manager, bridge, rx_parser)
        width = int(prov.get('index_width') or 0)
        prov['indexed'] = '%s_INDEX_WIDTH' % cls.upper() in text   # elided entirely for a single instance
        count = int(prov.get('instance_count') or 1)
        if int(r['knobs']['instance_index']) >= count:
            raise GenRefused('instance_index %d does not fit: %s has %d instance(s) bound on bridge %r (%s) — bind '
                             'another interface first, or pick 0..%d' % (r['knobs']['instance_index'], cls, count, bridge or '-',
                                                                         'no index at all' if count == 1 else '%d-bit index' % width
                                                                         if width else 'an explicit index', count - 1))
        hfn = '%s_packets.h' % cls.lower()
        open(os.path.join(project, hfn), 'w').write(text)
        order = prov.pop('tag_order', None) or _order_from_header(text, cls)
        orders[cls] = order
        class_rows.append(dict(prov, **{'class': cls, 'header': hfn, 'header_sha256': sha256(text), 'target': 'avr', 'msg_type': i + 1,
                                        'tag_order': order, 'wire': 2, 'bridge': bridge}))
    # brd-wire: the instance knob exists only for an indexed class (several boards bound on the bridge)
    open(os.path.join(project, 'board_config.h'), 'w').write(V.render_config(r, indexed=any(c.get('indexed') for c in class_rows)))
    viol = rule2_violations(project)
    if viol:
        raise GenRefused('RULE 2: a generated project holds only .c/.h/.v/.sv + Makefile/linker script — found %s' % viol)
    ssha = source_sha(project)
    now = datetime.datetime.now().isoformat(timespec='seconds')
    tfiles = [('template ' + fn, 'board/custom/firmware/uno/' + fn, os.path.join(tpl, fn)) for fn in TEMPLATE_FILES] \
        + [('template app %s (main.c)' % r['app'], 'board/custom/firmware/uno/apps/%s.c' % r['app'], app_src)]
    row = {'name': '%s-%s' % (r['name'], ssha[:12]), 'board_definition': board, 'state': 'generated', 'variant': r['name'],
           'classes_json': json.dumps(class_rows), 'template': 'board/custom/firmware/uno', 'source_sha': ssha,
           'header_sha256': compat.combined_sha(class_rows), 'tag_order_json': json.dumps(orders),
           'contract_hash_v2': class_rows[0]['hash_v2'] if len(class_rows) == 1 else sha256('\n'.join('%s:%s' % (c['class'], c['hash_v2']) for c in class_rows))[:16],
           'bridge_name': bridge, 'instance_index': int(r['knobs']['instance_index']),
           'artifact_sha256': '', 'engines_json': '{}', 'size_text': 0, 'size_data': 0, 'size_bss': 0, 'built_at': '',
           'flashed_to': '', 'flash_log': '', 'generated_at': now, 'hex_path': '',
           'repro_json': json.dumps({'inputs': [{'label': lab, 'path': p, 'sha256': sha256(open(fp, 'rb').read())} for lab, p, fp in tfiles]
                                    + [{'label': 'contract %s' % c['class'], 'path': c.get('path', c.get('url', '')), 'sha256': c.get('sha256', c['header_sha256'])} for c in class_rows],
                                    'knobs': dict(r['knobs'], variant=r['name'], app=r['app'], features=r['features'],
                                                  build_flags=['%s=%d' % f for f in r['flags']]),
                                    # brd-bo: where board_config.h's pin constants came from, and the board object's sha at gen time
                                    'board_object': {'board': board, 'board_sha': bsha, 'pins': pin_prov}}),
           'notes': 'generated (variant %s); `pol board build uno` compiles it' % r['name'], 'project_dir': project, 'work_dir': work}
    write_record(work, row)
    return row


def write_record(work, row):
    os.makedirs(work, exist_ok=True)
    json.dump(row, open(os.path.join(work, 'firmware_build.json'), 'w'), indent=1)


def read_record(work):
    p = os.path.join(work, 'firmware_build.json')
    if not os.path.isfile(p):
        raise GenRefused('no generated firmware in %s — run `pol board gen uno` first' % work)
    return json.load(open(p))


def store_dir(work, name):
    return os.path.join(work, 'builds', name)


def stored_builds(work):
    """Every built variant in the build store (newest first) — what the installer can put on a board."""
    root = os.path.join(work, 'builds')
    out = []
    if os.path.isdir(root):
        for name in os.listdir(root):
            try:
                out.append(read_record(os.path.join(root, name)))
            except GenRefused:
                continue
    return sorted(out, key=lambda r: r.get('built_at', ''), reverse=True)


def row_fields(row):
    """The FirmwareBuild constructor's fields only (the record carries a few local paths besides)."""
    import inspect
    from board.board_basis import FirmwareBuild
    names = set(inspect.signature(FirmwareBuild.__init__).parameters) - {'self', 'manager'}
    return {k: v for k, v in row.items() if k in names}


def main(argv):
    if argv and str(argv[0]).lower() in ('c3', 'esp32c3', 'esp32-c3'):   # sc-3: the ESP32-C3 template (ESP-IDF, FreeRTOS)
        from board.custom import gen_c3
        return gen_c3.main(argv)
    import argparse
    ap = argparse.ArgumentParser(prog='pol board gen')
    ap.add_argument('board')
    ap.add_argument('--variant', default='')
    ap.add_argument('--class', dest='classes', action='append')
    ap.add_argument('--out')
    ap.add_argument('--api', default='')
    ap.add_argument('--rig-name')
    ap.add_argument('--device-id', type=int)
    ap.add_argument('--u2x', type=int, dest='usart_u2x')
    ap.add_argument('--instance-index', type=int, dest='instance_index', help='brd-wire: this build\'s index among the bridge\'s bound instances')
    a = ap.parse_args(argv)
    try:
        row = gen(a.board, a.classes, a.out, a.api, variant=a.variant or None, rig_name=a.rig_name, device_id=a.device_id, usart_u2x=a.usart_u2x,
                  instance_index=a.instance_index)
    except GenRefused as e:
        print('[REFUSED] %s' % e)
        return 1
    cls = json.loads(row['classes_json'])
    print('[ OK ] %s  variant=%s  state=%s' % (row['name'], row['variant'], row['state']))
    print('       project  %s  (%s)' % (row['project_dir'], ', '.join(sorted(os.listdir(row['project_dir'])))))
    for c in cls:
        print('       header   %s  contract v%s hash %s  (%s)  sha256 %s' % (c['header'], c['contract_version'], c['contract_hash'], c['source'], c['header_sha256'][:16]))
        print('       wire v2  hash2 %s  index width %s bit(s)  bridge %s  instance %s' % (c.get('hash_v2'), c.get('index_width'), c.get('bridge') or '-', row['instance_index']))
        print('       wire     %s' % ', '.join(c['tag_order']))
    print('       next     pol board build %s' % a.board)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
