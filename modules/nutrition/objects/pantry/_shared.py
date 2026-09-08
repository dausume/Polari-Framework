"""@module nutrition.objects.pantry._shared — what the pantry row classes share (constants, seeds, helpers); split from pantry_basis.py (sap-2c)."""

STORAGE_STATES = ('pantry', 'fridge', 'freezer')
_PROV = 'mpa-3 (MEAL_PLANNING_APP_PLAN.md)'
def _pi(name, food, qty, unit, storage, date='', note=''):
    return {'name': name, 'household_name': 'demo-household',
            'food_name': food, 'quantity': qty, 'unit': unit,
            'storage_state': storage, 'acquired_date': date,
            'source_location_name': '', 'price_paid': 0.0,
            'currency': 'USD', 'is_prior': True,
            'provenance_id': _PROV,
            'notes': note or 'demo pantry row — replace with yours'}
SEED_PANTRY_ITEMS = [
    _pi('demo-pantry-rice', 'rice-white-raw', 2.0, 'kg', 'pantry',
        '2026-08-20'),
    _pi('demo-pantry-eggs', 'egg-whole-raw', 8.0, 'each', 'fridge',
        '2026-08-28'),
    _pi('demo-pantry-spinach', 'spinach-raw', 1.0, 'bunch', 'fridge',
        '2026-08-31'),
    _pi('demo-pantry-chicken', 'chicken-breast-raw', 1.0, 'lb',
        'freezer', '2026-08-15'),
    _pi('demo-pantry-oil', 'olive-oil', 400.0, 'g', 'pantry',
        '2026-07-01'),
]
