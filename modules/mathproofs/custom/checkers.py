"""
@module mathproofs.custom.checkers

RUN a claim through a tier and WRITE what happened (plan §I.3/I.9): a ProofRun row (checker, version, verdict,
detail, the rows-state hash) and the claim's `proof_status` / `checker` / `certificate_ref` / `counterexample_json`
/ `evidence_level` — by the honest vocabulary:

    numeric  holds → witnessed (evidence measured: on THESE rows)      refuted → refuted (counterexample kept)
    any      undetermined → undetermined: the statement is NOT DEFINED here (a `given` premise fails, a value is
             unrecorded) — the model shifts with the state space; nothing is falsified
    interval holds → decided   (evidence analytical: exact set arithmetic)
    sympy    holds → checked-symbolically (analytical: over symbols)
    z3       holds → decided (analytical: a decision procedure over the continuum / machine integers)
             refuted → refuted (the model IS the counterexample)   no answer within `budget_s` → the ProofRun says
             `undecided` (budget) and the claim's status is UNCHANGED (D-pf-9: absence of a decision ≠ a counterexample)
    lean     ok    → proved (analytical)                                                       [pf-2]
    human    a signed note → proved, labelled `human` (D-pf-6)
A refuted claim never deletes anything; a tier that cannot lower the term writes `unprovable-here` naming why.
`auto_tier(term)` picks the cheapest tier that can speak to a term; `check(manager, claim, tier=None)` runs it.
`stale(manager, claim)` says whether the last run's rows-state hash still matches.
"""
import datetime
import json
import time

from mathproofs.custom import numeric, symbolic, terms, z3tier
from mathproofs.custom.rows import rows_state_hash, by_name, _rows

STATUS_FOR = {('numeric', 'holds'): ('witnessed', 'measured'), ('interval', 'holds'): ('decided', 'analytical'),
              ('sympy', 'holds'): ('checked-symbolically', 'analytical'), ('z3', 'holds'): ('decided', 'analytical'),
              ('lean', 'holds'): ('proved', 'analytical'), ('human', 'holds'): ('proved', 'analytical')}
RANK = {'conjectured': 0, 'unprovable-here': 0, 'undetermined': 0, 'witnessed': 1, 'decided': 2, 'checked-symbolically': 2, 'proved': 3, 'refuted': 9}


def auto_tier(term):
    """The cheapest tier that can speak to a term (a person may still ask for a stronger one by name)."""
    if not isinstance(term, dict):
        return 'numeric'
    k = terms.op_of(term)
    if k == 'symbolic':
        return 'sympy'
    if k in ('subset', 'dims_subset'):
        return 'interval'
    if k == 'bitvector':
        return 'z3'
    if k == 'given':
        return auto_tier(term.get('holds'))
    if k in ('forall', 'exists') and any(str(b.get('in', '')).startswith(z3tier.CONTINUUM) for b in (term[k] or []) if isinstance(b, dict)):
        return 'z3'
    return 'numeric'


def _versions():
    out = {'numeric': 'mathproofs.numeric v0', 'interval': 'mathproofs.numeric v0 (interval)'}
    try:
        import sympy
        out['sympy'] = 'sympy %s' % sympy.__version__
    except Exception:
        out['sympy'] = 'sympy absent'
    out['z3'] = z3tier.version()
    return out


def evaluate(manager, term, tier, budget_s=10.0):
    if tier in ('numeric', 'interval'):
        return numeric.evaluate(manager, term)
    if tier == 'sympy':
        return symbolic.evaluate(term)
    if tier == 'z3':
        return z3tier.evaluate(manager, term, budget_s=budget_s)
    if tier == 'lean':
        return {'verdict': 'unprovable-here', 'tier': 'lean', 'detail': {'why': 'the lean tier arrives in pf-2 (polari-proof-tools, an engines worker)'}, 'counterexample': None}
    return {'verdict': 'error', 'tier': tier, 'detail': {'why': 'unknown tier %r' % tier}, 'counterexample': None}


def check(manager, claim, tier=None, make=None, save=True):
    """Run ONE claim; returns the ProofRun fields + what the claim became. `make(cls, **fields)` builds rows (a selftest
    with a fake manager passes its own); `save` persists through manager.db when present."""
    from mathproofs.mathproofs_basis import ProofRun
    term = terms_of(claim)
    errs = terms.validate(term)
    tier = tier or auto_tier(term)
    t0 = time.time()
    if errs:
        res = {'verdict': 'error', 'tier': tier, 'detail': {'why': 'invalid term: ' + '; '.join(errs)}, 'counterexample': None}
    else:
        res = evaluate(manager, term, tier, budget_s=float(getattr(claim, 'budget_s', 10.0) or 10.0))
    elapsed = round(time.time() - t0, 4)
    refs = _j(getattr(claim, 'about_refs_json', '[]'), [])
    state = rows_state_hash(manager, refs)
    now = datetime.datetime.now(datetime.timezone.utc)
    stamp = now.strftime('%Y-%m-%dT%H:%M:%SZ')
    run_name = '%s@%s@%s' % (getattr(claim, 'name', '?'), res['tier'], now.strftime('%Y%m%dT%H%M%S.%fZ'))   # unique to the microsecond: two runs in one second are two rows
    fields = {'name': run_name, 'description': '', 'claim': str(getattr(claim, 'name', '')), 'checker': res['tier'], 'checker_version': _versions().get(res['tier'], res['tier']),
              'verdict': res['verdict'], 'detail_json': json.dumps(res.get('detail') or {}, default=str), 'output_tail': '', 'elapsed_s': elapsed, 'rows_state_hash': state,
              'ran_at': stamp, 'ran_where': 'in-process', 'notes': ''}
    make = make or (lambda cls, **f: cls(manager=manager, **f))
    run = make(ProofRun, **fields)
    # the claim's status by the vocabulary — a weaker tier never overwrites a stronger verdict; refuted always wins
    before = str(getattr(claim, 'proof_status', 'conjectured'))
    if res['verdict'] == 'holds':
        status, ev = STATUS_FOR[(res['tier'], 'holds')]
        if RANK[status] >= RANK.get(before, 0) or before in ('conjectured', 'unprovable-here'):
            claim.proof_status = status; claim.checker = res['tier']; claim.certificate_ref = run_name; claim.evidence_level = ev; claim.counterexample_json = '{}'
    elif res['verdict'] == 'refuted':
        claim.proof_status = 'refuted'; claim.checker = res['tier']; claim.certificate_ref = run_name
        claim.counterexample_json = json.dumps(res.get('counterexample') or {}, default=str); claim.evidence_level = 'measured' if res['tier'] == 'numeric' else 'analytical'
    elif res['verdict'] == 'undetermined':
        # not defined here (a premise fails / a value is unrecorded): never a refutation, never vacuously true
        claim.proof_status = 'undetermined'; claim.checker = res['tier']; claim.certificate_ref = run_name; claim.counterexample_json = '{}'; claim.evidence_level = 'none'
    elif res['verdict'] == 'undecided':
        pass   # D-pf-9: the budget ran out — the run records it; the claim's status is untouched
    elif res['verdict'] == 'unprovable-here' and before == 'conjectured':
        claim.proof_status = 'unprovable-here'; claim.checker = res['tier']; claim.certificate_ref = run_name
    if not getattr(claim, 'statement_hash', ''):
        claim.statement_hash = terms.statement_hash(term)
    if not getattr(claim, 'statement_latex', ''):
        claim.statement_latex = terms.to_latex(term)
    db = getattr(manager, 'db', None)
    if save and db is not None and hasattr(db, 'saveInstanceInDB'):
        db.saveInstanceInDB(run); db.saveInstanceInDB(claim)
    return {'run': fields, 'claim': str(getattr(claim, 'name', '')), 'before': before, 'after': str(claim.proof_status), 'verdict': res['verdict'], 'tier': res['tier'],
            'detail': res.get('detail'), 'counterexample': res.get('counterexample')}


def stale(manager, claim):
    """True when the claim's certificate run exists and its rows-state hash no longer matches."""
    ref = str(getattr(claim, 'certificate_ref', '') or '')
    run = by_name(manager, 'ProofRun', ref) if ref else None
    if run is None:
        return False
    return str(getattr(run, 'rows_state_hash', '')) != rows_state_hash(manager, _j(getattr(claim, 'about_refs_json', '[]'), []))


def terms_of(claim):
    return _j(getattr(claim, 'statement_json', '{}'), {})


def _j(s, d):
    try:
        v = json.loads(s)
        return v if v is not None else d
    except Exception:
        return d


def status_of(manager, claim):
    """The claim's status as the world sees it now: `<status> (stale)` when the rows moved under its certificate."""
    st = str(getattr(claim, 'proof_status', 'conjectured'))
    return st + ' (stale)' if st not in ('conjectured', 'unprovable-here', 'undetermined') and stale(manager, claim) else st
