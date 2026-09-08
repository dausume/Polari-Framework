"""
@module collab.objects.avatar.AvatarDefinition

Row class AvatarDefinition of the collab module — one class per file (design §7), split
from avatar_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

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
