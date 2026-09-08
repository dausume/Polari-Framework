"""
@module electrodevice.objects.breadboard.BoardJumper

Row class BoardJumper of the electrodevice module — one class per file (design §7), split
from breadboard_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class BoardJumper(treeObject):
    """One wire between two boards (or two strips of one board) —
    the nets it touches become ONE net."""

    @treeObjectInit
    def __init__(self, name: str = '', board_a: str = '',
                 tie_a: str = '', board_b: str = '',
                 tie_b: str = '', description: str = '',
                 manager=None):
        self.name = name
        self.board_a = board_a
        self.tie_a = tie_a
        self.board_b = board_b
        self.tie_b = tie_b
        self.description = description
