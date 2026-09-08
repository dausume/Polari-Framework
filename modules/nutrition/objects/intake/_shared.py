"""@module nutrition.objects.intake._shared — what the intake row classes share (constants, seeds, helpers); split from intake_basis.py (sap-2c)."""

INTAKE_SOURCES = ('planned-confirmed', 'logged', 'estimated')
_PROV = 'mpa-4 (MEAL_PLANNING_APP_PLAN.md)'
def _ir(name, date, slot, template, variation, note=''):
    return {'name': name, 'person_name': 'demo-alex', 'date': date,
            'slot': slot, 'template_name': template,
            'variation_name': variation, 'scale': 1.0,
            'time_hhmm': '', 'source': 'logged',
            'plan_entry_name': '', 'is_prior': True,
            'provenance_id': _PROV,
            'notes': note or 'demo intake — replace with real logs'}
SEED_INTAKE_RECORDS = [
    _ir('demo-alex-2026-08-31-breakfast', '2026-08-31', 'breakfast',
        'omelet-breakfast', 'omelet-breakfast-base'),
    _ir('demo-alex-2026-08-31-dinner', '2026-08-31', 'dinner',
        'chicken-bowl-dinner', 'chicken-bowl-dinner-base'),
    _ir('demo-alex-2026-09-01-breakfast', '2026-09-01', 'breakfast',
        'omelet-breakfast', 'omelet-breakfast-base'),
    _ir('demo-alex-2026-09-01-dinner', '2026-09-01', 'dinner',
        'chicken-bowl-dinner', 'chicken-bowl-dinner-tofu'),
]
