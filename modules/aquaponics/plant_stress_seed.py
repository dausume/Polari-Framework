"""
@cross-cutting
@module aquaponics.plant_stress_seed
@tags @xc:bindings

Demo StressResponseCurve rows for sweet-basil (plant-growth-sim
phase 7, 2026-07-15) — Tier-A trapezoid bounds only (no Tier-B
equation_ref seeded here; that's a per-species opt-in, this is the
always-available default). Mock priors, same standing caveat as every
other biological constant in this codebase (flagged, not claimed
authoritative).

dwarf-pepper rows (2026-07-15, plant-growth-sim phase 12) — WITHOUT
these, pepper had ZERO StressResponseCurve rows at all, meaning
combined_stress_factor() found nothing to evaluate and silently
returned a perfect 1.0 for every tick — an unfair, incomplete
comparison against basil's real, sometimes-limiting curves, not a
genuine "pepper is more robust" result. Bounds shifted warmer + higher
-light than basil's (a fruiting pepper's real preference vs a leafy
herb's), a deliberate difference, not a rescaled copy.

Deliberately per-part, not uniform: ROOT curves read WATER fields
(oxygen/pH/salinity — what a root actually touches), STEM/LEAF curves
read ATMOSPHERE fields (temperature/humidity/light/CO2 — what the
canopy actually touches) — demonstrating Dustin's "vary based on the
plant part" requirement with real, different equations, not the same
curve copy-pasted three times. LEAF also gets its OWN temperature
curve (tighter than STEM's) — the same stress TYPE can have a
genuinely different response per part.

Checked against the two real seeded aquaponics.pot_system_seed.py
systems sharing this same plant (`basil-aquaponic-tent` — healthy
ventilated, `basil-aquaponic-sealed` — atmosphere-degraded): ROOT and
STEM come out identical between the two (they only read fields that
don't differ between those two atmospheres, or read the SHARED water
row), while LEAF genuinely differs (light + CO2 both mildly limiting
in the sealed chamber) — an honest, non-contrived contrast computed
from the real numbers, not forced.

@consumers
  - polariServer seed_pairs
@see /AQUAPONICS_POT_SHAPE_PLAN.md phase 7
"""

SEED_STRESS_CURVES = [
    {
        'name': 'sweet-basil-root-oxygen',
        'plant_name': 'sweet-basil', 'part': 'root',
        'stress_type': 'oxygen',
        'min_value': 2.0, 'optimal_low': 5.0, 'optimal_high': 9.0,
        'max_value': 14.0,
        'equation_ref': '', 'input_bindings_json': '{}',
        'provenance_id': 'plant-growth-sim phase 7 prior',
        'notes': 'root-zone dissolved O2 (WaterDefinition.'
                 'dissolved_oxygen_mg_l) — below ~5mg/L stresses roots '
                 '(matches the existing media_analysis.py finding).',
    },
    {
        'name': 'sweet-basil-root-water-ph',
        'plant_name': 'sweet-basil', 'part': 'root',
        'stress_type': 'water-ph',
        'min_value': 4.5, 'optimal_low': 5.5, 'optimal_high': 6.8,
        'max_value': 8.0,
        'equation_ref': '', 'input_bindings_json': '{}',
        'provenance_id': 'plant-growth-sim phase 7 prior',
        'notes': 'basil tolerates mildly acidic aquaponic water; '
                 'nutrient lockout above ~pH 8.',
    },
    {
        'name': 'sweet-basil-root-salinity',
        'plant_name': 'sweet-basil', 'part': 'root',
        'stress_type': 'salinity',
        'min_value': 0.3, 'optimal_low': 1.0, 'optimal_high': 2.0,
        'max_value': 3.5,
        'equation_ref': '', 'input_bindings_json': '{}',
        'provenance_id': 'plant-growth-sim phase 7 prior',
        'notes': 'root-zone electrical conductivity — too low starves '
                 'nutrients, too high is salt stress.',
    },
    {
        'name': 'sweet-basil-stem-temperature',
        'plant_name': 'sweet-basil', 'part': 'stem',
        'stress_type': 'temperature',
        'min_value': 8.0, 'optimal_low': 20.0, 'optimal_high': 28.0,
        'max_value': 38.0,
        'equation_ref': '', 'input_bindings_json': '{}',
        'provenance_id': 'plant-growth-sim phase 7 prior',
        'notes': 'whole-canopy structural tolerance — wider than the '
                 "leaf's own temperature curve below.",
    },
    {
        'name': 'sweet-basil-stem-humidity',
        'plant_name': 'sweet-basil', 'part': 'stem',
        'stress_type': 'humidity',
        'min_value': 20.0, 'optimal_low': 40.0, 'optimal_high': 75.0,
        'max_value': 95.0,
        'equation_ref': '', 'input_bindings_json': '{}',
        'provenance_id': 'plant-growth-sim phase 7 prior',
        'notes': 'basil tolerates a fairly wide relative-humidity band.',
    },
    {
        'name': 'sweet-basil-leaf-light',
        'plant_name': 'sweet-basil', 'part': 'leaf',
        'stress_type': 'light',
        'min_value': 80.0, 'optimal_low': 280.0, 'optimal_high': 550.0,
        'max_value': 900.0,
        'equation_ref': '', 'input_bindings_json': '{}',
        'provenance_id': 'plant-growth-sim phase 7 prior',
        'notes': 'PAR photon flux (AtmosphereDefinition.'
                 'light_ppfd_umol_m2_s) — the sealed-chamber demo '
                 '(250 PPFD) sits just below optimal_low, a mild, '
                 'real (not contrived) stress signal.',
    },
    {
        'name': 'sweet-basil-leaf-co2',
        'plant_name': 'sweet-basil', 'part': 'leaf',
        'stress_type': 'co2',
        'min_value': 150.0, 'optimal_low': 400.0, 'optimal_high': 700.0,
        'max_value': 1400.0,
        'equation_ref': '', 'input_bindings_json': '{}',
        'provenance_id': 'plant-growth-sim phase 7 prior',
        'notes': 'the sealed-chamber demo (800ppm) sits just above '
                 'optimal_high — basil tolerates elevated CO2 well but '
                 'not without some cost.',
    },
    {
        'name': 'sweet-basil-leaf-temperature',
        'plant_name': 'sweet-basil', 'part': 'leaf',
        'stress_type': 'temperature',
        'min_value': 10.0, 'optimal_low': 21.0, 'optimal_high': 27.0,
        'max_value': 34.0,
        'equation_ref': '', 'input_bindings_json': '{}',
        'provenance_id': 'plant-growth-sim phase 7 prior',
        'notes': 'tighter than the stem curve — leaf photosynthetic '
                 'efficiency is more heat-sensitive than stem survival.',
    },
    {
        'name': 'dwarf-pepper-root-oxygen',
        'plant_name': 'dwarf-pepper', 'part': 'root',
        'stress_type': 'oxygen',
        'min_value': 2.5, 'optimal_low': 5.5, 'optimal_high': 9.5,
        'max_value': 14.5,
        'equation_ref': '', 'input_bindings_json': '{}',
        'provenance_id': 'plant-growth-sim phase 12 prior',
        'notes': 'a larger root system than basil, slightly higher '
                 'oxygen demand.',
    },
    {
        'name': 'dwarf-pepper-root-water-ph',
        'plant_name': 'dwarf-pepper', 'part': 'root',
        'stress_type': 'water-ph',
        'min_value': 5.0, 'optimal_low': 6.0, 'optimal_high': 6.8,
        'max_value': 7.8,
        'equation_ref': '', 'input_bindings_json': '{}',
        'provenance_id': 'plant-growth-sim phase 12 prior',
        'notes': 'peppers prefer a more neutral pH than basil\'s wider '
                 'tolerance.',
    },
    {
        'name': 'dwarf-pepper-root-salinity',
        'plant_name': 'dwarf-pepper', 'part': 'root',
        'stress_type': 'salinity',
        'min_value': 0.4, 'optimal_low': 1.2, 'optimal_high': 2.5,
        'max_value': 4.0,
        'equation_ref': '', 'input_bindings_json': '{}',
        'provenance_id': 'plant-growth-sim phase 12 prior',
        'notes': 'moderately more salt-tolerant than basil.',
    },
    {
        'name': 'dwarf-pepper-stem-temperature',
        'plant_name': 'dwarf-pepper', 'part': 'stem',
        'stress_type': 'temperature',
        'min_value': 12.0, 'optimal_low': 22.0, 'optimal_high': 32.0,
        'max_value': 42.0,
        'equation_ref': '', 'input_bindings_json': '{}',
        'provenance_id': 'plant-growth-sim phase 12 prior',
        'notes': 'warmer optimum than basil\'s — a real Capsicum '
                 'preference, not a rescaled copy.',
    },
    {
        'name': 'dwarf-pepper-stem-humidity',
        'plant_name': 'dwarf-pepper', 'part': 'stem',
        'stress_type': 'humidity',
        'min_value': 25.0, 'optimal_low': 45.0, 'optimal_high': 70.0,
        'max_value': 90.0,
        'equation_ref': '', 'input_bindings_json': '{}',
        'provenance_id': 'plant-growth-sim phase 12 prior',
        'notes': 'similarly wide tolerance to basil.',
    },
    {
        'name': 'dwarf-pepper-leaf-light',
        'plant_name': 'dwarf-pepper', 'part': 'leaf',
        'stress_type': 'light',
        'min_value': 100.0, 'optimal_low': 350.0, 'optimal_high': 650.0,
        'max_value': 1000.0,
        'equation_ref': '', 'input_bindings_json': '{}',
        'provenance_id': 'plant-growth-sim phase 12 prior',
        'notes': 'a FRUITING plant genuinely wants more light than a '
                 'leafy herb — a real, deliberate difference from '
                 "basil's own leaf-light curve, not a copy.",
    },
    {
        'name': 'dwarf-pepper-leaf-co2',
        'plant_name': 'dwarf-pepper', 'part': 'leaf',
        'stress_type': 'co2',
        'min_value': 150.0, 'optimal_low': 400.0, 'optimal_high': 800.0,
        'max_value': 1500.0,
        'equation_ref': '', 'input_bindings_json': '{}',
        'provenance_id': 'plant-growth-sim phase 12 prior',
        'notes': 'similar CO2 tolerance to basil.',
    },
    {
        'name': 'dwarf-pepper-leaf-temperature',
        'plant_name': 'dwarf-pepper', 'part': 'leaf',
        'stress_type': 'temperature',
        'min_value': 14.0, 'optimal_low': 24.0, 'optimal_high': 30.0,
        'max_value': 38.0,
        'equation_ref': '', 'input_bindings_json': '{}',
        'provenance_id': 'plant-growth-sim phase 12 prior',
        'notes': 'warmer + tighter than basil\'s own leaf-temperature '
                 'curve.',
    },
]
