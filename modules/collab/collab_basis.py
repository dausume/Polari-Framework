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
# sap-2c INDEX (design §7): the classes live one-per-file under objects/collab/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

import re
from objectTreeDecorators import treeObject, treeObjectInit

from collab.objects.collab._shared import IDENTITY_SOURCE_VALUES, SESSION_SCOPE_VALUES, SESSION_STATUS_VALUES, _SAFE_ROOM_RE, moderation_grant, safe_room_name  # noqa: F401
from collab.objects.collab.CollaborationSession import CollaborationSession  # noqa: F401
from collab.objects.collab.MeetingRecord import MeetingRecord  # noqa: F401
