"""
@cross-cutting
@module aquaponics.media_seed
@tags @xc:bindings

Seeds for aqp-2: the nutrient-species vocabulary + reference soils,
waters, and nutrient profiles (one hydroponic, one aquaponic).
Idempotent-by-name.

@consumers
  - polariServer seed_pairs
@see /AQUAPONICS_MODULE_PLAN.md
"""

import json

#: The shared nutrient/gas vocabulary. Typical ranges are healthy
#: hydroponic-solution bands (mg/L) — editable priors.
SEED_NUTRIENT_SPECIES = [
    {'name': 'nitrate-n', 'display_name': 'Nitrate nitrogen',
     'symbol': 'NO3-N', 'role': 'macronutrient', 'unit': 'mg/L',
     'plant_mobility': 'mobile', 'typical_min': 100.0,
     'typical_max': 200.0,
     'description': 'Primary N source for most crops.'},
    {'name': 'ammonium-n', 'display_name': 'Ammonium nitrogen',
     'symbol': 'NH4-N', 'role': 'macronutrient', 'unit': 'mg/L',
     'plant_mobility': 'mobile', 'typical_min': 0.0,
     'typical_max': 20.0,
     'description': 'Aquaponic fish waste starts here before '
                    'nitrification; high levels are toxic.'},
    {'name': 'phosphorus-p', 'display_name': 'Phosphorus',
     'symbol': 'P', 'role': 'macronutrient', 'unit': 'mg/L',
     'plant_mobility': 'mobile', 'typical_min': 30.0,
     'typical_max': 50.0, 'description': 'Root + flower development.'},
    {'name': 'potassium-k', 'display_name': 'Potassium', 'symbol': 'K',
     'role': 'macronutrient', 'unit': 'mg/L',
     'plant_mobility': 'mobile', 'typical_min': 150.0,
     'typical_max': 300.0,
     'description': 'Osmotic regulation, fruiting.'},
    {'name': 'calcium-ca', 'display_name': 'Calcium', 'symbol': 'Ca',
     'role': 'secondary', 'unit': 'mg/L', 'plant_mobility': 'immobile',
     'typical_min': 150.0, 'typical_max': 200.0,
     'description': 'Cell walls; immobile → deficiency shows in new '
                    'growth.'},
    {'name': 'magnesium-mg', 'display_name': 'Magnesium',
     'symbol': 'Mg', 'role': 'secondary', 'unit': 'mg/L',
     'plant_mobility': 'mobile', 'typical_min': 40.0,
     'typical_max': 70.0,
     'description': 'Chlorophyll core.'},
    {'name': 'sulfur-s', 'display_name': 'Sulfur', 'symbol': 'S',
     'role': 'secondary', 'unit': 'mg/L', 'plant_mobility': 'immobile',
     'typical_min': 60.0, 'typical_max': 120.0,
     'description': 'Amino acids.'},
    {'name': 'iron-fe', 'display_name': 'Iron', 'symbol': 'Fe',
     'role': 'micronutrient', 'unit': 'mg/L',
     'plant_mobility': 'immobile', 'typical_min': 2.0,
     'typical_max': 5.0,
     'description': 'Chelated Fe; first micro to go deficient.'},
    {'name': 'manganese-mn', 'display_name': 'Manganese',
     'symbol': 'Mn', 'role': 'micronutrient', 'unit': 'mg/L',
     'plant_mobility': 'immobile', 'typical_min': 0.5,
     'typical_max': 1.0, 'description': 'Photosynthesis enzymes.'},
    {'name': 'zinc-zn', 'display_name': 'Zinc', 'symbol': 'Zn',
     'role': 'micronutrient', 'unit': 'mg/L',
     'plant_mobility': 'immobile', 'typical_min': 0.05,
     'typical_max': 0.3, 'description': 'Auxin synthesis.'},
    {'name': 'boron-b', 'display_name': 'Boron', 'symbol': 'B',
     'role': 'micronutrient', 'unit': 'mg/L',
     'plant_mobility': 'immobile', 'typical_min': 0.2,
     'typical_max': 0.5, 'description': 'Cell wall + pollen.'},
    {'name': 'dissolved-oxygen', 'display_name': 'Dissolved oxygen',
     'symbol': 'O2(aq)', 'role': 'dissolved-gas', 'unit': 'mg/L',
     'plant_mobility': 'n/a', 'typical_min': 5.0, 'typical_max': 9.0,
     'description': 'Root respiration; also the fish constraint in '
                    'aquaponics.'},
    {'name': 'dissolved-co2', 'display_name': 'Dissolved CO2',
     'symbol': 'CO2(aq)', 'role': 'dissolved-gas', 'unit': 'mg/L',
     'plant_mobility': 'n/a', 'typical_min': 1.0, 'typical_max': 10.0,
     'description': 'Couples to root zone + atmosphere exchange.'},
]

SEED_NUTRIENT_PROFILES = [
    {
        'name': 'leafy-greens-hydroponic',
        'display_name': 'Leafy greens (hydroponic)',
        'description': 'Balanced hydroponic feed for lettuce/herbs.',
        'concentrations_json': json.dumps({
            'nitrate-n': 150.0, 'ammonium-n': 10.0,
            'phosphorus-p': 40.0, 'potassium-k': 210.0,
            'calcium-ca': 175.0, 'magnesium-mg': 50.0,
            'sulfur-s': 90.0, 'iron-fe': 3.0, 'manganese-mn': 0.6,
            'zinc-zn': 0.15, 'boron-b': 0.3,
            'dissolved-oxygen': 7.5, 'dissolved-co2': 4.0}),
        'ph': 5.9, 'electrical_conductivity_ds_m': 1.6,
        'temperature_c': 20.0, 'basis': 'water-mg-per-L',
        'provenance_id': 'aqp-2 hydroponic reference',
    },
    {
        'name': 'tilapia-aquaponic',
        'display_name': 'Tilapia aquaponic loop',
        'description': 'Aquaponic solution — lower P/K than hydro, '
                       'some residual ammonium, iron often deficient '
                       '(the classic aquaponic gap).',
        'concentrations_json': json.dumps({
            'nitrate-n': 120.0, 'ammonium-n': 12.0,
            'phosphorus-p': 20.0, 'potassium-k': 90.0,
            'calcium-ca': 160.0, 'magnesium-mg': 45.0,
            'sulfur-s': 70.0, 'iron-fe': 1.2, 'manganese-mn': 0.5,
            'zinc-zn': 0.08, 'boron-b': 0.25,
            'dissolved-oxygen': 6.5, 'dissolved-co2': 6.0}),
        'ph': 6.8, 'electrical_conductivity_ds_m': 1.1,
        'temperature_c': 24.0, 'basis': 'water-mg-per-L',
        'provenance_id': 'aqp-2 aquaponic reference (Fe deficient)',
    },
]

SEED_SOILS = [
    {
        'name': 'coir-perlite-mix',
        'display_name': 'Coir + perlite (70/30)',
        'description': 'Free-draining soilless mix — the reference '
                       'self-watering pot medium.',
        'texture': 'coir',
        'bulk_density_kg_m3': 120.0, 'particle_density_kg_m3': 1500.0,
        'saturation_vol': 0.65, 'field_capacity_vol': 0.45,
        'wilting_point_vol': 0.10,
        'hydraulic_conductivity_mm_hr': 120.0,
        'cation_exchange_cmol_kg': 40.0,
        'organic_matter_fraction': 0.85,
        'nutrient_profile_name': '',
        'scales_json': json.dumps([
            {'scale': 'aggregate', 'grainSizeUm': 2000,
             'role': 'coir fibre bundles + perlite grains — '
                     'macropores drain fast'},
            {'scale': 'pore', 'grainSizeUm': 100,
             'role': 'intra-fibre capillary pores hold plant-'
                     'available water'},
            {'scale': 'colloid', 'grainSizeUm': 1,
             'role': 'coir surface CEC binds cations (K, Ca, Mg)'},
        ]),
        'provenance_id': 'aqp-2 medium reference',
    },
    {
        'name': 'sandy-loam',
        'display_name': 'Sandy loam',
        'description': 'A mineral garden soil for comparison.',
        'texture': 'loam',
        'bulk_density_kg_m3': 1450.0,
        'particle_density_kg_m3': 2650.0,
        'saturation_vol': 0.43, 'field_capacity_vol': 0.27,
        'wilting_point_vol': 0.11,
        'hydraulic_conductivity_mm_hr': 25.0,
        'cation_exchange_cmol_kg': 12.0,
        'organic_matter_fraction': 0.03,
        'nutrient_profile_name': '',
        'scales_json': json.dumps([
            {'scale': 'aggregate', 'grainSizeUm': 500,
             'role': 'sand + aggregate structure'},
            {'scale': 'pore', 'grainSizeUm': 30,
             'role': 'mesopores hold available water'},
            {'scale': 'colloid', 'grainSizeUm': 2,
             'role': 'clay + humus colloids, CEC'},
        ]),
        'provenance_id': 'aqp-2 mineral soil reference',
    },
]

SEED_WATERS = [
    {
        'name': 'tilapia-aquaponic-loop',
        'display_name': 'Tilapia aquaponic loop',
        'description': 'Recirculating aquaponic source feeding the '
                       'pot input holes.',
        'source_kind': 'aquaponic',
        'source_params_json': json.dumps({
            'fishSpecies': 'nile-tilapia', 'tankVolumeL': 200,
            'stockingKgPerM3': 20, 'feedRateGPerDay': 120,
            'biofilter': 'nitrifying media bed'}),
        'temperature_c': 24.0, 'ph': 6.8,
        'electrical_conductivity_ds_m': 1.1,
        'dissolved_oxygen_mg_l': 6.5, 'dissolved_co2_mg_l': 6.0,
        'flow_rate_l_per_hr': 1.5,
        'nutrient_profile_name': 'tilapia-aquaponic',
        'scales_json': json.dumps([
            {'scale': 'molecular', 'role': 'H2O + dissolved ions '
                                           '(NO3-, NH4+, K+, Ca2+) + '
                                           'dissolved O2/CO2'},
            {'scale': 'colloid', 'role': 'fine organic particulate '
                                         'from fish waste'},
            {'scale': 'bulk', 'role': 'the recirculating flow through '
                                      'the pot'},
        ]),
        'provenance_id': 'aqp-2 aquaponic source',
    },
    {
        'name': 'hydroponic-reservoir',
        'display_name': 'Hydroponic dosing reservoir',
        'description': 'A dosed hydroponic reservoir source.',
        'source_kind': 'hydroponic',
        'source_params_json': json.dumps({
            'reservoirL': 100, 'dosing': 'A+B stock + pH down',
            'topUp': 'RO water'}),
        'temperature_c': 20.0, 'ph': 5.9,
        'electrical_conductivity_ds_m': 1.6,
        'dissolved_oxygen_mg_l': 7.5, 'dissolved_co2_mg_l': 4.0,
        'flow_rate_l_per_hr': 1.0,
        'nutrient_profile_name': 'leafy-greens-hydroponic',
        'scales_json': json.dumps([
            {'scale': 'molecular', 'role': 'fully dissolved salts + '
                                           'dissolved gases'},
            {'scale': 'bulk', 'role': 'reservoir flow to the pot'},
        ]),
        'provenance_id': 'aqp-2 hydroponic source',
    },
]
