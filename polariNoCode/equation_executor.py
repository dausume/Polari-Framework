# Author: Dustin Etts
# Equation executor — symbolic + numerical math operations on LaTeX expressions
# and numeric dataseries.
#
# Pure module: no state-system integration. Frontend posts a LaTeX string + an
# operation type + variable bindings; this module returns:
#   { success, result_latex, result_numeric, error, warnings }
#
# Library stack:
#   sympy                        symbolic CAS (derivative, integral, ODE, PDE, solve, simplify, ...)
#   antlr4-python3-runtime       SymPy's parse_latex dependency
#   numpy                        dataseries arrays + np.gradient / np.trapz
#   scipy                        scipy.integrate (simpson, solve_ivp, quad)
#
# All open-source, all BSD-licensed, all run locally — no external services.

from __future__ import annotations

import json
from typing import Any

import sympy
from sympy import (
    Symbol,
    diff,
    integrate,
    limit,
    series,
    simplify,
    expand,
    factor,
    solve,
    dsolve,
    Eq,
    sympify,
    latex as sympy_latex,
    Function,
)

try:
    from sympy import pdsolve
    HAS_PDSOLVE = True
except ImportError:
    HAS_PDSOLVE = False

from sympy.parsing.latex import parse_latex

import numpy as np
from scipy import integrate as sp_integrate


# ============================================================================
# Operation types
# ============================================================================

OPERATION_TYPES = {
    'derivative',                    # symbolic derivative
    'integral_definite',             # symbolic definite integral
    'integral_indefinite',           # symbolic indefinite integral
    'evaluate',                      # substitute + numeric eval
    'simplify',                      # algebraic simplification
    'expand',                        # polynomial expansion
    'factor',                        # polynomial factoring
    'solve',                         # solve algebraic equation(s)
    'limit',                         # take a limit
    'series',                        # Taylor / power series expansion
    'ode_solve',                     # symbolic ODE solver (sympy.dsolve)
    'pde_solve',                     # symbolic PDE solver (sympy.pdsolve, limited classes)
    'dataseries_derivative',         # numerical derivative on a numeric array (np.gradient)
    'dataseries_integral',           # numerical integral on a numeric array (np.trapz / scipy simpson)
    'dataseries_ode_solve',          # numerical IVP ODE on dataseries (scipy.solve_ivp)
}


# ============================================================================
# Public entry point
# ============================================================================

def execute_equation(
    latex_expression: str,
    operation_type: str,
    variable_bindings: dict[str, Any] | None = None,
    bounds: dict[str, Any] | None = None,
    options: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Execute one symbolic or numeric operation on a LaTeX expression.

    Parameters
    ----------
    latex_expression : str
        The expression in LaTeX, e.g. ``r"\\int_0^1 \\sin(x) dx"`` or ``r"x^2 + 1"``.
        For dataseries operations, this can be empty if the expression is purely
        the dataseries (the operation runs directly on the numeric array).
    operation_type : str
        One of ``OPERATION_TYPES``.
    variable_bindings : dict[str, Any] | None
        Map of LaTeX symbol → runtime value. Values can be:
          - numeric literal (int/float)
          - LaTeX string (will be parsed)
          - list/np.ndarray (for dataseries operations)
        Symbols not in the mapping are treated as free symbolic variables.
    bounds : dict | None
        For definite integrals / sums: ``{'variable': 'x', 'lower': '0', 'upper': '1'}``.
        For limits: ``{'variable': 'x', 'point': '0', 'direction': '+' | '-' | None}``.
        For series: ``{'variable': 'x', 'point': '0', 'order': 4}``.
    options : dict | None
        Operation-specific options (method='trapezoidal' for dataseries integration, etc.).

    Returns
    -------
    dict
        ``{success, result_latex, result_numeric, error, warnings}``
    """
    options = options or {}
    bindings = _normalize_variable_bindings(variable_bindings)
    warnings: list[str] = []

    if operation_type not in OPERATION_TYPES:
        return _error(f"Unknown operation_type '{operation_type}'. "
                      f"Expected one of: {sorted(OPERATION_TYPES)}")

    # Dataseries ops handle their own data; symbolic ops parse LaTeX first.
    is_dataseries = operation_type.startswith('dataseries_')

    try:
        if is_dataseries:
            return _execute_dataseries(
                operation_type=operation_type,
                latex_expression=latex_expression,
                variable_bindings=bindings,
                bounds=bounds,
                options=options,
                warnings=warnings,
            )
        else:
            return _execute_symbolic(
                operation_type=operation_type,
                latex_expression=latex_expression,
                variable_bindings=bindings,
                bounds=bounds,
                options=options,
                warnings=warnings,
            )
    except Exception as e:
        return _error(f"{type(e).__name__}: {e}", warnings=warnings)


# ============================================================================
# Symbolic ops (SymPy)
# ============================================================================

def _execute_symbolic(
    operation_type: str,
    latex_expression: str,
    variable_bindings: dict[str, Any],
    bounds: dict[str, Any] | None,
    options: dict[str, Any],
    warnings: list[str],
) -> dict[str, Any]:
    expr = _parse_latex_to_sympy(latex_expression)

    # Apply scalar variable bindings (literals or LaTeX-string substitutes).
    # Dataseries values are never substituted into symbolic expressions.
    subs_map = _build_subs_map(expr, variable_bindings)

    if operation_type == 'derivative':
        var = _resolve_variable(expr, options.get('variable') or _first_free_symbol(expr))
        order = int(options.get('order', 1))
        result = diff(expr.subs(subs_map), var, order)

    elif operation_type == 'integral_indefinite':
        var = _resolve_variable(expr, options.get('variable') or _first_free_symbol(expr))
        result = integrate(expr.subs(subs_map), var)

    elif operation_type == 'integral_definite':
        if not bounds or 'variable' not in bounds:
            return _error("integral_definite requires bounds with 'variable', 'lower', 'upper'.")
        var = _resolve_variable(expr, bounds['variable'])
        lower = sympify(_unwrap_latex(bounds.get('lower', 0)))
        upper = sympify(_unwrap_latex(bounds.get('upper', 1)))
        result = integrate(expr.subs(subs_map), (var, lower, upper))

    elif operation_type == 'evaluate':
        result = expr.subs(subs_map)
        # Try to compute a numeric value in addition to the symbolic form.
        try:
            numeric = float(result.evalf())
            return _ok(result, numeric_override=numeric, warnings=warnings)
        except Exception:
            pass

    elif operation_type == 'simplify':
        result = simplify(expr.subs(subs_map))

    elif operation_type == 'expand':
        result = expand(expr.subs(subs_map))

    elif operation_type == 'factor':
        result = factor(expr.subs(subs_map))

    elif operation_type == 'solve':
        # Treat the expression as = 0 by default; or use lhs-rhs from an Eq.
        var_name = options.get('variable') or _first_free_symbol(expr)
        var = _resolve_variable(expr, var_name)
        result = solve(expr.subs(subs_map), var)
        # `solve` returns a list — render as a list of sympy expressions.
        return _ok_list(result, warnings=warnings)

    elif operation_type == 'limit':
        if not bounds or 'variable' not in bounds:
            return _error("limit requires bounds with 'variable' and 'point'.")
        var = _resolve_variable(expr, bounds['variable'])
        point = sympify(_unwrap_latex(bounds.get('point', 0)))
        direction = bounds.get('direction')
        if direction in ('+', '-'):
            result = limit(expr.subs(subs_map), var, point, direction)
        else:
            result = limit(expr.subs(subs_map), var, point)

    elif operation_type == 'series':
        if not bounds or 'variable' not in bounds:
            return _error("series requires bounds with 'variable' and 'point' and 'order'.")
        var = _resolve_variable(expr, bounds['variable'])
        point = sympify(_unwrap_latex(bounds.get('point', 0)))
        order = int(bounds.get('order', 6))
        result = series(expr.subs(subs_map), var, point, order).removeO()

    elif operation_type == 'ode_solve':
        # The expression is treated as the ODE f(x, y, y') = 0 (or `Eq(lhs, rhs)`).
        # Caller must declare the dependent function in `options.function` (default 'y(x)').
        func_decl = options.get('function', 'y(x)')
        f = _make_function(func_decl)
        var = _resolve_variable(expr, options.get('variable', 'x'))
        # Replace bare 'y' / 'y(x)' in the expression with the proper Function call.
        result = dsolve(expr.subs(subs_map), f)

    elif operation_type == 'pde_solve':
        if not HAS_PDSOLVE:
            return _error("PDE solving not available in this SymPy build.")
        func_decl = options.get('function', 'u(x, t)')
        f = _make_function(func_decl)
        result = pdsolve(expr.subs(subs_map), f)

    else:
        return _error(f"Operation '{operation_type}' not implemented.")

    return _ok(result, warnings=warnings)


# ============================================================================
# Dataseries ops (NumPy / SciPy)
# ============================================================================

def _execute_dataseries(
    operation_type: str,
    latex_expression: str,
    variable_bindings: dict[str, Any],
    bounds: dict[str, Any] | None,
    options: dict[str, Any],
    warnings: list[str],
) -> dict[str, Any]:
    series_name = options.get('dataseries', 'data')
    series_data = variable_bindings.get(series_name)
    if series_data is None:
        return _error(f"Dataseries operation requires variable_bindings['{series_name}'] "
                      f"to be a numeric array.")

    arr = np.asarray(series_data, dtype=float)

    if operation_type == 'dataseries_derivative':
        # First-order finite differences with edge-aware second-order accuracy.
        x = variable_bindings.get('x')
        if x is not None:
            x_arr = np.asarray(x, dtype=float)
            result_arr = np.gradient(arr, x_arr)
        else:
            result_arr = np.gradient(arr)
        return _ok_array(result_arr, warnings=warnings)

    elif operation_type == 'dataseries_integral':
        method = options.get('method', 'trapezoidal')
        x = variable_bindings.get('x')
        if method == 'simpson':
            result_val = float(sp_integrate.simpson(arr, x=x))
        else:
            if x is not None:
                result_val = float(np.trapz(arr, x=np.asarray(x, dtype=float)))
            else:
                result_val = float(np.trapz(arr))
        return _ok_scalar(result_val, warnings=warnings)

    elif operation_type == 'dataseries_ode_solve':
        # Initial value problem: dy/dt = f(t, y) where f is a SymPy expression
        # in terms of t and y. The dataseries here is the t-grid to evaluate on.
        if not latex_expression:
            return _error("dataseries_ode_solve requires latex_expression for f(t, y).")
        rhs = _parse_latex_to_sympy(latex_expression)
        t_sym = Symbol('t')
        y_sym = Symbol('y')
        rhs_func = sympy.lambdify((t_sym, y_sym), rhs, modules='numpy')
        t_eval = arr
        y0 = float(options.get('y0', 0.0))
        sol = sp_integrate.solve_ivp(
            fun=rhs_func,
            t_span=(float(t_eval[0]), float(t_eval[-1])),
            y0=[y0],
            t_eval=t_eval,
            method=options.get('method', 'RK45'),
        )
        if not sol.success:
            return _error(f"solve_ivp failed: {sol.message}")
        return _ok_array(sol.y[0], warnings=warnings)

    else:
        return _error(f"Dataseries operation '{operation_type}' not implemented.")


# ============================================================================
# Helpers
# ============================================================================

def _normalize_variable_bindings(variable_bindings: Any) -> dict[str, Any]:
    """
    Accept either:
      - a runtime dict ``{symbol: value}``  (preferred)
      - the storage-format list ``[{"symbol": s, "source": {...}}, ...]``
        which gets resolved to a dict containing only literal sources;
        non-literal source types are skipped and must be supplied via
        a separate runtime dict by the caller.
      - None, falsy → returns empty dict.
    """
    if not variable_bindings:
        return {}
    if isinstance(variable_bindings, dict):
        return variable_bindings
    if isinstance(variable_bindings, list):
        out: dict[str, Any] = {}
        for entry in variable_bindings:
            if not isinstance(entry, dict):
                continue
            symbol = entry.get('symbol')
            source = entry.get('source') or {}
            if symbol and source.get('type') == 'literal':
                out[symbol] = source.get('value')
        return out
    return {}


def _parse_latex_to_sympy(latex_expression: str):
    if not latex_expression:
        raise ValueError("latex_expression is empty.")
    # Strip leading/trailing whitespace and `$`-delimiters if present.
    s = latex_expression.strip().strip('$').strip()
    return parse_latex(s)


def _unwrap_latex(value: Any) -> Any:
    """Allow lower/upper bounds to be either numeric or LaTeX strings."""
    if isinstance(value, str):
        try:
            return _parse_latex_to_sympy(value)
        except Exception:
            return sympify(value)
    return value


def _build_subs_map(expr, variable_bindings: dict[str, Any]) -> dict:
    """Build a SymPy substitution map from variable_bindings, skipping dataseries."""
    subs: dict = {}
    free_symbols_by_name = {str(s): s for s in expr.free_symbols}
    for name, value in variable_bindings.items():
        if isinstance(value, (list, tuple, np.ndarray)):
            continue  # dataseries — not substituted into symbolic expressions
        sym = free_symbols_by_name.get(name) or Symbol(name)
        if isinstance(value, str):
            try:
                subs[sym] = _parse_latex_to_sympy(value)
            except Exception:
                subs[sym] = sympify(value)
        else:
            subs[sym] = value
    return subs


def _resolve_variable(expr, var_name: str) -> Symbol:
    if isinstance(var_name, Symbol):
        return var_name
    for s in expr.free_symbols:
        if str(s) == var_name:
            return s
    return Symbol(var_name)


def _first_free_symbol(expr) -> str:
    syms = sorted((str(s) for s in expr.free_symbols))
    if not syms:
        raise ValueError("Expression has no free symbols; specify 'variable' in options.")
    return syms[0]


def _make_function(decl: str):
    """Parse 'y(x)' or 'u(x, t)' into a SymPy Function applied to its args."""
    if '(' not in decl:
        return Function(decl.strip())(Symbol('x'))
    name, rest = decl.split('(', 1)
    args = [Symbol(a.strip()) for a in rest.rstrip(')').split(',')]
    return Function(name.strip())(*args)


def _ok(result, numeric_override: float | None = None, warnings: list[str] | None = None) -> dict:
    try:
        latex = sympy_latex(result)
    except Exception:
        latex = str(result)
    numeric: float | None = numeric_override
    if numeric is None:
        try:
            numeric = float(result.evalf())
        except Exception:
            numeric = None
    return {
        'success': True,
        'result_latex': latex,
        'result_numeric': numeric,
        'error': None,
        'warnings': warnings or [],
    }


def _ok_list(items: list, warnings: list[str] | None = None) -> dict:
    latex_parts = []
    numeric_parts = []
    for item in items:
        try:
            latex_parts.append(sympy_latex(item))
        except Exception:
            latex_parts.append(str(item))
        try:
            numeric_parts.append(float(item.evalf()))
        except Exception:
            numeric_parts.append(None)
    return {
        'success': True,
        'result_latex': r'\left\{' + ', '.join(latex_parts) + r'\right\}',
        'result_numeric': numeric_parts,
        'error': None,
        'warnings': warnings or [],
    }


def _ok_array(arr: np.ndarray, warnings: list[str] | None = None) -> dict:
    return {
        'success': True,
        'result_latex': None,
        'result_numeric': arr.tolist(),
        'error': None,
        'warnings': warnings or [],
    }


def _ok_scalar(val: float, warnings: list[str] | None = None) -> dict:
    return {
        'success': True,
        'result_latex': sympy_latex(sympy.Float(val)),
        'result_numeric': val,
        'error': None,
        'warnings': warnings or [],
    }


def _error(message: str, warnings: list[str] | None = None) -> dict:
    return {
        'success': False,
        'result_latex': None,
        'result_numeric': None,
        'error': message,
        'warnings': warnings or [],
    }
