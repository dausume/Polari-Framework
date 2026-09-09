"""
@module hwmap.objects.hwmap.HardwareMapSnapshot

HardwareMapSnapshot — one scan of one device.
"""
from objectTreeDecorators import treeObject, treeObjectInit


class HardwareMapSnapshot(treeObject):
    """What it is: the facts one `pol hwmap scan` found on one device at one
    moment: whether the CPU can virtualise, whether /dev/kvm, libvirt and
    an IOMMU are present (the hardware tier's prerequisites), and the
    counts of ports and slots. Rows are replaced per device on every push
    (the islemesh ingest rule), never merged.
    Related concepts: `HardwarePort`, `HardwareSlot`, `PassthroughCandidate`,
    `IsleDevice` (the device), `HardwareAppDefinition` (what would use it).
    How it is measured: `/proc/cpuinfo` flags, `/dev/kvm`, `virsh`, and
    `/sys/kernel/iommu_groups` on the device — never assumed.
    """

    @treeObjectInit
    def __init__(self, name: str = '', device_name: str = '', cpu_virt: bool = False, kvm_device: bool = False,
                 libvirt: bool = False, iommu_groups: int = 0, hardware_tier_ready: bool = False,
                 usb_ports: int = 0, pci_ports: int = 0, nics: int = 0, serial_ports: int = 0, slots: int = 0,
                 observed_at: str = '', scanner_version: str = '', is_mock: bool = False, notes: str = ''):
        self.name = name
        self.device_name = device_name
        self.cpu_virt = cpu_virt
        self.kvm_device = kvm_device
        self.libvirt = libvirt
        self.iommu_groups = iommu_groups
        self.hardware_tier_ready = hardware_tier_ready
        self.usb_ports = usb_ports
        self.pci_ports = pci_ports
        self.nics = nics
        self.serial_ports = serial_ports
        self.slots = slots
        self.observed_at = observed_at
        self.scanner_version = scanner_version
        self.is_mock = is_mock
        self.notes = notes
