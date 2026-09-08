"""@module nutrition.objects.weight._shared — what the weight row classes share (constants, seeds, helpers); split from weight_basis.py (sap-2c)."""

SEED_WEIGHT_OBSERVATIONS = [
    {'name': f'demo-alex-{d}', 'person_name': 'demo-alex',
     'date': d, 'day_index': i, 'weight_kg': w,
     'context': 'morning', 'is_prior': True,
     'provenance_id': 'mpa-5',
     'notes': 'demo observation — replace with real measurements'}
    for i, (d, w) in enumerate((
        ('2026-08-25', 80.4), ('2026-08-28', 80.1),
        ('2026-08-31', 79.8), ('2026-09-01', 79.9)))
]
