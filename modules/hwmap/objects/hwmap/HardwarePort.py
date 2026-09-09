"""
@module hwmap.objects.hwmap.HardwarePort

HardwarePort — one attachable thing on one device.
"""
from objectTreeDecorators import treeObject, treeObjectInit

PORT_KINDS = ('usb', 'pci', 'nic', 'serial')


class HardwarePort(treeObject):
    """What it is: one thing a guest could own on one device: a USB device
    (by bus/port path and vendor:product), a PCI function (by address, with
    its IOMMU group and bound driver), a network interface, or a serial
    adapter (its /dev/serial/by-id path — identity across replugs). Name =
    '<device>:<kind>:<id>'.
    Related concepts: `HardwareSlot` (the controller it hangs off),
    `PassthroughCandidate` (the verdict), `DeviceLink` (the reticulum arc's
    richer row for radios; a port may be promoted to one), `owner` follows
    the exclusivity rule (host or a guest name).
    How it is measured: lsusb / lspci -nnk / ip -br link / by-id paths on
    the device; `hub` and `root_hub` USB entries are ports too (they are
    what a slot's capacity is measured against).
    """

    @treeObjectInit
    def __init__(self, name: str = '', device_name: str = '', kind: str = 'usb', port_id: str = '',
                 vendor_id: str = '', product_id: str = '', description: str = '', driver: str = '',
                 usb_bus: str = '', usb_path: str = '', usb_class: str = '', speed_mbps: int = 0,
                 pci_address: str = '', pci_class: str = '', iommu_group: int = -1,
                 iface: str = '', mac: str = '', by_id_path: str = '', slot: str = '', role: str = 'other',
                 owner: str = 'host', observed_at: str = '', is_mock: bool = False):
        self.name = name
        self.device_name = device_name
        self.kind = kind
        self.port_id = port_id
        self.vendor_id = vendor_id
        self.product_id = product_id
        self.description = description
        self.driver = driver
        self.usb_bus = usb_bus
        self.usb_path = usb_path
        self.usb_class = usb_class
        self.speed_mbps = speed_mbps
        self.pci_address = pci_address
        self.pci_class = pci_class
        self.iommu_group = iommu_group
        self.iface = iface
        self.mac = mac
        self.by_id_path = by_id_path
        self.slot = slot
        self.role = role
        self.owner = owner
        self.observed_at = observed_at
        self.is_mock = is_mock
