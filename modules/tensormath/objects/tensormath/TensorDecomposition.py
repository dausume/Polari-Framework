"""
@module tensormath.objects.tensormath.TensorDecomposition

Row class TensorDecomposition of the tensormath module — one class per file. The class docstring is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit


class TensorDecomposition(treeObject):
    """A DECOMPOSITION RESULT (plan §17 D): T ≈ Σ_r A_ir B_jr C_kr and the like, with the information it lost — `reconstruction_error` = ‖T − T̂‖ / ‖T‖ (plan §F6.3)."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        description: str = '',
        tensor: str = '',
        method: str = 'cp',
        rank: int = 0,
        factors_json: str = '[]',
        reconstruction_error: float = 0.0,
        error_method: str = 'frobenius-relative',
        mapping_status: str = 'proposed',
        evidence_level: str = 'none',
        evidence_ref: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.description = description
        self.tensor = tensor  # Tensor.name
        self.method = method  # cp | tucker | svd | custom
        self.rank = rank  # the decomposition rank r
        self.factors_json = factors_json  # JSON list of factor Tensor names
        self.reconstruction_error = reconstruction_error  # ‖T − T̂‖ / ‖T‖
        self.error_method = error_method
        self.mapping_status = mapping_status
        self.evidence_level = evidence_level
        self.evidence_ref = evidence_ref
        self.notes = notes
