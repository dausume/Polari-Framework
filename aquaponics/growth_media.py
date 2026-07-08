"""
@cross-cutting
@module aquaponics.growth_media
@tags @xc:bindings

Multiscale soil + water + nutrient profiles (aqp-2). Dustin 2026-07-08:
"multiscale soil definitions, and multiscale water definitions with
nutrient profiles for both … water has an aquaponic or hydroponic
source and … tunable nutrient profiles."

Four classes, all auto-CRUDE + persisted (object-coherence — the
recipe IS the row, every concentration a knob):

  NutrientSpecies  — the shared vocabulary: one row per nutrient/gas
                     (nitrate-N, P, K, …, dissolved-O2, dissolved-CO2)
                     with role, unit, and a healthy typical range.
                     Grounds both media profiles AND per-part plant
                     I/O (aqp-4).
  NutrientProfile  — a named set of concentrations over species, with
                     pH / EC / temperature. Referenced by soils AND
                     waters; tunable.
  SoilDefinition   — a growing medium as a MULTISCALE object: bulk
                     hydrology (field capacity, wilting point,
                     conductivity, CEC) + per-scale structure
                     descriptors (aggregate → pore → colloid).
  WaterDefinition  — the aquaponic/hydroponic solution as a MULTISCALE
                     object: bulk state (T, pH, EC, dissolved gases) +
                     source (kind + feed rate) + per-scale descriptors
                     (ionic ↔ bulk-flow).

Analysis math lives in media_analysis.py.

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence)
  - aquaponics.media_analysis / aquaponics.media_api
@see /AQUAPONICS_MODULE_PLAN.md
"""

from objectTreeDecorators import treeObject, treeObjectInit

NUTRIENT_ROLES = ('macronutrient', 'secondary', 'micronutrient',
                  'dissolved-gas', 'beneficial')
WATER_SOURCES = ('aquaponic', 'hydroponic', 'rainwater', 'municipal',
                 'well')
SOIL_TEXTURES = ('sand', 'loam', 'silt', 'clay', 'peat', 'coir',
                 'perlite-mix', 'rockwool', 'clay-pellet')


class NutrientSpecies(treeObject):
    """One nutrient or dissolved gas in the shared vocabulary."""

    @treeObjectInit
    def __init__(
        self,
        # kebab-case unique key ('nitrate-n').
        name: str = '',
        display_name: str = '',
        # Chemical shorthand ('NO3-N').
        symbol: str = '',
        # NUTRIENT_ROLES entry.
        role: str = 'macronutrient',
        # Concentration unit for solution values ('mg/L').
        unit: str = 'mg/L',
        # Whether it moves within the plant (informs deficiency signs).
        plant_mobility: str = 'mobile',
        # A healthy solution range (for hydroponic/aquaponic water).
        typical_min: float = None,
        typical_max: float = None,
        description: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.display_name = display_name
        self.symbol = symbol
        self.role = role
        self.unit = unit
        self.plant_mobility = plant_mobility
        self.typical_min = typical_min
        self.typical_max = typical_max
        self.description = description
        self.notes = notes


class NutrientProfile(treeObject):
    """A named concentration set over NutrientSpecies (tunable)."""

    @treeObjectInit
    def __init__(
        self,
        # kebab-case unique key ('leafy-greens-hydroponic').
        name: str = '',
        display_name: str = '',
        description: str = '',
        # {species_name: concentration} in each species' unit (JSON).
        concentrations_json: str = '{}',
        # Solution chemistry knobs.
        ph: float = 6.0,
        electrical_conductivity_ds_m: float = 1.5,
        temperature_c: float = 20.0,
        # 'water-mg-per-L' (solution) or 'soil-mg-per-kg' (extract).
        basis: str = 'water-mg-per-L',
        source: str = '',
        provenance_id: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.display_name = display_name
        self.description = description
        self.concentrations_json = concentrations_json
        self.ph = ph
        self.electrical_conductivity_ds_m = \
            electrical_conductivity_ds_m
        self.temperature_c = temperature_c
        self.basis = basis
        self.source = source
        self.provenance_id = provenance_id
        self.notes = notes


class SoilDefinition(treeObject):
    """A growing medium — multiscale structure + bulk hydrology."""

    @treeObjectInit
    def __init__(
        self,
        # kebab-case unique key ('coir-perlite-mix').
        name: str = '',
        display_name: str = '',
        description: str = '',
        # SOIL_TEXTURES entry.
        texture: str = 'loam',
        # Bulk hydrology (volumetric fractions unless noted).
        bulk_density_kg_m3: float = 1300.0,
        particle_density_kg_m3: float = 2650.0,
        porosity: float = None,   # None → derived from densities
        saturation_vol: float = 0.45,
        field_capacity_vol: float = 0.30,
        wilting_point_vol: float = 0.12,
        hydraulic_conductivity_mm_hr: float = 20.0,
        cation_exchange_cmol_kg: float = 15.0,
        organic_matter_fraction: float = 0.05,
        # The soil-native nutrient store (→ NutrientProfile).
        nutrient_profile_name: str = '',
        # Per-scale structure descriptors (JSON list):
        # [{"scale":"aggregate","grainSizeUm":...,"role":...}, ...] —
        # the MULTISCALE definition (aggregate → pore → colloid).
        scales_json: str = '[]',
        provenance_id: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.display_name = display_name
        self.description = description
        self.texture = texture
        self.bulk_density_kg_m3 = bulk_density_kg_m3
        self.particle_density_kg_m3 = particle_density_kg_m3
        self.porosity = porosity
        self.saturation_vol = saturation_vol
        self.field_capacity_vol = field_capacity_vol
        self.wilting_point_vol = wilting_point_vol
        self.hydraulic_conductivity_mm_hr = \
            hydraulic_conductivity_mm_hr
        self.cation_exchange_cmol_kg = cation_exchange_cmol_kg
        self.organic_matter_fraction = organic_matter_fraction
        self.nutrient_profile_name = nutrient_profile_name
        self.scales_json = scales_json
        self.provenance_id = provenance_id
        self.notes = notes


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
