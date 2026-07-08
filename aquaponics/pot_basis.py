"""
@cross-cutting
@module aquaponics.pot_basis
@tags @xc:bindings

Self-watering pot GEOMETRY as first-class objects (aqp-1). Dustin
2026-07-08: a self-watering pot, ceramic or geopolymer (waterproof
variant), with at least two side holes — higher = water INPUT, lower =
water OUTPUT, on opposite sides; pot size + slot diameter/height/number
tunable, slot angles tunable but LIMITED so water still flows through
by GRAVITY.

Two classes, both auto-CRUDE + persisted (object-coherence — every
tunable is a knob on a row, no hidden geometry):

  PotDefinition — the parametric vessel: size, wall/base thickness,
                  shape, and the material it is made of (a
                  MaterialsScienceMaterial, ceramic/geopolymer).
  PotHole       — one bored slot, a child row keyed to its pot: kind
                  (input/output), diameter, height up the wall,
                  azimuth (which side), and bore angle (clamped so
                  outputs stay gravity-fed).

The geometry MATH (validation, the gravity constraint, hole
generation) lives in pot_geometry.py; materials in
pot_materials_seed.py.

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence)
  - aquaponics.pot_geometry / aquaponics.pot_api
@see /AQUAPONICS_MODULE_PLAN.md
"""

from objectTreeDecorators import treeObject, treeObjectInit

#: Vessel profiles. 'tapered' = a frustum (top diameter != base).
POT_SHAPES = ('cylinder', 'tapered')

#: Hole roles. Higher holes fill, lower holes drain (Dustin).
HOLE_KINDS = ('input', 'output')

#: Bore angle is TUNABLE BUT LIMITED — beyond this the slot would
#: breach the wall or lose structural sense. Degrees from horizontal.
MAX_ABS_ANGLE_DEG = 30.0

#: An output must be at least horizontal to drain; a small downhill is
#: recommended so it drains reliably rather than pooling at the lip.
MIN_OUTPUT_DOWNHILL_DEG = 0.0
RECOMMENDED_OUTPUT_DOWNHILL_DEG = 2.0

#: "On opposite sides": the input group and output group should sit at
#: least this far apart around the wall (ideal 180 degrees).
MIN_SIDE_SEPARATION_DEG = 90.0
IDEAL_SIDE_SEPARATION_DEG = 180.0


class PotDefinition(treeObject):
    """One parametric self-watering pot."""

    @treeObjectInit
    def __init__(
        self,
        # kebab-case unique key ('demo-herb-pot').
        name: str = '',
        display_name: str = '',
        description: str = '',
        # POT_SHAPES entry.
        shape: str = 'cylinder',
        # Outer diameters (mm). Equal → cylinder; differ → tapered
        # frustum (top vs base).
        outer_top_diameter_mm: float = 200.0,
        outer_base_diameter_mm: float = 200.0,
        # Overall vessel height (mm), outer base to rim.
        height_mm: float = 250.0,
        # Wall + base thickness (mm) — the waterproof shell.
        wall_thickness_mm: float = 8.0,
        base_thickness_mm: float = 12.0,
        # The material this pot is made of — a MaterialsScienceMaterial
        # (a waterproof ceramic/geopolymer). '' = unassigned.
        material_name: str = '',
        # Optional bottom reservoir height (mm) — the self-watering
        # water store below the soil. 0 = the output holes alone set
        # the maintained level (aqp-3 hydraulics uses this).
        reservoir_height_mm: float = 0.0,
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.display_name = display_name
        self.description = description
        self.shape = shape
        self.outer_top_diameter_mm = outer_top_diameter_mm
        self.outer_base_diameter_mm = outer_base_diameter_mm
        self.height_mm = height_mm
        self.wall_thickness_mm = wall_thickness_mm
        self.base_thickness_mm = base_thickness_mm
        self.material_name = material_name
        self.reservoir_height_mm = reservoir_height_mm
        self.notes = notes


class PotHole(treeObject):
    """One bored slot in a pot's wall (a child row of its pot)."""

    @treeObjectInit
    def __init__(
        self,
        # unique key ('demo-herb-pot-input-1').
        name: str = '',
        # The PotDefinition this hole belongs to.
        pot_name: str = '',
        # HOLE_KINDS entry.
        kind: str = 'input',
        # Bore diameter (mm).
        diameter_mm: float = 10.0,
        # Height of the hole CENTER up the wall (mm from outer base).
        height_mm: float = 50.0,
        # Position around the wall (degrees, 0-360) — which side.
        azimuth_deg: float = 0.0,
        # Bore inclination (degrees from horizontal). POSITIVE = the
        # outer opening sits LOWER than the inner (downhill-out, so an
        # output drains by gravity); negative = uphill-out (would trap
        # water). Clamped to +/- MAX_ABS_ANGLE_DEG.
        angle_deg: float = 0.0,
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.pot_name = pot_name
        self.kind = kind
        self.diameter_mm = diameter_mm
        self.height_mm = height_mm
        self.azimuth_deg = azimuth_deg
        self.angle_deg = angle_deg
        self.notes = notes
