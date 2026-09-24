"""
@module tensormath.tensormath_seed

Nothing is seeded but the classes: a Tensor is made over real values (tt-1). The seed pairs exist so the
tables are created and CRUDE is wired.
"""
from tensormath.tensormath_basis import (Tensor, TensorDimension, TensorMathExpression, TensorOperator,
                                         ComputeImplementation, TensorDecomposition)

TENSORMATH_SEED_PAIRS = [
    ('Tensor', Tensor, []), ('TensorDimension', TensorDimension, []), ('TensorMathExpression', TensorMathExpression, []),
    ('TensorOperator', TensorOperator, []), ('ComputeImplementation', ComputeImplementation, []),
    ('TensorDecomposition', TensorDecomposition, []),
]
