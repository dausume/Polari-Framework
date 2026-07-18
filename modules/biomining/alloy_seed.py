"""
@cross-cutting
@module biomining.alloy_seed
@tags @xc:bindings

biomine-1 ferrous-alloy variants (bio-alloys-1) — the nickel
phytomining chain + the galvanized/phosphated bio-steel corrosion-
resistant alternative to stainless. Ultramafic-rock feedstock is
DISREGARDED (not globally available); the Ni hyperaccumulator works on
any Ni-bearing substrate (contaminated soil, plating/battery/industrial
waste). Stainless itself is recorded as gated-on-chromium (see
materialsScience/bio_alloys_seed) and has no build here.
Idempotent-by-name. Flagged priors.

@consumers
  - polariServer seed_pairs (appended to the biomining agent/product/
    system lists)
@see materialsScience/bio_alloys_seed.py
"""

import json

SEED_ALLOY_AGENTS = [
    # Nickel hyperaccumulator PLANT (agromining/phytomining) — reaches
    # percent-level Ni in dry biomass; works on any Ni-bearing substrate.
    {'name': 'nickel-hyperaccumulator-plant',
     'display_name': 'Nickel hyperaccumulator (Odontarrhena/Berkheya)',
     'agent_type': 'plant', 'mechanism': 'bioaccumulation',
     'target_element': 'Ni', 'selectivity': 0.85,
     'uptake_rate_mg_per_g_per_day': 25.0, 'water_type': 'both',
     'byproduct': 'Ni bio-ore ash (~10-20% Ni)',
     'provenance_id': 'bio-alloys-1'},
]

SEED_ALLOY_PRODUCTS = [
    {'name': 'nickel-bio-ore', 'display_name': 'Nickel (from bio-ore)',
     'product_kind': 'nickel-metal', 'source_element': 'Ni',
     'refined_form': 'nickel metal', 'material_ref': 'nickel-metal',
     'refinement_pathway_json': json.dumps([
         'grow hyperaccumulator on a Ni-bearing substrate',
         'harvest + ash to bio-ore (~10-20% Ni)',
         'leach + reduce/smelt to nickel metal']),
     'element_to_product_yield': 1.0, 'purity_target': 0.95,
     'provenance_id': 'bio-alloys-1',
     'notes': 'Phytomining — geology-independent (works on Ni waste/'
              'contaminated soil too). Feeds plating/alloys/batteries/'
              'permalloy; would feed austenitic stainless IF Cr solved.'},
    {'name': 'galvanized-phosphated-steel',
     'display_name': 'Galvanized + phosphated bio-steel',
     'product_kind': 'coated-steel', 'source_element': 'Fe',
     'refined_form': 'phosphated + hot-dip galvanized steel',
     'material_ref': 'galvanized-bio-steel',
     'refinement_pathway_json': json.dumps([
         'carbothermically reduce bio-iron with biochar to plain steel',
         'alloy bio-Mn + bio-Si; form + machine the part',
         'bio-phosphate conversion coat (parkerize)',
         'hot-dip in molten bio-zinc (galvanize)']),
     'element_to_product_yield': 1.0, 'purity_target': 0.9,
     'provenance_id': 'bio-alloys-1',
     'notes': 'A VALID stainless alternative for structural/atmospheric '
              'use (self-healing sacrificial zinc). NOT for food-contact/'
              'immersion/marine/high-temp/machined faces — use bio-'
              'ceramic/geopolymer or bio-silica glass there. Fe is the '
              'bulk; Zn + phosphate are the coating supplements.'},
]

SEED_ALLOY_BIOMINE_SYSTEMS = [
    {'name': 'nickel-phytomining-biomine',
     'display_name': 'Nickel phytomining biomine',
     'description': 'Hyperaccumulator plants concentrate nickel from a '
                    'Ni-bearing substrate (soil or waste) into bio-ore, '
                    'smelted to nickel metal. Geology-independent.',
     'variant': 'trace-metal', 'water_type': 'both',
     'agent_stock_json': json.dumps(
         {'nickel-hyperaccumulator-plant': 40.0}),
     'product_name': 'nickel-bio-ore',
     'source_system_name': 'nickel-bearing-substrate',
     'source_kind': 'feedstock',
     'source_element_supply_mg_per_day': 700.0,
     'extraction_cap_mg_per_day': 0.0, 'provenance_id': 'bio-alloys-1'},
    {'name': 'corrosion-resistant-steel-biomine',
     'display_name': 'Galvanized/phosphated bio-steel biomine',
     'description': 'Bio-iron reduced to steel, then bio-phosphate + '
                    'bio-zinc coated — the community-feasible corrosion-'
                    'resistant alternative to stainless (structural use).',
     'variant': 'steel-feedstock', 'water_type': 'both',
     'agent_stock_json': json.dumps(
         {'iron-oxidizing-bacteria': 30.0,
          'zinc-accumulating-microbe': 15.0,
          'phosphate-accumulating-bacteria': 15.0}),
     'product_name': 'galvanized-phosphated-steel',
     'source_system_name': 'iron-rich-feedstock', 'source_kind':
     'feedstock', 'source_element_supply_mg_per_day': 2000.0,
     'extraction_cap_mg_per_day': 0.0, 'provenance_id': 'bio-alloys-1'},
]
