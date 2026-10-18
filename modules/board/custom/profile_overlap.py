"""
@module board.custom.profile_overlap

pp-1 (MISSION_PROFILE_SOLVER_PLAN.md §2.3): THE OVERLAP TABLE - which pin-profile kinds may share one pin, one net or one peripheral on a
SoC. AVR first (the ATmega328P, Microchip DS40002061B); another SoC family is another rules module behind the same functions.

Code-owned, DERIVED on every read, not stored: the 17 kinds x 3 scopes = 459 verdicts follow from a few dozen rules, each naming the
datasheet section and page (board.custom.profile_overlap_cites) or an existing code rule (single_output, claims, the lifecycle rows). A stored
ProfileOverlapRule class would only copy those rules into rows that could drift from them; the table is small enough to build in
milliseconds and the page/door/CLI all read the same function.

  scope   pin         two profiles on ONE physical pin           (profile_overlap_pin)
          net         two profiles on two pins wired together     (profile_overlap_net)
          peripheral  two profiles served by ONE peripheral block (profile_overlap_periph)
  verdict compatible | exclusive | conditional (with the condition) | undetermined (with the reason)
  mode    exclusive | shared-read | shared-config | time-multiplexed-later   (the claims vocabulary, plus the fgm-4 mode to come)

    python3 -m board.custom.profile_overlap table <soc> [--a KIND] [--b KIND] [--scope pin|net|peripheral] [--verdict V] [--json]
    python3 -m board.custom.profile_overlap kinds <soc> [--json]
    python3 -m board.custom.profile_overlap rules <soc> [--json]
"""
import json

from board.custom import profile_overlap_kinds as K
from board.custom import profile_overlap_net as NET
from board.custom import profile_overlap_periph as PER
from board.custom import profile_overlap_pin as PIN
from board.custom.profile_overlap_cites import CITES, render
from board.custom.soc_atmega328p import SOC

SCOPES = ('pin', 'net', 'peripheral')
VERDICTS = ('compatible', 'exclusive', 'conditional', 'undetermined')
MODES = ('exclusive', 'shared-read', 'shared-config', 'time-multiplexed-later')
_RULES = {'pin': PIN.rule, 'net': NET.rule, 'peripheral': PER.rule}
_ALIASES = ('uno', 'arduino-uno-r3', 'atmega328p', 'atmega328', 'avr')


def resolve_soc(arg):
    if str(arg).lower() in _ALIASES:
        return SOC
    raise KeyError('no overlap rules cited for SoC %r yet (AVR first: %s)' % (arg, SOC))


def _row(soc, a, b, scope):
    o = _RULES[scope](a, b)
    common = K.common_pins(a, b) if scope == 'pin' else []
    applies = PER.applies(a, b) if scope == 'peripheral' else True
    cites = [render(k) for k in o.cites]
    return {'name': '%s:%s+%s:%s' % (soc, a, b, scope), 'soc': soc, 'a': a, 'b': b, 'scope': scope, 'verdict': o.verdict, 'mode': o.mode,
            'condition': o.condition, 'reason': o.reason, 'rule': o.rule, 'cite': ' | '.join(cites), 'cites': cites, 'cite_keys': list(o.cites),
            'common_pins': ', '.join(common), 'applies': 'yes' if applies else 'no (different peripherals)',
            'pair': '%s + %s' % (a, b), 'same_kind': a == b}


_CACHE = {}


def table(soc=SOC):
    """Every row: each unordered pair of KINDS (a kind with itself included) at each scope."""
    soc = resolve_soc(soc)
    if soc not in _CACHE:
        _CACHE[soc] = [_row(soc, a, b, sc) for i, a in enumerate(K.KINDS) for b in K.KINDS[i:] for sc in SCOPES]
    return _CACHE[soc]


def lookup(soc, a, b, scope):
    """The one row for a pair (any order) at a scope. KeyError names what is unknown."""
    soc = resolve_soc(soc)
    for k in (a, b):
        if k not in K.KINDS:
            raise KeyError('unknown kind %r (one of %s)' % (k, ', '.join(K.KINDS)))
    if scope not in SCOPES:
        raise KeyError('unknown scope %r (one of %s)' % (scope, ', '.join(SCOPES)))
    a, b = sorted((a, b), key=K.KINDS.index)
    return next(r for r in table(soc) if r['a'] == a and r['b'] == b and r['scope'] == scope)


def rows(soc=SOC, a=None, b=None, scope=None, verdict=None):
    """Filtered table rows. `a`/`b` match either side of a pair (give one to see all of its partners)."""
    out = table(soc)
    for k in (a, b):
        if k and k not in K.KINDS:
            raise KeyError('unknown kind %r (one of %s)' % (k, ', '.join(K.KINDS)))
    if scope and scope not in SCOPES:
        raise KeyError('unknown scope %r (one of %s)' % (scope, ', '.join(SCOPES)))
    if verdict and verdict not in VERDICTS:
        raise KeyError('unknown verdict %r (one of %s)' % (verdict, ', '.join(VERDICTS)))
    if a and b:
        a, b = sorted((a, b), key=K.KINDS.index)
        out = [r for r in out if r['a'] == a and r['b'] == b]
    elif a or b:
        k = a or b
        out = [r for r in out if k in (r['a'], r['b'])]
    if scope:
        out = [r for r in out if r['scope'] == scope]
    if verdict:
        out = [r for r in out if r['verdict'] == verdict]
    return out


def totals(soc=SOC):
    t = table(soc)
    by_scope = {sc: {v: sum(1 for r in t if r['scope'] == sc and r['verdict'] == v) for v in VERDICTS} for sc in SCOPES}
    return {'soc': resolve_soc(soc), 'kinds': len(K.KINDS), 'pairs': len(t) // len(SCOPES), 'rows': len(t),
            'verdicts': {v: sum(1 for r in t if r['verdict'] == v) for v in VERDICTS}, 'by_scope': by_scope,
            'modes': {m: sum(1 for r in t if r['mode'] == m) for m in MODES},
            'not_applicable': sum(1 for r in t if r['applies'].startswith('no'))}


def kind_rows(soc=SOC):
    resolve_soc(soc)
    return [{'kind': k, 'title': K.TITLES[k], 'side': K.SIDE[k], 'peripherals': ', '.join(K.PERIPHERALS[k]), 'pins': ', '.join(K.pins_for(k))} for k in K.KINDS]


def rule_rows(soc=SOC):
    """The distinct rules used, with how many rows each decides and every citation it stands on."""
    by = {}
    for r in table(soc):
        e = by.setdefault(r['rule'], {'rule': r['rule'], 'rows': 0, 'cite_keys': set(), 'example': r['name'], 'reason': r['reason']})
        e['rows'] += 1
        e['cite_keys'].update(r['cite_keys'])
    return [{'rule': e['rule'], 'rows': e['rows'], 'example': e['example'], 'reason': e['reason'],
             'cite': ' | '.join(render(k) for k in sorted(e['cite_keys']))} for e in sorted(by.values(), key=lambda e: e['rule'])]


def citations():
    return {k: dict(v, text=render(k)) for k, v in CITES.items()}


def _line(r):
    cond = ('  IF ' + r['condition']) if r['condition'] else ''
    return '  %-34s %-12s %-12s %-23s%s' % (r['pair'], r['scope'], r['verdict'], r['mode'], cond)


def main(argv):
    if not argv or argv[0] in ('-h', '--help', 'help'):
        print(__doc__[__doc__.index('    python3'):])
        return 0
    as_json = '--json' in argv
    args = [x for x in argv if x != '--json']
    opts, pos, i = {}, [], 1
    while i < len(args):
        if args[i].startswith('--') and i + 1 < len(args):
            opts[args[i][2:]] = args[i + 1]
            i += 2
        else:
            pos.append(args[i])
            i += 1
    if not pos or args[0] not in ('table', 'kinds', 'rules'):
        print('usage: table <soc> [--a KIND] [--b KIND] [--scope pin|net|peripheral] [--verdict V] [--json]  |  kinds <soc>  |  rules <soc>')
        return 2
    try:
        soc = resolve_soc(pos[0])
        if args[0] == 'kinds':
            res = kind_rows(soc)
            print(json.dumps({'ok': True, 'soc': soc, 'rows': res}, indent=1) if as_json else '\n'.join(
                '  %-14s %-9s %-26s pins: %s' % (r['kind'], r['side'], r['peripherals'], r['pins']) for r in res))
            return 0
        if args[0] == 'rules':
            res = rule_rows(soc)
            print(json.dumps({'ok': True, 'soc': soc, 'rows': res}, indent=1) if as_json else '\n'.join(
                '  %-28s %3d rows  %s\n      %s' % (r['rule'], r['rows'], r['reason'], r['cite']) for r in res))
            return 0
        res = rows(soc, a=opts.get('a'), b=opts.get('b'), scope=opts.get('scope'), verdict=opts.get('verdict'))
        if as_json:
            print(json.dumps({'ok': True, 'soc': soc, 'totals': totals(soc), 'count': len(res), 'rows': res}, indent=1))
            return 0
        t = totals(soc)
        print('Profile overlap table for %s: %d kinds, %d pairs x 3 scopes = %d verdicts (%s)' % (
            soc, t['kinds'], t['pairs'], t['rows'], ', '.join('%d %s' % (n, v) for v, n in t['verdicts'].items())))
        for r in res:
            print(_line(r))
            if len(res) <= 12:
                print('      why:  %s\n      cite: %s' % (r['reason'], r['cite']))
        print('  (%d shown)' % len(res))
        return 0
    except KeyError as e:
        print('[REFUSED] %s' % e.args[0])
        return 3


if __name__ == '__main__':
    import sys
    sys.exit(main(sys.argv[1:]))
