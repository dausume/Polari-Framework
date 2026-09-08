"""
@module electrodevice.objects.level_bridge.PinBindingDefinition

Row class PinBindingDefinition of the electrodevice module — one class per file (design §7), split
from level_bridge_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class PinBindingDefinition(treeObject):
    """One design-output bit -> one driven source. A row, so the
    coupling is inspectable and editable AT the object."""

    @treeObjectInit
    def __init__(self, name: str = '', design_name: str = '',
                 output_node: str = '', bit: int = 0,
                 # 'placement' (ComponentPlacement) or 'component'
                 # (CircuitComponentDefinition); the target must be
                 # a 'vsource'.
                 target_kind: str = 'placement',
                 target_name: str = '', vdd: float = 3.3,
                 description: str = '', manager=None):
        self.name = name
        self.design_name = design_name
        self.output_node = output_node
        self.bit = bit
        self.target_kind = target_kind
        self.target_name = target_name
        self.vdd = vdd
        self.description = description
