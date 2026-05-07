"""
Equation seed data.

Each entry creates an EquationDefinition row at server boot if no row with
the same name exists. The definitions are simple, low-volume smoke-test cases
covering each operation type so a developer can:

  1. Open the Equations page in the frontend.
  2. Pick one of the seeded equations.
  3. Click "Run" to verify the executor end-to-end.

These are the SAME entities a user creates in production — there's no separate
test harness; the seeds just give us out-of-the-box examples.

Definition JSON shape (see polariApiServer/equationDefinition.py):
  {
    "latexExpression": str,
    "operationType":   str,        # see polariNoCode/equation_executor.OPERATION_TYPES
    "variableBindings": list,      # each: { "symbol": str, "source": { type, ... } }
    "bounds":          dict | None,
    "options":         dict,
    "resultSpec":      { "type": "scalar" | "expression" | "dataseries" }
  }
"""

import json


def _eq(name, description, latex, operation_type, *, bounds=None, options=None, bindings=None, result_spec=None):
    return {
        'name': name,
        'description': description,
        'source_class': '',
        'definition': json.dumps({
            'latexExpression': latex,
            'operationType': operation_type,
            'variableBindings': bindings or [],
            'bounds': bounds,
            'options': options or {},
            'resultSpec': result_spec or {'type': 'expression'},
        }),
    }


SEED_EQUATIONS = [
    _eq(
        'Smoke.Derivative.Polynomial',
        'Derivative of `x^2` with respect to `x`. Expected raw LaTeX: `2 x`. '
        'Smallest possible symbolic derivative — sanity check.',
        latex=r'x^2',
        operation_type='derivative',
        bounds={'variable': 'x'},
        result_spec={'type': 'expression'},
    ),
    _eq(
        'Smoke.Derivative.SinComposed',
        'Derivative of `\\sin(x^2)` with respect to `x` — exercises chain rule. '
        'Expected raw LaTeX: `2 x \\cos{\\left(x^{2} \\right)}`.',
        latex=r'\sin(x^2)',
        operation_type='derivative',
        bounds={'variable': 'x'},
        result_spec={'type': 'expression'},
    ),
    _eq(
        'Smoke.IntegralIndefinite.Polynomial',
        'Indefinite integral of `x` with respect to `x`. '
        'Expected raw LaTeX: `\\frac{x^{2}}{2}` — i.e. x²/2.',
        latex=r'x',
        operation_type='integral_indefinite',
        bounds={'variable': 'x'},
        result_spec={'type': 'expression'},
    ),
    _eq(
        'Smoke.IntegralIndefinite.MultiVarWrtY',
        'Indefinite integral of `x + y` with respect to `y` (NOT `x`). '
        'Expected raw LaTeX: `x y + \\frac{y^{2}}{2}` — i.e. xy + y²/2. '
        'This seed verifies the variable-of-operation actually flows through; '
        'if it failed and integrated wrt x you\'d get `\\frac{x^{2}}{2} + x y`.',
        latex=r'x + y',
        operation_type='integral_indefinite',
        bounds={'variable': 'y'},
        result_spec={'type': 'expression'},
    ),
    _eq(
        'Smoke.Derivative.PartialWrtY',
        'Partial derivative of `x^{2} y^{3}` with respect to `y` (treating x as constant). '
        'Expected raw LaTeX: `3 x^{2} y^{2}`.',
        latex=r'x^{2} y^{3}',
        operation_type='derivative',
        bounds={'variable': 'y'},
        result_spec={'type': 'expression'},
    ),
    _eq(
        'Smoke.Solve.LinearForY',
        'Solve `a y - b = 0` for `y`. Expected raw LaTeX: `\\frac{b}{a}` — i.e. y = b/a. '
        'Verifies that `solve` honors the user-chosen variable when multiple symbols are present.',
        latex=r'a y - b',
        operation_type='solve',
        bounds={'variable': 'y'},
        result_spec={'type': 'expression'},
    ),
    _eq(
        'Smoke.IntegralDefinite.MultiVarWrtX',
        'Definite integral of `x + y` from `0` to `1` with respect to `x` (y treated as constant). '
        'Expected raw LaTeX: `y + \\frac{1}{2}` — i.e. y + ½.',
        latex=r'x + y',
        operation_type='integral_definite',
        bounds={'variable': 'x', 'lower': '0', 'upper': '1'},
        result_spec={'type': 'expression'},
    ),
    _eq(
        'Smoke.IntegralDefinite.Sin',
        'Definite integral of `\\sin(x)` from `0` to `\\pi`. '
        'Expected raw LaTeX: `2` (numeric scalar). Classic textbook result.',
        latex=r'\sin(x)',
        operation_type='integral_definite',
        bounds={'variable': 'x', 'lower': '0', 'upper': r'\pi'},
        result_spec={'type': 'scalar'},
    ),
    _eq(
        'Smoke.Solve.Quadratic',
        'Solve `x^2 - 4 = 0` for `x`. Expected raw LaTeX: `\\left\\{-2, 2\\right\\}` '
        'rendered as the set {-2, 2}.',
        latex=r'x^2 - 4',
        operation_type='solve',
        bounds={'variable': 'x'},
        result_spec={'type': 'expression'},
    ),
    _eq(
        'Smoke.Limit.SincAtZero',
        'Limit of `\\sin(x)/x` as `x \\to 0`. Expected raw LaTeX: `1` (numeric scalar). '
        'Famous indeterminate-form sanity check.',
        latex=r'\frac{\sin(x)}{x}',
        operation_type='limit',
        bounds={'variable': 'x', 'point': '0'},
        result_spec={'type': 'scalar'},
    ),
    _eq(
        'Smoke.Series.ExpAroundZero',
        'Taylor series of `e^x` around `x = 0` truncated to order 4. '
        'Expected raw LaTeX: `\\frac{x^{3}}{6} + \\frac{x^{2}}{2} + x + 1` '
        '(i.e. 1 + x + x²/2 + x³/6).',
        latex=r'e^x',
        operation_type='series',
        bounds={'variable': 'x', 'point': '0', 'order': 4},
        result_spec={'type': 'expression'},
    ),
    _eq(
        'Smoke.Simplify.TrigIdentity',
        'Simplify `\\sin(x)^2 + \\cos(x)^2`. Expected raw LaTeX: `1`. '
        'Pythagorean identity — exercises trig simplification.',
        latex=r'\sin(x)^2 + \cos(x)^2',
        operation_type='simplify',
        result_spec={'type': 'expression'},
    ),
    _eq(
        'Smoke.Evaluate.LinearAtPoint',
        'Evaluate `3 x + 5` with the binding `x = 2`. Expected result_numeric: `11.0`. '
        'Verifies literal variable bindings flow through and `evalf()` produces a real number.',
        latex=r'3 x + 5',
        operation_type='evaluate',
        bindings=[{'symbol': 'x', 'source': {'type': 'literal', 'value': 2}}],
        result_spec={'type': 'scalar'},
    ),
    _eq(
        'Smoke.ODE.ExponentialGrowth',
        "Solve the ODE `y'(x) - y(x) = 0` for `y(x)`. Expected raw LaTeX: "
        "`y(x) = C_{1} e^{x}` (general solution with a free constant). "
        "Note: SymPy's parse_latex requires explicit `y'(x)` notation, NOT `dy/dx`.",
        latex=r"y'(x) - y(x)",
        operation_type='ode_solve',
        options={'function': 'y(x)', 'variable': 'x'},
        result_spec={'type': 'expression'},
    ),
    _eq(
        'Smoke.DataseriesIntegral.Trapezoidal',
        'Trapezoidal integral of `[0, 1, 4, 9]` (y = x² sampled at x ∈ {0,1,2,3}). '
        'Expected result_numeric: `9.5` (true value `\\int_0^3 x^2 dx = 9`; trapezoidal '
        'overshoots a convex function). Override the `data` binding at run time '
        'to feed real values into this equation.',
        latex='',
        operation_type='dataseries_integral',
        bindings=[
            {'symbol': 'data', 'source': {'type': 'literal', 'value': [0, 1, 4, 9]}},
        ],
        options={'dataseries': 'data', 'method': 'trapezoidal'},
        result_spec={'type': 'scalar'},
    ),
    _eq(
        'Smoke.Predicate.GreaterThan',
        'Evaluate the predicate `x > 0` with `x = 5`. Expected result_numeric: '
        '`true` (Python boolean, NOT 1). Verifies boolean serialization.',
        latex=r'x > 0',
        operation_type='evaluate_predicate',
        bindings=[{'symbol': 'x', 'source': {'type': 'literal', 'value': 5}}],
        result_spec={'type': 'scalar'},
    ),
    _eq(
        'Smoke.Predicate.LessThanFalse',
        'Evaluate the predicate `x < 0` with `x = 5`. Expected result_numeric: '
        '`false` (Python boolean). Companion to GreaterThan; verifies the false case.',
        latex=r'x < 0',
        operation_type='evaluate_predicate',
        bindings=[{'symbol': 'x', 'source': {'type': 'literal', 'value': 5}}],
        result_spec={'type': 'scalar'},
    ),
    _eq(
        'Smoke.Identity.Pythagorean',
        'Identity check: does `\\sin(x)^2 + \\cos(x)^2 = 1` hold for all `x`? '
        'Expected result_numeric: `true`. Pythagorean identity — should always be True. '
        'Verifies SymPy can simplify the LHS - RHS difference to zero.',
        latex=r'\sin(x)^2 + \cos(x)^2 = 1',
        operation_type='is_identity',
        result_spec={'type': 'scalar'},
    ),
    _eq(
        'Smoke.Piecewise.AbsoluteValue',
        'Piecewise definition of `abs(x)` evaluated at `x = -3`. Expected '
        'result_numeric: `3.0`, raw LaTeX: `3`. The `x < 0` branch matches '
        'so the result is `-(-3) = 3`. Exercises the custom `\\begin{cases}` '
        'parser — SymPy parse_latex doesn\'t support that environment natively.',
        latex=r'\begin{cases} x & x \geq 0 \\ -x & \text{otherwise} \end{cases}',
        operation_type='piecewise_evaluate',
        bindings=[{'symbol': 'x', 'source': {'type': 'literal', 'value': -3}}],
        result_spec={'type': 'scalar'},
    ),
    _eq(
        'Smoke.DataseriesDerivative.QuadraticGrid',
        'Numerical derivative (`np.gradient`) of `y = [0,1,4,9,16]` sampled on '
        '`x = [0,1,2,3,4]`. Expected result_numeric: approximately `[1, 2, 4, 6, 7]`. '
        'True derivative of y = x² is `2x`, so the central-difference estimates '
        'should converge to `[~1, 2, 4, 6, ~7]`.',
        latex='',
        operation_type='dataseries_derivative',
        bindings=[
            {'symbol': 'data', 'source': {'type': 'literal', 'value': [0, 1, 4, 9, 16]}},
            {'symbol': 'x', 'source': {'type': 'literal', 'value': [0, 1, 2, 3, 4]}},
        ],
        options={'dataseries': 'data'},
        result_spec={'type': 'dataseries'},
    ),
]
