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
        'd/dx of x^2 → 2x. Smallest possible symbolic derivative.',
        latex=r'x^2',
        operation_type='derivative',
        options={'variable': 'x'},
        result_spec={'type': 'expression'},
    ),
    _eq(
        'Smoke.Derivative.SinComposed',
        'd/dx of sin(x^2) → 2x cos(x^2). Chain rule.',
        latex=r'\sin(x^2)',
        operation_type='derivative',
        options={'variable': 'x'},
        result_spec={'type': 'expression'},
    ),
    _eq(
        'Smoke.IntegralIndefinite.Polynomial',
        'Indefinite integral of x → x^2/2.',
        latex=r'x',
        operation_type='integral_indefinite',
        options={'variable': 'x'},
        result_spec={'type': 'expression'},
    ),
    _eq(
        'Smoke.IntegralDefinite.Sin',
        'Definite integral of sin(x) on [0, π] → 2.',
        latex=r'\sin(x)',
        operation_type='integral_definite',
        bounds={'variable': 'x', 'lower': '0', 'upper': r'\pi'},
        result_spec={'type': 'scalar'},
    ),
    _eq(
        'Smoke.Solve.Quadratic',
        'Solve x^2 - 4 = 0 → {-2, 2}.',
        latex=r'x^2 - 4',
        operation_type='solve',
        options={'variable': 'x'},
        result_spec={'type': 'expression'},
    ),
    _eq(
        'Smoke.Limit.SincAtZero',
        'lim x→0 of sin(x)/x → 1.',
        latex=r'\frac{\sin(x)}{x}',
        operation_type='limit',
        bounds={'variable': 'x', 'point': '0'},
        result_spec={'type': 'scalar'},
    ),
    _eq(
        'Smoke.Series.ExpAroundZero',
        'Taylor series of e^x around 0 to order 4.',
        latex=r'e^x',
        operation_type='series',
        bounds={'variable': 'x', 'point': '0', 'order': 4},
        result_spec={'type': 'expression'},
    ),
    _eq(
        'Smoke.Simplify.TrigIdentity',
        'Simplify sin(x)^2 + cos(x)^2 → 1.',
        latex=r'\sin(x)^2 + \cos(x)^2',
        operation_type='simplify',
        result_spec={'type': 'expression'},
    ),
    _eq(
        'Smoke.Evaluate.LinearAtPoint',
        'Evaluate 3x + 5 at x = 2 → 11.',
        latex=r'3 x + 5',
        operation_type='evaluate',
        bindings=[{'symbol': 'x', 'source': {'type': 'literal', 'value': 2}}],
        result_spec={'type': 'scalar'},
    ),
    _eq(
        'Smoke.ODE.ExponentialGrowth',
        "Solve dy/dx = y → y(x) = C·e^x. Note: SymPy's parse_latex requires "
        "explicit derivative notation; LaTeX uses y'(x) - y(x) = 0 form.",
        latex=r"y'(x) - y(x)",
        operation_type='ode_solve',
        options={'function': 'y(x)', 'variable': 'x'},
        result_spec={'type': 'expression'},
    ),
    _eq(
        'Smoke.DataseriesIntegral.Trapezoidal',
        'Trapezoidal integral of [0, 1, 4, 9] (i.e. y=x^2 sampled at x=0,1,2,3) '
        '→ should be ~9.5. Override the "data" binding at run time to feed '
        'real data into this same equation.',
        latex='',
        operation_type='dataseries_integral',
        bindings=[
            {'symbol': 'data', 'source': {'type': 'literal', 'value': [0, 1, 4, 9]}},
        ],
        options={'dataseries': 'data', 'method': 'trapezoidal'},
        result_spec={'type': 'scalar'},
    ),
    _eq(
        'Smoke.DataseriesDerivative.QuadraticGrid',
        'Numerical derivative (np.gradient) of y=[0,1,4,9,16] sampled on x=[0,1,2,3,4] '
        'should approximate 2x → ~[1, 2, 4, 6, 7].',
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
