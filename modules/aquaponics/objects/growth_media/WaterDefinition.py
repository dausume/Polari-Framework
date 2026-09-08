"""
@module aquaponics.objects.growth_media.WaterDefinition

Row class WaterDefinition of the aquaponics module — one class per file (design §7), split
from growth_media_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class WaterDefinition(treeObject):
    """The aquaponic/hydroponic solution — multiscale + source."""

    @treeObjectInit
    def __init__(
        self,
        # kebab-case unique key ('tilapia-aquaponic-loop').
        name: str = '',
        display_name: str = '',
        description: str = '',
        # WATER_SOURCES entry.
        source_kind: str = 'aquaponic',
        # Source characteristics (JSON) — aquaponic: fish species,
        # stocking, feed rate; hydroponic: reservoir + dosing.
        source_params_json: str = '{}',
        # Bulk state.
        temperature_c: float = 22.0,
        ph: float = 6.8,
        electrical_conductivity_ds_m: float = 1.2,
        dissolved_oxygen_mg_l: float = 7.0,
        dissolved_co2_mg_l: float = 5.0,
        # Feed rate into the pot input holes (L/hr).
        flow_rate_l_per_hr: float = 1.0,
        # Dissolved nutrients (→ NutrientProfile).
        nutrient_profile_name: str = '',
        # Per-scale descriptors (JSON list): molecular/ionic ↔ bulk.
        scales_json: str = '[]',
        provenance_id: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.display_name = display_name
        self.description = description
        self.source_kind = source_kind
        self.source_params_json = source_params_json
        self.temperature_c = temperature_c
        self.ph = ph
        self.electrical_conductivity_ds_m = \
            electrical_conductivity_ds_m
        self.dissolved_oxygen_mg_l = dissolved_oxygen_mg_l
        self.dissolved_co2_mg_l = dissolved_co2_mg_l
        self.flow_rate_l_per_hr = flow_rate_l_per_hr
        self.nutrient_profile_name = nutrient_profile_name
        self.scales_json = scales_json
        self.provenance_id = provenance_id
        self.notes = notes
