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
