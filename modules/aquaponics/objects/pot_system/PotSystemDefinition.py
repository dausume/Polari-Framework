"""
@module aquaponics.objects.pot_system.PotSystemDefinition

Row class PotSystemDefinition of the aquaponics module — one class per file (design §7), split
from pot_system_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class PotSystemDefinition(treeObject):
    """One bound self-watering pot configuration."""

    @treeObjectInit
    def __init__(
        self,
        # kebab-case unique key ('demo-basil-aquaponic-tent').
        name: str = '',
        display_name: str = '',
        description: str = '',
        pot_name: str = '',
        soil_name: str = '',
        water_name: str = '',
        plant_name: str = '',
        atmosphere_name: str = '',
        # Optional aquaponics.light_basis.LightSourceDefinition name
        # (plant-growth-sim phase 8, 2026-07-15) — when set,
        # advance_growth's 'light' stress factor is computed from the
        # REAL geometric/spectral light field (aquaponics.custom.light_field)
        # instead of the static AtmosphereDefinition.
        # light_ppfd_umol_m2_s scalar. Empty = unchanged, existing
        # behavior (falls back to the atmosphere field).
        light_source_name: str = '',
        # Optional aquaponics.water_batch_basis.WaterBatchSchedule name
        # (plant-growth-sim phase 10, 2026-07-15) — when set, the
        # ACTIVE water source (which batch is currently governing the
        # pot) is resolved per-planting from the schedule and used for
        # BOTH the water-quality stress curves (phase 7) AND real
        # nutrient uptake (phase 10), OVERRIDING water_name for that
        # tick. Empty = unchanged, water_name is used directly.
        water_batch_schedule_name: str = '',
        # Persisted impact snapshot (JSON) — system_impact writes it;
        # scoring binds to it. Empty until first computed.
        impact_result_json: str = '',
        provenance_id: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.display_name = display_name
        self.description = description
        self.pot_name = pot_name
        self.soil_name = soil_name
        self.water_name = water_name
        self.plant_name = plant_name
        self.atmosphere_name = atmosphere_name
        self.light_source_name = light_source_name
        self.water_batch_schedule_name = water_batch_schedule_name
        self.impact_result_json = impact_result_json
        self.provenance_id = provenance_id
        self.notes = notes
