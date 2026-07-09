"""
@cross-cutting
@module nutrition.person_seed
@tags @xc:bindings

nut-3/4 demo — two people + a household, so the profiler + aggregation
have a live example. Idempotent-by-name.

@consumers
  - polariServer seed_pairs (persons before the household that lists them)
@see /HOUSEHOLD_NUTRITION_PLAN.md
"""

import json

SEED_PERSONS = [
    {
        'name': 'demo-alex', 'display_name': 'Alex (demo)',
        'sex': 'male', 'age_years': 34.0, 'weight_kg': 80.0,
        'height_cm': 178.0, 'activity_level': 'moderate',
        'goal': 'lose', 'goal_rate_kg_per_week': 0.5,
        'metabolism_factor': 1.0, 'provenance_id': 'nut-3 demo',
    },
    {
        'name': 'demo-sam', 'display_name': 'Sam (demo)',
        'sex': 'female', 'age_years': 31.0, 'weight_kg': 62.0,
        'height_cm': 165.0, 'activity_level': 'light',
        'goal': 'maintain', 'metabolism_factor': 1.0,
        'provenance_id': 'nut-3 demo',
    },
]

SEED_HOUSEHOLDS = [
    {
        'name': 'demo-household',
        'display_name': 'Demo two-person household',
        'description': 'Alex + Sam — the reference nutrition demand.',
        'member_names_json': json.dumps(['demo-alex', 'demo-sam']),
        'provenance_id': 'nut-4 demo',
    },
]
