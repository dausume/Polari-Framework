"""@module nutrition.objects.fulfillment._shared — what the fulfillment row classes share (constants, seeds, helpers); split from fulfillment_basis.py (sap-2c)."""

SEED_GARDEN_PLANS = [
    {'name': 'starter-garden', 'display_name': 'Starter garden',
     'household_name': 'demo-household', 'meal_plan_name': '',
     'plantings_json': '{"basil-leaf": 6, "kale-leaf": 8}',
     'harvest_period_days': 30.0,
     'is_prior': True, 'provenance_id': 'nmp-7',
     'notes': 'the nut-2 basil+kale pot roster as a coverage demo'},
]
