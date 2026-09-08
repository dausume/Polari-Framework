"""
@module magnetics.objects.magnet_circuit.FluxNodeDefinition

Row class FluxNodeDefinition of the magnetics module — one class per file (design §7), split
from magnet_circuit_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class FluxNodeDefinition(treeObject):
    """One declared flux node. Elements may reference undeclared
    nodes — that is a SUGGESTION (declare or fix the typo), never a
    silent pass or a hard stop. Node '0' is the return path by
    convention (the reference potential)."""

    @treeObjectInit
    def __init__(self, name: str = '', circuit_name: str = '',
                 node: str = '', is_reference: bool = False,
                 description: str = '', manager=None):
        self.name = name
        self.circuit_name = circuit_name
        self.node = node
        self.is_reference = is_reference
        self.description = description
