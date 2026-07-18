"""
@cross-cutting
@module aquaponics.water_batch_seed
@tags @xc:bindings

Demo WaterBatchSchedule (plant-growth-sim phase 10, 2026-07-15) —
alternates between the two REAL, already-seeded water sources with
genuinely different nutrient profiles (aquaponics.media_seed):
`hydroponic-reservoir` (rich, no Fe deficiency) and
`tilapia-aquaponic-loop` (real aquaponic solution, deliberately
Fe-deficient — "the classic aquaponic gap," per that seed's own
description). Exactly the "optimize growth or purposefully stress
plants... without killing them" pattern Dustin described: mostly
rich water, with a shorter deliberately-deficient window, repeating.

@consumers
  - polariServer seed_pairs
@see /AQUAPONICS_POT_SHAPE_PLAN.md phase 10
"""

import json

SEED_WATER_BATCH_SCHEDULES = [
    {
        'name': 'basil-fe-stress-cycle',
        'display_name': 'Basil Fe-stress cycle',
        'description': 'Mostly the rich hydroponic reservoir, with a '
                       'shorter deliberately Fe-deficient aquaponic '
                       'window each cycle — stresses iron uptake '
                       'specifically, on purpose, without starving '
                       'anything else.',
        'batches_json': json.dumps([
            {'waterName': 'hydroponic-reservoir', 'holdDays': 4.0,
             'holdHours': 0.0},
            {'waterName': 'tilapia-aquaponic-loop', 'holdDays': 1.0,
             'holdHours': 0.0},
        ]),
        'repeat': True,
        'provenance_id': 'plant-growth-sim phase 10',
        'notes': '5-day cycle: 4 days rich, 1 day Fe-deficient, '
                 'repeating.',
    },
]
