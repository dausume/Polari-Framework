"""@module collab.objects.collab._shared — what the collab row classes share (constants, seeds, helpers); split from collab_basis.py (sap-2c)."""
import re

SESSION_SCOPE_VALUES = ('local', 'web')
SESSION_STATUS_VALUES = ('open', 'closed')
IDENTITY_SOURCE_VALUES = ('keycloak-verified', 'payload-unverified')
_SAFE_ROOM_RE = re.compile(r'^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$')
def safe_room_name(name):
    """True when *name* is a single safe room/key segment."""
    return bool(_SAFE_ROOM_RE.match(name or '')) and '..' not in name
def moderation_grant(caller_subject, caller_roles, moderator_subject,
                     moderator_role):
    """Whether a VERIFIED caller gets the moderation (roomAdmin)
    grant: the session's claimed moderator, or any holder of the
    session's moderator_role. Pure — the token endpoint applies it,
    the selftest pins it. An empty moderator_subject grants NOTHING
    here (the self-claim happens before this is consulted)."""
    if caller_subject and moderator_subject \
            and caller_subject == moderator_subject:
        return True
    return bool(moderator_role) and moderator_role in (caller_roles or [])
