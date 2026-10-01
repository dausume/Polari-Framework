"""
@module board.custom.build

`pol board build uno` (brd-1, plan §3 step 3): avr-gcc + avr-objcopy + avr-size on the generated project, each through
the engines ladder (custom/engine_run.py: a local avr-gcc, the prf-board-engines image, or the remote worker). The
sizes are MEASURED (avr-size -A: .text/.data/.bss) into the FirmwareBuild row; the build is REFUSED past the UNO's
cited limits — flash (.text + .data) > 32256 B, static RAM (.data + .bss) > 2048 B (boards.txt upload.maximum_size /
maximum_data_size, DatasheetFact rows). The row carries the .hex sha256, the engine versions + where they ran and the
image id, and a repro block (inputs by sha256, knobs, tools, cost; the build is deterministic).

    python3 -m board.custom.build uno [--work DIR]
"""
import datetime
import hashlib
import json
import os
import platform
import re
import sys

from board.custom import engine_run, gen

MCU = 'atmega328p'
F_CPU = '16000000UL'
#: the SAME flags as firmware/uno/Makefile (the selftest asserts it)
CFLAGS = ['-mmcu=%s' % MCU, '-DF_CPU=%s' % F_CPU, '-Os', '-std=gnu99', '-Wall', '-Wextra', '-Werror', '-ffunction-sections', '-fdata-sections']
LDFLAGS = ['-Wl,--gc-sections']
ENGINES_USED = ('avr-gcc', 'avr-objcopy', 'avr-size')


def limits(board):
    """(flash bytes, ram bytes, citation) from the board's cited facts — never a literal here."""
    from board.custom.uno_facts import SEED_UNO_FACTS
    f = {x['fact_key']: x for x in SEED_UNO_FACTS if x['board'] == board}
    return int(f['upload.maximum_size']['value']), int(f['upload.maximum_data_size']['value']), \
        '%s / %s' % (f['upload.maximum_size']['url'], f['upload.maximum_data_size']['url'])


def parse_size_A(text):
    """avr-size -A (SysV) → {'.text': n, '.data': n, '.bss': n}. Berkeley (-B) is not used: binutils 2.43 folds .data
    into its `text` column for AVR, which would hide the RAM .data takes."""
    out = {}
    for line in text.splitlines():
        m = re.match(r'^(\.\w+)\s+(\d+)\s+\d+', line.strip())
        if m:
            out[m.group(1)] = int(m.group(2))
    return out


def check_limits(sizes, flash_max, ram_max):
    flash = sizes.get('.text', 0) + sizes.get('.data', 0)
    ram = sizes.get('.data', 0) + sizes.get('.bss', 0)
    why = []
    if flash > flash_max:
        why.append('flash %d B > %d B' % (flash, flash_max))
    if ram > ram_max:
        why.append('static RAM %d B > %d B' % (ram, ram_max))
    return flash, ram, why


def _fail(row, work, stage, res):
    row.update(state='refused', notes='%s failed (rc %s): %s' % (stage, res.get('returncode'), (res.get('stderr') or res.get('stdout') or '')[-1500:]))
    gen.write_record(work, row)
    return row


def build(board='uno', work=None, run=engine_run.run):
    board = gen.board_name(board)
    work = work or gen.default_work(board)
    row = gen.read_record(work)
    project = row['project_dir']
    files = {fn: open(os.path.join(project, fn), 'rb').read() for fn in sorted(os.listdir(project)) if fn.endswith(('.c', '.h'))}
    t0 = datetime.datetime.now()
    calls = {}
    r = run('avr-gcc', CFLAGS + LDFLAGS + ['-o', 'firmware.elf', 'main.c'], files)
    calls['avr-gcc'] = r
    if not r['ok'] or 'firmware.elf' not in r['files']:
        return _fail(row, work, 'avr-gcc', r)
    elf = r['files']['firmware.elf']
    r = run('avr-objcopy', ['-O', 'ihex', '-R', '.eeprom', 'firmware.elf', 'firmware.hex'], {'firmware.elf': elf})
    calls['avr-objcopy'] = r
    if not r['ok'] or 'firmware.hex' not in r['files']:
        return _fail(row, work, 'avr-objcopy', r)
    hexdata = r['files']['firmware.hex']
    r = run('avr-size', ['-A', 'firmware.elf'], {'firmware.elf': elf})
    calls['avr-size'] = r
    if not r['ok']:
        return _fail(row, work, 'avr-size', r)
    sizes = parse_size_A(r['stdout'])
    flash_max, ram_max, cite = limits(board)
    flash, ram, why = check_limits(sizes, flash_max, ram_max)
    out = os.path.join(work, 'out')
    os.makedirs(out, exist_ok=True)
    open(os.path.join(out, 'firmware.elf'), 'wb').write(elf)
    hex_path = os.path.join(out, 'firmware.hex')
    if why:   # a refused build leaves no flashable artefact behind
        if os.path.exists(hex_path):
            os.remove(hex_path)
    else:
        open(hex_path, 'wb').write(hexdata)
    engines = {}
    for e in ENGINES_USED:
        engines[e] = {'version': engine_run.version(e), 'how': calls[e]['how'], 'where': calls[e]['where']}
    try:
        from board.custom.board_engines import local_image, image_name
        if any(v['how'] == 'local-image' for v in engines.values()):
            engines['image'] = {'name': image_name(), 'id': local_image()}
    except Exception:
        pass
    cost = {e: calls[e].get('cost', {}) for e in ENGINES_USED}
    repro = json.loads(row.get('repro_json') or '{}')
    repro.update({
        'inputs': repro.get('inputs', []) + [{'label': 'project ' + fn, 'path': 'project/' + fn, 'sha256': hashlib.sha256(d).hexdigest()} for fn, d in files.items()],
        'tools': engines, 'conditions': {'mcu': MCU, 'f_cpu': F_CPU, 'cflags': CFLAGS, 'ldflags': LDFLAGS, 'limits': {'flash_b': flash_max, 'ram_b': ram_max, 'cited': cite}},
        'generated_files': [{'path': 'out/firmware.hex', 'sha256': hashlib.sha256(hexdata).hexdigest(), 'bytes': len(hexdata)},
                            {'path': 'out/firmware.elf', 'sha256': hashlib.sha256(elf).hexdigest(), 'bytes': len(elf)}],
        'seeds': {'deterministic': True, 'why': 'avr-gcc/objcopy are deterministic on identical inputs, flags and versions (no timestamps in the .hex)'},
        'recorded_at': datetime.datetime.now().isoformat(timespec='seconds'),
        'host': {'node': platform.node(), 'machine': platform.machine()},
        'how_to_rerun': 'pol board gen uno (same knobs) && pol board build uno', 'cost': cost,
        'rule': 'every result carries the initial conditions and seeds that produced it (2026-09-26)'})
    row.update(size_text=sizes.get('.text', 0), size_data=sizes.get('.data', 0), size_bss=sizes.get('.bss', 0),
               engines_json=json.dumps(engines), repro_json=json.dumps(repro), built_at=t0.isoformat(timespec='seconds'),
               artifact_sha256='' if why else hashlib.sha256(hexdata).hexdigest(), flash_bytes=flash, ram_bytes=ram,
               state='refused' if why else 'built',
               notes=('REFUSED: %s (the UNO\'s cited limits)' % '; '.join(why)) if why else
               'flash %d / %d B, static RAM %d / %d B (stack not counted)' % (flash, flash_max, ram, ram_max),
               hex_path='' if why else hex_path)
    gen.write_record(work, row)
    return row


def main(argv):
    import argparse
    ap = argparse.ArgumentParser(prog='pol board build')
    ap.add_argument('board')
    ap.add_argument('--work')
    a = ap.parse_args(argv)
    try:
        row = build(a.board, a.work)
    except (gen.GenRefused, engine_run.EngineRefused) as e:
        print('[REFUSED] %s' % e)
        return 1
    tag = '[ OK ]' if row['state'] == 'built' else '[REFUSED]'
    print('%s %s  state=%s' % (tag, row['name'], row['state']))
    print('       %s' % row['notes'])
    if row['state'] == 'built':
        print('       avr-size  .text %d  .data %d  .bss %d' % (row['size_text'], row['size_data'], row['size_bss']))
        print('       hex       %s  sha256 %s' % (row['hex_path'], row['artifact_sha256']))
        for e, v in json.loads(row['engines_json']).items():
            print('       %-11s %s' % (e, v.get('version') or v.get('id', '')) + ('  [%s]' % v['how'] if 'how' in v else ''))
        print('       next      pol board flash uno   (DRY-RUN)   ·   pol board twin uno up')
    return 0 if row['state'] == 'built' else 1


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
