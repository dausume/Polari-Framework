"""
@cross-cutting
@module tanks.tank_seed
@tags @xc:bindings

tank-1 seeds — the saltwater food-forest roster (from
SALTWATER_FOOD_FOREST_SPEC.md) + a minimal freshwater system, plus three
demo systems: a BALANCED saltwater food forest, a FISH-HEAVY imbalanced
one (exercises regulate_suggestions), and a basic freshwater one.
Idempotent-by-name. All fluxes/yields are flagged literature priors.

Per-100g nutrient values are in each DietaryNutrient's native unit
(iodine µg, sodium/chloride mg, protein g) — same convention as nut-2
NutrientContent.

@consumers
  - polariServer seed_pairs (species + tanks before systems)
@see /SALTWATER_FOOD_FOREST_SPEC.md
"""

import json


def _sp(name, common, water, roles, edible, wax, n, p, detritus,
        biomass, nutrients, prov='tank-1'):
    return {'name': name, 'common_name': common, 'display_name': common,
            'water_type': water, 'roles_json': json.dumps(roles),
            'edible': edible, 'wax_use': wax, 'daily_n_flux_mg': n,
            'daily_p_flux_mg': p, 'daily_detritus_removal_mg': detritus,
            'harvest_biomass_g': biomass,
            'harvest_nutrients_json': json.dumps(nutrients),
            'provenance_id': prov}


# Seaweed nutrient priors (per 100 g fresh): high iodine + sodium +
# chloride (the hydroponic gap) + some protein.
_SEAWEED = {'iodine': 150.0, 'sodium': 600.0, 'chloride': 900.0,
            'protein': 3.0}
_FISH = {'protein': 20.0, 'omega-3': 1.4}

SEED_AQUACULTURE_SPECIES = [
    # --- saltwater macroalgae (nutrient regulators, food + wax) ---
    _sp('sea-lettuce', 'Sea Lettuce', 'salt',
        ['nutrient-regulator', 'macroalgae-food', 'substrate-oxygenator'],
        True, True, -25.0, -4.0, 0.0, 50.0, _SEAWEED),
    _sp('red-ogo', 'Red Ogo', 'salt',
        ['nutrient-regulator', 'macroalgae-food'], True, True,
        -20.0, -3.0, 0.0, 45.0, _SEAWEED),
    _sp('dulse', 'Dulse (Palmaria palmata)', 'salt',
        ['nutrient-regulator', 'macroalgae-food'], True, True,
        -15.0, -2.0, 0.0, 30.0, _SEAWEED),
    _sp('chlorella-salina', 'Chlorella Salina', 'salt',
        ['nutrient-regulator', 'starch-producer'], True, False,
        -10.0, -1.5, 0.0, 20.0,
        {'carbohydrate': 60.0, 'protein': 12.0}),
    # --- filter feeders (protein) ---
    _sp('scallops', 'Scallops', 'salt',
        ['filter-feeder', 'protein-source'], True, False,
        2.0, 0.3, 40.0, 60.0, _FISH),
    _sp('mussels', 'Mussels', 'salt',
        ['filter-feeder', 'protein-source'], True, False,
        2.0, 0.3, 45.0, 30.0, _FISH),
    # --- detritus + cleaners ---
    _sp('tiger-tail-cucumber', 'Tiger Tail Sea Cucumber', 'salt',
        ['detritus-eater'], True, False, 0.0, 0.0, 60.0, 0.0, {}),
    _sp('cerith-snails', 'Cerith Snails', 'salt',
        ['detritus-eater', 'glass-cleaner'], True, False,
        0.0, 0.0, 15.0, 0.0, {}),
    _sp('trochus-snails', 'Trochus Snails', 'salt',
        ['glass-cleaner'], True, False, 0.0, 0.0, 12.0, 0.0, {}),
    # --- extra macroalgae (refugium nutrient regulator) ---
    _sp('chaetomorpha', 'Chaetomorpha (refugium algae)', 'salt',
        ['nutrient-regulator', 'macroalgae-food'], False, False,
        -30.0, -5.0, 0.0, 0.0, {}),
    # --- shrimp for CLEANING (+ Pacific White for protein) ---
    _sp('skunk-cleaner-shrimp', 'Skunk Cleaner Shrimp', 'salt',
        ['cleaner', 'detritus-eater', 'nuisance-algae-consumer'],
        False, False, 0.0, 0.0, 20.0, 0.0, {}),
    _sp('pacific-white-shrimp', 'Pacific White Shrimp', 'salt',
        ['protein-source', 'detritus-eater', 'cleaner'], True, False,
        3.0, 0.5, 30.0, 40.0, {'protein': 20.0}),
    # --- nutrient replenishers (fish — add N/P; protein + oil) ---
    _sp('anchovies', 'Anchovies', 'salt',
        ['nutrient-replenisher', 'protein-source'], True, False,
        30.0, 5.0, 0.0, 15.0, _FISH),
    _sp('sardines', 'Sardines', 'salt',
        ['nutrient-replenisher', 'protein-source'], True, False,
        40.0, 7.0, 0.0, 25.0, _FISH),
    # --- freshwater set ---
    _sp('hornwort', 'Hornwort', 'fresh',
        ['nutrient-regulator', 'substrate-oxygenator'], False, False,
        -25.0, -4.0, 0.0, 0.0, {}),
    _sp('amano-shrimp', 'Amano Shrimp (algae cleaner)', 'fresh',
        ['cleaner', 'detritus-eater', 'nuisance-algae-consumer'],
        False, False, 0.0, 0.0, 18.0, 0.0, {}),
    _sp('cherry-shrimp', 'Cherry Shrimp (cleaner)', 'fresh',
        ['cleaner', 'detritus-eater'], True, False,
        0.0, 0.0, 10.0, 1.0, {'protein': 18.0}),
    _sp('duckweed', 'Duckweed', 'fresh',
        ['nutrient-regulator', 'protein-source'], True, False,
        -18.0, -3.0, 0.0, 20.0, {'protein': 8.0}),
    _sp('water-hyacinth', 'Water Hyacinth', 'fresh',
        ['nutrient-regulator'], False, False, -30.0, -5.0, 0.0, 0.0, {}),
    _sp('freshwater-snails', 'Freshwater Snails', 'fresh',
        ['detritus-eater', 'glass-cleaner'], True, False,
        0.0, 0.0, 20.0, 0.0, {}),
    _sp('freshwater-mussels', 'Freshwater Mussels', 'fresh',
        ['filter-feeder'], True, False, 1.0, 0.2, 40.0, 25.0, _FISH),
    _sp('tilapia', 'Tilapia', 'fresh',
        ['nutrient-replenisher', 'protein-source'], True, False,
        45.0, 8.0, 0.0, 120.0, _FISH),
]

# The NEW tank-substrate ("soil") category — fresh + salt beds.
SEED_TANK_SUBSTRATES = [
    # Saltwater beds.
    {'name': 'live-aragonite-sand',
     'display_name': 'Live aragonite sand', 'water_type': 'salt',
     'kind': 'live-aragonite-sand', 'grain_size_mm': 1.0,
     'buffers_ph': True, 'target_ph': 8.2,
     'alkalinity_contribution': 8.0, 'nutrient_storage': 0.2,
     'releases_nutrients': False, 'biofiltration_capacity': 0.5,
     'denitrification_mg_n_per_l_per_day': 3.0,
     'supports_anaerobic_layer': True, 'provenance_id': 'tank-2'},
    {'name': 'live-rock-rubble', 'display_name': 'Live rock rubble',
     'water_type': 'salt', 'kind': 'live-rock-rubble',
     'grain_size_mm': 15.0, 'buffers_ph': True, 'target_ph': 8.1,
     'alkalinity_contribution': 4.0, 'nutrient_storage': 0.1,
     'biofiltration_capacity': 0.8,
     'denitrification_mg_n_per_l_per_day': 5.0,
     'supports_anaerobic_layer': True, 'provenance_id': 'tank-2'},
    {'name': 'saltwater-biochar-sand',
     'display_name': 'Biochar-sand (marine)', 'water_type': 'salt',
     'kind': 'biochar-sand', 'grain_size_mm': 1.5,
     'nutrient_storage': 0.3, 'biofiltration_capacity': 0.6,
     'denitrification_mg_n_per_l_per_day': 2.0,
     'supports_anaerobic_layer': True, 'provenance_id': 'tank-2'},
    # Freshwater beds.
    {'name': 'planted-aquasoil', 'display_name': 'Planted aquasoil',
     'water_type': 'fresh', 'kind': 'aquasoil', 'grain_size_mm': 3.0,
     'buffers_ph': True, 'target_ph': 6.5,
     'nutrient_storage': 0.7, 'releases_nutrients': True,
     'biofiltration_capacity': 0.4,
     'denitrification_mg_n_per_l_per_day': 1.5,
     'supports_anaerobic_layer': True, 'provenance_id': 'tank-2'},
    {'name': 'inert-gravel', 'display_name': 'Inert gravel',
     'water_type': 'fresh', 'kind': 'inert-gravel',
     'grain_size_mm': 4.0, 'biofiltration_capacity': 0.2,
     'denitrification_mg_n_per_l_per_day': 0.5,
     'provenance_id': 'tank-2'},
]

SEED_TANKS = [
    {'name': 'saltwater-tank-1', 'display_name': 'Saltwater tank 1',
     'water_type': 'salt', 'volume_gal': 30.0, 'role': 'general',
     'substrate_name': 'live-aragonite-sand', 'substrate_volume_l': 15.0,
     'provenance_id': 'tank-1'},
    {'name': 'saltwater-tank-2', 'display_name': 'Saltwater tank 2',
     'water_type': 'salt', 'volume_gal': 30.0, 'role': 'macroalgae',
     'substrate_name': 'live-rock-rubble', 'substrate_volume_l': 10.0,
     'provenance_id': 'tank-1'},
    {'name': 'freshwater-tank-1', 'display_name': 'Freshwater tank 1',
     'water_type': 'fresh', 'volume_gal': 30.0, 'role': 'general',
     'substrate_name': 'planted-aquasoil', 'substrate_volume_l': 12.0,
     'provenance_id': 'tank-1'},
]

SEED_TANK_SYSTEMS = [
    # Balanced: fish inputs (+340 N) ~ algae uptake (-350 N); all four
    # required roles present.
    {'name': 'saltwater-food-forest',
     'display_name': 'Saltwater food forest (balanced)',
     'description': 'The reference self-regulating 6-tank system.',
     'water_type': 'salt',
     'tank_names_json': json.dumps(['saltwater-tank-1',
                                    'saltwater-tank-2']),
     'species_stock_json': json.dumps({
         'sea-lettuce': 8, 'red-ogo': 6, 'dulse': 2, 'chaetomorpha': 2,
         'scallops': 4, 'mussels': 6, 'tiger-tail-cucumber': 2,
         'cerith-snails': 10, 'trochus-snails': 6,
         'skunk-cleaner-shrimp': 4, 'pacific-white-shrimp': 6,
         'anchovies': 6, 'sardines': 4}),
     'provenance_id': 'tank-1 balanced'},
    # Fish-heavy: nitrogen accumulates, no nutrient-regulator role.
    {'name': 'saltwater-fish-heavy',
     'display_name': 'Saltwater fish-heavy (imbalanced)',
     'description': 'Fish without enough algae — exercises the '
                    'regulation suggestions.',
     'water_type': 'salt',
     'tank_names_json': json.dumps(['saltwater-tank-1']),
     'species_stock_json': json.dumps({
         'anchovies': 20, 'sardines': 15, 'trochus-snails': 4}),
     'provenance_id': 'tank-1 imbalanced'},
    # Modest-surplus saltwater: the balanced forest + a few extra fish
    # → a small designed nitrogen surplus (~+160 mg N/day) for an algae
    # reactor to consume resiliently (algae-2 reactor-first demo).
    {'name': 'saltwater-modest-surplus',
     'display_name': 'Saltwater modest-surplus (reactor-ready)',
     'description': 'Balanced forest with a small designed N surplus '
                    'sized for one polish algae reactor.',
     'water_type': 'salt',
     'tank_names_json': json.dumps(['saltwater-tank-1',
                                    'saltwater-tank-2']),
     'species_stock_json': json.dumps({
         'sea-lettuce': 8, 'red-ogo': 6, 'dulse': 2, 'chaetomorpha': 2,
         'scallops': 4, 'mussels': 6, 'tiger-tail-cucumber': 2,
         'cerith-snails': 10, 'trochus-snails': 6,
         'skunk-cleaner-shrimp': 4, 'pacific-white-shrimp': 6,
         'anchovies': 13, 'sardines': 6}),
     'provenance_id': 'tank-1 modest-surplus'},
    # Freshwater basic.
    {'name': 'freshwater-basic',
     'display_name': 'Freshwater basic system',
     'description': 'Duckweed + tilapia nutrient loop.',
     'water_type': 'fresh',
     'tank_names_json': json.dumps(['freshwater-tank-1']),
     'species_stock_json': json.dumps({
         'duckweed': 30, 'water-hyacinth': 8, 'hornwort': 10,
         'freshwater-snails': 12, 'freshwater-mussels': 6,
         'amano-shrimp': 15, 'cherry-shrimp': 20, 'tilapia': 6}),
     'provenance_id': 'tank-1 freshwater'},
]
