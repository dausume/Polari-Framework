"""
@module cmod.custom.solve

sol-0 (MISSION_PROFILE_SOLVER_PLAN.md sections 2.5, 8.4): the ATTEMPT ENGINE's front door. `solve(mission, boards=None, tiers=None, objective=None, limits=None)` searches
hardware x runtime tier x isotope variants, places each choice's pin profiles on pins (ladder + overlap table + claims, backtracking, least specialised pin first, a reason for
every pin), scores by the Mission's objective, and returns Candidates, a Trade study, a Score card, the pruned-branch log and "Designed for" / "Also runs on". Pure Python, no
engine, nothing stored (cmod.custom.solve_record stores a run). Advised, never blocking. Deterministic.

    python3 -m cmod.custom.solve mission <name> [--board B] [--tier T] [--objective minimum-resources|fastest-cycle] [--occupy D6,D7] [--prefer bench-wiring] [--only-jobs a,b]
                                                [--purposes a,b] [--max-candidates N] [--json]
"""
import json
import time

from cmod.custom import solve_engine as EN
from cmod.custom import solve_inputs as SI
from cmod.custom import solve_report as R


def _package_difference(eng, ranked, w):
    """The package difference, said: the winner's plan on each other package of its board, and the analog-only pins (ADC6 / ADC7) on each package."""
    if w is None or not w['assignment']:
        return []
    out = []
    for c in ranked:
        if c is not w and c['routes'] == w['routes'] and c['tier'] == w['tier'] and c['hardware']['board'] == w['hardware']['board'] and c['hardware']['package'] != w['hardware']['package']:
            same = {a['need']: a['pin'] for a in c['assignment']} == {a['need']: a['pin'] for a in w['assignment']}
            out.append('the same plan on %s: %s; its open rungs: %s' % (c['hardware']['package'], 'the same pins' if same else 'different pins (%s)' % R.pins_text(c),
                                                                       '; '.join(r['text'] for r in c['risks'] if r['kind'] == 'ladder')[:240] or 'none'))
    for (board, pkg), o in sorted(eng.oracles.items()):
        if board != w['hardware']['board']:
            continue
        for lab in ('ADC6', 'ADC7'):
            try:
                r = o.rungs(lab, lab, 'runtime', False)
            except KeyError:
                continue
            blocked = next((x for x in r['rungs'] if x['verdict'] == 'blocked'), None)
            out.append('%s on %s: %s' % (lab, pkg, ('blocked at rung %d (%s): %s' % (blocked['rung'], blocked['name'], blocked['detail'][:140])) if blocked else r['available']))
    return out


def solve(mission, boards=None, tiers=None, objective=None, limits=None, manager=None, spec=None):
    t0 = time.time()
    eng = EN.Engine(mission, boards, tiers, objective, limits, manager, spec).run()
    ranked = R.rank(eng)
    w = ranked[0] if ranked else None
    ok_also, no_also = R.also_runs_on(w, ranked, eng)
    lim = eng.lim
    listed = ranked[:lim['max_candidates']]
    res = {'ok': True, 'mission': eng.row['name'], 'title': eng.row.get('title', ''), 'objective': eng.objective, 'secondary_objective': eng.secondary, 'solver_version': SI.SOLVER_VERSION,
           'boards_asked': boards, 'tiers_asked': tiers, 'boards': eng.boards, 'limits': lim, 'inputs': eng.fingerprint(),
           'hardware': [{'board': h['board'], 'soc': h['soc'], 'package': h['package'], 'usb_interfaces': h['usb_interfaces'], 'variant_pending': h['variant_pending'], 'placeable': h['ladder'],
                         'why_not': h['why_not_ladder']} for h in eng.hardware],
           'jobs': eng.order, 'profiles': [{'role': p['role'], 'kind': p['kind'], 'importance': p['importance'], 'reserved': bool(p.get('reserved'))} for p in eng.profiles],
           'counts': dict(eng.counts, candidates=len(ranked), listed=len(listed), unlisted=len(ranked) - len(listed), pruned=eng.pruned.total),
           'candidates': listed, 'summary': [R.summary(c) for c in ranked], 'chosen_candidate': w, 'chosen': w['id'] if w else '',
           'pruned': eng.pruned.as_dict(), 'pruned_rows': R.pruned_rows(eng.pruned), 'designed_for': R.designed_for(w, eng), 'also_runs_on': ok_also, 'does_not_run_on': no_also,
           'reference_wiring': R.reference_wiring(w, eng), 'package_difference': _package_difference(eng, ranked, w), '_ranked': ranked,
           'notes': ['Advised, never blocking: every number says measured, estimated, cited or undetermined; an undetermined cost is scored at a stated stand-in, never zero.',
                     'A variant that needs a part the bench lacks stays a candidate, ranked below every plan the bench can build, and is named - never called available.',
                     'Open ladder rungs (7 electrical, 9 claims unless a binding is given, 10 isotope requirements) are risks, shown on every pin.']}
    if len(ranked) > len(listed):
        res['notes'].append('%d more candidates were found than the %d listed (limits.max_candidates); all are summarised in the recorded run.' % (len(ranked) - len(listed), len(listed)))
    res['trade_study'] = R.trade_rows(ranked, lim['max_candidates'])
    card = R.score_card_rows(ranked, lim['max_candidates'], eng.objective)
    res['score_card'] = card[:1] + R.unplaced(eng, w) + card[1:]      # what could not be placed explains the choice, so it sits right under it
    res['assignment'] = R.assignment_rows(w)
    body = {'summary': res['summary'], 'chosen': res['chosen'], 'pruned': res['pruned'], 'trade': res['trade_study'], 'inputs': res['inputs'], 'detail': [{k: v for k, v in c.items()} for c in listed]}
    res['result_sha256'] = SI.sha(body)
    res['duration_s'] = round(time.time() - t0, 3)
    return res


def public(res):
    """The run as JSON-safe plain data (no internal handles)."""
    return {k: v for k, v in res.items() if not k.startswith('_')}


def view(res, name):
    return R.view_rows(res, name)


# ------------------------------------------------------------------ CLI
def _print(res):
    c = res['chosen_candidate']
    print('Mission %s - objective %s (secondary: %s) - %d candidates (%d listed), %d branches pruned, %.1f s' % (
        res['mission'], res['objective'], res['secondary_objective'], res['counts']['candidates'], res['counts']['listed'], res['pruned']['total'], res['duration_s']))
    if c is None:
        print('  NO candidate could be formed.')
    else:
        print('Chosen: %s' % R.label(c))
        for a in res['assignment']:
            print('  %-34s %-4s %-8s %s' % (a['need'], a['pin'], a['function'], a['why_this_pin']))
    print('Score card (the ranking with the deciding differences):')
    for r in res['score_card'][:12]:
        print('  #%-3d %-26s %-9s %s' % (r['rank'], r['verdict'], r['score'], r['candidate']))
        print('        vs the chosen: %s' % r['deciding_difference'])
    if res['designed_for']:
        d = res['designed_for']
        print('Designed for: %s / %s (%s)' % (d['hardware'], d['tier'], ', '.join('%s via %s' % kv for kv in sorted(d['variants'].items()))))
    for x in res['also_runs_on']:
        print('Also runs on: %s / %s - %s' % (x['hardware'], x['tier'], x['what_changed']))
    for x in res['does_not_run_on'][:8]:
        print('Does not run on: %s / %s - %s' % (x['hardware'], x['tier'], x['why'][:160]))
    for x in res['package_difference']:
        print('Package: %s' % x)
    print('Pruned: ' + '; '.join('%s %d' % (k, v['count']) for k, v in res['pruned']['by_kind'].items()))


def main(argv=None):
    import argparse
    import sys
    ap = argparse.ArgumentParser(prog='pol capability solve')
    ap.add_argument('cmd', choices=['mission'])
    ap.add_argument('name')
    ap.add_argument('--board', default='')
    ap.add_argument('--tier', default='')
    ap.add_argument('--objective', default='')
    ap.add_argument('--occupy', default='', help='comma list of pins to treat as occupied (a synthetic claim)')
    ap.add_argument('--prefer', default='')
    ap.add_argument('--only-jobs', default='')
    ap.add_argument('--purposes', default='')
    ap.add_argument('--max-candidates', type=int, default=0)
    ap.add_argument('--json', action='store_true')
    a = ap.parse_args(argv if argv is not None else sys.argv[1:])
    lim = {}
    if a.occupy:
        lim['occupied'] = [{'pin': p, 'by': 'the command line', 'why': 'occupied on request (--occupy)', 'blocks': 'all'} for p in a.occupy.split(',') if p]
    if a.prefer:
        lim['prefer'] = a.prefer
    if a.only_jobs:
        lim['only_jobs'] = [x for x in a.only_jobs.split(',') if x]
    if a.purposes:
        lim['purposes'] = [x for x in a.purposes.split(',') if x]
    if a.max_candidates:
        lim['max_candidates'] = a.max_candidates
    try:
        res = solve(a.name, boards=[a.board] if a.board else None, tiers=[a.tier] if a.tier else None, objective=a.objective or None, limits=lim)
    except (ValueError, KeyError) as e:
        print('[REFUSED] %s' % (e.args[0] if e.args else e))
        return 3
    if a.json:
        print(json.dumps(public(res), indent=1, default=str))
    else:
        _print(res)
    return 0


if __name__ == '__main__':
    import sys
    sys.exit(main())
