"""
@cross-cutting
@module aquaponics.plant_seed
@tags @xc:bindings

Demo plant (aqp-4): sweet basil — an annual herb in the reference pot.
Roots are soil-incorporated (some PERMANENT sequestration); stem and
leaves are harvested (captured but NOT permanent — the honest
distinction). Idempotent-by-name.

@consumers
  - polariServer seed_pairs
@see /AQUAPONICS_MODULE_PLAN.md
"""

import json

SEED_PLANTS = [
    {
        'name': 'sweet-basil',
        'display_name': 'Sweet basil',
        'species': 'Ocimum basilicum',
        'common_name': 'basil',
        'description': 'Annual culinary herb — the reference plant '
                       'for the self-watering pot.',
        'life_cycle': 'annual',
        'lifetime_days': 120.0,
        'growth_stages_json': json.dumps([
            {'stage': 'germination', 'startDay': 0, 'endDay': 14,
             'growthFraction': 0.05},
            {'stage': 'vegetative', 'startDay': 14, 'endDay': 70,
             'growthFraction': 0.5},
            {'stage': 'mature-harvest', 'startDay': 70, 'endDay': 120,
             'growthFraction': 0.9},
        ]),
        'mature_height_mm': 400.0, 'mature_canopy_mm': 300.0,
        'provenance_id': 'aqp-4 reference plant',
    },
]

SEED_PLANT_PARTS = [
    {
        'name': 'sweet-basil-root', 'plant_name': 'sweet-basil',
        'part': 'root', 'display_name': 'Basil root system',
        'mature_volume_cm3': 40.0, 'dry_density_g_cm3': 0.25,
        'dry_matter_fraction': 0.10, 'permanent_fraction': 0.40,
        'fate': 'soil-incorporated',
        'composition_json': json.dumps({
            'carbon': 0.44, 'nitrogen': 0.015, 'phosphorus': 0.003,
            'potassium': 0.012, 'calcium': 0.006, 'magnesium': 0.003,
            'hydrogen': 0.06, 'oxygen': 0.44}),
        'flux_json': json.dumps({
            # Roots respire (O2 in, CO2 out) and do the nutrient
            # uptake for the whole plant.
            'co2': {'direction': 'out', 'needed': 130.0,
                    'min': 40.0, 'max': 300.0},
            'o2': {'direction': 'in', 'needed': 95.0,
                   'min': 30.0, 'max': 220.0},
            'nitrate-n': {'direction': 'in', 'needed': 20.0,
                          'min': 8.0, 'max': 50.0},
            'ammonium-n': {'direction': 'in', 'needed': 3.0,
                           'min': 0.0, 'max': 12.0},
            'phosphorus-p': {'direction': 'in', 'needed': 3.0,
                             'min': 1.0, 'max': 8.0},
            'potassium-k': {'direction': 'in', 'needed': 15.0,
                            'min': 6.0, 'max': 40.0},
            'calcium-ca': {'direction': 'in', 'needed': 8.0,
                           'min': 3.0, 'max': 20.0},
            'magnesium-mg': {'direction': 'in', 'needed': 3.0,
                             'min': 1.0, 'max': 8.0},
            'iron-fe': {'direction': 'in', 'needed': 0.3,
                        'min': 0.1, 'max': 1.0}}),
        'provenance_id': 'aqp-4 demo (literature-informed priors)',
    },
    {
        'name': 'sweet-basil-stem', 'plant_name': 'sweet-basil',
        'part': 'stem', 'display_name': 'Basil stem',
        'mature_volume_cm3': 60.0, 'dry_density_g_cm3': 0.30,
        'dry_matter_fraction': 0.12, 'permanent_fraction': 0.50,
        'fate': 'harvested',
        'composition_json': json.dumps({
            'carbon': 0.45, 'nitrogen': 0.012, 'phosphorus': 0.002,
            'potassium': 0.015, 'calcium': 0.008, 'magnesium': 0.003,
            'hydrogen': 0.06, 'oxygen': 0.44}),
        'flux_json': json.dumps({
            'co2': {'direction': 'out', 'needed': 60.0,
                    'min': 20.0, 'max': 140.0},
            'o2': {'direction': 'in', 'needed': 44.0,
                   'min': 15.0, 'max': 100.0}}),
        'provenance_id': 'aqp-4 demo',
    },
    {
        'name': 'sweet-basil-leaf', 'plant_name': 'sweet-basil',
        'part': 'leaf', 'display_name': 'Basil leaves',
        'mature_volume_cm3': 120.0, 'dry_density_g_cm3': 0.25,
        'dry_matter_fraction': 0.11, 'permanent_fraction': 0.15,
        'fate': 'harvested',
        'composition_json': json.dumps({
            'carbon': 0.42, 'nitrogen': 0.035, 'phosphorus': 0.004,
            'potassium': 0.020, 'calcium': 0.015, 'magnesium': 0.004,
            'hydrogen': 0.06, 'oxygen': 0.42}),
        'flux_json': json.dumps({
            # Leaves fix CO2 and release O2 (net photosynthesis).
            'co2': {'direction': 'in', 'needed': 900.0,
                    'min': 200.0, 'max': 1500.0},
            'o2': {'direction': 'out', 'needed': 655.0,
                   'min': 145.0, 'max': 1090.0}}),
        'provenance_id': 'aqp-4 demo',
    },
]
