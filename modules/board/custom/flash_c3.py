"""
@module board.custom.flash_c3

`pol board flash c3` (sc-3). The argv is RENDERED from the ProgrammerKind row `esptool`
(`esptool.py --chip {chip} --port {port} --baud {baud} write_flash {offset} {artifact}`) and idf.py's OWN flash_args
(the flash mode/frequency/size flags, then every (offset, file) pair — bootloader 0x0, partition table 0x8000, app 0x10000
for this template), never typed here: {offset} {artifact} expands to the flags followed by the pairs, sorted by offset.
baud 460800 = idf.py flash's default (ESP-IDF v5.5.5 tools/idf_py_actions/serial_ext.py line 36: 'default': 460800, read in the image).

  DRY-RUN (the default): prints the exact argv; nothing is opened.
  REAL:    needs a detected esp32-c3 BoardInstance (board present, a port) AND --yes — the C3's USB VID:PID is not in the
           register yet, so detection cannot name one until it is captured on first plug (its road step). esptool runs on
           THIS host only (the ladder refuses a remote worker for a flash); only a run that exits 0 AND prints esptool's
           "Hash of data verified" once per image stamps the build flashed.

    python3 -m board.custom.flash_c3 c3 [--work DIR] [--port P] [--yes]
"""
import datetime
import os
import re
import sys

from board.custom import engine_run, flash as F, gen, gen_c3
from board.custom.programmers import render_dry_run

PROGRAMMER = 'esptool'
CHIP = 'esp32c3'
BAUD = 460800
NAMES = {'bootloader/bootloader.bin': 'bootloader.bin', 'partition_table/partition-table.bin': 'partition-table.bin',
         'polari_c3.bin': 'app.bin'}
VERIFIED_RE = re.compile(r'Hash of data verified', re.I)


def parse_flash_args(text):
    """idf.py's flash_args → (flags list, [(offset int, stored file name)])."""
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    flags = lines[0].split() if lines and lines[0].startswith('--') else []
    pairs = []
    for ln in lines[1 if flags else 0:]:
        off, path = ln.split(None, 1)
        pairs.append((int(off, 0), NAMES.get(path, os.path.basename(path))))
    return flags, sorted(pairs)


def argv_for(port, store, flash_args_text):
    flags, pairs = parse_flash_args(flash_args_text)
    offset = ' '.join(flags + ['0x%x' % pairs[0][0]])
    artifact = ' '.join([os.path.join(store, pairs[0][1])] + ['0x%x %s' % (o, os.path.join(store, f)) for o, f in pairs[1:]])
    return render_dry_run(PROGRAMMER, chip=CHIP, port=port, baud=BAUD, offset=offset, artifact=artifact).split()


def plan(work=None, port='', instance=None):
    work = work or gen_c3.default_work()
    row = gen.read_record(work)
    if row.get('board_definition') != gen_c3.BOARD or row.get('state') not in ('built', 'flashed'):
        raise F.FlashRefused('the firmware in %s is %r (%s), not a built C3 image — `pol board build c3` first' % (work, row.get('state'), row.get('board_definition')))
    store = row.get('store_dir') or gen.store_dir(work, row['name'])
    fa = os.path.join(store, 'flash_args.txt')
    if not os.path.isfile(fa):
        raise F.FlashRefused('no flash_args.txt beside the build (%s) — rebuild with `pol board build c3 --force`' % store)
    port = port or (instance or {}).get('by_id_path') or (instance or {}).get('port') or '{port}'
    argv = argv_for(port, store, open(fa).read())
    from board.custom import board_engines as be
    return {'board': gen_c3.BOARD, 'work': work, 'row': row, 'argv': argv, 'text': ' '.join(argv), 'port': port, 'store': store,
            'engine': be.resolve('esptool', flash=True), 'image_sha256': row.get('artifact_sha256', ''), 'app_sha256': row.get('app_sha256', '')}


def flash(work=None, port='', yes=False, instance=None, instances=None, run=engine_run.run, now=None):
    if instance is None and yes:
        instance = F.find_instance(gen_c3.BOARD, instances)
    p = plan(work, port, instance)
    if not yes:
        return dict(p, dry_run=True, why='DRY-RUN (the default): nothing was opened; a real flash needs the C3 detected on this host AND --yes')
    if instance is None:
        raise F.FlashRefused('--yes, but no esp32-c3 is detected on this host (pol board detect) — its USB VID:PID is captured on first plug')
    if p['engine']['how'] == 'refused':
        raise F.FlashRefused(p['engine']['why'])
    inner = F.INNER_PORT if p['engine']['how'] == 'local-image' else p['port']
    flags, pairs = parse_flash_args(open(os.path.join(p['store'], 'flash_args.txt')).read())
    files = {f: open(os.path.join(p['store'], f), 'rb').read() for _, f in pairs}
    args = ['--chip', CHIP, '--port', inner, '--baud', str(BAUD), 'write_flash'] + flags + [x for o, f in pairs for x in ('0x%x' % o, f)]
    devices = [(os.path.realpath(p['port']), F.INNER_PORT)] if p['engine']['how'] == 'local-image' else ()
    r = run('esptool', args, files, flash=True, devices=devices, timeout=300)
    log = (r.get('stdout') or '') + (r.get('stderr') or '')
    ok = r.get('ok') and len(VERIFIED_RE.findall(log)) >= len(pairs)
    row = p['row']
    stamp = (now or datetime.datetime.now()).isoformat(timespec='seconds')
    if not ok:
        row.update(flash_log=log[-4000:], notes='flash FAILED (rc %s; %d of %d images hash-verified) — nothing stamped'
                   % (r.get('returncode'), len(VERIFIED_RE.findall(log)), len(pairs)))
        gen.write_record(p['work'], row)
        raise F.FlashRefused(row['notes'] + '\n' + log[-1500:])
    row.update(state='flashed', flashed_to=instance.get('name', ''), flash_log=log[-4000:],
               notes='flashed %s; esptool verified the hash of all %d images' % (stamp, len(pairs)))
    gen.write_record(p['work'], row)
    return dict(p, dry_run=False, instance=instance, log=log)


def main(argv):
    import argparse
    ap = argparse.ArgumentParser(prog='pol board flash c3')
    ap.add_argument('board')
    ap.add_argument('--work')
    ap.add_argument('--port', default='')
    ap.add_argument('--yes', action='store_true')
    a = ap.parse_args(argv)
    try:
        res = flash(a.work, a.port, a.yes)
    except (gen.GenRefused, F.FlashRefused, engine_run.EngineRefused) as e:
        print('[REFUSED] %s' % e)
        return 1
    if res['dry_run']:
        print('[DRY-RUN] %s' % res['text'])
        print('          engine: esptool %s (%s)' % (res['engine']['how'], res['engine']['where'] or res['engine']['why']))
        print('          merged image sha256 %s · app.bin sha256 %s' % (res['image_sha256'], res['app_sha256']))
        print('          %s' % res['why'])
        return 0
    print('[ OK ] flashed %s → %s; every image hash-verified by esptool' % (res['row']['name'], res['port']))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
