"""
@module aquaponics.objects.plant.PlantDefinition

Row class PlantDefinition of the aquaponics module — one class per file (design §7), split
from plant_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class PlantDefinition(treeObject):
    """One plant's whole-organism profile."""

    @treeObjectInit
    def __init__(
        self,
        # kebab-case unique key ('sweet-basil').
        name: str = '',
        display_name: str = '',
        species: str = '',
        common_name: str = '',
        description: str = '',
        # Annual / perennial — informs default part fates.
        life_cycle: str = 'annual',
        # Full lifecycle length (days).
        lifetime_days: float = 120.0,
        # Growth stages (JSON list): [{"stage","startDay","endDay",
        # "growthFraction"}] — growthFraction is the share of mature
        # size reached by endDay (drives the lifetime integral).
        growth_stages_json: str = '[]',
        mature_height_mm: float = 400.0,
        mature_canopy_mm: float = 300.0,
        # Whole-plant logistic rate constant (per day) for NORMALIZED
        # GROWTH (2026-07-15, plant-growth-sim phase 1 — Dustin: "instead
        # of age we have normalized growth as the measure of 'age'").
        # A single 0-1 state per planting instance (aquaponics.
        # plant_growth_normalized.PotPlanting.normalized_growth) tracks
        # progress toward this species' Free Soil Constants; THIS rate
        # is the free-soil (unconfined, ideal-conditions) reference
        # speed — real conditions (water/soil supply) scale it down per
        # tick, confinement caps the CEILING it can reach, never the
        # rate itself. Distinct from PlantGrowthModel's per-PART rates
        # (aqp-8's raw-volume integrator, kept as-is) — this is the
        # whole-plant analog those never had.
        normalized_growth_rate_per_day: float = 0.045,
        provenance_id: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.display_name = display_name
        self.species = species
        self.common_name = common_name
        self.description = description
        self.life_cycle = life_cycle
        self.lifetime_days = lifetime_days
        self.growth_stages_json = growth_stages_json
        self.mature_height_mm = mature_height_mm
        self.mature_canopy_mm = mature_canopy_mm
        self.normalized_growth_rate_per_day = normalized_growth_rate_per_day
        self.provenance_id = provenance_id
        self.notes = notes
