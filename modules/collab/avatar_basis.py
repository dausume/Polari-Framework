"""
@cross-cutting
@module collab.avatar_basis
@tags @xc:bindings

mtg-5: AVATARS AS ROWS — the plan's §8 open question, answered.

Nothing existing fits (a scanned asset is a captured object, a
MathShapeDefinition is a solved geometry), so an avatar is its own
small class following the SAME rule every other asset follows: the
row carries identity, provenance and licence; the GLB lives in object
storage and is referenced, never inlined. A presence message
(mtg-4) names one of these rows — never a URL, because a URL carries
no licence and no provenance.

Deliberately small. An avatar here is a HEAD and two HANDS: that is
what a headset actually tracks without extra inference, and a body
we cannot measure is a body we would be making up. `rig` says which
of the two it is so a renderer never guesses.

Licence is a first-class field for the reason [[mesh-asset-licensing]]
records: a mesh catalogue that does not gate on licence quietly
launders one. `usable()` is the single gate, and its default answer
for an unstated licence is NO.

@consumers
  - polariApiServer.polariServer.defClassList (auto-CRUDE + persistence)
  - collab.collab_api (avatar listing for the VR client)
  - the mtg-5 WebXR meeting scene (resolves presence.avatarRef here)
@see modules/collab/realtime_schemas.py (presence.avatarRef),
     modules/meshassets (the licence-gated catalogue precedent)
"""
# sap-2c INDEX (design §7): the classes live one-per-file under objects/avatar/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

from objectTreeDecorators import treeObject, treeObjectInit

from collab.objects.avatar._shared import AVATAR_LICENCES, AVATAR_RIGS, SEED_AVATARS, _USABLE_LICENCES, usable  # noqa: F401
from collab.objects.avatar.AvatarDefinition import AvatarDefinition  # noqa: F401
