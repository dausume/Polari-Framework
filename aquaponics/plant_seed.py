"""
@cross-cutting
@module aquaponics.plant_seed
@tags @xc:bindings

Demo plants (aqp-4): sweet basil — an annual herb in the reference
pot. Roots are soil-incorporated (some PERMANENT sequestration); stem
and leaves are harvested (captured but NOT permanent — the honest
distinction).

dwarf-pepper (2026-07-15, plant-growth-sim phase 12) — a real second
species brought to FULL parity with sweet-basil, per Dustin's own
framing: "let's try to have at least two robust variants that we can
compare against each other." plant_morphology.morphology_seed already
had RootSystemModel + partial OrganModel rows for this species (the
"kept in a pot indefinitely" perennial case) — this file is what was
actually MISSING (PlantDefinition/PlantPart, without which
free_soil_constants() refused outright; confirmed via a direct audit
of every seed file before writing anything). A genuine, not just
scaled-up, contrast with basil: PERENNIAL not annual, its stem/root
are STANDING-PERMANENT (persist across seasons) rather than
harvested/soil-incorporated, it FRUITS (a new PLANT_PARTS entry this
seed data actually uses), and its own RootSystemModel already
declares a LOWER confinement_tolerance (0.45 vs basil's 0.7) — it
dwarfs less comfortably in the same demo-herb-pot and needs yearly
root pruning to survive indefinitely, a real, already-designed-in
comparison point that shows up naturally in constrained_limits().
Volumes/rates are documented, literature-adjacent priors scaled from
the real RootSystemModel geometry ratio (depth x spread^2, ~3.4x
basil's), same "mock estimate, flagged" honesty as every other
biological constant in this codebase.

@consumers
  - polariServer seed_pairs
@see /AQUAPONICS_MODULE_PLAN.md, /AQUAPONICS_POT_SHAPE_PLAN.md phase 12
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
    {
        'name': 'dwarf-pepper',
        'display_name': 'Dwarf pepper',
        'species': 'Capsicum annuum (dwarf cultivar)',
        'common_name': 'dwarf pepper',
        'description': 'Perennial fruiting pepper grown indefinitely '
                       'in a pot — the second full-parity comparison '
                       'species (plant-growth-sim phase 12), a real '
                       'contrast to basil: woodier, slower, fruits, '
                       'less confinement-tolerant.',
        'life_cycle': 'perennial',
        'lifetime_days': 730.0,
        'growth_stages_json': json.dumps([
            {'stage': 'germination', 'startDay': 0, 'endDay': 21,
             'growthFraction': 0.04},
            {'stage': 'vegetative', 'startDay': 21, 'endDay': 120,
             'growthFraction': 0.45},
            {'stage': 'fruiting', 'startDay': 120, 'endDay': 365,
             'growthFraction': 0.85},
        ]),
        'mature_height_mm': 450.0, 'mature_canopy_mm': 350.0,
        # Fallback rate — pepper is a slower, woodier perennial than
        # basil's fast annual herb growth (0.045).
        'normalized_growth_rate_per_day': 0.03,
        'provenance_id': 'plant-growth-sim phase 12',
        'notes': 'mock estimate, literature-adjacent, flagged as a '
                 'prior — same standing caveat as every other '
                 'biological constant in this codebase.',
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
    # dwarf-pepper — plant-growth-sim phase 12 (2026-07-15). Volumes
    # scaled from the real RootSystemModel geometry ratio vs basil
    # (depth x spread^2, ~3.4x); rates/fates deliberately DIFFERENT
    # from basil's, not just bigger — see plant_seed.py's own module
    # docstring for the full comparison rationale.
    {
        'name': 'dwarf-pepper-root', 'plant_name': 'dwarf-pepper',
        'part': 'root', 'display_name': 'Pepper root system',
        'mature_volume_cm3': 130.0, 'dry_density_g_cm3': 0.28,
        'dry_matter_fraction': 0.12, 'permanent_fraction': 0.45,
        # A PERENNIAL's root persists indefinitely, unlike an annual's
        # soil-incorporated-at-end-of-life root (basil's own fate) —
        # a genuine, not cosmetic, difference.
        'fate': 'standing-permanent',
        'composition_json': json.dumps({
            'carbon': 0.45, 'nitrogen': 0.016, 'phosphorus': 0.004,
            'potassium': 0.014, 'calcium': 0.007, 'magnesium': 0.003,
            'hydrogen': 0.06, 'oxygen': 0.42}),
        'flux_json': json.dumps({
            'co2': {'direction': 'out', 'needed': 200.0,
                    'min': 60.0, 'max': 450.0},
            'o2': {'direction': 'in', 'needed': 140.0,
                   'min': 45.0, 'max': 320.0},
            'nitrate-n': {'direction': 'in', 'needed': 30.0,
                          'min': 12.0, 'max': 70.0},
            'ammonium-n': {'direction': 'in', 'needed': 4.0,
                           'min': 0.0, 'max': 16.0},
            'phosphorus-p': {'direction': 'in', 'needed': 5.0,
                             'min': 2.0, 'max': 12.0},
            # Fruiting plants draw more potassium than a leafy herb.
            'potassium-k': {'direction': 'in', 'needed': 35.0,
                            'min': 14.0, 'max': 80.0},
            'calcium-ca': {'direction': 'in', 'needed': 12.0,
                           'min': 5.0, 'max': 28.0},
            'magnesium-mg': {'direction': 'in', 'needed': 4.0,
                             'min': 1.5, 'max': 10.0},
            'iron-fe': {'direction': 'in', 'needed': 0.4,
                        'min': 0.15, 'max': 1.2}}),
        'provenance_id': 'plant-growth-sim phase 12 (literature-'
                         'adjacent prior)',
    },
    {
        'name': 'dwarf-pepper-stem', 'plant_name': 'dwarf-pepper',
        'part': 'stem', 'display_name': 'Pepper stem/branches',
        'mature_volume_cm3': 100.0, 'dry_density_g_cm3': 0.35,
        'dry_matter_fraction': 0.18, 'permanent_fraction': 0.65,
        # A perennial pepper's woody stem STAYS (structural), never
        # harvested like basil's culinary stem — the other half of
        # the fate contrast started above.
        'fate': 'standing-permanent',
        'composition_json': json.dumps({
            'carbon': 0.47, 'nitrogen': 0.010, 'phosphorus': 0.002,
            'potassium': 0.013, 'calcium': 0.010, 'magnesium': 0.003,
            'hydrogen': 0.06, 'oxygen': 0.41}),
        'flux_json': json.dumps({
            'co2': {'direction': 'out', 'needed': 90.0,
                    'min': 30.0, 'max': 210.0},
            'o2': {'direction': 'in', 'needed': 65.0,
                   'min': 22.0, 'max': 150.0}}),
        'provenance_id': 'plant-growth-sim phase 12 (literature-'
                         'adjacent prior)',
    },
    {
        'name': 'dwarf-pepper-leaf', 'plant_name': 'dwarf-pepper',
        'part': 'leaf', 'display_name': 'Pepper leaves',
        'mature_volume_cm3': 140.0, 'dry_density_g_cm3': 0.25,
        'dry_matter_fraction': 0.11, 'permanent_fraction': 0.08,
        # Pepper leaves aren't a culinary product like basil's —
        # they senesce naturally, not harvested.
        'fate': 'senesces',
        'composition_json': json.dumps({
            'carbon': 0.43, 'nitrogen': 0.030, 'phosphorus': 0.004,
            'potassium': 0.022, 'calcium': 0.016, 'magnesium': 0.004,
            'hydrogen': 0.06, 'oxygen': 0.42}),
        'flux_json': json.dumps({
            'co2': {'direction': 'in', 'needed': 1100.0,
                    'min': 250.0, 'max': 1900.0},
            'o2': {'direction': 'out', 'needed': 800.0,
                   'min': 180.0, 'max': 1380.0}}),
        'provenance_id': 'plant-growth-sim phase 12 (literature-'
                         'adjacent prior)',
    },
    {
        # A NEW PLANT_PARTS entry actually used by seed data for the
        # first time ('fruit' already existed in plant_basis.
        # PLANT_PARTS, but no species had a fruit PlantPart until now)
        # — the actual yield-relevant part for this species.
        'name': 'dwarf-pepper-fruit', 'plant_name': 'dwarf-pepper',
        'part': 'fruit', 'display_name': 'Pepper fruit',
        'mature_volume_cm3': 180.0, 'dry_density_g_cm3': 0.15,
        'dry_matter_fraction': 0.08, 'permanent_fraction': 0.0,
        'fate': 'harvested',
        'composition_json': json.dumps({
            'carbon': 0.40, 'nitrogen': 0.018, 'phosphorus': 0.005,
            'potassium': 0.028, 'calcium': 0.004, 'magnesium': 0.003,
            'hydrogen': 0.07, 'oxygen': 0.44}),
        'flux_json': json.dumps({
            # Fruit is a respiring SINK (draws sugar/water via the
            # plant, doesn't photosynthesize meaningfully) — gas
            # exchange only, the same pattern basil's stem uses;
            # mineral uptake stays root's job (no direct soil access).
            'co2': {'direction': 'out', 'needed': 45.0,
                    'min': 15.0, 'max': 110.0},
            'o2': {'direction': 'in', 'needed': 35.0,
                   'min': 12.0, 'max': 85.0}}),
        'provenance_id': 'plant-growth-sim phase 12 (literature-'
                         'adjacent prior)',
    },
]
