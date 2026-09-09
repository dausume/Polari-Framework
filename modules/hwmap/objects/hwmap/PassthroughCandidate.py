"""
@module hwmap.objects.hwmap.PassthroughCandidate

PassthroughCandidate — the verdict: can this port be handed to a guest, and how.
"""
from objectTreeDecorators import treeObject, treeObjectInit

MAPPINGS = ('usb-hostdev', 'pci-vfio', 'nic-macvtap', 'serial-usb-hostdev', 'not-mappable')


class PassthroughCandidate(treeObject):
    """What it is: the answer to "what can be mapped to a potential KVM" for
    one port: the mapping kind (usb hostdev; pci vfio — only with an IOMMU
    group of its own and a driver that can be unbound; a NIC as macvtap; a
    USB serial adapter as usb hostdev by vendor:product or, better, by its
    by-id path), the blockers (no IOMMU, group shared with the host's own
    disk/GPU, currently owned by another guest, a root hub) and which
    hardware apps declare a need it satisfies.
    Related concepts: `HardwarePort`, `HardwareAppDefinition.passthrough_json`.
    How it is derived: `hwmap.custom.mapping.classify` — pure rules over the
    snapshot; the reasons are the evidence.
    """

    @treeObjectInit
    def __init__(self, name: str = '', device_name: str = '', port: str = '', mapping: str = 'not-mappable',
                 mappable: bool = False, reasons_json: str = '[]', satisfies_json: str = '[]',
                 fragment: str = '', observed_at: str = '', is_mock: bool = False):
        self.name = name
        self.device_name = device_name
        self.port = port
        self.mapping = mapping
        self.mappable = mappable
        self.reasons_json = reasons_json
        self.satisfies_json = satisfies_json
        self.fragment = fragment
        self.observed_at = observed_at
        self.is_mock = is_mock
