"""
@module board.custom.reachability

hsp-0 (L4): REACHABILITY — a DERIVED view (never a stored class). For one board: every SoC pin of every chip on it gets a verdict —
  header        an exposed crossing reaches a header / connector (which ConnectorPins)
  internal      the line stops on the board (consumed by ... : the 16 MHz part, an LED, the other chip, a probe pad)
  not-bonded    the chip has the pin, this package does not bring it out
  undetermined  the sources do not say
— and every function of the chip's pins is reachable at a header or not (a function on an internal / not-bonded pin is NOT reachable). Per header pin:
the inward trace (header pin -> board crossing -> package leg -> SoC pin -> its functions). His rule: account for everything, the unused included.
Works over seed tables or live rows (`tables` = {class: [dict]}). The ten-rung availability LADDER (a function's way through capability, package, board, parts,
extensions, multiplexing, electrical, lifecycle, claims, isotope) is board.custom.ladder, built on the same crossing rows.

    python3 -m board.custom.reachability exposure <board> [<pin>] [--json]
    python3 -m board.custom.reachability reach <board> [--json]
    python3 -m board.custom.reachability ladder <board> <pin> [<function>] [--package P] [--circuit C] [--transport T] [--phase PH] [--json]
"""
import json
import sys

from board.custom import exposure_view as V

VERDICTS = ('header', 'internal', 'not-bonded', 'undetermined')


def _components(tables, board):
    return sorted([c for c in tables.get('BoardComponent', []) if c['board'] == board and c.get('package')], key=lambda c: c['ref'])


def pin_verdict(tables, board, comp, soc_pin_name, package=None):
    """The verdict of one SocPin of one chip, in `package` (default: the package the design models for the component)."""
    package = package or comp['package']
    rows = V.board_rows(tables, board)
    leg = next((c for c in tables.get('PackageContact', []) if c['package'] == package and c.get('soc_pin') == soc_pin_name), None)
    if leg is None:
        return {'verdict': 'not-bonded', 'leg': '', 'headers': [], 'consumed_by': [], 'why': '%s has no contact for %s on %s' % (comp['name'], soc_pin_name, package)}
    ref = 'PackageContact:%s' % leg['name']
    e2 = [c for c in V.touching(rows, [ref]) if c['level'] == 'E2']
    headers, consumed = [], []
    for c in e2:
        k = V.outer_kind(c['outer_ref'], tables) if c['inner_ref'] == ref else 'chip'
        if c['exposed'] and k == 'header':
            headers += V.header_pins(c['outer_ref'], tables)
        elif c['exposed'] and k == 'test-pad':
            consumed.append('test pad %s (a probe point, not a header)' % c['outer_ref'].split(':')[1])
        else:
            consumed.append(c['consumed_by'] or ('' if c['via'] == 'internal-only' else V.short(c)))
    if headers:
        return {'verdict': 'header', 'leg': leg['name'], 'headers': sorted(set(headers)), 'consumed_by': consumed, 'why': ''}
    if e2:
        return {'verdict': 'internal', 'leg': leg['name'], 'headers': [], 'consumed_by': [x for x in consumed if x] or [''],
                'why': 'the crossings of this leg stop on the board' + ('' if all(c['verification'] == 'verified' for c in e2) else ' (some only partly verified)')}
    return {'verdict': 'undetermined', 'leg': leg['name'], 'headers': [], 'consumed_by': [], 'why': 'no board crossing is modelled for %s' % ref}


def reach(board, tables=None):
    from board.custom import board_object as BO
    board = BO.board_name(board)
    tables = tables if tables is not None else BO.seed_tables()
    pins, functions = [], []
    for comp in _components(tables, board):
        for sp in sorted([s for s in tables.get('SocPin', []) if s['soc'] == comp['soc']], key=lambda s: (s['port'], s['bit'])):
            v = pin_verdict(tables, board, comp, sp['name'])
            pins.append({'component': comp['name'], 'soc': comp['soc'], 'package': comp['package'], 'soc_pin': sp['name'], 'pin': sp['pin'], **v})
            for fn in ['GPIO'] + json.loads(sp.get('functions_json') or '[]'):
                functions.append({'component': comp['name'], 'soc_pin': sp['name'], 'function': fn, 'reachable': v['verdict'] == 'header',
                                  'verdict': v['verdict'], 'headers': v['headers']})
        # package signals that are not SocPins (the 328P's ADC6/ADC7): not-bonded on a package without a leg
        pkgs = {p['name']: p for p in tables.get('PackageDefinition', [])}
        for other in pkgs.values():
            if other['soc'] != comp['soc'] or other['name'] == comp['package']:
                continue
            mine = {c['label'] for c in tables.get('PackageContact', []) if c['package'] == comp['package']}
            for c in sorted([c for c in tables.get('PackageContact', []) if c['package'] == other['name'] and c['label'] not in mine], key=lambda c: c['number']):
                if any(p.get('signal') == '%s:%s' % (comp['soc'], c['label']) for p in pins):
                    continue
                pins.append({'component': comp['name'], 'soc': comp['soc'], 'package': comp['package'], 'soc_pin': '', 'pin': c['label'], 'signal': '%s:%s' % (comp['soc'], c['label']),
                             'verdict': 'not-bonded', 'leg': '', 'headers': [], 'consumed_by': [],
                             'why': '%s exists only in %s; %s has no leg for it' % (c['label'], other['name'], comp['package'])})
    return {'board': board, 'pins': pins, 'functions': functions, 'headers': header_traces(tables, board),
            'counts': {v: sum(1 for p in pins if p['verdict'] == v) for v in VERDICTS},
            'functions_reachable': sum(1 for f in functions if f['reachable']), 'functions_total': len(functions)}


def header_traces(tables, board):
    """{ConnectorPin name: {label, net, inward: [branch ...], note}} — each branch walks header pin -> crossing -> leg -> E1 crossing -> SocPin -> functions."""
    rows = V.board_rows(tables, board)
    e1 = {c['outer_ref']: c for c in rows if c['level'] == 'E1'}
    socpins = {s['name']: s for s in tables.get('SocPin', [])}
    out = {}
    for cp in sorted([c for c in tables.get('ConnectorPin', []) if c['board'] == board], key=lambda c: (c['connector'], c['number'])):
        refs = ['ConnectorPin:%s' % cp['name'], 'BoardNet:%s:%s' % (board, cp['net'])] if cp.get('net') else ['ConnectorPin:%s' % cp['name']]
        branches = []
        for c in [x for x in rows if x['level'] == 'E2' and x['outer_ref'] in refs]:
            leg = c['inner_ref']
            f = e1.get(leg)
            sp = socpins.get((f['inner_ref'] if f else '').partition(':')[2])
            branches.append({'crossing': c['name'], 'via': c['via'], 'via_part': c['via_part'], 'via_value': c['via_value'], 'leg': leg,
                             'package_crossing': f['name'] if f else '', 'inner': f['inner_ref'] if f else '',
                             'functions': (['GPIO'] + json.loads(sp.get('functions_json') or '[]')) if sp else [],
                             'also_on_the_leg': [V.short(o) for o in rows if o['level'] == 'E2' and o is not c and leg in (o['inner_ref'], o['outer_ref']) and o['outer_ref'] not in refs]})
        out[cp['name']] = {'label': cp['label'], 'net': cp.get('net', ''), 'inward': branches,
                           'note': '' if branches else 'no chip leg reaches this header pin in the model (a regulator / supply side or a no-connect: not modelled)'}
    return out


def exposure(board, pin=None, tables=None):
    """The crossings of a board (all), or those touching one pin: a BoardPin canonical (D13), a connector label (RESET, AREF, GND, +5V), or a SoC pin (PB6)."""
    from board.custom import board_object as BO
    board = BO.board_name(board)
    tables = tables if tables is not None else BO.seed_tables()
    rows = V.board_rows(tables, board)
    if pin is None:
        return rows
    refs = set()
    for bp in tables.get('BoardPin', []):
        if bp['board'] == board and bp['canonical'] == pin:
            refs.add('BoardPin:%s' % bp['name'])
            refs |= {'SocPin:%s' % s['name'] for s in tables.get('SocPin', []) if s['pin'] == bp['soc_pin'] and s['soc'] in {c['soc'] for c in _components(tables, board)}}
    for cp in tables.get('ConnectorPin', []):
        if cp['board'] == board and (cp['label'] == pin or cp.get('board_pin') == pin):
            refs.add('ConnectorPin:%s' % cp['name'])
            if cp.get('net'):
                refs.add('BoardNet:%s:%s' % (board, cp['net']))
    for sp in tables.get('SocPin', []):
        if (sp['pin'] == pin or sp['name'] == pin) and sp['soc'] in {c['soc'] for c in _components(tables, board)}:
            refs.add('SocPin:%s' % sp['name'])
    if not refs:
        raise KeyError('%s has no pin %s' % (board, pin))
    # every package leg of a SoC pin in the set, and every leg named by a connector label's rail
    for sp_ref in [r for r in refs if r.startswith('SocPin:')]:
        sp = next((s for s in tables.get('SocPin', []) if 'SocPin:%s' % s['name'] == sp_ref), None)
        refs |= set(json.loads((sp or {}).get('package_contacts_refs_json') or '[]'))
    first = V.touching(rows, refs)
    legs = {c['inner_ref'] for c in first if c['level'] == 'E2' and c['inner_ref'].startswith('PackageContact:')} - {r for r in refs}
    near = V.touching(rows, refs | legs) if legs else first
    return near


def main(argv):
    if not argv or argv[0] in ('-h', '--help', 'help'):
        print(__doc__[__doc__.index('    python3'):])
        return 0
    import contextlib
    import io
    from board.custom import board_object as BO
    with contextlib.redirect_stdout(io.StringIO()):
        tables = BO.seed_tables()
    as_json = '--json' in argv
    args = [a for a in argv if a != '--json']
    opts, pos, i = {}, [], 1
    while i < len(args):
        if args[i].startswith('--') and i + 1 < len(args):
            opts[args[i][2:]] = args[i + 1]
            i += 2
        else:
            pos.append(args[i])
            i += 1
    try:
        if args[0] == 'exposure' and pos:
            rows = exposure(pos[0], pos[1] if len(pos) > 1 else None, tables)
            if as_json:
                print(json.dumps({'ok': True, 'board': pos[0], 'pin': pos[1] if len(pos) > 1 else None, 'rows': rows}, indent=1))
                return 0
            print('%s %s — %d crossings' % (pos[0], pos[1] if len(pos) > 1 else '(all)', len(rows)))
            for c in rows:
                print('  %-3s %-34s -> %-40s %-16s %s%s' % (c['level'], c['inner_ref'][:34] or '(die pad undetermined)', c['outer_ref'][:40] or '-', c['via'],
                                                           ' '.join(x for x in (c['via_part'], c['via_value']) if x), (' [%s]' % c['consumed_by']) if c['consumed_by'] else ''))
            return 0
        if args[0] == 'reach' and pos:
            r = reach(pos[0], tables)
            if as_json:
                print(json.dumps(dict(r, ok=True), indent=1))
                return 0
            print('%s — %s; %d/%d functions reachable at a header' % (r['board'], ', '.join('%d %s' % (n, v) for v, n in r['counts'].items()), r['functions_reachable'], r['functions_total']))
            for p in r['pins']:
                print('  %-12s %-12s %-10s %s' % (p['component'].rpartition(':')[2], p['pin'], p['verdict'],
                                                  ', '.join(p['headers']) if p['headers'] else '; '.join(x for x in p['consumed_by'] if x) or p['why']))
            return 0
        if args[0] == 'ladder' and len(pos) >= 2:
            from board.custom import ladder as L
            ctx = {'board': pos[0], **{k: v for k, v in opts.items()}}
            res = L.availability(pos[1], pos[2] if len(pos) > 2 else 'GPIO', ctx, tables)
            if as_json:
                print(json.dumps(dict(res, ok=True), indent=1))
                return 0
            print(L.render(res))
            return 0
    except (KeyError, BO.BoardObjectRefused) as e:
        print('refused: %s' % e)
        return 2
    print('unknown: %s' % ' '.join(argv))
    return 2


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
