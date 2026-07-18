"""
@cross-cutting
@module aquaponics.pot_seed
@tags @xc:bindings

Demo pots (aqp-1) — one valid reference pot and one deliberately
broken pot, so the geometry validator has a live parity case and a
live failure case. Idempotent-by-name.

@consumers
  - polariServer seed_pairs
@see /AQUAPONICS_MODULE_PLAN.md
"""

#: A valid herb pot: 200mm cylinder, two input holes high on side 0,
#: two output holes low on the opposite side (180), outputs downhill.
SEED_POTS = [
    {
        'name': 'demo-herb-pot',
        'display_name': 'Demo herb pot',
        'description': 'Reference self-watering pot — 200mm glazed '
                       'ceramic cylinder, gravity-valid holes.',
        'shape': 'cylinder',
        'outer_top_diameter_mm': 200.0,
        'outer_base_diameter_mm': 200.0,
        'height_mm': 250.0,
        'wall_thickness_mm': 8.0,
        'base_thickness_mm': 12.0,
        'material_name': 'ceramic-glazed',
        'reservoir_height_mm': 40.0,
    },
    {
        'name': 'demo-broken-pot',
        'display_name': 'Demo broken pot (validator exercise)',
        'description': 'Deliberately invalid — outputs uphill, inputs '
                       'not above outputs, holes on the same side.',
        'shape': 'cylinder',
        'outer_top_diameter_mm': 180.0,
        'outer_base_diameter_mm': 180.0,
        'height_mm': 220.0,
        'wall_thickness_mm': 7.0,
        'base_thickness_mm': 10.0,
        'material_name': 'geopolymer-waterproof',
        'reservoir_height_mm': 0.0,
    },
]

SEED_POT_HOLES = [
    # Valid pot: inputs high on side 0, outputs low on side 180.
    {'name': 'demo-herb-pot-input-1', 'pot_name': 'demo-herb-pot',
     'kind': 'input', 'diameter_mm': 10.0, 'height_mm': 200.0,
     'azimuth_deg': 350.0, 'angle_deg': 0.0},
    {'name': 'demo-herb-pot-input-2', 'pot_name': 'demo-herb-pot',
     'kind': 'input', 'diameter_mm': 10.0, 'height_mm': 200.0,
     'azimuth_deg': 10.0, 'angle_deg': 0.0},
    {'name': 'demo-herb-pot-output-1', 'pot_name': 'demo-herb-pot',
     'kind': 'output', 'diameter_mm': 12.0, 'height_mm': 45.0,
     'azimuth_deg': 170.0, 'angle_deg': 2.0},
    {'name': 'demo-herb-pot-output-2', 'pot_name': 'demo-herb-pot',
     'kind': 'output', 'diameter_mm': 12.0, 'height_mm': 45.0,
     'azimuth_deg': 190.0, 'angle_deg': 2.0},
    # Broken pot: output uphill + same side as input + input too low.
    {'name': 'demo-broken-pot-input-1', 'pot_name': 'demo-broken-pot',
     'kind': 'input', 'diameter_mm': 10.0, 'height_mm': 60.0,
     'azimuth_deg': 0.0, 'angle_deg': 0.0},
    {'name': 'demo-broken-pot-output-1', 'pot_name': 'demo-broken-pot',
     'kind': 'output', 'diameter_mm': 12.0, 'height_mm': 90.0,
     'azimuth_deg': 20.0, 'angle_deg': -5.0},
]
