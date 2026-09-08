"""@module nutrition.objects.meal._shared — what the meal row classes share (constants, seeds, helpers); split from meal_basis.py (sap-2c)."""

SEED_MEAL_PLANS = [
    {'name': 'demo-alex-week', 'display_name': "Alex's demo week",
     'person_name': 'demo-alex', 'household_name': 'demo-household',
     'days': 3, 'start_date': '2026-09-01', 'is_prior': True,
     'provenance_id': 'mpa-5',
     'notes': 'demo plan — replace with a real week'},
]
SEED_MEAL_ENTRIES = [
    {'name': f'demo-alex-week-d{d}-{slot}',
     'plan_name': 'demo-alex-week', 'day_index': d, 'slot': slot,
     'template_name': t, 'variation_name': v, 'scale': 1.0,
     'time_hhmm': '', 'serving_split_json': '', 'is_prior': True,
     'provenance_id': 'mpa-5', 'notes': ''}
    for d, slot, t, v in (
        (1, 'breakfast', 'omelet-breakfast', 'omelet-breakfast-base'),
        (1, 'dinner', 'chicken-bowl-dinner',
         'chicken-bowl-dinner-base'),
        (2, 'breakfast', 'omelet-breakfast', 'omelet-breakfast-base'),
        (2, 'dinner', 'chicken-bowl-dinner',
         'chicken-bowl-dinner-tofu'),
        (3, 'dinner', 'chicken-bowl-dinner',
         'chicken-bowl-dinner-base'),
    )
]
