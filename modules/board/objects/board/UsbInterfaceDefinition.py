"""
@module board.objects.board.UsbInterfaceDefinition

UsbInterfaceDefinition — one class per file (design §7); fgm-2 (his ruling 2026-10-15: package and USB-interface variants
are modelled INDEPENDENTLY, the physical board's actual pair stays PENDING).
"""
from objectTreeDecorators import treeObject, treeObjectInit


class UsbInterfaceDefinition(treeObject):
    """What it is: ONE WAY A BOARD TALKS USB — the chip behind the USB connector (an ATmega16U2 on a genuine UNO R3, a CH340 on
    many clones), the VID:PID pairs it shows the host, whether the serial line's DTR wire resets the main chip (the
    auto-reset the upload relies on), and whether that chip is itself a programmable MCU (the 16U2 is; its own SoC row is
    `programmable_soc`). Independent of the package axis (`PackageDefinition`). Detect reads the id the host sees; this table
    says which interface that id means.
    Related concepts: `BoardDefinition.allowed_usb_interfaces_json`, `BoardInstance.usb_interface` (the actual one, PENDING
    until Detect/attestation), `PinLifecycleConstraint` (RESET <- DTR), `BoardComponent` (U2).
    """

    plain_words = ('A USB interface is the small chip that lets a board talk to a computer over USB, the ids it shows, and whether '
                   'opening the serial port also restarts the main chip.')

    @treeObjectInit
    def __init__(self, name: str = '', title: str = '', bridge_chip: str = '', programmable: bool = False, programmable_soc: str = '',
                 usb_ids_json: str = '[]', serial_transport: str = '', dtr_resets_mcu: str = 'undetermined', dtr_path: str = '',
                 firmware: str = '', allowed_boards_json: str = '[]', verification: str = 'unverified', document: str = '',
                 datasheet: str = '', page_table: str = '', url: str = '', undetermined: str = '', notes: str = '', manager=None):
        self.name = name  # 'atmega16u2-bridge' | 'ch340-bridge'
        self.title = title
        self.bridge_chip = bridge_chip
        self.programmable = programmable  # the bridge chip runs firmware of its own
        self.programmable_soc = programmable_soc  # its SocDefinition row ('' = none modelled)
        self.usb_ids_json = usb_ids_json  # [{id: 'vvvv:pppp', note: ...}]
        self.serial_transport = serial_transport  # the MCU pins the serial line lands on ('USART0 / D0 D1')
        self.dtr_resets_mcu = dtr_resets_mcu  # true | false | undetermined (a string: the clone's schematic may not be read)
        self.dtr_path = dtr_path  # the cited path (16U2 PD7 -> C5 100 nF -> 328P RESET)
        self.firmware = firmware  # what the bridge runs, when cited
        self.allowed_boards_json = allowed_boards_json
        self.verification = verification  # verified | partial | unverified | conflicted
        self.document = document
        self.datasheet = datasheet
        self.page_table = page_table
        self.url = url
        self.undetermined = undetermined
        self.notes = notes
