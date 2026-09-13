"""
@module security.objects.security.DeviceInventory

Row class DeviceInventory — what Polari put on one device and in what form (deb, image, checkout, unit, guest).
"""
from objectTreeDecorators import treeObject, treeObjectInit


class DeviceInventory(treeObject):
    """One device's installed footprint (his ask 2026-09-13: "where everything is installed and in what
    formats"): OS and kernel, docker and its swarm role, the Polari containers / stacks / images / volumes,
    the Polari debs, the apt sources, the CLIs and their paths, the git checkouts (branch, size), the
    systemd units and timers, KVM guests, the rings' files present (AppArmor, sudoers, /etc/isle-mesh,
    /etc/polari). Posted by `pol deploy inventory <node> --post`; the raw JSON is kept for the details."""

    @treeObjectInit
    def __init__(self, name: str = '', device: str = '', role: str = '', os_release: str = '', kernel: str = '', docker_version: str = '',
                 swarm: str = '', kvm: bool = False, iommu: bool = False, containers: str = '', stacks: str = '', images: int = 0, volumes: int = 0,
                 debs: str = '', apt_sources: str = '', clis: str = '', checkouts: str = '', units: str = '', timers: str = '', guests: str = '',
                 rings_present: str = '', formats: str = '', observed_at: str = '', raw_json: str = ''):
        self.name = name
        self.device = device
        self.role = role
        self.os_release = os_release
        self.kernel = kernel
        self.docker_version = docker_version
        self.swarm = swarm
        self.kvm = kvm
        self.iommu = iommu
        self.containers = containers
        self.stacks = stacks
        self.images = images
        self.volumes = volumes
        self.debs = debs
        self.apt_sources = apt_sources
        self.clis = clis
        self.checkouts = checkouts
        self.units = units
        self.timers = timers
        self.guests = guests
        self.rings_present = rings_present
        self.formats = formats
        self.observed_at = observed_at
        self.raw_json = raw_json
