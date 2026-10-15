"""
@module board.objects.board.BoardComponent

BoardComponent — one class per file (design §7); fgm-2.
"""
from objectTreeDecorators import treeObject, treeObjectInit


class BoardComponent(treeObject):
    """What it is: ONE CHIP ON A BOARD AS A ROW — U1 is the ATmega328P (role mcu), U2 the ATmega16U2 (role usb-bridge, a
    programmable MCU of its own). Derived from `BoardHardware.components_json` (never typed twice): the JSON stays the
    schematic-level list, this row gives each chip its own `SocDefinition`, its package, and what it does for the board.
    Milestone-1 firmware targets U1 only; U2 appears as the transport participant and the cause of the DTR auto-reset.
    Related concepts: `BoardHardware`, `SocDefinition`, `PackageDefinition`, `UsbInterfaceDefinition`.
    """

    plain_words = 'A board component is one chip on a board (the main chip, the USB chip) with its own chip row, package and job.'

    @treeObjectInit
    def __init__(self, name: str = '', board: str = '', ref: str = '', value: str = '', role: str = '', soc: str = '',
                 package: str = '', package_options_json: str = '[]', programmable: bool = False, targeted_by_firmware: bool = False,
                 usb_interface: str = '', fact: str = '', origin: str = '', undetermined: str = '', notes: str = '', manager=None):
        self.name = name  # '<board>:<ref>' e.g. 'arduino-uno-r3:U1'
        self.board = board
        self.ref = ref  # U1 | U2 (OUR designators on the UNO; the schematic's own refs are ZU4 / U3)
        self.value = value  # the part as components_json carries it
        self.role = role  # mcu | usb-bridge
        self.soc = soc  # the SocDefinition row
        self.package = package  # the PackageDefinition the design models ('' = none modelled)
        self.package_options_json = package_options_json  # every PackageDefinition the design allows for this chip
        self.programmable = programmable
        self.targeted_by_firmware = targeted_by_firmware  # milestone 1: U1 only
        self.usb_interface = usb_interface  # for the usb-bridge role: the UsbInterfaceDefinition it is
        self.fact = fact
        self.origin = origin
        self.undetermined = undetermined
        self.notes = notes
