"""
@cross-cutting
@module plant_morphology.organ_basis
@tags @xc:bindings, @xc:render-3d

3D stand-in / MOCK morphology models for plant organs + root systems —
parametric estimates, NOT photoreal meshes. Each organ is a shape
primitive with dimensions + count, giving a 3D bounding geometry and a
volume estimate the analysis reasons over (canopy envelope, root ball,
confinement). Own module + own data (separated cleanly from
aquaponics/nutrition), depends only on framework core.

Two treeObjects (auto-CRUDE + persisted — object-coherence):

  OrganModel       one organ TYPE of a plant (leaf / stem / branch /
                   root-visible / fruit / flower): a shape primitive
                   (ellipsoid, cylinder, cone, sphere, lamina) + its
                   dimensions + count + arrangement → a mock 3D form
                   and volume. The stand-in geometry until real meshes.
  RootSystemModel  the below-ground structure: spreading PATTERN,
                   natural spread radius + depth, root-ball density, and
                   the CONFINEMENT response knobs — can this plant be
                   dwarfed and kept in a pot indefinitely, and with what
                   root-prune cadence.

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence)
  - plant_morphology.morphology_analysis (geometry, root spread,
    confinement), SimSpace3D stand-in rendering later
@see /HOUSEHOLD_NUTRITION_PLAN.md, /AQUAPONICS_MODULE_PLAN.md
"""

from objectTreeDecorators import treeObject, treeObjectInit

#: Organ types we model a stand-in for.
ORGAN_TYPES = ('leaf', 'stem', 'branch', 'root-visible', 'fruit',
               'flower', 'tuber')

#: Shape primitives → the volume/bounding formula the analysis applies.
SHAPE_PRIMITIVES = ('ellipsoid', 'cylinder', 'cone', 'sphere', 'lamina')

#: Phyllotaxis / branching arrangement (informs canopy spread).
ARRANGEMENTS = ('rosette', 'basal', 'alternate', 'opposite', 'whorled',
                'vining')

#: Root spreading patterns — drive the natural envelope + confinement.
ROOT_PATTERNS = ('taproot', 'fibrous', 'spreading', 'rhizomatous')


class OrganModel(treeObject):
    """A parametric 3D stand-in for one organ type of a plant."""

    @treeObjectInit
    def __init__(
        self,
        # unique key ('sweet-basil-leaf-organ').
        name: str = '',
        # The aqp-4 PlantDefinition this belongs to (by name).
        plant_name: str = '',
        # ORGAN_TYPES entry.
        organ: str = 'leaf',
        display_name: str = '',
        # SHAPE_PRIMITIVES entry — how volume/bounds are computed.
        shape_primitive: str = 'ellipsoid',
        # Bounding dimensions of ONE organ (mm).
        length_mm: float = 40.0,
        width_mm: float = 20.0,
        thickness_mm: float = 3.0,
        # How many of this organ at maturity (drives total volume +
        # canopy fill).
        count: int = 20,
        # ARRANGEMENTS entry.
        arrangement: str = 'opposite',
        # Estimate vs measured.
        is_prior: bool = True,
        provenance_id: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.plant_name = plant_name
        self.organ = organ
        self.display_name = display_name
        self.shape_primitive = shape_primitive
        self.length_mm = length_mm
        self.width_mm = width_mm
        self.thickness_mm = thickness_mm
        self.count = count
        self.arrangement = arrangement
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes


class RootSystemModel(treeObject):
    """The below-ground structure + confinement/dwarfing response.

    The confinement knobs answer Dustin's question directly: can this
    plant be dwarfed and kept in a pot indefinitely? `dwarfable`,
    `confinement_tolerance`, and `root_prune_cadence_days` are the
    tunable estimate; morphology_analysis.confinement_assessment reads
    them against a pot's inner volume."""

    @treeObjectInit
    def __init__(
        self,
        # unique key ('sweet-basil-roots').
        name: str = '',
        plant_name: str = '',
        # ROOT_PATTERNS entry.
        pattern: str = 'fibrous',
        # The UNCONFINED mature root envelope (mm): a radius (spread)
        # and a depth. Volume ≈ a hemisphere/cone of this extent.
        natural_spread_radius_mm: float = 120.0,
        natural_depth_mm: float = 200.0,
        # Fraction of that envelope that is DENSE root ball (the part
        # that must physically fit a container) vs fine exploratory
        # roots. 1.0 = the whole envelope is dense.
        root_ball_fraction: float = 0.5,
        # 0-1: how well the plant tolerates being pot-bound (1 = thrives
        # root-restricted, e.g. many herbs/strawberries; 0 = declines).
        confinement_tolerance: float = 0.6,
        # Can it be kept DWARFED (canopy shrinks with the root ball
        # rather than the plant failing)?
        dwarfable: bool = True,
        # Root-prune interval (days) to hold it indefinitely in a fixed
        # pot; 0 = no root pruning needed (naturally self-limiting).
        root_prune_cadence_days: float = 0.0,
        # The estimate: can it live in a pot indefinitely (with the
        # cadence above)? honest bool the analysis re-derives + explains.
        indefinite_in_pot: bool = True,
        is_prior: bool = True,
        provenance_id: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.plant_name = plant_name
        self.pattern = pattern
        self.natural_spread_radius_mm = natural_spread_radius_mm
        self.natural_depth_mm = natural_depth_mm
        self.root_ball_fraction = root_ball_fraction
        self.confinement_tolerance = confinement_tolerance
        self.dwarfable = dwarfable
        self.root_prune_cadence_days = root_prune_cadence_days
        self.indefinite_in_pot = indefinite_in_pot
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes
