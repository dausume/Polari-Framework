"""
@cross-cutting
@module aquaponics.plant_growth_basis
@tags @xc:bindings

aqp-8 — PlantGrowthModel: the per-part growth knobs, a SIBLING row
keyed to an aqp-4 PlantPart (extends aqp-4, does not rebuild it —
file-size-decomposition + "reuse PlantPart, don't duplicate"). One
row per part carries how that part grows and its volume->mass density
(the interaction currency Dustin asked for).

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence)
  - aquaponics.plant_growth (the integrator reads these)
@see /AQUAPONICS_PHASE2_PLAN.md §aqp-8
"""

from objectTreeDecorators import treeObject, treeObjectInit


class PlantGrowthModel(treeObject):
    """Per-part growth parameters, referencing a PlantPart by name."""

    @treeObjectInit
    def __init__(
        self,
        # unique key ('sweet-basil-leaf-growth').
        name: str = '',
        # The PlantPart this models (aqp-4 row, by name).
        part_name: str = '',
        # Asymptotic volume (cm3) the logistic saturates at. Defaults
        # to the part's mature_volume_cm3 when 0.
        max_volume_cm3: float = 0.0,
        # Logistic growth-rate parameter (per day).
        growth_rate: float = 0.12,
        # Starting condition (healthy/stressed/senescing/failed).
        condition: str = 'healthy',
        # g dry / cm3 — converts per-mass composition to per-VOLUME
        # (the interaction currency). Defaults to the part's
        # dry_density_g_cm3 when 0.
        volume_density_g_cm3: float = 0.0,
        provenance_id: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.part_name = part_name
        self.max_volume_cm3 = max_volume_cm3
        self.growth_rate = growth_rate
        self.condition = condition
        self.volume_density_g_cm3 = volume_density_g_cm3
        self.provenance_id = provenance_id
        self.notes = notes
