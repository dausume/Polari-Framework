"""
@module board.custom.flash

`pol board flash uno` (brd-1, plan §3 step 4). The argv is RENDERED from the ProgrammerKind row `avrdude-optiboot`
(`avrdude -p atmega328p -c arduino -P <by-id> -b 115200 -D -U flash:w:<hex>:i`) with the board's cited facts
(build.mcu, upload.speed) — never typed here.

  DRY-RUN (the default): prints the exact argv (and the docker wrapper when the image rung would run it); exit 0;
           nothing is opened.
  REAL:    needs BOTH a detected BoardInstance of the board (board present, a port) AND --yes. avrdude runs on THIS
           host (a local binary, or the image with the port mapped in — a remote worker is refused by the ladder);
           avrdude writes then reads the flash back and compares (its default verify; `-V` is never passed). Only a
           run that exits 0 AND reports the bytes verified stamps BoardInstance.firmware_sha / last_flash_at and
           marks the FirmwareBuild flashed.

    python3 -m board.custom.flash uno [--work DIR] [--port P] [--yes] [--api URL]
"""
import datetime
import json
import os
import re
import ssl
import sys
import urllib.request

from board.custom import engine_run, gen
from board.custom.programmers import render_dry_run

PROGRAMMER = 'avrdude-optiboot'
INNER_PORT = '/dev/ttyPOLARI0'   # the port's name INSIDE the image when the image rung flashes
VERIFIED_RE = re.compile(r'(\d+)\s+bytes of flash verified', re.I)


class FlashRefused(RuntimeError):
    pass


def _facts(board):
    from board.custom.uno_facts import SEED_UNO_FACTS
    return {f['fact_key']: f['value'] for f in SEED_UNO_FACTS if f['board'] == board}


def argv_for(board, port, artifact):
    f = _facts(board)
    return render_dry_run(PROGRAMMER, mcu=f['build.mcu'], port=port, baud=f['upload.speed'], artifact=artifact).split()


def find_instance(board, instances=None):
    """The detected BoardInstance dict of this board on THIS host (hwmap's scanner), or None."""
    if instances is None:
        from board.custom.detect import scan_host, match
        from board.custom.register_map import board_rows, adapter_rows
        instances = match(scan_host(), board_rows(), adapter_rows())['instances']
    for i in instances:
        if i.get('definition') == board and i.get('state') == 'board present' and (i.get('by_id_path') or i.get('port')):
            return i
    return None


def plan(board='uno', work=None, port='', instance=None):
    board = gen.board_name(board)
    work = work or gen.default_work(board)
    row = gen.read_record(work)
    if row.get('state') not in ('built', 'flashed') or not row.get('hex_path'):
        raise FlashRefused('the firmware in %s is %r, not built — `pol board build uno` first (a refused build is never flashed)' % (work, row.get('state')))
    port = port or (instance or {}).get('by_id_path') or (instance or {}).get('port') or '{port}'
    argv = argv_for(board, port, row['hex_path'])
    from board.custom import board_engines as be
    where = be.resolve('avrdude', flash=True)
    wrapper = []
    if where['how'] == be.LOCAL_IMAGE:
        inner = argv_for(board, INNER_PORT, '/w/firmware.hex')
        dev = os.path.realpath(port) if port != '{port}' else port
        wrapper = engine_run.docker_prefix(where['where'], [(dev, INNER_PORT)])(os.path.dirname(row['hex_path']))[:-1] + [where['where']] + inner
    return {'board': board, 'work': work, 'row': row, 'argv': argv, 'text': ' '.join(argv), 'port': port,
            'engine': where, 'wrapper': wrapper, 'hex_sha256': row['artifact_sha256']}


def flash(board='uno', work=None, port='', yes=False, instance=None, instances=None, api='', run=engine_run.run, now=None):
    """DRY-RUN unless yes AND a detected instance. Returns {'dry_run', 'argv', ...}; raises FlashRefused."""
    board = gen.board_name(board)
    if instance is None and yes:
        instance = find_instance(board, instances)
    p = plan(board, work, port, instance)
    if not yes:
        return dict(p, dry_run=True, why='DRY-RUN (the default): nothing was opened; add --yes with the board plugged in to flash')
    if instance is None:
        raise FlashRefused('--yes, but no %s is detected on this host (pol board detect) — a real flash needs the board present' % board)
    if p['engine']['how'] == 'refused':
        raise FlashRefused(p['engine']['why'])
    port = p['port']
    hexdata = open(p['row']['hex_path'], 'rb').read()
    if p['engine']['how'] == 'local-image':
        args = argv_for(board, INNER_PORT, 'firmware.hex')[1:]
        devices = [(os.path.realpath(port), INNER_PORT)]
    else:
        args = argv_for(board, port, 'firmware.hex')[1:]
        devices = ()
    r = run('avrdude', args, {'firmware.hex': hexdata}, flash=True, devices=devices, timeout=180)
    log = (r.get('stdout') or '') + (r.get('stderr') or '')
    m = VERIFIED_RE.search(log)
    row = p['row']
    stamp = (now or datetime.datetime.now()).isoformat(timespec='seconds')
    if not (r.get('ok') and m):
        row.update(flash_log=log[-4000:], notes='flash FAILED (rc %s%s) — the board keeps its old firmware or none; nothing stamped'
                   % (r.get('returncode'), '' if m else ', no read-back verification line'))
        gen.write_record(p['work'], row)
        raise FlashRefused(row['notes'] + '\n' + log[-1500:])
    instance = dict(instance, firmware_sha=row['artifact_sha256'], last_flash_at=stamp)
    row.update(state='flashed', flashed_to=instance.get('name', ''), flash_log=log[-4000:],
               notes='flashed %s; avrdude read back %s bytes and they matched' % (stamp, m.group(1)))
    gen.write_record(p['work'], row)
    pushed = push(api, row, instance) if api else None
    return dict(p, dry_run=False, verified_bytes=int(m.group(1)), instance=instance, pushed=pushed, log=log)


def push(api, row, instance=None):
    """POST /api/board/builds — upserts the FirmwareBuild row (and stamps the instance when flashed)."""
    body = {'build': gen.row_fields(row)}
    if instance:
        body['instance'] = {k: instance.get(k, '') for k in ('name', 'firmware_sha', 'last_flash_at')}
    req = urllib.request.Request('%s/api/board/builds' % api.rstrip('/'), data=json.dumps(body).encode(), headers={'Content-Type': 'application/json'}, method='POST')
    from polariApiServer import outbound
    with outbound.http_request('self', 'board', 'POST', req, means='rest', timeout=30, lib='urllib', context=ssl._create_unverified_context()) as r:
        return json.load(r)


def main(argv):
    if argv and str(argv[0]).lower() in ('c3', 'esp32c3', 'esp32-c3'):   # sc-3: esptool over the C3's USB
        from board.custom import flash_c3
        return flash_c3.main(argv)
    import argparse
    ap = argparse.ArgumentParser(prog='pol board flash')
    ap.add_argument('board')
    ap.add_argument('--work')
    ap.add_argument('--port', default='')
    ap.add_argument('--yes', action='store_true')
    ap.add_argument('--api', default='')
    a = ap.parse_args(argv)
    try:
        res = flash(a.board, a.work, a.port, a.yes, api=a.api)
    except (gen.GenRefused, FlashRefused, engine_run.EngineRefused) as e:
        print('[REFUSED] %s' % e)
        return 1
    if res['dry_run']:
        print('[DRY-RUN] %s' % res['text'])
        if res['wrapper']:
            print('          runs as: %s' % ' '.join(res['wrapper']))
        print('          engine: avrdude %s (%s)' % (res['engine']['how'], res['engine']['where'] or res['engine']['why']))
        print('          hex sha256 %s' % res['hex_sha256'])
        print('          %s' % res['why'])
        return 0
    print('[ OK ] flashed %s → %s; %d bytes verified by read-back; firmware_sha %s' % (res['row']['name'], res['port'], res['verified_bytes'], res['hex_sha256']))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
