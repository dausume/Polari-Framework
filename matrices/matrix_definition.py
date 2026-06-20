from objectTreeDecorators import treeObject, treeObjectInit


class MatrixDefinition(treeObject):
    """
    A named, reusable matrix/tensor — the math-logic analogue of
    EquationDefinition. Mirrors that class's persistence pattern (a
    treeObject registered in `defClassList`, generic CRUD for free), and
    is evaluated to a concrete NumPy array by `matrices.matrix_executor`.

    Fields
    ------
    name : str
        Unique identity (referenced by other matrices / sim fields).
    description : str
    shape_json : str
        Row-major dimensions, e.g. ``"[3, 3]"`` (3×3), ``"[4]"`` (vector),
        ``"[2, 3, 4]"`` (rank-3 tensor). For ``element_type == "matrix"``
        this is the BLOCK layout (the outer grid of sub-matrices), not the
        composed shape.
    element_type : str
        What each element is:
          - ``"float" | "int" | "complex"`` — a numeric literal
          - ``"equation"`` — an EquationDefinition (or inline LaTeX) that
            resolves to a scalar per element
          - ``"matrix"`` — another MatrixDefinition (matrix-of-matrices /
            block composition)
    element_matrix_ref : str
        Default sub-matrix name when ``element_type == "matrix"`` and a
        cell doesn't name its own. Optional.
    values_json : str
        Flat, row-major list of the elements — interpretation depends on
        ``element_type``:
          - numeric types: ``[1, 0, 0, 1]``
          - ``"equation"``: ``[{"equationRef": "...", "operationType": "evaluate",
            "bindings": {"x": 2}} | {"latex": "x^2", ...}, ...]``
          - ``"matrix"``: ``["blockA", {"matrixRef": "blockB"}, ...]``
        Ignored when ``computation_json.kind`` is ``"elementwise"`` or
        ``"matrix_op"`` (the result is computed, not stored).
    computation_json : str
        How the matrix is produced:
          - ``{"kind": "literal"}`` (default) — elements come from values_json
          - ``{"kind": "elementwise", "equationRef": "...", "operationType":
            "evaluate", "bindings": {"<symbol>": "<matrixRef>" | <scalar>}}``
            — one equation applied elementwise across binding matrices;
            result shape follows the (shape-agreeing) binding matrices.
          - ``{"kind": "matrix_op", "expr": "A @ B + C", "operands":
            {"A": "<matrixRef>", "B": "<matrixRef>", ...}}`` — a restricted
            NumPy matrix expression over referenced matrices.
    is_template : bool
        True for shape-only stubs (no values) used as type declarations.
    tags : str
        Comma-separated freeform tags.
    """

    @treeObjectInit
    def __init__(
        self,
        name='',
        description='',
        shape_json='[]',
        element_type='float',
        element_matrix_ref='',
        values_json='[]',
        computation_json='{"kind": "literal"}',
        is_template=False,
        tags='',
        manager=None,
    ):
        self.name = name
        self.description = description
        self.shape_json = shape_json
        self.element_type = element_type
        self.element_matrix_ref = element_matrix_ref
        self.values_json = values_json
        self.computation_json = computation_json
        self.is_template = is_template
        self.tags = tags
