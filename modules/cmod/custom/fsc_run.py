"""
@module cmod.custom.fsc_run

fsc-0..2: the ORCHESTRATOR. One Mission -> the solve candidates (cmod.custom.solve_doors.compute, cached) -> distinct plans (the same plan on another package of the same board is one
row that says so, as the score card does) -> each is FAILED (cmod.custom.fsc_failure), or scored: linked to the built firmware that realises it (cmod.custom.fsc_link), marked
finished | plan, and given its term values (cmod.custom.fsc_values). `scores()` then runs profiles over the compared set (cmod.custom.fsc_score).

    build(mission, manager=None, boards=None) -> {mission, records [non-failed, solver order], failures [...], suggestions [...], unmatched_configs [...], ctx, counts}
    scores(built, profiles, scope='both', mode=None) -> {profiles {name: result}, rows [one per record], set_words}
"""
from cmod.custom import fsc_failure as F
from cmod.custom import fsc_labels as LB
from cmod.custom import fsc_link as L
from cmod.custom import fsc_values as V
from cmod.custom import fsc_profiles as P
from cmod.custom import solve_inputs as SI

_CACHE = {}
_SCORES = {}   # fsc-3: score results by their inputs (see scores())
_CTX = {}
LADDER_ROUTE = {'declared': 0, 'template-exists': 0, 'compiles': 0, 'proven-on-twin': 50, 'proven-on-hardware': 100}


def _twin_key(c):
    return (c['hardware']['board'], c['tier'], tuple(sorted(c['routes'].items())), tuple((a['need'], a['pin']) for a in c['assignment']), c['rank_class'], tuple(l['job'] for l in c['lost']))


def solution_name(mission, c):
    return 'msol:%s:%s' % (mission, c['id'])


def _evidence(c, link, proof, ctx, manager):
    from cmod.custom import isotope_variants as IV
    from cmod.custom import fsc_terms as T
    statuses, _ok, mean = proof
    if link is not None:
        built, _w, _st = L.built_state(link['config'], list(c['routes']), ctx, manager)
        if built:
            return T.q('measured' if manager is not None else 'stand-in', round(mean, 2), 'mean over the %d Purposes of the Mission of the proof ladder (none 0, twin 50, hardware 100) for built config %s: %s%s' % (
                len(statuses), link['config'], '; '.join('%s %s' % (p, s) for p, (s, _w2) in sorted(statuses.items())),
                '' if manager is not None else ' (no live server: the seeded statuses are read back unchanged, not evidence)'))
    sts = []
    for j, r in sorted(c['routes'].items()):
        v = (ctx['variants'].get(j) or {}).get(r)
        sts.append((j, r, IV.status(v, manager)['status'] if v is not None else 'declared'))
    val = sum(LADDER_ROUTE.get(s, 0) for _j, _r, s in sts) / float(len(sts) or 1)
    return T.q('estimated', round(val, 2), 'no firmware is built for exactly this plan; the mean proof of its routes: %s' % ', '.join('%s:%s %s' % x for x in sts))


def build(mission, manager=None, boards=None, importance_weights=None, unprovable='block'):
    from cmod.custom import solve_doors as SD
    from cmod.custom import fsc_prices as PR
    res = SD.compute(mission, boards, None, None, {}, manager)
    ck = SI.sha([res['inputs']['mission_row'], res['inputs']['profiles'], importance_weights])
    if ck not in _CTX:       # the Mission read costs seconds with a live manager (pin-profile roll-up): remembered by the solve's own input hashes
        if len(_CTX) > 4:
            _CTX.pop(next(iter(_CTX)))
        _CTX[ck] = V_ctx(mission, manager, importance_weights)
    ctx = _CTX[ck]
    proof = L.purposes_proof(ctx, manager, unprovable)
    po = PR.load()
    key = SI.sha([res['result_sha256'], boards, importance_weights, {p: s for p, (s, _w) in proof[0].items()}, manager is not None, unprovable, po['path'], len(po['offers']), po['present']])
    if key in _CACHE:
        return _CACHE[key]
    ranked = res['_ranked']
    reps, seen = [], {}
    for c in ranked:
        k = _twin_key(c)
        if k in seen:
            seen[k]['also_on'].append(c['hardware']['package'] or 'package not modelled')
            continue
        c['also_on'] = []
        seen[k] = c
        reps.append(c)
    jobs_vary = LB.varying_jobs(ranked)
    tier_vary = LB.tiers_vary(ranked)
    failures, ok = [], []
    for c in reps:
        f = F.failure_of(c)
        if f:
            failures.append(dict(f, id=c['id'], solution=solution_name(mission, c), routes=c['routes_text'], hardware=c['hardware']['board'], rank=c['rank'], state='failed', short_label=LB.short_label(c, jobs_vary, tier_vary)))
        else:
            ok.append(c)
    links, unmatched = L.resolve(list(res['jobs']), ok, manager)
    runs_on = {}
    for c in ok:
        runs_on.setdefault(tuple(sorted(c['routes'].items())), set()).add((c['hardware']['board'], c['hardware']['package'], c['tier']))
        for pk in c['also_on']:
            runs_on[tuple(sorted(c['routes'].items()))].add((c['hardware']['board'], pk, c['tier']))
    records = []
    for c in ok:
        link = links.get(c['id'])
        st = L.state_of(c, link, ctx, proof, manager)
        f = V.facts(c, ctx, manager)
        n = len(runs_on[tuple(sorted(c['routes'].items()))]) - 1
        hw = V.hardware_values(c, ctx, f, _evidence(c, link, proof, ctx, manager), n, manager)
        pv = V.purpose_values(c, ctx, f, manager)
        rts = [d['route-time'] for d in pv.values() if 'route-time' in d]
        hw['route-time'] = V.T.q(V.T.weakest([x['kind'] for x in rts]), round(sum(x['value'] for x in rts), 3), 'route work counted once: the sum of the Purposes\' attributed shares (a shared route is split by importance weight, so it is not counted twice)')
        records.append({'id': c['id'], 'name': solution_name(mission, c), 'rank': c['rank'], 'candidate': c, 'facts': f, 'state': st['state'], 'state_why': st['why'], 'link': link,
                        'values': hw, 'purpose_values': pv, 'also_on': c['also_on'], 'label': (link['config'] if link and st['state'] == 'finished' else c['routes_text']), 'short_label': LB.short_label(c, jobs_vary, tier_vary),
                        'unflagged_deadline_misses': F.unflagged_violations(c)})
    out = {'mission': mission, 'records': records, 'failures': failures, 'suggestions': F.suggestions(ctx['purposes']), 'unmatched_configs': unmatched, 'ctx': ctx,
           'counts': {'candidates': len(ranked), 'distinct_plans': len(reps), 'failed': len(failures), 'finished': sum(1 for r in records if r['state'] == 'finished'),
                      'plan': sum(1 for r in records if r['state'] == 'plan')}, 'solve_sha256': res['result_sha256'], 'proof': proof[0], 'cache_key': key}
    if len(_CACHE) > 4:
        _CACHE.pop(next(iter(_CACHE)))
    _CACHE[key] = out
    return out


def V_ctx(mission, manager, importance_weights):
    from cmod.custom import fsc_context as C
    return C.mission_context(mission, manager, importance_weights)


SCOPES = ('both', 'finished', 'plan')


def compared(built, scope='both'):
    recs = [r for r in built['records'] if scope == 'both' or r['state'] == scope]
    words = {'both': 'every non-failed solution (finished and plan)', 'finished': 'finished solutions only', 'plan': 'plans only (not yet built)'}[scope]
    return recs, '%s: %d solution(s); failures never enter the set' % (words, len(recs))


def profile_sha(p):
    """A profile's identity for caching: its terms and weights, knobs, name (a weight edit changes it, so the cached result can never be stale)."""
    return SI.sha([p['name'], p['entries'], p['knobs']])


def clear_scores(name=None):
    """Drop the cached score results of profile `name` (all of them when None). A profile edit calls this; the key already changes with the weights, so this only frees the old results."""
    for k in [k for k in _SCORES if name is None or k[3] == name]:
        del _SCORES[k]


def scores(built, profiles, scope='both', mode=None):
    """-> {profiles {name: score_profile result}, set_words, rows [{id, solution, label, short_label, state, state_why, link, scores {profile: {score, rank, raw, confidence}}}]}.

    fsc-3: CACHED per profile by (the build's own input key - Mission row sha, solve sha, ScenarioRun statuses, offers file - the scope, the mode, the profile's sha INCLUDING its
    weights), so a row click or a tab change never recomputes the compared set; a profile edit changes that profile's sha and clear_scores() frees the old results."""
    from cmod.custom import fsc_score as S
    recs, words = compared(built, scope)
    results = {}
    for p in profiles:
        k = (built.get('cache_key'), scope, mode, p['name'], profile_sha(p))
        if built.get('cache_key') is not None and k in _SCORES:
            results[p['name']] = _SCORES[k]
            continue
        results[p['name']] = S.score_profile(recs, p, built['ctx'], mode, words)
        if built.get('cache_key') is not None:
            if len(_SCORES) > 200:
                _SCORES.pop(next(iter(_SCORES)))
            _SCORES[k] = results[p['name']]
    fin = [r['id'] for r in recs if r['state'] == 'finished']
    rows = []
    for r in recs:
        row = {'id': r['id'], 'solution': r['name'], 'label': r['label'], 'short_label': r['short_label'], 'state': r['state'], 'state_why': r['state_why'], 'routes': r['candidate']['routes_text'], 'hardware': r['candidate']['hardware']['board'],
               'also_on': r['also_on'], 'link': r['link'], 'scores': {}}
        for pn, res in results.items():
            s = res['scores'][r['id']]
            fin_rank = [i for i in res['order'] if i in fin].index(r['id']) + 1 if r['id'] in fin else None
            row['scores'][pn] = {'score': s['score'], 'rank': s['rank'], 'rank_among_finished': fin_rank, 'raw': s['raw'], 'confidence': s['confidence']}
        rows.append(row)
    return {'profiles': results, 'set_words': words, 'rows': rows}
