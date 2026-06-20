# Author: Dustin Etts
# Matrix executor — resolves a MatrixDefinition to a concrete NumPy array.
#
# Pure module: no server state beyond a `manager` (used only to look up
# referenced MatrixDefinition / EquationDefinition rows by name). Mirrors the
# equation_executor contract — callers pass a definition + runtime bindings and
# get back a value (here, an np.ndarray) or a raised MatrixEvalError.
#
# Element kinds, in order of how they nest:
#   numeric ("float"/"int"/"complex")  — literal numbers
#   "equation"                         — each cell is an equation → scalar
#   "matrix"                           — each cell is a sub-matrix (block compose)
# Computation kinds (how the whole matrix is produced):
#   "literal"      — elements taken straight from values_json (default)
#   "elementwise"  — one equation applied across binding matrices, cell by cell
#   "matrix_op"    — a restricted NumPy expression over referenced matrices

from __future__ import annotations

import json
from typing import Any

import numpy as np

from polariNoCode.equation_executor import execute_equation

# Guards matrix-of-matrices recursion (also a backstop against reference cycles
# that slip past the per-path `seen` set).
MAX_DEPTH = 16

_NUMERIC_DTYPES = {
    'int': np.int64,
    'float': np.float64,
    'complex': np.complex128,
}


class MatrixEvalError(Exception):
    """Raised for any structural / evaluation failure. The API layer turns
    this into a clean 400 with the message."""


# ============================================================================
# Public entry point
# ============================================================================

def evaluate(matrix_def, binding_values: dict | None = None, manager=None,
             _depth: int = 0, _seen: frozenset | None = None) -> np.ndarray:
    """Resolve ``matrix_def`` to a concrete NumPy array.

    Parameters
    ----------
    matrix_def : MatrixDefinition
        The matrix to evaluate (may reference other matrices/equations).
    binding_values : dict | None
        Runtime scalars/arrays available to equation bindings and matrix_op
        operands by name (supplements anything the definition declares).
    manager : object | None
        Used to look up referenced MatrixDefinition / EquationDefinition rows.
    """
    if _depth > MAX_DEPTH:
        raise MatrixEvalError("matrix nesting exceeded max depth (probable reference cycle)")
    binding_values = binding_values or {}
    name = getattr(matrix_def, 'name', '') or '<anonymous>'
    seen = _seen or frozenset()
    if name in seen:
        raise MatrixEvalError(f"cyclic matrix reference through '{name}'")
    seen = seen | {name}

    # MatrixDefinition is strictly an isolated matrix — operations (elementwise,
    # matmul, …) live on MatrixEquationDefinition. Always resolve literally.
    return _eval_literal(matrix_def, binding_values, manager, _depth, seen)


# ============================================================================
# Literal matrices (elements from values_json)
# ============================================================================

def _eval_literal(matrix_def, binding_values, manager, depth, seen) -> np.ndarray:
    shape = parse_shape(getattr(matrix_def, 'shape_json', '[]'))
    etype = getattr(matrix_def, 'element_type', 'float') or 'float'
    values = _parse_json(getattr(matrix_def, 'values_json', '[]') or '[]', [])
    if not isinstance(values, list):
        raise MatrixEvalError("values_json must be a flat, row-major list")

    if etype in _NUMERIC_DTYPES:
        return _numeric_array(values, shape, etype)
    if etype == 'equation':
        nums = [_eval_equation_element(v, binding_values, manager) for v in values]
        out_type = 'complex' if any(isinstance(n, complex) for n in nums) else 'float'
        return _numeric_array(nums, shape, out_type)
    if etype == 'matrix':
        return _compose_blocks(matrix_def, values, shape, binding_values, manager, depth, seen)
    if etype == 'mixed':
        return _eval_mixed(values, shape, binding_values, manager, depth, seen)
    raise MatrixEvalError(f"unknown element_type '{etype}'")


def _eval_mixed(values, shape, binding_values, manager, depth, seen) -> np.ndarray:
    """Per-cell self-describing elements: each cell is ``{kind: 'number' |
    'equation' | 'matrix', ...}``. All-scalar cells → a numeric array; all-
    matrix cells → block composition; mixing the two ranks is rejected."""
    total = _product(shape)
    if len(values) != total:
        raise MatrixEvalError(
            f"expected {total} element(s) for shape {list(shape)}, got {len(values)}")
    resolved = [_resolve_mixed_cell(c, binding_values, manager, depth, seen) for c in values]
    arrays = [r for r in resolved if isinstance(r, np.ndarray) and r.ndim >= 1]
    if arrays and len(arrays) != len(resolved):
        raise MatrixEvalError(
            "cannot mix scalar and matrix elements in one matrix — make every cell "
            "a matrix (block composition) or every cell a scalar")
    if not arrays:
        nums = [_as_py_number(r) if isinstance(r, np.ndarray) else r for r in resolved]
        out_type = 'complex' if any(isinstance(n, complex) for n in nums) else 'float'
        return _numeric_array(nums, shape, out_type)
    # All cells are matrices → compose as blocks (1-D or 2-D layout).
    if len(shape) not in (1, 2):
        raise MatrixEvalError("matrix-element composition supports 1-D or 2-D block layouts only")
    blocks = [np.atleast_2d(r) for r in resolved]
    if len(shape) == 1:
        grid: Any = [blocks]
    else:
        rows, cols = shape
        grid = [blocks[r * cols:(r + 1) * cols] for r in range(rows)]
    try:
        return np.block(grid)
    except ValueError as e:
        raise MatrixEvalError(f"block shapes are incompatible for composition: {e}")


def _resolve_mixed_cell(cell, binding_values, manager, depth, seen):
    """Resolve one self-describing cell to a scalar or an np.ndarray."""
    if isinstance(cell, (int, float, complex)):
        return cell
    if isinstance(cell, dict):
        kind = cell.get('kind')
        if kind == 'number' or (kind is None and 'value' in cell):
            return _coerce_number(cell.get('value', 0), 'float')
        if kind == 'equation' or (kind is None and ('latex' in cell or 'equationRef' in cell)):
            return _eval_equation_element(cell, binding_values, manager)
        if kind == 'matrix' or (kind is None and ('matrixRef' in cell or 'ref' in cell)):
            ref = cell.get('matrixRef') or cell.get('ref')
            if not ref:
                raise MatrixEvalError("matrix cell has no matrixRef")
            sub = _find_named('MatrixDefinition', ref, manager)
            if sub is None:
                raise MatrixEvalError(f"referenced matrix '{ref}' not found")
            return evaluate(sub, binding_values, manager, depth + 1, seen)
        if 're' in cell and 'im' in cell:
            return complex(cell['re'], cell['im'])
    raise MatrixEvalError(f"unrecognized cell (need kind number|equation|matrix): {cell!r}")


def _numeric_array(values, shape, etype) -> np.ndarray:
    total = _product(shape)
    if len(values) != total:
        raise MatrixEvalError(
            f"expected {total} element(s) for shape {list(shape)}, got {len(values)}")
    dtype = _NUMERIC_DTYPES.get(etype, np.float64)
    try:
        flat = np.array([_coerce_number(v, etype) for v in values], dtype=dtype)
    except MatrixEvalError:
        raise
    except Exception as e:  # pragma: no cover - defensive
        raise MatrixEvalError(f"could not build numeric array: {e}")
    return flat.reshape(shape) if shape else flat.reshape(())


# ============================================================================
# Equation-typed elements (each cell resolves to a scalar)
# ============================================================================

def _eval_equation_element(spec, binding_values, manager):
    """Resolve one ``element_type == "equation"`` cell to a number.

    `spec` is either a bare number (treated as a literal) or a dict:
      {"equationRef": "<name>"} | {"latex": "x^2"}, plus optional
      "operationType", "bindings", "bounds", "options".
    """
    if isinstance(spec, (int, float, complex)):
        return spec
    if not isinstance(spec, dict):
        raise MatrixEvalError(f"equation element must be a number or object, got {type(spec).__name__}")

    latex, op, bounds, options, base_bindings = _equation_source(
        spec.get('equationRef'), spec.get('latex'), spec.get('operationType', 'evaluate'), manager)
    if 'bounds' in spec and isinstance(spec['bounds'], dict):
        bounds = spec['bounds']
    if 'options' in spec and isinstance(spec['options'], dict):
        options = {**(options or {}), **spec['options']}

    # Precedence: runtime bindings (global, from the Test tab) form the base so
    # an equation cell with no per-cell bindings still reduces; the equation's
    # own stored literals override those; explicit per-cell bindings win last.
    bindings = dict(binding_values or {})
    bindings.update(base_bindings)
    for sym, val in (spec.get('bindings') or {}).items():
        bindings[sym] = _resolve_scalar_binding(val, binding_values)

    res = execute_equation(latex, op, variable_bindings=bindings, bounds=bounds, options=options)
    if not res.get('success'):
        raise MatrixEvalError(f"equation element failed: {res.get('error')}")
    num = res.get('result_numeric')
    if num is None or isinstance(num, (list, tuple)):
        raise MatrixEvalError(
            f"equation element did not reduce to a scalar (got {num!r}); "
            f"bind all free symbols")
    return num


def _equation_source(eq_ref, inline_latex, operation_type, manager):
    """Return (latex, operation_type, bounds, options, base_bindings) from
    either a stored EquationDefinition or an inline LaTeX spec."""
    if eq_ref:
        eq = _find_named('EquationDefinition', eq_ref, manager)
        if eq is None:
            raise MatrixEvalError(f"referenced equation '{eq_ref}' not found")
        definition = _parse_json(getattr(eq, 'definition', '') or '{}', {})
        latex = definition.get('latexExpression', '') or definition.get('latex', '')
        if not latex:
            raise MatrixEvalError(f"equation '{eq_ref}' has no latexExpression")
        op = operation_type or definition.get('operationType', 'evaluate')
        bounds = definition.get('bounds')
        options = definition.get('options') or {}
        base = _literal_bindings(definition.get('variableBindings'))
        return latex, op, bounds, options, base
    if inline_latex:
        return inline_latex, operation_type or 'evaluate', None, {}, {}
    raise MatrixEvalError("equation element needs either 'equationRef' or 'latex'")


def _literal_bindings(variable_bindings) -> dict:
    """Pull literal-source bindings out of an EquationDefinition's
    storage-format binding list (non-literal sources are left for the caller
    to supply at runtime)."""
    out: dict = {}
    if isinstance(variable_bindings, dict):
        return dict(variable_bindings)
    if isinstance(variable_bindings, list):
        for entry in variable_bindings:
            if not isinstance(entry, dict):
                continue
            sym = entry.get('symbol')
            src = entry.get('source') or {}
            if sym and src.get('type') == 'literal':
                out[sym] = src.get('value')
    return out


# ============================================================================
# Matrix-typed elements (matrix-of-matrices / block composition)
# ============================================================================

def _compose_blocks(matrix_def, values, shape, binding_values, manager, depth, seen) -> np.ndarray:
    if len(shape) not in (1, 2):
        raise MatrixEvalError("matrix-of-matrices composition supports 1-D or 2-D block layouts only")
    total = _product(shape)
    if len(values) != total:
        raise MatrixEvalError(
            f"expected {total} block entr(ies) for layout {list(shape)}, got {len(values)}")
    default_ref = getattr(matrix_def, 'element_matrix_ref', '') or ''
    blocks = [_resolve_block(v, default_ref, binding_values, manager, depth, seen) for v in values]

    if len(shape) == 1:
        grid: Any = [blocks]                       # one row of blocks
    else:
        rows, cols = shape
        grid = [blocks[r * cols:(r + 1) * cols] for r in range(rows)]
    try:
        return np.block(grid)
    except ValueError as e:
        raise MatrixEvalError(f"block shapes are incompatible for composition: {e}")


def _resolve_block(entry, default_ref, binding_values, manager, depth, seen) -> np.ndarray:
    ref = None
    if isinstance(entry, str):
        ref = entry
    elif isinstance(entry, dict):
        ref = entry.get('matrixRef') or entry.get('ref')
    ref = ref or default_ref
    if not ref:
        raise MatrixEvalError("matrix element has no matrixRef and no element_matrix_ref default")
    sub = _find_named('MatrixDefinition', ref, manager)
    if sub is None:
        raise MatrixEvalError(f"referenced matrix '{ref}' not found")
    block = evaluate(sub, binding_values, manager, depth + 1, seen)
    return np.atleast_2d(block)


# ============================================================================
# Computed matrices
# ============================================================================

def _eval_elementwise(computation, binding_values, manager, depth, seen) -> np.ndarray:
    """Apply one equation to each cell across the binding matrices.

    NOTE: re-runs the equation executor per cell, so it's O(n) parse/eval —
    fine for the matrices a user authors by hand, not for huge arrays.
    """
    bindings_spec = computation.get('bindings') or {}
    resolved: dict = {}
    grid_shape = None
    for sym, val in bindings_spec.items():
        operand = _resolve_operand(val, binding_values, manager, depth, seen)
        resolved[sym] = operand
        if isinstance(operand, np.ndarray):
            if grid_shape is None:
                grid_shape = operand.shape
            elif operand.shape != grid_shape:
                raise MatrixEvalError("elementwise binding matrices disagree on shape")
    if grid_shape is None:
        raise MatrixEvalError("elementwise computation needs at least one matrix binding")

    latex, op, bounds, options, base_bindings = _equation_source(
        computation.get('equationRef'), computation.get('latex'),
        computation.get('operationType', 'evaluate'), manager)

    flat_n = _product(grid_shape)
    results = []
    is_complex = False
    for i in range(flat_n):
        idx = np.unravel_index(i, grid_shape)
        per = dict(base_bindings)
        for sym, operand in resolved.items():
            per[sym] = (_as_py_number(operand[idx]) if isinstance(operand, np.ndarray)
                        else operand)
        res = execute_equation(latex, op, variable_bindings=per, bounds=bounds, options=options)
        if not res.get('success'):
            raise MatrixEvalError(f"elementwise equation failed at index {idx}: {res.get('error')}")
        num = res.get('result_numeric')
        if num is None or isinstance(num, (list, tuple)):
            raise MatrixEvalError(f"elementwise equation did not reduce to a scalar at {idx}")
        if isinstance(num, complex):
            is_complex = True
        results.append(num)
    dtype = np.complex128 if is_complex else np.float64
    return np.array(results, dtype=dtype).reshape(grid_shape)


def _eval_matrix_op(computation, binding_values, manager, depth, seen) -> np.ndarray:
    """Evaluate a restricted NumPy expression over referenced matrices, e.g.
    ``"A @ B + C"`` with operands {A, B, C} each a matrix ref / runtime array."""
    expr = computation.get('expr')
    if not expr or not isinstance(expr, str):
        raise MatrixEvalError("matrix_op requires a string 'expr'")
    if '__' in expr:
        raise MatrixEvalError("matrix_op expression may not contain '__'")
    operands_spec = computation.get('operands') or {}
    env = {
        name: _resolve_operand(ref, binding_values, manager, depth, seen)
        for name, ref in operands_spec.items()
    }
    return _safe_matrix_eval(expr, env)


# Curated helpers exposed to matrix_op expressions (no builtins).
def _normalize_vec(v):
    """Unit vector of v; raises on the zero vector (no defined direction)."""
    arr = np.asarray(v, dtype=float)
    n = np.linalg.norm(arr)
    if n == 0:
        raise MatrixEvalError("cannot normalize the zero vector")
    return arr / n


_MATRIX_OP_HELPERS = {
    'np': np,
    'inv': np.linalg.inv,
    'det': np.linalg.det,
    'solve': np.linalg.solve,
    'tr': np.trace,
    'T': np.transpose,
    'eye': np.eye,
    'kron': np.kron,
    'diag': np.diag,
    'dot': np.dot,
    # Vector ops — make 3-vector math expressible in matrix-equation `expr`
    # (and, through the MatrixEquationOperation no-code state, in solutions).
    'cross': np.cross,
    'norm': np.linalg.norm,
    'normalize': _normalize_vec,
}


def _safe_matrix_eval(expr: str, env: dict) -> np.ndarray:
    arrays = {k: (v if isinstance(v, np.ndarray) else np.asarray(v)) for k, v in env.items()}
    scope = {**_MATRIX_OP_HELPERS, **arrays}
    try:
        result = eval(expr, {'__builtins__': {}}, scope)  # noqa: S307 - sandboxed scope, '__' rejected
    except MatrixEvalError:
        raise
    except Exception as e:
        raise MatrixEvalError(f"matrix_op evaluation failed: {type(e).__name__}: {e}")
    return np.asarray(result)


# ============================================================================
# Operand / binding resolution shared by elementwise + matrix_op
# ============================================================================

def _resolve_operand(spec, binding_values, manager, depth, seen):
    """Resolve a binding/operand spec to a scalar or an np.ndarray.

    Accepts: a number; a runtime-binding name; a matrix ref name; or a dict
    {"matrixRef": name} / {"scalar": value} / {"value": value}."""
    if isinstance(spec, (int, float, complex)):
        return spec
    if isinstance(spec, list):
        return np.asarray(spec)
    if isinstance(spec, str):
        if spec in binding_values:
            v = binding_values[spec]
            return np.asarray(v) if isinstance(v, list) else v
        sub = _find_named('MatrixDefinition', spec, manager)
        if sub is None:
            raise MatrixEvalError(f"operand '{spec}' is neither a runtime binding nor a known matrix")
        return evaluate(sub, binding_values, manager, depth + 1, seen)
    if isinstance(spec, dict):
        if 'scalar' in spec:
            return spec['scalar']
        if 'value' in spec:
            return spec['value']
        ref = spec.get('matrixRef') or spec.get('ref')
        if ref:
            sub = _find_named('MatrixDefinition', ref, manager)
            if sub is None:
                raise MatrixEvalError(f"referenced matrix '{ref}' not found")
            return evaluate(sub, binding_values, manager, depth + 1, seen)
    raise MatrixEvalError(f"could not resolve operand from {spec!r}")


def _resolve_scalar_binding(val, binding_values):
    """Per-element equation binding value: a literal, or a runtime-binding
    name to substitute."""
    if isinstance(val, str) and val in binding_values:
        return binding_values[val]
    return val


# ============================================================================
# Low-level helpers (shared with the validator)
# ============================================================================

def parse_shape(shape_json) -> tuple:
    raw = shape_json if isinstance(shape_json, (list, tuple)) else _parse_json(shape_json or '[]', None)
    if not isinstance(raw, (list, tuple)):
        raise MatrixEvalError(f"shape must be a list, got {type(raw).__name__}")
    dims = []
    for d in raw:
        try:
            n = int(d)
        except (TypeError, ValueError):
            raise MatrixEvalError(f"shape dimension '{d}' is not an integer")
        if n <= 0:
            raise MatrixEvalError(f"shape dimensions must be positive, got {n}")
        dims.append(n)
    return tuple(dims)


def _find_named(class_name: str, name: str, manager):
    if manager is None or not name:
        return None
    table = manager.objectTables.get(class_name, {}) or {}
    for inst in table.values():
        if getattr(inst, 'name', '') == name:
            return inst
    return None


def _coerce_number(v, etype):
    if isinstance(v, bool):
        v = int(v)
    if etype == 'complex':
        if isinstance(v, str):
            return complex(v.replace('i', 'j'))
        return complex(v)
    if etype == 'int':
        return int(v)
    # float (default)
    if isinstance(v, str):
        s = v.strip()
        if s == '':
            raise MatrixEvalError("empty string is not a number")
        return float(s)
    return float(v)


def _as_py_number(x):
    """Turn a NumPy scalar into a plain Python number for the equation executor."""
    val = x.item() if hasattr(x, 'item') else x
    if isinstance(val, complex) and val.imag == 0:
        return val.real
    return val


def _product(shape) -> int:
    total = 1
    for d in shape:
        total *= d
    return total


def _parse_json(raw, default):
    if isinstance(raw, (dict, list)):
        return raw
    try:
        return json.loads(raw)
    except (TypeError, ValueError):
        return default
