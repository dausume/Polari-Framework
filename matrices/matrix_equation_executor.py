# Author: Dustin Etts
# Matrix-equation executor — evaluates a MatrixEquationDefinition to a concrete
# NumPy result. Operands may be isolated matrices, other matrix equations, or
# scalar EquationDefinitions (plus literal scalars). Guards recursive
# matrix-equation references (infinite loops).

from __future__ import annotations

import numpy as np

from polariNoCode.equation_executor import execute_equation
from matrices.matrix_executor import (
    MatrixEvalError,
    evaluate as evaluate_matrix,
    _safe_matrix_eval,
    _equation_source,
    _find_named,
    _parse_json,
    _as_py_number,
)

MAX_DEPTH = 16

# Operation kinds and their operand-slot requirements (for validation + UI).
BINARY_OPS = {'matmul', 'add', 'subtract', 'hadamard', 'kron', 'solve'}
UNARY_OPS = {'transpose', 'inverse', 'determinant', 'trace'}
ALL_OP_KINDS = BINARY_OPS | UNARY_OPS | {'scalar_mul', 'power', 'elementwise', 'expr'}


# ============================================================================
# Public entry point
# ============================================================================

def evaluate_equation(eq_def, binding_values: dict | None = None, manager=None,
                      _depth: int = 0, _seen: frozenset | None = None) -> np.ndarray:
    if _depth > MAX_DEPTH:
        raise MatrixEvalError("matrix-equation nesting exceeded max depth (probable reference cycle)")
    binding_values = binding_values or {}
    name = getattr(eq_def, 'name', '') or '<anonymous equation>'
    seen = _seen or frozenset()
    if name in seen:
        raise MatrixEvalError(f"cyclic matrix-equation reference through '{name}'")
    seen = seen | {name}

    op = _parse_json(getattr(eq_def, 'operation_json', '') or '{}', {})
    if not isinstance(op, dict):
        raise MatrixEvalError("operation_json must be a JSON object")
    operands = _parse_json(getattr(eq_def, 'operands_json', '') or '{}', {})
    if not isinstance(operands, dict):
        raise MatrixEvalError("operands_json must be a JSON object")

    def resolve(sym):
        if sym is None or sym not in operands:
            raise MatrixEvalError(f"operation references operand '{sym}' which is not defined")
        return _resolve_operand_spec(operands[sym], binding_values, manager, _depth, seen)

    kind = op.get('kind')
    if kind in BINARY_OPS:
        a = _as_matrix(resolve(op.get('a')))
        b = _as_matrix(resolve(op.get('b')))
        result = _binary(kind, a, b)
    elif kind in UNARY_OPS:
        result = _unary(kind, _as_matrix(resolve(op.get('a'))))
    elif kind == 'scalar_mul':
        c = _as_scalar(resolve(op.get('scalar')))
        result = c * _as_matrix(resolve(op.get('a')))
    elif kind == 'power':
        a = _as_matrix(resolve(op.get('a')))
        n = int(_as_scalar(resolve(op.get('n'))))
        result = np.linalg.matrix_power(a, n)
    elif kind == 'elementwise':
        result = _elementwise(op, _as_matrix(resolve(op.get('a'))), binding_values, manager)
    elif kind == 'expr':
        expr = op.get('expr')
        if not expr or not isinstance(expr, str):
            raise MatrixEvalError("expr operation requires a string 'expr'")
        env = {sym: resolve(sym) for sym in operands.keys()}
        result = _safe_matrix_eval(expr, env)
    else:
        raise MatrixEvalError(f"unknown matrix-equation operation kind '{kind}'")

    return np.asarray(result)


# ============================================================================
# Operand resolution
# ============================================================================

def _resolve_operand_spec(spec, binding_values, manager, depth, seen):
    """Resolve one operand to a scalar or an np.ndarray."""
    if isinstance(spec, (int, float, complex)):
        return spec
    if isinstance(spec, list):
        return np.asarray(spec)
    if isinstance(spec, str):
        return _resolve_named(spec, binding_values, manager, depth, seen)
    if isinstance(spec, dict):
        kind = spec.get('kind')
        if kind == 'scalar':
            return spec.get('value', 0)
        ref = spec.get('ref') or spec.get('matrixRef')
        if kind == 'matrix':
            m = _find_named('MatrixDefinition', ref, manager)
            if m is None:
                raise MatrixEvalError(f"referenced matrix '{ref}' not found")
            return evaluate_matrix(m, binding_values, manager, depth + 1)
        if kind == 'matrixEquation':
            e = _find_named('MatrixEquationDefinition', ref, manager)
            if e is None:
                raise MatrixEvalError(f"referenced matrix equation '{ref}' not found")
            return evaluate_equation(e, binding_values, manager, depth + 1, seen)
        if kind == 'equation':
            return _eval_scalar_equation(ref, manager, binding_values)
        if kind is None and ref:
            return _resolve_named(ref, binding_values, manager, depth, seen)
    raise MatrixEvalError(f"could not resolve operand from {spec!r}")


def _resolve_named(name, binding_values, manager, depth, seen):
    """Resolve a bare name: runtime binding, then matrix, then matrix equation."""
    if name in binding_values:
        v = binding_values[name]
        return np.asarray(v) if isinstance(v, list) else v
    m = _find_named('MatrixDefinition', name, manager)
    if m is not None:
        return evaluate_matrix(m, binding_values, manager, depth + 1)
    e = _find_named('MatrixEquationDefinition', name, manager)
    if e is not None:
        return evaluate_equation(e, binding_values, manager, depth + 1, seen)
    raise MatrixEvalError(f"operand '{name}' is not a runtime binding, matrix, or matrix equation")


def _eval_scalar_equation(ref, manager, binding_values):
    eq = _find_named('EquationDefinition', ref, manager)
    if eq is None:
        raise MatrixEvalError(f"referenced equation '{ref}' not found")
    latex, op, bounds, options, base = _equation_source(ref, None, 'evaluate', manager)
    bindings = dict(binding_values)
    bindings.update(base)
    res = execute_equation(latex, op, variable_bindings=bindings, bounds=bounds, options=options)
    if not res.get('success'):
        raise MatrixEvalError(f"scalar equation '{ref}' failed: {res.get('error')}")
    num = res.get('result_numeric')
    if num is None or isinstance(num, (list, tuple)):
        raise MatrixEvalError(f"equation operand '{ref}' did not reduce to a scalar")
    return num


# ============================================================================
# Operations
# ============================================================================

def _binary(kind, a, b):
    if kind == 'matmul':   return a @ b
    if kind == 'add':      return a + b
    if kind == 'subtract': return a - b
    if kind == 'hadamard': return a * b
    if kind == 'kron':     return np.kron(a, b)
    if kind == 'solve':    return np.linalg.solve(a, b)
    raise MatrixEvalError(f"unknown binary op '{kind}'")


def _unary(kind, a):
    if kind == 'transpose':   return np.transpose(a)
    if kind == 'inverse':     return np.linalg.inv(a)
    if kind == 'determinant': return np.linalg.det(a)
    if kind == 'trace':       return np.trace(a)
    raise MatrixEvalError(f"unknown unary op '{kind}'")


def _elementwise(op, a, binding_values, manager):
    """Apply a scalar equation f to each cell of matrix `a`."""
    symbol = op.get('symbol', 'x')
    latex, opn, bounds, options, base = _equation_source(
        op.get('equationRef'), op.get('latex'), op.get('operationType', 'evaluate'), manager)
    flat = np.asarray(a).ravel()
    out, is_complex = [], False
    for val in flat:
        per = dict(binding_values)
        per.update(base)
        per[symbol] = _as_py_number(val)
        res = execute_equation(latex, opn, variable_bindings=per, bounds=bounds, options=options)
        if not res.get('success'):
            raise MatrixEvalError(f"elementwise equation failed: {res.get('error')}")
        num = res.get('result_numeric')
        if num is None or isinstance(num, (list, tuple)):
            raise MatrixEvalError("elementwise equation did not reduce to a scalar")
        if isinstance(num, complex):
            is_complex = True
        out.append(num)
    return np.array(out, dtype=np.complex128 if is_complex else np.float64).reshape(np.asarray(a).shape)


# ============================================================================
# Coercion helpers
# ============================================================================

def _as_matrix(v):
    return np.asarray(v)


def _as_scalar(v):
    if isinstance(v, np.ndarray):
        if v.ndim == 0:
            return _as_py_number(v)
        raise MatrixEvalError("expected a scalar operand but got a matrix")
    return v


# ============================================================================
# Validation
# ============================================================================

def validate_equation(eq_def, manager=None) -> dict:
    errors: list = []
    warnings: list = []

    op = _parse_json(getattr(eq_def, 'operation_json', '') or '{}', {})
    operands = _parse_json(getattr(eq_def, 'operands_json', '') or '{}', {})
    if not isinstance(op, dict):
        errors.append("operation_json must be a JSON object")
        op = {}
    if not isinstance(operands, dict):
        errors.append("operands_json must be a JSON object")
        operands = {}

    kind = op.get('kind')
    if kind not in ALL_OP_KINDS:
        errors.append(f"unknown operation kind '{kind}'")

    # Required operand symbols per kind must be present in operands.
    required = []
    if kind in BINARY_OPS:
        required = [op.get('a'), op.get('b')]
    elif kind in UNARY_OPS or kind == 'elementwise':
        required = [op.get('a')]
    elif kind == 'scalar_mul':
        required = [op.get('scalar'), op.get('a')]
    elif kind == 'power':
        required = [op.get('a'), op.get('n')]
    for sym in required:
        if not sym:
            errors.append(f"operation '{kind}' is missing an operand slot")
        elif sym not in operands:
            errors.append(f"operand '{sym}' referenced by the operation is not defined")
    if kind == 'expr' and not op.get('expr'):
        errors.append("expr operation requires 'expr'")
    if kind == 'elementwise' and not op.get('equationRef') and not op.get('latex'):
        errors.append("elementwise operation needs an equationRef or inline latex")

    # Referenced operands must resolve.
    for sym, spec in operands.items():
        _validate_operand_ref(sym, spec, manager, errors, warnings)

    cycle = _detect_equation_cycle(eq_def, manager)
    if cycle:
        errors.append("recursive matrix-equation reference would loop: " + " → ".join(cycle))

    return {'valid': not errors, 'errors': errors, 'warnings': warnings, 'kind': kind}


def _validate_operand_ref(sym, spec, manager, errors, warnings):
    if not isinstance(spec, dict):
        return
    kind = spec.get('kind')
    ref = spec.get('ref') or spec.get('matrixRef')
    if kind == 'scalar':
        return
    if kind == 'matrix':
        if not ref or _find_named('MatrixDefinition', ref, manager) is None:
            errors.append(f"operand '{sym}': matrix '{ref}' not found")
    elif kind == 'matrixEquation':
        if not ref or _find_named('MatrixEquationDefinition', ref, manager) is None:
            errors.append(f"operand '{sym}': matrix equation '{ref}' not found")
    elif kind == 'equation':
        if not ref or _find_named('EquationDefinition', ref, manager) is None:
            warnings.append(f"operand '{sym}': equation '{ref}' not found")


def _equation_refs_of(eq_def, manager) -> list:
    operands = _parse_json(getattr(eq_def, 'operands_json', '') or '{}', {})
    refs = []
    if isinstance(operands, dict):
        for spec in operands.values():
            if isinstance(spec, dict) and spec.get('kind') == 'matrixEquation':
                ref = spec.get('ref')
                if ref:
                    refs.append(ref)
    return refs


def _detect_equation_cycle(eq_def, manager):
    start = getattr(eq_def, 'name', '') or '<this equation>'

    def dfs(node, path):
        for ref in _equation_refs_of(node, manager):
            if ref == start:
                return [*path, ref]
            if ref in path:
                continue
            child = _find_named('MatrixEquationDefinition', ref, manager)
            if child is not None:
                found = dfs(child, [*path, ref])
                if found:
                    return found
        return None

    return dfs(eq_def, [start])
