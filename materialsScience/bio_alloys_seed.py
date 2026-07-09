"""
@cross-cutting
@module materialsScience.bio_alloys_seed
@tags @xc:bindings

Bio-derivable ferrous metals + the honest stainless gap (bio-alloys-1).
Materials the biomining alloy variants refine toward:
  plain-bio-steel        Fe + C (biochar-reduced) + Mn + Si.
  galvanized-bio-steel   plain steel + bio-phosphate conversion coat +
                         bio-zinc hot-dip — a VALID stainless
                         alternative WITHIN an envelope (structural /
                         atmospheric), NOT for food-contact / immersion /
                         high-temp (the honest limits live in `notes`).
  nickel-metal           from Ni hyperaccumulator bio-ore (phytomining).
  stainless-steel        GATED: needs chromium, for which there is no
                         viable bio-route (chromite is refractory; Cr(VI)
                         is pollution). Recorded as an honest gap, not
                         built — disregarded pending a chromium feedstock.

@consumers
  - polariServer seed_pairs (MaterialsScienceMaterial + PropertyMeaning)
  - biomining alloy products' material_ref links resolve to these
@see /biomining/alloy_seed.py
"""

import json

_PROV = 'bio-alloys-1'

SEED_BIO_ALLOY_MATERIALS = [
    {'name': 'plain-bio-steel', 'display_name': 'Plain bio steel',
     'material_kind': 'mixture', 'category': 'structural',
     'element_symbols_json': json.dumps(['Fe', 'C', 'Mn', 'Si']),
     'tags_json': json.dumps(['metal', 'steel', 'fully-bio',
                              'biochar-reduced']),
     'provenance_id': _PROV,
     'notes': 'Bio-iron carbothermically reduced with biochar, alloyed '
              'with bio-Mn + bio-Si. Rusts unprotected — pair with a '
              'coating (galvanized-bio-steel) for corrosion service.'},
    {'name': 'galvanized-bio-steel',
     'display_name': 'Galvanized + phosphated bio steel',
     'material_kind': 'composite', 'category': 'composite',
     'element_symbols_json': json.dumps(['Fe', 'Zn', 'P', 'O', 'C']),
     'tags_json': json.dumps(['metal', 'steel', 'galvanized',
                              'corrosion-resistant', 'fully-bio']),
     'provenance_id': _PROV,
     'notes': 'Plain bio-steel + a bio-phosphate conversion coat + a '
              'bio-zinc hot-dip. VALID stainless alternative FOR: '
              'structural / atmospheric / outdoor corrosion (zinc gives '
              'self-healing sacrificial protection at scratches). NOT '
              'for: food-contact (zinc leaches, esp. acidic), continuous '
              'immersion / marine / acidic-alkaline (incl. the saltwater '
              'tank), high temp (>~200 C), or machined/cut faces. For '
              'those, use bio-ceramic/geopolymer or bio-silica glass '
              '(food-safe, corrosion-proof).'},
    {'name': 'nickel-metal', 'display_name': 'Nickel (bio-ore derived)',
     'material_kind': 'pure', 'category': 'elemental',
     'element_symbols_json': json.dumps(['Ni']),
     'tags_json': json.dumps(['metal', 'nickel', 'phytomined',
                              'fully-bio']),
     'provenance_id': _PROV,
     'notes': 'Smelted from Ni hyperaccumulator bio-ore (agromining). '
              'Useful for plating, Ni alloys, catalysts, batteries, '
              'permalloy magnets — and WOULD feed austenitic stainless '
              'IF a chromium source is ever solved.'},
    {'name': 'stainless-steel',
     'display_name': 'Stainless steel (GATED — not currently bio-feasible)',
     'material_kind': 'mixture', 'category': 'structural',
     'element_symbols_json': json.dumps(['Fe', 'Cr', 'Ni', 'Mn', 'Si']),
     'tags_json': json.dumps(['metal', 'stainless', 'gated',
                              'not-currently-feasible']),
     'provenance_id': _PROV,
     'notes': 'GATED on CHROMIUM (the element that makes steel '
              'stainless, >=10.5%). No viable bulk bio-route: chromite '
              '(FeCr2O4) is refractory to bioleaching, and soluble '
              'Cr(VI) is pollution, not a sustainable feedstock. Ni IS '
              'bio-derivable (phytomining) and Fe/Mn/Si are covered — '
              'only Cr blocks it. Disregarded for now; use '
              'galvanized-bio-steel (structural) or bio-ceramic/glass '
              '(food/wet) instead.'},
]

SEED_BIO_ALLOY_PROPERTY_MEANINGS = [
    {'name': 'corrosionProtectionMode',
     'display_name': 'Corrosion protection mode',
     'units': 'category',
     'meaning': 'HOW a metal resists corrosion: passive (a self-healing '
                'oxide throughout the bulk, e.g. stainless Cr2O3), '
                'sacrificial (a coating that corrodes preferentially, '
                'e.g. zinc galvanizing), or barrier (an inert coating '
                'that fails once breached, e.g. paint/phosphate alone).',
     'scenario_context': 'Passive protection survives machining + '
                         'immersion + heat (why stainless is used for '
                         'food/wet/hot); sacrificial zinc self-heals '
                         'scratches but is consumed over time and fails '
                         'in food/acid/marine/high-temp service — the '
                         'envelope galvanized-bio-steel is valid within.',
     'aliases_json': json.dumps(
         ['protectionMode', 'corrosion_protection_mode',
          'corrosionMode']),
     'scale_levels_json': json.dumps([0, 1])},
]
