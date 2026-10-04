"""
@module board.objects.board.BoardHardware

BoardHardware — one class per file (design §7); brd-bo, THE BOARD OBJECT.
"""
from objectTreeDecorators import treeObject, treeObjectInit


class BoardHardware(treeObject):
    """What it is: The BoardHardware layer (§2b) as ONE linked row per board (BoardDefinition stays the Identity layer): the
    components with their reference designators and footprint refs, the power rails, the crystal / resonator, and the USB
    bridge chip that IS the board's USB identity (ties to BoardDefinition.usb_ids_json). Connectors and nets are their own
    rows (`Connector`, `ConnectorPin`, `BoardNet`).
    """

    @treeObjectInit
    def __init__(self, name: str = '', board: str = '', components_json: str = '[]', power_rails_json: str = '[]',
                 crystal: str = '', usb_bridge_chip: str = '', usb_ids_json: str = '[]', facts_json: str = '[]',
                 source: str = '', undetermined: str = '', notes: str = '', manager=None):
        self.name = name  # the board name
        self.board = board
        self.components_json = components_json  # [{ref, value, footprint, lib, part, role, fact}]
        self.power_rails_json = power_rails_json  # [{net, volts, source, fact}]
        self.crystal = crystal  # the MCU clock source + frequency
        self.usb_bridge_chip = usb_bridge_chip  # the chip behind the USB VID:PID (ATmega16U2 / the C3 itself)
        self.usb_ids_json = usb_ids_json  # copied from the Identity row (BoardDefinition) — never typed twice
        self.facts_json = facts_json
        self.source = source
        self.undetermined = undetermined
        self.notes = notes
