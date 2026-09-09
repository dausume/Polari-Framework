"""
@module hwmap.objects.hwmap.HardwareSlot

HardwareSlot — a controller with capacity (USB root hub/hub, PCI root port).
"""
from objectTreeDecorators import treeObject, treeObjectInit

SLOT_KINDS = ('usb-controller', 'usb-hub', 'pcie-root-port', 'pci-bridge')


class HardwareSlot(treeObject):
    """What it is: something ports plug INTO: a USB controller or hub (with
    its port count and speed), a PCIe root port or bridge. Slots say how
    much a device can still take (a hub with 4 ports and 3 used has one
    free) and which controller a guest inherits when a whole controller is
    passed through.
    Related concepts: `HardwarePort` (`slot` names its slot),
    `HardwareMapSnapshot`.
    How it is measured: lsusb -t (controllers, hubs, port counts, speeds),
    lspci for bridges/root ports.
    """

    @treeObjectInit
    def __init__(self, name: str = '', device_name: str = '', kind: str = 'usb-hub', slot_id: str = '',
                 driver: str = '', ports_total: int = 0, ports_used: int = 0, speed_mbps: int = 0,
                 parent: str = '', pci_address: str = '', observed_at: str = '', is_mock: bool = False):
        self.name = name
        self.device_name = device_name
        self.kind = kind
        self.slot_id = slot_id
        self.driver = driver
        self.ports_total = ports_total
        self.ports_used = ports_used
        self.speed_mbps = speed_mbps
        self.parent = parent
        self.pci_address = pci_address
        self.observed_at = observed_at
        self.is_mock = is_mock
