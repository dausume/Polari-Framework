"""
@module foodstate.food_materials_basis

fsp-1 — the COMMON-BASE-INGREDIENTS roster (Dustin 2026-09-01:
"start putting together a database of common base ingredients").
One FoodMaterial identity row per base ingredient; nmp decision 8
(meals build STRICTLY from base ingredients + meats) makes this
roster the meal-planning vocabulary.

v1 roster = the 49 foods of the vendored, sha-pinned FDC subset
(`modules/nutrition/custom/vendor/fdc_foundation_subset.csv`, CC0,
retrieved 2026-08-20) — every identity resolves to a pinned fdc_id
from the vendor file itself, never from memory (derive-or-cite).
Extending the roster = add a slug + category here AND a vendored
row set; an identity without vendor rows would refuse coverage
honestly, not invent it.

The identity's name doubles as the pspp material key: composition
claims land on the canonical subject '<name>#as-defined'
(pspp sync-on-need — no MaterialState row is required to exist).

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence + seeds)
  - foodstate.custom.food_composition (claims + coverage)
  - foodstate.food_materials_selftest
"""

from objectTreeDecorators import treeObject, treeObjectInit

_PROV = ('fsp-1 roster (FOOD_STATE_PSPP_PLAN.md §4 fsp-1); identity '
         'set = the vendored FDC subset, nutrition/custom/vendor/README.md')

ROSTER_CATEGORIES = (
    'grain', 'legume', 'vegetable', 'fruit', 'meat-fish-egg',
    'dairy', 'oil-fat', 'nut-seed', 'flavor-base', 'pantry-staple',
)


class FoodMaterial(treeObject):
    """One base-ingredient identity — the food-side material row
    whose name anchors '<name>#<state>' subjects."""

    @treeObjectInit
    def __init__(
        self,
        # kebab-case identity, = the vendor food_slug ('tomato-raw').
        name: str = '',
        display_name: str = '',
        # ROSTER_CATEGORIES entry.
        roster_category: str = '',
        # Pinned FDC id — filled FROM the vendor file at seed build
        # (0 = not resolved; coverage reports it as a gap).
        fdc_id: int = 0,
        # 'foundation' | 'sr-legacy' (vendor fdc_dataset column).
        fdc_dataset: str = '',
        # FDC's own description for the pinned row.
        fdc_description: str = '',
        # Optional nut-2 FoodItem.name link (harvest loop) — '' = none.
        food_item_name: str = '',
        provenance_id: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.display_name = display_name
        self.roster_category = roster_category
        self.fdc_id = fdc_id
        self.fdc_dataset = fdc_dataset
        self.fdc_description = fdc_description
        self.food_item_name = food_item_name
        self.provenance_id = provenance_id
        self.notes = notes


#: slug → roster category, hand-curated (the only judgment here —
#: identities and numbers come from the vendor file).
ROSTER = {
    # grains + grain staples
    'flour-all-purpose': 'grain', 'flour-whole-wheat': 'grain',
    'oats-rolled': 'grain', 'pasta-dry': 'grain',
    'quinoa-raw': 'grain', 'rice-brown-raw': 'grain',
    'rice-white-raw': 'grain',
    # legumes
    'black-beans-dry': 'legume', 'chickpeas-dry': 'legume',
    'lentils-dry': 'legume', 'tofu-firm': 'legume',
    # vegetables
    'bell-pepper-red-raw': 'vegetable', 'broccoli-raw': 'vegetable',
    'carrot-raw': 'vegetable', 'celery-raw': 'vegetable',
    'cucumber-raw': 'vegetable', 'kale-raw': 'vegetable',
    'lettuce-romaine-raw': 'vegetable',
    'mushroom-white-raw': 'vegetable',
    'potato-russet-raw': 'vegetable', 'spinach-raw': 'vegetable',
    'sweet-potato-raw': 'vegetable', 'tomato-raw': 'vegetable',
    # flavor bases (the aromatics recipes start from)
    'garlic-raw': 'flavor-base', 'onion-raw': 'flavor-base',
    # fruits
    'apple-raw': 'fruit', 'avocado-raw': 'fruit',
    'banana-raw': 'fruit', 'blueberries-raw': 'fruit',
    'orange-raw': 'fruit', 'strawberries-raw': 'fruit',
    # meat / fish / egg
    'beef-chuck-raw': 'meat-fish-egg',
    'chicken-breast-raw': 'meat-fish-egg', 'cod-raw': 'meat-fish-egg',
    'egg-whole-raw': 'meat-fish-egg',
    'ground-beef-90-raw': 'meat-fish-egg',
    'pork-loin-raw': 'meat-fish-egg',
    'salmon-atlantic-raw': 'meat-fish-egg',
    'tilapia-raw': 'meat-fish-egg',
    'turkey-ground-raw': 'meat-fish-egg',
    # dairy
    'butter-unsalted': 'dairy', 'cheese-cheddar': 'dairy',
    'milk-whole': 'dairy', 'yogurt-plain-whole': 'dairy',
    # oils / fats
    'olive-oil': 'oil-fat',
    # nuts / seeds
    'almonds-raw': 'nut-seed', 'walnuts-raw': 'nut-seed',
    # pantry staples
    'salt-iodized': 'pantry-staple', 'sugar-white': 'pantry-staple',
}


def _display(slug):
    words = slug.replace('-raw', '').replace('-dry', '').split('-')
    return ' '.join(w.capitalize() for w in words)


def build_food_material_seeds(vendor_index=None):
    """Roster seeds with fdc identity RESOLVED FROM the vendor file
    (vendor_index: slug → {fdc_id, fdc_dataset, fdc_description},
    from food_composition.vendor_food_index). Unresolvable slugs
    keep fdc_id 0 — an honest gap, never a guess."""
    seeds = []
    for slug in sorted(ROSTER):
        info = (vendor_index or {}).get(slug, {})
        seeds.append({
            'name': slug,
            'display_name': _display(slug),
            'roster_category': ROSTER[slug],
            'fdc_id': int(info.get('fdc_id', 0) or 0),
            'fdc_dataset': info.get('fdc_dataset', ''),
            'fdc_description': info.get('fdc_description', ''),
            'food_item_name': '',
            'provenance_id': _PROV,
            'notes': ('' if info else
                      'no vendored FDC rows — coverage refuses for '
                      'this ingredient until data is vendored'),
        })
    return seeds
