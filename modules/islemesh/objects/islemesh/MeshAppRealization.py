"""
@module islemesh.objects.islemesh.MeshAppRealization

Row class MeshAppRealization of the islemesh module — one class per file (design §7), split
from islemesh_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class MeshAppRealization(treeObject):
    """One way one app is delivered (handoff §9/§11): simultaneous,
    not exclusive — the same app can be a local .deb stub, a shell
    install, the plain website, and (hardware apps) a KVM. All
    carry the same .isle URL once converged."""

    @treeObjectInit
    def __init__(
        self,
        # Unique key: '<app>@<kind>' ('myapp@website').
        name: str = '',
        app_name: str = '',
        # REALIZATION_KINDS entry.
        kind: str = 'website',
        # The URL this realization opens ('' until known).
        url: str = '',
        # PACKAGE_KINDS entry ('' = not delivered as a package).
        package_kind: str = '',
        # kvm only: hardware-affinity pin — the device the physical
        # USB device is plugged into. The mover REFUSES to move a
        # pinned realization (suggest replug-at-target instead).
        hardware_pin_device: str = '',
        status: str = '',
        is_mock: bool = False,
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.app_name = app_name
        self.kind = kind
        self.url = url
        self.package_kind = package_kind
        self.hardware_pin_device = hardware_pin_device
        self.status = status
        self.is_mock = is_mock
        self.notes = notes
