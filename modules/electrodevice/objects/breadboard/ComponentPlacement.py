"""
@module electrodevice.objects.breadboard.ComponentPlacement

Row class ComponentPlacement of the electrodevice module — one class per file (design §7), split
from breadboard_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class ComponentPlacement(treeObject):
    """One component PLUGGED INTO a board — same electrical fields
    as CircuitComponentDefinition, but wired by tie points."""

    @treeObjectInit
    def __init__(self, name: str = '', board_name: str = '',
                 kind: str = 'resistor', params_json: str = '{}',
                 # Ordered tie points (element node order), e.g.
                 # '["r5L", "r7L"]' or '["vplus", "r3R"]'.
                 tiepoints_json: str = '[]',
                 device_name: str = '',
                 description: str = '', manager=None):
        self.name = name
        self.board_name = board_name
        self.kind = kind
        self.params_json = params_json
        self.tiepoints_json = tiepoints_json
        self.device_name = device_name
        self.description = description
