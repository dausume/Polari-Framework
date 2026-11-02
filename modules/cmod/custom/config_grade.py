"""
@module cmod.custom.config_grade

cfg-0: FROM CHECK RESULTS TO A VERDICT, A SCORE AND THE AUTOMATIC DEFAULT. Pure functions over dicts; nothing here reads or writes rows.

  verdict(results) -> (verdict, why)    the worst outcome of the checks that ran. No check ran -> compromise ("not checked"): an option is never
                                        called ideal without evidence.
  score(graded, weights=None)           competitive scoring over the VALID options only (the competitive-scoring rule): per term min-max (best = 1,
                                        worst = 0), weighted, then the combined value min-max again to 0..100. A set of one, or a tie, = 100 with
                                        "no competition". Invalid options get 0 and are left out of the set.
            terms: margin  the smallest margin any check reported (more is better)
                   cost    how many things it gives up (fewer is better)
  default(graded) -> the graded option chosen automatically: ideal above compromise, then the higher score, then the name; None when all are invalid
  gives_up(chosen, auto) -> words: what a person's choice gives up against the automatic one
"""
from cmod.custom.config_groups import rank

#: the scoring weights (knobs)
DEFAULT_WEIGHTS = {'margin': 1.0, 'cost': 0.5}


def verdict(results):
    ran = [r for r in results if r['outcome'] != 'skipped']
    if not ran:
        return 'compromise', 'not checked: no check applies to this option yet, so it cannot be called ideal'
    worst = min(ran, key=lambda r: rank(r['outcome']))
    if worst['outcome'] == 'ideal':
        return 'ideal', 'every check passed with the full recommended margin'
    return worst['outcome'], '%s: %s' % (worst['check'], worst['why'])


def _terms(g):
    ran = [r for r in g['results'] if r['outcome'] != 'skipped']
    gave = [r for r in ran if r.get('gives_up')]
    return {'margin': min([r['margin'] for r in ran] or [0.0]), 'cost': float(len(gave) + (0 if ran else 1))}


def score(graded, weights=None):
    w = dict(DEFAULT_WEIGHTS, **(weights or {}))
    valid = [g for g in graded if g['verdict'] != 'invalid']
    for g in graded:
        g['score'], g['score_why'] = 0.0, 'invalid: left out of the scoring'
    if not valid:
        return graded
    terms = {id(g): _terms(g) for g in valid}
    combined = {}
    for g in valid:
        total = 0.0
        for term, better_high in (('margin', True), ('cost', False)):
            vals = [terms[id(x)][term] for x in valid]
            lo, hi = min(vals), max(vals)
            v = terms[id(g)][term]
            n = 1.0 if hi == lo else (v - lo) / (hi - lo)
            total += w[term] * (n if better_high else 1.0 - n)
        combined[id(g)] = total
    lo, hi = min(combined.values()), max(combined.values())
    for g in valid:
        if hi == lo:
            g['score'], g['score_why'] = 100.0, 'no competition (%s)' % ('a set of one' if len(valid) == 1 else 'every valid option ties')
        else:
            g['score'] = round(100.0 * (combined[id(g)] - lo) / (hi - lo), 1)
            g['score_why'] = 'among %d valid options: margin %.3f, gives up %d thing(s)' % (len(valid), terms[id(g)]['margin'], terms[id(g)]['cost'])
    return graded


def default(graded):
    valid = [g for g in graded if g['verdict'] != 'invalid']
    if not valid:
        return None
    return sorted(valid, key=lambda g: (-rank(g['verdict']), -g['score'], g['option']['name']))[0]


def gives_up(chosen, auto):
    if auto is None or chosen['option']['name'] == auto['option']['name']:
        return 'nothing: it is the automatic choice'
    parts = ['%s (score %g) instead of the automatic %s "%s" (%s, score %g)' % (chosen['verdict'], chosen['score'], auto['verdict'],
                                                                          auto['option']['name'], auto['option'].get('title') or '-', auto['score'])]
    costs = [r['gives_up'] for r in chosen['results'] if r.get('gives_up')]
    if costs:
        parts.append('it gives up: ' + '; '.join(costs))
    return ' - '.join(parts)
