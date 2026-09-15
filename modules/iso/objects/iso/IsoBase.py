"""
@module iso.objects.iso.IsoBase

IsoBase — one Ubuntu base image Polari can build an installer from.
"""
from objectTreeDecorators import treeObject, treeObjectInit


class IsoBase(treeObject):
    """IsoBase

    What it is: an Ubuntu Server live ISO (the subiquity installer) for one release and architecture, with where it
    comes from, its published checksum and whether it is cached on this instance; plus the kernel's modules.alias
    table for that release (what the compatibility check derives from).
    Related concepts: IsoBuild (built from a base), DeviceProbe (checked against a base's kernel table).
    How it is measured or derived: release/url from the seed (Ubuntu's releases server), sha256 from Ubuntu's
    SHA256SUMS, cached bytes measured on disk; the kernel table fetched from the Ubuntu archive. Never typed.
    """

    @treeObjectInit
    def __init__(self, name: str = '', release: str = '', codename: str = '', arch: str = 'amd64', url: str = '', sha256: str = '',
                 bytes: int = 0, cached: bool = False, cached_path: str = '', kernel_table: str = '', kernel_abi: str = '',
                 default: bool = False, note: str = ''):
        self.name = name
        self.release = release
        self.codename = codename
        self.arch = arch
        self.url = url
        self.sha256 = sha256
        self.bytes = bytes
        self.cached = cached
        self.cached_path = cached_path
        self.kernel_table = kernel_table
        self.kernel_abi = kernel_abi
        self.default = default
        self.note = note
