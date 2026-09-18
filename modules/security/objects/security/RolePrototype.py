"""
@module security.objects.security.RolePrototype

Row class RolePrototype of the security module — one class per file.
"""
from objectTreeDecorators import treeObject, treeObjectInit


class RolePrototype(treeObject):
    """A PROTOTYPE ROLE (his ask 2026-09-16): a role that exists to be role-played. Acting as it in dev mode lets
    the person do anything while everything they touch is recorded against the role; the review becomes the
    template a permissions admin concretes into an enforced group (AppPermissionProfile + KC group), after which
    the recording is replayed to prove the role can still do its job. State moves prototype → concreted → enforced."""

    SELF_CLAIMABLE_DOC = (
        'SELF-CLAIMABLE (his ask 2026-09-18): whether a signed-in person may put themselves into this role without '
        'an administrator. In DEV posture every prototype role is claimable unless this is explicitly False; in '
        'PRODUCTION only the roles flagged True (plus the knob list `claimable_groups`) are. Admin roles are NEVER '
        'claimable, whatever this says — see security.custom.security_claims.')

    @treeObjectInit
    def __init__(self, name: str = '', title: str = '', description: str = '', state: str = 'prototype', created_by: str = '',
                 created_at: str = '', concreted_profile: str = '', concreted_at: str = '', verified_at: str = '', verified_verdict: str = '',
                 self_claimable: bool = False):
        self.name = name                        # the role id, lower-case ('journalist')
        self.title = title
        self.description = description
        self.state = state                      # prototype | concreted | enforced
        self.created_by = created_by
        self.created_at = created_at
        self.concreted_profile = concreted_profile   # the AppPermissionProfile name it was concreted into
        self.concreted_at = concreted_at
        self.verified_at = verified_at
        self.verified_verdict = verified_verdict
        self.self_claimable = self_claimable    # may anyone signed-in claim it? (see SELF_CLAIMABLE_DOC)
