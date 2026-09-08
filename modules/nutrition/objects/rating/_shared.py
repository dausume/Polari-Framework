"""@module nutrition.objects.rating._shared — what the rating row classes share (constants, seeds, helpers); split from rating_basis.py (sap-2c)."""

_PROV = 'mpb-8 (MEAL_PLANNING_APP_PLAN §3b)'
SEED_MEAL_RATINGS = [
    {'name': 'demo-alex-bowl-r1', 'person_name': 'demo-alex',
     'template_name': 'chicken-bowl-dinner',
     'variation_name': 'chicken-bowl-dinner-base', 'rating': 4,
     'note': 'demo — solid weeknight dinner', 'date': '2026-08-31',
     'intake_record_name': 'demo-alex-2026-08-31-dinner',
     'is_prior': True, 'provenance_id': _PROV, 'notes': ''},
    {'name': 'demo-alex-omelet-r1', 'person_name': 'demo-alex',
     'template_name': 'omelet-breakfast',
     'variation_name': 'omelet-breakfast-base', 'rating': 5,
     'note': 'demo — favorite breakfast', 'date': '2026-09-01',
     'intake_record_name': 'demo-alex-2026-09-01-breakfast',
     'is_prior': True, 'provenance_id': _PROV, 'notes': ''},
]
