"""
@module scoring.objects.group_authority.InstanceAuthorityGrant

Row class InstanceAuthorityGrant of the scoring module — one class per file (design §7), split
from group_authority_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class InstanceAuthorityGrant(treeObject):
    """One user's authority (primary|shared) over one Polari
    instance."""

    @treeObjectInit
    def __init__(
        self,
        # unique key ('ia--<instance>--<subject>').
        name: str = '',
        instance_name: str = '',
        subject: str = '',
        username: str = '',
        role: str = 'shared',
        status: str = 'active',
        granted_by_subject: str = '',
        granted_by_username: str = '',
        identity_source: str = 'payload-unverified',
        granted_at: str = '',
        revoked_at: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.instance_name = instance_name
        self.subject = subject
        self.username = username
        self.role = role
        self.status = status
        self.granted_by_subject = granted_by_subject
        self.granted_by_username = granted_by_username
        self.identity_source = identity_source
        self.granted_at = granted_at
        self.revoked_at = revoked_at
        self.notes = notes
