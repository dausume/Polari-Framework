"""
@module electrodevice.objects.circuit.CircuitNetDefinition

Row class CircuitNetDefinition of the electrodevice module — one class per file (design §7), split
from circuit_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class CircuitNetDefinition(treeObject):
    """One declared net. Components may reference undeclared nets —
    that is a SUGGESTION (declare or fix the typo), never a silent
    pass or a hard stop."""

    @treeObjectInit
    def __init__(self, name: str = '', circuit_name: str = '',
                 net: str = '', is_ground: bool = False,
                 description: str = '',
                 # ucd-0c (UNO_CORE_DEMO_PLAN.md §5g item 3, additive): the board.custom.BoardPin rows a
                 # BoardPinNet row ties to THIS net (Class:name refs, the 'refs' column format) — a net the board
                 # module never touches keeps the default '[]'; never derived here (electrodevice does not import
                 # board — the board side hand-writes this reverse link where it knows the pins).
                 board_pins_refs_json: str = '[]',
                 manager=None):
        self.name = name
        self.circuit_name = circuit_name
        self.net = net
        self.is_ground = is_ground
        self.description = description
        self.board_pins_refs_json = board_pins_refs_json
