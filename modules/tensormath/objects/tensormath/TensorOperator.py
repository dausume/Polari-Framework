"""
@module tensormath.objects.tensormath.TensorOperator

Row class TensorOperator of the tensormath module — one class per file. The class docstring is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit


class TensorOperator(treeObject):
    """A MATHEMATICAL OPERATION with a meaning, independent of how it is computed (plan §18): σ_ij = C_ijkl ε_kl is one operator; its ComputeImplementation rows say how it runs on numpy, an FPGA kernel, a future ASIC."""

    plain_words = ('An operator is the meaning of a computation, independent of how it is carried out: stress from strain is '
                   'an operator whether it runs on a laptop, a chip design or a piece of silicon.')

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        description: str = '',
        expression_ref: str = '',
        input_tensors_json: str = '[]',
        output_tensor: str = '',
        semantics: str = '',
        tags: str = '',
        manager=None,
    ):
        self.name = name
        self.description = description
        self.expression_ref = expression_ref  # TensorMathExpression.name
        self.input_tensors_json = input_tensors_json  # JSON list of Tensor names
        self.output_tensor = output_tensor  # Tensor.name
        self.semantics = semantics  # what the operation MEANS (physics), in words
        self.tags = tags
