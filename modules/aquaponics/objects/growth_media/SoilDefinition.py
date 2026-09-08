"""
@module aquaponics.objects.growth_media.SoilDefinition

Row class SoilDefinition of the aquaponics module — one class per file (design §7), split
from growth_media_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

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
