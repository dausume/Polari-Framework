"""
@module board.custom.hardware_system

hsp-1 (HARDWARE_SYSTEM_PINS_PLAN.md L6/L7/L9): THE HARDWARE SYSTEM — `build(tables, manager)` derives, from the rows in hand, the HardwareSystem row(s) (board.custom.hwsys_system), their SystemLinks
(board.custom.hwsys_links) and their SignalPaths (board.custom.hwsys_paths): {'HardwareSystem', 'SystemLink', 'SignalPath'}. Nothing is typed twice; every path verdict is CALLED from the owner of
that check (the availability ladder, the electrical rules, the pin lifecycle, the contract hash, the Purpose proof) or says `unchecked`. A check that fails to build says so on its path (never a
silent empty). The code-owned seeds (`seed_rows`) are recomputed on every seed; the doors compute from the live rows on every read. Checks are ADVISED — nothing here blocks a build or export.

    python3 -m board.custom.hardware_system list [--json]
    python3 -m board.custom.hardware_system show <system> [--json]
    python3 -m board.custom.hardware_system links <system> [--json]
    python3 -m board.custom.hardware_system paths <system> [<path>] [--json]      one hop per line with its verdict
"""
import json
import sys

from board.custom import hwsys_links as HL
from board.custom import hwsys_paths as HP
from board.custom import hwsys_system as HS
from board.custom.hwsys_context import Ctx


def build(tables, manager=None, strict=False, only=None):
    out = {'HardwareSystem': [], 'SystemLink': [], 'SignalPath': []}
    for s in HS.rows(tables):
        ctx = Ctx(tables, manager, s)
        lk = HL.links(ctx, s['name'])
        links = {l['name'].partition(':')[2]: l for l in lk}
        ctx.extra = {'SystemLink': {l['name'] for l in lk}}
        out['HardwareSystem'].append(dict(s, links_refs_json=json.dumps(['SystemLink:%s' % l['name'] for l in lk])))
        out['SystemLink'] += lk
        for slug, fn in HP.PATHS:
            if only and slug != only:
                continue
            try:
                p = fn(ctx, links)
            except Exception as e:   # noqa: BLE001 — a check that cannot be built says so; never a silent empty
                if strict:
                    raise
                p = {'hops': [], 'verdict': 'unchecked', 'blocked_at': 0, 'gap_free': False, 'direction': 'up', 'origin': '', 'destination': '', 'title': slug,
                     'error': '%s: %s' % (type(e).__name__, e)}
            hops = p['hops']
            counts = {}
            for h in hops:
                counts[h['verdict']] = counts.get(h['verdict'], 0) + 1
            first = next((h for h in hops if h['n'] == p['blocked_at']), None)
            summary = ('%d hops: %s' % (len(hops), ', '.join('%d %s' % (n, v) for v, n in sorted(counts.items(), key=lambda kv: -kv[1])))) if hops else 'not built'
            if first:
                summary += '; first blocked hop %d: %s' % (first['n'], first['detail'][:200])
            out['SignalPath'].append({'name': '%s:%s' % (s['name'], slug), 'title': p['title'], 'system': s['name'], 'direction': p['direction'], 'origin': p['origin'],
                                      'destination': p['destination'], 'hops_json': json.dumps(hops), 'hop_count': len(hops), 'verdict': p['verdict'],
                                      'blocked_at': p['blocked_at'], 'gap_free': p['gap_free'], 'summary': summary + ('; BUILD ERROR ' + p['error'] if p.get('error') else ''),
                                      'notes': 'derived on every seed / read (never typed): the verdict of a hop is the verdict of the check that owns it'})
    return out


def default_tables(manager=None):
    try:
        from board.custom import electrical_check as EC
        return EC.tables_for(manager)
    except Exception:   # noqa: BLE001 — electrodevice absent: the board tables alone (circuit checks then say unchecked)
        from board.custom import board_object as BO
        return BO.seed_tables()


def seed_rows():
    """The code-owned seed rows (recomputed on every seed)."""
    try:
        return build(default_tables())
    except Exception:   # noqa: BLE001 — never break board's import: the system row alone still seeds
        from board.custom import board_object as BO
        return {'HardwareSystem': HS.rows(BO.seed_tables()), 'SystemLink': [], 'SignalPath': []}


# ---------------------------------------------------------------- CLI
def render_path(p):
    hops = json.loads(p['hops_json']) if isinstance(p['hops_json'], str) else p['hops_json']
    lines = ['%s — %s' % (p['name'], p['title']), '  %s -> %s   [%s]%s' % (p['origin'], p['destination'], p['verdict'], '' if p['gap_free'] else '  (HAS A GAP)'), '  ' + p['summary']]
    for h in hops:
        lines.append('  %2d. %-13s %-12s %s' % (h['n'], h['kind'], h['verdict'], h['what']))
        lines.append('        %s   [check: %s]' % (h['ref'] or '(no ref)', h['check']))
        if h.get('detail'):
            lines.append('        %s' % h['detail'][:300])
    return '\n'.join(lines)


def main(argv):
    js = '--json' in argv
    argv = [a for a in argv if a != '--json']
    if not argv or argv[0] not in ('list', 'show', 'links', 'paths'):
        print(__doc__)
        return 2
    cmd, rest = argv[0], argv[1:]
    res = build(default_tables(), strict=True)
    if cmd == 'list':
        rows = [{'name': s['name'], 'title': s['title'], 'stage': s['stage'], 'links': len(json.loads(s['links_refs_json'])), 'solution': s['solution'],
                 'paths': [(p['name'].partition(':')[2], p['verdict']) for p in res['SignalPath'] if p['system'] == s['name']]} for s in res['HardwareSystem']]
        print(json.dumps(rows, indent=1) if js else '\n'.join('%s  %s  stage %s  %d links  solution %s  paths %s' % (r['name'], r['title'], r['stage'], r['links'], r['solution'], r['paths']) for r in rows))
        return 0
    system = next((s for s in res['HardwareSystem'] if rest and s['name'] == rest[0]), None)
    if system is None:
        print('no hardware system %r (list: %s)' % (rest[0] if rest else '', ', '.join(s['name'] for s in res['HardwareSystem'])), file=sys.stderr)
        return 1
    if cmd == 'show':
        print(json.dumps(system, indent=1) if js else '\n'.join('%-22s %s' % (k, v) for k, v in system.items()))
    elif cmd == 'links':
        lks = [l for l in res['SystemLink'] if l['system'] == system['name']]
        print(json.dumps(lks, indent=1) if js else '\n'.join('%s  [%s/%s, %s]  via %d crossing(s)%s\n    %s' % (l['name'], l['medium'], l['signal_kind'], l['verification'], len(json.loads(l['via_refs_json'])),
                                                                                    ('  protocol ' + l['protocol']) if l['protocol'] else '', l['title']) for l in lks))
    else:
        ps = [p for p in res['SignalPath'] if p['system'] == system['name'] and (len(rest) < 2 or p['name'].endswith(':' + rest[1]))]
        if len(rest) > 1 and not ps:
            print('no path %r' % rest[1], file=sys.stderr)
            return 1
        print(json.dumps(ps, indent=1) if js else '\n\n'.join(render_path(p) for p in ps))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
