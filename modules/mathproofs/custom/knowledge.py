"""
@module mathproofs.custom.knowledge

PROOFS AS KNOWLEDGE (plan §I.7 pf-4): the mathematics the tensor arc's readings REST ON, as a tech tree the learning
layer can point at — one TechNode per idea, edges = recommended learning order, each node CITING the MathClaims that
establish it (cross_refs relation `proved-by`) and the compute-lod rungs / tensortree rules it underwrites (relation
`rests-on` / `underwrites`). Nothing here is a copy of a claim: the claims stay the truth, the node is the place a
person learns from, and `reading(manager)` joins the two LIVE — a node is `established` only while every claim it
cites is SETTLED — it holds (witnessed / decided / checked-symbolically / proved, not stale) or it is refuted by a
counterexample (a refutation is knowledge too); an open / undetermined / stale claim shows on the node it belongs to,
so the tree says what is actually known, not what was planned.

The tree is `tensor-proofs`; the rows belong to techtree (seeded only when it is present, exactly as computelod's
concept tree). The compute-lod rungs are joined by name (`lod-<rung>` TechNodes of computelod's tree).
"""
import json

from mathproofs.custom import checkers
from mathproofs.custom.rows import _rows, by_name

TREE = 'tensor-proofs'
OK = ('witnessed', 'decided', 'checked-symbolically', 'proved')


def _n(name, title, description, depends=(), claims=(), rules=(), rungs=(), mappings=(), column=0):
    refs = [{'module': 'mathproofs', 'class': 'MathClaim', 'name': c, 'relation': 'proved-by'} for c in claims]
    refs += [{'module': 'mathproofs', 'class': 'InferenceRule', 'name': r, 'relation': 'underwrites'} for r in rules]
    refs += [{'module': 'computelod', 'class': 'ComputeLOD', 'name': r, 'relation': 'rests-on'} for r in rungs]
    refs += [{'module': 'tensortree', 'class': 'TensorMapping', 'name': m, 'relation': 'rests-on'} for m in mappings]
    return {'name': name, 'tree_name': TREE, 'title': title, 'description': description, 'depends_on_json': json.dumps(list(depends)),
            'layout_hints_json': json.dumps({'column': column}), 'cross_refs_json': json.dumps(refs), 'data_dependencies_json': '[]', 'notes': ''}


SEED_PROOF_TECH_TREES = [{'name': TREE, 'title': 'The mathematics the tensor arc rests on — what to learn, and what is actually established',
                          'owner': 'polari', 'description': 'One node per idea the tensor trees and the compute ladder depend on; each cites the MathClaims that establish it, '
                                                            'and the reading joins them LIVE: a node is established only while every claim it cites is ok (plan §I pf-4).',
                          'is_active': False, 'is_baseline': False, 'notes': 'plan COMPUTE_LOD_TENSOR_PLAN.md §I.7 pf-4'}]

SEED_PROOF_TECH_NODES = [
    _n('pf-witness-vs-proof', 'A witness is not a proof', 'The vocabulary every other node is read through: a numeric witness holds ON THE ROWS WE HAVE (measured); an interval / z3 decision '
       'and a SymPy check hold for every value (analytical); a Lean theorem is machine-checked; inapplicable (not defined on this state space) ≠ undetermined (a premise fails / unrecorded) ≠ refuted (a counterexample).',
       column=0),
    _n('pf-index-notation', 'Named-dimension contraction', 'σ_ij = C_ijkl ε_kl as a contraction over named dims — what the tensormath operator does and what every symmetry statement is written in.',
       depends=('pf-witness-vs-proof',), mappings=('eps→sigma',), rungs=('rtl',), column=1),
    _n('pf-minor-symmetries', 'Minor symmetries of the stiffness', 'C_ijkl = C_jikl suffices for σ to be symmetric — checked over symbols in 2-D and 3-D, proved for every rank; the second minor symmetry and ε\'s symmetry matter for the inverse map, not for this direction.',
       depends=('pf-index-notation',), claims=('sigma-from-strain-is-symmetric', 'sigma-from-strain-is-symmetric-3d', 'sigma-symmetry-general-rank'), rules=('operator-symmetry',), column=2),
    _n('pf-linear-composition', 'Linear links compose to a linear map', 'u→ε (the symmetric gradient) and ε→σ (Hooke) are linear, so their composition is — over symbols; the FEM solve rests on it.',
       depends=('pf-index-notation',), claims=('ob:plate-mechanics:operator-linear:u→eps-eps→sigma',), rules=('operator-linear',), column=2),
    _n('pf-interval-domains', 'Validity domains as boxes', 'A mapping is valid on a box over dims; a selection is a box; ⊆ on boxes is per-dim range inclusion — decided exactly, and re-derived by z3 as ∀x∈A: x∈B; the converse of an inclusion is refuted by a POINT (a speed of 6 m/s), not by a feeling.',
       depends=('pf-witness-vs-proof',), claims=('spectrum-range-inside-the-drag-coupling-range', 'spectrum-valid-over-the-drag-coupling-range'), rules=('chain-domain-inclusion', 'dims-compose'), mappings=('wind-grid→spectrum', 'wind-grid→bob-drag'), column=1),
    _n('pf-chain-composition', 'Pairwise inclusion makes a chain valid', 'If every link\'s domain lies inside the previous one\'s, the chain is valid on the last domain and that domain is the intersection — so checking neighbours suffices (the Lean lemma).',
       depends=('pf-interval-domains',), claims=('chain-domains-compose-lemma', 'ob:plate-mechanics:chain-domain-inclusion:u→eps-eps→sigma', 'ob:plate-mechanics:chain-domain-inclusion:eps→sigma-sigma→balance'), column=2),
    _n('pf-restriction', 'Restriction is idempotent', 'Keeping an index range twice is keeping it once — the smoke theorem, and what makes a slice of a slice the slice.',
       depends=('pf-interval-domains',), claims=('restriction-idempotent-theorem', 'ob:wind-spatial:restriction-idempotent:wind-grid→slice-z0'), rules=('restriction-idempotent',), column=2),
    _n('pf-decomposition-error', 'A decomposition must say what it loses', 'A reconstruction error with a stated method, within the rule\'s bound (a knob); with none recorded the claim is undetermined, not refuted.',
       depends=('pf-witness-vs-proof',), claims=('ob:wind-spatial:decomposition-reconstructs:wind-grid→spectrum',), rules=('decomposition-reconstructs',), mappings=('wind-grid→spectrum',), column=1),
    _n('pf-fixed-point', 'Fixed-point arithmetic and overflow', 'Scaling reals to integers (kPa, nano-strain) and accumulating in a wider word: the operands must fit their ports and no prefix sum may leave the accumulator — decided over exact integers, with the bounds read from the rows.',
       depends=('pf-witness-vs-proof',), claims=('fpga-nano-strain-fits-int32', 'fpga-C-in-kPa-fits-int32-for-electrical-steel', 'fpga-int64-accumulate-never-overflows'), rungs=('rtl', 'microarchitecture'), column=1),
    _n('pf-two-sources-agree', 'Two independent sources agreeing is evidence', 'LEF footprints summed and the Liberty\'s areas; our transistor-level delays and the foundry\'s; extraction narrowing one gap and widening another — witnesses on the rows, never theorems, and honest about it.',
       depends=('pf-witness-vs-proof',), claims=('lod3-lef-area-equals-liberty-area', 'lod3b-falls-faster-than-liberty', 'lod3c-extraction-slows-every-arc', 'lod3c-extraction-narrows-every-fall-gap', 'lod3c-extraction-widens-every-rise-gap'),
       rungs=('standard-cells', 'devices', 'layout'), column=1),
]

SEED_PROOF_TECH_SEGMENTS = [{'name': 'pf:%s:%s' % (n['name'], c['name']), 'tech_node': n['name'], 'tree_name': TREE, 'segment_kind': 'theory', 'ref_name': c['name'], 'notes': c['relation']}
                            for n in SEED_PROOF_TECH_NODES for c in json.loads(n['cross_refs_json']) if c['class'] == 'MathClaim']


def reading(manager):
    """The tree joined LIVE to the claims: per node the cited claims with their current status, whether the node is established, and what it underwrites."""
    nodes = [n for n in _rows(manager, 'TechNode') if str(getattr(n, 'tree_name', '')) == TREE]
    out = []
    for n in sorted(nodes, key=lambda x: (json.loads(getattr(x, 'layout_hints_json', '{}') or '{}').get('column', 0), str(x.name))):
        refs = json.loads(getattr(n, 'cross_refs_json', '[]') or '[]')
        cited = []
        for r in refs:
            if r.get('class') != 'MathClaim':
                continue
            c = by_name(manager, 'MathClaim', r['name'])
            st = checkers.status_of(manager, c) if c is not None else 'missing (not generated on this instance)'
            head = st.split(' ')[0]; fresh = '(stale)' not in st
            # settled = the claim has a definite answer that still stands: it holds, OR it is refuted by a counterexample (a
            # refutation is knowledge too — "the converse fails at speed 6" is a fact a person learns); open / undetermined /
            # unprovable-here / stale are not settled
            cited.append({'claim': r['name'], 'status': st, 'holds': head in OK and fresh, 'settled': (head in OK or head == 'refuted') and fresh})
        established = bool(cited) and all(c['settled'] for c in cited)
        out.append({'node': str(n.name), 'title': str(getattr(n, 'title', '')), 'depends_on': json.loads(getattr(n, 'depends_on_json', '[]') or '[]'), 'claims': cited,
                    'established': established, 'refutations': [c['claim'] for c in cited if c['settled'] and not c['holds']],
                    'why': ('every cited claim is settled' if established else ('no claim cited: a concept, not a result' if not cited else 'a cited claim is ' + ', '.join(sorted({c['status'] for c in cited if not c['settled']})))),
                    'underwrites': [{'class': r['class'], 'name': r['name'], 'relation': r['relation']} for r in refs if r.get('class') != 'MathClaim']})
    by_rung = {}
    for o in out:
        for u in o['underwrites']:
            if u['class'] == 'ComputeLOD':
                by_rung.setdefault(u['name'], []).append({'node': o['node'], 'established': o['established']})
    return {'tree': TREE, 'nodes': out, 'established': sum(1 for o in out if o['established']), 'by_rung': by_rung,
            'note': 'a node is established only while every claim it cites is settled (holds, or refuted by a counterexample) and not stale; an open / undetermined claim shows on the node it belongs to — the tree says what is known, not what was planned'}
