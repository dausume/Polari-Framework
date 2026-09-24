"""
@module tensortree.tensortree_basis

The INDEX of the tensortree rows: classes live one-per-file under objects/tensortree/; this file re-exports them
and holds the class list the server registers.

A rooted, navigable interpretation of tensor/physical state (plan §11–§16): TensorNodes whose every
localized dimension has a coherent visualization (a sim-space binding), UnresolvedTensorSpaces
anywhere with what is known kept, TensorMappings that may cross branches, TensorSelections that are
mathematical objects, and discovery of the mappings a selection can take — hard filters, then a
CONFIGURED score.
"""
from tensortree.objects.tensortree.TensorTreeDefinition import TensorTreeDefinition  # noqa: F401
from tensortree.objects.tensortree.TensorNode import TensorNode  # noqa: F401
from tensortree.objects.tensortree.UnresolvedTensorSpace import UnresolvedTensorSpace  # noqa: F401
from tensortree.objects.tensortree.LocalizedDimension import LocalizedDimension  # noqa: F401
from tensortree.objects.tensortree.TensorMapping import TensorMapping  # noqa: F401
from tensortree.objects.tensortree.TensorSelection import TensorSelection  # noqa: F401
from tensortree.objects.tensortree.TensorDiscoveryPolicy import TensorDiscoveryPolicy  # noqa: F401

#: every row class of the module, in registration order (the selftest asserts the count)
TENSORTREE_CLASSES = [TensorTreeDefinition, TensorNode, UnresolvedTensorSpace, LocalizedDimension, TensorMapping, TensorSelection, TensorDiscoveryPolicy]
