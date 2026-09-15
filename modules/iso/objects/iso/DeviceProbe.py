"""
@module iso.objects.iso.DeviceProbe

DeviceProbe — what the probe stick found on one computer, and the compatibility verdict Polari derived.
"""
from objectTreeDecorators import treeObject, treeObjectInit


class DeviceProbe(treeObject):
    """DeviceProbe

    What it is: one computer as its own probe reported it (his idea 2026-09-15): the OS it runs today, CPU, memory,
    disks and free space, firmware mode, Secure Boot, TPM, disk encryption in use, RAID mode, GPU, WiFi, every PCI
    and USB id — keyed by a hardware hash so the same machine probed twice is one row — and the VERDICT Polari
    derived against a base's kernel table: compatible / compatible with notes / not compatible, with the evidence
    per device id and the traps that apply. Apple silicon gets the plain-words message.
    Related concepts: IsoBase (the kernel table), IsoBuild (a build targets a probe), the topology's planned devices.
    How it is measured or derived: the report is measured on the machine; the verdict is derived (modules.alias +
    linux-firmware + the curated trap list). Never typed.
    """

    @treeObjectInit
    def __init__(self, name: str = '', hw_hash: str = '', label: str = '', os_name: str = '', os_version: str = '', cpu: str = '', arch: str = '',
                 virtualization: bool = False, memory_gb: float = 0.0, disks: str = '', free_gb: float = 0.0, firmware: str = '', secure_boot: str = '',
                 tpm: str = '', disk_encryption: str = '', raid_mode: str = '', gpu: str = '', wifi: str = '', nics: int = 0, device_ids: str = '',
                 apple_silicon: bool = False, verdict: str = 'unchecked', verdict_text: str = '', base_checked: str = '', drivers_in_kernel: int = 0,
                 drivers_firmware: int = 0, drivers_third_party: int = 0, drivers_missing: int = 0, traps: str = '', suggested_role: str = '',
                 suggested_reason: str = '', probed_at: str = '', raw_json: str = '', joined_at: str = '', joined_hostname: str = '', joined_addresses: str = '',
                 joined_role: str = '', joined_shape: str = '', detected: str = '', ssh_user: str = ''):
        self.name = name
        self.hw_hash = hw_hash
        self.label = label
        self.os_name = os_name
        self.os_version = os_version
        self.cpu = cpu
        self.arch = arch
        self.virtualization = virtualization
        self.memory_gb = memory_gb
        self.disks = disks
        self.free_gb = free_gb
        self.firmware = firmware
        self.secure_boot = secure_boot
        self.tpm = tpm
        self.disk_encryption = disk_encryption
        self.raid_mode = raid_mode
        self.gpu = gpu
        self.wifi = wifi
        self.nics = nics
        self.device_ids = device_ids
        self.apple_silicon = apple_silicon
        self.verdict = verdict
        self.verdict_text = verdict_text
        self.base_checked = base_checked
        self.drivers_in_kernel = drivers_in_kernel
        self.drivers_firmware = drivers_firmware
        self.drivers_third_party = drivers_third_party
        self.drivers_missing = drivers_missing
        self.traps = traps
        self.suggested_role = suggested_role
        self.suggested_reason = suggested_reason
        self.probed_at = probed_at
        self.raw_json = raw_json
        self.joined_at = joined_at
        self.joined_hostname = joined_hostname
        self.joined_addresses = joined_addresses
        self.joined_role = joined_role
        self.joined_shape = joined_shape
        self.detected = detected
        self.ssh_user = ssh_user
