"""
@module mathproofs.mathproofs_seed

pf-0 seeds: the EIGHT inference rules (the logic between parts of a tree, as data — plan §I.3), and the standalone
claims of §I.5 the cheap tiers can speak to today (lod cross-checks as claims; σ = C:ε symmetry over symbols).
pf-1 adds the z3 claims (the tt-3 kernel's fixed-point contract over machine integers and the continuum; two
domain statements over the wind tree, one of them refuted by a model) and the parasitics verdict as two inequalities;
the decomposition bound became the rule's knob (`params_json.bound`); pf-2 adds the three theorem claims (D-pf-10),
proved by committed .lean certificates when a person asks. Obligations themselves are GENERATED per tree —
at boot (custom/boot.py) and on `POST /api/mathproofs/trees/{name}/obligations` — not seeded.
"""
import json

from mathproofs.mathproofs_basis import MathClaim, ProofRun, InferenceRule, ProofObligation

_R = lambda **k: dict({'description': '', 'enabled': True, 'params_json': '{}', 'notes': ''}, **k)
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
                                 'holds': {'le': [{'ref': 'TensorMapping:{m1}', 'path': ['reconstruction_error']}, {'ref': 'InferenceRule:decomposition-reconstructs', 'path': ['params_json', 'bound']}]}}),
       params_json=json.dumps({'bound': 0.05, 'bound_note': 'the largest reconstruction error a decomposition may carry and still discharge this obligation (relative, by the mapping\'s own error_method) — a POLICY a person edits here; every obligation under it goes stale when it changes'}),
       rationale='a decomposition must SAY what it loses. GIVEN a recorded reconstruction error (error_method names how it was measured), it must be within the rule\'s bound (params_json.bound, a knob — read by ref, so the claim names it); with none recorded the claim is UNDETERMINED: not defined yet, not falsified'),
    _R(name='operator-linear', pattern='chain:operator,operator', obligation_kind='composition', checker_default='sympy',
       template_json=json.dumps({'symbolic': {'template': 'linear-composition', 'args': {}}}),
       rationale='two linear operator links compose to a linear map — proved over symbols; the obligation assumes both links are linear (u→ε and ε→σ are)'),
    _R(name='operator-symmetry', pattern='mapping:operator:contract', obligation_kind='symmetry', checker_default='sympy',
       template_json=json.dumps({'symbolic': {'template': 'symmetry-of-contraction', 'args': {'n': 2}}}),
       rationale='an operator that is a contraction with a minor-symmetric tensor preserves symmetry (σ = C:ε) — proved over symbols in the plate\'s dimension'),
]

_C = lambda **k: dict({'description': '', 'assumptions_json': '[]', 'scope_json': '{}', 'proof_status': 'conjectured', 'checker': '', 'certificate_ref': '', 'counterexample_json': '{}',
                       'evidence_level': 'none', 'statement_hash': '', 'statement_latex': '', 'budget_s': 25.0, 'provenance': 'seed (pf-0)', 'notes': ''}, **k)
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
    # ---- pf-1: the parasitics verdict of lod-3c as TWO inequalities over the extracted arcs (numeric witnesses)
    _C(name='lod3c-extraction-narrows-every-fall-gap', kind='inequality', about_refs_json=json.dumps(['CharacterizationMapping:lod3c: inv_1 A→Y tpHL (extracted)', 'CharacterizationMapping:lod3c: nand2_1 A→Y tpHL (extracted)', 'CharacterizationMapping:lod3c: nand2_1 B→Y tpHL (extracted)']),
       statement_json=json.dumps({'forall': [{'var': 'c', 'in': 'rows:CharacterizationMapping:name~tpHL (extracted)'}],
                                  'holds': {'and': [{'gt': [{'ref': 'c', 'path': ['conditions_json', 'delta_pct']}, {'ref': 'c', 'path': ['conditions_json', 'schematic_delta_pct']}]},
                                                    {'lt': [{'ref': 'c', 'path': ['conditions_json', 'delta_pct']}, 0]}]}}),
       description='WITNESS (the parasitics verdict, half 1): on every extracted tpHL arc the gap to the Liberty is SMALLER than the schematic netlist\'s (delta_pct > schematic_delta_pct, both negative) — extraction explains PART of the fall gap'),
    _C(name='lod3c-extraction-widens-every-rise-gap', kind='inequality', about_refs_json=json.dumps(['CharacterizationMapping:lod3c: inv_1 A→Y tpLH (extracted)', 'CharacterizationMapping:lod3c: nand2_1 A→Y tpLH (extracted)', 'CharacterizationMapping:lod3c: nand2_1 B→Y tpLH (extracted)']),
       statement_json=json.dumps({'forall': [{'var': 'c', 'in': 'rows:CharacterizationMapping:name~tpLH (extracted)'}],
                                  'holds': {'and': [{'gt': [{'ref': 'c', 'path': ['conditions_json', 'delta_pct']}, {'ref': 'c', 'path': ['conditions_json', 'schematic_delta_pct']}]},
                                                    {'gt': [{'ref': 'c', 'path': ['conditions_json', 'schematic_delta_pct']}, 0]}]}}),
       description='WITNESS (the parasitics verdict, half 2): on every extracted tpLH arc the gap to the Liberty is LARGER than the schematic netlist\'s (both positive: we are already slower on the rise, extraction makes it worse) — parasitics explain NONE of the rise gap; what remains is the vendor setup'),
    # ---- pf-1: the tt-3 kernel's fixed-point contract, DECIDED (z3): the bounds are read from the rows that state them
    _C(name='fpga-nano-strain-fits-int32', kind='bound', about_refs_json=json.dumps(['ComputeImplementation:stress-from-strain/fpga-stress-mac', 'TensorMapping:eps→sigma']),
       statement_json=json.dumps({'forall': [{'var': 'x', 'in': 'validity:eps→sigma'}],
                                  'holds': {'and': [{'le': [{'mul': [{'ref': 'x', 'path': ['strain']}, 1000000000]}, 2147483647]}, {'ge': [{'mul': [{'ref': 'x', 'path': ['strain']}, 1000000000]}, -2147483647]}]}}),
       description='DECIDED over the continuum: for every strain in the mapping\'s validity domain, ε in nano-strain (×1e9) fits the kernel\'s signed 32-bit operand port'),
    _C(name='fpga-C-in-kPa-fits-int32-for-electrical-steel', kind='bound', about_refs_json=json.dumps(['ComputeImplementation:stress-from-strain/fpga-stress-mac', 'MagneticMaterialOption:opt-electrical-steel']),
       statement_json=json.dumps({'le': [{'mul': [{'ref': 'MagneticMaterialOption:opt-electrical-steel', 'path': ['properties_json', 'youngs_modulus_mpa', 'value']}, 1000]},
                                         {'mul': [2147483647, {'add': [1, {'mul': [-1, {'ref': 'MagneticMaterialOption:opt-electrical-steel', 'path': ['properties_json', 'poisson_ratio', 'value']}, {'ref': 'MagneticMaterialOption:opt-electrical-steel', 'path': ['properties_json', 'poisson_ratio', 'value']}]}]}]}]}),
       description='WITNESS on the cited material: the largest plane-stress stiffness E/(1−ν²) in kPa (E in MPa × 1e3) fits the signed 32-bit coefficient port — E·10³ ≤ (2³¹−1)(1−ν²)'),
    _C(name='fpga-int64-accumulate-never-overflows', kind='bound', about_refs_json=json.dumps(['ComputeImplementation:stress-from-strain/fpga-stress-mac', 'TensorMapping:eps→sigma']),
       statement_json=json.dumps({'bitvector': {'template': 'mac-no-overflow', 'args': {'products': 4, 'operand_bits': 32, 'acc_bits': 64, 'a_abs_max': 2147483647,
                                                                                         'b_abs_max': {'mul': [{'ref': 'TensorMapping:eps→sigma', 'path': ['validity_json', 'strain', 1]}, 1000000000]}}}}),
       description='DECIDED over the machine integers: the kernel\'s four products C_ijkl·ε_kl (any int32 coefficient; ε within the validity domain, in nε) summed in the 64-bit accumulator never overflow — the tt-3 kernel\'s exactness claim as a decision, not a comment'),
    # ---- pf-1: domains over a continuum (z3) — one decided, one REFUTED with the model as the counterexample
    _C(name='spectrum-range-inside-the-drag-coupling-range', kind='domain-inclusion', about_refs_json=json.dumps(['TensorMapping:wind-grid→spectrum', 'TensorMapping:wind-grid→bob-drag']),
       statement_json=json.dumps({'forall': [{'var': 'x', 'in': 'validity:wind-grid→spectrum'}], 'holds': {'in': ['x', 'validity:wind-grid→bob-drag']}}),
       description='DECIDED: every wind speed the proposed decomposition claims (0–5 m/s) is one the drag coupling is valid for (0–30 m/s)'),
    _C(name='spectrum-valid-over-the-drag-coupling-range', kind='domain-inclusion', about_refs_json=json.dumps(['TensorMapping:wind-grid→spectrum', 'TensorMapping:wind-grid→bob-drag']),
       statement_json=json.dumps({'forall': [{'var': 'x', 'in': 'validity:wind-grid→bob-drag'}], 'holds': {'in': ['x', 'validity:wind-grid→spectrum']}}),
       description='the converse — is the decomposition valid wherever the drag coupling is? REFUTED by a model: a wind speed inside the coupling\'s range and outside the decomposition\'s (the counterexample is a real point, kept)'),
    # ---- pf-2: the theorems (D-pf-10) — proved by committed .lean certificates in polari-proof-tools, checked through the
    # engines worker when a PERSON asks (never at boot); budget 300 s: Mathlib's imports load before the check runs
    _C(name='sigma-symmetry-general-rank', kind='symmetry', about_refs_json=json.dumps(['TensorMapping:eps→sigma']), budget_s=300.0,
       statement_json=json.dumps({'symbolic': {'template': 'symmetry-of-contraction', 'args': {'n': 'any'}}}),
       description='THE THEOREM (D-pf-10 a): σ = C:ε is symmetric in EVERY rank n given C\'s first minor symmetry — sympy checked 2-D and 3-D; the general statement is proved by PolariProofs/SigmaSymmetry.lean under the pinned Lean + Mathlib'),
    _C(name='chain-domains-compose-lemma', kind='composition', about_refs_json=json.dumps(['InferenceRule:chain-domain-inclusion']), budget_s=300.0,
       statement_json=json.dumps({'symbolic': {'template': 'chain-domains-compose', 'args': {'links': 'any'}}}),
       description='THE TREE-COMPOSITION LEMMA (D-pf-10 b): pairwise inclusion V_{i+1} ⊆ V_i along a chain makes the chain valid on the last domain, which IS the intersection — the reason the chain-domain-inclusion rule\'s pairwise obligations suffice; PolariProofs/ChainComposition.lean'),
    _C(name='restriction-idempotent-theorem', kind='identity', about_refs_json='[]', budget_s=300.0,
       statement_json=json.dumps({'symbolic': {'template': 'restriction-idempotent', 'args': {}}}),
       description='the toolchain smoke test (D-pf-10 c): the same statement the sympy tier checks for a fixed range, as a Lean theorem over any index type — PolariProofs/RestrictionIdempotent.lean; ask ?tier=lean'),
]

MATHPROOFS_SEED_PAIRS = [
    ('InferenceRule', InferenceRule, SEED_INFERENCE_RULES),
    ('MathClaim', MathClaim, SEED_MATH_CLAIMS),
    ('ProofRun', ProofRun, []),
    ('ProofObligation', ProofObligation, []),
]
