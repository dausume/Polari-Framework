"""
@module board.custom.build_c3

`pol board build c3` (sc-3): ONE ESP-IDF build of the generated C3 project through the engines ladder (engine `idf-build`
of the esp family: a local polari-idf-build, the prf-esp-engines image on this docker, or the ESP_ENGINES_URL worker).
The project goes over as a deterministic tar (sorted, mtime 0, uid/gid 0); back come the ELF, the three flashed images,
idf.py's flash_args, the merged 4 MB flash image the twin boots, `idf.py size --format json2` and the build's own cost.

Sizes (MEASURED, idf.py size json2) into the FirmwareBuild row, mapped onto the UNO's three columns and said so:
  size_text = Flash Code .text + the IRAM .text in DRAM (code)   size_data = DRAM .data + Flash Data (.rodata, .appdesc, …)
  size_bss  = DRAM .bss
  flash_bytes = app.bin as flashed      ram_bytes = DRAM used (.data + .bss + IRAM .text — the C3's DRAM/IRAM are one SRAM)
REFUSED past the app partition (partitions.csv: factory 0x100000 = 1 048 576 B — the template's own table) or past DRAM
total (idf.py size's own `total`). The artifact sha256 is the merged flash image's (what the twin boots; app.bin's is in
the repro block). CONFIG_APP_REPRODUCIBLE_BUILD=y (sdkconfig.defaults): the image carries no path, date or time.

A BUILD CACHE: a variant whose source sha AND engine image id match a stored build is not rebuilt (the record says
`cached`); `--force` rebuilds. Scenario campaigns run one binary many times — the cost rule.

    python3 -m board.custom.build_c3 c3 [--work DIR] [--force]
"""
import datetime
import hashlib
import io
import json
import os
import platform
import shutil
import sys
import tarfile

from board.custom import engine_run, gen, gen_c3

APP_PARTITION_BYTES = 0x100000   # partitions.csv `factory` (the template's own table — not a datasheet number)
OUT_FILES = ('firmware.elf', 'app.bin', 'bootloader.bin', 'partition-table.bin', 'flash_args.txt', 'flash_image.bin', 'size.json',
             'build.json', 'build.log')
ENGINE = 'idf-build'


def sha(b):
    return hashlib.sha256(b).hexdigest()


def project_tar(project):
    """A deterministic tar of the project (the same sources → the same bytes → the same input sha)."""
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode='w', format=tarfile.USTAR_FORMAT) as t:
        for rel in gen_c3.project_files(project):
            data = open(os.path.join(project, rel), 'rb').read()
            ti = tarfile.TarInfo('./' + rel)
            ti.size, ti.mtime, ti.mode, ti.uid, ti.gid, ti.uname, ti.gname = len(data), 0, 0o644, 0, 0, '', ''
            t.addfile(ti, io.BytesIO(data))
    return buf.getvalue()


def parse_size(js):
    """idf.py size --format json2 → the three columns + DRAM used/total (see the module docstring)."""
    d = json.loads(js) if isinstance(js, (str, bytes)) else js
    lay = {x['name']: x for x in d.get('layout', [])}
    part = lambda region, sec: int(((lay.get(region) or {}).get('parts') or {}).get(sec, {}).get('size', 0))  # noqa: E731
    dram = lay.get('DRAM') or {}
    fdata = sum(int(v.get('size', 0)) for v in ((lay.get('Flash Data') or {}).get('parts') or {}).values())
    return {'size_text': part('Flash Code', '.text') + part('DRAM', '.text'), 'size_data': part('DRAM', '.data') + fdata,
            'size_bss': part('DRAM', '.bss'), 'dram_used': int(dram.get('used', 0)), 'dram_total': int(dram.get('total', 0)),
            'flash_code': part('Flash Code', '.text'), 'flash_data': fdata, 'iram_text': part('DRAM', '.text'),
            'dram_data': part('DRAM', '.data'), 'dram_bss': part('DRAM', '.bss')}


def _image_id():
    from board.custom import board_engines as be
    return be.local_image('esp')


def cached(work, name, image_id):
    d = gen.store_dir(work, name)
    try:
        rec = gen.read_record(d)
    except gen.GenRefused:
        return None
    if rec.get('state') != 'built' or (image_id and rec.get('image_id') and rec['image_id'] != image_id):
        return None
    if not all(os.path.isfile(os.path.join(d, f)) for f in ('flash_image.bin', 'firmware.elf', 'size.json')):
        return None
    return rec


def build(board='c3', work=None, run=engine_run.run, force=False):
    work = work or gen_c3.default_work()
    row = gen.read_record(work)
    if row.get('board_definition') != gen_c3.BOARD:
        raise gen.GenRefused('the record in %s is a %s build — `pol board gen c3` first' % (work, row.get('board_definition')))
    image_id = _image_id()
    hit = None if force else cached(work, row['name'], image_id)
    if hit:
        hit = dict(hit, notes='cached: %s (same source sha + engine image) — `--force` rebuilds' % hit.get('notes', ''), cache='hit')
        _install_out(work, gen.store_dir(work, row['name']))
        gen.write_record(work, dict(hit, project_dir=row['project_dir'], work_dir=work))
        return hit
    project = row['project_dir']
    tar = project_tar(project)
    t0 = datetime.datetime.now()
    r = run(ENGINE, ['project.tar'], {'project.tar': tar}, timeout=1800)
    files = r.get('files') or {}
    bj = json.loads(files.get('build.json', b'{}') or b'{}')
    out = os.path.join(work, 'out')
    os.makedirs(out, exist_ok=True)
    for fn in OUT_FILES:
        if fn in files:
            open(os.path.join(out, fn), 'wb').write(files[fn])
    if not r.get('ok') or not bj.get('ok') or 'flash_image.bin' not in files:
        tail = (files.get('build.log') or b'').decode('utf-8', 'replace')[-1500:] or (r.get('stderr') or r.get('stdout') or '')[-1500:]
        row.update(state='refused', notes='idf.py build failed (rc %s): %s' % (r.get('returncode'), tail))
        gen.write_record(work, row)
        return row
    sizes = parse_size(files['size.json'])
    app_b = len(files['app.bin'])
    why = []
    if app_b > APP_PARTITION_BYTES:
        why.append('app.bin %d B > the factory partition %d B' % (app_b, APP_PARTITION_BYTES))
    if sizes['dram_total'] and sizes['dram_used'] > sizes['dram_total']:
        why.append('DRAM %d B > %d B' % (sizes['dram_used'], sizes['dram_total']))
    img = files['flash_image.bin']
    steps = {s['step']: s for s in bj.get('steps', [])}
    engines = {ENGINE: {'version': bj.get('idf_version', ''), 'how': r['how'], 'where': r['where'],
                        'toolchain': 'riscv32-esp-elf-gcc 14.2.0 (esp-14.2.0_20260121)', 'qemu': 'esp_develop_9.2.2_20260417'}}
    if r['how'] == 'local-image':
        engines['image'] = {'name': r['where'], 'id': image_id}
    repro = json.loads(row.get('repro_json') or '{}')
    repro.update({
        'inputs': repro.get('inputs', []) + [{'label': 'project ' + f, 'path': 'project/' + f, 'sha256': sha(open(os.path.join(project, f), 'rb').read())}
                                             for f in gen_c3.project_files(project)] + [{'label': 'project.tar (what the engine got)', 'sha256': sha(tar)}],
        'tools': engines, 'conditions': {'target': 'esp32c3', 'sdkconfig_defaults': 'project/sdkconfig.defaults (in inputs)',
                                         'limits': {'app_partition_b': APP_PARTITION_BYTES, 'dram_total_b': sizes['dram_total'],
                                                    'cited': 'partitions.csv (the template) / idf.py size json2 total'}},
        'generated_files': [{'path': 'out/' + f, 'sha256': bj.get('sha256', {}).get(f) or sha(files[f]), 'bytes': len(files[f])}
                            for f in ('flash_image.bin', 'app.bin', 'bootloader.bin', 'partition-table.bin', 'firmware.elf') if f in files],
        'seeds': {'deterministic': True, 'why': 'CONFIG_APP_REPRODUCIBLE_BUILD=y: no paths, dates or times in the image; the same sources, '
                                                'knobs and engine image give the same bytes (the selftest re-checks two builds)'},
        'recorded_at': datetime.datetime.now().isoformat(timespec='seconds'), 'host': {'node': platform.node(), 'machine': platform.machine()},
        'how_to_rerun': 'pol board gen c3 --variant %s && pol board build c3 --force' % row.get('variant'),
        'cost': {'build': steps.get('build'), 'size': steps.get('size'), 'merge_bin': steps.get('merge_bin'), 'engine': r.get('cost')},
        'rule': 'every result carries the initial conditions and seeds that produced it (2026-09-26)'})
    row.update(size_text=sizes['size_text'], size_data=sizes['size_data'], size_bss=sizes['size_bss'], flash_bytes=app_b, ram_bytes=sizes['dram_used'],
               sizes=sizes, engines_json=json.dumps(engines), repro_json=json.dumps(repro), built_at=t0.isoformat(timespec='seconds'),
               artifact_sha256='' if why else sha(img), app_sha256=sha(files['app.bin']), image_id=image_id, cache='miss',
               build_cost=steps.get('build', {}), state='refused' if why else 'built',
               notes=('REFUSED: %s' % '; '.join(why)) if why else 'app %d / %d B, DRAM %d / %d B (stack: FreeRTOS task stacks are in .bss/heap)'
               % (app_b, APP_PARTITION_BYTES, sizes['dram_used'], sizes['dram_total']),
               hex_path='' if why else os.path.join(out, 'flash_image.bin'), image_path='' if why else os.path.join(out, 'flash_image.bin'))
    gen.write_record(work, row)
    if not why:
        store(work, row)
    return row


def _install_out(work, d):
    out = os.path.join(work, 'out')
    os.makedirs(out, exist_ok=True)
    for fn in OUT_FILES:
        if os.path.isfile(os.path.join(d, fn)):
            shutil.copy(os.path.join(d, fn), os.path.join(out, fn))


def store(work, row):
    d = gen.store_dir(work, row['name'])
    os.makedirs(d, exist_ok=True)
    for fn in OUT_FILES:
        p = os.path.join(work, 'out', fn)
        if os.path.isfile(p):
            shutil.copy(p, os.path.join(d, fn))
    rec = dict(row, hex_path=os.path.join(d, 'flash_image.bin'), image_path=os.path.join(d, 'flash_image.bin'), store_dir=d)
    gen.write_record(d, rec)
    return rec


def main(argv):
    import argparse
    ap = argparse.ArgumentParser(prog='pol board build c3')
    ap.add_argument('board')
    ap.add_argument('--work')
    ap.add_argument('--force', action='store_true')
    a = ap.parse_args(argv)
    try:
        row = build(a.board, a.work, force=a.force)
    except (gen.GenRefused, engine_run.EngineRefused) as e:
        print('[REFUSED] %s' % e)
        return 1
    tag = '[ OK ]' if row['state'] == 'built' else '[REFUSED]'
    print('%s %s  state=%s%s' % (tag, row['name'], row['state'], '  (cached)' if row.get('cache') == 'hit' else ''))
    print('       %s' % row['notes'][-600:])
    if row['state'] == 'built':
        s = row.get('sizes') or {}
        print('       idf.py size  flash code %s  flash data %s  IRAM .text %s  DRAM .data %s  .bss %s  (DRAM %s / %s B)' % (
            s.get('flash_code'), s.get('flash_data'), s.get('iram_text'), s.get('dram_data'), s.get('dram_bss'), s.get('dram_used'), s.get('dram_total')))
        print('       image        %s  sha256 %s' % (row['image_path'], row['artifact_sha256']))
        bc = row.get('build_cost') or {}
        if bc:
            print('       build cost   %.1f s wall · %.1f CPU-s · peak RSS %.1f MB (the largest process)' % (bc.get('wall_s', 0), bc.get('cpu_s', 0), bc.get('peak_rss_mb', 0)))
        print('       next         pol board flash c3   (DRY-RUN)   ·   pol board twin c3 up')
    return 0 if row['state'] == 'built' else 1


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
