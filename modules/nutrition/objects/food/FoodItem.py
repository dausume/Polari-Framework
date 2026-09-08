"""
@module nutrition.objects.food.FoodItem

Row class FoodItem of the nutrition module — one class per file (design §7), split
from food_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class FoodItem(treeObject):
    """One edible harvest product from a plant."""

    @treeObjectInit
    def __init__(
        self,
        # kebab-case unique key ('basil-leaf').
        name: str = '',
        display_name: str = '',
        # The aqp-4 PlantDefinition this is harvested from (by name).
        plant_name: str = '',
        # JSON list of PlantPart names that are eaten.
        edible_parts_json: str = '[]',
        # PREPARATIONS entry — 'fermented' is how plant B12 appears.
        preparation: str = 'raw',
        # Fresh -> prepared mass loss (0-1); e.g. drying/cooking.
        moisture_loss_fraction: float = 0.0,
        # Fresh mass is mostly water; dry_matter in aqp-4 is small.
        # This factor converts dry-part mass back to FRESH edible mass
        # (1 / dry_matter_fraction ~ 8-12 for leafy greens). 0 = derive
        # from the part's dry_matter_fraction.
        fresh_to_dry_ratio: float = 0.0,
        # nmp-0: FDC linkage — the exact FoodData Central row this
        # item's composition came from (0 = not FDC-linked, e.g. our
        # own grown foods with estimated contents).
        fdc_id: int = 0,
        # 'foundation' | 'sr_legacy' | '' — which FDC dataset the id
        # lives in (they are separate releases with separate ids).
        fdc_dataset: str = '',
        # nmp-2 (decision 9): glycemic index of the food AS EATEN
        # (Atkinson 2008 published tables; 0 = unknown — honest
        # absence, never a guess). Raw staples carry the cooked
        # value with the caveat in gi_source.
        gi_value: float = 0.0,
        gi_source: str = '',
        provenance_id: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.display_name = display_name
        self.plant_name = plant_name
        self.edible_parts_json = edible_parts_json
        self.preparation = preparation
        self.moisture_loss_fraction = moisture_loss_fraction
        self.fresh_to_dry_ratio = fresh_to_dry_ratio
        self.fdc_id = fdc_id
        self.fdc_dataset = fdc_dataset
        self.gi_value = gi_value
        self.gi_source = gi_source
        self.provenance_id = provenance_id
        self.notes = notes
