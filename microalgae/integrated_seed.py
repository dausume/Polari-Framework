"""
@cross-cutting
@module microalgae.integrated_seed
@tags @xc:bindings

algae-2 seeds — two integrated loops, one per design mode:
  reactor-first-forest — a modest-surplus tank sized to a polish
                         reactor → resilient-balanced (the recommended
                         design).
  addon-fishheavy-loop — a big excess fish tank with one reactor →
                         net-accumulating / fragile (the anti-pattern
                         the resilience check flags).
Idempotent-by-name.

@consumers
  - polariServer seed_pairs (after tanks + reactors exist)
@see /SALTWATER_FOOD_FOREST_SPEC.md
"""

import json

SEED_INTEGRATED_LOOPS = [
    {
        'name': 'reactor-first-forest',
        'display_name': 'Reactor-first food forest (resilient)',
        'description': 'An ecosystem designed around a polish algae '
                       'reactor: a modest designed N surplus the reactor '
                       'consumes while fixing CO2; fails safe if the '
                       'reactor stops.',
        'design_mode': 'reactor-first',
        'source_system_names_json': json.dumps(
            ['saltwater-modest-surplus']),
        'source_kind': 'tank',
        'reactor_names_json': json.dumps(['polish-reactor']),
        'provenance_id': 'algae-2 resilient',
    },
    {
        'name': 'addon-fishheavy-loop',
        'display_name': 'Reactor bolted onto a fish-heavy tank (fragile)',
        'description': 'A big excess fish tank with one reactor — the '
                       'resilience check flags it as load-bearing / '
                       'net-accumulating.',
        'design_mode': 'add-on',
        'source_system_names_json': json.dumps(['saltwater-fish-heavy']),
        'source_kind': 'tank',
        'reactor_names_json': json.dumps(['nanno-saltforest-reactor']),
        'provenance_id': 'algae-2 fragile-demo',
    },
]
