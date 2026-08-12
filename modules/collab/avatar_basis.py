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

from objectTreeDecorators import treeObject, treeObjectInit

#: What a renderer should expect to drive.
AVATAR_RIGS = ('head-hands', 'head-only')

#: Licences we may ship an avatar under. 'unstated' is the honest
#: default and is NOT usable — silence is not permission.
AVATAR_LICENCES = ('unstated', 'CC0', 'CC-BY', 'GPLv3-compatible',
                   'project-owned')

#: The licences `usable()` admits. GPLv3 is the project frame
#: ([[project-license-gplv3]]): a GPL-compatible or public-domain
#: asset is fine; anything unstated or non-commercial is not.
_USABLE_LICENCES = ('CC0', 'CC-BY', 'GPLv3-compatible', 'project-owned')


def usable(licence, attribution=''):
    """May this avatar be shown to other participants? Refuses an
    unstated licence, and refuses CC-BY that names nobody — an
    attribution licence with no attribution is unfulfilled, not
    merely untidy."""
    if licence not in _USABLE_LICENCES:
        return {'ok': False,
                'reason': f'licence {licence!r} is not usable here '
                          '(unstated licence = all rights reserved; '
                          'silence is not permission)'}
    if licence == 'CC-BY' and not (attribution or '').strip():
        return {'ok': False,
                'reason': 'CC-BY requires an attribution string, and '
                          'this row carries none — the licence is '
                          'unfulfilled until it does'}
    return {'ok': True, 'reason': ''}


class AvatarDefinition(treeObject):
    """One avatar a participant may present as. Geometry lives in
    object storage; this row is identity + licence + rig."""

    @treeObjectInit
    def __init__(self, name='', display_name='', rig='head-hands',
                 glb_ref='', licence='unstated', attribution='',
                 source='', height_m=1.7, colour='#6a7fd6',
                 is_default=False, notes='', manager=None):
        self.name = name
        self.display_name = display_name
        # AVATAR_RIGS — a headset tracks a head and two hands; a body
        # we cannot measure is a body we would be inventing.
        self.rig = rig
        # Storage reference (bucket/key), NOT a URL: a URL carries no
        # licence and no provenance. Empty = the built-in primitive
        # rendering, which is always available and needs no asset.
        self.glb_ref = glb_ref
        self.licence = licence
        self.attribution = attribution
        self.source = source
        # Eye height in metres — the scale a scene places the head at
        # when a headset reports no floor (seated 'local' fallback).
        self.height_m = height_m
        # Used by the primitive rendering and as the speaking tint.
        self.colour = colour
        self.is_default = is_default
        self.notes = notes


#: Seeded avatars: PRIMITIVES ONLY, deliberately. They carry no
#: geometry file, so they are licence-clean by construction and a
#: meeting works on a fresh instance with no asset pipeline at all.
#: Imported meshes are a later, gated act — see usable().
SEED_AVATARS = [
    {'name': 'avatar-primitive-slate', 'display_name': 'Slate',
     'rig': 'head-hands', 'glb_ref': '', 'licence': 'project-owned',
     'attribution': '', 'source': 'built-in primitive',
     'height_m': 1.7, 'colour': '#6a7fd6', 'is_default': True,
     'notes': 'Default: a head and two hands drawn from primitives. '
              'No asset file, so nothing to licence-gate and nothing '
              'to download before a meeting works.'},
    {'name': 'avatar-primitive-moss', 'display_name': 'Moss',
     'rig': 'head-hands', 'glb_ref': '', 'licence': 'project-owned',
     'attribution': '', 'source': 'built-in primitive',
     'height_m': 1.7, 'colour': '#4f9d69', 'is_default': False,
     'notes': 'Second primitive so a room of two is legible at a '
              'glance without anyone configuring anything.'},
    {'name': 'avatar-primitive-ember', 'display_name': 'Ember',
     'rig': 'head-hands', 'glb_ref': '', 'licence': 'project-owned',
     'attribution': '', 'source': 'built-in primitive',
     'height_m': 1.7, 'colour': '#c9704a', 'is_default': False,
     'notes': 'Third primitive.'},
]
