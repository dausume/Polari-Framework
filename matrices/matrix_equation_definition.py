from objectTreeDecorators import treeObject, treeObjectInit


class MatrixEquationDefinition(treeObject):
    """
    A matrix-level equation/operation — the "matrices + LaTeX" entity, distinct
    from `MatrixDefinition` (which is now strictly an isolated matrix).

    A matrix equation applies an operation to operands that may themselves be
    isolated matrices, OTHER matrix equations, or scalar EquationDefinitions
    (plus literal scalars). Evaluated by `matrices.matrix_equation_executor`,
    which guards against recursive operand references.

    Fields
    ------
    name : str            Unique identity (referenceable by other equations).
    description : str
    latex : str           Display form, rendered with KaTeX (e.g. ``A B + C``,
                          ``A^{-1}``, ``A^{\\top}``). For show only — `operation`
                          drives evaluation.
    operation_json : str  The math to perform. Shapes:
        {"kind": "matmul"|"add"|"subtract"|"hadamard"|"kron"|"solve",
         "a": "<sym>", "b": "<sym>"}
        {"kind": "transpose"|"inverse"|"determinant"|"trace", "a": "<sym>"}
        {"kind": "scalar_mul", "scalar": "<sym>", "a": "<sym>"}
        {"kind": "power", "a": "<sym>", "n": "<sym>"}
        {"kind": "elementwise", "a": "<sym>", "symbol": "x",
         "equationRef": "<name>" | "latex": "x^2"}
        {"kind": "expr", "expr": "A @ B + C"}   # advanced numpy expression
    operands_json : str   Map ``symbol -> operand spec``. Each spec:
        {"kind": "matrix", "ref": "<MatrixDefinition name>"}
        {"kind": "matrixEquation", "ref": "<MatrixEquationDefinition name>"}
        {"kind": "equation", "ref": "<EquationDefinition name>"}  # → scalar
        {"kind": "scalar", "value": <number>}
    tags : str            Comma-separated freeform tags.
    """

    @treeObjectInit
    def __init__(
        self,
        name='',
        description='',
        latex='',
        operation_json='{"kind": "matmul", "a": "A", "b": "B"}',
        operands_json='{}',
        tags='',
        manager=None,
    ):
        self.name = name
        self.description = description
        self.latex = latex
        self.operation_json = operation_json
        self.operands_json = operands_json
        self.tags = tags
