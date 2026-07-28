"""
@module supplychain.sourcing_seed

Seeded sources, REAL dated price citations (web research 2026-07-28),
and the default preference ladder (Dustin's ordering, as data).

Citation honesty: is_estimate=True wherever a figure is inferred
(a price RANGE without a size mapping, a 'from $X/lb' floor) rather
than a listed exact price — the citation_note says which.

@consumers polariServer seed_pairs
"""

import json

#: Item vocabulary (item_ref) used across citations/supplies/demands:
#: geopolymer-kit, soy-wax, beeswax, carnauba-wax, wax-source-biomass,
#: geopolymer-self-watering-pot, geopolymer-pot-shelf.

SEED_SUPPLY_SOURCES = [
    {
        'name': 'geopolymer-international',
        'display_name': 'Geopolymer International (gpi.earth)',
        'supplier_name': 'Geopolymer International',
        'url': 'https://gpi.earth/',
        'is_open_source': False, 'is_commercial': True,
        'is_local': False, 'is_polari': False,
        'is_eco_friendly': True,
        'availability': 'available',
        'supplies_json': json.dumps(['geopolymer-kit']),
        'demands_json': '[]',
        'business_model_ref': '',
        'locality_note': 'South Carolina, US — ships',
        'is_prior': True, 'provenance_id': 'src-1',
        'notes': 'Hydroxide-free geopolymer kits (GeoCement/GeoPrint) '
                 'for casting pots, vases, furniture. eco flag per '
                 'VENDOR CLAIM of ~80% CO2 reduction vs Portland '
                 'cement — not independently verified here.',
    },
    {
        'name': 'aztec-candle-soap',
        'display_name': 'Aztec Candle & Soap (candlemaking.com)',
        'supplier_name': 'Aztec Candle & Soap Making Supplies',
        'url': 'https://www.candlemaking.com/',
        'is_open_source': False, 'is_commercial': True,
        'is_local': False, 'is_polari': False,
        'is_eco_friendly': False,
        'availability': 'available',
        'supplies_json': json.dumps(['soy-wax']),
        'demands_json': '[]',
        'business_model_ref': '',
        'locality_note': '',
        'is_prior': True, 'provenance_id': 'src-1',
        'notes': 'Bulk soy container wax (LP402) by the 50 lb case.',
    },
    {
        'name': 'bulk-beeswax-com',
        'display_name': 'Bulk Beeswax (bulkbeeswax.com)',
        'supplier_name': 'Bulk Beeswax',
        'url': 'https://bulkbeeswax.com/',
        'is_open_source': False, 'is_commercial': True,
        'is_local': False, 'is_polari': False,
        'is_eco_friendly': False,
        'availability': 'available',
        'supplies_json': json.dumps(['beeswax']),
        'demands_json': '[]',
        'business_model_ref': '',
        'locality_note': '',
        'is_prior': True, 'provenance_id': 'src-1',
        'notes': 'Wholesale beeswax; advertised floor price per lb.',
    },
    {
        'name': 'aroma-depot',
        'display_name': 'Aroma Depot (aromadepot.com)',
        'supplier_name': 'Aroma Depot',
        'url': 'https://aromadepot.com/',
        'is_open_source': False, 'is_commercial': True,
        'is_local': False, 'is_polari': False,
        'is_eco_friendly': False,
        'availability': 'available',
        'supplies_json': json.dumps(['carnauba-wax']),
        'demands_json': '[]',
        'business_model_ref': '',
        'locality_note': '',
        'is_prior': True, 'provenance_id': 'src-1',
        'notes': 'Carnauba T1 flakes — the cheaper of two cited '
                 'commercial carnauba sources.',
    },
    {
        'name': 'oils-center',
        'display_name': 'Oils Center (oilscenter.com)',
        'supplier_name': 'Oils Center',
        'url': 'https://oilscenter.com/',
        'is_open_source': False, 'is_commercial': True,
        'is_local': False, 'is_polari': False,
        'is_eco_friendly': False,
        'availability': 'available',
        'supplies_json': json.dumps(['carnauba-wax']),
        'demands_json': '[]',
        'business_model_ref': '',
        'locality_note': '',
        'is_prior': True, 'provenance_id': 'src-1',
        'notes': 'Second commercial carnauba source — exists so the '
                 'price-compare has a real spread to show.',
    },
    {
        'name': 'machinable-wax-com',
        'display_name': 'MachinableWax.com (Print2Cast)',
        'supplier_name': 'MachinableWax.com',
        'url': 'https://machinablewax.com/',
        'is_open_source': False, 'is_commercial': True,
        'is_local': False, 'is_polari': False,
        'is_eco_friendly': False,
        'availability': 'available',
        'supplies_json': json.dumps(['machinable-wax']),
        'demands_json': '[]',
        'business_model_ref': '',
        'locality_note': '',
        'is_prior': True, 'provenance_id': 'src-3',
        'notes': 'THE current commercial alternative for 3D-printing '
                 'wax (machinable/Print2Cast). NOT eco-friendly: '
                 'machinable wax is a paraffin + polyethylene '
                 '(plastic) blend, and it emits fumes when '
                 'overheated — ventilation required, non-user-'
                 'friendly under some conditions. Exists here as the '
                 'substitute benchmark our natural blend must beat.',
    },
    {
        'name': 'pool360-metamax',
        'display_name': 'POOL360 (BASF MetaMax metakaolin)',
        'supplier_name': 'POOL360 / SCP Distributors',
        'url': 'https://www.pool360.com/',
        'is_open_source': False, 'is_commercial': True,
        'is_local': False, 'is_polari': False,
        'is_eco_friendly': False,
        'availability': 'available',
        'supplies_json': json.dumps(['metakaolin']),
        'demands_json': '[]',
        'business_model_ref': '',
        'locality_note': 'pool-plaster distribution network',
        'is_prior': True, 'provenance_id': 'src-4',
        'notes': 'Metakaolin ships in 55 lb bags through pool-plaster '
                 'supply — the accessible retail-ish channel for the '
                 'geopolymer precursor.',
    },
    {
        'name': 'sheffield-pottery',
        'display_name': 'Sheffield Pottery (sheffield-pottery.com)',
        'supplier_name': 'Sheffield Pottery',
        'url': 'https://www.sheffield-pottery.com/',
        'is_open_source': False, 'is_commercial': True,
        'is_local': False, 'is_polari': False,
        'is_eco_friendly': False,
        'availability': 'available',
        'supplies_json': json.dumps(['sodium-silicate-solution']),
        'demands_json': '[]',
        'business_model_ref': '',
        'locality_note': '',
        'is_prior': True, 'provenance_id': 'src-4',
        'notes': 'Pottery-supply waterglass (40% solution) by the '
                 'gallon — the silicate activator channel.',
    },
    {
        'name': 'essential-depot',
        'display_name': 'Essential Depot (essentialdepot.com)',
        'supplier_name': 'Essential Depot',
        'url': 'https://www.essentialdepot.com/',
        'is_open_source': False, 'is_commercial': True,
        'is_local': False, 'is_polari': False,
        'is_eco_friendly': False,
        'availability': 'available',
        'supplies_json': json.dumps(['sodium-hydroxide-lye']),
        'demands_json': '[]',
        'business_model_ref': '',
        'locality_note': '',
        'is_prior': True, 'provenance_id': 'src-4',
        'notes': 'Food-grade NaOH micro-beads in bulk (soap-making '
                 'channel). CAUSTIC — PPE required; the user-'
                 'friendliness cost of the DIY alkali route.',
    },
    {
        'name': 'home-depot',
        'display_name': 'The Home Depot (big-box)',
        'supplier_name': 'The Home Depot',
        'url': 'https://www.homedepot.com/',
        'is_open_source': False, 'is_commercial': True,
        'is_local': False, 'is_polari': False,
        'is_eco_friendly': False,
        'availability': 'available',
        'supplies_json': json.dumps(['silica-sand']),
        'demands_json': '[]',
        'business_model_ref': '',
        'locality_note': 'big-box, locally stocked everywhere',
        'is_prior': True, 'provenance_id': 'src-4',
        'notes': 'Washed/screened/dried play sand — the aggregate. '
                 'Locally STOCKED but not a local business (the '
                 'is_local flag means local enterprise, not local '
                 'shelf).',
    },
    {
        'name': 'polari-waxprint-lab',
        'display_name': 'Polari wax-print lab (our own blend)',
        'supplier_name': 'Polari (self)',
        'url': '',
        'is_open_source': True, 'is_commercial': False,
        'is_local': True, 'is_polari': True,
        'is_eco_friendly': True,
        'availability': 'potential',
        'supplies_json': json.dumps(['natural-print-wax-blend']),
        'demands_json': json.dumps(['soy-wax', 'beeswax',
                                    'carnauba-wax']),
        'business_model_ref': 'wax-mold-goods-microbusiness',
        'locality_note': 'on-site',
        'is_prior': True, 'provenance_id': 'src-1',
        'notes': 'POTENTIAL: blend the natural 3D-printable wax '
                 'ourselves from cited raw waxes (waxprint '
                 'WaxFeedstockDefinition carries the material '
                 'properties). Rank-1 on the default ladder once '
                 'real.',
    },
    {
        'name': 'local-hydroponics-farm',
        'display_name': 'Local hydroponics farm (potential partner)',
        'supplier_name': '(to be found/founded)',
        'url': '',
        'is_open_source': False, 'is_commercial': True,
        'is_local': True, 'is_polari': False,
        'is_eco_friendly': True,
        'availability': 'potential',
        'supplies_json': json.dumps(['wax-source-biomass']),
        'demands_json': json.dumps(['geopolymer-self-watering-pot',
                                    'geopolymer-pot-shelf']),
        'business_model_ref': 'hydroponic-wax-source-farm',
        'locality_note': 'local delivery radius',
        'is_prior': True, 'provenance_id': 'src-1',
        'notes': 'The alternate-source-as-business-model example: a '
                 'hydroponics business growing the wax source — AND '
                 'a customer wanting geopolymer self-watering pots '
                 'plus shelving for them (mutual supply loop). '
                 'Climbs to rank 1 if it adopts the polari '
                 'open-source stack (flags are editable data).',
    },
]

SEED_PRICE_CITATIONS = [
    {
        'name': 'gpi-geocement-10lb-2026-07-28',
        'source_ref': 'geopolymer-international',
        'item_ref': 'geopolymer-kit',
        'price': 34.95, 'currency': 'USD',
        'amount': 10.0, 'amount_unit': 'lb',
        'observed_at': '2026-07-28T10:20:00',
        'citation_url': 'https://gpi.earth/product/'
                        'geocement-repair-mortar/',
        'citation_note': 'GeoCement & Repair Mortar page lists pack '
                         'sizes (10 lb kit .. 50 lb) with a PRICE '
                         'RANGE $34.95-$110.00; low end mapped to '
                         'the 10 lb kit by inference.',
        'is_estimate': True,
        'is_prior': True, 'provenance_id': 'src-1', 'notes': '',
    },
    {
        'name': 'gpi-geocement-50lb-2026-07-28',
        'source_ref': 'geopolymer-international',
        'item_ref': 'geopolymer-kit',
        'price': 110.00, 'currency': 'USD',
        'amount': 50.0, 'amount_unit': 'lb',
        'observed_at': '2026-07-28T10:20:00',
        'citation_url': 'https://gpi.earth/product/'
                        'geocement-repair-mortar/',
        'citation_note': 'High end of the listed $34.95-$110.00 '
                         'range mapped to the 50 lb size by '
                         'inference.',
        'is_estimate': True,
        'is_prior': True, 'provenance_id': 'src-1', 'notes': '',
    },
    {
        'name': 'aztec-lp402-soy-50lb-2026-07-28',
        'source_ref': 'aztec-candle-soap',
        'item_ref': 'soy-wax',
        'price': 109.00, 'currency': 'USD',
        'amount': 50.0, 'amount_unit': 'lb',
        'observed_at': '2026-07-28T10:15:00',
        'citation_url': 'https://www.candlemaking.com/'
                        'lp-402-soy-container-wax-50lb-case.html',
        'citation_note': 'LP 402 Soy Container Wax — 50 lb case, '
                         'listed price.',
        'is_estimate': False,
        'is_prior': True, 'provenance_id': 'src-1', 'notes': '',
    },
    {
        'name': 'bulkbeeswax-floor-2026-07-28',
        'source_ref': 'bulk-beeswax-com',
        'item_ref': 'beeswax',
        'price': 8.99, 'currency': 'USD',
        'amount': 1.0, 'amount_unit': 'lb',
        'observed_at': '2026-07-28T10:17:00',
        'citation_url': 'https://bulkbeeswax.com/',
        'citation_note': 'Advertised wholesale FLOOR ("from '
                         '$8.99/lb") — actual tier pricing varies '
                         'with quantity.',
        'is_estimate': True,
        'is_prior': True, 'provenance_id': 'src-1', 'notes': '',
    },
    {
        'name': 'aromadepot-carnauba-5lb-2026-07-28',
        'source_ref': 'aroma-depot',
        'item_ref': 'carnauba-wax',
        'price': 78.36, 'currency': 'USD',
        'amount': 5.0, 'amount_unit': 'lb',
        'observed_at': '2026-07-28T10:18:00',
        'citation_url': 'https://aromadepot.com/product/'
                        'carnauba-wax-flakes-t1-100-pure-natural-'
                        'multipurpose/',
        'citation_note': 'Carnauba T1 flakes, 5 lb listing.',
        'is_estimate': False,
        'is_prior': True, 'provenance_id': 'src-1', 'notes': '',
    },
    {
        'name': 'oilscenter-carnauba-5lb-2026-07-28',
        'source_ref': 'oils-center',
        'item_ref': 'carnauba-wax',
        'price': 92.99, 'currency': 'USD',
        'amount': 5.0, 'amount_unit': 'lb',
        'observed_at': '2026-07-28T10:18:00',
        'citation_url': 'https://oilscenter.com/'
                        'carnauba-wax-brazil-flakes',
        'citation_note': 'Carnauba Brazil flakes, 5 lb listing.',
        'is_estimate': False,
        'is_prior': True, 'provenance_id': 'src-1', 'notes': '',
    },
]

SEED_PRICE_CITATIONS.append(
    {
        'name': 'machinablewax-pellets-2026-07-28',
        'source_ref': 'machinable-wax-com',
        'item_ref': 'machinable-wax',
        'price': 10.00, 'currency': 'USD',
        'amount': 1.0, 'amount_unit': 'lb',
        'observed_at': '2026-07-28T11:05:00',
        'citation_url': 'https://machinablewax.com/'
                        'machinable-wax-pelletized-10-pound-box/',
        'citation_note': 'Pelletized 10 lb box product exists; exact '
                         'store price NOT retrievable at observation '
                         'time (site TLS error) — ~$10/lb is the '
                         'commonly forum-referenced figure for '
                         'machinable wax. Re-cite with the exact '
                         'store price when reachable.',
        'is_estimate': True,
        'is_prior': True, 'provenance_id': 'src-3', 'notes': '',
    })

SEED_PRICE_CITATIONS.extend([
    {
        'name': 'pool360-metamax-55lb-2026-07-28',
        'source_ref': 'pool360-metamax',
        'item_ref': 'metakaolin',
        'price': 70.00, 'currency': 'USD',
        'amount': 55.0, 'amount_unit': 'lb',
        'observed_at': '2026-07-28T11:35:00',
        'citation_url': 'https://www.pool360.com/Product/'
                        '55-lb-pa-metamax-metakaolin-pool-aaa-65-300',
        'citation_note': '55 lb MetaMax bag product confirmed; exact '
                         'price sits behind the dealer login — $70 is '
                         'the typical $60-80/bag retail range '
                         'midpoint. Re-cite exact when accessible.',
        'is_estimate': True,
        'is_prior': True, 'provenance_id': 'src-4', 'notes': '',
    },
    {
        'name': 'sheffield-waterglass-1gal-2026-07-28',
        'source_ref': 'sheffield-pottery',
        'item_ref': 'sodium-silicate-solution',
        'price': 46.00, 'currency': 'USD',
        'amount': 5.2, 'amount_unit': 'kg',
        'observed_at': '2026-07-28T11:30:00',
        'citation_url': 'https://www.sheffield-pottery.com/products/'
                        'sodium-silicate-1-gallon-rmsodsilw35g',
        'citation_note': 'PRICE EXACT ($46.00/gallon, listed); MASS '
                         'inferred — 40% solution at SG~1.38 makes a '
                         'gallon ~5.2 kg AS-SOLUTION (water included; '
                         'dry-silicate basis would cost more per kg).',
        'is_estimate': True,
        'is_prior': True, 'provenance_id': 'src-4', 'notes': '',
    },
    {
        'name': 'essentialdepot-lye-16lb-2026-07-28',
        'source_ref': 'essential-depot',
        'item_ref': 'sodium-hydroxide-lye',
        'price': 69.97, 'currency': 'USD',
        'amount': 16.0, 'amount_unit': 'lb',
        'observed_at': '2026-07-28T11:32:00',
        'citation_url': 'https://www.essentialdepot.com/category/'
                        'sodium-hydroxide.html',
        'citation_note': 'Food-grade NaOH micro-beads, 8x2 lb '
                         'bottles = 16 lb at $69.97 (listed bulk '
                         'pack).',
        'is_estimate': False,
        'is_prior': True, 'provenance_id': 'src-4', 'notes': '',
    },
    {
        'name': 'homedepot-playsand-50lb-2026-07-28',
        'source_ref': 'home-depot',
        'item_ref': 'silica-sand',
        'price': 7.39, 'currency': 'USD',
        'amount': 50.0, 'amount_unit': 'lb',
        'observed_at': '2026-07-28T11:36:00',
        'citation_url': 'https://www.homedepot.com/p/Quikrete-50-lb-'
                        'Quikrete-Premium-Play-Sand-111351/206363630',
        'citation_note': 'Quikrete Premium Play Sand 50 lb, listed '
                         'price (local store prices may vary).',
        'is_estimate': False,
        'is_prior': True, 'provenance_id': 'src-4', 'notes': '',
    },
])

SEED_PRODUCT_REQUIREMENTS = [
    {
        'name': 'natural-print-wax-blend-requirements',
        'display_name': 'Natural 3D-printable wax — full feedstock '
                        'space',
        'product_item_ref': 'natural-print-wax-blend',
        'roles_json': json.dumps([
            {'role': 'base-wax',
             'purpose': 'bulk body of the blend; melt behavior',
             'min_fraction': 0.60, 'max_fraction': 0.85,
             'candidates': ['soy-wax', 'rice-bran-wax',
                            'candelilla-wax']},
            {'role': 'toughener',
             'purpose': 'flexibility/toughness so printed molds '
                        'survive handling + demolding',
             'min_fraction': 0.10, 'max_fraction': 0.30,
             'candidates': ['beeswax']},
            {'role': 'hardener',
             'purpose': 'raises stiffness + melting point for '
                        'dimensional stability during geopolymer '
                        'cure',
             'min_fraction': 0.05, 'max_fraction': 0.15,
             'candidates': ['carnauba-wax', 'stearic-acid',
                            'candelilla-wax']},
        ]),
        'substitutes_json': json.dumps([
            {'item_ref': 'machinable-wax',
             'caveats': [
                 'contains plastics — paraffin + polyethylene blend',
                 'emits fumes when overheated; ventilation required '
                 '(non-user-friendly under some conditions)',
                 'not eco-friendly (petrochemical feedstock)',
             ],
             'notes': 'Drop-in commercial 3D-printing wax '
                      '(MachinableWax.com Print2Cast family) — the '
                      'benchmark substitute for cost comparison.'},
        ]),
        'is_prior': True,
        'provenance_id': 'src-2',
        'notes': 'The COMPLETE candidate space, cited or not — '
                 'uncited candidates (rice-bran-wax, candelilla-wax, '
                 'stearic-acid) surface as research gaps in '
                 'coverage, driving the next price hunts. Fractions '
                 'are v1 engineering priors; waxprint '
                 'WaxFeedstockDefinition carries the material '
                 'properties side.',
    },
    {
        'name': 'geopolymer-mix-requirements',
        'display_name': 'DIY geopolymer castable — full feedstock '
                        'space',
        'product_item_ref': 'geopolymer-mix',
        'roles_json': json.dumps([
            {'role': 'precursor',
             'purpose': 'aluminosilicate that geopolymerizes '
                        '(the reactive backbone)',
             'min_fraction': 0.30, 'max_fraction': 0.50,
             'candidates': ['metakaolin', 'fly-ash-class-f',
                            'ggbfs-slag']},
            {'role': 'silicate-activator',
             'purpose': 'waterglass — dissolves/polycondenses the '
                        'precursor (mass as 40% SOLUTION, v1 '
                        'simplification)',
             'min_fraction': 0.10, 'max_fraction': 0.22,
             'candidates': ['sodium-silicate-solution']},
            {'role': 'alkali-activator',
             'purpose': 'raises pH for dissolution — CAUSTIC, the '
                        'user-friendliness cost of the DIY route',
             'min_fraction': 0.01, 'max_fraction': 0.06,
             'candidates': ['sodium-hydroxide-lye']},
            {'role': 'aggregate',
             'purpose': 'filler for castable strength + volume',
             'min_fraction': 0.30, 'max_fraction': 0.55,
             'candidates': ['silica-sand']},
        ]),
        'substitutes_json': json.dumps([
            {'item_ref': 'geopolymer-kit',
             'caveats': [
                 'closed-source proprietary formula',
                 'shipping on heavy material not in the cited price',
                 'cuts the OTHER way too: the kit is hydroxide-free '
                 '— friendlier chemistry than our DIY NaOH route '
                 '(caustic, PPE required)',
             ],
             'notes': 'Geopolymer International ready castable — '
                      'the buy-it option for pots/vases/furniture.'},
        ]),
        'is_prior': True,
        'provenance_id': 'src-4',
        'notes': 'Fractions are dry-mass engineering priors from the '
                 'suite geopolymer work; silicate counted '
                 'as-solution (water incl.) — dry-basis costing and '
                 'mix-water are v2 refinements. fly-ash/slag are '
                 'UNCITED gaps (not retail-purchasable easily — '
                 'industrial byproduct channels, often cheap-to-'
                 'free locally: worth the hunt).',
    },
]

SEED_PRODUCT_FORMULAS = [
    {
        'name': 'natural-print-wax-v0',
        'display_name': 'Natural print wax v0 (70/20/10)',
        'product_item_ref': 'natural-print-wax-blend',
        'components_json': json.dumps([
            {'item_ref': 'soy-wax', 'role': 'base-wax',
             'fraction': 0.70},
            {'item_ref': 'beeswax', 'role': 'toughener',
             'fraction': 0.20},
            {'item_ref': 'carnauba-wax', 'role': 'hardener',
             'fraction': 0.10},
        ]),
        'status': 'candidate',
        'is_prior': True,
        'provenance_id': 'src-2',
        'notes': 'First engineering guess — exists so cost scoring '
                 'has a baseline to beat; NOT print-validated.',
    },
    {
        'name': 'geopolymer-castable-v0',
        'display_name': 'DIY geopolymer castable v0 (40/16/3/41)',
        'product_item_ref': 'geopolymer-mix',
        'components_json': json.dumps([
            {'item_ref': 'metakaolin', 'role': 'precursor',
             'fraction': 0.40},
            {'item_ref': 'sodium-silicate-solution',
             'role': 'silicate-activator', 'fraction': 0.16},
            {'item_ref': 'sodium-hydroxide-lye',
             'role': 'alkali-activator', 'fraction': 0.03},
            {'item_ref': 'silica-sand', 'role': 'aggregate',
             'fraction': 0.41},
        ]),
        'status': 'candidate',
        'is_prior': True,
        'provenance_id': 'src-4',
        'notes': 'Metakaolin-waterglass castable engineering guess — '
                 'NOT cure-validated; exists so the buy-vs-make '
                 'comparison against the GPI kit has a DIY cost.',
    },
]

SEED_SOURCE_POLICIES = [
    {
        'name': 'polari-preference-ladder-v1',
        'display_name': 'Polari source preference ladder',
        'rules_json': json.dumps([
            {'rank': 1, 'label': 'polari open-source local',
             'require': {'is_polari': True, 'is_open_source': True,
                         'is_local': True}},
            {'rank': 2, 'label': 'polari open-source (non-local)',
             'require': {'is_polari': True,
                         'is_open_source': True}},
            {'rank': 3, 'label': 'open-source non-polari '
                                 '(eco-friendly)',
             'require': {'is_open_source': True,
                         'is_eco_friendly': True}},
            {'rank': 4, 'label': 'local closed-source',
             'require': {'is_local': True}},
            {'rank': 5, 'label': 'general commercial closed-source',
             'require': {'is_commercial': True}},
        ]),
        'default_rank': 6,
        'is_active': True,
        'is_prior': True, 'provenance_id': 'src-1',
        'notes': "Dustin's ordering 2026-07-28. First-match-wins "
                 'over the overlap-capable flags; edit the rules, '
                 'not code. Rank 3 requires eco-friendliness by '
                 'design — open-source alone does not outrank local.',
    },
]
