"""
@module board.custom.board_object_cli

`pol board pins|render|ingest|conflicts|assign` (brd-bo, THE BOARD OBJECT) with NO server: the rows are the seeds (the same rows
a server seeds), views and conflicts go to the local ledger (board.custom.ingest.ledger_path()). With a server, the same doors
are GET /api/board/<board>/pins|views|conflicts and POST /api/board/<board>/render|ingest (board.board_object_api).

    python3 -m board.custom.board_object_cli pins <board>
    python3 -m board.custom.board_object_cli render <board> --as kicad|zephyr|esp-idf|bare-c [--out DIR]
    python3 -m board.custom.board_object_cli ingest <path> --as KIND [--board B]
    python3 -m board.custom.board_object_cli conflicts [<board>]
    python3 -m board.custom.board_object_cli assign <board> <net> <pin>      # the flip: every view's changed lines (rows not saved)
"""
import argparse
import difflib
import json
import os
import re
import sys

from board.custom import board_object as bo
from board.custom import ingest as I
from board.custom import views as V


def _pins(board):
    r = bo.rows_for(board)
    pkg = {s['pin']: s['package_pin'] for s in r['soc_pins']}
    print('%s  soc %s  revision %s  board sha %s' % (r['board'], (r['soc'] or {}).get('name', '-'), r['identity'].get('revision', '-'), bo.board_sha(r)[:16]))
    print('%-8s %-7s %-4s %-12s %-12s %-7s %-16s %-21s %s' % ('pin', 'soc', 'pkg', 'net', 'connector', 'func', 'periph/signal', 'C symbol', 'origin'))
    for p in r['pins']:
        print('%-8s %-7s %-4s %-12s %-12s %-7s %-16s %-21s %s' % (p['canonical'], p['soc_pin'], pkg.get(p['soc_pin'], '?'), p['net'][:12], p['connector_pin'] or '-',
                                                               p['function'], ('%s %s' % (p['peripheral'], p['signal'])).strip()[:16] or '-',
                                                               p['firmware_symbol'] or '-', p['origin'].split('@')[0][:60]))
    print('\nruntime profiles:')
    for rt, prof in sorted(r['profiles'].items()):
        print('  %-9s %s' % (rt, 'supported — console %s, tick %s Hz, twin %s' % (prof['console_uart'] or '-', prof['tick_hz'], prof['twin'] or '-')
                             if prof['supported'] else 'REFUSED: %s' % prof['refusal'][:140]))
    why = bo.validate(r)
    print('\nrules: %s' % ('pins named once, no SoC pin assigned twice, every net/connector/soc pin a row — OK' if not why else '; '.join(why)))
    return 0 if not why else 1


def _out_dir(board, kind, out):
    if out:
        return out
    from polariApiServer.module_home import module_home
    return os.path.join(module_home('board', os.environ.get('POLARI_BOARD_HOME')), bo.board_name(board), 'views', kind)


def _render(board, kind, out):
    res, row = I.render_row(board, kind)
    if res is None:
        I.ledger_write(views=[row])
        print('[REFUSED] %s --as %s: %s' % (row['board'], kind, row['refusal']))
        return 3
    d = _out_dir(board, kind, out)
    os.makedirs(d, exist_ok=True)
    for name, text in res['files'].items():
        open(os.path.join(d, name), 'w').write(text)
    row['path'] = d
    I.ledger_write(views=[row])
    print('[ OK ] %s --as %s  view sha256 %s  board sha %s' % (row['board'], kind, res['sha256'], res['board_sha'][:16]))
    for name in sorted(res['files']):
        print('       %s/%s' % (d, name))
    return 0


def _board_of(files, board):
    if board:
        return bo.board_name(board)
    for text in files.values():
        m = re.search(r'THE BOARD OBJECT rows of ([a-z0-9-]+)', text)
        if m:
            return m.group(1)
    raise V.ViewRefused('which board? the files carry no render banner — pass --board')


def _ingest(path, kind, board):
    files = I.read_path(path)
    board = _board_of(files, board)
    res = I.ingest(board, files, kind, path=os.path.abspath(path))
    I.ledger_write(views=[res['view']], conflicts=res['conflicts'])
    v = res['view']
    print('[ OK ] ingested %s as %s for %s  view sha256 %s  (carries: %s)' % (path, v['kind'], board, v['sha256'][:16], v['fields_carried']))
    print('       %d pin(s) read; %d conflict(s) — the rows are UNCHANGED (board sha %s)' % (len(res['pins']), len(res['conflicts']), res['board_sha'][:16]))
    for c in res['conflicts']:
        print('       CONFLICT  %-10s %-16s rows %-28s view %s' % (c['pin'], c['field'], c['rows_value'][:28], c['view_value']))
    return 0


def _conflicts(board):
    led = I.ledger_read()
    rows = [c for c in led['conflicts'] if not board or c['board'] == bo.board_name(board)]
    if not rows:
        print('no conflicts in the ledger (%s)%s' % (I.ledger_path(), ' for %s' % board if board else ''))
        return 0
    for c in rows:
        print('%-5s %-15s %-8s %-10s %-16s rows %-26s view %s' % (c['state'], c['board'], c['view_kind'], c['pin'], c['field'], c['rows_value'][:26], c['view_value']))
    print('\n%d conflict(s) — shown, never auto-resolved (ledger %s)' % (len(rows), I.ledger_path()))
    return 0


def _assign(board, net, pin):
    r0 = bo.rows_for(board)
    try:
        r1, touched = bo.assign(r0, net, pin)
    except bo.BoardObjectRefused as e:
        print('[REFUSED] %s' % e)
        return 3
    print('[ OK ] net %s → pin %s on %s (rows touched: %s; NOT saved — a seed is code-owned: edit the seed / ingest a view, or POST to a server)'
          % (net, pin, r0['board'], ', '.join(touched)))
    for kind in V.KINDS:
        try:
            a, b = V.render(r0, kind), V.render(r1, kind)
        except V.ViewRefused as e:
            print('\n  %-8s refused: %s' % (kind, str(e)[:120]))
            continue
        print('\n  %-8s %s → %s' % (kind, a['sha256'][:12], b['sha256'][:12]))
        for name in sorted(a['files']):
            for ln in difflib.unified_diff(a['files'][name].splitlines(), b['files'][name].splitlines(), lineterm='', n=0):
                if ln.startswith(('+', '-')) and not ln.startswith(('+++', '---')) and 'board sha' not in ln:
                    print('    %s' % ln[:150])
    return 0


def main(argv):
    ap = argparse.ArgumentParser(prog='pol board')
    ap.add_argument('verb', choices=('pins', 'render', 'ingest', 'conflicts', 'assign'))
    ap.add_argument('args', nargs='*')
    ap.add_argument('--as', dest='kind', default='')
    ap.add_argument('--out', default='')
    ap.add_argument('--board', default='')
    a = ap.parse_args(argv)
    try:
        if a.verb == 'pins':
            return _pins(a.args[0] if a.args else 'uno')
        if a.verb == 'render':
            if not a.args or a.kind not in V.KINDS:
                print('usage: pol board render <board> --as kicad|zephyr|esp-idf|bare-c')
                return 2
            return _render(a.args[0], a.kind, a.out)
        if a.verb == 'ingest':
            if not a.args:
                print('usage: pol board ingest <path> --as kicad|zephyr|esp-idf|bare-c [--board B]')
                return 2
            return _ingest(a.args[0], a.kind or None, a.board)
        if a.verb == 'conflicts':
            return _conflicts(a.args[0] if a.args else '')
        if len(a.args) != 3:
            print('usage: pol board assign <board> <net> <pin>   (e.g. uno PWM_LED D5)')
            return 2
        return _assign(*a.args)
    except (bo.BoardObjectRefused, V.ViewRefused) as e:
        print('[REFUSED] %s' % e)
        return 3


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
