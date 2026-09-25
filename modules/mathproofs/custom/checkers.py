"""
@module mathproofs.custom.checkers

RUN a claim through a tier and WRITE what happened (plan §I.3/I.9): a ProofRun row (checker, version, verdict,
detail, the rows-state hash) and the claim's `proof_status` / `checker` / `certificate_ref` / `counterexample_json`
/ `evidence_level` — by the honest vocabulary:

    numeric  holds → witnessed (evidence measured: on THESE rows)      refuted → refuted (counterexample kept)
    interval holds → decided   (evidence analytical: exact set arithmetic)
    sympy    holds → checked-symbolically (analytical: over symbols)
    z3       holds → decided; timeout → undecided (budget), status unchanged (D-pf-9)        [pf-1]
    lean     ok    → proved (analytical)                                                       [pf-2]
    human    a signed note → proved, labelled `human` (D-pf-6)
A refuted claim never deletes anything; a tier that cannot lower the term writes `unprovable-here` naming why.
`auto_tier(term)` picks the cheapest tier that can speak to a term; `check(manager, claim, tier=None)` runs it.
`stale(manager, claim)` says whether the last run's rows-state hash still matches.
"""
import datetime
import json
import time

from mathproofs.custom import numeric, symbolic, terms
from mathproofs.custom.rows import rows_state_hash, by_name, _rows

STATUS_FOR = {('numeric', 'holds'): ('witnessed', 'measured'), ('interval', 'holds'): ('decided', 'analytical'),
              ('sympy', 'holds'): ('checked-symbolically', 'analytical'), ('z3', 'holds'): ('decided', 'analytical'),
              ('lean', 'holds'): ('proved', 'analytical'), ('human', 'holds'): ('proved', 'analytical')}
RANK = {'conjectured': 0, 'unprovable-here': 0, 'witnessed': 1, 'decided': 2, 'checked-symbolically': 2, 'proved': 3, 'refuted': 9}


def auto_tier(term):
    if isinstance(term, dict) and 'symbolic' in term:
        return 'sympy'
    if isinstance(term, dict) and terms.op_of(term) in ('subset', 'dims_subset'):
        return 'interval'
    return 'numeric'


def _versions():
    out = {'numeric': 'mathproofs.numeric v0', 'interval': 'mathproofs.numeric v0 (interval)'}
    try:
        import sympy
        out['sympy'] = 'sympy %s' % sympy.__version__
    except Exception:
        out['sympy'] = 'sympy absent'
    return out


def evaluate(manager, term, tier):
    if tier in ('numeric', 'interval'):
        return numeric.evaluate(manager, term)
    if tier == 'sympy':
        return symbolic.evaluate(term)
    if tier == 'z3':
        return {'verdict': 'unprovable-here', 'tier': 'z3', 'detail': {'why': 'the z3 tier arrives in pf-1'}, 'counterexample': None}
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
        res = evaluate(manager, term, tier)
    elapsed = round(time.time() - t0, 4)
    refs = _j(getattr(claim, 'about_refs_json', '[]'), [])
    state = rows_state_hash(manager, refs)
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    run_name = '%s@%s@%s' % (getattr(claim, 'name', '?'), res['tier'], stamp.replace(':', '').replace('-', ''))
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
    return st + ' (stale)' if st not in ('conjectured', 'unprovable-here') and stale(manager, claim) else st
