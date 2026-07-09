"""
@cross-cutting
@module biomining.biomining_seed
@tags @xc:bindings

biomine-1 seeds — bioextraction agents, refined products (linked to the
real materialsScience ferrite + carbon-nanotube material rows), and four
specialized aquaponic variants: iron→ferrite (magnets), mixed-metal→
steel feedstock, carbon→CNT feedstock, and P→nutrient recovery that
supplements a lacking system. Idempotent-by-name. Flagged priors.

@consumers
  - polariServer seed_pairs (agents + products before systems)
@see materialsScience/ material rows: 'ferrite', 'carbon-nanotube'
"""

import json

SEED_BIOEXTRACTION_AGENTS = [
    # Iron: magnetotactic bacteria biomineralize magnetite directly —
    # the ideal ferrite precursor.
    {'name': 'magnetotactic-bacteria',
     'display_name': 'Magnetotactic bacteria', 'agent_type': 'bacteria',
     'mechanism': 'biomineralization', 'target_element': 'Fe',
     'selectivity': 0.9, 'uptake_rate_mg_per_g_per_day': 30.0,
     'water_type': 'both', 'byproduct': 'intracellular magnetite (Fe3O4)',
     'provenance_id': 'biomine-1'},
    {'name': 'iron-oxidizing-bacteria',
     'display_name': 'Iron-oxidizing bacteria (Gallionella/Leptothrix)',
     'agent_type': 'bacteria', 'mechanism': 'bioprecipitation',
     'target_element': 'Fe', 'selectivity': 0.8,
     'uptake_rate_mg_per_g_per_day': 45.0, 'water_type': 'fresh',
     'byproduct': 'ferric oxyhydroxide sheaths', 'provenance_id':
     'biomine-1'},
    # Steel-alloy metals via bioleaching.
    {'name': 'metal-bioleaching-bacteria',
     'display_name': 'Acidithiobacillus (bioleaching)',
     'agent_type': 'bacteria', 'mechanism': 'bioleaching',
     'target_element': 'Fe', 'selectivity': 0.55,
     'uptake_rate_mg_per_g_per_day': 35.0, 'water_type': 'fresh',
     'optimal_ph': 2.5, 'byproduct': 'leached Ni/Cr/Mn co-mobilized',
     'provenance_id': 'biomine-1'},
    # Carbon-concentrating alga for CNT feedstock.
    {'name': 'carbon-concentrating-alga',
     'display_name': 'Carbon-concentrating microalga',
     'agent_type': 'algae', 'mechanism': 'bioaccumulation',
     'target_element': 'C', 'selectivity': 0.7,
     'uptake_rate_mg_per_g_per_day': 60.0, 'water_type': 'both',
     'byproduct': 'high-carbon biomass', 'provenance_id': 'biomine-1'},
    # Phosphate-accumulating organisms for nutrient recovery.
    {'name': 'phosphate-accumulating-bacteria',
     'display_name': 'Phosphate-accumulating organisms (PAOs)',
     'agent_type': 'bacteria', 'mechanism': 'bioaccumulation',
     'target_element': 'P', 'selectivity': 0.85,
     'uptake_rate_mg_per_g_per_day': 25.0, 'water_type': 'both',
     'byproduct': 'polyphosphate granules', 'provenance_id': 'biomine-1'},
]

SEED_BIOMINERAL_PRODUCTS = [
    {'name': 'ferrite-magnet-feedstock',
     'display_name': 'Ferrite magnet feedstock',
     'product_kind': 'ferrite-magnet', 'source_element': 'Fe',
     'refined_form': 'magnetite Fe3O4 → sintered ferrite',
     'material_ref': 'ferrite',
     'refinement_pathway_json': json.dumps([
         'harvest magnetite-bearing biomass', 'lyse + magnetic separation',
         'calcine to Fe3O4 powder', 'blend carbonates + sinter to ferrite',
         'magnetize']),
     'element_to_product_yield': 1.38, 'purity_target': 0.92,
     'provenance_id': 'biomine-1'},
    {'name': 'steel-feedstock',
     'display_name': 'Reduced steel feedstock',
     'product_kind': 'steel-feedstock', 'source_element': 'Fe',
     'refined_form': 'reduced metal powder (Fe + Ni/Cr/Mn)',
     'material_ref': '',
     'refinement_pathway_json': json.dumps([
         'collect leachate metals', 'precipitate + dewater',
         'carbothermic/H2 reduction to metal powder',
         'alloy blend for steel']),
     'element_to_product_yield': 1.0, 'purity_target': 0.85,
     'provenance_id': 'biomine-1'},
    {'name': 'cnt-carbon-feedstock',
     'display_name': 'Carbon-nanotube carbon feedstock',
     'product_kind': 'carbon-nanotube-feedstock', 'source_element': 'C',
     'refined_form': 'purified graphitic carbon',
     'material_ref': 'carbon-nanotube',
     'refinement_pathway_json': json.dumps([
         'harvest high-carbon biomass', 'pyrolyze to biochar',
         'graphitize + purify', 'CVD growth into carbon nanotubes']),
     'element_to_product_yield': 0.8, 'purity_target': 0.95,
     'provenance_id': 'biomine-1'},
    {'name': 'recovered-phosphate',
     'display_name': 'Recovered phosphate (struvite)',
     'product_kind': 'recovered-nutrient', 'source_element': 'P',
     'refined_form': 'struvite / phosphate salt',
     'material_ref': '',
     'refinement_pathway_json': json.dumps([
         'harvest polyphosphate biomass', 'release P',
         'precipitate struvite (MgNH4PO4)']),
     'element_to_product_yield': 3.0, 'purity_target': 0.9,
     'provenance_id': 'biomine-1'},
]

SEED_BIOMINE_SYSTEMS = [
    {'name': 'iron-ferrite-biomine',
     'display_name': 'Iron → ferrite (magnets) biomine',
     'description': 'Magnetotactic + iron bacteria pull dissolved iron '
                    'from an iron-rich feedstock into magnetite for '
                    'ferrite magnets.',
     'variant': 'iron-ferrite', 'water_type': 'fresh',
     'agent_stock_json': json.dumps({'magnetotactic-bacteria': 20.0,
                                     'iron-oxidizing-bacteria': 15.0}),
     'product_name': 'ferrite-magnet-feedstock',
     'source_system_name': 'iron-rich-feedstock', 'source_kind':
     'feedstock', 'source_element_supply_mg_per_day': 1500.0,
     'extraction_cap_mg_per_day': 0.0, 'provenance_id': 'biomine-1'},
    {'name': 'steel-feedstock-biomine',
     'display_name': 'Mixed metals → steel feedstock biomine',
     'description': 'Bioleaching bacteria mobilize Fe/Ni/Cr/Mn into a '
                    'reduced steel feedstock.',
     'variant': 'steel-feedstock', 'water_type': 'fresh',
     'agent_stock_json': json.dumps({'metal-bioleaching-bacteria': 30.0}),
     'product_name': 'steel-feedstock',
     'source_system_name': 'metal-tailings-feedstock',
     'source_kind': 'feedstock',
     'source_element_supply_mg_per_day': 800.0,
     'extraction_cap_mg_per_day': 0.0, 'provenance_id': 'biomine-1'},
    {'name': 'carbon-cnt-biomine',
     'display_name': 'Carbon → CNT feedstock biomine',
     'description': 'Carbon-concentrating algae build high-carbon '
                    'biomass, refined toward carbon-nanotube feedstock; '
                    'fed by an algae reactor\'s biomass carbon.',
     'variant': 'carbon-nanotube', 'water_type': 'both',
     'agent_stock_json': json.dumps({'carbon-concentrating-alga': 40.0}),
     'product_name': 'cnt-carbon-feedstock',
     'source_system_name': 'nanno-saltforest-reactor',
     'source_kind': 'reactor',
     'source_element_supply_mg_per_day': 5000.0,
     'extraction_cap_mg_per_day': 0.0, 'provenance_id': 'biomine-1'},
    {'name': 'phosphate-recovery-biomine',
     'display_name': 'Phosphate recovery → supplement a lacking system',
     'description': 'PAOs recover excess phosphate from a nutrient-heavy '
                    'tank and supply it to a P-deficient hydroponic loop.',
     'variant': 'nutrient-recovery', 'water_type': 'salt',
     'agent_stock_json': json.dumps(
         {'phosphate-accumulating-bacteria': 25.0}),
     'product_name': 'recovered-phosphate',
     'source_system_name': 'saltwater-fish-heavy', 'source_kind': 'tank',
     'source_element_supply_mg_per_day': 0.0,
     'extraction_cap_mg_per_day': 300.0,
     'supplement_target_system': 'household-hydroponic-reservoir',
     'provenance_id': 'biomine-1'},
]
