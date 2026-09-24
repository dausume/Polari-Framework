"""
@module tensortree.objects.tensortree.TensorTreeDefinition

Row class TensorTreeDefinition of the tensortree module — one class per file. The class docstring is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit


class TensorTreeDefinition(treeObject):
    """ONE ROOTED VIEW over a tensor (plan §11): exactly one root; a tensor may have MANY trees (spatial, scale, modal, decomposition, operator — plan §F6.4); a tree may be arbitrarily incomplete and is useful before it is finished."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        description: str = '',
        tensor: str = '',
        root_node: str = '',
        view_kind: str = 'spatial',
        status: str = 'partial',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.description = description
        self.tensor = tensor  # Tensor.name
        self.root_node = root_node  # TensorNode.name or UnresolvedTensorSpace.name
        self.view_kind = view_kind  # spatial | scale | modal | decomposition | operator | other
        self.status = status  # partial | resolved
        self.notes = notes
