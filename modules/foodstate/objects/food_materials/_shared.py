"""@module foodstate.objects.food_materials._shared — what the food_materials row classes share (constants, seeds, helpers); split from food_materials_basis.py (sap-2c)."""

_PROV = ('fsp-1 roster (FOOD_STATE_PSPP_PLAN.md §4 fsp-1); identity '
         'set = the vendored FDC subset, nutrition/custom/vendor/README.md')
ROSTER_CATEGORIES = (
    'grain', 'legume', 'vegetable', 'fruit', 'meat-fish-egg',
    'dairy', 'oil-fat', 'nut-seed', 'flavor-base', 'pantry-staple',
)
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
