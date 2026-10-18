"""
@module cmod.custom.solve_assign

sol-0: the CONSTRAINT SEARCH that puts needs on pins. Depth-first with backtracking and branch-and-bound:

  order      reserved lines first, then by importance (safety > required > important > desired), then the need with the fewest candidate pins
  options    the oracle's pins for a need (ladder rungs 1-9 not blocked, not occupied), cheapest first: the least specialised pin before INT0/INT1, PWM, ADC, comparator pins
  sharing    OFF by default: a pin carries one signal, and two Mission roles are two signals (the button's line and the LED's line are not the same wire). `share_pins` =
             'compatible' | 'conditional' lets a pin take a second need when pp-1's PIN-scope verdict for the pair allows it (the condition is carried); two pins wired together (the sense wire on the LED line) are checked at NET scope; needs on one peripheral at PERIPHERAL scope
  cost       (pins used, pins off the bench wiring when that is preferred, summed specialisation cost) - compared lexicographically, so FEWER PINS first, then the cheapest;
             equal-cost alternatives are not explored (the first found in option order wins - deterministic)
  bound      `max_nodes` per search; a search that hits it says so and keeps the best found

A search with no solution says WHY (the need with no pin at all, or the set of needs that outnumber the pins they could take). `place_by_importance` drops whole jobs, least
important first, until the rest fit, and names what was dropped.
"""
import itertools

from board.custom import profile_overlap as PO
from board.custom import profile_overlap_periph as PER
from cmod.custom import mission_colocation as MC
from cmod.custom import pin_profiles as PP

#: sense-led-line watches the line drive-led drives (the job words: "watch the wire that powers the light"). The two are ALWAYS two pins joined by a real wire, never one pin:
#: the sense job exists to give the firmware its own independent proof, and a pin read back through PINx (or an interrupt that fires on outputs too) shows the pad, not the line
#: (pp-1's note on this pair, mission_colocation.mission_colocation). So they are checked at NET scope and never share a pin, whatever the pin-scope verdict.
NET_LINKS = (('sense-led-line', 'drive-led'),)


def _p(n):
    return {'kind': n['okind'], 'role': n['role'], 'reserved': n['reserved'], 'drive': n['drive'] or {}, 'id': n['id']}


def pair_rules(needs, share='none'):
    """{(i, j): {'share': ok?, 'pin': row, 'conditions': [...], 'periph_exclusive': bool, 'periph': row}} for i < j."""
    allowed = {'none': (), 'compatible': ('compatible',), 'conditional': ('compatible', 'conditional')}[share]
    out = {}
    for i, j in itertools.combinations(range(len(needs)), 2):
        a, b = _p(needs[i]), _p(needs[j])
        pin = MC.evaluate(a, b, 'pin')
        per_applies = PER.applies(a['kind'], b['kind']) if a['kind'] in PO.K.KINDS and b['kind'] in PO.K.KINDS else False
        per = MC.evaluate(a, b, 'peripheral') if per_applies else None
        wire = frozenset((needs[i]['job'], needs[j]['job'])) in {frozenset(l) for l in NET_LINKS}
        out[(i, j)] = {'share': pin['verdict'] in allowed and not wire, 'pin': pin, 'conditions': [pin['condition']] if pin['condition'] else [], 'real_wire': wire,
                       'periph_exclusive': bool(per and per['verdict'] == 'exclusive'), 'periph': per}
    return out


def net_checks(needs):
    """The net-scope verdict for each wired-together pair (the sense wire on the LED line). -> [{a, b, verdict, condition, reason, cite, applies}]"""
    out = []
    for watcher, driver in NET_LINKS:
        ws = [n for n in needs if n['job'] == watcher]
        ds = [n for n in needs if n['job'] == driver and n['kind'] in ('digital-out', 'pwm-out')]
        if not ws or not (ds or [n for n in needs if n['job'] == driver]):
            continue
        for w in ws:
            if not ds:
                out.append({'a': w['id'], 'b': driver, 'verdict': 'undetermined', 'condition': '', 'applies': False,
                            'reason': 'the %s is not driven straight from a pin on this route, so the tap point of the sense wire is not modelled' % driver, 'cite': ''})
                continue
            r = MC.evaluate(_p(w), _p(ds[0]), 'net')
            out.append({'a': w['id'], 'b': ds[0]['id'], 'verdict': r['verdict'], 'condition': r['condition'], 'reason': r['reason'], 'cite': r['cite'], 'applies': True})
    return out


def _fail_reason(needs, optmap, rejmap, rules, nodes, bounded):
    for n in needs:
        if not optmap[n['id']]:
            kinds = {}
            for r in rejmap[n['id']]:
                kinds.setdefault(r['kind'], []).append(r)
            named = '; '.join('%s: %s' % (k, ', '.join(sorted({x['pin'] for x in v})[:6]) + (' ...' if len({x['pin'] for x in v}) > 6 else '')) for k, v in sorted(kinds.items()) if k != 'no-function')
            return {'need': n['id'], 'kind': 'no-pin', 'why': '%s has no pin: %d pins carry none of %s; refused - %s' % (
                n['part'], len(kinds.get('no-function', [])), ' / '.join(n['patterns']), named or 'none other')}
    ids = [n['id'] for n in needs]
    for size in range(2, min(5, len(needs)) + 1):
        for sub in itertools.combinations(range(len(needs)), size):
            union = {o['pin'] for i in sub for o in optmap[ids[i]]}
            sharing = any(rules[(a, b)]['share'] for a, b in itertools.combinations(sub, 2))
            if len(union) < size and not sharing:
                return {'need': ids[sub[0]], 'kind': 'outnumbered', 'why': '%d needs (%s) compete for only %d pin(s) (%s) and may not share them' % (
                    size, ', '.join(needs[i]['part'] for i in sub), len(union), ', '.join(sorted(union)))}
    return {'need': ids[0] if ids else '', 'kind': 'no-combination' if not bounded else 'bounded',
            'why': ('no combination of pins satisfies every pairwise rule (%d search nodes)' % nodes) if not bounded else 'the search hit its node limit (%d) without finding a placement' % nodes}


def assign(needs, oracle, max_nodes=20000, share='none'):
    """-> {ok, assignment {need_id: option}, cost, nodes, bounded, sharing [...], nets [...], fail, optmap, rejmap}"""
    optmap, rejmap = {}, {}
    for n in needs:
        opts, rej = oracle.options(n)
        optmap[n['id']] = sorted(oracle.with_bench(n, opts), key=lambda o: (o['nonbench'], o['spec'], o['index']))
        rejmap[n['id']] = rej
    rules = pair_rules(needs, share)
    nets = net_checks(needs)
    base = {'ok': False, 'assignment': {}, 'cost': None, 'nodes': 0, 'bounded': False, 'sharing': [], 'nets': nets, 'fail': None, 'optmap': optmap, 'rejmap': rejmap}
    bad_net = next((x for x in nets if x['applies'] and x['verdict'] == 'exclusive'), None)
    if bad_net:
        return dict(base, fail={'need': bad_net['a'], 'kind': 'colocation', 'why': 'the wire from %s to %s is exclusive at net scope: %s' % (bad_net['a'], bad_net['b'], bad_net['reason'])})
    if any(not optmap[n['id']] for n in needs):
        return dict(base, fail=_fail_reason(needs, optmap, rejmap, rules, 0, False))
    idx = {n['id']: i for i, n in enumerate(needs)}
    order = sorted(needs, key=lambda n: (not n['reserved'], PP.IMPORTANCE.index(n['importance']), len(optmap[n['id']]), n['id']))
    can_share = {n['id']: any(rules[tuple(sorted((idx[n['id']], j)))]['share'] for j in range(len(needs)) if j != idx[n['id']]) for n in needs}
    lb_pins, lb_spec = [0] * (len(order) + 1), [0.0] * (len(order) + 1)
    for k in range(len(order) - 1, -1, -1):
        n = order[k]
        solo = not can_share[n['id']]
        lb_pins[k] = lb_pins[k + 1] + (1 if solo else 0)
        lb_spec[k] = lb_spec[k + 1] + (min(o['spec'] for o in optmap[n['id']]) if solo else 0.0)
    state = {'best': None, 'assign': None, 'nodes': 0, 'bounded': False}
    chosen, pins = {}, {}

    def rec(k, cost):
        state['nodes'] += 1
        if state['nodes'] > max_nodes:
            state['bounded'] = True
            return
        lb = (cost[0] + lb_pins[k], cost[1], round(cost[2] + lb_spec[k], 4))
        if state['best'] is not None and lb >= state['best']:
            return
        if k == len(order):
            state['best'], state['assign'] = cost, {nid: dict(o) for nid, o in chosen.items()}
            return
        n = order[k]
        i = idx[n['id']]
        for o in optmap[n['id']]:
            occupants = pins.get(o['pin'], [])
            if occupants and not all(rules[tuple(sorted((i, idx[m])))]['share'] for m in occupants):
                continue
            if any(rules[tuple(sorted((i, idx[mid])))]['periph_exclusive'] for mid in chosen if mid != n['id']):
                continue
            add = (0, o['nonbench'], 0.0) if occupants else (1, o['nonbench'], o['spec'])
            chosen[n['id']] = o
            pins.setdefault(o['pin'], []).append(n['id'])
            rec(k + 1, (cost[0] + add[0], cost[1] + add[1], round(cost[2] + add[2], 4)))
            pins[o['pin']].pop()
            if not pins[o['pin']]:
                del pins[o['pin']]
            del chosen[n['id']]
            if state['bounded']:
                return

    rec(0, (0, 0, 0.0))
    if state['best'] is None:
        return dict(base, nodes=state['nodes'], bounded=state['bounded'], fail=_fail_reason(needs, optmap, rejmap, rules, state['nodes'], state['bounded']))
    pc = []
    for (i, j), r in sorted(rules.items()):
        if needs[i]['id'] in state['assign'] and needs[j]['id'] in state['assign'] and r['periph'] and r['periph']['verdict'] in ('conditional', 'undetermined') and r['periph']['rule'] != 'periph.gpio-port':
            pc.append({'a': needs[i]['id'], 'b': needs[j]['id'], 'verdict': r['periph']['verdict'], 'condition': r['periph']['condition'] or r['periph']['reason'][:200], 'cite': r['periph']['cite']})
    shared = []
    by_pin = {}
    for nid, o in state['assign'].items():
        by_pin.setdefault(o['pin'], []).append(nid)
    for pin, ids in sorted(by_pin.items()):
        if len(ids) > 1:
            conds = [c for a, b in itertools.combinations(sorted(ids, key=idx.get), 2) for c in rules[(idx[a], idx[b])]['conditions']]
            shared.append({'pin': pin, 'needs': ids, 'conditions': conds})
    return dict(base, ok=True, assignment=state['assign'], cost=state['best'], nodes=state['nodes'], bounded=state['bounded'], sharing=shared, periph=pc)


def place_by_importance(needs, job_order, oracle, max_nodes=20000, share='none'):
    """When the full set cannot be placed: drop whole jobs, the least important first, until the rest fit.
    -> (result of assign() on the kept needs, [dropped {job, importance, purposes, why}], full-set failure). The transport (reserved) is never dropped.
    Equal importance: the job LATER in the Mission's order is dropped first (a tie, said)."""
    full = assign(needs, oracle, max_nodes, share)
    jobs = [j for j in job_order if any(n['job'] == j and not n['reserved'] for n in needs)]
    imp = {j: min((n['importance'] for n in needs if n['job'] == j), key=PP.IMPORTANCE.index) for j in jobs}
    pos = {j: i for i, j in enumerate(job_order)}
    subsets = []
    for r in range(1, len(jobs) + 1):
        for drop in itertools.combinations(jobs, r):
            weight = tuple(sum(1 for j in drop if imp[j] == lvl) for lvl in PP.IMPORTANCE)
            subsets.append((weight, tuple(-pos[j] for j in sorted(drop, key=pos.get)), drop))
    subsets.sort(key=lambda s: (s[0], s[1], s[2]))
    for _w, _t, drop in subsets:
        kept = [n for n in needs if n['job'] not in drop]
        res = assign(kept, oracle, max_nodes, share)
        if res['ok']:
            lost = []
            for j in sorted(drop, key=pos.get):
                ns = [n for n in needs if n['job'] == j]
                lost.append({'job': j, 'importance': imp[j], 'purposes': sorted({p for n in ns for p in n['purposes']}),
                             'role': ns[0]['role'], 'why': (full['fail'] or {}).get('why', 'the pins ran out')})
            return res, lost, full
    return None, [], full
