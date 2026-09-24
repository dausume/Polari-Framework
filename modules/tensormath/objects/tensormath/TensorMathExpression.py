"""
@module tensormath.objects.tensormath.TensorMathExpression

Row class TensorMathExpression of the tensormath module — one class per file. The class docstring is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit


class TensorMathExpression(treeObject):
    """A NAMED-DIMENSION TENSOR EXPRESSION (plan §9): contraction, product, outer, permute, slice, reshape, reduce, derivative, integral, or a free expression. Delegates to a MatrixEquationDefinition when the operands are rank ≤ 2 (`matrix_equation_ref`)."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        description: str = '',
        latex: str = '',
        operation: str = 'contract',
        operands_json: str = '[]',
        dims_json: str = '[]',
        matrix_equation_ref: str = '',
        result_shape_json: str = '[]',
        tags: str = '',
        manager=None,
    ):
        self.name = name
        self.description = description
        self.latex = latex
        self.operation = operation  # contract | product | outer | permute | slice | reshape | reduce | derivative | integral | expr
        self.operands_json = operands_json  # JSON [{tensor, dims:[…]}] — the tensors and the named dims the operation touches
        self.dims_json = dims_json  # the named dims contracted / reduced / sliced
        self.matrix_equation_ref = matrix_equation_ref  # MatrixEquationDefinition.name when the whole expression is matrix algebra
        self.result_shape_json = result_shape_json
        self.tags = tags
