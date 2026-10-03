"""
@module board.custom.sim_cost_c3

THE C3 TWIN'S COST (sc-3; plan §8a: measure a twin before relying on it). One simulated ESP32-C3 costs:

  rows      per device: BoardDefinition, Road, its board-roads TechNode, the ProgrammerKind (esptool), its DatasheetFacts
            (none yet); per simulated board the same run-time rows as the UNO (board.custom.sim_cost.RUN_ROWS)
  state     QEMU has no core-state probe like simavr's --state-size: the state is the emulator process's PEAK RSS (wait4 on
            qemu-system-riscv32), beside the guest's own memory (the 4 MiB flash image it boots)
  speed     a scenario image run with -icount 3 (sleep=off): virtual seconds (the firmware's own esp_timer at @END) per wall
            second = the wall-time ratio; virtual instructions per second = virtual ns / 2^3 per wall second

    python3 -m board.custom.sim_cost_c3 [--work DIR] [--write]     # needs a built SCENARIO image (one that prints @END)
"""
import datetime
import json
import os
import platform
import re
import sys

from board.custom import engine_run, gen, gen_c3
from board.custom.sim_cost import RUN_ROWS, CLASS_ROWS, seeded_rows

BOARD = gen_c3.BOARD
TWIN = 'qemu:esp32c3'
SHIFT = 3
MEASURED = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'sim_cost_c3.json')


def object_cost():
    seeded = seeded_rows(BOARD)
    counts = {k: len(v) for k, v in seeded.items()}
    per_board = sum(counts.values()) + sum(RUN_ROWS.values())
    return {'per_board_rows': per_board, 'seeded': counts, 'run_time': RUN_ROWS, 'per_class_shared': CLASS_ROWS,
            'seeded_row_bytes_json': sum(len(json.dumps(r)) for v in seeded.values() for r in v),
            'total_rows_first_board': per_board + sum(CLASS_ROWS.values())}


def twin_run(image_bytes, run=engine_run.run):
    r = run('c3-run', ['flash_image.bin', '--icount', str(SHIFT), '--max-wall', '120'], {'flash_image.bin': image_bytes}, timeout=200)
    files = r.get('files') or {}
    rj = json.loads(files.get('run.json', b'{}') or b'{}')
    trace = (files.get('trace.log') or b'').decode('utf-8', 'replace')
    m = re.search(r'^@END t_us=(\d+)', trace, re.M)
    return rj, (int(m.group(1)) if m else 0), r


def measure(work=None, run=engine_run.run):
    work = work or gen_c3.default_work()
    row = gen.read_record(work)
    img = row.get('image_path') or ''
    if row.get('board_definition') != BOARD or not os.path.isfile(img):
        raise gen.GenRefused('no built C3 image in %s — `pol board gen c3 --variant c3-prio-inversion && pol board build c3` first' % work)
    rj, t_us, r = twin_run(open(img, 'rb').read(), run)
    if not t_us or not rj.get('wall_s'):
        raise gen.GenRefused('the image did not print `@END t_us=` (variant %s) — measure with a scenario variant' % row.get('variant'))
    vs, wall = t_us / 1e6, float(rj['wall_s'])
    ips = t_us * 1000.0 / (2 ** SHIFT) / wall
    obj = object_cost()
    rss = float(rj.get('peak_rss_mb', 0.0))
    return {'name': '%s:%s' % (BOARD, TWIN), 'board': BOARD, 'twin': TWIN, 'object_count': obj['per_board_rows'],
            'state_bytes': int(rss * 1024 * 1024), 'cycles_per_s': round(ips, 0),
            'host_class': '%s (%s, %d cpus)' % (platform.node(), platform.machine(), os.cpu_count() or 0),
            'measured_at': datetime.datetime.now().isoformat(timespec='seconds'),
            'method': json.dumps({'objects': obj, 'run': {k: rj.get(k) for k in ('wall_s', 'cpu_s', 'peak_rss_mb', 'qemu_version', 'argv', 'icount_shift')},
                                  'virtual_s': vs, 'wall_time_ratio': round(vs / wall, 3), 'build': row['name'], 'variant': row.get('variant'),
                                  'image_sha256': row.get('artifact_sha256'), 'how': r.get('how'), 'where': r.get('where'),
                                  'guest_flash_bytes': len(open(img, 'rb').read())}),
            'notes': ('wall-time ratio %.3f (virtual s per wall s at -icount %d, sleep=off — boot + window, the whole QEMU process); '
                      '%.1f M virtual instructions/s; QEMU peak RSS %.1f MB (state_bytes = that RSS: no core-state probe in QEMU); '
                      'guest flash image %d B' % (vs / wall, SHIFT, ips / 1e6, rss, len(open(img, 'rb').read())))}


SEED_C3_SIM_COSTS = []
try:   # the committed evidence; the seed row is read FROM it (one source)
    _m = json.load(open(MEASURED))
    SEED_C3_SIM_COSTS = [{k: _m[k] for k in ('name', 'board', 'twin', 'object_count', 'state_bytes', 'cycles_per_s', 'host_class', 'measured_at',
                                             'method', 'notes')}]
except Exception:   # pragma: no cover — absent until measured
    SEED_C3_SIM_COSTS = []


def main(argv):
    import argparse
    ap = argparse.ArgumentParser(prog='pol board cost c3')
    ap.add_argument('--work')
    ap.add_argument('--write', action='store_true', help='write custom/sim_cost_c3.json (the committed evidence)')
    a = ap.parse_args(argv)
    try:
        m = measure(a.work)
    except (gen.GenRefused, engine_run.EngineRefused) as e:
        print('[REFUSED] %s' % e)
        return 1
    if a.write:
        json.dump(m, open(MEASURED, 'w'), indent=1)
    print(json.dumps(dict(m, method=json.loads(m['method'])), indent=1))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
