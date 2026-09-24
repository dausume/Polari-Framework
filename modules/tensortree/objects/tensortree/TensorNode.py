"""
@module tensortree.objects.tensortree.TensorNode

Row class TensorNode of the tensortree module — one class per file. The class docstring is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit


class TensorNode(treeObject):
    """A LOCALLY COHERENT, VISUALIZABLE TENSOR SPACE (plan §12). Validity is LOCAL: every LocalizedDimension of this node has a coherent channel in `binding_ref` (a SimSpaceBindingDefinition); an unresolved child never invalidates it (plan §F6.1)."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        description: str = '',
        tree: str = '',
        parent: str = '',
        title: str = '',
        tensor: str = '',
        dims_json: str = '[]',
        binding_ref: str = '',
        global_params_json: str = '{}',
        status: str = 'unresolved',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.description = description
        self.tree = tree  # TensorTreeDefinition.name
        self.parent = parent  # structural parent (empty = the root)
        self.title = title
        self.tensor = tensor  # Tensor.name this node views
        self.dims_json = dims_json  # JSON list of LocalizedDimension names
        self.binding_ref = binding_ref  # SimSpaceBindingDefinition.name — the ONE visualization of this node
        self.global_params_json = global_params_json  # parameters constant across the node
        self.status = status  # resolved | unresolved — set by the validator, never by hand
        self.notes = notes
