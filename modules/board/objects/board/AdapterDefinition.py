"""
@module board.objects.board.AdapterDefinition

AdapterDefinition — one class per file (design §7).
"""
from objectTreeDecorators import treeObject, treeObjectInit


class AdapterDefinition(treeObject):
    """What it is: A USB adapter or programmer between the Polari host and a target (register §1a): USB-UART
    bridges, USB SWD/JTAG probes, USB ISP dongles, mass-storage bridges. Its HOST side is always USB (RULE 1, refined).
    Detection of an adapter alone yields 'adapter present, target unknown'. `usb_ids_json` is filled only for a
    generic-chip row with a cited id; a product built on a generic chip (digirig, tigard) presents that chip's id.
    Related concepts: `BoardDefinition.adapter_ids_json`, `ProgrammerKind.adapter_kind`, `BoardInstance`.
    """

    @treeObjectInit
    def __init__(self, name: str = '', register_id: str = '', kind: str = '', chip: str = '',
                 usb_connector: str = '', usb_ids_json: str = '[]', usb_ids_source: str = '',
                 by_id_hints_json: str = '[]', targets: str = '', engine: str = '', hardware_open: str = '',
                 firmware_open: str = '', origin: str = '', price_class: str = '', notes: str = '', manager=None):
        self.name = name
        self.register_id = register_id
        self.kind = kind
        self.chip = chip
        self.usb_connector = usb_connector
        self.usb_ids_json = usb_ids_json
        self.usb_ids_source = usb_ids_source  # where the VID:PID comes from
        self.by_id_hints_json = by_id_hints_json
        self.targets = targets  # targets it programs, verbatim
        self.engine = engine  # engine that drives it, verbatim
        self.hardware_open = hardware_open
        self.firmware_open = firmware_open
        self.origin = origin
        self.price_class = price_class
        self.notes = notes
