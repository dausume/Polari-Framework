"""
@module grpcbridge.objects.bridges.BridgePath

BridgePath - one class per file (design section 7). HARDWARE_SYSTEM_PINS_PLAN.md section 7 (hsp-3a; D-hsp-6 recommended: the bridge owns its location).
"""
from objectTreeDecorators import treeObject, treeObjectInit


class BridgePath(treeObject):
    """What it is: "where the bridge is" (his notebook draft, 2026-10-28) - the ordered hops a board's serial line travels from the chip's UART pins to the
    process on a computer that reads it. `hops_json` = [{n, kind, what, ref, signal_level_v, basis}] with kind chip-pins (the UART pins and the chip's logic
    level) -> converter (the USB-serial chip: ATmega16U2 on the UNO, CH340 on the Elecrow S3; its UsbInterfaceDefinition row in `ref`; his note "FT -> 5 V,
    TTA -> 3.3 V" = the converter's signal level is a fact to record) -> connector (USB-B | USB-C | micro-USB; a C -> A adapter is its own hop) ->
    host-port (hwmap's scanned bus / port on the device) -> userspace (the process: the Polari Hardware Bridge, a scope reader). A level nobody has cited is -1
    and its basis says what to read. `protocol` = uart-text | polari-frames | scpi; `mode` = serial (the real port) | simulated (the twin worker's port).
    Related concepts: PolariBridgeInstance (rides one path), UsbInterfaceDefinition (board), hwmap's port rows, HardwareSystem links (hsp-1).
    """

    plain_words = 'A bridge path is the chain from a board\'s serial pins, through its USB chip and cable, to the program on the computer that listens to it.'

    @treeObjectInit
    def __init__(self, name: str = '', bench: str = '', board: str = '', label: str = '', hops_json: str = '[]', protocol: str = '', mode: str = 'serial',
                 basis: str = '', notes: str = '', manager=None):
        self.name = name            # '<bench>/<label>:usb'
        self.bench = bench          # a Bench name
        self.board = board          # a BoardDefinition name
        self.label = label          # the bench entry's label (UNO #1)
        self.hops_json = hops_json  # [{n, kind, what, ref, signal_level_v, basis}]
        self.protocol = protocol    # uart-text | polari-frames | scpi
        self.mode = mode            # serial | simulated
        self.basis = basis
        self.notes = notes
