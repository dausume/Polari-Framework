"""
@cross-cutting
@module supplychain.chain_seed
@tags @xc:bindings

chain-1 seeds — one demo bio supply chain wiring a node per module:
aquaponics pot, saltwater tank food forest, algae reactor, iron→ferrite
and KDP biomines, a wax source, and a hydroponic garden, fed by an
external mineral feedstock. Outputs are declared priors (grams/year)
until live-resolved. Idempotent-by-name.

@consumers
  - polariServer seed_pairs (nodes + flows before the chain)
@see nutrition/ aquaponics/ tanks/ microalgae/ biomining/ waxsupply/
"""

import json


def _out(resource, kind, rate, unit='g'):
    return {'resource': resource, 'kind': kind, 'ratePerYear': rate,
            'unit': unit}


def _node(name, display, module, system, outputs, inputs=None):
    return {'name': name, 'display_name': display, 'module': module,
            'system_ref': system, 'outputs_json': json.dumps(outputs),
            'inputs_json': json.dumps(inputs or []),
            'provenance_id': 'chain-1'}


SEED_SUPPLY_NODES = [
    _node('aquaponics-pot-node', 'Aquaponics self-watering pot',
          'aquaponics', 'basil-aquaponic-tent',
          [_out('basil', 'food', 900.0),
           _out('permanent-carbon', 'carbon', 5.3)]),
    _node('tank-food-forest-node', 'Saltwater food forest',
          'tanks', 'saltwater-food-forest',
          [_out('seaweed', 'food', 6000.0),
           _out('shellfish-fish-protein', 'food', 4000.0),
           _out('iodine-sodium-chloride', 'nutrient', 300.0),
           _out('co2-cycled', 'carbon', 1800.0),
           _out('excess-nitrogen', 'nutrient', 400.0)]),
    _node('algae-reactor-node', 'Nannochloropsis reactor',
          'microalgae', 'nanno-saltforest-reactor',
          [_out('co2-fixed', 'carbon', 9837.0),
           _out('algae-biomass', 'material', 5365.0)],
          [_out('nitrogen', 'nutrient', 375.0)]),
    _node('biomine-ferrite-node', 'Iron → ferrite biomine',
          'biomining', 'iron-ferrite-biomine',
          [_out('ferrite-magnet-feedstock', 'material', 486000.0)],
          [_out('iron-feedstock', 'material', 400000.0)]),
    _node('biomine-kdp-node', 'KDP electro-optic biomine',
          'biomining', 'kdp-electro-optic-biomine',
          [_out('kdp-crystal', 'material', 158000.0)],
          [_out('phosphate', 'nutrient', 12000.0),
           _out('potassium', 'nutrient', 10000.0)]),
    _node('wax-node', 'Candelilla wax source',
          'waxsupply', 'candelilla',
          [_out('candelilla-wax', 'material', 300.0)]),
    _node('garden-node', 'Hydroponic garden',
          'garden', 'household-hydroponic-reservoir',
          [_out('leafy-greens', 'food', 12000.0),
           _out('mushrooms', 'food', 3000.0)]),
    _node('external-feedstock-node', 'External mineral feedstock',
          'external-feedstock', '',
          [_out('iron-feedstock', 'material', 500000.0),
           _out('phosphate', 'nutrient', 15000.0),
           _out('potassium', 'nutrient', 12000.0)]),
]


def _flow(name, frm, to, resource, kind, rate, unit='g'):
    return {'name': name, 'from_node': frm, 'to_node': to,
            'resource': resource, 'kind': kind, 'rate_per_year': rate,
            'unit': unit, 'provenance_id': 'chain-1'}


SEED_SUPPLY_FLOWS = [
    # tank excess nitrogen feeds the algae reactor (the sustainable loop).
    _flow('tank-to-reactor-n', 'tank-food-forest-node',
          'algae-reactor-node', 'nitrogen', 'nutrient', 375.0),
    # external feedstock feeds the biomines.
    _flow('feedstock-to-ferrite', 'external-feedstock-node',
          'biomine-ferrite-node', 'iron-feedstock', 'material', 400000.0),
    _flow('feedstock-to-kdp-p', 'external-feedstock-node',
          'biomine-kdp-node', 'phosphate', 'nutrient', 12000.0),
    _flow('feedstock-to-kdp-k', 'external-feedstock-node',
          'biomine-kdp-node', 'potassium', 'nutrient', 10000.0),
    # harvested outputs leaving the system.
    _flow('ferrite-harvest', 'biomine-ferrite-node', 'harvest',
          'ferrite-magnet-feedstock', 'material', 486000.0),
    _flow('kdp-harvest', 'biomine-kdp-node', 'harvest', 'kdp-crystal',
          'material', 158000.0),
    _flow('wax-harvest', 'wax-node', 'harvest', 'candelilla-wax',
          'material', 300.0),
    _flow('food-harvest', 'garden-node', 'harvest', 'leafy-greens',
          'food', 12000.0),
]

SEED_SUPPLY_CHAINS = [
    {'name': 'household-bio-chain',
     'display_name': 'Household bio supply chain',
     'description': 'The full chain: food + bio-materials + carbon '
                    'sinks across aquaponics, tanks, algae, biomining, '
                    'wax, and the garden.',
     'node_names_json': json.dumps([n['name'] for n in SEED_SUPPLY_NODES]),
     'flow_names_json': json.dumps([f['name'] for f in SEED_SUPPLY_FLOWS]),
     'provenance_id': 'chain-1'},
]
