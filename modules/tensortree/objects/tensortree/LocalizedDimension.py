"""
@module tensortree.objects.tensortree.LocalizedDimension

Row class LocalizedDimension of the tensortree module — one class per file. The class docstring is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit


class LocalizedDimension(treeObject):
    """ONE DIMENSION AS A NODE SEES IT: a range of a tensor axis and the visual channel it is bound to (plan §12, §F4). The channel vocabulary: position.x, position.y, position.z, color, opacity, size, shape, orientation, vector, label, time — with the scale INSIDE the channel config."""

    plain_words = ('A localized dimension is one axis of the data as it appears in one particular view (for example the x '
                   'position of the plate), together with the visual channel it is shown through and the range of values it '
                   'covers there.')

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        description: str = '',
        node: str = '',
        dimension: str = '',
        range_json: str = '[]',
        channel: str = '',
        scale_json: str = '{}',
        coherent: bool = False,
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.description = description
        self.node = node  # TensorNode.name
        self.dimension = dimension  # TensorDimension.name (or an axis name)
        self.range_json = range_json  # [lo, hi] in the axis unit; [] = all
        self.channel = channel  # position.x | position.y | position.z | color | opacity | size | shape | orientation | vector | label | time
        self.scale_json = scale_json  # e.g. {"kind": "continuous", "domain": [300, 900]}
        self.coherent = coherent  # set by the validator
        self.notes = notes
