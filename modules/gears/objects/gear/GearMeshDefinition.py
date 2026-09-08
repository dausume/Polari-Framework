"""
@module gears.objects.gear.GearMeshDefinition

Row class GearMeshDefinition of the gears module — one class per file (design §7), split
from gear_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class GearMeshDefinition(treeObject):
    """One mesh = the EDGE: driving gear -> driven gear. Carries the
    efficiency actually used (empty = take the type's prior band
    midpoint, flagged) and the mesh-specific overrides."""

    @treeObjectInit
    def __init__(self, name='', train_ref='', driving_gear_ref='',
                 driven_gear_ref='', efficiency_override=None,
                 center_distance_mm_override=None,
                 is_internal=False, is_prior=True,
                 provenance_id='', notes='', manager=None):
        self.name = name
        self.train_ref = train_ref
        self.driving_gear_ref = driving_gear_ref
        self.driven_gear_ref = driven_gear_ref
        #: None => the type's prior band midpoint, FLAGGED as a
        #: prior in the payload. A measured value belongs here.
        self.efficiency_override = efficiency_override
        #: None => derived (module * (N1 + N2) / 2 for external
        #: parallel meshes). An override documents a real, measured
        #: build (or a deliberate profile shift, gr-2 follow-up).
        self.center_distance_mm_override = center_distance_mm_override
        #: Internal (ring) meshes do NOT reverse direction and their
        #: center distance is a difference, not a sum.
        self.is_internal = is_internal
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes
