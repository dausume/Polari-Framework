"""
@cross-cutting
@module aquaponics.plant_growth_seed
@tags @xc:bindings

aqp-8 — per-part growth models for the demo plants + the scoring
bridge (realized-capture / survival-margin). One PlantGrowthModel per
seeded PlantPart. Idempotent-by-name.

dwarf-pepper rows (2026-07-15, plant-growth-sim phase 12) complete
that species' full-parity comparison against basil — max_volume_cm3
matches each PlantPart's own mature_volume_cm3 exactly (the same
convention basil's rows already use); growth_rate is deliberately
SLOWER than basil's across every part (a perennial's woodier growth),
not just a rescaled copy.

@consumers
  - polariServer seed_pairs
@see /AQUAPONICS_PHASE2_PLAN.md §aqp-8, /AQUAPONICS_POT_SHAPE_PLAN.md phase 12
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
    {
        'name': 'dwarf-pepper-root-growth',
        'part_name': 'dwarf-pepper-root',
        'max_volume_cm3': 130.0, 'growth_rate': 0.09,
        'condition': 'healthy', 'volume_density_g_cm3': 0.28,
        'provenance_id': 'plant-growth-sim phase 12',
    },
    {
        'name': 'dwarf-pepper-stem-growth',
        'part_name': 'dwarf-pepper-stem',
        'max_volume_cm3': 100.0, 'growth_rate': 0.07,
        'condition': 'healthy', 'volume_density_g_cm3': 0.35,
        'provenance_id': 'plant-growth-sim phase 12',
    },
    {
        'name': 'dwarf-pepper-leaf-growth',
        'part_name': 'dwarf-pepper-leaf',
        'max_volume_cm3': 140.0, 'growth_rate': 0.10,
        'condition': 'healthy', 'volume_density_g_cm3': 0.25,
        'provenance_id': 'plant-growth-sim phase 12',
    },
    {
        'name': 'dwarf-pepper-fruit-growth',
        'part_name': 'dwarf-pepper-fruit',
        'max_volume_cm3': 180.0, 'growth_rate': 0.12,
        'condition': 'healthy', 'volume_density_g_cm3': 0.15,
        'provenance_id': 'plant-growth-sim phase 12',
    },
]
