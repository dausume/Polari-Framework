"""@module nutrition.objects.condition._shared — what the condition row classes share (constants, seeds, helpers); split from condition_basis.py (sap-2c)."""

POSTURE = ('stated by you, never diagnosed here; we only steer '
           'toward meals that avoid known aggravators of the '
           'condition you named — comfort steering, not treatment '
           'or medical advice; your clinician\'s numbers always '
           'win')
_PROV = ('mpb-2 (MEAL_PLANNING_APP_PLAN §3b, ratified 2026-09-01); '
         'aggravator mappings ride the nmp-2 cited tolerance rows')
def _steer(condition, display, substances, guidance, citation,
           confidence='low', notes=''):
    import json as _json
    return {'condition': condition, 'name': f'steer-{condition}',
            'display_name': display,
            'aggravator_substances_json': _json.dumps(substances),
            'guidance': guidance, 'citation': citation,
            'confidence': confidence, 'is_prior': True,
            'provenance_id': _PROV, 'notes': notes}
SEED_CONDITION_STEERINGS = [
    _steer('reflux', 'Reflux / heartburn (stated)',
           ['meal-acidity', 'meal-fat-load',
            'reflux-trigger-categories'],
           'prefer meals with a lower high-acid mass share, and '
           'avoid the high-fat x large-meal combination; the '
           'trigger categories (carbonation, caffeine, mint, '
           'chocolate) are noted when present',
           'decision-9 reflux rows (dietary-trigger surveys, '
           'heterogeneous evidence)', 'low'),
    _steer('sodium-sensitive', 'Sodium-sensitive (stated)',
           ['sodium'],
           'prefer meals that keep the day comfortably under the '
           'sodium CDRR; single very salty meals are flagged',
           'NASEM 2019 sodium CDRR', 'ul-grade'),
    _steer('glycemic-sensitive', 'Glycemic-sensitive (stated)',
           ['glycemic-load'],
           'prefer meals under the published high-GL convention; '
           'spikes are flagged per meal',
           'Atkinson 2008 GI/GL tables (GL>20 = the published '
           'high convention)', 'moderate',
           notes='diabetes MANAGEMENT stays out of scope — this '
                 'is spike-avoidance steering only, per the '
                 'ratified no-diagnosis boundary'),
    _steer('fodmap-sensitive', 'FODMAP-sensitive (stated)',
           ['fructans', 'lactose', 'sorbitol', 'xylitol'],
           'prefer meals under the published low-FODMAP '
           'per-serve cutoffs where we can compute them; the '
           'ones we cannot compute from FDC data are named as '
           'gaps, never guessed',
           'Varney et al. 2017 published cutoffs', 'low'),
]
SEED_STATED_CONDITIONS = [
    {'name': 'demo-alex-reflux', 'person_name': 'demo-alex',
     'condition': 'reflux',
     'stated_reason': 'demo row — heartburn after large meals',
     'declared_date': '2026-09-01', 'is_prior': True,
     'provenance_id': _PROV,
     'notes': 'demo — replace with real declarations'},
]
