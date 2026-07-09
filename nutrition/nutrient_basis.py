"""
@cross-cutting
@module nutrition.nutrient_basis
@tags @xc:bindings

nut-1 — the shared dietary-nutrient vocabulary + Recommended Daily
Allowance reference data. Two treeObjects (auto-CRUDE + persisted):

  DietaryNutrient    one nutrient a household must hit — its category,
                     unit, role, and whether plants can supply it
                     (honest-absence: B12 / iodine / sodium / chloride
                     are NOT plant-native).
  NutrientReference  the RDA/AI basis for a demographic band, keyed to a
                     DietaryNutrient BY NAME — so the person profiler
                     (nut-3) scales every need from ONE sourced table,
                     never magic numbers.

Standing principles: object-coherence (every nutrient + RDA is a
configurable row), knobs-and-suggestions, honest-absence (missing
plant-availability = a named flag), labels-travel-with-numbers (every
reference carries its source + prior flag).

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence)
  - nutrition.person_analysis (reads references), nutrition.nutrient_seed
@see /HOUSEHOLD_NUTRITION_PLAN.md §nut-1
"""

from objectTreeDecorators import treeObject, treeObjectInit

#: Broad nutrient families (drive UI grouping + which are macros).
NUTRIENT_CATEGORIES = ('macro', 'vitamin', 'mineral', 'electrolyte',
                       'trace', 'fatty-acid')

#: Can a hydroponic/plant system supply it?
#:   'common' — readily from the plant roster
#:   'hard'   — possible but awkward (e.g. via fermentation)
#:   'none'   — NOT plant-native; needs the saltwater food forest or
#:              another source (the gap nut-5 names honestly).
PLANT_AVAILABILITY = ('common', 'hard', 'none')


class DietaryNutrient(treeObject):
    """One nutrient the household nutrition ledger tracks."""

    @treeObjectInit
    def __init__(
        self,
        # kebab-case unique key ('vitamin-c').
        name: str = '',
        display_name: str = '',
        # NUTRIENT_CATEGORIES entry.
        category: str = 'vitamin',
        # Reporting unit ('mg' / 'ug' / 'g' / 'kcal' / 'IU').
        unit: str = 'mg',
        # Free-text physiological role ('immunity & collagen').
        role: str = '',
        # PLANT_AVAILABILITY entry — the honesty seam.
        plant_availability: str = 'common',
        # For a 'none'/'hard' nutrient, WHERE it actually comes from.
        alternate_source: str = '',
        provenance_id: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.display_name = display_name
        self.category = category
        self.unit = unit
        self.role = role
        self.plant_availability = plant_availability
        self.alternate_source = alternate_source
        self.provenance_id = provenance_id
        self.notes = notes


class NutrientReference(treeObject):
    """The RDA/AI for one nutrient over a demographic band.

    The person profiler matches the row whose (sex, age_min..age_max)
    contains the person, then scales by period. `rda_per_day` is the
    target; `upper_limit_per_day` is the toxicity ceiling (0 = none
    established). `is_prior` flags an AI/estimate vs a firm RDA."""

    @treeObjectInit
    def __init__(
        self,
        # unique key ('vitamin-c-female-19-50').
        name: str = '',
        # The DietaryNutrient this bounds (by name).
        nutrient_name: str = '',
        # 'any' | 'male' | 'female'.
        sex: str = 'any',
        age_min: float = 19.0,
        age_max: float = 120.0,
        # Recommended intake per day (in the nutrient's unit).
        rda_per_day: float = 0.0,
        # Tolerable upper intake per day (0 = none established).
        upper_limit_per_day: float = 0.0,
        # For nutrients that scale with body mass (e.g. protein), the
        # per-kg basis the profiler prefers over the flat RDA (0 = use
        # the flat rda_per_day).
        per_kg_body_mass: float = 0.0,
        source: str = 'NIH DRI',
        is_prior: bool = False,
        provenance_id: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.nutrient_name = nutrient_name
        self.sex = sex
        self.age_min = age_min
        self.age_max = age_max
        self.rda_per_day = rda_per_day
        self.upper_limit_per_day = upper_limit_per_day
        self.per_kg_body_mass = per_kg_body_mass
        self.source = source
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes
