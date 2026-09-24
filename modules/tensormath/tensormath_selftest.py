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
check('seed pairs cover every class; the only seeded rows are tensors over REAL state (engine-backed) and their expressions', [p[0] for p in TENSORMATH_SEED_PAIRS] == [c.__name__ for c in TENSORMATH_CLASSES] and all(t['storage_kind'] == 'engine' for t in TENSORMATH_SEED_PAIRS[0][2]) and TENSORMATH_SEED_PAIRS[3][2] == [])

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

# ---- tt-1: ENGINE storage — a live grid field and a sim-state time series, read where they are
from simulations.wind_field_grid_sim_state import build_initial_cells, WIND_GRID_COUNTS
from tensormath.tensormath_seed import SEED_TENSORS, SEED_TENSOR_EXPRESSIONS
m.objectTables['WindFieldGridState'] = {}; m.objectTables['WaxPrintSimState'] = {}
tw = _add(m, 'Tensor', **SEED_TENSORS[0])
try:
    values(m, tw); check('engine: with NO grid row yet the tensor refuses honestly (values are read live, never stored)', False)
except TensorOpsError as e:
    check('engine: with NO grid row yet the tensor refuses honestly (values are read live, never stored)', 'no WindFieldGridState rows' in str(e))
cells = build_initial_cells()
_add(m, 'WindFieldGridState', name='r1-wind-field-grid-0', simulation_run_ref='r1', step=0, time=0.0, cells_json=json.dumps(cells))
cells2 = [c[:3] + [c[3] * 2, c[4] * 2, c[5] * 2] for c in cells]
_add(m, 'WindFieldGridState', name='r1-wind-field-grid-1', simulation_run_ref='r1', step=1, time=0.1, cells_json=json.dumps(cells2))
W = values(m, tw)
check('engine matrixfield: the newest WindFieldGridState row (highest step) is read and reshaped to [4,4,4,6]', W.shape == (4, 4, 4, 6) and np.allclose(W.reshape(-1, 6), np.array(cells2)))
check('  …the cell centres survive the reshape in grid order (x fastest-varying last: [ix,iy,iz])', np.allclose(W[3, 0, 0, 0], 1.2) and np.allclose(W[0, 3, 0, 1], 0.2))
ex = {e['name']: e for e in SEED_TENSOR_EXPRESSIONS}
sp = evaluate(m, types.SimpleNamespace(**ex['wind-speed']))
check('wind-speed = the L2 norm over the velocity columns: shape [4,4,4], values ≥ 0, equal to the per-cell |w|',
      sp['shape'] == [4, 4, 4] and np.allclose(np.array(sp['values']).reshape(-1), np.linalg.norm(np.array(cells2)[:, 3:6], axis=1)) and sp['dims'] == ['x', 'y', 'z'])
sl = evaluate(m, types.SimpleNamespace(**ex['wind-slice-z0']))
check('wind-slice-z0 keeps one z layer', sl['shape'] == [4, 4, 1, 6])
mn = evaluate(m, types.SimpleNamespace(**ex['wind-mean-over-y']))
check('wind-mean-over-y reduces the y axis', mn['shape'] == [4, 4, 6] and mn['dims'] == ['x', 'z', 'component'])
ts = _add(m, 'Tensor', **SEED_TENSORS[1])
for i, (t_, mf, h) in enumerate(((60.0, 1.0, 0.0), (58.5, 0.9, 0.4), (57.0, 0.7, 0.8))):
    _add(m, 'WaxPrintSimState', name='wp-%d' % i, simulation_run_ref='wp', step=i, exit_temp_c=t_, melt_fraction=mf, height_mm=h, warp_index=0.01 * i)
S = values(m, ts)
check('engine simstate: the wax print series is [steps, 4 quantities] in step order, read live', S.shape == (3, 4) and np.allclose(S[:, 0], [60.0, 58.5, 57.0]) and np.allclose(S[2, 2], 0.8))
tb = _add(m, 'Tensor', name='bad-ref', rank=1, shape_json='[]', dimensions_json='[]', storage_kind='engine', storage_ref='nonsense', semantics='', metadata_json='{}')
try:
    values(m, tb); check('a malformed engine ref is refused with the two accepted forms named', False)
except TensorOpsError as e:
    check('a malformed engine ref is refused with the two accepted forms named', 'matrixfield:' in str(e) and 'simstate:' in str(e))

man = json.load(open('modules/tensormath/polari-app.json'))
from moduleService.manifests import validate
check('the manifest is valid, declares six classes + the API, and requires numpy', validate(man) == [] and len([c for c in man['classes'] if c != 'TensorMathAPI']) == 6 and man['requires']['libraries'] == ['numpy'])

n_ok = sum(1 for _, ok in _results if ok)
print(f'\n{n_ok}/{len(_results)} checks passed')
sys.exit(0 if n_ok == len(_results) else 1)
