"""
@module board.objects.board.ConnectorPin

ConnectorPin — one class per file (design §7); brd-bo, THE BOARD OBJECT.
"""
from objectTreeDecorators import treeObject, treeObjectInit


class ConnectorPin(treeObject):
    """What it is: One pin of a `Connector`: its number in the connector's order, its printed label and its net.
    """

    @treeObjectInit
    def __init__(self, name: str = '', board: str = '', connector: str = '', number: int = 0, label: str = '',
                 net: str = '', board_pin: str = '', fact: str = '', notes: str = '', manager=None):
        self.name = name  # '<board>:<connector>:<n>'
        self.board = board
        self.connector = connector
        self.number = number  # 1-based
        self.label = label  # as printed (D6, +5V, GND)
        self.net = net  # the BoardNet net name
        self.board_pin = board_pin  # the BoardPin (canonical) this connector pin is wired to ('' = a power / ground pin) — its net follows that pin
        self.fact = fact
        self.notes = notes
