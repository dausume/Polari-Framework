"""
@module aquaponics.objects.growth_media.NutrientSpecies

Row class NutrientSpecies of the aquaponics module — one class per file (design §7), split
from growth_media_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

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
