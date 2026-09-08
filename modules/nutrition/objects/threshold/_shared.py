"""@module nutrition.objects.threshold._shared — what the threshold row classes share (constants, seeds, helpers); split from threshold_basis.py (sap-2c)."""

THRESHOLD_PERIODS = ('meal', 'day', 'week', 'month')
SEED_EATING_PATTERNS = [
    {'name': '2-meal', 'display_name': '2 meals a day',
     'slot_fractions_json':
         '[{"slot": "brunch", "fraction": 0.45},'
         ' {"slot": "dinner", "fraction": 0.55}]',
     'is_prior': True, 'provenance_id': 'nmp-1',
     'notes': 'convention prior — meal-distribution literature is '
              'thin; tune freely'},
    {'name': '3-meal', 'display_name': '3 meals a day',
     'slot_fractions_json':
         '[{"slot": "breakfast", "fraction": 0.25},'
         ' {"slot": "lunch", "fraction": 0.35},'
         ' {"slot": "dinner", "fraction": 0.40}]',
     'is_prior': True, 'provenance_id': 'nmp-1',
     'notes': 'convention prior — meal-distribution literature is '
              'thin; tune freely'},
    {'name': '3-small-2-snacks',
     'display_name': '3 small meals + 2 snacks',
     'slot_fractions_json':
         '[{"slot": "breakfast", "fraction": 0.25},'
         ' {"slot": "lunch", "fraction": 0.25},'
         ' {"slot": "dinner", "fraction": 0.30},'
         ' {"slot": "snack", "fraction": 0.10},'
         ' {"slot": "snack-2", "fraction": 0.10}]',
     'is_prior': True, 'provenance_id': 'nmp-1',
     'notes': 'convention prior — meal-distribution literature is '
              'thin; tune freely'},
]
