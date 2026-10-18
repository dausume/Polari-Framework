"""
@module cmod.custom.mission_colocation

pp-1 (MISSION_PROFILE_SOLVER_PLAN.md §2.3, "Output per Mission"): which of a Mission's pin profiles (pp-0, cmod.custom.pin_profile_mission) COULD
share one pin or one net, by the cited overlap table (board.custom.profile_overlap), the minimum pin count under the most permissive valid
sharing, the conflicts named, and which profiles are forced apart.

  - A profile's kind maps to table kinds: a reserved profile is the `transport` reservation; pp-0's `interrupt-in` may be a dedicated INT pin or a
    pin-change pin, so both are tried and the MOST PERMISSIVE verdict wins (the kinds used are named in every row).
  - Two refinements the kind table cannot see, both from the profiles' own drive (pp-0) and cited: a role that needs the pin's PULL-UP cannot share
    a pin with an output (the pull-up exists only while the pin is an input, Table 14-1), and a net that a switch closes to ground cannot take a second
    output (it would be shorted whenever the contact closes).
  - Pin groups are found by trying every way to partition the profiles (exact for up to 10 profiles); a group needs every pair allowed AND one pin
    that offers every kind in it. A conditional verdict counts as allowed - its condition is carried into the group so it is never hidden.
    python3 -m cmod.custom.mission_colocation colocation <mission> [--purposes a,b] [--json]
"""
import itertools
import json

from board.custom import profile_overlap as PO
from board.custom import profile_overlap_kinds as K
from board.custom.profile_overlap_cites import render
from cmod.custom import pin_profile_mission as PM

_RANK = {'compatible': 0, 'conditional': 1, 'undetermined': 2, 'exclusive': 3}
_ALLOWED = ('compatible', 'conditional')
_OUTPUTS = ('digital-out', 'pwm-out', 'uart-tx')
SOC = 'atmega328p'


def table_kinds(p, other=None):
    """Table kinds for a profile. A reserved profile is the `transport` reservation against anything that is not itself reserved;
    two reserved profiles are two different lines of the host link (rx, tx) and are compared by their own kinds."""
    if p.get('reserved') and not (other and other.get('reserved')):
        return ['transport']
    if p['kind'] == 'interrupt-in':
        return ['interrupt-in', 'pin-change-in']
    return [p['kind']] if p['kind'] in K.KINDS else []


def _wants_pull(p):
    return (p.get('drive') or {}).get('need') in ('pull-up', 'pull-down')


def _switched(p):
    return 'switch' in str((p.get('drive') or {}).get('load_class', '')) or _wants_pull(p)


def _refine(pa, pb, ka, kb, scope, row):
    """The profile-level drive refinements; returns a row (a copy, changed) or the same row."""
    out_a, out_b = ka in _OUTPUTS, kb in _OUTPUTS
    if scope == 'pin' and ((_wants_pull(pa) and out_b) or (_wants_pull(pb) and out_a)):
        puller = pa if _wants_pull(pa) else pb
        return dict(row, verdict='exclusive', mode='exclusive', rule='pin.pull-needs-input', condition='',
                    reason='%s needs the pin\'s pull-up (%s), and the pull-up exists only while the pin is an INPUT (DDxn = 0); the other role needs it to be an output (DDxn = 1)' % (
                        puller['role'], puller['drive']['need']),
                    cite=' | '.join(render(k) for k in ('pin-table', 'pin-config')), cites=[render(k) for k in ('pin-table', 'pin-config')])
    if scope == 'net' and ((_switched(pa) and out_b) or (_switched(pb) and out_a)):
        sw = pa if _switched(pa) else pb
        return dict(row, verdict='exclusive', mode='exclusive', rule='net.switch-to-ground', condition='',
                    reason='the net of %s is closed to ground by a switch (%s); a second output on it would be shorted whenever the contact closes' % (
                        sw['role'], sw['drive'].get('load_class', sw['drive']['need'])),
                    cite=' | '.join(render(k) for k in ('pin-table', 'single-output')), cites=[render(k) for k in ('pin-table', 'single-output')])
    return row


def evaluate(pa, pb, scope):
    """Most permissive row for two profiles at a scope, with the table kinds it used."""
    best = None
    for ka in table_kinds(pa, pb) or ['digital-in']:
        for kb in table_kinds(pb, pa) or ['digital-in']:
            row = _refine(pa, pb, ka, kb, scope, PO.lookup(SOC, ka, kb, scope))
            if scope == 'pin' and (pa.get('reserved') != pb.get('reserved')) and row['verdict'] in _ALLOWED:
                row = dict(row, verdict='exclusive', mode='exclusive', rule='pin.reserved-line', condition='',
                           reason='one of the two is a pin the board reserves for the host link; nothing else may take that pin', cite=render('lifecycle'), cites=[render('lifecycle')])
            if scope in ('pin', 'net') and pa.get('reserved') and pb.get('reserved') and row['verdict'] in _ALLOWED:
                row = dict(row, verdict='exclusive', mode='exclusive', rule='%s.reserved-lines' % scope, condition='',
                           reason='both are lines the board wires to the USB-serial bridge and reserves for the host link; they are two different lines and stay apart',
                           cite=render('lifecycle'), cites=[render('lifecycle')])
            if best is None or _RANK[row['verdict']] < _RANK[best[0]['verdict']]:
                best = (row, ka, kb)
    row, ka, kb = best
    return dict(row, used='%s + %s' % (ka, kb), kinds=[ka, kb])


def _group_ok(members, profiles, pair):
    """members: indices. -> (ok, pins, conditions)"""
    if len(members) == 1:
        return True, [], []
    for i in members:
        if profiles[i].get('count', 1) != 1:
            return False, [], []
    conds = []
    for i, j in itertools.combinations(members, 2):
        r = pair[(i, j)]['pin']
        if r['verdict'] not in _ALLOWED:
            return False, [], []
        if r['condition']:
            conds.append('%s + %s: %s' % (profiles[i]['role'], profiles[j]['role'], r['condition']))
    # one pin that offers one candidate kind of EVERY member
    cand = None
    union = set()
    for choice in itertools.product(*[table_kinds(profiles[i]) or ['digital-in'] for i in members]):
        common = set(K.pins_for(choice[0]))
        for k in choice[1:]:
            common &= set(K.pins_for(k))
        if common:
            union |= common
            cand = cand or (None, choice)
    if cand is None:
        return False, [], []
    if any(profiles[i].get('reserved') for i in members) is False:
        union -= set(K.pins_for('transport')) if any(p.get('reserved') for p in profiles) else set()
    return True, (sorted(union), cand[1]), conds


def _partitions(n):
    def rec(i, groups):
        if i == n:
            yield [list(g) for g in groups]
            return
        for g in groups:
            g.append(i)
            yield from rec(i + 1, groups)
            g.pop()
        groups.append([i])
        yield from rec(i + 1, groups)
        groups.pop()
    yield from rec(0, [])


def _best_grouping(profiles, pair):
    n = len(profiles)
    if n > 10:   # beyond exact search: every profile on its own pin (a safe upper bound, said in the notes)
        return [[i] for i in range(n)], True
    best, best_cost = None, None
    for part in _partitions(n):
        okays = [_group_ok(g, profiles, pair) for g in part]
        if not all(o[0] for o in okays):
            continue
        cost = sum(max(profiles[i].get('count', 1) for i in g) for g in part)
        if best is None or cost < best_cost:
            best, best_cost = part, cost
    return best, False


def mission_colocation(mission='', purposes=None, manager=None):
    res = PM.mission_profiles(mission, purposes=purposes, manager=manager)
    profs = res['profiles']
    pair = {}
    for i, j in itertools.combinations(range(len(profs)), 2):
        pair[(i, j)] = {s: evaluate(profs[i], profs[j], s) for s in PO.SCOPES}
    part, capped = _best_grouping(profs, pair)
    groups = []
    for g in sorted(part, key=lambda g: g[0]):
        ok, cand, conds = _group_ok(g, profs, pair)
        groups.append({'profiles': [profs[i]['role'] + ' (' + profs[i]['kind'] + ')' for i in g], 'shared': len(g) > 1,
                       'pin_options': ', '.join(cand[0]) if cand else '', 'as': ' + '.join(cand[1]) if cand else '', 'conditions': conds,
                       'reserved': any(profs[i].get('reserved') for i in g)})
    rows, apart, share_pin, share_net = [], [], [], []
    for (i, j), by in pair.items():
        a, b = profs[i], profs[j]
        for s in PO.SCOPES:
            r = by[s]
            rows.append({'pair': '%s + %s' % (a['role'], b['role']), 'scope': s, 'verdict': r['verdict'], 'mode': r['mode'], 'condition': r['condition'],
                         'reason': r['reason'], 'used': r['used'], 'cite': r['cite']})
        for s in ('pin', 'net'):
            r = by[s]
            line = {'a': a['role'], 'b': b['role'], 'scope': s, 'verdict': r['verdict'], 'condition': r['condition'], 'why': r['reason'], 'cite': r['cite'], 'used': r['used']}
            (share_pin if s == 'pin' else share_net).append(line) if r['verdict'] in _ALLOWED else apart.append(line)
    total = sum(p.get('count', 1) for p in profs)
    pins_min = sum(max(profs[i].get('count', 1) for i in g) for g in part)
    notes = []
    if capped:
        notes.append('more than 10 profiles: exact grouping not attempted, every profile counted on its own pin (an upper bound)')
    if res.get('unresolved'):
        notes.append('%d task(s) gave no profile, so the Mission may need more pins than counted' % len(res['unresolved']))
    for pr in profs:
        if pr.get('origin') == 'bench' or 'sense' in pr['role']:
            for o in profs:
                if o is not pr and o['kind'] == 'digital-out':
                    pin_r = next((v['pin'] for (i, j), v in pair.items() if {profs[i]['id'], profs[j]['id']} == {pr['id'], o['id']}), None)
                    notes.append('%s reading %s: on ONE pin it would read the pin back through PINx (%s) or sense it with the interrupt that fires on outputs too (%s, %s) - '
                                 'the pad level, not the line the LED is on; the demo deliberately uses a REAL WIRE (one output, one listening input on one net - rule single_output) '
                                 'so the sense proves the wired line' % (pr['role'], o['role'], render('pinx-read'), render('exint-output'), 'pin verdict: %s' % (pin_r['verdict'] if pin_r else '?')))
    return {'ok': True, 'mission': mission, 'basis': res['basis'], 'soc': SOC, 'profiles': [{'id': p['id'], 'role': p['role'], 'kind': p['kind'], 'reserved': bool(p.get('reserved')),
            'count': p.get('count', 1), 'table_kinds': table_kinds(p), 'origin': p.get('origin', ''), 'importance': p.get('importance', '')} for p in profs],
            'pins_without_sharing': total, 'min_pins': pins_min, 'groups': groups, 'can_share_pin': share_pin, 'can_share_net': share_net, 'forced_apart': apart,
            'pair_rows': rows, 'notes': notes}


def view_rows(r, view='pairs'):
    """Plain-words rows of one view of a mission_colocation result: pairs (every pair at every scope) | groups | apart."""
    if view == 'groups':
        return [{'group': ' + '.join(g['profiles']), 'shared': 'yes' if g['shared'] else 'no', 'pin_options': g['pin_options'] or '(chosen later)', 'as': g['as'],
                 'conditions': '; '.join(g['conditions']) or 'none', 'reserved': 'yes' if g['reserved'] else 'no'} for g in r['groups']]
    if view == 'apart':
        return [{'pair': '%s + %s' % (x['a'], x['b']), 'scope': x['scope'], 'verdict': x['verdict'], 'why': x['why'], 'cite': x['cite']} for x in r['forced_apart']]
    return r['pair_rows']


def table_rows(mission='', purposes=None, view='pairs', manager=None):
    return view_rows(mission_colocation(mission, purposes, manager), view)


def main(argv):
    import argparse
    ap = argparse.ArgumentParser(prog='pol capability colocation')
    ap.add_argument('cmd', choices=['colocation'])
    ap.add_argument('name')
    ap.add_argument('--purposes', default='')
    ap.add_argument('--json', action='store_true')
    a = ap.parse_args(argv)
    try:
        r = mission_colocation(a.name, [x for x in a.purposes.split(',') if x] or None)
    except ValueError as e:
        print('[REFUSED] %s' % e)
        return 3
    if a.json:
        print(json.dumps(r, indent=1))
        return 0
    print('Co-location of Mission %s on %s: %d profiles need %d pins as separate pins; the most permissive valid sharing needs %d' % (
        a.name, r['soc'], len(r['profiles']), r['pins_without_sharing'], r['min_pins']))
    for g in r['groups']:
        print('  %-3s %s%s' % ('ONE' if g['shared'] else 'own', ' + '.join(g['profiles']),
                              ('   pin options: ' + g['pin_options']) if g['shared'] else ('   reserved' if g['reserved'] else '')))
        for c in g['conditions']:
            print('        if %s' % c)
    print('  could share a NET:')
    for x in r['can_share_net']:
        print('    %s + %s (%s)%s' % (x['a'], x['b'], x['verdict'], ('  if ' + x['condition']) if x['condition'] else ''))
    print('  forced apart:')
    for x in r['forced_apart']:
        print('    %s + %s at %s: %s' % (x['a'], x['b'], x['scope'], x['why']))
    for n in r['notes']:
        print('  note: %s' % n)
    return 0


if __name__ == '__main__':
    import sys
    sys.exit(main(sys.argv[1:]))
