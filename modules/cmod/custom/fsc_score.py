"""
@module cmod.custom.fsc_score

fsc-2: the SCORER. Score = sum_p alpha_p x ( sum_t w_t,p x norm(v_t,p) / sum_t w_t,p ), then COMPETITIVE across the compared set (his ruling 2026-10-18: "the top scorer is normalized to the
top score and the bottom score to 0 and the rest distributed in between"):
  PER TERM     min-max over the compared solutions (best 100, worst 0, linear between; direction from the term is_positive) - the scoring engine's own `normalize_value` with the
               `min-max-auto` method. Chip limits are never bounds (they stay in the basis text). A set of one, or every solution tied on a term -> 100 for all, "no competition on this term".
               A stand-in competes AT its stand-in and is marked. A term nobody has a value for competes as tied (no basis); one only some have scores the others at the midpoint (stated).
  PER PROFILE  the weighted result is min-max normalized again within the profile column (top 100, bottom 0); the raw weighted value is kept in the breakdown.
  COMPARED SET every non-failed solution handed in (the caller says which: finished only, plans only, or both). Failures never enter it.
Ties are broken by the solver's own rank (the same deterministic chain sol-0 uses; `tie_rank` {id: rank} names another objective's order for the reproduction proof). A profile in `sol-0-compatible` mode feeds sol-0's raw FRACTIONS (absolute bounds, the profile's
compat_weights) and, for fastest-cycle, the bench gate, so sol-0's ranking is reproduced exactly; it is never the default.
"""
from scoring.custom.scoring_engine import normalize_value

from cmod.custom import fsc_terms as T

_DEF = {'accept_used': True, 'accept_local': True}
MONEY = ('bom-cost', 'cost-to-build-now')
EPS = 1e-9


def _term_meta():
    return {r['name']: r for r in T.term_rows()}


def _group_value(rec, term, purpose, ctx, knobs, cache):
    """The q of (record, term, group). Money terms are recomputed when the profile accepts other offers than the defaults."""
    if term in MONEY and any(knobs.get(k, True) != _DEF[k] for k in _DEF):
        key = (rec['id'], tuple(sorted((k, knobs.get(k, True)) for k in _DEF)))
        if key not in cache:
            from cmod.custom import fsc_values as V
            cache[key] = V.money(rec['candidate'], rec['facts'], ctx, {k: knobs.get(k, True) for k in _DEF})
        m = cache[key]
        if purpose:
            return (m['per_purpose'].get(purpose) or {}).get('bom' if term == 'bom-cost' else 'build')
        return m['bom'] if term == 'bom-cost' else m['build']
    src = rec['purpose_values'].get(purpose, {}) if purpose else rec['values']
    return src.get(term)


def _resolve_entries(records, profile, ctx, knobs, cache):
    """Apply fallbacks: an entry with `fallback` whose term has no CITED value anywhere in the set is replaced by its fallback terms (weights scaled to the entry weight)."""
    out, notes = [], []
    for e in profile['entries']:
        fb = e.get('fallback')
        if fb:
            vals = [_group_value(r, e['term'], e.get('purpose', ''), ctx, knobs, cache) for r in records]
            if not any(v and v['kind'] == 'cited' for v in vals):
                tot = sum(x['weight'] for x in fb) or 1.0
                for x in fb:
                    out.append({'term': x['term'], 'weight': e['weight'] * x['weight'] / tot, 'purpose': e.get('purpose', ''),
                                'fallback_for': e['term']})
                notes.append('%s has no cited price for any compared solution, so %s stands in for it' % (e['term'], ' + '.join(x['term'] for x in fb)))
                continue
        out.append({'term': e['term'], 'weight': e['weight'], 'purpose': e.get('purpose', '')})
    return out, notes


def _norm(values, term, positive, mode, ids):
    """-> {id: (normalized 0..1, how)} for one (term, group): competitive min-max-auto, or the absolute sol-0 bounds in compatible mode."""
    pool = [v['value'] for v in values.values() if v is not None]
    absolute = mode == 'sol-0-compatible' and term in T.ABS_BOUNDS
    out = {}
    if not pool:
        return {i: (1.0, 'no competition on this term: nobody has a value (no basis yet)') for i in ids}
    if absolute:
        lo, hi = T.ABS_BOUNDS[term]
        for i in ids:
            v = values.get(i)
            if v is None:
                out[i] = (T.ABSENT_NORMALIZED, 'no value: scored at the midpoint (stand-in)')
                continue
            ok, n, _a = normalize_value(v['value'], {'method': 'min-max', 'min': lo, 'max': hi}, positive)
            out[i] = (n, 'sol-0-compatible: absolute bounds %s..%s (sol-0\'s own fractions)' % (lo, hi))
        return out
    if len(ids) < 2 or max(pool) - min(pool) < EPS:
        why = 'no competition on this term' + (' (a set of one)' if len(ids) < 2 else ' (every solution ties at %s)' % pool[0])
        return {i: (1.0, why) for i in ids}
    lo, hi = min(pool), max(pool)
    for i in ids:
        v = values.get(i)
        if v is None:
            out[i] = (T.ABSENT_NORMALIZED, 'no value for this solution: scored at the midpoint (stand-in)')
            continue
        ok, n, a = normalize_value(v['value'], {'method': 'min-max-auto'}, positive, pool)
        out[i] = (n, 'competitive min-max over %d solutions: best %s -> 100, worst %s -> 0%s' % (len(ids), hi if positive else lo, lo if positive else hi, '' if positive else ' (lower is better)'))
    return out


def score_profile(records, profile, ctx, mode=None, set_words='', tie_rank=None):
    """-> {profile, mode, set, notes, order [ids], scores {id: {raw, score, rank, confidence, rows [...], groups [...]}}}. `records` = the non-failed subject records (id, rank, values,
    purpose_values, candidate, facts)."""
    knobs = profile['knobs']
    mode = mode or knobs.get('normalization', 'competitive')
    assert mode in T.NORMALIZATIONS, mode
    meta = _term_meta()
    cache = {}
    ids = [r['id'] for r in records]
    by_id = {r['id']: r for r in records}
    entries, notes = _resolve_entries(records, profile, ctx, knobs, cache)
    if mode == 'sol-0-compatible' and knobs.get('compat_weights'):
        entries = [dict(e, weight=knobs['compat_weights'].get(e['term'], e['weight'])) for e in entries]
        notes.append('sol-0-compatible: weights are the profile compat_weights and the terms are fed as sol-0\'s raw fractions (absolute bounds)')
    groups = {}
    for e in entries:
        groups.setdefault(e['purpose'] or '*', []).append(e)
    alpha_knob = knobs.get('alpha') or {}
    alpha = {}
    for g in groups:
        if g == '*':
            alpha[g] = alpha_knob.get('*', ctx['importance_weights'].get('required', 3.0))
        else:
            alpha[g] = alpha_knob.get(g, (ctx['by_name'].get(g) or {}).get('weight', ctx['importance_weights'].get('required', 3.0)))
    asum = sum(alpha.values()) or 1.0
    res = {i: {'rows': [], 'groups': [], 'raw': 0.0, 'conf_num': 0.0, 'conf_den': 0.0} for i in ids}
    for g, es in groups.items():
        wsum = sum(e['weight'] for e in es) or 1.0
        gscore = {i: 0.0 for i in ids}
        for e in es:
            term = e['term']
            vals = {i: _group_value(by_id[i], term, e['purpose'], ctx, knobs, cache) for i in ids}
            positive = meta[term]['is_positive']
            norms = _norm(vals, term, positive, mode, ids)
            for i in ids:
                n, how = norms[i]
                v = vals[i]
                share = e['weight'] / wsum
                gscore[i] += share * n
                points = alpha[g] / asum * share * n * 100.0
                kind = v['kind'] if v else 'stand-in'
                res[i]['rows'].append({'term': term, 'label': meta[term]['display_name'], 'context': ('purpose:%s' % g) if g != '*' else 'hardware:%s' % by_id[i]['candidate']['hardware']['board'],
                                       'purpose': e['purpose'], 'value': v['value'] if v else None, 'unit': meta[term]['unit'], 'kind': kind,
                                       'basis': v['basis'] if v else 'no value: no basis yet for this term', 'normalized': round(n * 100.0, 4), 'normalization': how,
                                       'weight': round(e['weight'], 6), 'weight_share': round(share, 6), 'alpha': round(alpha[g] / asum, 6), 'points': round(points, 4),
                                       'fallback_for': e.get('fallback_for', '')})
                res[i]['conf_num'] += alpha[g] / asum * share * T.KIND_CONFIDENCE.get(kind, 0.0)
                res[i]['conf_den'] += alpha[g] / asum * share
        for i in ids:
            res[i]['raw'] += alpha[g] / asum * gscore[i]
            res[i]['groups'].append({'group': g, 'alpha': round(alpha[g] / asum, 6), 'weighted': round(gscore[i], 6)})
    raws = [res[i]['raw'] for i in ids]
    lo, hi = (min(raws), max(raws)) if raws else (0, 0)
    for i in ids:
        r = res[i]
        if len(ids) < 2 or hi - lo < EPS:
            r['score'], r['profile_norm'] = 100.0, 'no competition in this profile column (%s)' % ('a set of one' if len(ids) < 2 else 'every solution ties')
        else:
            r['score'], r['profile_norm'] = 100.0 * (r['raw'] - lo) / (hi - lo), 'competitive min-max within the profile column: best %.4f -> 100, worst %.4f -> 0' % (hi, lo)
        r['confidence'] = round(100.0 * r['conf_num'] / r['conf_den'], 2) if r['conf_den'] else 0.0
        r['score'], r['raw'] = round(r['score'], 4), round(r['raw'], 6)
        del r['conf_num'], r['conf_den']

    def key(i):
        rec = by_id[i]
        gate = (len(rec['candidate']['parts_missing']) > 0) if (mode == 'sol-0-compatible' and knobs.get('bench_gate')) else False
        return (gate, -round(res[i]['raw'], 9), (tie_rank or {}).get(i, rec['rank']))
    order = sorted(ids, key=key)
    for n, i in enumerate(order):
        res[i]['rank'] = n + 1
    return {'profile': profile['name'], 'mode': mode, 'set': set_words or '%d non-failed solutions' % len(ids), 'notes': notes, 'order': order, 'scores': res}
