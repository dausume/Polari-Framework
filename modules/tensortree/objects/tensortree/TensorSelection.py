"""
@module tensortree.objects.tensortree.TensorSelection

Row class TensorSelection of the tensortree module — one class per file. The class docstring is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit


class TensorSelection(treeObject):
    """A CLICK THAT IS A MATHEMATICAL OBJECT (plan §15): a region of a node, per dimension. VISUALIZE → SELECT → DISCOVER → MAP → VISUALIZE."""

    plain_words = ('A selection is a click made durable: the region of a view a person picked, written down as ranges of its '
                   'dimensions so that it can be reasoned about, mapped elsewhere, or turned into a claim to check.')

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        description: str = '',
        node: str = '',
        ranges_json: str = '{}',
        created_from: str = '',
        created_at: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.description = description
        self.node = node  # TensorNode.name
        self.ranges_json = ranges_json  # {dim: [lo, hi]}
        self.created_from = created_from  # the display item / panel that made it
        self.created_at = created_at
        self.notes = notes
