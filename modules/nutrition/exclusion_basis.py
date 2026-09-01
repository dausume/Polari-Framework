"""
@cross-cutting
@module nutrition.exclusion_basis
@tags @xc:bindings

mpb-1 — allergen/intolerance exclusions as data (MEAL_PLANNING_APP_
PLAN §3b, ratified 2026-09-01: a SAFETY FILTER, never diagnosis):

  FoodAllergenFlag   one roster food × one FDA major-9 allergen
                     class it contains BY IDENTITY (cheddar IS
                     milk; pasta IS wheat). Identity facts, not
                     lab analysis — cross-contact/processing
                     contamination is explicitly OUT (named).
  PersonExclusion    one person's declared exclusion: an allergen
                     class or a single food, with THEIR stated
                     reason and severity. Declared, never
                     inferred; 'allergy-hard' excludes absolutely,
                     'preference-soft' ranks down with a note.

FDA major-9 vocabulary: milk, egg, fish, crustacean-shellfish,
tree-nut, peanut, wheat, soybean, sesame (FASTER Act 2021 added
sesame). Roster foods that carry none of these seed no row —
absence of a flag row for an exotic future food is NOT evidence of
safety; the report says so.

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence)
  - nutrition.exclusion_analysis, mealplanning_api
@see AI-Notes/plans/MEAL_PLANNING_APP_PLAN.md §3b mpb-1
"""

from objectTreeDecorators import treeObject, treeObjectInit

#: FDA major-9 allergen classes (FASTER Act 2021 list).
ALLERGEN_CLASSES = (
    'milk', 'egg', 'fish', 'crustacean-shellfish', 'tree-nut',
    'peanut', 'wheat', 'soybean', 'sesame',
)

EXCLUSION_SEVERITIES = ('allergy-hard', 'intolerance-hard',
                        'preference-soft')

_PROV = ('mpb-1 (MEAL_PLANNING_APP_PLAN §3b); allergen class = '
         'food IDENTITY under the FDA major-9 vocabulary '
         '(FASTER Act 2021) — not a lab analysis')


class FoodAllergenFlag(treeObject):
    """One food × one allergen class it contains by identity."""

    @treeObjectInit
    def __init__(
        self,
        # unique key ('cheese-cheddar-milk').
        name: str = '',
        food_name: str = '',
        # ALLERGEN_CLASSES entry.
        allergen_class: str = '',
        # why the flag holds ('is a dairy product').
        basis: str = '',
        is_prior: bool = True,
        provenance_id: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.food_name = food_name
        self.allergen_class = allergen_class
        self.basis = basis
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes


class PersonExclusion(treeObject):
    """One person's DECLARED exclusion (never inferred)."""

    @treeObjectInit
    def __init__(
        self,
        # unique key ('demo-alex-tree-nut').
        name: str = '',
        person_name: str = '',
        # exactly one of these two is set.
        allergen_class: str = '',
        food_name: str = '',
        # EXCLUSION_SEVERITIES entry.
        severity: str = 'allergy-hard',
        # the person's own words ('diagnosed peanut allergy 2019',
        # 'dairy makes me ill', 'I just hate mushrooms').
        stated_reason: str = '',
        is_prior: bool = False,
        provenance_id: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.person_name = person_name
        self.allergen_class = allergen_class
        self.food_name = food_name
        self.severity = severity
        self.stated_reason = stated_reason
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes


def _flag(food, allergen, basis):
    return {'name': f'{food}-{allergen}', 'food_name': food,
            'allergen_class': allergen, 'basis': basis,
            'is_prior': True, 'provenance_id': _PROV, 'notes': ''}


#: Identity-derived flags over the 49-food roster. Peanut /
#: crustacean-shellfish / sesame have no roster members yet — the
#: classes exist so future foods flag correctly.
SEED_FOOD_ALLERGEN_FLAGS = [
    _flag('milk-whole', 'milk', 'is milk'),
    _flag('yogurt-plain-whole', 'milk', 'cultured milk product'),
    _flag('butter-unsalted', 'milk', 'milk-fat product'),
    _flag('cheese-cheddar', 'milk', 'milk product'),
    _flag('egg-whole-raw', 'egg', 'is egg'),
    _flag('cod-raw', 'fish', 'is finfish'),
    _flag('salmon-atlantic-raw', 'fish', 'is finfish'),
    _flag('tilapia-raw', 'fish', 'is finfish'),
    _flag('almonds-raw', 'tree-nut', 'is a tree nut'),
    _flag('walnuts-raw', 'tree-nut', 'is a tree nut'),
    _flag('flour-all-purpose', 'wheat', 'wheat flour'),
    _flag('flour-whole-wheat', 'wheat', 'wheat flour'),
    _flag('pasta-dry', 'wheat', 'durum-wheat product'),
    _flag('tofu-firm', 'soybean', 'soybean curd'),
]

#: A demo declared exclusion so pages/selftests exercise the path.
SEED_PERSON_EXCLUSIONS = [
    {'name': 'demo-alex-tree-nut', 'person_name': 'demo-alex',
     'allergen_class': 'tree-nut', 'food_name': '',
     'severity': 'allergy-hard',
     'stated_reason': 'demo row — declared tree-nut allergy',
     'is_prior': True, 'provenance_id': _PROV,
     'notes': 'demo — replace with real declarations'},
]
