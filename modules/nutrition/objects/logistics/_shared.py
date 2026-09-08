"""@module nutrition.objects.logistics._shared — what the logistics row classes share (constants, seeds, helpers); split from logistics_basis.py (sap-2c)."""

_PROV = 'mlg-1'
SEED_MEAL_LOGISTICS = [
    {'name': 'demo-alex-week-d2-dinner-demo-sam', 'entry_name': 'demo-alex-week-d2-dinner',
     'person_name': 'demo-sam', 'situation_name': 'at-workplace-cold',
     'container_tool_name': 'insulated-lunchbox', 'cold_pack_count': 2, 'pack_when': 'morning',
     'is_prior': True, 'provenance_id': _PROV, 'notes': 'demo: Sam eats day-2 dinner on shift'},
]
EATING_PRIORS = {'breakfast': 15.0, 'brunch': 30.0, 'lunch': 30.0, 'linner': 35.0,
                 'dinner': 40.0, 'snack': 10.0}
SEED_MEAL_TIME_PROFILES = [
    {'name': f'{p}-{slot}', 'person_name': p, 'slot': slot, 'eating_min': m,
     'fidelity': 'estimate', 'is_prior': True, 'provenance_id': _PROV,
     'notes': 'household prior — no literature worth citing; refined from observations'}
    for p in ('demo-alex', 'demo-sam') for slot, m in EATING_PRIORS.items()
]
