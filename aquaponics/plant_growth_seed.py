"""
@cross-cutting
@module aquaponics.plant_growth_seed
@tags @xc:bindings

aqp-8 — per-part growth models for the demo basil plant + the scoring
bridge (realized-capture / survival-margin). One PlantGrowthModel per
seeded PlantPart. Idempotent-by-name.

@consumers
  - polariServer seed_pairs
@see /AQUAPONICS_PHASE2_PLAN.md §aqp-8
"""

import json

SEED_PLANT_GROWTH_MODELS = [
    {
        'name': 'sweet-basil-root-growth', 'part_name': 'sweet-basil-root',
        'max_volume_cm3': 40.0, 'growth_rate': 0.14,
        'condition': 'healthy', 'volume_density_g_cm3': 0.25,
        'provenance_id': 'aqp-8',
    },
    {
        'name': 'sweet-basil-stem-growth', 'part_name': 'sweet-basil-stem',
        'max_volume_cm3': 60.0, 'growth_rate': 0.11,
        'condition': 'healthy', 'volume_density_g_cm3': 0.30,
        'provenance_id': 'aqp-8',
    },
    {
        'name': 'sweet-basil-leaf-growth', 'part_name': 'sweet-basil-leaf',
        'max_volume_cm3': 120.0, 'growth_rate': 0.16,
        'condition': 'healthy', 'volume_density_g_cm3': 0.25,
        'provenance_id': 'aqp-8',
    },
]
