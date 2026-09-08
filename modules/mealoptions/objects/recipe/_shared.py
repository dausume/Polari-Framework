"""@module mealoptions.objects.recipe._shared — what the recipe row classes share (constants, seeds, helpers); split from recipe_basis.py (sap-2c)."""

COOKING_METHODS = ('raw', 'boiled', 'steamed', 'baked', 'roasted',
                   'fried', 'sauteed', 'grilled', 'braised',
                   'simmered', 'microwaved')
def _line(recipe, food, grams, method='raw', yield_pct=100.0,
          retention='', order=0, prep=''):
    return {'name': f'{recipe}-{food}', 'recipe_name': recipe,
            'food_name': food, 'grams': grams, 'method': method,
            'yield_percent': yield_pct, 'retention_code': retention,
            'prep_note': prep, 'order': order, 'is_prior': True,
            'provenance_id': 'nmp-3'}
SEED_RECIPES = [
    {'name': 'chicken-rice-bowl', 'display_name': 'Chicken rice bowl',
     'description': 'Grilled chicken over rice with steamed broccoli.',
     'servings': 2.0, 'origin': 'hand-authored', 'is_prior': True,
     'provenance_id': 'nmp-3',
     'notes': 'demo recipe over the FDC starter pantry'},
    {'name': 'spinach-omelet', 'display_name': 'Spinach omelet',
     'description': 'Two-egg omelet with baby spinach in olive oil.',
     'servings': 1.0, 'origin': 'hand-authored', 'is_prior': True,
     'provenance_id': 'nmp-3',
     'notes': 'demo recipe over the FDC starter pantry'},
]
SEED_INGREDIENT_LINES = [
    # chicken-rice-bowl (2 servings)
    _line('chicken-rice-bowl', 'chicken-breast-raw', 300.0,
          method='grilled', yield_pct=70.0, retention='0801',
          order=1, prep='grilled, sliced'),
    _line('chicken-rice-bowl', 'rice-white-raw', 55.0,
          method='boiled', yield_pct=280.0, retention='0432',
          order=2, prep='dry weight; boils up ~2.8x. Portion sized '
                        'so the meal passes the decision-9 GL<=20 '
                        'gate at max scale — white rice is '
                        'high-GI, so the bowl stays rice-light'),
    _line('chicken-rice-bowl', 'broccoli-raw', 200.0,
          method='steamed', yield_pct=95.0, retention='3784',
          order=3),
    _line('chicken-rice-bowl', 'olive-oil', 15.0, order=4),
    # spinach-omelet (1 serving)
    _line('spinach-omelet', 'egg-whole-raw', 100.0,
          method='fried', yield_pct=88.0, retention='0103',
          order=1, prep='two large eggs'),
    _line('spinach-omelet', 'spinach-raw', 60.0,
          method='sauteed', yield_pct=65.0, retention='3004',
          order=2),
    _line('spinach-omelet', 'olive-oil', 10.0, order=3),
]
SEED_COOKING_STEPS = [
    {'name': 'chicken-rice-bowl-step-1',
     'recipe_name': 'chicken-rice-bowl', 'order': 1,
     'instruction': 'Boil the rice in 2:1 water until absorbed.',
     'method': 'boiled', 'duration_min': 18.0,
     'is_prior': True, 'provenance_id': 'nmp-3'},
    {'name': 'chicken-rice-bowl-step-2',
     'recipe_name': 'chicken-rice-bowl', 'order': 2,
     'instruction': 'Grill the chicken breast until done; slice.',
     'method': 'grilled', 'duration_min': 12.0,
     'is_prior': True, 'provenance_id': 'nmp-3'},
    {'name': 'chicken-rice-bowl-step-3',
     'recipe_name': 'chicken-rice-bowl', 'order': 3,
     'instruction': 'Steam the broccoli; assemble with the oil.',
     'method': 'steamed', 'duration_min': 6.0,
     'is_prior': True, 'provenance_id': 'nmp-3'},
    {'name': 'spinach-omelet-step-1',
     'recipe_name': 'spinach-omelet', 'order': 1,
     'instruction': 'Saute the spinach in half the oil; set aside.',
     'method': 'sauteed', 'duration_min': 3.0,
     'is_prior': True, 'provenance_id': 'nmp-3'},
    {'name': 'spinach-omelet-step-2',
     'recipe_name': 'spinach-omelet', 'order': 2,
     'instruction': 'Beat the eggs, fry, fold the spinach in.',
     'method': 'fried', 'duration_min': 5.0,
     'is_prior': True, 'provenance_id': 'nmp-3'},
]
