"""
@module tensormath.custom.tensor_ops

NAMED-DIMENSION TENSOR OPERATIONS on numpy (plan §9), and where the VALUES come from (plan §B4):
`matrix` storage reads a rank-N MatrixDefinition's values_json (the small case); the other storage kinds
(dataset, engine, claim) are resolved by their owning modules in later slices and REFUSE here by name.

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
    raise TensorOpsError('tensor %s: storage_kind %r is resolved by its owning module (dataset → pspp DigitizedDataset, '
                         'engine → the FEM/meso engines, claim → PropertyClaim) — not in this slice' % (tensor.name, kind))


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


def permute(a, names, order):
    return np.transpose(a, [names.index(d) for d in order]), list(order)


def slice_(a, names, ranges):
    idx = tuple(slice(*[int(x) for x in ranges[n]]) if n in ranges else slice(None) for n in names)
    return a[idx], names


def evaluate(manager, expression):
    """Evaluate a TensorMathExpression over matrix-backed tensors. Returns {values, dims, einsum, delegated}."""
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
    elif op == 'permute':
        r, out = permute(a, names, dims)
    elif op == 'slice':
        r, out = slice_(a, names, ops[0].get('ranges', {}))
    else:
        raise TensorOpsError('operation %r is not implemented in this slice (contract|outer|reduce|permute|slice)' % op)
    return {'values': np.asarray(r).tolist(), 'dims': out, 'shape': list(np.asarray(r).shape), 'einsum': '', 'delegated': ''}
