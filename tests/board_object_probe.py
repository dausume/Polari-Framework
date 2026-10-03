"""brd-bo PROBE — THE BOARD OBJECT's builds, for real, through the engine WORKERS (his rule 2026-10-03: across devices — no engine
worker and no twin on the editing box; the workers run on isle-core):

  BOARD_ENGINES_URL=http://<isle-core>:9830  every UNO variant generated with board_config.h's pin constants FROM BoardPin rows →
                                             avr-gcc on the worker → each .hex byte-identical to dev-hn-0's (the fixture
                                             custom/fixtures/brd_bo_baseline.json; uno-sim-rig-ring512 refused by design, as then);
                                             + the FLIP: uno-sim-rig from rows with PWM_LED moved to D5 builds (PWM_PIN 5, a different
                                             .hex — the rows reached the firmware)
  ESP_ENGINES_URL=http://<isle-core>:9850    c3-sim-rig with main/board_pins.h + sdkconfig.defaults' board lines generated from the rows →
                                             idf.py on the worker → the merged image, app.bin and ELF byte-identical to dev-hn-0's

Each worker's /capability is asked first; a worker that does not answer is SKIPPED and said so (never a local fallback). The twins
(avr-twin, c3-run) refuse a remote rung by design (a long-lived local process) — not run here; owed: "twin on a remote worker".

    cd polari-framework && BOARD_ENGINES_URL=… ESP_ENGINES_URL=… PYTHONPATH=.:modules python3 tests/board_object_probe.py [--no-c3]
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

FW = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [FW, os.path.join(FW, 'modules')]
FIX = json.load(open(os.path.join(FW, 'modules', 'board', 'custom', 'fixtures', 'brd_bo_baseline.json')))
results = []


def check(label, cond, extra=''):
    results.append(bool(cond))
    print(('PASS' if cond else 'FAIL') + ': ' + label + (('  [%s]' % extra) if extra and not cond else ''), flush=True)


def capability(knob):
    url = os.environ.get(knob, '')
    if not url:
        return None, '%s is not set' % knob
    try:
        from polariApiServer import outbound
        with outbound.http_request('engine', 'board', 'GET', url.rstrip('/') + '/capability', means='rest', timeout=10, lib='urllib') as r:
            d = json.load(r)
        return d, ''
    except Exception as e:  # noqa: BLE001 — a worker down is a skip, said
        return None, '%s (%s) did not answer /capability: %s' % (knob, url, e)


def free_m():
    try:
        return subprocess.run(['free', '-m'], capture_output=True, text=True, timeout=10).stdout.splitlines()[1]
    except Exception:  # noqa: BLE001
        return '?'


def uno(tmp):
    from board.custom import board_object as bo, build, gen, variants as V
    from firmwarefaults.custom.scenarios import scenario_variants
    rows = V.SEED_FIRMWARE_VARIANTS + scenario_variants()
    base = FIX['uno']
    same, built, refused, where = 0, 0, [], set()
    t0 = time.time()
    for name, kn in [(v['name'], {}) for v in rows] + [('uno-pair', {'instance_index': 1})]:
        key = name + ('#1' if kn else '')
        work = os.path.join(tmp, 'uno', key.replace('#', '_'))
        gen.gen('uno', None, work, variant=name, variant_rows=rows, **kn)
        b = build.build('uno', work)
        want = base[key]['hex_sha256']
        if b['state'] == 'built':
            built += 1
            where.add(json.loads(b['engines_json'])['avr-gcc']['where'])
            same += b['artifact_sha256'] == want
            print('       %-24s %s  %s' % (key, b['artifact_sha256'][:16], 'byte-identical' if b['artifact_sha256'] == want else 'DIFFERS from %s' % want[:16]), flush=True)
        else:
            refused.append(key)
            print('       %-24s refused (%s)' % (key, b['notes'][:90]), flush=True)
    check('UNO: %d variants built on %s, every .hex byte-identical to dev-hn-0\'s (%d/%d); refused as before: %s (%.0f s)'
          % (built, ', '.join(sorted(where)), same, built, refused, time.time() - t0),
          built == 16 and same == 16 and refused == ['uno-sim-rig-ring512'] and where == {os.environ['BOARD_ENGINES_URL']})
    r2, touched = bo.assign(bo.rows_for('uno'), 'PWM_LED', 'D5')
    work = os.path.join(tmp, 'uno', 'flip')
    row = gen.gen('uno', None, work, variant='uno-sim-rig', board_tables=bo.to_tables(r2, bo.seed_tables()))
    cfg = open(os.path.join(row['project_dir'], 'board_config.h')).read()
    b = build.build('uno', work)
    check('THE FLIP reaches the firmware: PWM_LED → D5 in the rows → board_config.h PWM_PIN 5 → built on the worker, a different .hex (%s, flash %s B)'
          % (b.get('artifact_sha256', '')[:16], b.get('flash_bytes')),
          '#define PWM_PIN      5' in cfg and b['state'] == 'built' and b['artifact_sha256'] != FIX['uno']['uno-sim-rig']['hex_sha256'])


def c3(tmp):
    from board.custom import build_c3, gen_c3
    work = os.path.join(tmp, 'c3')
    t0 = time.time()
    row = gen_c3.gen_c3('c3-sim-rig', work)
    prov = json.loads(row['repro_json'])['board_object']
    b = build_c3.build('c3', work, force=True)
    base = FIX['c3']['c3-sim-rig']
    elf = next((g['sha256'] for g in json.loads(b.get('repro_json') or '{}').get('generated_files', []) if g['path'] == 'out/firmware.elf'), '')
    where = json.loads(b.get('engines_json') or '{}').get('idf-build', {}).get('where', '')
    print('       image %s  app %s  elf %s  (%s, %.0f s; build %s)' % (b.get('artifact_sha256', '')[:16], b.get('app_sha256', '')[:16], elf[:16], where,
                                                                      time.time() - t0, b.get('build_cost')), flush=True)
    check('C3: c3-sim-rig built on %s from main/board_pins.h + sdkconfig board lines GENERATED from the rows (board sha %s) — merged image, app.bin and ELF '
          'byte-identical to dev-hn-0\'s (%s…)' % (where, prov['board_sha'][:12], base['image_sha256'][:16]),
          b['state'] == 'built' and b['artifact_sha256'] == base['image_sha256'] and b['app_sha256'] == base['app_sha256'] and elf == base['elf_sha256']
          and where == os.environ['ESP_ENGINES_URL'])


def main():
    print('free -m before: %s' % free_m())
    tmp = tempfile.mkdtemp(prefix='brdbo-probe-')
    try:
        cap, why = capability('BOARD_ENGINES_URL')
        if cap is None:
            print('SKIP: the UNO builds — %s' % why)
        else:
            print('       board worker: %s (%s)' % (cap.get('worker'), os.environ['BOARD_ENGINES_URL']))
            uno(tmp)
        if '--no-c3' in sys.argv:
            print('SKIP: the C3 build (--no-c3)')
        else:
            cap, why = capability('ESP_ENGINES_URL')
            if cap is None:
                print('SKIP: the C3 build — %s' % why)
            else:
                print('       esp worker: %s (%s)' % (cap.get('worker'), os.environ['ESP_ENGINES_URL']))
                c3(tmp)
        print('NOT RUN (owed): the twins — avr-twin / c3-run refuse a remote rung by design; "twin on a remote worker" is owed')
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print('free -m after:  %s' % free_m())
    print('\n%d/%d checks passed' % (sum(results), len(results)))
    return 0 if results and all(results) else 1


if __name__ == '__main__':
    sys.exit(main())
