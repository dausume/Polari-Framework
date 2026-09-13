"""
@module security.objects.security.ServiceIdentity

Row class ServiceIdentity of the security module — one class per file.
"""
from objectTreeDecorators import treeObject, treeObjectInit


class ServiceIdentity(treeObject):
    """One service certificate from the cert manifests: hostnames (SANs), issuer, not_after when issued, which peers must verify it. Derived from ca/cert-manifest.conf rows and ca/issued/."""

    @treeObjectInit
    def __init__(self, name: str = '', service: str = '', manifest: str = '', issuer: str = '', hostnames: str = '', path: str = '', issued: bool = False, not_after: str = '', days_left: int = -1, verifies: str = '', mtls_required_by: str = ''):
        self.name = name
        self.service = service
        self.manifest = manifest
        self.issuer = issuer
        self.hostnames = hostnames
        self.path = path
        self.issued = issued
        self.not_after = not_after
        self.days_left = days_left
        self.verifies = verifies
        self.mtls_required_by = mtls_required_by
