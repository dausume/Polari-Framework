"""
@cross-cutting
@module mathshapes.tower_seed
@tags @xc:bindings

One demo aquaponic tower stacking the shape-1 'pot-with-holes' math pot
into 4 tiers. Idempotent-by-name. Lengths in cm.

@consumers
  - polariServer seed_pairs
@see /MATH_SHAPES_PLAN.md (PHASE shape-2)
"""

SEED_TOWERS = [
    {'name': 'demo-herb-tower', 'display_name': 'Demo herb tower',
     'pot_shape_name': 'pot-with-holes', 'n_tiers': 4,
     'tier_spacing_cm': 25.0, 'shared_reservoir': True,
     'reservoir_volume_l': 10.0, 'grow_fraction': 0.6,
     'notes': 'four pot-with-holes tiers over a shared reservoir; the '
              'shape-4 growth-forecast demo tower.',
     'provenance_id': 'shape-2'},
]
