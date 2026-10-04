"""
@module pcb.custom.pcb_cli

What `pol pcb engines|ingest|render-schematic` print with NO server (pcb-0) — straight calls into pcb.custom.*, the
same functions `pcb_api.py` wraps for a running instance.

    python3 -m pcb.custom.pcb_cli engines
    python3 -m pcb.custom.pcb_cli ingest <path> [--board B] [--no-engine]
    python3 -m pcb.custom.pcb_cli render-schematic uno-shield [--out FILE]
"""
import json
import sys


def _engines():
    from pcb.custom.pcb_engines import placement
    p = placement()
    print('%-12s %-10s %-24s %s' % ('engine', 'how', 'where', 'why'))
    r = p['resolved']
    print('%-12s %-10s %-24s %s' % (p['engine'], r['how'], r['where'] or '-', r['why']))
    print('licence: %s' % p['licence'])
    if p.get('worker'):
        w = p['worker']
        print('worker: %s' % w.get('worker'))
        for k, v in (w.get('libraries') or {}).items():
            print('  library %-18s %s (%d files)' % (k, v.get('version'), v.get('files', 0)))
    return 0


def _ingest(argv):
    path = argv[0] if argv else None
    if not path:
        print('usage: ingest <path> [--board B] [--no-engine]')
        return 2
    board = None
    engines = True
    rest = argv[1:]
    i = 0
    while i < len(rest):
        if rest[i] == '--board' and i + 1 < len(rest):
            board = rest[i + 1]
            i += 2
        elif rest[i] == '--no-engine':
            engines = False
            i += 1
        else:
            i += 1
    from pcb.custom import ingest as I
    res = I.ingest(path, board=board, engines=engines)
    rows = res['rows']
    print('board: %s' % rows.get('board'))
    for k in ('Part', 'Symbol', 'Footprint', 'PcbBoard', 'Placement', 'BoardNet', 'Route', 'DrcResult', 'FabricationExport'):
        if rows.get(k) is not None:
            print('%-20s %d' % (k, len(rows[k])))
    if rows.get('problems'):
        print('problems:')
        for p in rows['problems']:
            print('  - %s' % p)
    if res['refused']:
        print('ENGINE REFUSED: %s' % res['refused'])
    elif res['record']:
        print('record: %s' % res['record_path'])
        print('engine: %s' % res['record']['engine']['version'])
    return 0


def _render_schematic(argv):
    which = argv[0] if argv else ''
    if which != 'uno-shield':
        print('usage: render-schematic uno-shield [--out FILE]')
        return 2
    out = None
    if '--out' in argv:
        out = argv[argv.index('--out') + 1]
    from pcb.custom import uno_shield as U
    from pcb.custom import schematic_writer as W
    from pcb.custom import pcb_engines as E
    d = U.design()
    need = {c['lib_id'] for c in d['components']} | {W.POWER_LIB[n] for n in d['nets'] if n in W.POWER_LIB} | {'power:PWR_FLAG'}
    try:
        libs = {}
        for lib_id in sorted(need):
            lib, name = lib_id.split(':', 1)
            libs[lib_id] = E.library('symbol', lib, name)['text']
        text, report = W.write(d, libs, title='UNO Shield (pcb-0 schematic skeleton)')
    except (E.EngineRefused, W.WriterRefused) as e:
        print('REFUSED: %s' % e)
        return 3
    print('board: %s  host: %s' % (d['board'], d['host']))
    print('components: %d  connections: %d  unconnected pins: %d  power symbols: %d  labels: %d'
          % (len(d['components']), len(report['connections']), len(report['unconnected_pins']), report['power_symbols'], report['labels']))
    if out:
        open(out, 'w').write(text)
        print('written: %s' % out)
    try:
        res = E.run(['sch', 'erc', '--format', 'json', '--severity-all', '-o', 'erc.json', 'uno-shield.kicad_sch'],
                    {'uno-shield.kicad_sch': text}, source_date=E.SOURCE_DATE)
        rep = json.loads(res['files'].get('erc.json', b'{}') or b'{}')
        n = sum(len(s.get('violations', [])) for s in rep.get('sheets', []))
        print('erc: exit %s, %d violation(s) reported (unconnected header pins are expected — not hidden)' % (res['returncode'], n))
    except E.EngineRefused as e:
        print('erc skipped — %s' % e)
    return 0


def main(argv):
    verb = argv[0] if argv else 'engines'
    rest = argv[1:]
    if verb == 'engines':
        return _engines()
    if verb == 'ingest':
        return _ingest(rest)
    if verb == 'render-schematic':
        return _render_schematic(rest)
    print(__doc__)
    return 2


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
