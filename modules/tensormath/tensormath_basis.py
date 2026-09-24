"""
@module tensormath.tensormath_basis

The INDEX of the tensormath rows: classes live one-per-file under objects/tensormath/; this file re-exports them
and holds the class list the server registers.

Arbitrary-rank tensors as rows (values by reference: a rank-N MatrixDefinition, a DigitizedDataset,
a live engine state or a PropertyClaim), named dimensions, tensor expressions and operators, and the
compute implementations an operator has — the bridge TensorOperator → ComputeImplementation →
ComputeLOD (plan §F8).
"""
from tensormath.objects.tensormath.Tensor import Tensor  # noqa: F401
from tensormath.objects.tensormath.TensorDimension import TensorDimension  # noqa: F401
from tensormath.objects.tensormath.TensorMathExpression import TensorMathExpression  # noqa: F401
from tensormath.objects.tensormath.TensorOperator import TensorOperator  # noqa: F401
from tensormath.objects.tensormath.ComputeImplementation import ComputeImplementation  # noqa: F401
from tensormath.objects.tensormath.TensorDecomposition import TensorDecomposition  # noqa: F401
from tensormath.objects.tensormath.FEMFieldState import FEMFieldState  # noqa: F401

#: every row class of the module, in registration order (the selftest asserts the count)
TENSORMATH_CLASSES = [Tensor, TensorDimension, TensorMathExpression, TensorOperator, ComputeImplementation, TensorDecomposition, FEMFieldState]
