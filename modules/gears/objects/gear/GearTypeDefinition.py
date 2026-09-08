"""
@module gears.objects.gear.GearTypeDefinition

Row class GearTypeDefinition of the gears module — one class per file (design §7), split
from gear_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit
from gears.objects.gear._shared import AXIS_RELATIONS, PROFILE_FAMILIES, TOLERANCE_TIERS

class GearTypeDefinition(treeObject):
    """One KIND of gear, as knobs. The ratio LAW is named (and, for
    the simple cases, computed by the solver from tooth counts); the
    efficiency band is a literature prior with both ends stated so a
    report can never quietly pick the flattering end."""

    @treeObjectInit
    def __init__(self, name='', display_name='', description='',
                 axis_relation='parallel',
                 ratio_law='n_driven / n_driving',
                 efficiency_prior_min=0.9,
                 efficiency_prior_max=0.99,
                 reverses_direction=True,
                 profile_family='involute',
                 geometry_generator='',
                 produces_thrust=False,
                 can_self_lock=False,
                 makeability_note='', tolerance_tier_min='T0',
                 is_prior=True, provenance_id='', notes='',
                 manager=None):
        self.name = name
        self.display_name = display_name
        self.description = description
        self.axis_relation = (axis_relation
                              if axis_relation in AXIS_RELATIONS
                              else 'parallel')
        #: Human-readable law; the solver implements the standard
        #: cases and REFUSES types it cannot yet chain (never
        #: guesses a ratio).
        self.ratio_law = ratio_law
        #: Literature band, BOTH ends — flagged as a prior wherever
        #: it is used. Worm drives span 0.30-0.90 and that spread is
        #: the whole point of showing both numbers.
        self.efficiency_prior_min = efficiency_prior_min
        self.efficiency_prior_max = efficiency_prior_max
        #: External meshes reverse rotation; internal (ring) meshes
        #: do not. Getting this wrong is a classic silent bug, so it
        #: is a row field AND a selftest.
        self.reverses_direction = reverses_direction
        self.profile_family = (profile_family
                               if profile_family in PROFILE_FAMILIES
                               else 'involute')
        #: gr-3 hook: which generator builds this type's
        #: MathShapeDefinition rows. Empty = geometry NOT built yet;
        #: the abstract sim still runs and the 3D view refuses by
        #: name (sim is never blocked on geometry).
        self.geometry_generator = geometry_generator
        self.produces_thrust = produces_thrust
        #: Whether the type CAN self-lock — never whether a given
        #: design DOES (that needs a friction coefficient for the
        #: material pair, which cast composites do not have; the
        #: solve returns 'unassessed' with the ask).
        self.can_self_lock = can_self_lock
        #: How this would be made in OUR stack, honestly.
        self.makeability_note = makeability_note
        self.tolerance_tier_min = (tolerance_tier_min
                                   if tolerance_tier_min
                                   in TOLERANCE_TIERS else 'T0')
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes
