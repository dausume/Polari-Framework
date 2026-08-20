"""
@cross-cutting
@module nutrition.food_basis
@tags @xc:bindings

nut-2 — the FOOD side of the ledger: a harvest of a plant, and its
food-nutrition composition. Two treeObjects:

  FoodItem        an edible harvest product tied to an aqp-4
                  PlantDefinition + which PlantParts are eaten + how it
                  is prepared. Fermentation is how B12 legitimately
                  appears (honest — flagged on the item).
  NutrientContent the food-nutrition composition — RICHER than aqp-4's
                  ELEMENTAL composition_json (which exists for carbon
                  capture): vitamins + bioavailable minerals per 100 g
                  edible. One row per (food, nutrient) — a transparent,
                  tunable USDA-prior table.

Reuses the aquaponics self-watering-pot plant model: the same
sweet-basil PlantDefinition/PlantPart that grows in a flowing
self-watering pot (aqp-1/aqp-8) becomes a FoodItem here, so a plant
GROWN in the pot system yields a computable meal-nutrient harvest.

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence)
  - nutrition.harvest_analysis, nutrition.food_seed
@see /HOUSEHOLD_NUTRITION_PLAN.md §nut-2 + Appendix A
"""

from objectTreeDecorators import treeObject, treeObjectInit

PREPARATIONS = ('raw', 'cooked', 'flour', 'fermented', 'dried', 'sprouted')


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
        self.provenance_id = provenance_id
        self.notes = notes


class NutrientContent(treeObject):
    """One (food, nutrient) content value per 100 g edible."""

    @treeObjectInit
    def __init__(
        self,
        # unique key ('basil-leaf-vitamin-k').
        name: str = '',
        # The FoodItem (by name).
        food_name: str = '',
        # The DietaryNutrient (by name).
        nutrient_name: str = '',
        # Amount per 100 g edible, in the nutrient's unit.
        amount_per_100g: float = 0.0,
        unit: str = 'mg',
        # USDA FoodData Central value vs an estimate.
        is_prior: bool = True,
        source: str = 'USDA FDC',
        provenance_id: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.food_name = food_name
        self.nutrient_name = nutrient_name
        self.amount_per_100g = amount_per_100g
        self.unit = unit
        self.is_prior = is_prior
        self.source = source
        self.provenance_id = provenance_id
        self.notes = notes
