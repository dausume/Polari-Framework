"""
@module hardwareapps.objects.hardwareapps.HardwareAppDefinition

HardwareAppDefinition — one KVM guest as data, or one extension of one.
"""
from objectTreeDecorators import treeObject, treeObjectInit

HARDWARE_APP_KINDS = ('hardware-app', 'hardware-extension-app')
GUEST_KINDS = ('openwrt', 'debian', 'alpine')
ROLES = ('router', 'relay', 'guestnet', 'lab', 'sdr-rx', 'radio', 'custom')


class HardwareAppDefinition(treeObject):
    """What it is: one KVM guest the isle defines (kind `hardware-app`) or
    functionality pushed into such a guest (kind `hardware-extension-app`,
    `extends` names the host app). The isle's own router is the archetype
    and stays woven into the isle; relay and guestnet are the first
    definable ones.
    Related concepts: `IsleCatalogEntry` (the store row that points here),
    `DeviceLink` (the USB/NIC devices passed through — `passthrough_json`
    names them; passthrough is exclusive), `HardwareAppState` (the twin).
    How it is realised: the libvirt domain XML is RENDERED from this row by
    `hardwareapps.custom.domain_xml` (the router's template: q35,
    host-passthrough CPU, eight spare PCIe ports, virtio disk, the bridges
    listed here, then one hostdev/macvtap per passthrough); the guest's
    OpenWrt configuration is rendered by `hardwareapps.custom.uci_profiles`
    from `uci_params_json`. Images are pinned by RAW sha like the router's
    (`image_sha256_raw`); never a booted image.
    """

    @treeObjectInit
    def __init__(self, name: str = '', title: str = '', kind: str = 'hardware-app',
                 role: str = 'custom', extends: str = '', guest_kind: str = 'openwrt',
                 vm_image_ref: str = 'openwrt-isle-router.qcow2', image_sha256_raw: str = '',
                 memory_mb: int = 512, vcpus: int = 2,
                 # bridges the guest attaches to, in NIC order (eth0, eth1, …)
                 bridges_json: str = '["br-mgmt", "isle-br-0"]',
                 # DeviceLink names (USB) and host NIC names (macvtap) handed to the guest
                 passthrough_json: str = '[]',
                 # the UCI profile name + its parameters (uci_profiles.PROFILES)
                 uci_profile: str = '', uci_params_json: str = '{}',
                 requires_tier: str = 'hardware', autostart: bool = True,
                 pinned_device: str = '', is_prior: bool = True, notes: str = ''):
        self.name = name
        self.title = title
        self.kind = kind
        self.role = role
        self.extends = extends
        self.guest_kind = guest_kind
        self.vm_image_ref = vm_image_ref
        self.image_sha256_raw = image_sha256_raw
        self.memory_mb = memory_mb
        self.vcpus = vcpus
        self.bridges_json = bridges_json
        self.passthrough_json = passthrough_json
        self.uci_profile = uci_profile
        self.uci_params_json = uci_params_json
        self.requires_tier = requires_tier
        self.autostart = autostart
        self.pinned_device = pinned_device
        self.is_prior = is_prior
        self.notes = notes
