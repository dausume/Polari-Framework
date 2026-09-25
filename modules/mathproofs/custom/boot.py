"""
@module mathproofs.custom.boot

WHAT RUNS AT BOOT (pf-1): after the seed pass, the obligations of every TensorTreeDefinition are (re)generated
from the enabled rules — so the tree panel's badges and the validator's `logic` section exist without a person's
POST — and every claim that has NEVER been run (`conjectured`, no certificate) is checked once through its auto tier.
The cheap tiers cost milliseconds; the z3 tier honours each claim's `budget_s` and a timeout leaves the claim
`conjectured` with an `undecided` run beside it (D-pf-9). The lean tier is NEVER run here (plan §I.9): a claim whose
only tier is lean is listed as awaiting a person or the pipeline. The whole pass is therefore bounded by the aggregate's
worst case (`GET /api/mathproofs/aggregate`), which is the number a person watches. Idempotent: rows are upserted
by name, and a claim with a verdict is never re-run here (staleness is shown, not silently re-decided — a person or
the pipeline re-checks).
"""
import time

from mathproofs.custom import checkers, rules
from mathproofs.custom.rows import _rows


def run_at_boot(manager, log=None, make=None, save=True):
    """`make`/`save` as in rules.generate / checkers.check (a selftest's fake manager passes its own row factory)."""
    log = log or (lambda *_: None)
    t0 = time.time()
    out = {'trees': {}, 'claims_checked': [], 'undecided': [], 'elapsed_s': 0.0}
    for tree in sorted(str(getattr(t, 'name', '')) for t in _rows(manager, 'TensorTreeDefinition')):
        try:
            r = rules.generate(manager, tree, make=make, save=save)
            out['trees'][tree] = r.get('summary') if r.get('ok') else {'error': r.get('error')}
        except Exception as exc:   # one tree's failure never takes the boot with it
            out['trees'][tree] = {'error': '%s: %s' % (type(exc).__name__, exc)}
    for c in sorted(_rows(manager, 'MathClaim'), key=lambda c: str(getattr(c, 'name', ''))):
        if str(getattr(c, 'proof_status', '')) != 'conjectured' or str(getattr(c, 'certificate_ref', '') or ''):
            continue
        if not checkers.terms_of(c):
            continue
        if checkers.auto_tier(checkers.terms_of(c)) == 'lean':
            out.setdefault('awaiting_person', []).append(str(c.name)); continue   # plan §I.9: lean is never automatic
        try:
            r = checkers.check(manager, c, make=make, save=save)
        except Exception as exc:
            out['claims_checked'].append((str(c.name), 'error: %s' % exc)); continue
        out['claims_checked'].append((str(c.name), r['verdict'], r['tier'], r['run']['elapsed_s']))
        if r['verdict'] == 'undecided':
            out['undecided'].append(str(c.name))
    out['elapsed_s'] = round(time.time() - t0, 3)
    log('[MathProofsBoot] trees %s; claims checked %d (%s); undecided within budget: %s; lean claims left to a person/pipeline: %s; %.3f s' % (
        out['trees'], len(out['claims_checked']), ', '.join('%s=%s' % (n[0].split(':')[-1][:28], n[1]) for n in out['claims_checked']) or '-', out['undecided'] or 'none', out.get('awaiting_person') or 'none', out['elapsed_s']))
    return out
