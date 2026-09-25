"""
@module mathproofs.mathproofs_seed

pf-0 seeds: the EIGHT inference rules (the logic between parts of a tree, as data — plan §I.3), and the standalone
claims of §I.5 the cheap tiers can speak to today (lod cross-checks as claims; σ = C:ε symmetry over symbols).
Obligations themselves are GENERATED per tree (`POST /api/mathproofs/trees/{name}/obligations`), not seeded.
"""
import json

from mathproofs.mathproofs_basis import MathClaim, ProofRun, InferenceRule, ProofObligation

_R = lambda **k: dict({'description': '', 'enabled': True, 'notes': ''}, **k)
SEED_INFERENCE_RULES = [
    _R(name='chain-domain-inclusion', pattern='chain', obligation_kind='domain-inclusion', checker_default='interval',
       template_json=json.dumps({'subset': ['validity:{m2}', 'validity:{m1}']}),
       rationale='a chain m1 → node → m2 is legitimate only where the second link\'s validity lies inside the first\'s on every dimension they share; dims only one of them constrains are unconstrained, not violated'),
    _R(name='dims-compose', pattern='chain', obligation_kind='well-typed', checker_default='interval',
       template_json=json.dumps({'dims_subset': ['{m2}.source_dims', '{m1}.target_dims']}),
       rationale='what the second link consumes at the node must be what the first link produced there (source dims ⊆ the previous target dims)'),
    _R(name='units-compose', pattern='chain', obligation_kind='well-typed', checker_default='numeric', template_json='{}',
       rationale='units must compose along a chain — NOT decidable here: mappings carry one `units` string, not per-dim units; the obligation stands open as a named gap'),
    _R(name='evidence-monotone', pattern='mapping:scale', obligation_kind='bound', checker_default='numeric', template_json='{}',
       rationale='a scale mapping\'s evidence never exceeds its pspp transfer\'s — the transfer status is a string vocabulary, not a number; open until a rank reader exists'),
    _R(name='restriction-idempotent', pattern='mapping:restriction', obligation_kind='identity', checker_default='sympy',
       template_json=json.dumps({'symbolic': {'template': 'restriction-idempotent', 'args': {}}}),
       rationale='restricting twice is restricting once — proved over symbols for an index-range restriction; the obligation assumes the mapping IS one'),
    _R(name='decomposition-reconstructs', pattern='mapping:decomposition', obligation_kind='bound', checker_default='numeric',
       template_json=json.dumps({'given': {'recorded': {'ref': 'TensorMapping:{m1}', 'path': ['error_method']}},
                                 'holds': {'le': [{'ref': 'TensorMapping:{m1}', 'path': ['reconstruction_error']}, 0.05]}}),
       rationale='a decomposition must SAY what it loses. GIVEN a recorded reconstruction error (error_method names how it was measured), it must be within the bound (0.05 — a placeholder knob, pf-1 moves it to policy); with none recorded the claim is UNDETERMINED: not defined yet, not falsified'),
    _R(name='operator-linear', pattern='chain:operator,operator', obligation_kind='composition', checker_default='sympy',
       template_json=json.dumps({'symbolic': {'template': 'linear-composition', 'args': {}}}),
       rationale='two linear operator links compose to a linear map — proved over symbols; the obligation assumes both links are linear (u→ε and ε→σ are)'),
    _R(name='operator-symmetry', pattern='mapping:operator:contract', obligation_kind='symmetry', checker_default='sympy',
       template_json=json.dumps({'symbolic': {'template': 'symmetry-of-contraction', 'args': {'n': 2}}}),
       rationale='an operator that is a contraction with a minor-symmetric tensor preserves symmetry (σ = C:ε) — proved over symbols in the plate\'s dimension'),
]

_C = lambda **k: dict({'description': '', 'assumptions_json': '[]', 'scope_json': '{}', 'proof_status': 'conjectured', 'checker': '', 'certificate_ref': '', 'counterexample_json': '{}',
                       'evidence_level': 'none', 'statement_hash': '', 'statement_latex': '', 'budget_s': 10.0, 'provenance': 'seed (pf-0)', 'notes': ''}, **k)
SEED_MATH_CLAIMS = [
    _C(name='lod3-lef-area-equals-liberty-area', kind='identity', about_refs_json=json.dumps(['CharacterizationMapping:lod3: rv32_add layout area (LEF)', 'CharacterizationMapping:lod2: rv32_add cell area']),
       statement_json=json.dumps({'eq': [{'ref': 'CharacterizationMapping:lod3: rv32_add layout area (LEF)', 'path': ['result']}, {'ref': 'CharacterizationMapping:lod2: rv32_add cell area', 'path': ['result']}], 'tol': {'abs': 0.01}}),
       description='two independent PDK sources (LEF footprints summed; the Liberty\'s cell areas) agree on the mapped adder\'s area'),
    _C(name='lod3b-falls-faster-than-liberty', kind='inequality', about_refs_json=json.dumps(['CharacterizationMapping:lod3: inv_1 A→Y tpHL', 'CharacterizationMapping:lod3: nand2_1 A→Y tpHL', 'CharacterizationMapping:lod3: nand2_1 B→Y tpHL']),
       statement_json=json.dumps({'forall': [{'var': 'c', 'in': 'rows:CharacterizationMapping:name~tpHL'}],
                                  'holds': {'lt': [{'ref': 'c', 'path': ['conditions_json', 'delta_pct']}, 0]}}),
       description='WITNESS on the arcs we ran: every tpHL characterization (schematic AND extracted) is faster than the Liberty (delta_pct < 0) — the sign the parasitics reading predicts'),
    _C(name='lod3c-extraction-slows-every-arc', kind='inequality', about_refs_json=json.dumps(['CharacterizationMapping:lod3c: inv_1 A→Y tpHL (extracted)']),
       statement_json=json.dumps({'forall': [{'var': 'c', 'in': 'rows:CharacterizationMapping:method=ngspice transient on the EXTRACTED netlist'}],
                                  'holds': {'gt': [{'mul': [{'ref': 'c', 'path': ['result']}, 1000]}, {'ref': 'c', 'path': ['conditions_json', 'schematic_ps']}]}}),
       description='WITNESS: parasitics add delay on every extracted arc — result (ns × 1000) exceeds the schematic value (ps) recorded in its conditions'),
    _C(name='sigma-from-strain-is-symmetric', kind='symmetry', about_refs_json=json.dumps(['TensorMapping:eps→sigma']),
       statement_json=json.dumps({'symbolic': {'template': 'symmetry-of-contraction', 'args': {'n': 2}}}),
       description='σ = C:ε preserves symmetry when C has the minor symmetries and ε is symmetric — over symbols, the plate\'s dimension'),
    _C(name='sigma-from-strain-is-symmetric-3d', kind='symmetry', about_refs_json=json.dumps(['TensorMapping:eps→sigma']),
       statement_json=json.dumps({'symbolic': {'template': 'symmetry-of-contraction', 'args': {'n': 3}}}),
       description='the same statement in three dimensions (the general-rank theorem is pf-2\'s Lean target, D-pf-10)'),
]

MATHPROOFS_SEED_PAIRS = [
    ('InferenceRule', InferenceRule, SEED_INFERENCE_RULES),
    ('MathClaim', MathClaim, SEED_MATH_CLAIMS),
    ('ProofRun', ProofRun, []),
    ('ProofObligation', ProofObligation, []),
]
