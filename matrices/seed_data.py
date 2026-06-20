# Seed MatrixDefinition rows — concept tests + element-kind demos.
#
# Idempotent by name (see polariServer._seedMatrixDefinitions). References
# between matrices resolve at evaluate time, so creation order is irrelevant.

import json


def _m(name, description, shape, element_type='float', values=None,
       computation=None, element_matrix_ref='', is_template=False, tags=''):
    return {
        'name': name,
        'description': description,
        'shape_json': json.dumps(shape),
        'element_type': element_type,
        'element_matrix_ref': element_matrix_ref,
        'values_json': json.dumps(values if values is not None else []),
        'computation_json': json.dumps(computation or {'kind': 'literal'}),
        'is_template': is_template,
        'tags': tags,
    }


SEED_MATRICES = [
    # --- numeric literals ---
    _m('identity-2x2', '2×2 identity matrix.', [2, 2],
       values=[1, 0, 0, 1], tags='identity,demo'),
    _m('identity-3x3', '3×3 identity matrix (Identity concept test).', [3, 3],
       values=[1, 0, 0, 0, 1, 0, 0, 0, 1], tags='identity,demo'),
    _m('mat-a-2x2', 'A simple 2×2 block [[1,2],[3,4]].', [2, 2],
       values=[1, 2, 3, 4], tags='demo'),

    # --- matrix-of-matrices (block composition → 4×4) ---
    _m('block-4x4',
       'Block decomposition concept test: a 2×2 grid of 2×2 blocks → 4×4.',
       [2, 2], element_type='matrix',
       values=['mat-a-2x2', 'identity-2x2', 'identity-2x2', 'mat-a-2x2'],
       tags='composition,demo'),

    # --- equation-typed elements (each cell is an equation → scalar) ---
    _m('eq-elements-2x2',
       'Equation elements: each cell is x^2 with a different bound x → [[1,4],[9,16]].',
       [2, 2], element_type='equation',
       values=[
           {'latex': 'x^2', 'bindings': {'x': 1}},
           {'latex': 'x^2', 'bindings': {'x': 2}},
           {'latex': 'x^2', 'bindings': {'x': 3}},
           {'latex': 'x^2', 'bindings': {'x': 4}},
       ],
       tags='equation,demo'),

    # --- supporting matrices for the real-world composite equations below ---
    _m('design-X', 'Regression design matrix: rows [1, xᵢ] for x=1,2,3.', [3, 2],
       values=[1, 1, 1, 2, 1, 3], tags='regression,data'),
    _m('target-y', 'Regression target vector y = [1,2,3]ᵀ (perfectly linear).', [3, 1],
       values=[1, 2, 3], tags='regression,data'),
    _m('vec-v', 'Column vector v = [1,1]ᵀ.', [2, 1], values=[1, 1], tags='vector,data'),
    _m('vec-d', 'Deviation vector d = [1,2]ᵀ (x − μ).', [2, 1], values=[1, 2], tags='vector,data'),
    _m('sigma-2x2', 'Covariance matrix Σ = diag(2,3).', [2, 2],
       values=[2, 0, 0, 3], tags='covariance,data'),
    _m('kalman-P', 'Prior state covariance P = 2·I.', [2, 2],
       values=[2, 0, 0, 2], tags='kalman,data'),
    _m('rot-45', '2-D rotation by 45°.', [2, 2],
       values=[0.7071067811865476, -0.7071067811865476,
               0.7071067811865476, 0.7071067811865476], tags='rotation,data'),
]


# ---------------------------------------------------------------------------
# Matrix equations — operations over matrices/equations. Migrated here from
# the old computed MatrixDefinition kinds, plus one example per math kind.
# ---------------------------------------------------------------------------

def _eq(name, description, latex, operation, operands, tags=''):
    return {
        'name': name,
        'description': description,
        'latex': latex,
        'operation_json': json.dumps(operation),
        'operands_json': json.dumps(operands),
        'tags': tags,
    }


_MREF = lambda ref: {'kind': 'matrix', 'ref': ref}        # noqa: E731
_EQREF = lambda ref: {'kind': 'matrixEquation', 'ref': ref}  # noqa: E731
# Operands resolved from RUNTIME bindings (a bare-name string spec). Used when
# a MatrixEquationOperation no-code state supplies operand values from the
# solution context rather than referencing stored matrices.
_RUNTIME = lambda name: name  # noqa: E731
_SCALAR = lambda v: {'kind': 'scalar', 'value': v}        # noqa: E731

SEED_MATRIX_EQUATIONS = [
    _eq('a-times-identity', 'A · I → A (matrix multiply).', r'A\,I',
        {'kind': 'matmul', 'a': 'A', 'b': 'B'},
        {'A': _MREF('mat-a-2x2'), 'B': _MREF('identity-2x2')}, 'matmul,demo'),

    _eq('elementwise-square-of-a', 'Apply x² to every cell of A → [[1,4],[9,16]].',
        r'A_{ij}^{2}',
        {'kind': 'elementwise', 'a': 'A', 'symbol': 'x', 'latex': 'x^2'},
        {'A': _MREF('mat-a-2x2')}, 'elementwise,demo'),

    _eq('a-plus-a', 'A + A → 2A.', r'A + A',
        {'kind': 'add', 'a': 'A', 'b': 'B'},
        {'A': _MREF('mat-a-2x2'), 'B': _MREF('mat-a-2x2')}, 'add,demo'),

    _eq('a-minus-identity', 'A − I.', r'A - I',
        {'kind': 'subtract', 'a': 'A', 'b': 'B'},
        {'A': _MREF('mat-a-2x2'), 'B': _MREF('identity-2x2')}, 'subtract,demo'),

    _eq('two-times-a', '2 · A (scalar multiply).', r'2A',
        {'kind': 'scalar_mul', 'scalar': 'c', 'a': 'A'},
        {'c': _SCALAR(2), 'A': _MREF('mat-a-2x2')}, 'scalar_mul,demo'),

    _eq('a-transpose', 'Aᵀ (transpose).', r'A^{\top}',
        {'kind': 'transpose', 'a': 'A'},
        {'A': _MREF('mat-a-2x2')}, 'transpose,demo'),

    _eq('a-inverse', 'A⁻¹ (inverse).', r'A^{-1}',
        {'kind': 'inverse', 'a': 'A'},
        {'A': _MREF('mat-a-2x2')}, 'inverse,demo'),

    _eq('a-determinant', 'det(A) → scalar.', r'\det(A)',
        {'kind': 'determinant', 'a': 'A'},
        {'A': _MREF('mat-a-2x2')}, 'determinant,demo'),

    _eq('a-trace', 'tr(A) → scalar.', r'\operatorname{tr}(A)',
        {'kind': 'trace', 'a': 'A'},
        {'A': _MREF('mat-a-2x2')}, 'trace,demo'),

    _eq('a-squared', 'A² (matrix power).', r'A^{2}',
        {'kind': 'power', 'a': 'A', 'n': 'n'},
        {'A': _MREF('mat-a-2x2'), 'n': _SCALAR(2)}, 'power,demo'),

    _eq('a-kron-identity', 'A ⊗ I (Kronecker product) → 4×4.', r'A \otimes I',
        {'kind': 'kron', 'a': 'A', 'b': 'B'},
        {'A': _MREF('mat-a-2x2'), 'B': _MREF('identity-2x2')}, 'kron,demo'),

    _eq('a-hadamard-a', 'A ∘ A (elementwise product).', r'A \circ A',
        {'kind': 'hadamard', 'a': 'A', 'b': 'B'},
        {'A': _MREF('mat-a-2x2'), 'B': _MREF('mat-a-2x2')}, 'hadamard,demo'),

    # References ANOTHER matrix equation (a-transpose) → AᵀA. Demonstrates
    # equation-of-equation composition with cycle guarding.
    _eq('at-times-a', 'AᵀA — composes the a-transpose equation with A.', r'A^{\top} A',
        {'kind': 'matmul', 'a': 'T', 'b': 'A'},
        {'T': _EQREF('a-transpose'), 'A': _MREF('mat-a-2x2')}, 'matmul,compose,demo'),

    # 2D→3D plane embedding — invoked from the pendulum step solution via a
    # MatrixEquationOperation no-code state. Operands x, y, n, Yup are bound
    # at runtime from the solution context (note the bare-name specs). Given
    # a horizontal normal n, world = x·normalize(Yup×n) + y·Yup places the
    # 2D swing into a vertical plane in 3D.
    _eq('pendulum-embed',
        '2D→3D plane embedding: world = x·normalize(Yup×n) + y·Yup. Used by '
        'the pendulum step solution to compute the bob/string 3D position '
        'from the 2D (x, y) and the swing-plane normal.',
        r'\mathbf{w} = x\,\widehat{\mathbf{Yup}\times\mathbf{n}} + y\,\mathbf{Yup}',
        {'kind': 'expr', 'expr': 'x * normalize(cross(Yup, n)) + y * Yup'},
        {'x': _RUNTIME('x'), 'y': _RUNTIME('y'),
         'n': _RUNTIME('n'), 'Yup': _RUNTIME('Yup')},
        'embedding,pendulum,vector'),

    # ----------------------------------------------------------------------
    # Composite, real-world matrix equations (expression form).
    # ----------------------------------------------------------------------

    # Ordinary least squares — the workhorse of linear regression.
    _eq('ols-regression-beta',
        'Ordinary least squares: regression coefficients β = (XᵀX)⁻¹Xᵀy. '
        'Fits a line to (X, y); here β = [intercept, slope] = [0, 1].',
        r'\hat{\boldsymbol\beta} = (\mathbf{X}^{\top}\mathbf{X})^{-1}\mathbf{X}^{\top}\mathbf{y}',
        {'kind': 'expr', 'expr': 'inv(T(X) @ X) @ T(X) @ y'},
        {'X': _MREF('design-X'), 'y': _MREF('target-y')}, 'regression,ols,composite'),

    # Hat / projection matrix — maps observations to fitted values.
    _eq('hat-matrix',
        'Regression hat matrix H = X(XᵀX)⁻¹Xᵀ. Projects y onto the column space '
        'of X; its diagonal gives the leverages. Idempotent (H² = H).',
        r'\mathbf{H} = \mathbf{X}(\mathbf{X}^{\top}\mathbf{X})^{-1}\mathbf{X}^{\top}',
        {'kind': 'expr', 'expr': 'X @ inv(T(X) @ X) @ T(X)'},
        {'X': _MREF('design-X')}, 'regression,projection,composite'),

    # Fitted values — composes the hat-matrix EQUATION with y (equation-of-equation).
    _eq('regression-fitted-values',
        'Fitted values ŷ = H·y, composing the hat-matrix equation with the '
        'target. Equals y here since the data is perfectly linear.',
        r'\hat{\mathbf{y}} = \mathbf{H}\,\mathbf{y}',
        {'kind': 'matmul', 'a': 'H', 'b': 'y'},
        {'H': _EQREF('hat-matrix'), 'y': _MREF('target-y')}, 'regression,compose,composite'),

    # Gram matrix / normal-equations LHS.
    _eq('gram-matrix',
        'Gram matrix G = XᵀX — the left-hand side of the normal equations; '
        'also the (uncentered) scatter matrix.',
        r'\mathbf{G} = \mathbf{X}^{\top}\mathbf{X}',
        {'kind': 'expr', 'expr': 'T(X) @ X'},
        {'X': _MREF('design-X')}, 'regression,statistics,composite'),

    # Sample covariance scaling (uncentered): 1/(n-1) · XᵀX.
    _eq('covariance-scaled',
        'Scaled scatter matrix s·XᵀX with s = 1/(n−1) = 0.5 — the shape of an '
        '(uncentered) sample covariance.',
        r'\mathbf{S} = \tfrac{1}{n-1}\,\mathbf{X}^{\top}\mathbf{X}',
        {'kind': 'expr', 'expr': 's * (T(X) @ X)'},
        {'s': _SCALAR(0.5), 'X': _MREF('design-X')}, 'statistics,covariance,composite'),

    # Quadratic form xᵀAx — energy, variance, optimization objectives.
    _eq('quadratic-form',
        'Quadratic form vᵀAv → scalar. Appears in energy, variance, and the '
        'objective of quadratic programs. Here = 10.',
        r'q = \mathbf{v}^{\top}\mathbf{A}\,\mathbf{v}',
        {'kind': 'expr', 'expr': 'T(v) @ A @ v'},
        {'v': _MREF('vec-v'), 'A': _MREF('mat-a-2x2')}, 'quadratic,optimization,composite'),

    # Mahalanobis distance² — anomaly detection / clustering distance.
    _eq('mahalanobis-sq',
        'Squared Mahalanobis distance dᵀΣ⁻¹d — scale-aware distance used in '
        'anomaly detection and clustering. Here = 11/6 ≈ 1.833.',
        r'D^2 = \mathbf{d}^{\top}\boldsymbol\Sigma^{-1}\mathbf{d}',
        {'kind': 'expr', 'expr': 'T(d) @ inv(S) @ d'},
        {'d': _MREF('vec-d'), 'S': _MREF('sigma-2x2')}, 'statistics,distance,composite'),

    # Schur complement — block elimination, control, Gaussian conditioning.
    _eq('schur-complement',
        'Schur complement A − BD⁻¹C. Central to block-matrix elimination, '
        'control theory, and conditioning a Gaussian.',
        r'\mathbf{A} - \mathbf{B}\mathbf{D}^{-1}\mathbf{C}',
        {'kind': 'expr', 'expr': 'A - B @ inv(D) @ C'},
        {'A': _MREF('mat-a-2x2'), 'B': _MREF('identity-2x2'),
         'C': _MREF('identity-2x2'), 'D': _MREF('mat-a-2x2')}, 'control,blocks,composite'),

    # Kalman gain — the heart of the Kalman filter update.
    _eq('kalman-gain',
        'Kalman gain K = PHᵀ(HPHᵀ + R)⁻¹ — weights the measurement vs. the '
        'prediction in a Kalman filter update. Here = (2/3)·I.',
        r'\mathbf{K} = \mathbf{P}\mathbf{H}^{\top}(\mathbf{H}\mathbf{P}\mathbf{H}^{\top} + \mathbf{R})^{-1}',
        {'kind': 'expr', 'expr': 'P @ T(H) @ inv(H @ P @ T(H) + R)'},
        {'P': _MREF('kalman-P'), 'H': _MREF('identity-2x2'), 'R': _MREF('identity-2x2')},
        'kalman,control,composite'),

    # Composition of two rotations — graphics / robotics.
    _eq('rotation-compose',
        'Composing two 45° rotations R₁R₂ = R(90°). Sequencing transforms in '
        'graphics and robotics.',
        r'\mathbf{R}_1\mathbf{R}_2',
        {'kind': 'matmul', 'a': 'R1', 'b': 'R2'},
        {'R1': _MREF('rot-45'), 'R2': _MREF('rot-45')}, 'graphics,rotation,composite'),
]
