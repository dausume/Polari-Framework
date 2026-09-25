"""
@module mathproofs.mathproofs_selftest

pf-0 selftest (no server): the four rows; the term language (validate, canonical hash, derived LaTeX); the numeric
witness (holds / refuted with the counterexample / unprovable-here by name); the interval decision; the SymPy
templates over symbols; the checker's status vocabulary (a witness is never a proof; refuted always wins; a weaker
tier never overwrites a stronger verdict); staleness; the inference rules generating obligations on the seeded
tensor trees (chains found, dims composed, a decomposition with no recorded error REFUSED); discovery refusing on a
refuted obligation through the soft seam; the manifest.

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
from mathproofs.custom import terms, numeric, symbolic, checkers, rules  # noqa: E402

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
check('MathClaim defaults: conjectured, no checker, evidence none, budget 10 s (D-pf-9, a knob)', c.proof_status == 'conjectured' and c.checker == '' and c.evidence_level == 'none' and c.budget_s == 10.0)
check('the seed pairs cover every class; eight inference rules; five standalone claims', {p[0] for p in MATHPROOFS_SEED_PAIRS} == {c_.__name__ for c_ in MATHPROOFS_CLASSES} and len(SEED_INFERENCE_RULES) == 8 and len(SEED_MATH_CLAIMS) == 5)
check('every seeded rule names a pattern, a claim kind and a default checker; two are honestly template-less (units, evidence rank: not decidable here)',
      all(r['pattern'] and r['obligation_kind'] and r['checker_default'] in CHECKERS for r in SEED_INFERENCE_RULES) and sum(1 for r in SEED_INFERENCE_RULES if r['template_json'] == '{}') == 2)

# ---- the term language
t_eq = {'eq': [{'ref': 'CharacterizationMapping:a', 'path': ['result']}, 3.0], 'tol': {'abs': 0.01}}
check('validate: a well-formed term is [] ; a bad ref / unknown operator / a forall without holds are named',
      terms.validate(t_eq) == [] and terms.validate({'ref': 'x'}) and terms.validate({'frobnicate': 1}) and terms.validate({'forall': [{'var': 'x', 'in': 'rows:A'}]}))
check('canonical + statement_hash are stable under key order', terms.statement_hash({'eq': [1, 2], 'tol': {'abs': 0.1}}) == terms.statement_hash({'tol': {'abs': 0.1}, 'eq': [1, 2]}))
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

# ---- symbolic
r = symbolic.evaluate({'symbolic': {'template': 'symmetry-of-contraction', 'args': {'n': 2}}})
check('sympy: σ = C:ε symmetric over 12 free symbols in 2-D (residual simplifies to 0)', r['verdict'] == 'holds' and r['detail']['free_symbols'] == 12 and r['detail']['residuals'] == {'01': '0'})
check('  …and in 3-D (42 symbols)', symbolic.evaluate({'symbolic': {'template': 'symmetry-of-contraction', 'args': {'n': 3}}})['detail']['free_symbols'] == 42)
check('  …linear composition and restriction idempotence hold over symbols', symbolic.evaluate({'symbolic': {'template': 'linear-composition', 'args': {}}})['verdict'] == 'holds' and symbolic.evaluate({'symbolic': {'template': 'restriction-idempotent', 'args': {}}})['verdict'] == 'holds')
check('  …a free expression is refused by name (templates only in v0)', symbolic.evaluate({'eq': [1, 1]})['verdict'] == 'unprovable-here')

# ---- the checker: runs, vocabulary, staleness
cl = _add(m, 'MathClaim', name='k1', kind='identity', about_refs_json=json.dumps(['CharacterizationMapping:a']), statement_json=json.dumps(t_eq), proof_status='conjectured', checker='', certificate_ref='',
          counterexample_json='{}', evidence_level='none', statement_hash='', statement_latex='', budget_s=10.0)
res = checkers.check(m, cl, make=_mk(m), save=False)
check('check: a numeric holds → WITNESSED with evidence MEASURED (on these rows), a ProofRun with the rows-state hash, the derived LaTeX + hash filled',
      res['after'] == 'witnessed' and cl.evidence_level == 'measured' and cl.checker == 'numeric' and len(m.objectTables['ProofRun']) == 1 and cl.statement_hash and cl.statement_latex and res['run']['rows_state_hash'], res)
check('  …the claim is not stale while its rows stand', not checkers.stale(m, cl) and checkers.status_of(m, cl) == 'witnessed')
m.objectTables['CharacterizationMapping'][[k for k, v in m.objectTables['CharacterizationMapping'].items() if v.name == 'a'][0]].result = 3.5
check('  …and becomes STALE the moment the row it speaks of changes (never silently still witnessed)', checkers.stale(m, cl) and checkers.status_of(m, cl) == 'witnessed (stale)')
res = checkers.check(m, cl, make=_mk(m), save=False)
check('  …re-checking refutes it now, and refuted keeps the counterexample', res['after'] == 'refuted' and json.loads(cl.counterexample_json)['lhs'] == 3.5)
cs = _add(m, 'MathClaim', name='k2', kind='symmetry', about_refs_json='[]', statement_json=json.dumps({'symbolic': {'template': 'symmetry-of-contraction', 'args': {'n': 2}}}), proof_status='conjectured', checker='', certificate_ref='',
          counterexample_json='{}', evidence_level='none', statement_hash='', statement_latex='', budget_s=10.0)
res = checkers.check(m, cs, make=_mk(m), save=False)
check('  …a symbolic holds → CHECKED-SYMBOLICALLY, evidence ANALYTICAL; auto_tier picked sympy', res['after'] == 'checked-symbolically' and cs.evidence_level == 'analytical' and res['tier'] == 'sympy')
res = checkers.check(m, cs, tier='numeric', make=_mk(m), save=False)
check('  …the numeric tier cannot lower a symbolic term → unprovable-here, and the STRONGER verdict stands (a weaker tier never overwrites)', res['verdict'] == 'unprovable-here' and cs.proof_status == 'checked-symbolically')
res = checkers.check(m, cs, tier='lean', make=_mk(m), save=False)
check('  …the lean tier refuses by name until pf-2 (an engines worker), status unchanged', res['verdict'] == 'unprovable-here' and 'pf-2' in res['detail']['why'] and cs.proof_status == 'checked-symbolically')

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
d2 = discover(m, sel)
check('  …discovery: an inapplicable mapping (outside the state space) and a refuted one are DIFFERENT lists with different words; the old `refused` key is their union', 'inapplicable' in d2 and 'refuted' in d2 and len(d2['refused']) == len(d2['inapplicable']) + len(d2['refuted']))

# ---- manifest
from moduleService.manifests import validate
man = json.load(open(os.path.join(HERE, 'polari-app.json')))
check('the manifest is valid, declares four classes + the API, requires sympy, and declares `lean` as an ENGINE (resolved through the engines ladder, never a device assumption)',
      validate(man) == [] and len([c_ for c_ in man['classes'] if c_ != 'MathProofsAPI']) == 4 and man['requires']['libraries'] == ['sympy'] and man['requires']['engines'][0]['name'] == 'lean')

n_ok = sum(1 for _, ok in _results if ok)
print('\n%d/%d checks passed' % (n_ok, len(_results)))
sys.exit(0 if n_ok == len(_results) else 1)
