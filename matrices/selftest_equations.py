"""
Standalone self-test for the matrix-equation executor — no server, no sudo.

Run from polari-framework/:
    python3 -m matrices.selftest_equations

Loads the seeded MatrixDefinitions + MatrixEquationDefinitions into a fake
manager and asserts every matrix-math kind, equation-of-equation composition,
and recursive-reference detection.
"""

from types import SimpleNamespace

import numpy as np

from matrices.matrix_equation_executor import evaluate_equation, validate_equation, MatrixEvalError
from matrices.seed_data import SEED_MATRICES, SEED_MATRIX_EQUATIONS


class FakeManager:
    def __init__(self):
        self.objectTables = {
            'MatrixDefinition': {},
            'MatrixEquationDefinition': {},
            'EquationDefinition': {},
        }


def _mgr():
    m = FakeManager()
    for s in SEED_MATRICES:
        m.objectTables['MatrixDefinition'][s['name']] = SimpleNamespace(**s)
    for s in SEED_MATRIX_EQUATIONS:
        m.objectTables['MatrixEquationDefinition'][s['name']] = SimpleNamespace(**s)
    return m


PASS, FAIL = '\033[0;32mPASS\033[0m', '\033[0;31mFAIL\033[0m'
results = []


def check(label, got, expected):
    try:
        ok = np.allclose(np.asarray(got, dtype=complex), np.asarray(expected, dtype=complex))
    except Exception as e:
        ok, got = False, f'<error: {e}>'
    results.append(ok)
    print(f'  [{PASS if ok else FAIL}] {label}')
    if not ok:
        print(f'        expected: {np.asarray(expected)}')
        print(f'        got:      {np.asarray(got)}')


def by_name(mgr, name):
    return evaluate_equation(mgr.objectTables['MatrixEquationDefinition'][name], manager=mgr)


def main():
    mgr = _mgr()
    A = np.array([[1, 2], [3, 4]])
    I = np.eye(2)
    print('Matrix-equation executor self-test\n')

    check('matmul  A·I = A',        by_name(mgr, 'a-times-identity'), A)
    check('elementwise x²',         by_name(mgr, 'elementwise-square-of-a'), [[1, 4], [9, 16]])
    check('add     A+A',            by_name(mgr, 'a-plus-a'), A + A)
    check('subtract A−I',           by_name(mgr, 'a-minus-identity'), A - I)
    check('scalar  2A',             by_name(mgr, 'two-times-a'), 2 * A)
    check('transpose Aᵀ',           by_name(mgr, 'a-transpose'), A.T)
    check('inverse A⁻¹',            by_name(mgr, 'a-inverse'), np.linalg.inv(A))
    check('determinant det(A)',     by_name(mgr, 'a-determinant'), np.linalg.det(A))
    check('trace tr(A)',            by_name(mgr, 'a-trace'), np.trace(A))
    check('power   A²',             by_name(mgr, 'a-squared'), A @ A)
    check('kron    A⊗I',            by_name(mgr, 'a-kron-identity'), np.kron(A, I))
    check('hadamard A∘A',           by_name(mgr, 'a-hadamard-a'), A * A)
    check('compose AᵀA (eq-of-eq)', by_name(mgr, 'at-times-a'), A.T @ A)

    # advanced expr + runtime binding
    expr_def = SimpleNamespace(
        name='_expr', latex='', operation_json='{"kind":"expr","expr":"A @ B + C"}',
        operands_json='{"A":{"kind":"matrix","ref":"mat-a-2x2"},'
                      '"B":{"kind":"matrix","ref":"identity-2x2"},'
                      '"C":{"kind":"matrix","ref":"mat-a-2x2"}}', tags='')
    check('expr    A@B + C', evaluate_equation(expr_def, manager=mgr), A @ I + A)

    # scalar-equation operand (constant equation 2+3 → 5, times A)
    mgr.objectTables['EquationDefinition']['five'] = SimpleNamespace(
        name='five', definition='{"latexExpression":"2+3","operationType":"evaluate"}')
    sc_def = SimpleNamespace(
        name='_sc', latex='', operation_json='{"kind":"scalar_mul","scalar":"c","a":"A"}',
        operands_json='{"c":{"kind":"equation","ref":"five"},'
                      '"A":{"kind":"matrix","ref":"mat-a-2x2"}}', tags='')
    check('scalar-equation operand 5·A', evaluate_equation(sc_def, manager=mgr), 5 * A)

    # --- vector helpers (cross/normalize) + the 2D→3D plane embedding ---
    # world = x * normalize(cross(Yup, n)) + y * Yup  (the no-code embedding)
    def embed(xx, yy, n):
        emb = SimpleNamespace(
            name='_embed', latex='',
            operation_json='{"kind":"expr","expr":"x * normalize(cross(Yup, n)) + y * Yup"}',
            operands_json=('{"x":{"kind":"scalar","value":%r},'
                           '"y":{"kind":"scalar","value":%r},'
                           '"n":{"kind":"scalar","value":%r},'
                           '"Yup":{"kind":"scalar","value":[0,1,0]}}' % (xx, yy, list(n))),
            tags='')
        return evaluate_equation(emb, manager=mgr)
    check('embed default normal (0,0,1) → XY plane', embed(0.5, -0.866, [0, 0, 1]),
          [0.5, -0.866, 0])
    check('embed normal (1,0,0) → YZ plane', embed(0.5, -0.866, [1, 0, 0]),
          [0, -0.866, -0.5])

    # --- composite, real-world equations ---
    print()
    X = np.array([[1, 1], [1, 2], [1, 3]], dtype=float)
    y = np.array([[1], [2], [3]], dtype=float)
    v = np.array([[1], [1]], dtype=float)
    d = np.array([[1], [2]], dtype=float)
    Sig = np.array([[2, 0], [0, 3]], dtype=float)
    P = np.array([[2, 0], [0, 2]], dtype=float)
    r45 = np.array([[np.cos(np.pi / 4), -np.sin(np.pi / 4)],
                    [np.sin(np.pi / 4), np.cos(np.pi / 4)]])

    check('OLS β = (XᵀX)⁻¹Xᵀy',       by_name(mgr, 'ols-regression-beta'),
          np.linalg.inv(X.T @ X) @ X.T @ y)
    check('hat matrix X(XᵀX)⁻¹Xᵀ',    by_name(mgr, 'hat-matrix'),
          X @ np.linalg.inv(X.T @ X) @ X.T)
    check('fitted ŷ = H·y (eq-of-eq)', by_name(mgr, 'regression-fitted-values'), y)
    check('Gram XᵀX',                 by_name(mgr, 'gram-matrix'), X.T @ X)
    check('covariance 0.5·XᵀX',       by_name(mgr, 'covariance-scaled'), 0.5 * (X.T @ X))
    check('quadratic form vᵀAv',      by_name(mgr, 'quadratic-form'),
          v.T @ np.array([[1, 2], [3, 4]]) @ v)
    check('Mahalanobis dᵀΣ⁻¹d',       by_name(mgr, 'mahalanobis-sq'),
          d.T @ np.linalg.inv(Sig) @ d)
    check('Schur A − BD⁻¹C',          by_name(mgr, 'schur-complement'),
          np.array([[1, 2], [3, 4]]) - np.linalg.inv(np.array([[1, 2], [3, 4]])))
    check('Kalman gain',              by_name(mgr, 'kalman-gain'),
          P @ np.linalg.inv(P + np.eye(2)))
    check('rotation R₁R₂ = R(90°)',   by_name(mgr, 'rotation-compose'), r45 @ r45)
    print()

    # validation: good equation
    v_ok = validate_equation(mgr.objectTables['MatrixEquationDefinition']['at-times-a'], manager=mgr)
    results.append(v_ok['valid'])
    print(f"  [{PASS if v_ok['valid'] else FAIL}] validate(at-times-a) valid={v_ok['valid']}")

    # validation: missing operand
    bad = SimpleNamespace(name='_bad', latex='',
                          operation_json='{"kind":"matmul","a":"A","b":"B"}',
                          operands_json='{"A":{"kind":"matrix","ref":"mat-a-2x2"}}', tags='')
    v_bad = validate_equation(bad, manager=mgr)
    bad_caught = (not v_bad['valid']) and len(v_bad['errors']) > 0
    results.append(bad_caught)
    print(f"  [{PASS if bad_caught else FAIL}] validate(missing operand) errors={v_bad['errors']}")

    # cycle: E1 → E2 → E1
    e1 = SimpleNamespace(name='cyc-e1', latex='', operation_json='{"kind":"transpose","a":"X"}',
                         operands_json='{"X":{"kind":"matrixEquation","ref":"cyc-e2"}}', tags='')
    e2 = SimpleNamespace(name='cyc-e2', latex='', operation_json='{"kind":"transpose","a":"X"}',
                         operands_json='{"X":{"kind":"matrixEquation","ref":"cyc-e1"}}', tags='')
    mgr.objectTables['MatrixEquationDefinition']['cyc-e1'] = e1
    mgr.objectTables['MatrixEquationDefinition']['cyc-e2'] = e2
    v_cyc = validate_equation(e1, manager=mgr)
    cyc_caught = (not v_cyc['valid']) and any('recursive' in e for e in v_cyc['errors'])
    results.append(cyc_caught)
    print(f"  [{PASS if cyc_caught else FAIL}] validate detects E1→E2→E1: {v_cyc['errors']}")
    try:
        evaluate_equation(e1, manager=mgr)
        cyc_eval = False
    except MatrixEvalError:
        cyc_eval = True
    results.append(cyc_eval)
    print(f"  [{PASS if cyc_eval else FAIL}] evaluate raises on cycle")

    print()
    n = sum(1 for r in results if r)
    print(f'{n}/{len(results)} checks passed')
    return 0 if n == len(results) else 1


if __name__ == '__main__':
    import sys
    sys.exit(main())
