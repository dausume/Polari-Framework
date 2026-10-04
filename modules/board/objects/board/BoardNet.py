"""
@module board.objects.board.BoardNet

BoardNet — one class per file (design §7); brd-bo, THE BOARD OBJECT.
"""
from objectTreeDecorators import treeObject, treeObjectInit


class BoardNet(treeObject):
    """What it is: One net of a board (§2b BoardHardware): the KiCad net name, its class (power | ground | signal) and voltage. A
    `BoardPin` names its net; nets are linked to pins, never merged with them. Not electrodevice's CircuitNetDefinition:
    that one is scoped to a simulated circuit and carries no class or voltage — `circuit_net` links one when a board's net
    is also simulated.
    """

    @treeObjectInit
    def __init__(self, name: str = '', board: str = '', net: str = '', net_class: str = 'signal', volts: float = 0.0,
                 circuit_net: str = '', fact: str = '', notes: str = '', manager=None):
        self.name = name  # '<board>:<net>'
        self.board = board
        self.net = net  # the KiCad net name
        self.net_class = net_class  # power | ground | signal
        self.volts = volts  # power nets only (0 = n/a)
        self.circuit_net = circuit_net  # an electrodevice CircuitNetDefinition name, when simulated
        self.fact = fact
        self.notes = notes
