"""
@module mathproofs.mathproofs_selftest

pf-0/pf-1 selftest (no server): the four rows; the term language (validate, canonical hash, derived LaTeX); the numeric
witness (holds / refuted with the counterexample / unprovable-here by name); the interval decision; the SymPy
templates over symbols; the Z3 tier (pf-1: a forall over a continuum decided, refuted with the model as the
counterexample, the subset decision re-derived and agreeing with the interval tier, the kernel's fixed-point contract
over exact integers with a prefix-sum counterexample, the budget → undecided with the claim's status untouched); the
checker's status vocabulary (a witness is never a proof; refuted always wins; a weaker tier never overwrites a stronger
verdict); staleness; the inference rules generating obligations on the seeded tensor trees (chains found, dims composed,
a decomposition with no recorded error undetermined, the bound a KNOB on the rule); the boot pass; discovery refusing
on a refuted obligation through the soft seam; the manifest.

    PYTHONPATH=.:modules python3 modules/mathproofs/mathproofs_selftest.py
"""
import json
import os
import sys
import types

HERE = os.path.dirname(os.path.abspath(__file__))
FW = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, FW); sys.path.insert(0, os.path.join(FW, 'modules'))

from mathproofs.mathproofs_basis import MATHPROOFS_CLASSES, MathClaim, ProofRun, InferenceRule, ProofObligation, PROOF_STATUSES, CHECKERS  # noqa: E402
from mathproofs.mathproofs_seed import MATHPROOFS_SEED_PAIRS, SEED_INFERENCE_RULES, SEED_MATH_CLAIMS  # noqa: E402
from mathproofs.custom import terms, numeric, symbolic, checkers, rules, z3tier, boot, lean_tier, proof_engines, authoring  # noqa: E402

_results = []


def check(label, cond, extra=''):
    _results.append((label, bool(cond)))
    print(('PASS' if cond else 'FAIL') + ': ' + label + ('' if cond else '  — %s' % (extra,)))


def _mgr():
    tables = {c.__name__: {} for c in MATHPROOFS_CLASSES}
    for c in ('TensorTreeDefinition', 'TensorNode', 'UnresolvedTensorSpace', 'LocalizedDimension', 'TensorMapping', 'TensorSelection', 'TensorDiscoveryPolicy',
              'TensorMathExpression', 'CharacterizationMapping', 'SimSpaceBindingDefinition'):
        tables[c] = {}
    return types.SimpleNamespace(objectTables=tables, db=None)


def _add(mgr, cls, **kw):
    row = types.SimpleNamespace(**kw); mgr.objectTables[cls][id(row)] = row; return row


_mk = lambda mgr: (lambda cls, **f: _add(mgr, cls.__name__, **f))

# ---- rows + seeds
check('the module registers exactly FOUR row classes', len(MATHPROOFS_CLASSES) == 4 and [c.__name__ for c in MATHPROOFS_CLASSES] == ['MathClaim', 'ProofRun', 'InferenceRule', 'ProofObligation'])
c = MathClaim(name='x', kind='identity', statement_json='{}')
check('MathClaim defaults: conjectured, no checker, evidence none, budget 25 s (D-pf-9, a knob; his 2026-09-25 number: the slowest honest instance took 19 s)', c.proof_status == 'conjectured' and c.checker == '' and c.evidence_level == 'none' and c.budget_s == 25.0)
check('the seed pairs cover every class; eight inference rules; fifteen standalone claims (5 pf-0 + 7 pf-1 + 3 theorems pf-2)', {p[0] for p in MATHPROOFS_SEED_PAIRS} == {c_.__name__ for c_ in MATHPROOFS_CLASSES} and len(SEED_INFERENCE_RULES) == 8 and len(SEED_MATH_CLAIMS) == 15)
check('every seeded rule names a pattern, a claim kind and a default checker; two are honestly template-less (units, evidence rank: not decidable here)',
      all(r['pattern'] and r['obligation_kind'] and r['checker_default'] in CHECKERS for r in SEED_INFERENCE_RULES) and sum(1 for r in SEED_INFERENCE_RULES if r['template_json'] == '{}') == 2)

# ---- the term language
t_eq = {'eq': [{'ref': 'CharacterizationMapping:a', 'path': ['result']}, 3.0], 'tol': {'abs': 0.01}}
check('validate: a well-formed term is [] ; a bad ref / unknown operator / a forall without holds are named',
      terms.validate(t_eq) == [] and terms.validate({'ref': 'x'}) and terms.validate({'frobnicate': 1}) and terms.validate({'forall': [{'var': 'x', 'in': 'rows:A'}]}))
check('canonical + statement_hash are stable under key order', terms.statement_hash({'eq': [1, 2], 'tol': {'abs': 0.1}}) == terms.statement_hash({'tol': {'abs': 0.1}, 'eq': [1, 2]}))
check('  …pf-1 operators validate: exists over a continuum, in, bitvector (args complete; the bounds are terms); a bitvector missing a bound is named',
      terms.validate({'exists': [{'var': 'x', 'in': 'validity:a'}], 'holds': {'in': ['x', 'domain:n']}}) == [] and terms.validate({'bitvector': {'template': 'mac-no-overflow', 'args': {'products': 4, 'operand_bits': 32, 'acc_bits': 64, 'a_abs_max': 1, 'b_abs_max': {'ref': 'X:y', 'path': ['v']}}}}) == []
      and terms.validate({'bitvector': {'template': 'mac-no-overflow', 'args': {'products': 4}}}) and terms.validate({'in': ['x', 'rows:A']}))
check('  …and their LaTeX is derived too (∃, ∈, the accumulator bound)', '\\exists' in terms.to_latex({'exists': [{'var': 'x', 'in': 'validity:a'}], 'holds': {'in': ['x', 'domain:n']}}) and '2^{63}' in terms.to_latex({'bitvector': {'template': 'mac-no-overflow', 'args': {'products': 4, 'operand_bits': 32, 'acc_bits': 64, 'a_abs_max': 1, 'b_abs_max': 2}}}))
check('LaTeX is DERIVED from the term (∀, ⊆, ≤, the symbolic templates)', '\\forall' in terms.to_latex({'forall': [{'var': 'c', 'in': 'rows:X'}], 'holds': {'le': [1, 2]}}) and '\\subseteq' in terms.to_latex({'subset': ['validity:a', 'validity:b']})
      and '\\sigma_{ij}' in terms.to_latex({'symbolic': {'template': 'symmetry-of-contraction', 'args': {}}}))

# ---- numeric witness + interval decision on a fake manager
m = _mgr()
_add(m, 'CharacterizationMapping', name='a', result=3.0, method='sch', conditions_json=json.dumps({'delta_pct': -5.0, 'schematic_ps': 10.0}))
_add(m, 'CharacterizationMapping', name='b', result=0.02, method='ext', conditions_json=json.dumps({'delta_pct': 4.0, 'schematic_ps': 10.0}))
_add(m, 'CharacterizationMapping', name='c', result=2.99, method='sch', conditions_json=json.dumps({'delta_pct': -1.0}))
r = numeric.evaluate(m, t_eq)
check('numeric: eq with abs tolerance holds and reports lhs/rhs', r['verdict'] == 'holds' and r['tier'] == 'numeric' and r['detail']['lhs'] == 3.0)
r = numeric.evaluate(m, {'eq': [{'ref': 'CharacterizationMapping:a', 'path': ['result']}, {'ref': 'CharacterizationMapping:c', 'path': ['result']}]})
check('  …and REFUTES a near-miss without tolerance, keeping the counterexample', r['verdict'] == 'refuted' and r['counterexample'] == {'lhs': 3.0, 'rhs': 2.99})
r = numeric.evaluate(m, {'forall': [{'var': 'x', 'in': 'rows:CharacterizationMapping:method=sch'}], 'holds': {'lt': [{'ref': 'x', 'path': ['conditions_json', 'delta_pct']}, 0]}})
check('  …a finite forall over filtered rows walks the rows through a json path', r['verdict'] == 'holds' and r['detail']['rows'] == 2)
r = numeric.evaluate(m, {'forall': [{'var': 'x', 'in': 'rows:CharacterizationMapping'}], 'holds': {'lt': [{'ref': 'x', 'path': ['conditions_json', 'delta_pct']}, 0]}})
check('  …and the first failing row IS the counterexample', r['verdict'] == 'refuted' and r['counterexample']['row'] == 'b')
r = numeric.evaluate(m, {'gt': [{'mul': [{'ref': 'CharacterizationMapping:b', 'path': ['result']}, 1000]}, {'ref': 'CharacterizationMapping:b', 'path': ['conditions_json', 'schematic_ps']}]})
check('  …arithmetic (mul) inside a comparison: 0.02 ns × 1000 = 20 ps > 10 ps', r['verdict'] == 'holds')
r = numeric.evaluate(m, {'forall': [{'var': 'x', 'in': 'validity:nope'}], 'holds': {'lt': [1, 2]}})
check('  …a forall over a continuum is UNPROVABLE-HERE by name (the z3 tier), never a fake pass', r['verdict'] in ('unprovable-here', 'error') and 'z3' in r['detail']['why'] or 'no TensorMapping' in r['detail']['why'])
_add(m, 'TensorMapping', name='m1', kind='operator', source_node='u', target_node='e', source_dims_json='["node","i"]', target_dims_json='["n","k","l"]', validity_json=json.dumps({'strain': [0, 0.002]}), expression_ref='', reconstruction_error=0.0)
_add(m, 'TensorMapping', name='m2', kind='operator', source_node='e', target_node='s', source_dims_json='["n","k","l"]', target_dims_json='["n","i","j"]', validity_json=json.dumps({'strain': [0, 0.001], 'temp': [0, 300]}), expression_ref='sig', reconstruction_error=0.0)
_add(m, 'TensorMapping', name='m3', kind='operator', source_node='s', target_node='s', source_dims_json='["n","i","j","extra"]', target_dims_json='["node","i"]', validity_json=json.dumps({'strain': [0, 0.005]}), expression_ref='', reconstruction_error=0.0)
r = numeric.evaluate(m, {'subset': ['validity:m2', 'validity:m1']})
check('interval: validity(m2) ⊆ validity(m1) on the shared dim (strain [0,0.001] ⊆ [0,0.002]); temp is unconstrained in m1, not a violation', r['verdict'] == 'holds' and r['tier'] == 'interval' and r['detail']['unconstrained_in_outer'] == ['temp'])
r = numeric.evaluate(m, {'subset': ['validity:m3', 'validity:m2']})
check('  …and REFUTES [0,0.005] ⊆ [0,0.001] naming the dim', r['verdict'] == 'refuted' and 'strain' in r['counterexample'])
r = numeric.evaluate(m, {'dims_subset': ['m2.source_dims', 'm1.target_dims']})
check('  …dims compose: m2 consumes what m1 produced', r['verdict'] == 'holds')
r = numeric.evaluate(m, {'dims_subset': ['m3.source_dims', 'm2.target_dims']})
check('  …and a dim nobody produced is the counterexample', r['verdict'] == 'refuted' and r['counterexample'] == {'missing': ['extra']})

r = numeric.evaluate(m, {'exists': [{'var': 'x', 'in': 'rows:CharacterizationMapping'}], 'holds': {'gt': [{'ref': 'x', 'path': ['conditions_json', 'delta_pct']}, 0]}})
check('  …a finite exists holds on the first satisfying row (the witness named) and is refuted when no row does', r['verdict'] == 'holds' and r['detail']['witness'] == 'b'
      and numeric.evaluate(m, {'exists': [{'var': 'x', 'in': 'rows:CharacterizationMapping'}], 'holds': {'gt': [{'ref': 'x', 'path': ['result']}, 100]}})['verdict'] == 'refuted')

# ---- z3 (pf-1): the continuum and the machine integers, decided — or refuted by a model — within a budget
r = z3tier.evaluate(m, {'forall': [{'var': 'x', 'in': 'validity:m1'}], 'holds': {'le': [{'mul': [{'ref': 'x', 'path': ['strain']}, 1000000000]}, 2147483647]}})
check('z3: ∀ strain ∈ [0, 0.002]: strain·1e9 ≤ 2³¹−1 — DECIDED (no model of the negation); the box and what was asked are in the detail',
      r['verdict'] == 'holds' and r['tier'] == 'z3' and r['detail']['over']['x']['box'] == {'strain': [0, 0.002]} and 'negation' in r['detail']['asked'], r)
r = z3tier.evaluate(m, {'forall': [{'var': 'x', 'in': 'validity:m1'}], 'holds': {'le': [{'mul': [{'ref': 'x', 'path': ['strain']}, 1000000000]}, 1000000]}})
check('  …and REFUTED when the bound is too small — the counterexample is a REAL POINT of the domain (strain > 0.001)', r['verdict'] == 'refuted' and r['counterexample']['x.strain'] > 0.001, r)
z_ok = z3tier.evaluate(m, {'subset': ['validity:m2', 'validity:m1']}); z_bad = z3tier.evaluate(m, {'subset': ['validity:m3', 'validity:m2']})
check('  …the subset decision re-derived as ∀x∈A: x∈B agrees with the interval tier on both pairs (m2⊆m1 holds; m3⊄m2 refuted with a strain in (0.001, 0.005])',
      z_ok['verdict'] == 'holds' and z_bad['verdict'] == 'refuted' and 0.001 < z_bad['counterexample']['x.strain'] <= 0.005, (z_ok['verdict'], z_bad))
r = z3tier.evaluate(m, {'exists': [{'var': 'x', 'in': 'validity:m1'}], 'holds': {'gt': [{'ref': 'x', 'path': ['strain']}, 0.0015]}})
check('  …exists over the continuum holds with a witness point', r['verdict'] == 'holds' and r['detail']['witness']['x.strain'] > 0.0015)
t_mac = {'bitvector': {'template': 'mac-no-overflow', 'args': {'products': 4, 'operand_bits': 32, 'acc_bits': 64, 'a_abs_max': 2147483647, 'b_abs_max': {'mul': [{'ref': 'TensorMapping:m1', 'path': ['validity_json', 'strain', 1]}, 1000000000]}}}}
r = z3tier.evaluate(m, t_mac)
check('  …the kernel\'s fixed-point contract: four int32×int32 products (ε bound READ from the mapping\'s validity: 0.002·1e9 = 2·10⁶ nε) summed in int64 never overflow — DECIDED over exact integers, ~9 bits of headroom stated',
      r['verdict'] == 'holds' and r['detail']['b_abs_max'] == 2000000 and r['detail']['analytic_bound']['headroom_bits'] > 9 and 'QF_NIA' in r['detail']['encoding'], r)
r = z3tier.evaluate(m, {'bitvector': {'template': 'mac-no-overflow', 'args': {'products': 4, 'operand_bits': 32, 'acc_bits': 64, 'a_abs_max': 2147483647, 'b_abs_max': 2147483647}}})
check('  …with full-range operands it is REFUTED: the model gives the operands and the prefix sums, and names the first step that overflows',
      r['verdict'] == 'refuted' and len(r['counterexample']['a']) == 4 and r['counterexample']['first_overflow_at'] is not None and abs(r['counterexample']['prefix_sums'][r['counterexample']['first_overflow_at']]) > 2 ** 63 - 1, r['counterexample'])
import z3 as _z3
r = z3tier.evaluate(m, t_mac, budget_s=0.001, _check=lambda s_: _z3.unknown)
check('  …no decision within the budget → UNDECIDED naming the budget (D-pf-9), never a refutation', r['verdict'] == 'undecided' and 'budget' in r['detail']['why'] and r['counterexample'] is None)
check('  …what z3 does not lower is refused by name: a closed statement over row values (the numeric tier\'s witness), a relative tolerance over a continuum, a symbolic template',
      'witness' in z3tier.evaluate(m, {'le': [1, 2]})['detail']['why'] and z3tier.evaluate(m, {'forall': [{'var': 'x', 'in': 'validity:m1'}], 'holds': {'eq': [{'ref': 'x', 'path': ['strain']}, 1], 'tol': {'rel': 0.1}}})['verdict'] == 'unprovable-here'
      and z3tier.evaluate(m, {'symbolic': {'template': 'restriction-idempotent', 'args': {}}})['verdict'] == 'unprovable-here')
check('  …a `given` whose premise fails is UNDETERMINED here too', z3tier.evaluate(m, {'given': {'recorded': {'ref': 'TensorMapping:m1', 'path': ['expression_ref']}}, 'holds': {'forall': [{'var': 'x', 'in': 'validity:m1'}], 'holds': {'le': [1, 2]}}})['verdict'] == 'undetermined')
check('auto_tier: a forall over a continuum and a bitvector go to z3; over rows to numeric; subset stays interval (cheapest first)',
      checkers.auto_tier({'forall': [{'var': 'x', 'in': 'validity:m1'}], 'holds': {'le': [1, 2]}}) == 'z3' and checkers.auto_tier(t_mac) == 'z3' and checkers.auto_tier({'forall': [{'var': 'x', 'in': 'rows:A'}], 'holds': {'le': [1, 2]}}) == 'numeric' and checkers.auto_tier({'subset': ['validity:a', 'validity:b']}) == 'interval')

# ---- symbolic
r = symbolic.evaluate({'symbolic': {'template': 'symmetry-of-contraction', 'args': {'n': 2}}})
check('sympy: σ = C:ε symmetric over 12 free symbols in 2-D (residual simplifies to 0)', r['verdict'] == 'holds' and r['detail']['free_symbols'] == 12 and r['detail']['residuals'] == {'01': '0'})
check('  …and in 3-D (42 symbols)', symbolic.evaluate({'symbolic': {'template': 'symmetry-of-contraction', 'args': {'n': 3}}})['detail']['free_symbols'] == 42)
check('  …linear composition and restriction idempotence hold over symbols', symbolic.evaluate({'symbolic': {'template': 'linear-composition', 'args': {}}})['verdict'] == 'holds' and symbolic.evaluate({'symbolic': {'template': 'restriction-idempotent', 'args': {}}})['verdict'] == 'holds')
check('  …a free expression is refused by name (templates only in v0)', symbolic.evaluate({'eq': [1, 1]})['verdict'] == 'unprovable-here')

# ---- the checker: runs, vocabulary, staleness
cl = _add(m, 'MathClaim', name='k1', kind='identity', about_refs_json=json.dumps(['CharacterizationMapping:a']), statement_json=json.dumps(t_eq), proof_status='conjectured', checker='', certificate_ref='',
          counterexample_json='{}', evidence_level='none', statement_hash='', statement_latex='', budget_s=25.0)
res = checkers.check(m, cl, make=_mk(m), save=False)
check('check: a numeric holds → WITNESSED with evidence MEASURED (on these rows), a ProofRun with the rows-state hash, the derived LaTeX + hash filled',
      res['after'] == 'witnessed' and cl.evidence_level == 'measured' and cl.checker == 'numeric' and len(m.objectTables['ProofRun']) == 1 and cl.statement_hash and cl.statement_latex and res['run']['rows_state_hash'], res)
check('  …the claim is not stale while its rows stand', not checkers.stale(m, cl) and checkers.status_of(m, cl) == 'witnessed')
m.objectTables['CharacterizationMapping'][[k for k, v in m.objectTables['CharacterizationMapping'].items() if v.name == 'a'][0]].result = 3.5
check('  …and becomes STALE the moment the row it speaks of changes (never silently still witnessed)', checkers.stale(m, cl) and checkers.status_of(m, cl) == 'witnessed (stale)')
res = checkers.check(m, cl, make=_mk(m), save=False)
check('  …re-checking refutes it now, and refuted keeps the counterexample', res['after'] == 'refuted' and json.loads(cl.counterexample_json)['lhs'] == 3.5)
cs = _add(m, 'MathClaim', name='k2', kind='symmetry', about_refs_json='[]', statement_json=json.dumps({'symbolic': {'template': 'symmetry-of-contraction', 'args': {'n': 2}}}), proof_status='conjectured', checker='', certificate_ref='',
          counterexample_json='{}', evidence_level='none', statement_hash='', statement_latex='', budget_s=25.0)
res = checkers.check(m, cs, make=_mk(m), save=False)
check('  …a symbolic holds → CHECKED-SYMBOLICALLY, evidence ANALYTICAL; auto_tier picked sympy', res['after'] == 'checked-symbolically' and cs.evidence_level == 'analytical' and res['tier'] == 'sympy')
res = checkers.check(m, cs, tier='numeric', make=_mk(m), save=False)
check('  …the numeric tier cannot lower a symbolic term → unprovable-here, and the STRONGER verdict stands (a weaker tier never overwrites)', res['verdict'] == 'unprovable-here' and cs.proof_status == 'checked-symbolically')
res = checkers.check(m, cs, tier='lean', make=_mk(m), save=False)
check('  …the lean tier on a FIXED-size symbolic term (n = 2) has no committed theorem for it → unprovable-here naming the templates proved; status unchanged', res['verdict'] == 'unprovable-here' and 'no committed theorem' in res['detail']['why'] and cs.proof_status == 'checked-symbolically')

# ---- lean (pf-2): the ladder, the statement_hash bridge, the honest verdicts — with the worker faked, then real when present
_t_gen = {'symbolic': {'template': 'symmetry-of-contraction', 'args': {'n': 'any'}}}
_t_chain = {'symbolic': {'template': 'chain-domains-compose', 'args': {'links': 'any'}}}
check('lean: the general statements (n = any; the chain lemma) auto-tier to LEAN and map to committed theorem files; sympy names them as the lean tier\'s and steps aside',
      checkers.auto_tier(_t_gen) == 'lean' and checkers.auto_tier(_t_chain) == 'lean' and lean_tier.theorem_for(_t_gen) == 'PolariProofs/SigmaSymmetry.lean' and lean_tier.theorem_for(_t_chain) == 'PolariProofs/ChainComposition.lean'
      and 'lean tier' in symbolic.evaluate(_t_gen)['detail']['why'] and checkers.auto_tier({'symbolic': {'template': 'restriction-idempotent', 'args': {}}}) == 'sympy')
check('  …validate accepts the chain-domains-compose template; its LaTeX is derived (∀ n marked)', terms.validate(_t_chain) == [] and '(\\forall n)' in terms.to_latex(_t_gen) and 'bigcap' in terms.to_latex(_t_chain))
_saved = (dict(os.environ), proof_engines.PROJECT, proof_engines.IMAGE, proof_engines.check)
os.environ.pop('PROOF_ENGINES_URL', None); proof_engines.PROJECT = ''; proof_engines.IMAGE = 'no-such-image:none'; proof_engines._IMAGE_CACHE.clear()
_place = proof_engines.resolve()
check('  …the engines LADDER with nothing present REFUSES naming BOTH knobs (PROOF_ENGINES_URL, pol allocate mathproofs.engines) — never a device assumption', _place['how'] == 'refused' and 'PROOF_ENGINES_URL' in _place['why'] and 'pol allocate mathproofs.engines' in _place['why'], _place)
check('  …and the lean tier then answers unprovable-here with the placement, status untouched', lean_tier.evaluate(m, _t_gen)['verdict'] == 'unprovable-here')
_h = terms.statement_hash(_t_gen)
def _fake(reply):
    def _check(file, statement_hash, timeout=600):
        r = dict(reply); r['hash_matches'] = (r.get('statement_hash_in_file') == statement_hash); r['file'] = file; return r
    return _check
proof_engines.resolve = lambda: {'how': 'remote', 'where': 'http://fake:9810', 'why': 'test'}
proof_engines.check = _fake({'ok': True, 'verdict': 'proved', 'returncode': 0, 'statement_hash_in_file': _h, 'file_sha256': 'abc', 'pins': {'lean': 'leanprover/lean4:v4.34.1', 'mathlib': 'd13f23b723b8'}, 'elapsed_s': 3.2, 'how': 'remote', 'where': 'http://fake:9810'})
cl3 = _add(m, 'MathClaim', name='thm', kind='symmetry', about_refs_json='[]', statement_json=json.dumps(_t_gen), proof_status='conjectured', checker='', certificate_ref='', counterexample_json='{}', evidence_level='none', statement_hash='', statement_latex='', budget_s=300.0)
res = checkers.check(m, cl3, make=_mk(m), save=False)
check('  …a worker that accepts the file AND whose header cites THIS statement\'s hash → PROVED, evidence analytical; the run cites the Lean toolchain + Mathlib commit + where it ran',
      res['after'] == 'proved' and cl3.checker == 'lean' and cl3.evidence_level == 'analytical' and 'v4.34.1' in res['run']['checker_version'] and 'd13f23b723b8' in res['run']['checker_version'] and res['detail']['hash_matches'], res['run'])
proof_engines.check = _fake({'ok': True, 'verdict': 'proved', 'returncode': 0, 'statement_hash_in_file': 'deadbeef', 'file_sha256': 'abc', 'pins': {'lean': 'x', 'mathlib': 'y'}, 'elapsed_s': 1})
cl4 = _add(m, 'MathClaim', name='thm-other', kind='symmetry', about_refs_json='[]', statement_json=json.dumps(_t_gen), proof_status='conjectured', checker='', certificate_ref='', counterexample_json='{}', evidence_level='none', statement_hash='', statement_latex='', budget_s=300.0)
res = checkers.check(m, cl4, make=_mk(m), save=False)
check('  …a proof of a DIFFERENT statement (header hash ≠ the claim\'s) is NOT counted: unprovable-here by name (the status a never-proved claim then carries), no certificate', res['verdict'] == 'unprovable-here' and 'different statement' in res['detail']['why'] and cl4.proof_status == 'unprovable-here' and cl4.checker == 'lean')
proof_engines.check = _fake({'ok': True, 'verdict': 'error', 'returncode': 1, 'statement_hash_in_file': _h, 'stderr': 'error: unsolved goals', 'pins': {'lean': 'x', 'mathlib': 'y'}, 'elapsed_s': 1})
res = checkers.check(m, cl4, make=_mk(m), save=False)
check('  …lean REJECTING the file is an ERROR run (a proof failed to check — nothing is said of the statement), never refuted; status untouched', res['verdict'] == 'error' and cl4.proof_status == 'unprovable-here' and json.loads(cl4.counterexample_json) == {})
proof_engines.check = _fake({'ok': True, 'verdict': 'timeout', 'returncode': 124, 'statement_hash_in_file': _h, 'pins': {}, 'elapsed_s': 300})
res = checkers.check(m, cl4, make=_mk(m), save=False)
check('  …a timeout is UNDECIDED within the claim\'s budget (300 s for the theorems: Mathlib\'s imports load first), status untouched', res['verdict'] == 'undecided' and cl4.proof_status == 'unprovable-here')
_add(m, 'MathClaim', name='thm-waiting', kind='symmetry', about_refs_json='[]', statement_json=json.dumps(_t_chain), proof_status='conjectured', checker='', certificate_ref='', counterexample_json='{}', evidence_level='none', statement_hash='', statement_latex='', budget_s=300.0)
os.environ.clear(); os.environ.update(_saved[0]); proof_engines.PROJECT, proof_engines.IMAGE, proof_engines.check = _saved[1], _saved[2], _saved[3]; proof_engines.resolve = proof_engines.__dict__.get('_orig_resolve', proof_engines.resolve)
import importlib; importlib.reload(proof_engines); proof_engines._IMAGE_CACHE.clear()
_place = proof_engines.resolve()
if _place['how'] != 'refused':
    _r = lean_tier.evaluate(m, {'symbolic': {'template': 'restriction-idempotent', 'args': {}}}, budget_s=600)
    check('  …REAL check (lean via %s %s): the smoke theorem RestrictionIdempotent.lean is accepted under the pinned toolchain and cites its statement — %s s' % (_place['how'], _place['where'], _r['detail'].get('elapsed_s')),
          _r['verdict'] == 'holds' and _r['detail']['hash_matches'] and _r['detail']['pins'].get('lean', '').endswith('v4.34.1'), _r['detail'].get('why') or _r['detail'].get('stderr_tail'))
else:
    check('  …no lean engine on this device (stated: %s) — the real check runs where the worker is (the live-boot probe / the pipeline)' % _place['why'][:80], True)
cz = _add(m, 'MathClaim', name='k3', kind='bound', about_refs_json=json.dumps(['TensorMapping:m1']), statement_json=json.dumps(t_mac), proof_status='conjectured', checker='', certificate_ref='',
          counterexample_json='{}', evidence_level='none', statement_hash='', statement_latex='', budget_s=25.0)
res = checkers.check(m, cz, make=_mk(m), save=False)
check('  …a z3 holds through check() → DECIDED, evidence ANALYTICAL, the run cites the z3 version and the claim\'s budget', res['after'] == 'decided' and cz.evidence_level == 'analytical' and res['run']['checker_version'].startswith('z3 ') and res['detail']['budget_s'] == 25.0, res['run'])
cz2 = _add(m, 'MathClaim', name='k4', kind='bound', about_refs_json='[]', statement_json=json.dumps(t_mac), proof_status='conjectured', checker='', certificate_ref='', counterexample_json='{}', evidence_level='none', statement_hash='', statement_latex='', budget_s=0.0001)
_orig = z3tier.evaluate; z3tier.evaluate = lambda mgr, t, budget_s=25.0, _check=None: _orig(mgr, t, budget_s, _check=lambda s_: __import__('z3').unknown)
res = checkers.check(m, cz2, make=_mk(m), save=False); z3tier.evaluate = _orig
check('  …a run that exhausts its budget is recorded as UNDECIDED and the claim stays CONJECTURED (D-pf-9: the budget self-disarms, nothing is asserted)', res['verdict'] == 'undecided' and cz2.proof_status == 'conjectured' and res['run']['verdict'] == 'undecided' and cz2.certificate_ref == '')

# ---- rules over a tree: obligations generated, cheap tiers run, honest gaps kept
_add(m, 'TensorTreeDefinition', name='T', root_node='u')
for n in ('u', 'e', 's'):
    _add(m, 'TensorNode', name=n, tree='T', dims_json='[]')
_add(m, 'TensorMathExpression', name='sig', operation='contract')
_add(m, 'TensorMapping', name='dec', kind='decomposition', source_node='s', target_node='s', source_dims_json='["n"]', target_dims_json='["mode"]', validity_json='{}', expression_ref='', reconstruction_error=0.0)
_add(m, 'TensorMapping', name='res', kind='restriction', source_node='u', target_node='u', source_dims_json='["node","i"]', target_dims_json='["node","i"]', validity_json='{}', expression_ref='', reconstruction_error=0.0)
for rr in SEED_INFERENCE_RULES:
    _add(m, 'InferenceRule', **rr)
g = rules.generate(m, 'T', make=_mk(m), save=False)
names = {o['obligation']: o for o in g['obligations']}
check('rules.generate on a 3-node chain u→e→s: obligations for every rule that matches — chains (m1→m2, m2→m3, m3→m3, …), the contract operator, the restriction, the decomposition',
      g['ok'] and any('chain-domain-inclusion' in k and 'm1-m2' in k for k in names) and any('operator-symmetry' in k and ':m2' in k for k in names) and any('restriction-idempotent' in k for k in names) and any('decomposition-reconstructs' in k for k in names), sorted(names)[:8])
check('  …domain inclusion DECIDED on m1→m2 and REFUTED on m2→m3 (strain [0,0.005] ⊄ [0,0.001]) with the dim named',
      names['ob:T:chain-domain-inclusion:m1-m2']['status'] == 'decided' and names['ob:T:chain-domain-inclusion:m2-m3']['status'] == 'refuted' and 'strain' in names['ob:T:chain-domain-inclusion:m2-m3']['counterexample'], {k: v['status'] for k, v in names.items() if 'domain' in k})
check('  …dims compose on m1→m2; the dim nobody produced refutes m2→m3', names['ob:T:dims-compose:m1-m2']['status'] == 'decided' and names['ob:T:dims-compose:m2-m3']['status'] == 'refuted')
check('  …σ symmetry on the contract operator: CHECKED-SYMBOLICALLY; the operator chain m1→m2 is linear: checked-symbolically; restriction idempotent: checked-symbolically',
      names['ob:T:operator-symmetry:m2']['status'] == 'checked-symbolically' and names['ob:T:operator-linear:m1-m2']['status'] == 'checked-symbolically' and names['ob:T:restriction-idempotent:res']['status'] == 'checked-symbolically')
check('  …a decomposition with NO recorded reconstruction error is UNDETERMINED — not defined yet, neither falsified nor vacuously true (the model is silent there)', names['ob:T:decomposition-reconstructs:dec']['status'] == 'undetermined')
check('  …the template-less rules stand as UNPROVABLE-HERE obligations (units-compose) — a visible gap, not silence', names['ob:T:units-compose:m1-m2']['status'] == 'unprovable-here')
check('  …re-generation is idempotent by name (no duplicate claims / obligations)', len(rules.generate(m, 'T', make=_mk(m), save=False)['obligations']) == len(g['obligations']) and len(m.objectTables['ProofObligation']) == len(g['obligations']))
lm = rules.logic_of_mapping(m, 'm3')
check('logic_of_mapping(m3): the refuted obligations are listed (what discovery will refuse on), the ok ones too', len(lm['refuted']) >= 1 and all('m3' in o['name'] for o in lm['refuted']))

# ---- the soft seam: discovery refuses on a refuted obligation (with the counterexample), shows open ones
from tensortree.custom.tensortree_logic import of_mapping, available
check('the tensortree seam sees mathproofs and gives m3 the badge refuted, m1 ok/open', available() and of_mapping(m, 'm3')['badge'] == 'refuted' and of_mapping(m, 'm1')['badge'] in ('ok', 'open'))
from tensortree.custom.tensortree_discover import discover
_add(m, 'TensorDiscoveryPolicy', name='default', is_default=True, w_evidence=0.3, w_dims=0.25, w_validity=0.25, w_context=0.1, w_uncertainty=0.1, evidence_map_json=json.dumps({'none': 0.0, 'analytical': 0.4, 'simulated': 0.7, 'measured': 1.0}))
for mm in m.objectTables['TensorMapping'].values():
    for k, v in (('mapping_status', 'implemented'), ('evidence_level', 'none'), ('uncertainty_json', '{}'), ('evidence_ref', ''), ('loss_note', '')):
        if not hasattr(mm, k):
            setattr(mm, k, v)
sel = _add(m, 'TensorSelection', name='sel-s', node='s', ranges_json=json.dumps({'n': [0, 10], 'i': [0, 2], 'j': [0, 2], 'extra': [0, 1], 'strain': [0, 0.0005]}))
d = discover(m, sel)
check('discovery from node s REFUSES m3 (its obligation is refuted: domains, dims) naming the obligation and the counterexample; other candidates carry a logic badge',
      any(r_['mapping'] == 'm3' and 'falsified' in r_['why'] for r_ in d['refuted']) and all('logic' in c_ for c_ in d['candidates']), (d['refuted'], [c_['mapping'] for c_ in d['candidates']]))
_add(m, 'TensorMapping', name='dec2', kind='decomposition', source_node='s', target_node='s', source_dims_json='["n"]', target_dims_json='["mode"]', validity_json='{}', expression_ref='', reconstruction_error=0.03, error_method='frobenius-relative', mapping_status='implemented', evidence_level='none', uncertainty_json='{}', evidence_ref='', loss_note='')
g2 = rules.generate(m, 'T', make=_mk(m), save=False); n2 = {o['obligation']: o for o in g2['obligations']}
check('  …and a decomposition WITH a recorded error (method named, 0.03 ≤ 0.05) is WITNESSED; the vocabulary tells the two apart', n2['ob:T:decomposition-reconstructs:dec2']['status'] == 'witnessed' and n2['ob:T:decomposition-reconstructs:dec']['status'] == 'undetermined')
r = numeric.evaluate(m, {'given': {'recorded': {'ref': 'TensorMapping:dec', 'path': ['error_method']}}, 'holds': {'le': [1, 2]}})
check('  …`given` with an unrecorded premise → verdict undetermined, no counterexample', r['verdict'] == 'undetermined' and r['counterexample'] is None)
_rule = next(r_ for r_ in m.objectTables['InferenceRule'].values() if r_.name == 'decomposition-reconstructs')
_c2 = next(c_ for c_ in m.objectTables['MathClaim'].values() if c_.name == 'ob:T:decomposition-reconstructs:dec2')
check('  …the bound is the rule\'s KNOB (params_json.bound = 0.05), read by ref: the rule row is in the claim\'s about_refs and the claim is not stale', json.loads(_rule.params_json)['bound'] == 0.05 and 'InferenceRule:decomposition-reconstructs' in json.loads(_c2.about_refs_json) and not checkers.stale(m, _c2))
_rule.params_json = json.dumps({'bound': 0.01})
check('  …turning the knob (0.01) makes the witnessed claim STALE; re-generation re-checks and REFUTES it (0.03 > 0.01) — a policy change is never a silent re-verdict', checkers.stale(m, _c2)
      and {o['obligation']: o for o in rules.generate(m, 'T', make=_mk(m), save=False)['obligations']}['ob:T:decomposition-reconstructs:dec2']['status'] == 'refuted')
_rule.params_json = json.dumps({'bound': 0.05})
# ---- boot (pf-1): obligations + never-run claims, once, bounded
_add(m, 'MathClaim', name='seed-like', kind='bound', about_refs_json='[]', statement_json=json.dumps(t_mac), proof_status='conjectured', checker='', certificate_ref='', counterexample_json='{}', evidence_level='none', statement_hash='', statement_latex='', budget_s=25.0)
_add(m, 'MathClaim', name='already-decided', kind='bound', about_refs_json='[]', statement_json=json.dumps(t_mac), proof_status='decided', checker='z3', certificate_ref='x', counterexample_json='{}', evidence_level='analytical', statement_hash='', statement_latex='', budget_s=25.0)
_n_runs = len(m.objectTables['ProofRun'])
_b = boot.run_at_boot(m, make=_mk(m), save=False)
check('boot: every tree\'s obligations regenerated, the never-run claim checked once (z3 within its budget), the already-decided one left alone; the pass reports its cost',
      'T' in _b['trees'] and any(c_[0] == 'seed-like' and c_[1] == 'holds' for c_ in _b['claims_checked']) and not any(c_[0] == 'already-decided' for c_ in _b['claims_checked']) and _b['elapsed_s'] >= 0, _b)
check('  …and a claim whose only tier is LEAN is never run at boot (plan §I.9) — listed as awaiting a person / the pipeline', 'thm-waiting' in _b.get('awaiting_person', []) and not any(c_[0] == 'thm-waiting' for c_ in _b['claims_checked']), _b.get('awaiting_person'))
d2 = discover(m, sel)
check('  …discovery: an inapplicable mapping (outside the state space) and a refuted one are DIFFERENT lists with different words; the old `refused` key is their union', 'inapplicable' in d2 and 'refuted' in d2 and len(d2['refused']) == len(d2['inapplicable']) + len(d2['refuted']))

# ---- pf-3: the doors a person writes through
pv = authoring.preview(m, {'forall': [{'var': 'x', 'in': 'validity:m1'}], 'holds': {'le': [{'ref': 'x', 'path': ['strain']}, 0.002]}})
check('authoring.preview: a term validated, its LaTeX DERIVED (never authored), the tier that would speak (z3), its hash', pv['valid'] and '\\forall' in pv['latex'] and pv['tier'] == 'z3' and len(pv['statement_hash']) == 64)
pv2 = authoring.preview(m, {'frobnicate': 1})
check('  …and a malformed term is refused with the path named', not pv2['valid'] and pv2['errors'] and pv2['latex'] == '')
a1 = authoring.author(m, {'name': 'my-claim', 'kind': 'bound', 'about': ['TensorMapping:m1'], 'statement': {'forall': [{'var': 'x', 'in': 'validity:m1'}], 'holds': {'le': [{'mul': [{'ref': 'x', 'path': ['strain']}, 1000000000]}, 2147483647]}}, 'description': 'mine', 'from': 'the selftest'}, make=_mk(m), save=False)
check('authoring.author: a claim written by a person is validated, stored with provenance, and CHECKED AT ONCE through its cheapest tier (z3 → decided)', a1['ok'] and a1['status'] == 'decided' and a1['check']['tier'] == 'z3' and 'authored by a person' in next(c_ for c_ in m.objectTables['MathClaim'].values() if c_.name == 'my-claim').provenance, a1)
check('  …a second claim with the same name is refused (409: claims are re-checked, not re-written); a bad kind, a missing row, an invalid term are refused by name',
      authoring.author(m, {'name': 'my-claim', 'statement': {'le': [1, 2]}}, make=_mk(m), save=False).get('status') == 409
      and 'kind' in authoring.author(m, {'name': 'k9', 'kind': 'vibes', 'statement': {'le': [1, 2]}}, make=_mk(m), save=False)['error']
      and 'do not exist' in authoring.author(m, {'name': 'k9', 'about': ['TensorMapping:nope'], 'statement': {'le': [1, 2]}}, make=_mk(m), save=False)['error']
      and authoring.author(m, {'name': 'k9', 'statement': {'frob': 1}}, make=_mk(m), save=False).get('errors'))
a2 = authoring.author(m, {'name': 'my-theorem', 'kind': 'symmetry', 'statement': {'symbolic': {'template': 'symmetry-of-contraction', 'args': {'n': 'any'}}}}, make=_mk(m), save=False)
check('  …a general statement (lean) is stored but NOT run (plan §I.9) — the answer says how to ask', a2['ok'] and a2['status'] == 'conjectured' and a2['check']['verdict'] is None and 'tier=lean' in a2['check']['note'])
pr = authoring.propose_from_discovery(m, 'm2', 'sel-s', make=_mk(m), save=False)
check('propose_from_discovery: the candidate\'s validity on THIS selection becomes a durable row — subset(scope:<claim>, validity:m2) with the selection\'s ranges as scope — and the interval tier DECIDES it at once (strain [0, 0.0005] ⊆ [0, 0.001])',
      pr['ok'] and pr['proposed'][0]['what'] == 'valid-on-selection' and pr['proposed'][0]['status'] == 'decided' and json.loads(next(c_ for c_ in m.objectTables['MathClaim'].values() if c_.name == pr['proposed'][0]['claim']).scope_json)['strain'] == [0, 0.0005], pr)
sel_big = _add(m, 'TensorSelection', name='sel-big', node='s', ranges_json=json.dumps({'strain': [0, 0.004]}))
pr2 = authoring.propose_from_discovery(m, 'm2', 'sel-big', via='m1', make=_mk(m), save=False)
check('  …a selection outside the validity is REFUTED with the dim named; arriving via m1, the chain pair (domains, dims) is proposed too and decided; the obligations carry the rule name proposed-from-discovery',
      pr2['ok'] and pr2['proposed'][0]['status'] == 'refuted' and 'strain' in pr2['proposed'][0]['counterexample'] and [p_['what'] for p_ in pr2['proposed']] == ['valid-on-selection', 'chain-domain-inclusion', 'dims-compose']
      and pr2['proposed'][1]['status'] == 'decided' and all(o.rule == 'proposed-from-discovery' for o in m.objectTables['ProofObligation'].values() if o.name.startswith('ob:proposed:sel-big')), pr2)
check('  …proposing twice is idempotent by name; a missing selection / mapping is a 404 by name', len({o.name for o in m.objectTables['ProofObligation'].values() if o.name.startswith('ob:proposed:sel-big')}) == 3
      and len(authoring.propose_from_discovery(m, 'm2', 'sel-big', via='m1', make=_mk(m), save=False)['proposed']) == 3 and authoring.propose_from_discovery(m, 'm2', 'nope', make=_mk(m), save=False).get('status') == 404)
d3 = discover(m, sel, context_mapping='m1')
check('  …and every discovery candidate now CARRIES the door (method, path, body incl. via) through the soft seam', all(c_.get('propose', {}).get('path') == '/api/mathproofs/obligations/propose' and c_['propose']['body'].get('via') == 'm1' for c_ in d3['candidates']), [c_.get('propose') for c_ in d3['candidates']][:1])

# ---- manifest
from moduleService.manifests import validate
man = json.load(open(os.path.join(HERE, 'polari-app.json')))
check('the manifest is valid, declares four classes + the API, requires sympy + z3 (libraries, in-process), and declares `lean` as an ENGINE (resolved through the engines ladder, never a device assumption)',
      validate(man) == [] and len([c_ for c_ in man['classes'] if c_ != 'MathProofsAPI']) == 4 and man['requires']['libraries'] == ['sympy', 'z3'] and man['requires']['engines'][0]['name'] == 'lean' and 'custom/z3tier' in man['files']['custom'] and 'custom/boot' in man['files']['custom'] and 'custom/lean_tier' in man['files']['custom'] and 'custom/proof_engines' in man['files']['custom'] and 'custom/authoring' in man['files']['custom'])

n_ok = sum(1 for _, ok in _results if ok)
print('\n%d/%d checks passed' % (n_ok, len(_results)))
sys.exit(0 if n_ok == len(_results) else 1)
