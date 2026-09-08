"""
@module plant_morphology.objects.organ.RootSystemModel

Row class RootSystemModel of the plant_morphology module — one class per file (design §7), split
from organ_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

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
        # --- Free Soil Constants additions (2026-07-15, plant-growth-
        # sim phase 1 — Dustin: root branching needs "usual root
        # density when it has only free soil" + "how root thickness
        # changes with distance from plant core as a function of
        # growth"). All three are UNCONFINED references, same status
        # as natural_spread_radius_mm/natural_depth_mm above — the
        # confinement math (morphology_analysis.confinement_assessment)
        # scales them down for a specific pot, it never edits them. ---
        # Root dry-mass density WITHIN the occupied soil envelope at
        # full unconfined growth (g root dry mass / cm3 of SOIL the
        # roots have colonized — a real soil-science quantity,
        # distinct from PlantGrowthModel.volume_density_g_cm3, which is
        # the density of the root TISSUE itself, not how densely it
        # fills the soil around it).
        soil_root_density_g_per_cm3: float = 0.02,
        # Root diameter AT the core (seed origin) once fully mature
        # (mm) — the taper profile's starting point.
        root_core_diameter_mm: float = 3.0,
        # Taper exponent: diameter(distance) = root_core_diameter_mm *
        # (1 - distance/envelope_extent) ** root_taper_exponent, floored
        # at root_hair_diameter_mm. Higher = thins out faster near the
        # core; lower = a more gradual taper reaching further before
        # thinning. 1.0 = linear taper.
        root_taper_exponent: float = 1.6,
        # Floor diameter (mm) roots never taper below, however far from
        # the core — real root hairs, not a mathematical zero.
        root_hair_diameter_mm: float = 0.2,
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
        self.soil_root_density_g_per_cm3 = soil_root_density_g_per_cm3
        self.root_core_diameter_mm = root_core_diameter_mm
        self.root_taper_exponent = root_taper_exponent
        self.root_hair_diameter_mm = root_hair_diameter_mm
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes
