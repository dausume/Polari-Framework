"""
@module tensormath.objects.tensormath.TensorDimension

Row class TensorDimension of the tensormath module — one class per file. The class docstring is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit


class TensorDimension(treeObject):
    """ONE NAMED AXIS of a tensor, as a row — so a mapping or a selection can address it by name. The inline form is Tensor.dimensions_json; a row exists when the axis must be referenced."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        description: str = '',
        tensor: str = '',
        index: int = 0,
        label: str = '',
        size: int = 0,
        unit: str = '',
        kind: str = 'unknown',
        semantics: str = 'unknown',
        coordinate_ref: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.description = description
        self.tensor = tensor  # Tensor.name
        self.index = index  # axis position
        self.label = label
        self.size = size
        self.unit = unit
        self.kind = kind  # spatial | temporal | index | channel | modal | scale | unknown
        self.semantics = semantics
        self.coordinate_ref = coordinate_ref  # a coordinate/basis definition when the axis is a coordinate
        self.notes = notes
