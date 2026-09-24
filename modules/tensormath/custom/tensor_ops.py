"""
@module tensormath.custom.tensor_ops

NAMED-DIMENSION TENSOR OPERATIONS on numpy (plan §9), and where the VALUES come from (plan §B4):
`matrix` storage reads a rank-N MatrixDefinition's values_json (the small case); `engine` storage (tt-1) reads a
LIVE simulation state — two forms of storage_ref:
    matrixfield:<Class>:<row-name|*>:<field>   one row whose <field> is an N×k JSON matrix (WindFieldGridState.
                                               cells_json = [cx,cy,cz,wx,wy,wz] per cell); metadata_json
                                               {"grid_counts": [nx,ny,nz]} reshapes it to [nx,ny,nz,k];
                                               '*' = the newest row (highest step)
    simstate:<Class>:<run|*>:<f1,f2,…>          the rows of a sim-state class for one run, ordered by step →
                                               [steps, fields]  (WaxPrintSimState: per-step scalars)
    fem:<FEMModelDefinition.name>:<field>       tt-2: the plane-elasticity solve of one FEM case (materialsScience
                                               fem_engine, scikit-fem), field ∈ displacement [nodes,2] · nodes
                                               [nodes,2] · triangles [elem,3] · strain [elem,2,2] · stress
                                               [elem,2,2] · centroids [elem,2] · stiffness [2,2,2,2] (C_ijkl from
                                               the Lamé pair the engine used). E, ν come from the case's
                                               materials_json: {"material_option": <MagneticMaterialOption>} (its
                                               cited youngs_modulus_mpa / poisson_ratio, provenance kept) or an
                                               explicit {"E_pa", "nu", "provenance"}. Solved once per process.
`dataset` and `claim` are resolved by their owning modules in later slices and REFUSE here by name.

  values(manager, tensor)                       → np.ndarray, or raises TensorOpsError with the reason
  contract(a, dims_a, b, dims_b)                → einsum over the named dims (σ_ij = C_ijkl ε_kl is contract)
  reduce(a, dims, how), permute(a, order), slice_(a, ranges), outer(a, b)
  evaluate(manager, expression)                 → the expression's result + the einsum it used
Rank ≤ 2 matrix algebra belongs to the matrix module: an expression with matrix_equation_ref delegates.
"""
import json

import numpy as np


class TensorOpsError(Exception):
    pass


def _rows(manager, cls):
    return (getattr(manager, 'objectTables', {}) or {}).get(cls, {}).values()


def _find(manager, cls, name):
    for r in _rows(manager, cls):
        if str(getattr(r, 'name', '')) == name:
            return r
    return None


def _j(s, default):
    try:
        v = json.loads(s or '')
        return v if v is not None else default
    except Exception:
        return default


def dim_names(tensor):
    return [str(d.get('name', 'axis%d' % i)) for i, d in enumerate(_j(getattr(tensor, 'dimensions_json', '[]'), []))]


def values(manager, tensor):
    kind = str(getattr(tensor, 'storage_kind', 'matrix') or 'matrix'); ref = str(getattr(tensor, 'storage_ref', '') or '')
    if kind == 'matrix':
        m = _find(manager, 'MatrixDefinition', ref)
        if m is None:
            raise TensorOpsError('tensor %s: storage_kind=matrix but no MatrixDefinition %r' % (tensor.name, ref))
        arr = np.array(_j(getattr(m, 'values_json', '[]'), []), dtype=float)
        shape = _j(getattr(tensor, 'shape_json', '[]'), [])
        if shape and list(arr.shape) != [int(s) for s in shape]:
            try:
                arr = arr.reshape([int(s) for s in shape])
            except ValueError:
                raise TensorOpsError('tensor %s: MatrixDefinition %s holds shape %s, the tensor says %s' % (tensor.name, ref, list(arr.shape), shape))
        return arr
    if kind == 'engine':
        return engine_values(manager, tensor, ref)
    raise TensorOpsError('tensor %s: storage_kind %r is resolved by its owning module (dataset → pspp DigitizedDataset, '
                         'claim → PropertyClaim) — not in this slice' % (tensor.name, kind))


_FEM_CACHE = {}


def fem_case_solution(manager, case_name):
    """Solve (once per process) the FEMModelDefinition case and return the engine's tensorField + provenance."""
    case = _find(manager, 'FEMModelDefinition', case_name)
    if case is None:
        raise TensorOpsError('no FEMModelDefinition %r' % case_name)
    dom = _j(getattr(case, 'domain_json', '{}'), {}); mats = _j(getattr(case, 'materials_json', '[]'), [])
    bcs = _j(getattr(case, 'boundary_conditions_json', '{}'), {}); mesh = _j(getattr(case, 'mesh_json', '{}'), {})
    solver = _j(getattr(case, 'solver_json', '{}'), {})
    key = (case_name, json.dumps([dom, mats, bcs, mesh, solver], sort_keys=True))
    if key in _FEM_CACHE:
        return _FEM_CACHE[key]
    mat = mats[0] if mats else {}
    if mat.get('material_option'):
        opt = _find(manager, 'MagneticMaterialOption', str(mat['material_option']))
        if opt is None:
            raise TensorOpsError('case %s names material option %r but no MagneticMaterialOption row exists (magnetics absent?)' % (case_name, mat['material_option']))
        props = _j(getattr(opt, 'properties_json', '{}'), {})
        E = props.get('youngs_modulus_mpa', {}); nu = props.get('poisson_ratio', {})
        if not isinstance(E, dict) or not isinstance(nu, dict):
            raise TensorOpsError('material option %r carries no youngs_modulus_mpa / poisson_ratio' % mat['material_option'])
        E_pa, nu_v = float(E.get('value')) * 1e6, float(nu.get('value'))
        prov = '%s: E = %s MPa (%s), nu = %s (%s)' % (mat['material_option'], E.get('value'), E.get('provenance', '?'), nu.get('value'), nu.get('provenance', '?'))
    elif 'E_pa' in mat and 'nu' in mat:
        E_pa, nu_v, prov = float(mat['E_pa']), float(mat['nu']), str(mat.get('provenance', 'explicit, uncited'))
    else:
        raise TensorOpsError('case %s: materials_json needs {"material_option": …} or {"E_pa", "nu", "provenance"}' % case_name)
    from materialsScience.engines.fem_engine import solve_elasticity_2d
    r = solve_elasticity_2d(width=float(dom.get('width', 1.0)), height=float(dom.get('height', 1.0)), youngs_modulus=E_pa, poisson_ratio=nu_v,
                            tractions=tuple(bcs.get('tractions', [])), fixed_edges=tuple(bcs.get('fixed_edges', [])),
                            assumption=str(solver.get('assumption', 'plane-stress')), hole_radius=dom.get('hole_radius'), hole_center=dom.get('hole_center'),
                            refine=int(mesh.get('refine', 2)), include_field=True)
    if not r.get('ok'):
        raise TensorOpsError('FEM solve of %s failed: %s' % (case_name, r.get('error')))
    tf = r['tensorField']; lam, mu = tf['lame']['lambda'], tf['lame']['mu']
    C = np.zeros((2, 2, 2, 2))
    for i in range(2):
        for j in range(2):
            for k in range(2):
                for l in range(2):
                    C[i, j, k, l] = lam * (i == j) * (k == l) + mu * ((i == k) * (j == l) + (i == l) * (j == k))
    sol = {'fields': {'displacement': np.array(tf['displacement']), 'nodes': np.array(tf['nodes']), 'triangles': np.array(tf['triangles']),
                      'strain': np.array(tf['strain']), 'stress': np.array(tf['stress']), 'centroids': np.array(tf['centroids']), 'stiffness': C},
           'lame': tf['lame'], 'material_provenance': prov, 'validity': r.get('validity', ''), 'elements': int(np.array(tf['strain']).shape[0]),
           'degrees_of_freedom': r.get('degreesOfFreedom', 0), 'assumption': r.get('assumption', '')}
    _FEM_CACHE[key] = sol
    return sol


def engine_values(manager, tensor, ref):
    parts = ref.split(':')
    if len(parts) == 3 and parts[0] == 'fem':
        sol = fem_case_solution(manager, parts[1])
        if parts[2] not in sol['fields']:
            raise TensorOpsError('tensor %s: fem field %r is not one of %s' % (tensor.name, parts[2], ', '.join(sol['fields'])))
        return sol['fields'][parts[2]]
    if len(parts) != 4 or parts[0] not in ('matrixfield', 'simstate'):
        raise TensorOpsError('tensor %s: an engine storage_ref is matrixfield:<Class>:<row|*>:<field>, '
                             'simstate:<Class>:<run|*>:<f1,f2,…> or fem:<FEMModelDefinition>:<field> — got %r' % (tensor.name, ref))
    form, cls, which, fields = parts
    rows = list(_rows(manager, cls))
    if not rows:
        raise TensorOpsError('tensor %s: no %s rows exist on this instance yet — the field is read LIVE, never stored here '
                             '(run the simulation, or seed a step)' % (tensor.name, cls))
    meta = _j(getattr(tensor, 'metadata_json', '{}'), {})
    if form == 'matrixfield':
        row = (max(rows, key=lambda r: int(getattr(r, 'step', 0) or 0)) if which == '*'
               else next((r for r in rows if str(getattr(r, 'name', '')) == which), None))
        if row is None:
            raise TensorOpsError('tensor %s: no %s row named %r' % (tensor.name, cls, which))
        arr = np.array(_j(getattr(row, fields, '[]'), []), dtype=float)
        if arr.ndim != 2:
            raise TensorOpsError('tensor %s: %s.%s is not an N×k matrix' % (tensor.name, cls, fields))
        counts = meta.get('grid_counts')
        if counts:
            try:
                arr = arr.reshape([int(c) for c in counts] + [arr.shape[1]])
            except ValueError:
                raise TensorOpsError('tensor %s: %d cells do not fill grid_counts %s' % (tensor.name, arr.shape[0], counts))
        return arr
    run_rows = [r for r in rows if which == '*' or str(getattr(r, 'simulation_run_ref', '')) == which]
    if which == '*' and run_rows:   # the newest run only
        newest = max(run_rows, key=lambda r: (str(getattr(r, 'simulation_run_ref', '')), int(getattr(r, 'step', 0) or 0)))
        run_rows = [r for r in run_rows if str(getattr(r, 'simulation_run_ref', '')) == str(getattr(newest, 'simulation_run_ref', ''))]
    if not run_rows:
        raise TensorOpsError('tensor %s: no %s rows for run %r' % (tensor.name, cls, which))
    run_rows.sort(key=lambda r: int(getattr(r, 'step', 0) or 0))
    names = [f for f in fields.split(',') if f]
    return np.array([[float(getattr(r, f, 0.0) or 0.0) for f in names] for r in run_rows], dtype=float)


_LETTERS = 'abcdefghijklmnopqrstuvwxyz'


def _spec(names_a, names_b, contracted):
    """einsum subscripts for a contraction over the named dims shared by both operands."""
    letters = {}
    for n in list(names_a) + list(names_b):
        letters.setdefault(n, _LETTERS[len(letters)])
    sa = ''.join(letters[n] for n in names_a); sb = ''.join(letters[n] for n in names_b)
    out = [n for n in list(names_a) + [x for x in names_b if x not in names_a] if n not in contracted]
    return '%s,%s->%s' % (sa, sb, ''.join(letters[n] for n in out)), out


def contract(a, names_a, b, names_b, dims):
    for d in dims:
        if d not in names_a or d not in names_b:
            raise TensorOpsError('contract: dim %r must be on BOTH operands (a: %s, b: %s)' % (d, names_a, names_b))
    spec, out = _spec(names_a, names_b, set(dims))
    return np.einsum(spec, a, b), out, spec


def outer(a, names_a, b, names_b):
    spec, out = _spec(names_a, names_b, set())
    return np.einsum(spec, a, b), out, spec


def reduce_(a, names, dims, how='sum'):
    axes = tuple(names.index(d) for d in dims)
    f = {'sum': np.sum, 'mean': np.mean, 'max': np.max, 'min': np.min}.get(how)
    if f is None:
        raise TensorOpsError('reduce: how=%r is not sum|mean|max|min' % how)
    return f(a, axis=axes), [n for n in names if n not in dims]


def norm(a, names, dim, ranges=None):
    """L2 norm over ONE named dim (optionally over a [lo,hi) slice of it first): |w| from the component axis."""
    ax = names.index(dim)
    if ranges and dim in ranges:
        lo, hi = [int(x) for x in ranges[dim]]
        a = np.take(a, range(lo, hi), axis=ax)
    return np.sqrt(np.sum(a * a, axis=ax)), [n for n in names if n != dim]


def permute(a, names, order):
    return np.transpose(a, [names.index(d) for d in order]), list(order)


def slice_(a, names, ranges):
    idx = tuple(slice(*[int(x) for x in ranges[n]]) if n in ranges else slice(None) for n in names)
    return a[idx], names


def evaluate(manager, expression):
    """Evaluate a TensorMathExpression over its tensors. Returns {values, dims, shape, einsum, delegated, elapsed_s}
    — elapsed_s is the numpy path's wall clock for THIS call (a reading, not a stored benchmark: lad-5 stores those)."""
    import time
    t0 = time.perf_counter()
    out = _evaluate(manager, expression)
    out['elapsed_s'] = round(time.perf_counter() - t0, 6)
    return out


def _evaluate(manager, expression):
    if str(getattr(expression, 'matrix_equation_ref', '') or ''):
        return {'delegated': 'matrices', 'matrix_equation_ref': expression.matrix_equation_ref,
                'note': 'rank ≤ 2: evaluate with POST /api/matrix-equations/evaluate (the matrix module owns it)'}
    op = str(getattr(expression, 'operation', '') or ''); ops = _j(getattr(expression, 'operands_json', '[]'), [])
    dims = [str(d) for d in _j(getattr(expression, 'dims_json', '[]'), [])]
    ts = []
    for o in ops:
        t = _find(manager, 'Tensor', str(o.get('tensor', '')))
        if t is None:
            raise TensorOpsError('operand tensor %r not found' % o.get('tensor'))
        ts.append((t, values(manager, t), dim_names(t)))
    if op in ('contract', 'outer'):
        if len(ts) != 2:
            raise TensorOpsError('%s needs exactly two operands' % op)
        (ta, a, na), (tb, b, nb) = ts
        r, out, spec = contract(a, na, b, nb, dims) if op == 'contract' else outer(a, na, b, nb)
        return {'values': r.tolist(), 'dims': out, 'shape': list(r.shape), 'einsum': spec, 'delegated': ''}
    if len(ts) != 1:
        raise TensorOpsError('%s needs exactly one operand' % op)
    t, a, names = ts[0]
    if op == 'reduce':
        r, out = reduce_(a, names, dims, str(ops[0].get('how', 'sum')))
    elif op == 'norm':
        r, out = norm(a, names, dims[0], ops[0].get('ranges'))
    elif op == 'permute':
        r, out = permute(a, names, dims)
    elif op == 'slice':
        r, out = slice_(a, names, ops[0].get('ranges', {}))
    else:
        raise TensorOpsError('operation %r is not implemented in this slice (contract|outer|reduce|norm|permute|slice)' % op)
    return {'values': np.asarray(r).tolist(), 'dims': out, 'shape': list(np.asarray(r).shape), 'einsum': '', 'delegated': ''}
