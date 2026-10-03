"""
@module board.objects.board.Connector

Connector — one class per file (design §7); brd-bo, THE BOARD OBJECT.
"""
from objectTreeDecorators import treeObject, treeObjectInit


class Connector(treeObject):
    """What it is: A connector / header on a board (§2b BoardHardware) with its pin order; the pins are `ConnectorPin` rows.
    """

    @treeObjectInit
    def __init__(self, name: str = '', board: str = '', connector: str = '', ref: str = '', kind: str = '',
                 pin_count: int = 0, footprint: str = '', order_note: str = '', fact: str = '', notes: str = '',
                 manager=None):
        self.name = name  # '<board>:<connector>'
        self.board = board
        self.connector = connector  # POWER | ANALOG | DIGITAL_L | …
        self.ref = ref  # the reference designator in the KiCad view (J1 …)
        self.kind = kind  # header | usb | icsp
        self.pin_count = pin_count
        self.footprint = footprint  # a KiCad library footprint ref
        self.order_note = order_note  # how the pin numbers were assigned, said
        self.fact = fact
        self.notes = notes
