"""
@module aquaponics.objects.plant_growth.PlantGrowthModel

Row class PlantGrowthModel of the aquaponics module — one class per file (design §7), split
from plant_growth_basis.py (sap-2c). The class docstring below is the explanation.
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
