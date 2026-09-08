"""@module nutrition.objects.waste._shared — what the waste row classes share (constants, seeds, helpers); split from waste_basis.py (sap-2c)."""

WASTE_REASONS = ('spoiled', 'expired', 'plate-waste',
                 'over-prepped', 'other')
_PROV = 'mpb-4 (MEAL_PLANNING_APP_PLAN §3b)'
SEED_WASTE_RECORDS = [
    {'name': 'demo-waste-spinach', 'household_name':
     'demo-household', 'food_name': 'spinach-raw',
     'quantity': 0.5, 'unit': 'bunch', 'reason': 'spoiled',
     'date': '2026-08-30', 'pantry_item_name': '',
     'is_prior': True, 'provenance_id': _PROV,
     'notes': 'demo row — log real waste, it is the honest '
              'budget leak'},
]
