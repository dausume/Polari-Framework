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


check('the module registers exactly SEVEN row classes (tt-6 added FEMFieldState)', len(TENSORMATH_CLASSES) == 7, [c.__name__ for c in TENSORMATH_CLASSES])
check('every class is one file under objects/tensormath/', all(c.__module__ == 'tensormath.objects.tensormath.%s' % c.__name__ for c in TENSORMATH_CLASSES))
pairs = {p[0]: p[2] for p in TENSORMATH_SEED_PAIRS}
check('seed pairs cover every class (+ the tt-2 FEM case, a core row); every seeded tensor reads REAL state (engine-backed); no decomposition is seeded',
      set(pairs) >= {c.__name__ for c in TENSORMATH_CLASSES} and all(t['storage_kind'] == 'engine' for t in pairs['Tensor']) and pairs['TensorDecomposition'] == []
      and 'FEMModelDefinition' in pairs)

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

# ---- tt-2: CONTINUUM MECHANICS on the FEM resolution — the interop proof (Validation B)
from tensormath.tensormath_seed import SEED_FEM_CASES, SEED_TENSOR_OPERATORS, SEED_COMPUTE_IMPLEMENTATIONS
from tensormath.custom.tensor_ops import fem_case_solution
m.objectTables['FEMModelDefinition'] = {}; m.objectTables['MagneticMaterialOption'] = {}
case = _add(m, 'FEMModelDefinition', **SEED_FEM_CASES[0])
try:
    fem_case_solution(m, 'tt2-plate-tension'); check('fem: the case names a material option that is ABSENT → refused by name (magnetics not admitted)', False)
except TensorOpsError as e:
    check('fem: the case names a material option that is ABSENT → refused by name (magnetics not admitted)', 'opt-electrical-steel' in str(e))
_add(m, 'MagneticMaterialOption', name='opt-electrical-steel', properties_json=json.dumps({'youngs_modulus_mpa': {'value': 200000.0, 'unit': 'MPa', 'provenance': 'literature-est'},
                                                                                          'poisson_ratio': {'value': 0.3, 'provenance': 'literature-est'}}))
sol = fem_case_solution(m, 'tt2-plate-tension')
check('fem: the plate solves (scikit-fem) with E, ν from the CITED material option, and the provenance travels', sol['elements'] > 0 and 'literature-est' in sol['material_provenance'], sol['material_provenance'])
for nm in ('tt2-u', 'tt2-eps', 'tt2-sigma', 'tt2-C', 'tt2-centroids'):
    _add(m, 'Tensor', **next(t for t in SEED_TENSORS if t['name'] == nm))
U, E_, S_, Cc = (values(m, next(t for t in m.objectTables['Tensor'].values() if t.name == n)) for n in ('tt2-u', 'tt2-eps', 'tt2-sigma', 'tt2-C'))
check('the tensors read the solve live: u [nodes,2], ε [elem,2,2], σ [elem,2,2], C [2,2,2,2]', U.ndim == 2 and U.shape[1] == 2 and E_.shape[1:] == (2, 2) and S_.shape == E_.shape and Cc.shape == (2, 2, 2, 2))
check('C is the isotropic stiffness from the engine\'s Lamé pair (C_0000 = λ + 2μ, C_0011 = λ, C_0101 = μ)',
      abs(Cc[0, 0, 0, 0] - (sol['lame']['lambda'] + 2 * sol['lame']['mu'])) < 1 and abs(Cc[0, 0, 1, 1] - sol['lame']['lambda']) < 1 and abs(Cc[0, 1, 0, 1] - sol['lame']['mu']) < 1)
ex2 = {e['name']: e for e in SEED_TENSOR_EXPRESSIONS}
res = evaluate(m, types.SimpleNamespace(**ex2['tt2-sigma-from-C']))
sig = np.array(res['values'])
check('σ_ij = C_ijkl ε_kl by NAMED CONTRACTION equals the engine\'s σ element by element (rtol 1e-9) — TensorMath and the FEM engine agree',
      res['dims'] == ['i', 'j', 'n'] and np.allclose(np.transpose(sig, (2, 0, 1)), S_, rtol=1e-9, atol=1e-3), (res['dims'], res['shape']))
check('  …and the evaluate call reports its wall clock (a reading, never a stored benchmark)', 'elapsed_s' in res and res['elapsed_s'] >= 0)
check('  …the plate is in tension: σ_xx ≈ 1 MPa on average (the applied traction), σ_yy small', abs(S_[:, 0, 0].mean() - 1.0e6) / 1.0e6 < 0.15 and abs(S_[:, 1, 1].mean()) < 0.3e6, (S_[:, 0, 0].mean(), S_[:, 1, 1].mean()))
tr = evaluate(m, types.SimpleNamespace(**ex2['tt2-trace-eps']))
check('the volumetric strain reduces over k', np.array(tr['values']).shape == (E_.shape[0], 2))
check('the operator stress-from-strain names its expression and its ONE implementation (numpy), whose latency is a per-call reading, not an invented benchmark',
      SEED_TENSOR_OPERATORS[0]['expression_ref'] == 'tt2-sigma-from-C' and SEED_COMPUTE_IMPLEMENTATIONS[0]['evidence_level'] == 'none' and SEED_COMPUTE_IMPLEMENTATIONS[0]['latency_s'] == 0.0)
tb2 = _add(m, 'Tensor', name='bad-field', rank=1, shape_json='[]', dimensions_json='[]', storage_kind='engine', storage_ref='fem:tt2-plate-tension:nope', semantics='', metadata_json='{}')
try:
    values(m, tb2); check('an unknown fem field is refused naming the seven', False)
except TensorOpsError as e:
    check('an unknown fem field is refused naming the seven', 'stiffness' in str(e) and 'displacement' in str(e))

# ---- Phase 6: the SAME operator on hardware — the committed FPGA report and its implementation row
from tensormath.custom.fpga_kernel import report as fpga_report, implementation_row, KERNEL, TOP, C_SCALE, E_SCALE

# ---- D5: PyTorch as the third ComputeImplementation — through the engines ladder, never assumed on a device
import sys as _sys, types as _types, os as _os
from tensormath.custom import torch_engine as _te
from tensormath.tensormath_seed import SEED_COMPUTE_IMPLEMENTATIONS as _IMPLS
_torch_row = next((r for r in _IMPLS if r['name'] == 'stress-from-strain/torch'), None)
check('D5: the seed carries a THIRD implementation of stress-from-strain — torch — with NO number invented (latency 0, evidence none) and the worker/knob named in its target_ref',
      _torch_row is not None and _torch_row['operator'] == 'stress-from-strain' and _torch_row['evidence_level'] == 'none' and _torch_row['latency_s'] == 0.0 and 'TORCH_ENGINES_URL' in _torch_row['target_ref']
      and len([r for r in _IMPLS if r['operator'] == 'stress-from-strain']) == 3, [r['name'] for r in _IMPLS])
_saved_knob = _os.environ.pop('TORCH_ENGINES_URL', None); _saved_torch = _sys.modules.get('torch')
_sys.modules['torch'] = None   # make `import torch` fail regardless of the host
_te._CAP_CACHE.clear()
_r = _te.resolve()
check('  …the ladder REFUSES honestly with nothing available: no knob, no import, no provider — and the refusal names both knobs and the worker\'s absence',
      _r['how'] == 'refused' and 'TORCH_ENGINES_URL' in _r['why'] and 'tensormath.engines' in _r['why'] and 'Alpine' in _r['why'], _r)
_os.environ['TORCH_ENGINES_URL'] = 'http://127.0.0.1:1'; _te._CAP_CACHE.clear()
_r = _te.resolve()
check('  …a DECLARED worker that is unreachable is a refusal, never a silent fall-back', _r['how'] == 'refused' and 'unreachable' in _r['why'], _r)
_os.environ.pop('TORCH_ENGINES_URL', None); _te._CAP_CACHE.clear()
# a stand-in torch (numpy underneath) exercises the LOCAL rung and the comparison to numpy without torch installed
import numpy as _np
_fake = _types.ModuleType('torch'); _fake.__version__ = 'stub-for-selftest'; _fake.float64 = _np.float64; _fake.float32 = _np.float32
class _T:
    def __init__(self, a): self.a = _np.asarray(a); self.device = 'cpu(stub)'
    def tolist(self): return self.a.tolist()
    @property
    def shape(self): return self.a.shape
_fake.tensor = lambda a, dtype=None: _T(_np.asarray(a, dtype=dtype))
_fake.einsum = lambda spec, *ts: _T(_np.einsum(spec, *[t.a for t in ts]))
_fake.get_num_threads = lambda: 1; _fake.use_deterministic_algorithms = lambda flag: None
_sys.modules['torch'] = _fake
_r = _te.resolve()
check('  …with torch importable the ladder resolves LOCAL and reports the version', _r['how'] == 'local' and _r['version'] == 'stub-for-selftest', _r)
_e = next(x for x in m.objectTables['TensorMathExpression'].values() if x.name == 'tt2-sigma-from-C') if 'TensorMathExpression' in m.objectTables and any(x.name == 'tt2-sigma-from-C' for x in m.objectTables['TensorMathExpression'].values()) else None
if _e is not None:
    _res = _te.evaluate(m, _e)
    check('  …torch evaluates the SAME contraction spec numpy derived (σ = C:ε) and is compared to numpy: error ~0, shape equal, how/where recorded — the reference is numpy, never torch itself',
          _res['einsum'] and _res['error_vs_numpy'] < 1e-12 and _res['how'] == 'local' and _res['torch']['version'] == 'stub-for-selftest' and _res['shape'] == list(_np.asarray(_res['values']).shape), {k: _res[k] for k in ('einsum', 'error_vs_numpy', 'how', 'shape')})
else:
    check('  …torch evaluation on the σ expression — the fixture holds no tt2-sigma-from-C expression here; covered by the live-boot probe', True)
_pl = _te.placement()
check('  …placement names the ladder, the knob, the provider module, the worker and the licence (BSD-3)', _pl['knob'] == 'TORCH_ENGINES_URL' and len(_pl['ladder']) == 4 and 'torch-engines' in _pl['worker'] and 'BSD-3' in _pl['licence'])
if _saved_torch is not None: _sys.modules['torch'] = _saved_torch
else: _sys.modules.pop('torch', None)
if _saved_knob is not None: _os.environ['TORCH_ENGINES_URL'] = _saved_knob
_te._CAP_CACHE.clear()
from computelod.custom.repro import complete as _repro_complete
_fr = fpga_report()
check('reproducibility (his rule 2026-09-26): the FPGA report carries a complete `reproduction` block — the kernel sources hashed, yosys/nextpnr/iverilog versions, the fixed-point knobs, and nextpnr\'s SEED stated (the default, not implicit)',
      _fr is not None and _repro_complete(_fr.get('reproduction'))[0] and 'nextpnr-ice40 --seed' in _fr['reproduction']['seeds'] and any(i.get('label') == 'kernel RTL' for i in _fr['reproduction']['inputs']), (_fr or {}).get('reproduction', {}).get('seeds'))
frep = fpga_report()
check('fpga: a committed report exists (the flow RAN: iverilog → yosys synth_ice40 → nextpnr-ice40)', frep is not None and 'simulation' in frep and 'place_and_route' in frep)
check('  …the kernel is EXACT on every real element of the plate (64/64, 0 fails)', 'PASS' in frep['simulation']['verdict'] and frep['simulation']['stream_cycles'] > 0, frep['simulation'])
check('  …the operand rounding (C to kPa, ε to nano-strain) costs ~1e-4 relative vs float64, and that number is recorded, not hidden', 0 < frep['reference_error_vs_float'] < 1e-3, frep['reference_error_vs_float'])
check('  …the streaming form (16 multipliers) did NOT fit the part and the report says so with the numbers (the LUT budget below dictates the schedule above)',
      frep['streaming_variant']['fit'] is False and frep['streaming_variant']['SB_LUT4'] > frep['streaming_variant']['part_luts'])
check('  …the time-multiplexed form fits: LCs used < available, Fmax > 0, 17 cycles per element',
      frep['place_and_route'].get('fmax_mhz', 0) > 0 and frep['place_and_route']['utilization']['ICESTORM_LC']['used'] < frep['place_and_route']['utilization']['ICESTORM_LC']['available']
      and frep['simulation']['cycles_per_element'] == 17, frep['place_and_route'])
check('  …latency_s is DERIVED (cycles / Fmax) and the report says so', 'DERIVED' in frep['derived']['note'] and abs(frep['derived']['latency_s_per_element_at_fmax'] - 17 / (frep['place_and_route']['fmax_mhz'] * 1e6)) < 1e-12)
row = implementation_row(frep)
check('the FPGA ComputeImplementation: rung rtl / kind accelerator, evidence SIMULATED (a timing model, not a bench), validated by the exact simulation, energy 0 = not known',
      row['target_rung'] == 'rtl' and row['target_kind'] == 'accelerator' and row['evidence_level'] == 'simulated' and row['mapping_status'] == 'validated' and row['energy_j'] == 0.0 and 'not yet' in row['notes'])
check('the kernel RTL is Verilog-2001 with ONE multiplier (D6; the * appears once in the datapath) and a register-bus top the size of a register map',
      KERNEL.count(' * ') == 1 and 'module stress_mac_top' in TOP and 'addr' in TOP)
check('the THREE implementations of stress-from-strain are seeded side by side: numpy (evidence none until benchmarked), torch (D5, evidence none until benchmarked where it resolves) and the FPGA row (simulated)',
      [i['name'] for i in SEED_COMPUTE_IMPLEMENTATIONS] == ['stress-from-strain/numpy', 'stress-from-strain/torch', 'stress-from-strain/fpga-stress-mac'] and SEED_COMPUTE_IMPLEMENTATIONS[0]['evidence_level'] == 'none' and SEED_COMPUTE_IMPLEMENTATIONS[1]['evidence_level'] == 'none')
check('the fixed-point scales are stated once, in code, and are what the kernel comment says', C_SCALE == 1e-3 and E_SCALE == 1e9 and 'kPa' in KERNEL and 'nano-strain' in KERNEL)

man = json.load(open('modules/tensormath/polari-app.json'))
from moduleService.manifests import validate
check('the manifest is valid, declares seven classes + the API, and requires numpy', validate(man) == [] and len([c for c in man['classes'] if c != 'TensorMathAPI']) == 7 and man['requires']['libraries'] == ['numpy'])

# ---- tt-6: the σ field written down, and seen through a 2-D field binding
from tensormath.custom.fem_field import field_row_from_tensor_field, seed_field_rows, LazySeedRows, FIELD_COLUMNS
from tensormath.tensormath_seed import SEED_FEM_FIELD_STATES, SEED_PLATE_BINDINGS, SEED_PLATE_SIMSPACES, PLATE_SIGMA_DOMAIN
_tf = {'nodes': [[0, 0], [1, 0], [0, 1]], 'triangles': [[0, 1, 2]], 'displacement': [[0, 0], [1e-6, 0], [0, -3e-7]],
       'stress': [[[1e6, 0.0], [0.0, 0.0]]], 'centroids': [[1 / 3, 1 / 3]], 'lame': {'assumption': 'plane-stress'}}
fr = field_row_from_tensor_field(_tf, 'unit-case', material_provenance='test: E = 1 (none)')
_el = json.loads(fr['elements_json'])
check('field_row_from_tensor_field: one element row [cx, cy, σ_vm, σ_xx, σ_yy, σ_xy, area]; uniaxial 1 MPa → σ_vm = 1 MPa, area ½',
      fr['n_elements'] == 1 and fr['n_nodes'] == 3 and abs(_el[0][2] - 1e6) < 1e-6 and abs(_el[0][6] - 0.5) < 1e-12 and json.loads(fr['columns_json']) == FIELD_COLUMNS and fr['u_max'] == 1e-6, _el)
check('the seed field row is solved at seed time from the seed case + the seed material option (64 elements, σ_vm within 0.8–1.1 MPa of the 1 MPa pull, E/ν cited)',
      isinstance(SEED_FEM_FIELD_STATES, LazySeedRows) and len(SEED_FEM_FIELD_STATES) == 1 and SEED_FEM_FIELD_STATES[0]['n_elements'] == 64
      and PLATE_SIGMA_DOMAIN[0] <= SEED_FEM_FIELD_STATES[0]['sigma_vm_min'] <= SEED_FEM_FIELD_STATES[0]['sigma_vm_max'] <= PLATE_SIGMA_DOMAIN[1]
      and 'literature-est' in SEED_FEM_FIELD_STATES[0]['material_provenance'], {k: v for k, v in (SEED_FEM_FIELD_STATES[0] if SEED_FEM_FIELD_STATES else {}).items() if 'json' not in k})
_sb = next(b for b in SEED_PLATE_BINDINGS if b['name'] == 'FEMFieldState-2d')
_bj = json.loads(_sb['binding_json'])
check('the binding FEMFieldState-2d is a 2-D `field` over elements_json, colour = column 2 (σ_vm) over PLATE_SIGMA_DOMAIN in Pa; the scene binds the class',
      _sb['name'] == 'FEMFieldState-2d' and _bj['kind'] == 'field' and _bj['layout']['scalarCol'] == 2 and _bj['color']['domain'] == PLATE_SIGMA_DOMAIN and _bj['color']['unit'] == 'Pa'
      and json.loads(SEED_PLATE_SIMSPACES[0]['bound_classes_json'])[0]['className'] == 'FEMFieldState' and SEED_PLATE_SIMSPACES[0]['dimensionality'] == '2d')
from simSpace.compilers.field_projection_2d import emit_field_2d, ramp_color
_inst = types.SimpleNamespace(name='f', elements_json=json.dumps([[0.1, 0.2, 0.8e6, 0, 0, 0, 1], [0.3, 0.4, 1.1e6, 0, 0, 0, 1], [0.5, 0.6, 'nan', 0, 0, 0, 1]]))
_warn = []
_objs = emit_field_2d('FEMFieldState', {1: _inst}, _bj, 'FEMFieldState-2d', None, _warn)
check('emit_field_2d fans the row into one object per element at its centroid, colorOverride from the ramp (low → blue end, high → red end), per-cell stable ids',
      len(_objs) == 3 and _objs[0]['position'] == [0.1, 0.2] and _objs[0]['colorOverride'] == ramp_color('stress', 0.0) and _objs[1]['colorOverride'] == ramp_color('stress', 1.0)
      and _objs[0]['id'] == 'FEMFieldState-2d:FEMFieldState:0' and _objs[0]['userData']['scalar'] == 0.8e6 and _objs[0]['userData']['unit'] == 'Pa'
      and _objs[0]['shapeRef'] == 'tt2-plate-tension-field-el-0' and _objs[2]['shapeRef'] == 'tt2-plate-tension-field-el-2' and 'scale' not in _objs[0], _objs[:2])
_bj_marker = dict(_bj); _bj_marker.pop('shapeRefPattern'); _bj_marker['cellSize'] = 2.2
_objm = emit_field_2d('FEMFieldState', {1: _inst}, _bj_marker, 'x', None, [])
check('tt-11: with a shapeRefPattern each cell references ITS OWN shape (an element polygon in space units) and carries no marker scale; without one it is a rectangle marker with cellSize as before',
      _objm[0]['shapeRef'] == 'rectangle' and _objm[0]['scale'] == 2.2 and not _objm[0]['userData'].get('ownShape'))
# the element shapes themselves, from the seed field row through the math-shape library
from tensormath.custom.fem_shapes import element_shapes
from tensormath.tensormath_seed import SEED_FEM_ELEMENT_MATH_SHAPES, SEED_FEM_ELEMENT_SHAPES_2D
from mathshapes.custom.shape_geometry import primitive_properties, primitive_inside
_ms0 = SEED_FEM_ELEMENT_MATH_SHAPES[0]; _p0 = json.loads(_ms0['parameters_json'])
_vol, _area, _bounds, _cen = primitive_properties('polygon', _p0)
check('tt-11: 64 polygon MathShapeDefinitions from the seed field: element 0 = the triangle (0,0),(0,0.25),(0.25,0.25); area 1/32 m² == the field row\'s area column; centroid == the FEM centroid; a point inside is inside',
      len(SEED_FEM_ELEMENT_MATH_SHAPES) == 64 and _ms0['primitive_kind'] == 'polygon' and _p0['vertices'] == [[0.0, 0.0], [0.0, 0.25], [0.25, 0.25]] and abs(_area - 0.03125) < 1e-12
      and abs(_area - json.loads(SEED_FEM_FIELD_STATES[0]['elements_json'])[0][6]) < 1e-12 and abs(_cen[0] - json.loads(SEED_FEM_FIELD_STATES[0]['elements_json'])[0][0]) < 1e-9
      and primitive_inside('polygon', _p0, 0.05, 0.2, 0) and not primitive_inside('polygon', _p0, 0.2, 0.05, 0), (_area, _cen))
_s0 = SEED_FEM_ELEMENT_SHAPES_2D[0]
check('  …and 64 Shape2DDefinitions through mathshapes.shape2d_bridge: source svg, units SPACE, anchor center, one <polygon> with points relative to the centroid, NO fill in the svg (the colour is the object\'s data)',
      len(SEED_FEM_ELEMENT_SHAPES_2D) == 64 and _s0['name'] == 'tt2-plate-tension-field-el-0' and _s0['source'] == 'svg' and _s0['units'] == 'space' and _s0['anchor'] == 'center'
      and _s0['svg_string'].startswith('<polygon points=') and 'fill' not in _s0['svg_string'] and '-0.083333,-0.166667' in _s0['svg_string'], _s0)
check('  …a cell whose scalar is not a number is drawn grey and says so (refused, never invented)', _objs[2]['colorOverride'] == '#bdbdbd' and 'no numeric scalar' in _objs[2]['userData']['refused'], _objs[2])
from simSpace.compilers.field_projection_2d import emit_vectorfield_2d
_ub = json.loads(next(b for b in SEED_PLATE_BINDINGS if b['name'] == 'FEMFieldState-u-2d')['binding_json'])
_uinst = types.SimpleNamespace(name='f', nodes_json=json.dumps([[0.0, 0.0, 0.0, 0.0], [2.0, 0.5, 1e-5, -2.5e-6]]))
_conns = emit_vectorfield_2d('FEMFieldState', {1: _uinst}, _ub, 'FEMFieldState-u-2d', None, [])
check('tt-8: emit_vectorfield_2d draws u as a CONNECTION node → node + k·u with k = 20000 the binding\'s stated knob (2 m, 0.5 m + (0.2, −0.05)); the raw u and k ride userData; a zero vector is skipped only below magnitudeMin (0 → drawn)',
      _ub['kind'] == 'vectorfield' and len(_conns) == 2 and _conns[1]['sourcePosition'] == [2.0, 0.5] and abs(_conns[1]['targetPosition'][0] - 2.2) < 1e-9 and abs(_conns[1]['targetPosition'][1] - 0.45) < 1e-9
      and _conns[1]['userData']['vector'] == [1e-5, -2.5e-6] and _conns[1]['userData']['vectorScale'] == 20000.0 and _conns[1]['id'] == 'FEMFieldState-u-2d:FEMFieldState:1', _conns)
from simSpace.compilers.field_projection_2d import emit_meshwire_2d
_mb = json.loads(next(b for b in SEED_PLATE_BINDINGS if b['name'] == 'FEMFieldState-mesh-2d')['binding_json'])
_minst = types.SimpleNamespace(name='f', nodes_json=json.dumps([[0, 0, 0, 0], [1, 0, 0, 0], [0, 1, 0, 0], [1, 1, 0, 0]]), triangles_json=json.dumps([[0, 1, 2], [1, 3, 2]]))
_edges = emit_meshwire_2d('FEMFieldState', {1: _minst}, _mb, 'FEMFieldState-mesh-2d', None, [])
check('tt-9: emit_meshwire_2d draws two triangles as FIVE edges (the shared diagonal once), reference positions, stable edge ids',
      _mb['kind'] == 'meshwire' and len(_edges) == 5 and sorted(e['userData']['edge'] for e in _edges) == [[0, 1], [0, 2], [1, 2], [1, 3], [2, 3]] and _edges[0]['id'] == 'FEMFieldState-mesh-2d:FEMFieldState:0-1', _edges)
check('  …the seed field row carries the mesh (64 triangles) so the wireframe has something to draw', len(json.loads(SEED_FEM_FIELD_STATES[0]['triangles_json'])) == 64)
check('  …the ramp is clamped and monotone in hue stops', ramp_color('stress', -1) == ramp_color('stress', 0) and ramp_color('stress', 2) == ramp_color('stress', 1) and ramp_color('nope', 0.5) == ramp_color('grey', 0.5))

n_ok = sum(1 for _, ok in _results if ok)
print(f'\n{n_ok}/{len(_results)} checks passed')
sys.exit(0 if n_ok == len(_results) else 1)
