"""
@module security.objects.security.PermissionGroup

Row class PermissionGroup of the security module — one class per file.
"""
from objectTreeDecorators import treeObject, treeObjectInit


class PermissionGroup(treeObject):
    """A host group Polari relies on: the two sudoers groups (polari-remote, polari-app) with the exact verbs their drop-ins allow, the docker/libvirt/kvm groups, and the hardware groups; members and the apps needing them come from an audit run."""

    @treeObjectInit
    def __init__(self, name: str = '', purpose: str = '', verbs: str = '', sudoers_file: str = '', granted_by: str = '', members: str = '', apps_needing: str = '', installed: str = 'unknown'):
        self.name = name
        self.purpose = purpose
        self.verbs = verbs
        self.sudoers_file = sudoers_file
        self.granted_by = granted_by
        self.members = members
        self.apps_needing = apps_needing
        self.installed = installed
