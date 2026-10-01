"""
@module board.custom.gen

`pol board gen uno --class SimRigState` (brd-1, plan §3 step 2): render a plain-C avr-libc project AROUND the generated
per-class header. The project is the template (`board/custom/firmware/uno/`: main.c, Makefile, board_config.h with the
person's knobs) + `<class>_packets.h` rendered with c_twin target=avr — fetched live from
`GET <api>/api/grpc/exposures/<class>/c-header?target=avr` when --api is given, else rendered here from the pinned
contract snapshot (custom/contracts/<class>.v<N>.json, which says what it pins). RULE 2 is checked on the result: a
generated project holds only .c/.h/.v/.sv + Makefile/linker script.

Layout of a work dir (default ~/.cache/polari-board/<board>/):
    project/              the buildable tree (nothing else lives in it — RULE 2)
    out/                  firmware.elf / firmware.hex after `pol board build`
    firmware_build.json   the FirmwareBuild row (state generated → built | refused → flashed), its repro block

    python3 -m board.custom.gen uno --class SimRigState [--out DIR] [--api URL] [--rig-name N] [--device-id N] [--u2x 0|1]
"""
import datetime
import hashlib
import json
import os
import re
import shutil
import ssl
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
MOD = os.path.dirname(HERE)
TEMPLATES = {'arduino-uno-r3': os.path.join(HERE, 'firmware', 'uno')}
TEMPLATE_FILES = ('main.c', 'Makefile')
ALIASES = {'uno': 'arduino-uno-r3', 'arduino-uno': 'arduino-uno-r3', 'arduino-uno-r3': 'arduino-uno-r3'}
#: the classes a template's main.c is written for (another class = a new template, brd-4)
TEMPLATE_CLASSES = {'arduino-uno-r3': ('SimRigState',)}
RULE2_EXT = ('.c', '.h', '.v', '.sv')
RULE2_NAMES = ('Makefile', 'link.ld')
CONTRACTS = os.path.join(HERE, 'contracts')
DEFAULT_KNOBS = {'rig_name': 'uno-rig', 'device_id': 3, 'usart_u2x': 1}


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
    for fn in sorted(os.listdir(CONTRACTS), reverse=True):
        if fn.startswith(cls + '.v') and fn.endswith('.json'):
            return json.load(open(os.path.join(CONTRACTS, fn))), os.path.join(CONTRACTS, fn)
    raise GenRefused('no pinned contract for %s — pass --api to fetch the live header' % cls)


def header(cls, api=''):
    """(text, provenance) of `<cls>_packets.h` with target=avr."""
    if api:
        url = '%s/api/grpc/exposures/%s/c-header?msg_type=1&target=avr' % (api.rstrip('/'), cls)
        from polariApiServer import outbound
        with outbound.http_request('self', 'board', 'GET', url, means='rest', timeout=30, lib='urllib', context=ssl._create_unverified_context()) as r:
            text = r.read().decode()
        m = re.search(r'contract v(\d+)\s+hash (\w*)', text)
        if '%s_MSG_TYPE' % cls.upper() not in text or 'target avr' not in text:
            raise GenRefused('the server returned no AVR header for %s (exposure enabled?)' % cls)
        return text, {'source': 'live', 'url': url, 'contract_version': int(m.group(1)) if m else 0, 'contract_hash': m.group(2) if m else ''}
    from grpcbridge.custom.c_twin import render_c_header
    c, path = pinned_contract(cls)
    text = render_c_header(cls, c['field_map'], c['msg_type'], version=c['contract_version'], contract_hash=c['contract_hash'], target='avr')
    return text, {'source': 'pinned', 'path': os.path.relpath(path, os.path.dirname(MOD)), 'sha256': sha256(open(path, 'rb').read()),
                  'contract_version': c['contract_version'], 'contract_hash': c['contract_hash']}


def render_config(knobs):
    return ('/* board_config.h — rendered by `pol board gen` (board.custom.gen); the knobs are also in the FirmwareBuild\n'
            ' * row\'s repro block. */\n#ifndef BOARD_CONFIG_H\n#define BOARD_CONFIG_H\n\n'
            '#define RIG_NAME  "%s"\n#define DEVICE_ID %du\n#define USART_U2X %d\n\n#endif /* BOARD_CONFIG_H */\n'
            % (knobs['rig_name'].replace('"', ''), int(knobs['device_id']), 1 if int(knobs['usart_u2x']) else 0))


def rule2_violations(project):
    return sorted(fn for fn in os.listdir(project) if not (fn.endswith(RULE2_EXT) or fn in RULE2_NAMES))


def source_sha(project):
    h = hashlib.sha256()
    for fn in sorted(os.listdir(project)):
        h.update(fn.encode() + b'\0' + open(os.path.join(project, fn), 'rb').read() + b'\0')
    return h.hexdigest()


def gen(board='uno', classes=('SimRigState',), work=None, api='', **knobs):
    board = board_name(board)
    classes = list(classes)
    bad = [c for c in classes if c not in TEMPLATE_CLASSES[board]]
    if bad:
        raise GenRefused('the %s template is written for %s; %s needs its own template (a generated header alone is not firmware)'
                         % (board, ', '.join(TEMPLATE_CLASSES[board]), ', '.join(bad)))
    k = dict(DEFAULT_KNOBS, **{a: b for a, b in knobs.items() if b is not None})
    work = work or default_work(board)
    project = os.path.join(work, 'project')
    if os.path.isdir(project):
        shutil.rmtree(project)
    shutil.rmtree(os.path.join(work, 'out'), ignore_errors=True)
    os.makedirs(project)
    tpl = TEMPLATES[board]
    for fn in TEMPLATE_FILES:
        shutil.copy(os.path.join(tpl, fn), os.path.join(project, fn))
    open(os.path.join(project, 'board_config.h'), 'w').write(render_config(k))
    class_rows = []
    for cls in classes:
        text, prov = header(cls, api)
        hfn = '%s_packets.h' % cls.lower()
        open(os.path.join(project, hfn), 'w').write(text)
        class_rows.append(dict(prov, **{'class': cls, 'header': hfn, 'header_sha256': sha256(text), 'target': 'avr'}))
    viol = rule2_violations(project)
    if viol:
        raise GenRefused('RULE 2: a generated project holds only .c/.h/.v/.sv + Makefile/linker script — found %s' % viol)
    ssha = source_sha(project)
    now = datetime.datetime.now().isoformat(timespec='seconds')
    row = {'name': '%s-%s' % (board, ssha[:12]), 'board_definition': board, 'state': 'generated',
           'classes_json': json.dumps(class_rows), 'template': 'board/custom/firmware/uno', 'source_sha': ssha,
           'artifact_sha256': '', 'engines_json': '{}', 'size_text': 0, 'size_data': 0, 'size_bss': 0, 'built_at': '',
           'flashed_to': '', 'flash_log': '', 'generated_at': now,
           'repro_json': json.dumps({'inputs': [{'label': 'template ' + fn, 'path': 'board/custom/firmware/uno/' + fn, 'sha256': sha256(open(os.path.join(tpl, fn), 'rb').read())} for fn in TEMPLATE_FILES]
                                    + [{'label': 'contract %s' % c['class'], 'path': c.get('path', c.get('url', '')), 'sha256': c.get('sha256', c['header_sha256'])} for c in class_rows],
                                    'knobs': k}),
           'notes': 'generated; `pol board build uno` compiles it', 'project_dir': project, 'work_dir': work}
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
    ap.add_argument('--class', dest='classes', action='append')
    ap.add_argument('--out')
    ap.add_argument('--api', default='')
    ap.add_argument('--rig-name')
    ap.add_argument('--device-id', type=int)
    ap.add_argument('--u2x', type=int, dest='usart_u2x')
    a = ap.parse_args(argv)
    try:
        row = gen(a.board, a.classes or ['SimRigState'], a.out, a.api, rig_name=a.rig_name, device_id=a.device_id, usart_u2x=a.usart_u2x)
    except GenRefused as e:
        print('[REFUSED] %s' % e)
        return 1
    cls = json.loads(row['classes_json'])
    print('[ OK ] %s  state=%s' % (row['name'], row['state']))
    print('       project  %s  (%s)' % (row['project_dir'], ', '.join(sorted(os.listdir(row['project_dir'])))))
    for c in cls:
        print('       header   %s  contract v%s hash %s  (%s)  sha256 %s' % (c['header'], c['contract_version'], c['contract_hash'], c['source'], c['header_sha256'][:16]))
    print('       next     pol board build %s' % a.board)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
