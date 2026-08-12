"""
@cross-cutting
@module collab.collab_basis
@tags @xc:bindings

Collaboration sessions (mtg-2, LIVEKIT_COLLABORATION_PLAN v2 §2):
ONE object, many client surfaces (browser meeting, simulation-side
voice, VR) — "do not build Polari Video Meetings and later Polari VR
Meetings". The second module born manifest-first on the dyn-1
machinery (scanning walked it first).

The one hard architectural line (plan §2), stated here because this
module is where it would be easiest to violate:

    NOTHING THAT ARRIVES OVER LIVEKIT MAY MUTATE POLARI STATE.

LiveKit carries pose/presence/speaking/drag PREVIEWS — transient and
unvalidated. Rows here are the durable side: who may meet where
(CollaborationSession) and what a meeting decided (MeetingRecord).
Committed changes ride the normal propose→execute path, never a
message that happened to arrive on an authenticated socket.

Two treeObjects (auto-CRUDE + persisted — object-coherence):

  CollaborationSession  a meeting room's identity + policy: scope
                        (local|web — LAN is the whole 2026 story),
                        moderation (first VERIFIED token-minter
                        self-claims moderator, the group-authority
                        first-come precedent; a KC role may also
                        carry it), open/closed state.
  MeetingRecord         the durable trace §7 wants: participants,
                        decisions, artifact links. DELIBERATELY NO
                        AUDIO FIELD — a session is ephemeral by
                        default; recording would be its own consented
                        audited act and is OUT of v1.

@consumers
  - polariApiServer.polariServer.defClassList (auto-CRUDE + persistence)
  - collab.collab_api (token minting, capability, join-info)
@see modules/collab/livekit_remote.py (the resolution ladder),
     modules/scoring/group_authority.py (identity-as-evidence idiom)
"""

import re

from objectTreeDecorators import treeObject, treeObjectInit

#: Where a session is reachable from. 'local' = the LAN under the
#: Polari CA (all of 2026 per the defaulted scope decision); 'web'
#: exists as vocabulary so rows can DECLARE the ambition, but the
#: capability ladder refuses it until the EXTERNAL_APPS + TURN work
#: exists — declaring is not enabling.
SESSION_SCOPE_VALUES = ('local', 'web')

#: Lifecycle of a CollaborationSession.
SESSION_STATUS_VALUES = ('open', 'closed')

#: How the caller that touched a row was identified — identity is
#: evidence (group_authority precedent), never a bare assertion.
IDENTITY_SOURCE_VALUES = ('keycloak-verified', 'payload-unverified')

#: Room names travel into LiveKit JWTs and URLs: one safe segment.
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


class CollaborationSession(treeObject):
    """A meeting room's identity + policy. The room EXISTS as a row
    first; LiveKit only ever sees tokens this backend minted for it."""

    @treeObjectInit
    def __init__(self, name='', title='', room_name='', scope='local',
                 status='open', moderator_subject='',
                 moderator_username='', moderator_role='',
                 moderator_source='', bound_route='', bound_ref='',
                 notes='', manager=None):
        self.name = name
        self.title = title
        # mtg-6: WHICH SURFACE this meeting belongs to, as data.
        # bound_route is a page path ('/sim-spaces/motor-m2-viz'), so a
        # page can ask "is there a meeting about what I am showing?"
        # without anything being hardcoded on either side; bound_ref is
        # the object itself ('SimSpaceDefinition/motor-m2-viz') for the
        # cases where several routes show one object. Both empty = a
        # standalone meeting, which is the ordinary case.
        self.bound_route = bound_route
        self.bound_ref = bound_ref
        # LiveKit room identity; defaults to the row name at token
        # time so a bare CRUDE create still yields a joinable room.
        self.room_name = room_name
        self.scope = scope
        self.status = status
        # Moderation: empty until the first VERIFIED caller mints a
        # token and self-claims (first-come PRIMARY, the
        # group-authority precedent). moderator_role additionally
        # grants moderation to any caller carrying that KC role.
        self.moderator_subject = moderator_subject
        self.moderator_username = moderator_username
        self.moderator_role = moderator_role
        # How the moderator identity was established — evidence.
        self.moderator_source = moderator_source
        self.notes = notes


class MeetingRecord(treeObject):
    """What a meeting DECIDED — the durable, consented trace.
    Participants, decisions, artifact links. No audio, by design."""

    @treeObjectInit
    def __init__(self, name='', session_name='', started_at='',
                 ended_at='', participants_json='[]',
                 decisions_json='[]', artifact_links_json='[]',
                 notes='', manager=None):
        self.name = name
        self.session_name = session_name
        self.started_at = started_at
        self.ended_at = ended_at
        # [{identity, source}] — who was present, per the token log,
        # not per anything that arrived over the media plane.
        self.participants_json = participants_json
        # [{decision, decided_by, ref}] — refs point at proposals/
        # provenance entries; the record CITES commits, it never IS one.
        self.decisions_json = decisions_json
        # [{kind, name}] — rows/assets a meeting produced or discussed.
        self.artifact_links_json = artifact_links_json
        self.notes = notes
