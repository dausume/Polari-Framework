"""
@cross-cutting
@module microalgae.reactor_seed
@tags @xc:bindings

algae-1 seeds — microalgae strains + three demo reactors that exercise
the sustainability verdicts: a SUSTAINABLE chlorella reactor on a
hydroponic reservoir, a SUSTAINABLE nannochloropsis reactor on the
nitrogen-accumulating fish-heavy saltwater tank (consumes the excess N
while fixing CO2 — the ideal decarbonization host), and an OVERSIZED
reactor on the already-balanced food forest that would collapse it.
Idempotent-by-name. Flagged priors.

@consumers
  - polariServer seed_pairs (strains before reactors)
@see /SALTWATER_FOOD_FOREST_SPEC.md
"""

import json

SEED_ALGAE_STRAINS = [
    {'name': 'chlorella-vulgaris', 'display_name': 'Chlorella vulgaris',
     'common_name': 'Chlorella', 'water_type': 'fresh',
     'max_growth_rate_per_day': 0.9, 'carbon_fraction': 0.5,
     'n_per_biomass_mg_g': 90.0, 'p_per_biomass_mg_g': 13.0,
     'optimal_density_g_l': 2.5, 'edible': True,
     'product': 'food-protein',
     'harvest_nutrients_json': json.dumps({
         'protein': 55.0, 'iron': 130.0, 'magnesium': 315.0}),
     'provenance_id': 'algae-1'},
    {'name': 'spirulina', 'display_name': 'Spirulina (Arthrospira)',
     'common_name': 'Spirulina', 'water_type': 'fresh',
     'max_growth_rate_per_day': 0.8, 'carbon_fraction': 0.48,
     'n_per_biomass_mg_g': 100.0, 'p_per_biomass_mg_g': 12.0,
     'optimal_density_g_l': 2.0, 'edible': True,
     'product': 'food-protein',
     'harvest_nutrients_json': json.dumps({
         'protein': 60.0, 'iron': 28.0}),
     'provenance_id': 'algae-1'},
    {'name': 'nannochloropsis', 'display_name': 'Nannochloropsis',
     'common_name': 'Nanno', 'water_type': 'salt',
     'max_growth_rate_per_day': 0.7, 'carbon_fraction': 0.5,
     'n_per_biomass_mg_g': 70.0, 'p_per_biomass_mg_g': 10.0,
     'optimal_density_g_l': 4.0, 'edible': False,
     'product': 'omega-oil', 'harvest_nutrients_json': '{}',
     'provenance_id': 'algae-1'},
    {'name': 'tetraselmis', 'display_name': 'Tetraselmis',
     'common_name': 'Tetraselmis', 'water_type': 'salt',
     'max_growth_rate_per_day': 0.75, 'carbon_fraction': 0.5,
     'n_per_biomass_mg_g': 75.0, 'p_per_biomass_mg_g': 11.0,
     'optimal_density_g_l': 3.5, 'edible': False, 'product': 'feed',
     'harvest_nutrients_json': '{}', 'provenance_id': 'algae-1'},
]

SEED_ALGAE_REACTORS = [
    # Sustainable: hydroponic reservoir with plenty of spare N, capped.
    {'name': 'chlorella-hydro-reactor',
     'display_name': 'Chlorella reactor on hydroponic reservoir',
     'strain_name': 'chlorella-vulgaris', 'water_type': 'fresh',
     'volume_l': 20.0, 'light_intensity': 0.8,
     'co2_supply_mode': 'injected', 'co2_injection_g_per_day': 25.0,
     'coupled_system_name': 'household-hydroponic-reservoir',
     'coupled_system_kind': 'hydroponic',
     'nutrient_draw_cap_mg_n_per_day': 900.0,
     'assumed_parent_surplus_mg_n_per_day': 1000.0,
     'target_density_fraction': 0.5,
     'harvest_fraction': 0.35, 'harvest_period_days': 1.0,
     'provenance_id': 'algae-1 sustainable/hydroponic'},
    # Sustainable: fish-heavy saltwater tank (accumulating N) — the
    # reactor consumes the excess while fixing CO2. IDEAL host.
    {'name': 'nanno-saltforest-reactor',
     'display_name': 'Nannochloropsis reactor on fish-heavy tank',
     'strain_name': 'nannochloropsis', 'water_type': 'salt',
     'volume_l': 30.0, 'light_intensity': 0.7,
     'co2_supply_mode': 'injected', 'co2_injection_g_per_day': 40.0,
     'coupled_system_name': 'saltwater-fish-heavy',
     'coupled_system_kind': 'tank',
     'nutrient_draw_cap_mg_n_per_day': 1100.0,
     'target_density_fraction': 0.5,
     'harvest_fraction': 0.35, 'harvest_period_days': 1.0,
     'provenance_id': 'algae-1 sustainable/tank'},
    # Small "polish" reactor sized to a modest surplus (~160 mg N/day) —
    # the reactor-first resilient loop's consumer (algae-2).
    {'name': 'polish-reactor',
     'display_name': 'Chlorella polish reactor (small)',
     'strain_name': 'chlorella-vulgaris', 'water_type': 'salt',
     'volume_l': 4.0, 'light_intensity': 0.8,
     'co2_supply_mode': 'injected', 'co2_injection_g_per_day': 6.0,
     'coupled_system_name': 'saltwater-modest-surplus',
     'coupled_system_kind': 'tank',
     'nutrient_draw_cap_mg_n_per_day': 200.0,
     'target_density_fraction': 0.5,
     'harvest_fraction': 0.35, 'harvest_period_days': 1.0,
     'provenance_id': 'algae-2 polish'},
    # Collapse risk: coupled to the already-BALANCED food forest, which
    # has no nutrient surplus — the reactor would deplete it.
    {'name': 'oversized-foodforest-reactor',
     'display_name': 'Oversized reactor on the balanced food forest',
     'strain_name': 'nannochloropsis', 'water_type': 'salt',
     'volume_l': 60.0, 'light_intensity': 0.9,
     'co2_supply_mode': 'injected', 'co2_injection_g_per_day': 80.0,
     'coupled_system_name': 'saltwater-food-forest',
     'coupled_system_kind': 'tank',
     'nutrient_draw_cap_mg_n_per_day': 0.0,
     'target_density_fraction': 0.5,
     'harvest_fraction': 0.35, 'harvest_period_days': 1.0,
     'provenance_id': 'algae-1 collapse-demo'},
]
