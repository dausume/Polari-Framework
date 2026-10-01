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

brd-fi: the FirmwareBuild row also carries `header_sha256` + `tag_order_json` (per class, the wire order) captured HERE,
so the installer can judge compatibility on what the board will actually speak (board.custom.compat) — never on
contract_hash alone (brd-1's finding: v1/v2 share a hash yet differ in order).

Layout of a work dir (default ~/.cache/polari-board/<board>/):
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
    if not b:
        raise GenRefused('no firmware template for %r — only the UNO is picked (plan §8a); every other device is a Road' % alias)
    return b


def default_work(board):
    return os.path.expanduser(os.path.join(os.environ.get('POLARI_BOARD_HOME', '~/.cache/polari-board'), board))


def pinned_contract(cls):
    c, path = compat.pinned_contract(cls)
    if c is None:
        raise GenRefused('no pinned contract for %s — pass --api to fetch the live header' % cls)
    return c, path


def header(cls, api='', msg_type=1, manager=None):
    """(text, provenance) of `<cls>_packets.h` with target=avr."""
    if api:
        url = '%s/api/grpc/exposures/%s/c-header?msg_type=%d&target=avr' % (api.rstrip('/'), cls, int(msg_type))
        from polariApiServer import outbound
        with outbound.http_request('self', 'board', 'GET', url, means='rest', timeout=30, lib='urllib', context=ssl._create_unverified_context()) as r:
            text = r.read().decode()
        m = re.search(r'contract v(\d+)\s+hash (\w*)', text)
        if '%s_MSG_TYPE' % cls.upper() not in text or 'target avr' not in text:
            raise GenRefused('the server returned no AVR header for %s (exposure enabled?)' % cls)
        return text, {'source': 'live', 'url': url, 'contract_version': int(m.group(1)) if m else 0, 'contract_hash': m.group(2) if m else '',
                      'tag_order': _order_from_header(text, cls)}
    if manager is not None:
        now = compat.server_header(manager, cls, msg_type, 'avr')
        if now is None:
            raise GenRefused('this server knows no contract for %s (no gRPC exposure, no pinned snapshot)' % cls)
        prov = {k: now[k] for k in ('source', 'contract_version', 'contract_hash', 'tag_order', 'where') if k in now}
        prov.update({k: now[k] for k in ('path', 'sha256') if k in now})
        if now['source'] == 'live':
            prov['url'] = 'in-process: %s' % now['where']
        return now['text'], prov
    from grpcbridge.custom.c_twin import render_c_header
    c, path = pinned_contract(cls)
    text = render_c_header(cls, c['field_map'], int(msg_type), version=c['contract_version'], contract_hash=c['contract_hash'], target='avr')
    return text, {'source': 'pinned', 'path': os.path.relpath(path, os.path.dirname(MOD)), 'sha256': sha256(open(path, 'rb').read()),
                  'contract_version': c['contract_version'], 'contract_hash': c['contract_hash'], 'tag_order': compat.tag_order(c['field_map'])}


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


def gen(board='uno', classes=None, work=None, api='', variant=None, manager=None, variant_rows=None, **knobs):
    board = board_name(board)
    v = pick_variant(list(classes or []), variant, variant_rows)
    try:
        r = V.resolve(v, {a: b for a, b in knobs.items() if b is not None})
    except V.VariantRefused as e:
        raise GenRefused(str(e))
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
    open(os.path.join(project, 'board_config.h'), 'w').write(V.render_config(r))
    class_rows, orders = [], {}
    for i, cls in enumerate(r['classes']):
        text, prov = header(cls, api, i + 1, manager)
        hfn = '%s_packets.h' % cls.lower()
        open(os.path.join(project, hfn), 'w').write(text)
        order = prov.pop('tag_order', None) or _order_from_header(text, cls)
        orders[cls] = order
        class_rows.append(dict(prov, **{'class': cls, 'header': hfn, 'header_sha256': sha256(text), 'target': 'avr', 'msg_type': i + 1,
                                        'tag_order': order}))
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
           'artifact_sha256': '', 'engines_json': '{}', 'size_text': 0, 'size_data': 0, 'size_bss': 0, 'built_at': '',
           'flashed_to': '', 'flash_log': '', 'generated_at': now, 'hex_path': '',
           'repro_json': json.dumps({'inputs': [{'label': lab, 'path': p, 'sha256': sha256(open(fp, 'rb').read())} for lab, p, fp in tfiles]
                                    + [{'label': 'contract %s' % c['class'], 'path': c.get('path', c.get('url', '')), 'sha256': c.get('sha256', c['header_sha256'])} for c in class_rows],
                                    'knobs': dict(r['knobs'], variant=r['name'], app=r['app'], features=r['features'],
                                                  build_flags=['%s=%d' % f for f in r['flags']])}),
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
    a = ap.parse_args(argv)
    try:
        row = gen(a.board, a.classes, a.out, a.api, variant=a.variant or None, rig_name=a.rig_name, device_id=a.device_id, usart_u2x=a.usart_u2x)
    except GenRefused as e:
        print('[REFUSED] %s' % e)
        return 1
    cls = json.loads(row['classes_json'])
    print('[ OK ] %s  variant=%s  state=%s' % (row['name'], row['variant'], row['state']))
    print('       project  %s  (%s)' % (row['project_dir'], ', '.join(sorted(os.listdir(row['project_dir'])))))
    for c in cls:
        print('       header   %s  contract v%s hash %s  (%s)  sha256 %s' % (c['header'], c['contract_version'], c['contract_hash'], c['source'], c['header_sha256'][:16]))
        print('       wire     %s' % ', '.join(c['tag_order']))
    print('       next     pol board build %s' % a.board)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
