"""
@module aquaponics.objects.growth_media.NutrientProfile

Row class NutrientProfile of the aquaponics module — one class per file (design §7), split
from growth_media_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

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
