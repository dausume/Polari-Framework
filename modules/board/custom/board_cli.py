"""
@module board.custom.board_cli

What `pol board list|roads|facts <board>|engines` print on a host with NO server: the rows exactly as the seed builds
them from the register snapshot (the same rows a server seeds). `detect` lives in board.custom.detect.

    python3 -m board.custom.board_cli list|roads|facts <board>|engines        # from polari-framework/
"""
import json
import sys


def _list():
    from board.custom.register_map import board_rows, adapter_rows
    boards = board_rows()
    print('%-30s %-14s %-17s %-13s %-5s %-18s %s' % ('device', 'kind', 'programmer', 'usb rule', 'sim', 'twin', 'road'))
    for b in boards:
        print('%-30s %-14s %-17s %-13s %-5s %-18s %s' % (b['name'][:30], b['kind'], b['programmer'] or '-', b['usb_rule'],
                                                        'yes' if b['simulated'] else '', b['twin'] or '-', b['road_status']))
    adapters = adapter_rows()
    print('\n%-28s %-30s %s' % ('adapter', 'usb ids', 'kind'))
    for a in adapters:
        print('%-28s %-30s %s' % (a['name'], ','.join(json.loads(a['usb_ids_json'])) or '- (captured on first plug)', a['kind'][:60]))
    print('\n%d devices (%d simulated), %d adapters' % (len(boards), sum(1 for b in boards if b['simulated']), len(adapters)))


def _roads():
    from board.custom.register_map import board_rows, road_rows
    for r in road_rows(board_rows()):
        steps = json.loads(r['steps_json'])
        print('%-36s %-12s %s' % (r['name'], r['status'], ' '.join('%s:%s' % (s['step'], s['status']) for s in steps if s['status'] != 'todo') or 'all steps todo'))


def _facts(board):
    from board.custom.uno_facts import SEED_UNO_FACTS
    facts = [f for f in SEED_UNO_FACTS if f['board'] == board]
    if not facts:
        print('no cited facts for %s yet — capturing them is the first step of its road' % board)
        return 1
    for f in facts:
        print('%-28s %-34s %-8s %s' % (f['fact_key'], f['value'], f['unit'], f['url']))
    return 0


def _engines():
    from board.custom.board_engines import placement
    p = placement()
    for e, r in p['engines'].items():
        print('%-16s %-12s %-13s %s' % (e, r['kind'], r['how'], r['where'] or r['why']))


def main(argv):
    verb = argv[0] if argv else 'list'
    if verb == 'list':
        _list()
    elif verb == 'roads':
        _roads()
    elif verb == 'facts':
        if len(argv) < 2:
            print('usage: facts <board>')
            return 2
        return _facts(argv[1])
    elif verb == 'engines':
        _engines()
    else:
        print(__doc__)
        return 2
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
