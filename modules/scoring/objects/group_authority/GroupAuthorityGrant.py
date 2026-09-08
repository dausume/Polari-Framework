"""
@module scoring.objects.group_authority.GroupAuthorityGrant

Row class GroupAuthorityGrant of the scoring module — one class per file (design §7), split
from group_authority_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class GroupAuthorityGrant(treeObject):
    """One user's authority (primary|shared) over one ScoreGroup."""

    @treeObjectInit
    def __init__(
        self,
        # unique key ('ga--<group>--<subject>').
        name: str = '',
        group_name: str = '',
        # Keycloak subject (sub claim) of the authority holder.
        subject: str = '',
        username: str = '',
        # AUTHORITY_ROLES entry.
        role: str = 'shared',
        # GRANT_STATUSES entry.
        status: str = 'active',
        granted_by_subject: str = '',
        granted_by_username: str = '',
        # 'keycloak-verified' | 'payload-unverified' at grant time.
        identity_source: str = 'payload-unverified',
        granted_at: str = '',
        revoked_at: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.group_name = group_name
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
