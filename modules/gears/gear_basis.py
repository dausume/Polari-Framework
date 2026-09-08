"""
@module gears.gear_basis

gr-1 (GEARS_PLAN §2, §3): GEAR TRAINS AS DATA. A gear train is a
GRAPH of rotating bodies: SHAFT NODES carry one angular speed each,
MESH EDGES impose a speed ratio and a torque ratio between two
shafts. That is the mechanical twin of the reluctance network
(mag-3): shaft node ~ flux node, mesh ~ element, power conservation ~
flux conservation — so it rides the same rows-then-solve discipline
rather than a second invented one.

Every gear TYPE is a row (GearTypeDefinition), never a code branch:
its ratio law, its efficiency PRIOR BAND (literature, flagged, until
measured runs replace it), its axis relationship, its geometry
generator key, and how it would actually be MADE in our stack. Adding
a type = adding a row + (for 3D) a generator.

Honesty pinned here so it travels on every payload:
- quasi-static ONLY; inertia/acceleration/resonance are out of v1;
- efficiency numbers are priors until GearVerificationRun rows land;
- tooth stress is a SCREEN (gr-2), never a certification;
- backlash is a first-class column — cast (T0) parts have a lot of
  it, and a reduction train ACCUMULATES it.

@consumers gears.custom.gear_kinematics, gears.gear_api, polariServer
"""

from objectTreeDecorators import treeObject, treeObjectInit

#: Axis relationship between the two meshing bodies.
AXIS_RELATIONS = ('parallel', 'coaxial', 'intersecting',
                  'skew', 'rotary-linear')

#: Tolerance tiers — the SAME ladder the motor designs use (§2c of
#: the magnetics plan): T0 cast / T1 lapped / T2 fired / T3 machined.
TOLERANCE_TIERS = ('T0', 'T1', 'T2', 'T3')

#: Profile families a geometry generator (gr-3) may be asked for.
#: 'none' = this type has no tooth profile of its own (a shaft
#: coupling, a rack's mating pinion is still involute, etc.).
PROFILE_FAMILIES = ('involute', 'cycloidal', 'lantern', 'none')


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


class GearDefinition(treeObject):
    """One physical gear body. Material is BY REFERENCE into the
    existing catalogs (msci material / magnetics option / supply
    item) so cost cascades and realization gates travel unchanged —
    the same discipline as motor material slots."""

    @treeObjectInit
    def __init__(self, name='', display_name='', train_ref='',
                 gear_type_ref='spur', teeth=20, module_mm=1.0,
                 face_width_mm=6.0, pressure_angle_deg=20.0,
                 shaft_ref='', material_ref='',
                 backlash_mm_prior=0.0, is_input=False,
                 is_output=False, is_prior=True, provenance_id='',
                 notes='', manager=None):
        self.name = name
        self.display_name = display_name
        self.train_ref = train_ref
        self.gear_type_ref = gear_type_ref
        #: Tooth count. For a rack this is the (virtual) count used
        #: only for the travel-per-turn math; the type row says so.
        self.teeth = teeth
        #: Module (mm of pitch diameter per tooth) — pitch diameter
        #: = module * teeth. The metric convention; diametral pitch
        #: is a display concern, not a second stored number.
        self.module_mm = module_mm
        self.face_width_mm = face_width_mm
        self.pressure_angle_deg = pressure_angle_deg
        #: The shaft this body rides — bodies sharing a shaft turn
        #: at the SAME speed (that is what makes a compound stage a
        #: compound stage).
        self.shaft_ref = shaft_ref
        self.material_ref = material_ref
        #: Prior until a measured GearVerificationRun replaces it.
        #: Cast T0 parts carry a lot; the train ACCUMULATES it.
        self.backlash_mm_prior = backlash_mm_prior
        self.is_input = is_input
        self.is_output = is_output
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes


class ShaftNodeDefinition(treeObject):
    """One shaft = one angular speed. The graph node. Declared rows
    are documentation + drift visibility; a gear may reference an
    undeclared shaft and that is a SUGGESTION (declare it, or fix
    the typo), never a silent pass — the mag-3 flux-node rule."""

    @treeObjectInit
    def __init__(self, name='', train_ref='', shaft='',
                 is_input=False, is_output=False, is_fixed=False,
                 bearing_item_ref='', description='',
                 is_prior=True, provenance_id='', notes='',
                 manager=None):
        self.name = name
        self.train_ref = train_ref
        self.shaft = shaft
        self.is_input = is_input
        self.is_output = is_output
        #: A GROUNDED member (a fixed ring gear, a stationary
        #: carrier). Speed pinned to zero; it is how planetary
        #: ratios are chosen.
        self.is_fixed = is_fixed
        #: mag-1 already cites 608 bearings + 8 mm shaft.
        self.bearing_item_ref = bearing_item_ref
        self.description = description
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes


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


class GearTrainDefinition(treeObject):
    """One drivetrain: the unit that solves. Input torque/speed may
    come from a motor row (gr-5 splice) or be stated directly for
    teaching/sizing."""

    @treeObjectInit
    def __init__(self, name='', display_name='', description='',
                 input_shaft='', output_shaft='',
                 input_torque_nm=0.0, input_speed_rpm=0.0,
                 motor_design_ref='', tolerance_tier='T0',
                 is_prior=True, provenance_id='', notes='',
                 manager=None):
        self.name = name
        self.display_name = display_name
        self.description = description
        self.input_shaft = input_shaft
        self.output_shaft = output_shaft
        #: Stated drive, used when no motor is referenced.
        self.input_torque_nm = input_torque_nm
        self.input_speed_rpm = input_speed_rpm
        #: gr-5: when set, the motor's own torque curve drives the
        #: train and the parity watermarks travel through.
        self.motor_design_ref = motor_design_ref
        self.tolerance_tier = (tolerance_tier
                               if tolerance_tier in TOLERANCE_TIERS
                               else 'T0')
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes


class GearVerificationRun(treeObject):
    """A MEASURED run on a real train — never seeded, observed state
    only (the MotorVerificationRun rule). Measured efficiency and
    backlash replace the priors; that replacement is the whole
    point of the ladder."""

    @treeObjectInit
    def __init__(self, name='', train_ref='', kind='sim',
                 measured_ratio=None, measured_efficiency=None,
                 measured_backlash_mm=None, notes='', manager=None):
        self.name = name
        self.train_ref = train_ref
        #: 'sim' | 'measured' — only 'measured' rows count toward
        #: made-and-measured.
        self.kind = kind
        self.measured_ratio = measured_ratio
        self.measured_efficiency = measured_efficiency
        self.measured_backlash_mm = measured_backlash_mm
        self.notes = notes
