"""
@module mathproofs.custom.lean_tier

TIER 3 — FORMAL (Lean 4 + Mathlib, through the `polari-proof-tools` engines worker; plan §I, pf-2). A claim's term is
the SPEC; the `.lean` file is the PROOF; the bridge is the `statement_hash` both carry: the file's header cites the
canonical term and its sha256, the worker reports whether that hash is the one the framework asked about, and this
tier writes `proved` ONLY when (a) `lean` accepted the file under the pinned toolchain and (b) the hash matches — a
proof of a different statement is refused by name, never counted.

What the tier proves today (`THEOREMS`: term template → committed file, D-pf-10):
    symmetry-of-contraction  n = "any"   → PolariProofs/SigmaSymmetry.lean       (every rank; C's first minor symmetry)
    chain-domains-compose    links "any" → PolariProofs/ChainComposition.lean    (pairwise inclusion ⇒ valid on the last
                                                                                  domain = the intersection)
    restriction-idempotent   {}          → PolariProofs/RestrictionIdempotent.lean (the toolchain smoke test)
Anything else → unprovable-here naming the template (a theorem is added to the submodule, never improvised here).
Lean is NEVER run automatically (plan §I.9 / boot.py): a person or the pipeline asks; the claim's `budget_s` is the
check's timeout and a timeout is `undecided` (D-pf-9). The certificate the ProofRun carries: the file, its sha256, the
Lean toolchain and the Mathlib commit it was checked under, and where it ran (the ladder's answer).
"""
from mathproofs.custom import proof_engines, terms

THEOREMS = {
    ('symmetry-of-contraction', 'any'): 'PolariProofs/SigmaSymmetry.lean',
    ('chain-domains-compose', 'any'): 'PolariProofs/ChainComposition.lean',
    ('restriction-idempotent', ''): 'PolariProofs/RestrictionIdempotent.lean',
}


def _res(verdict, detail, ce=None):
    return {'verdict': verdict, 'tier': 'lean', 'detail': detail, 'counterexample': ce}


def theorem_for(term):
    """The committed theorem file a term is proved by, or None."""
    if not (isinstance(term, dict) and terms.op_of(term) == 'symbolic'):
        return None
    spec = term['symbolic']; args = spec.get('args') or {}
    key = (spec.get('template'), str(args.get('n', args.get('links', ''))))
    return THEOREMS.get(key)


def evaluate(manager, term, budget_s=25.0):
    """{'verdict': holds | undecided | unprovable-here | error, 'tier': 'lean', 'detail', 'counterexample': None}.
    A Lean failure is `error` (a proof did not check — it says nothing about the statement's truth), never `refuted`."""
    fpath = theorem_for(term)
    if fpath is None:
        return _res('unprovable-here', {'why': 'no committed theorem for this term (polari-proof-tools/theorems/ — templates proved: %s)' % ', '.join(sorted('%s[%s]' % k for k in THEOREMS))})
    want = terms.statement_hash(term)
    place = proof_engines.resolve()
    if place['how'] == 'refused':
        return _res('unprovable-here', {'why': place['why'], 'file': fpath, 'statement_hash': want, 'placement': place})
    try:
        rep = proof_engines.check(fpath, want, timeout=max(1, int(float(budget_s))))
    except proof_engines.EngineError as exc:
        return _res('error', {'why': str(exc), 'file': fpath, 'statement_hash': want, 'placement': place})
    detail = {'file': fpath, 'file_sha256': rep.get('file_sha256', ''), 'statement_hash': want, 'statement_hash_in_file': rep.get('statement_hash_in_file', ''), 'hash_matches': bool(rep.get('hash_matches')),
              'term_in_file': rep.get('term_in_file', ''), 'pins': rep.get('pins') or {}, 'lean_verdict': rep.get('verdict'), 'returncode': rep.get('returncode'), 'elapsed_s': rep.get('elapsed_s'),
              'budget_s': budget_s, 'how': rep.get('how'), 'where': rep.get('where'), 'stderr_tail': (rep.get('stderr') or '')[-1500:], 'stdout_tail': (rep.get('stdout') or '')[-1500:]}
    if rep.get('verdict') == 'timeout':
        return _res('undecided', dict(detail, why='budget: lean gave no answer within %s s' % budget_s))
    if rep.get('verdict') != 'proved':
        return _res('error', dict(detail, why='lean rejected the file under %s (a proof failed to check; nothing is said about the statement)' % (rep.get('pins') or {}).get('lean', 'the pinned toolchain')))
    if not rep.get('hash_matches'):
        return _res('unprovable-here', dict(detail, why='the certificate %s proves statement %s…, not this claim\'s %s… — a proof of a different statement is not counted' % (fpath, (rep.get('statement_hash_in_file') or '?')[:12], want[:12])))
    return _res('holds', dict(detail, result='lean accepted the certificate and its header cites this statement'))
