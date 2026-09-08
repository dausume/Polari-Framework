"""
@module scoring.objects.group_authority.GroupInstanceBinding

Row class GroupInstanceBinding of the scoring module — one class per file (design §7), split
from group_authority_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class GroupInstanceBinding(treeObject):
    """One group's designation of one Polari instance as its
    authoritative source, defined on both sides."""

    @treeObjectInit
    def __init__(
        self,
        # unique key ('binding--<group>--<instance>').
        name: str = '',
        group_name: str = '',
        instance_name: str = '',
        # Who the remote side is (only 'psc' today).
        counterparty: str = 'psc',
        # BINDING_STATUSES entry.
        status: str = 'confirmed-local',
        proposed_by_subject: str = '',
        proposed_by_username: str = '',
        identity_source: str = 'payload-unverified',
        confirmed_local_at: str = '',
        confirmed_remote_at: str = '',
        confirmed_remote_by: str = '',
        revoked_at: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.group_name = group_name
        self.instance_name = instance_name
        self.counterparty = counterparty
        self.status = status
        self.proposed_by_subject = proposed_by_subject
        self.proposed_by_username = proposed_by_username
        self.identity_source = identity_source
        self.confirmed_local_at = confirmed_local_at
        self.confirmed_remote_at = confirmed_remote_at
        self.confirmed_remote_by = confirmed_remote_by
        self.revoked_at = revoked_at
        self.notes = notes
