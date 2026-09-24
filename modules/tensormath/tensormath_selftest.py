"""
Selftest for tensormath (tt-0). Run from polari-framework/:
  PYTHONPATH=.:modules python3 modules/tensormath/tensormath_selftest.py
Fake manager; exercises: the six classes, an UNINTERPRETED tensor is valid, values by reference (matrix storage
reads a rank-N MatrixDefinition; the other kinds refuse by name), named-dimension contraction — σ_ij = C_ijkl
ε_kl on real numbers — reduce/permute/slice, delegation of rank ≤ 2 to the matrix module, the bridge rows.
"""
import json
import sys
import types

import numpy as np

from tensormath.tensormath_basis import (TENSORMATH_CLASSES, Tensor, TensorDimension, TensorMathExpression, TensorOperator,
                                         ComputeImplementation, TensorDecomposition)
from tensormath.tensormath_seed import TENSORMATH_SEED_PAIRS
from tensormath.custom.tensor_ops import values, evaluate, contract, dim_names, TensorOpsError

_results = []


def check(label, cond, extra=''):
    _results.append((label, bool(cond)))
    print(f'{"PASS" if cond else "FAIL"}: {label}' + (f' — {extra}' if extra and not cond else ''))


def _mgr():
    tables = {c.__name__: {} for c in TENSORMATH_CLASSES}; tables['MatrixDefinition'] = {}
    return types.SimpleNamespace(objectTables=tables, db=None)


def _add(mgr, cls, **kw):
    row = types.SimpleNamespace(**kw); mgr.objectTables[cls][id(row)] = row; return row


check('the module registers exactly SIX row classes', len(TENSORMATH_CLASSES) == 6, [c.__name__ for c in TENSORMATH_CLASSES])
check('every class is one file under objects/tensormath/', all(c.__module__ == 'tensormath.objects.tensormath.%s' % c.__name__ for c in TENSORMATH_CLASSES))
check('seed pairs cover every class and seed NO rows (a tensor is made over real values)', [p[0] for p in TENSORMATH_SEED_PAIRS] == [c.__name__ for c in TENSORMATH_CLASSES] and all(p[2] == [] for p in TENSORMATH_SEED_PAIRS))

# ---- an uninterpreted tensor is valid (plan §10)
t = Tensor(name='blob', rank=4, shape_json='[128,128,3,6]', dimensions_json=json.dumps([{'name': 'axis0', 'semantics': 'unknown'}] * 4))
check('a Tensor with UNKNOWN semantics on every axis is a valid row (plan §10)', t.semantics == 'unknown' and t.rank == 4 and t.storage_kind == 'matrix')
check('values are NEVER stored on the tensor: there is no values column', not hasattr(t, 'values_json') and hasattr(t, 'storage_ref'))
check('storage kinds are the four homes values already have (B4/D2): matrix | dataset | engine | claim — no threshold',
      'matrix | dataset | engine | claim' in open('modules/tensormath/objects/tensormath/Tensor.py').read() and 'threshold' in Tensor.__doc__)

# ---- values by reference: a rank-N MatrixDefinition
m = _mgr()
# C_ijkl for an isotropic material (λ=1, μ=2) in 3-D; ε a symmetric strain; σ = C:ε computed two ways
lam, mu = 1.0, 2.0
C = np.zeros((3, 3, 3, 3))
for i in range(3):
    for j in range(3):
        for k in range(3):
            for l in range(3):
                C[i, j, k, l] = lam * (i == j) * (k == l) + mu * ((i == k) * (j == l) + (i == l) * (j == k))
eps = np.array([[0.01, 0.002, 0.0], [0.002, -0.003, 0.001], [0.0, 0.001, 0.004]])
_add(m, 'MatrixDefinition', name='C-iso', values_json=json.dumps(C.tolist()), shape_json='[3,3,3,3]')
_add(m, 'MatrixDefinition', name='eps-1', values_json=json.dumps(eps.tolist()), shape_json='[3,3]')
tC = _add(m, 'Tensor', name='C', rank=4, shape_json='[3,3,3,3]', dimensions_json=json.dumps([{'name': n} for n in 'ijkl']), storage_kind='matrix', storage_ref='C-iso', semantics='stiffness')
tE = _add(m, 'Tensor', name='eps', rank=2, shape_json='[3,3]', dimensions_json=json.dumps([{'name': n} for n in 'kl']), storage_kind='matrix', storage_ref='eps-1', semantics='strain')
check('matrix storage: the values are READ from the rank-N MatrixDefinition row (numpy at runtime)', np.allclose(values(m, tC), C) and values(m, tC).shape == (3, 3, 3, 3))
check('named dims come from dimensions_json', dim_names(tC) == ['i', 'j', 'k', 'l'])
r, out, spec = contract(values(m, tC), ['i', 'j', 'k', 'l'], values(m, tE), ['k', 'l'], ['k', 'l'])
sigma = lam * np.trace(eps) * np.eye(3) + 2 * mu * eps
check('σ_ij = C_ijkl ε_kl by NAMED contraction equals the closed form λ tr(ε) I + 2 μ ε', np.allclose(r, sigma) and out == ['i', 'j'], spec)
check('  …and the einsum it used is legible', spec == 'abcd,cd->ab', spec)
ex = _add(m, 'TensorMathExpression', name='sigma', operation='contract', operands_json=json.dumps([{'tensor': 'C'}, {'tensor': 'eps'}]), dims_json='["k","l"]', matrix_equation_ref='', latex=r'\\sigma_{ij} = C_{ijkl}\\epsilon_{kl}')
res = evaluate(m, ex)
check('evaluate(expression) runs the contraction and returns values + dims + shape', np.allclose(np.array(res['values']), sigma) and res['dims'] == ['i', 'j'] and res['shape'] == [3, 3])
try:
    contract(values(m, tC), ['i', 'j', 'k', 'l'], values(m, tE), ['k', 'l'], ['i'])
    check('contracting a dim that is not on both operands is refused', False)
except TensorOpsError as e:
    check('contracting a dim that is not on both operands is refused, naming the dim', "'i'" in str(e))
red = _add(m, 'TensorMathExpression', name='mean-strain', operation='reduce', operands_json=json.dumps([{'tensor': 'eps', 'how': 'mean'}]), dims_json='["l"]', matrix_equation_ref='')
check('reduce over a named dim', np.allclose(np.array(evaluate(m, red)['values']), eps.mean(axis=1)) and evaluate(m, red)['dims'] == ['k'])
perm = _add(m, 'TensorMathExpression', name='eps-T', operation='permute', operands_json=json.dumps([{'tensor': 'eps'}]), dims_json='["l","k"]', matrix_equation_ref='')
check('permute by named dims', np.allclose(np.array(evaluate(m, perm)['values']), eps.T))
sl = _add(m, 'TensorMathExpression', name='eps-row0', operation='slice', operands_json=json.dumps([{'tensor': 'eps', 'ranges': {'k': [0, 1]}}]), dims_json='[]', matrix_equation_ref='')
check('slice by named ranges', np.allclose(np.array(evaluate(m, sl)['values']), eps[0:1]))
dele = _add(m, 'TensorMathExpression', name='voigt', operation='expr', operands_json='[]', dims_json='[]', matrix_equation_ref='voigt-stress')
check('rank ≤ 2 matrix algebra DELEGATES to the matrix module (matrix_equation_ref) — never re-implemented here', evaluate(m, dele)['delegated'] == 'matrices')
tD = _add(m, 'Tensor', name='big', rank=3, shape_json='[500,500,500]', dimensions_json='[]', storage_kind='dataset', storage_ref='ds-1', semantics='')
try:
    values(m, tD); check('a dataset/engine/claim-backed tensor refuses in this slice, naming the owning module', False)
except TensorOpsError as e:
    check('a dataset/engine/claim-backed tensor refuses in this slice, naming the owning module', 'DigitizedDataset' in str(e))
tM = _add(m, 'Tensor', name='missing', rank=2, shape_json='[2,2]', dimensions_json='[]', storage_kind='matrix', storage_ref='nope', semantics='')
try:
    values(m, tM); check('a matrix-backed tensor whose MatrixDefinition is absent refuses by name', False)
except TensorOpsError as e:
    check('a matrix-backed tensor whose MatrixDefinition is absent refuses by name', "'nope'" in str(e))

# ---- the bridge rows (plan §F8)
ci = ComputeImplementation(name='sigma-numpy', operator='sigma-op', target_rung='microarchitecture', target_kind='in-order', mapping_status='implemented', evidence_level='measured', evidence_ref='bench-9')
check('ComputeImplementation carries the target rung + kind and the TWO statuses (plan §F2/§F8)', ci.target_rung == 'microarchitecture' and ci.evidence_level == 'measured' and ci.mapping_status == 'implemented')
dc = TensorDecomposition(name='cp-3', tensor='T-field', method='cp', rank=3, reconstruction_error=0.04)
check('TensorDecomposition keeps the information it lost (reconstruction_error, plan §F6.3)', dc.reconstruction_error == 0.04 and dc.error_method == 'frobenius-relative')

man = json.load(open('modules/tensormath/polari-app.json'))
from moduleService.manifests import validate
check('the manifest is valid, declares six classes + the API, and requires numpy', validate(man) == [] and len([c for c in man['classes'] if c != 'TensorMathAPI']) == 6 and man['requires']['libraries'] == ['numpy'])

n_ok = sum(1 for _, ok in _results if ok)
print(f'\n{n_ok}/{len(_results)} checks passed')
sys.exit(0 if n_ok == len(_results) else 1)
