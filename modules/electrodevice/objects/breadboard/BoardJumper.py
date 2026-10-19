"""
@module electrodevice.objects.breadboard.BoardJumper

Row class BoardJumper of the electrodevice module — one class per file (design §7), split
from breadboard_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class BoardJumper(treeObject):
    """One wire between two boards (or two strips of one board) —
    the nets it touches become ONE net.

    lay-0: `kind` says what the ends are. 'jumper' (the default) joins two tie points of breadboards. 'header' joins a header pin of a
    development board (a BoardPin canonical name such as D6, or a power label such as GND / 5V; the board is a devboard BenchBoard) to a
    hole or rail of a breadboard: the HeaderWire of the layout view. `colour_override` is this one wire's own colour, kept BESIDE the colour
    the WireColorScheme derives for it ('' = use the derived colour)."""

    @treeObjectInit
    def __init__(self, name: str = '', board_a: str = '',
                 tie_a: str = '', board_b: str = '',
                 tie_b: str = '', description: str = '',
                 kind: str = 'jumper', colour_override: str = '',
                 manager=None):
        self.name = name
        self.board_a = board_a
        self.tie_a = tie_a
        self.board_b = board_b
        self.tie_b = tie_b
        self.description = description
        self.kind = kind
        self.colour_override = colour_override
