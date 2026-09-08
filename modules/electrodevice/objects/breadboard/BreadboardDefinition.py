"""
@module electrodevice.objects.breadboard.BreadboardDefinition

Row class BreadboardDefinition of the electrodevice module — one class per file (design §7), split
from breadboard_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class BreadboardDefinition(treeObject):
    """One physical board (rows of tie strips + two rails)."""

    @treeObjectInit
    def __init__(self, name: str = '', rows: int = 30,
                 description: str = '', manager=None):
        self.name = name
        self.rows = rows
        self.description = description
