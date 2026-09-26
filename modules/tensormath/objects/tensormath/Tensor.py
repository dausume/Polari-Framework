"""
@module tensormath.objects.tensormath.Tensor

Row class Tensor of the tensormath module — one class per file. The class docstring is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit


class Tensor(treeObject):
    """AN ARBITRARY-RANK TENSOR, possibly UNINTERPRETED (plan §10). Unknown semantics on every axis is a VALID tensor.

    Values are never stored here: `storage_kind` says where they live — `matrix` = a rank-N MatrixDefinition row
    (the small case; JSON values, numpy at runtime), `dataset` = a DigitizedDataset / file, `engine` = a live engine
    state (the FEM stress tensors, the meso gyration tensor, a sim state field), `claim` = PropertyClaim.value_json.
    No element-count threshold (D2): storage follows representation and persistence need."""

    plain_words = ('A tensor here is a block of numbers with any number of axes, described by reference: the numbers '
                   'themselves stay wherever they already live (a matrix row, a dataset, a simulation state) and this row '
                   'just says what they are and how they are laid out.')

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        description: str = '',
        rank: int = 0,
        shape_json: str = '[]',
        dtype: str = 'float',
        dimensions_json: str = '[]',
        units: str = '',
        semantics: str = 'unknown',
        storage_kind: str = 'matrix',
        storage_ref: str = '',
        metadata_json: str = '{}',
        tags: str = '',
        manager=None,
    ):
        self.name = name
        self.description = description
        self.rank = rank  # number of axes
        self.shape_json = shape_json  # JSON list of axis sizes
        self.dtype = dtype  # float | int | complex | bool
        self.dimensions_json = dimensions_json  # JSON [{name, size, unit, semantics}] — semantics "unknown" is valid
        self.units = units  # units of the VALUES (per-axis units live in dimensions_json)
        self.semantics = semantics  # what the tensor means, in words; unknown is valid
        self.storage_kind = storage_kind  # matrix | dataset | engine | claim
        self.storage_ref = storage_ref  # the MatrixDefinition / DigitizedDataset / engine state / PropertyClaim name
        self.metadata_json = metadata_json  # anything else, JSON
        self.tags = tags
