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
        'supplies_json': json.dumps(['carnauba-wax',
                                     'rice-bran-wax']),
        'demands_json': '[]',
        'business_model_ref': '',
        'locality_note': '',
        'is_prior': True, 'provenance_id': 'src-1',
        'notes': 'Second commercial carnauba source — exists so the '
                 'price-compare has a real spread to show. Also the '
                 'rice-bran-wax channel (src-8).',
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
        'name': 'clay-art-center',
        'display_name': 'Clay Art Center (clayartcenter.net)',
        'supplier_name': 'Clay Art Center',
        'url': 'https://clayartcenter.net/',
        'is_open_source': False, 'is_commercial': True,
        'is_local': False, 'is_polari': False,
        'is_eco_friendly': False,
        'availability': 'available',
        'supplies_json': json.dumps(['metakaolin']),
        'demands_json': '[]',
        'business_model_ref': '',
        'locality_note': 'Tacoma WA showroom (weigh-outs in store) '
                         '+ ships',
        'is_prior': True, 'provenance_id': 'src-4',
        'notes': 'Pottery-supply metakaolin from 1 lb weigh-outs to '
                 '50 lb dry bags with volume tiers (10-30% off by '
                 'bag count) — the second, EXACTLY-priced metakaolin '
                 'source.',
    },
    {
        'name': 'municipal-water-utility',
        'display_name': 'Municipal water utility (tap)',
        'supplier_name': '(your local utility)',
        'url': 'https://capitalregionwater.com/customer-support/'
               'water-sewer-rates/',
        'is_open_source': False, 'is_commercial': True,
        'is_local': True, 'is_polari': False,
        'is_eco_friendly': True,
        'availability': 'available',
        'supplies_json': json.dumps(['tap-water']),
        'demands_json': '[]',
        'business_model_ref': '',
        'locality_note': 'by definition local — rank 4 on the '
                         'ladder (local closed-source)',
        'is_prior': True, 'provenance_id': 'src-5',
        'notes': 'Process water for making intermediaries '
                 '(waterglass digestion, geopolymer mix water). '
                 'Rates vary by utility; the citation uses one '
                 'published 2026 tariff.',
    },
    {
        'name': 'milliard-amazon',
        'display_name': 'Milliard via Amazon (citric acid)',
        'supplier_name': 'Milliard',
        'url': 'https://www.amazon.com/Milliard-Citric-Acid-'
               '10-Pound/dp/B00GNBHPAS',
        'is_open_source': False, 'is_commercial': True,
        'is_local': False, 'is_polari': False,
        'is_eco_friendly': False,
        'availability': 'available',
        'supplies_json': json.dumps(['citric-acid']),
        'demands_json': '[]',
        'business_model_ref': '',
        'locality_note': '',
        'is_prior': True, 'provenance_id': 'src-6',
        'notes': 'Food-grade citric acid by the 10 lb bag — the '
                 'sol-gel community route acid catalyst (the '
                 'citrus-juice route made shelf-stable).',
    },
    {
        'name': 'alpha-chemicals-walmart',
        'display_name': 'Alpha Chemicals via Walmart (magnetite)',
        'supplier_name': 'Alpha Chemicals',
        'url': 'https://www.walmart.com/ip/Black-Iron-Oxide-'
               'Fe3O4-Natural-5-Pounds/687367701',
        'is_open_source': False, 'is_commercial': True,
        'is_local': False, 'is_polari': False,
        'is_eco_friendly': False,
        'availability': 'available',
        'supplies_json': json.dumps(['magnetite-powder',
                                     'ferrous-sulfate']),
        'demands_json': '[]',
        'business_model_ref': '',
        'locality_note': '',
        'is_prior': True, 'provenance_id': 'src-6',
        'notes': 'Natural Fe3O4 pigment powder — the buy-side of '
                 'the ferrite feedstock question.',
    },
    {
        'name': 'cheap-tubes',
        'display_name': 'Cheap Tubes (cheaptubes.com)',
        'supplier_name': 'Cheap Tubes Inc',
        'url': 'https://www.cheaptubes.com/',
        'is_open_source': False, 'is_commercial': True,
        'is_local': False, 'is_polari': False,
        'is_eco_friendly': False,
        'availability': 'available',
        'supplies_json': json.dumps(['mwcnt-powder', 'swcnt-powder',
                                     'cnt-water-dispersion']),
        'demands_json': '[]',
        'business_model_ref': '',
        'locality_note': '',
        'is_prior': True, 'provenance_id': 'src-6',
        'notes': 'CNT vendor across grades — industrial MWCNT '
                 'through electronic SWCNT; the varying-CNT price '
                 'ladder lives in the citations.',
    },
    {
        'name': 'polari-cnt-lab',
        'display_name': 'Polari CNT synthesis (EXPLICITLY far off)',
        'supplier_name': 'Polari (self)',
        'url': '',
        'is_open_source': True, 'is_commercial': False,
        'is_local': True, 'is_polari': True,
        'is_eco_friendly': False,
        'availability': 'potential',
        'supplies_json': json.dumps(['mwcnt-powder', 'swcnt-powder']),
        'demands_json': '[]',
        'business_model_ref': '',
        'locality_note': '',
        'is_prior': True, 'provenance_id': 'src-6',
        'notes': 'ASSUMPTION ON RECORD (Dustin 2026-07-28): making '
                 'CNTs from scratch is FAR OFF — CVD synthesis is '
                 'not planned near-term, so NO make-formula is '
                 'seeded on purpose and CNT powders stay buy-only. '
                 'The techtree CNT-builder work models structure, '
                 'not production. DISPERSIONS of bought powder are '
                 'makeable today.',
    },
    {
        'name': 'soapgoods',
        'display_name': 'Soapgoods (soapgoods.com)',
        'supplier_name': 'Soapgoods',
        'url': 'https://www.soapgoods.com/',
        'is_open_source': False, 'is_commercial': True,
        'is_local': False, 'is_polari': False,
        'is_eco_friendly': False,
        'availability': 'available',
        'supplies_json': json.dumps(['sls-surfactant']),
        'demands_json': '[]', 'business_model_ref': '',
        'locality_note': '',
        'is_prior': True, 'provenance_id': 'src-7',
        'notes': 'Soap-making surfactants — the CNT-dispersion '
                 'stabilizer channel.',
    },
    {
        'name': 'homebrewing-org',
        'display_name': 'Adventures in Homebrewing (rice hulls)',
        'supplier_name': 'Adventures in Homebrewing',
        'url': 'https://homebrewing.org/products/'
               'rice-hulls-50-lb-bag',
        'is_open_source': False, 'is_commercial': True,
        'is_local': False, 'is_polari': False,
        'is_eco_friendly': True,
        'availability': 'available',
        'supplies_json': json.dumps(['rice-hulls']),
        'demands_json': '[]', 'business_model_ref': '',
        'locality_note': 'homebrew shops stock locally too',
        'is_prior': True, 'provenance_id': 'src-7',
        'notes': 'Agricultural byproduct by the 50 lb bag — the '
                 'rice-husk-ash feedstock (brewing/garden channel; '
                 'rice MILLS often give hulls near-free).',
    },
    {
        'name': 'clay-king',
        'display_name': 'Clay King (EPK kaolin)',
        'supplier_name': 'Clay King',
        'url': 'https://www.clay-king.com/product/'
               'edgar-plastic-kaolin-epk/',
        'is_open_source': False, 'is_commercial': True,
        'is_local': False, 'is_polari': False,
        'is_eco_friendly': False,
        'availability': 'available',
        'supplies_json': json.dumps(['kaolin-raw']),
        'demands_json': '[]', 'business_model_ref': '',
        'locality_note': '',
        'is_prior': True, 'provenance_id': 'src-7',
        'notes': 'Raw EPK kaolin — the metakaolin FEEDSTOCK '
                 '(calcine ~700C to dehydroxylate).',
    },
    {
        'name': 'wholesale-supplies-plus',
        'display_name': 'Wholesale Supplies Plus (stearic acid)',
        'supplier_name': 'Wholesale Supplies Plus',
        'url': 'https://www.wholesalesuppliesplus.com/products/'
               'stearic-acid',
        'is_open_source': False, 'is_commercial': True,
        'is_local': False, 'is_polari': False,
        'is_eco_friendly': False,
        'availability': 'available',
        'supplies_json': json.dumps(['stearic-acid']),
        'demands_json': '[]', 'business_model_ref': '',
        'locality_note': '',
        'is_prior': True, 'provenance_id': 'src-7',
        'notes': 'Vegetable stearic acid — wax hardener candidate '
                 '(cheaper than carnauba).',
    },
    {
        'name': 'candelilla-amazon-listing',
        'display_name': 'Candelilla wax (Amazon marketplace)',
        'supplier_name': '(marketplace listing)',
        'url': 'https://www.amazon.com/Candelilla-Natural-Flakes-'
               'Alternative-Beeswax/dp/B07LHKT1F9',
        'is_open_source': False, 'is_commercial': True,
        'is_local': False, 'is_polari': False,
        'is_eco_friendly': False,
        'availability': 'available',
        'supplies_json': json.dumps(['candelilla-wax']),
        'demands_json': '[]', 'business_model_ref': '',
        'locality_note': '',
        'is_prior': True, 'provenance_id': 'src-7',
        'notes': 'Vegan beeswax alternative — base/hardener '
                 'candidate in the wax blend.',
    },
    {
        'name': 'in-the-swim',
        'display_name': 'In The Swim (soda ash)',
        'supplier_name': 'In The Swim',
        'url': 'https://www.intheswim.com/p/ph-increaser-5-lbs./'
               '400249.html',
        'is_open_source': False, 'is_commercial': True,
        'is_local': False, 'is_polari': False,
        'is_eco_friendly': False,
        'availability': 'available',
        'supplies_json': json.dumps(['soda-ash']),
        'demands_json': '[]', 'business_model_ref': '',
        'locality_note': 'pool stores stock locally',
        'is_prior': True, 'provenance_id': 'src-7',
        'notes': '100% sodium carbonate via the pool channel — the '
                 'alkali for the FUSED (furnace) waterglass route; '
                 'cited but NOT wired into the digestion recipe '
                 '(different process, needs a melt furnace).',
    },
    {
        'name': 'science-company',
        'display_name': 'The Science Company (ferric chloride)',
        'supplier_name': 'The Science Company',
        'url': 'https://www.sciencecompany.com/',
        'is_open_source': False, 'is_commercial': True,
        'is_local': False, 'is_polari': False,
        'is_eco_friendly': False,
        'availability': 'available',
        'supplies_json': json.dumps(['ferric-chloride']),
        'demands_json': '[]', 'business_model_ref': '',
        'locality_note': '',
        'is_prior': True, 'provenance_id': 'src-8',
        'notes': 'Lab/hobby chemicals — ferric chloride etchant '
                 '(the PCB channel; also the Fe3+ salt for '
                 'magnetite coprecipitation).',
    },
    {
        'name': 'ebay-teos-listing',
        'display_name': 'TEOS small-vial listing (eBay)',
        'supplier_name': '(marketplace listing)',
        'url': 'https://www.ebay.com/itm/204582215772',
        'is_open_source': False, 'is_commercial': True,
        'is_local': False, 'is_polari': False,
        'is_eco_friendly': False,
        'availability': 'available',
        'supplies_json': json.dumps(['teos']),
        'demands_json': '[]', 'business_model_ref': '',
        'locality_note': '',
        'is_prior': True, 'provenance_id': 'src-8',
        'notes': 'The lab-alkoxide sol-gel precursor; lab-house '
                 'bulk prices are login-gated, so the visible '
                 'anchor is a small vial.',
    },
    {
        'name': 'countertop-admix-ebay',
        'display_name': 'Countertop admixture channel (eBay)',
        'supplier_name': '(concrete-countertop supply listings)',
        'url': 'https://www.ebay.com/itm/225760472235',
        'is_open_source': False, 'is_commercial': True,
        'is_local': False, 'is_polari': False,
        'is_eco_friendly': True,
        'availability': 'available',
        'supplies_json': json.dumps(['fly-ash-class-f',
                                     'ggbfs-slag']),
        'demands_json': '[]', 'business_model_ref': '',
        'locality_note': '',
        'is_prior': True, 'provenance_id': 'src-8',
        'notes': 'Small-bag fly ash + GGBFS via the concrete-'
                 'countertop hobby channel. BOTH are industrial '
                 'byproducts (eco flag) whose BULK price is ~100x '
                 'lower — the real play is a local ready-mix '
                 'plant / utility channel.',
    },
    {
        'name': 'walmart-grocery',
        'display_name': 'Walmart grocery (vinegar)',
        'supplier_name': 'Walmart (Great Value)',
        'url': 'https://www.walmart.com/ip/Great-Value-Distilled-'
               'White-Vinegar-1-gal/10450998',
        'is_open_source': False, 'is_commercial': True,
        'is_local': False, 'is_polari': False,
        'is_eco_friendly': False,
        'availability': 'available',
        'supplies_json': json.dumps(['acetic-vinegar']),
        'demands_json': '[]', 'business_model_ref': '',
        'locality_note': 'grocery — stocked everywhere',
        'is_prior': True, 'provenance_id': 'src-8',
        'notes': 'Distilled white vinegar (5% acetic) — the '
                 'kitchen-grade sol-gel acid catalyst.',
    },
    {
        'name': 'dry-and-dry-ebay',
        'display_name': 'Dry & Dry silica gel (eBay)',
        'supplier_name': 'Dry & Dry',
        'url': 'https://www.ebay.com/itm/272443787355',
        'is_open_source': False, 'is_commercial': True,
        'is_local': False, 'is_polari': False,
        'is_eco_friendly': False,
        'availability': 'available',
        'supplies_json': json.dumps(['silica-gel-desiccant']),
        'demands_json': '[]', 'business_model_ref': '',
        'locality_note': '',
        'is_prior': True, 'provenance_id': 'src-8',
        'notes': 'Commodity desiccant beads — the substitute '
                 'benchmark for DRYING uses of silica gel (never a '
                 'sol-gel processing substitute).',
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

SEED_PRICE_CITATIONS.extend([
    {
        'name': 'clayart-metakaolin-50lb-2026-07-28',
        'source_ref': 'clay-art-center',
        'item_ref': 'metakaolin',
        'price': 66.00, 'currency': 'USD',
        'amount': 50.0, 'amount_unit': 'lb',
        'observed_at': '2026-07-28T19:23:00',
        'citation_url': 'https://clayartcenter.net/product/'
                        'rm450-kaolin-meta/',
        'citation_note': 'EXACT listed price, 50 lbs Dry selector = '
                         '$66.00 (single bag; 1 lb weigh-out = '
                         '$5.00). Site bot-blocks automated fetch — '
                         'price captured from Dustin\'s in-store-'
                         'browser screenshots 2026-07-28.',
        'is_estimate': False,
        'is_prior': True, 'provenance_id': 'src-4', 'notes': '',
    },
    {
        'name': 'clayart-metakaolin-40bag-tier-2026-07-28',
        'source_ref': 'clay-art-center',
        'item_ref': 'metakaolin',
        'price': 1848.00, 'currency': 'USD',
        'amount': 2000.0, 'amount_unit': 'lb',
        'observed_at': '2026-07-28T19:23:00',
        'citation_url': 'https://clayartcenter.net/product/'
                        'rm450-kaolin-meta/',
        'citation_note': 'Volume tier: 40-999 bags at 30% off = '
                         '$46.20/50 lb bag; amount is the 40-bag '
                         'MINIMUM commitment (2000 lb) so the pack '
                         'size shows what the price demands. Tiers: '
                         '2-9 -10% $59.40, 10-19 -20% $52.80, 20-39 '
                         '-25% $49.50. Same screenshot capture.',
        'is_estimate': False,
        'is_prior': True, 'provenance_id': 'src-4', 'notes': '',
    },
])

SEED_PRICE_CITATIONS.append(
    {
        'name': 'capital-region-water-2026-tariff',
        'source_ref': 'municipal-water-utility',
        'item_ref': 'tap-water',
        'price': 11.63, 'currency': 'USD',
        'amount': 3785.4, 'amount_unit': 'kg',
        'observed_at': '2026-07-28T12:05:00',
        'citation_url': 'https://capitalregionwater.com/'
                        'customer-support/water-sewer-rates/',
        'citation_note': 'Published tariff effective 2026-01-01: '
                         '$11.63 per 1000 gallons (= 3785.4 kg). '
                         'EXACT for that utility; rates vary '
                         'widely by locality — re-cite your own '
                         'utility for real runs.',
        'is_estimate': False,
        'is_prior': True, 'provenance_id': 'src-5', 'notes': '',
    })

SEED_PRICE_CITATIONS.extend([
    {
        'name': 'milliard-citric-10lb-2026-07-28',
        'source_ref': 'milliard-amazon',
        'item_ref': 'citric-acid',
        'price': 25.99, 'currency': 'USD',
        'amount': 10.0, 'amount_unit': 'lb',
        'observed_at': '2026-07-28T12:40:00',
        'citation_url': 'https://www.amazon.com/Milliard-Citric-'
                        'Acid-10-Pound/dp/B00GNBHPAS',
        'citation_note': 'Typical listing price for the 10 lb bag — '
                         'Amazon prices fluctuate; flagged estimate '
                         'until pinned on a dated screenshot.',
        'is_estimate': True,
        'is_prior': True, 'provenance_id': 'src-6', 'notes': '',
    },
    {
        'name': 'alpha-magnetite-5lb-2026-07-28',
        'source_ref': 'alpha-chemicals-walmart',
        'item_ref': 'magnetite-powder',
        'price': 21.99, 'currency': 'USD',
        'amount': 5.0, 'amount_unit': 'lb',
        'observed_at': '2026-07-28T12:42:00',
        'citation_url': 'https://www.walmart.com/ip/Black-Iron-'
                        'Oxide-Fe3O4-Natural-5-Pounds/687367701',
        'citation_note': 'Listed price, natural Fe3O4 5 lb, free '
                         'shipping.',
        'is_estimate': False,
        'is_prior': True, 'provenance_id': 'src-6', 'notes': '',
    },
    {
        'name': 'cheaptubes-mwcnt-1kg-2026-07-28',
        'source_ref': 'cheap-tubes',
        'item_ref': 'mwcnt-powder',
        'price': 375.00, 'currency': 'USD',
        'amount': 1.0, 'amount_unit': 'kg',
        'observed_at': '2026-07-28T12:45:00',
        'citation_url': 'https://www.cheaptubes.com/product/'
                        'industrial-grade-multi-walled-carbon-'
                        'nanotubes-10-30nm/',
        'citation_note': 'Industrial-grade MWCNT 10-30nm listed '
                         '$375-$390/kg; low end cited. Ton-scale '
                         'pricing exists on request.',
        'is_estimate': True,
        'is_prior': True, 'provenance_id': 'src-6', 'notes': '',
    },
    {
        'name': 'swcnt-electronic-grade-2026-07-28',
        'source_ref': 'cheap-tubes',
        'item_ref': 'swcnt-powder',
        'price': 500.00, 'currency': 'USD',
        'amount': 0.001, 'amount_unit': 'kg',
        'observed_at': '2026-07-28T12:46:00',
        'citation_url': 'https://www.cheaptubes.com/'
                        'product-category/single-walled-carbon-'
                        'nanotubes/',
        'citation_note': 'Electronic/semiconducting SWCNT reported '
                         '$500-1500 PER GRAM (low end cited = '
                         '$500k/kg); research-grade SWCNT runs far '
                         'lower but still ~10x MWCNT. The point on '
                         'record: SWCNT is ORDERS OF MAGNITUDE '
                         'above MWCNT — grade choice dominates '
                         'cost. Re-cite per exact grade when '
                         'selected.',
        'is_estimate': True,
        'is_prior': True, 'provenance_id': 'src-6', 'notes': '',
    },
    {
        'name': 'cnt-dispersion-market-2026-07-28',
        'source_ref': 'cheap-tubes',
        'item_ref': 'cnt-water-dispersion',
        'price': 185.00, 'currency': 'USD',
        'amount': 1.0, 'amount_unit': 'kg',
        'observed_at': '2026-07-28T12:47:00',
        'citation_url': 'https://www.indexbox.io/store/china-carbon-'
                        'nanotube-dispersions-market-analysis-'
                        'forecast-size-trends-and-insights/',
        'citation_note': 'Market-report range $120-250/kg for SWCNT '
                         'water dispersions; midpoint cited. Vendor '
                         'quotes (TUBALL etc.) are volume-'
                         'personalized — re-cite on quote.',
        'is_estimate': True,
        'is_prior': True, 'provenance_id': 'src-6', 'notes': '',
    },
])

SEED_PRICE_CITATIONS.extend([
    {
        'name': 'alpha-ferrous-sulfate-5lb-2026-07-28',
        'source_ref': 'alpha-chemicals-walmart',
        'item_ref': 'ferrous-sulfate',
        'price': 16.00, 'currency': 'USD',
        'amount': 5.0, 'amount_unit': 'lb',
        'observed_at': '2026-07-28T13:10:00',
        'citation_url': 'https://www.walmart.com/ip/Ferrous-Sulfate-'
                        'Heptahydrate-FeSO47H2O-20-Iron-Very-Soluble-'
                        '5-Pounds/2011562598',
        'citation_note': 'Product page bot-gated at observation; '
                         '$16 is the typical $14-18 listing range '
                         'midpoint for the Alpha Chemicals 5 lb. '
                         'Re-cite exact (screenshot works).',
        'is_estimate': True,
        'is_prior': True, 'provenance_id': 'src-7', 'notes': '',
    },
    {
        'name': 'soapgoods-sls-1lb-2026-07-28',
        'source_ref': 'soapgoods',
        'item_ref': 'sls-surfactant',
        'price': 15.84, 'currency': 'USD',
        'amount': 1.0, 'amount_unit': 'lb',
        'observed_at': '2026-07-28T13:12:00',
        'citation_url': 'https://www.soapgoods.com/sodium-lauryl-'
                        'sulfate-sls-powder-p-1841.html',
        'citation_note': 'Listed EXACT $15.84/lb — page showed OUT '
                         'OF STOCK at observation; availability '
                         'caveat, price real.',
        'is_estimate': False,
        'is_prior': True, 'provenance_id': 'src-7', 'notes': '',
    },
    {
        'name': 'homebrewing-rice-hulls-50lb-2026-07-28',
        'source_ref': 'homebrewing-org',
        'item_ref': 'rice-hulls',
        'price': 30.00, 'currency': 'USD',
        'amount': 50.0, 'amount_unit': 'lb',
        'observed_at': '2026-07-28T13:14:00',
        'citation_url': 'https://homebrewing.org/products/'
                        'rice-hulls-50-lb-bag',
        'citation_note': 'Typical homebrew-channel price for the '
                         '50 lb bag ($27-35 range midpointish); '
                         'page price not shown in search — re-cite '
                         'exact. Rice mills often give hulls '
                         'near-free locally.',
        'is_estimate': True,
        'is_prior': True, 'provenance_id': 'src-7', 'notes': '',
    },
    {
        'name': 'clayking-epk-50lb-2026-07-28',
        'source_ref': 'clay-king',
        'item_ref': 'kaolin-raw',
        'price': 21.50, 'currency': 'USD',
        'amount': 50.0, 'amount_unit': 'lb',
        'observed_at': '2026-07-28T13:16:00',
        'citation_url': 'https://www.clay-king.com/product/'
                        'edgar-plastic-kaolin-epk/',
        'citation_note': 'Listed range $4.90-$21.50 by size; top '
                         'mapped to the 50 lb bag by inference '
                         '(other suppliers quote ~$0.40/lb bulk).',
        'is_estimate': True,
        'is_prior': True, 'provenance_id': 'src-7', 'notes': '',
    },
    {
        'name': 'wsp-stearic-5lb-2026-07-28',
        'source_ref': 'wholesale-supplies-plus',
        'item_ref': 'stearic-acid',
        'price': 40.19, 'currency': 'USD',
        'amount': 5.0, 'amount_unit': 'lb',
        'observed_at': '2026-07-28T13:18:00',
        'citation_url': 'https://www.wholesalesuppliesplus.com/'
                        'products/stearic-acid',
        'citation_note': 'Listed $40.19 for 5 lb ($8.04/lb) — '
                         'search-surfaced listing price.',
        'is_estimate': False,
        'is_prior': True, 'provenance_id': 'src-7', 'notes': '',
    },
    {
        'name': 'amazon-candelilla-5lb-2026-07-28',
        'source_ref': 'candelilla-amazon-listing',
        'item_ref': 'candelilla-wax',
        'price': 48.00, 'currency': 'USD',
        'amount': 5.0, 'amount_unit': 'lb',
        'observed_at': '2026-07-28T13:20:00',
        'citation_url': 'https://www.amazon.com/Candelilla-Natural-'
                        'Flakes-Alternative-Beeswax/dp/B07LHKT1F9',
        'citation_note': 'Search-surfaced 5 lb listing ~$48; '
                         'marketplace prices swing wildly ($14-18/lb '
                         'quoted elsewhere, one $152.99/5lb '
                         'outlier) — flagged until pinned.',
        'is_estimate': True,
        'is_prior': True, 'provenance_id': 'src-7', 'notes': '',
    },
    {
        'name': 'intheswim-soda-ash-5lb-2026-07-28',
        'source_ref': 'in-the-swim',
        'item_ref': 'soda-ash',
        'price': 14.00, 'currency': 'USD',
        'amount': 5.0, 'amount_unit': 'lb',
        'observed_at': '2026-07-28T13:22:00',
        'citation_url': 'https://www.intheswim.com/p/'
                        'ph-increaser-5-lbs./400249.html',
        'citation_note': 'Typical listing for the 5 lb pH-increaser '
                         '(100% soda ash); exact not search-visible '
                         '— re-cite. Feeds the FUSED waterglass '
                         'route when that recipe lands.',
        'is_estimate': True,
        'is_prior': True, 'provenance_id': 'src-7', 'notes': '',
    },
])

SEED_PRICE_CITATIONS.extend([
    {
        'name': 'oilscenter-ricebran-5lb-2026-07-28',
        'source_ref': 'oils-center',
        'item_ref': 'rice-bran-wax',
        'price': 65.99, 'currency': 'USD',
        'amount': 5.0, 'amount_unit': 'lb',
        'observed_at': '2026-07-28T13:55:00',
        'citation_url': 'https://oilscenter.com/rice-bran-wax-'
                        'organic-flakes-vegan-beads-vegetable-'
                        'pastilles-100-pure-5-lb',
        'citation_note': 'Listed EXACT $65.99/5 lb — closes the '
                         'LAST uncited wax-blend candidate.',
        'is_estimate': False,
        'is_prior': True, 'provenance_id': 'src-8', 'notes': '',
    },
    {
        'name': 'sciencecompany-fecl3-500ml-2026-07-28',
        'source_ref': 'science-company',
        'item_ref': 'ferric-chloride',
        'price': 21.95, 'currency': 'USD',
        'amount': 0.70, 'amount_unit': 'kg',
        'observed_at': '2026-07-28T13:57:00',
        'citation_url': 'https://www.sciencecompany.com/Ferric-'
                        'Chloride-Etchant-Solution-40-500mL-P17177',
        'citation_note': 'PRICE EXACT ($21.95, 500 mL of 40% '
                         'solution); MASS inferred at SG~1.40 -> '
                         '~0.70 kg as-solution.',
        'is_estimate': True,
        'is_prior': True, 'provenance_id': 'src-8', 'notes': '',
    },
    {
        'name': 'ebay-teos-20ml-2026-07-28',
        'source_ref': 'ebay-teos-listing',
        'item_ref': 'teos',
        'price': 5.80, 'currency': 'USD',
        'amount': 0.0187, 'amount_unit': 'kg',
        'observed_at': '2026-07-28T13:58:00',
        'citation_url': 'https://www.ebay.com/itm/204582215772',
        'citation_note': 'Listed small-vial price (20 mL x SG 0.933 '
                         '= ~18.7 g) -> ~310/kg at THIS scale; '
                         'lab-house bulk is login-gated and lower, '
                         'but TEOS stays 1-2 ORDERS above '
                         'waterglass as a silica source either way '
                         '— which is exactly why the sg-community '
                         'alkoxide-free route exists.',
        'is_estimate': True,
        'is_prior': True, 'provenance_id': 'src-8', 'notes': '',
    },
    {
        'name': 'ebay-flyash-7lb-2026-07-28',
        'source_ref': 'countertop-admix-ebay',
        'item_ref': 'fly-ash-class-f',
        'price': 17.00, 'currency': 'USD',
        'amount': 7.0, 'amount_unit': 'lb',
        'observed_at': '2026-07-28T14:00:00',
        'citation_url': 'https://www.ebay.com/itm/225760472235',
        'citation_note': 'Countertop-channel 7 lb bag, typical '
                         '$12-22 (midpoint cited, listing price not '
                         'search-visible). BULK truth: $30-80/'
                         'METRIC TON (~0.03-0.08/kg) — a ~100x gap; '
                         'hunt a local ready-mix/utility channel.',
        'is_estimate': True,
        'is_prior': True, 'provenance_id': 'src-8', 'notes': '',
    },
    {
        'name': 'ebay-ggbfs-7lb-2026-07-28',
        'source_ref': 'countertop-admix-ebay',
        'item_ref': 'ggbfs-slag',
        'price': 17.00, 'currency': 'USD',
        'amount': 7.0, 'amount_unit': 'lb',
        'observed_at': '2026-07-28T14:01:00',
        'citation_url': 'https://www.ebay.com/itm/225893034174',
        'citation_note': 'Same countertop channel, same midpoint '
                         'estimate. BULK: ~$54/MT USA (2026-03) = '
                         '~0.054/kg — the local-channel hunt '
                         'applies doubly.',
        'is_estimate': True,
        'is_prior': True, 'provenance_id': 'src-8', 'notes': '',
    },
    {
        'name': 'walmart-vinegar-1gal-2026-07-28',
        'source_ref': 'walmart-grocery',
        'item_ref': 'acetic-vinegar',
        'price': 3.97, 'currency': 'USD',
        'amount': 3.78, 'amount_unit': 'kg',
        'observed_at': '2026-07-28T14:02:00',
        'citation_url': 'https://www.walmart.com/ip/Great-Value-'
                        'Distilled-White-Vinegar-1-gal/10450998',
        'citation_note': 'Listed EXACT $3.97/gallon; mass = ~3.78 '
                         'kg AS 5% SOLUTION — per kg of ACETIC ACID '
                         'this is ~21/kg, the dilution is the '
                         'catch.',
        'is_estimate': False,
        'is_prior': True, 'provenance_id': 'src-8', 'notes': '',
    },
    {
        'name': 'dryndry-silicagel-10lb-2026-07-28',
        'source_ref': 'dry-and-dry-ebay',
        'item_ref': 'silica-gel-desiccant',
        'price': 35.00, 'currency': 'USD',
        'amount': 10.0, 'amount_unit': 'lb',
        'observed_at': '2026-07-28T14:03:00',
        'citation_url': 'https://www.ebay.com/itm/272443787355',
        'citation_note': 'Typical listing for the 10 lb bag '
                         '(~$30-40 range midpoint; exact not '
                         'search-visible).',
        'is_estimate': True,
        'is_prior': True, 'provenance_id': 'src-8', 'notes': '',
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
             'candidates': ['silica-sand',
                            'crushed-geopolymer-aggregate']},
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
        'notes': 'AGGREGATE LOOPBACK (mold-1): crushed retired '
                 'geopolymer MOLDS re-enter here as '
                 'crushed-geopolymer-aggregate — a coverage gap '
                 'until crush events are logged/cited, near-free '
                 'in practice. Fractions are dry-mass engineering '
                 'priors from the '
                 'suite geopolymer work; silicate counted '
                 'as-solution (water incl.) — dry-basis costing and '
                 'mix-water are v2 refinements. fly-ash/slag are '
                 'UNCITED gaps (not retail-purchasable easily — '
                 'industrial byproduct channels, often cheap-to-'
                 'free locally: worth the hunt).',
    },
    {
        'name': 'sodium-silicate-solution-requirements',
        'display_name': 'Waterglass (40% solution) — MAKEABLE '
                        'intermediary, routes as data',
        'product_item_ref': 'sodium-silicate-solution',
        'roles_json': json.dumps([
            {'role': 'silica-source',
             'purpose': 'amorphous/reactive SiO2 to dissolve '
                        '(modulus ~2.5 target)',
             'min_fraction': 0.24, 'max_fraction': 0.32,
             'candidates': ['silica-sand', 'rice-husk-ash',
                            'waste-glass-fines']},
            {'role': 'alkali',
             'purpose': 'NaOH to digest the silica — CAUSTIC, hot: '
                        'the safety cost of making it ourselves',
             'min_fraction': 0.12, 'max_fraction': 0.18,
             'candidates': ['sodium-hydroxide-lye']},
            {'role': 'water',
             'purpose': 'solution water (~40% solids product)',
             'min_fraction': 0.52, 'max_fraction': 0.62,
             'candidates': ['tap-water']},
        ]),
        'substitutes_json': '[]',
        'is_prior': True,
        'provenance_id': 'src-5',
        'notes': 'WATERGLASS IS AN INTERMEDIARY, NOT A NATURAL '
                 'MATERIAL (Dustin 2026-07-28) — critical to '
                 'geopolymer activation, sol-gel (sg-community '
                 'alkoxide-free route), pspp chemistry. Three '
                 'production routes as data: (1) hydrothermal '
                 'sand+NaOH digestion — needs sustained heat '
                 '(ENERGY EXCLUDED from v1 cost, loudly); (2) '
                 'rice-husk-ash + NaOH — the LOW-temperature '
                 'community route from the sol-gel tech-tree work, '
                 'RHA uncited gap (husks near-free at mills, ash '
                 'it yourself); (3) waste-glass fines + NaOH — '
                 'uncited gap, ties the recycling loop. Same '
                 'item_ref also has PURCHASE citations — the '
                 'cascaded costing compares make vs buy.',
    },
    {
        'name': 'silica-xerogel-requirements',
        'display_name': 'Silica xerogel (sol-gel) — community route '
                        'feedstock space',
        'product_item_ref': 'silica-xerogel',
        'roles_json': json.dumps([
            {'role': 'silicate-precursor',
             'purpose': 'silica source for the sol (community route '
                        'uses OUR waterglass; TEOS is the lab-'
                        'alkoxide alternative)',
             'min_fraction': 0.50, 'max_fraction': 0.65,
             'candidates': ['sodium-silicate-solution', 'teos',
                            'rice-husk-ash']},
            {'role': 'acid-catalyst',
             'purpose': 'drops pH to gel the silicate (citrus-juice '
                        'route made shelf-stable = citric acid)',
             'min_fraction': 0.05, 'max_fraction': 0.20,
             'candidates': ['citric-acid', 'acetic-vinegar']},
            {'role': 'water',
             'purpose': 'dilution water for workable sol',
             'min_fraction': 0.25, 'max_fraction': 0.40,
             'candidates': ['tap-water']},
        ]),
        'substitutes_json': json.dumps([
            {'item_ref': 'silica-gel-desiccant',
             'caveats': [
                 'desiccant grade — NOT a functional sol-gel '
                 'coating/monolith precursor',
                 'uncited — comparison pending a dated citation',
             ],
             'notes': 'Commodity silica gel exists cheap; it '
                      'substitutes only for drying uses, never for '
                      'sol-gel processing.'},
        ]),
        'is_prior': True,
        'provenance_id': 'src-6',
        'notes': 'The sg-community alkoxide-free route as COST data '
                 '(the sol-gel tech node carries the chemistry). '
                 'TEOS + vinegar + RHA = uncited gaps. Drying '
                 'ENERGY excluded v1; yield lives on the formula.',
    },
    {
        'name': 'magnetite-powder-requirements',
        'display_name': 'Magnetite/ferrite feedstock — '
                        'coprecipitation space',
        'product_item_ref': 'magnetite-powder',
        'roles_json': json.dumps([
            {'role': 'iron-salt',
             'purpose': 'dissolved Fe2+/Fe3+ for coprecipitation',
             'min_fraction': 0.55, 'max_fraction': 0.75,
             'candidates': ['ferrous-sulfate', 'ferric-chloride']},
            {'role': 'alkali',
             'purpose': 'precipitates Fe3O4 from the salt solution',
             'min_fraction': 0.10, 'max_fraction': 0.25,
             'candidates': ['sodium-hydroxide-lye']},
            {'role': 'water',
             'purpose': 'reaction solution',
             'min_fraction': 0.10, 'max_fraction': 0.30,
             'candidates': ['tap-water']},
        ]),
        'substitutes_json': '[]',
        'is_prior': True,
        'provenance_id': 'src-6',
        'notes': 'FERRITE v1 = magnetite powder (Fe3O4). The buy '
                 'side is cited ($21.99/5lb pigment powder); the '
                 'coprecipitation make-route exists as data but '
                 'now COSTS (ferrous sulfate cited src-7) — and '
                 'BUYING WINS ~2x for pigment-grade Fe3O4; '
                 'coprecipitation earns its keep only where nano/'
                 'monodisperse particles matter. ferric-chloride '
                 '(PCB-etchant channel) still uncited. Sintered MnZn/NiZn ferrite PARTS '
                 '(inductor cores) are a further processing step, '
                 'not this item.',
    },
    {
        'name': 'cnt-water-dispersion-requirements',
        'display_name': 'CNT water dispersion — makeable from '
                        'BOUGHT powder',
        'product_item_ref': 'cnt-water-dispersion',
        'roles_json': json.dumps([
            {'role': 'cnt',
             'purpose': 'the nanotubes (grade choice dominates '
                        'cost: MWCNT vs SWCNT is orders of '
                        'magnitude)',
             'min_fraction': 0.01, 'max_fraction': 0.04,
             'candidates': ['mwcnt-powder', 'swcnt-powder']},
            {'role': 'water',
             'purpose': 'dispersion medium',
             'min_fraction': 0.96, 'max_fraction': 0.99,
             'candidates': ['tap-water']},
            {'role': 'surfactant',
             'purpose': 'stabilizer so the dispersion does not '
                        'settle (optional in v1 recipes)',
             'min_fraction': 0.0, 'max_fraction': 0.02,
             'candidates': ['sls-surfactant']},
        ]),
        'substitutes_json': '[]',
        'is_prior': True,
        'provenance_id': 'src-6',
        'notes': 'CNT SYNTHESIS FROM SCRATCH IS FAR OFF (assumption '
                 'on record — polari-cnt-lab stays potential, no '
                 'powder make-formula). Dispersing BOUGHT powder is '
                 'near-term: sonication energy/equipment EXCLUDED '
                 'v1, and surfactant-free dispersions SETTLE — the '
                 'surfactant route (SDS et al.) is an uncited gap.',
    },
    {
        'name': 'metakaolin-requirements',
        'display_name': 'Metakaolin — makeable by calcining kaolin',
        'product_item_ref': 'metakaolin',
        'roles_json': json.dumps([
            {'role': 'kaolin',
             'purpose': 'raw kaolin, dehydroxylated at ~700C to the '
                        'reactive metakaolin phase',
             'min_fraction': 1.0, 'max_fraction': 1.0,
             'candidates': ['kaolin-raw']},
        ]),
        'substitutes_json': '[]',
        'is_prior': True,
        'provenance_id': 'src-7',
        'notes': 'THE metakaolin intermediary: buy calcined ($46-66/'
                 '50lb) or calcine raw EPK ($21.50/50lb) at ~700C — '
                 'kiln ENERGY EXCLUDED v1 (a pottery kiln does it; '
                 'the suite already models sintering schedules). '
                 'Yield ~0.86 (14% dehydroxylation water loss).',
    },
    {
        'name': 'rice-husk-ash-requirements',
        'display_name': 'Rice husk ash — burned from cited hulls',
        'product_item_ref': 'rice-husk-ash',
        'roles_json': json.dumps([
            {'role': 'hulls',
             'purpose': 'agricultural byproduct, controlled burn -> '
                        'amorphous silica ash (~90% SiO2)',
             'min_fraction': 1.0, 'max_fraction': 1.0,
             'candidates': ['rice-hulls']},
        ]),
        'substitutes_json': '[]',
        'is_prior': True,
        'provenance_id': 'src-7',
        'notes': 'The sg-community silica source becomes makeable: '
                 'controlled-burn hulls to amorphous ash (burn '
                 'conditions matter for reactivity — the sol-gel '
                 'tech node carries the chemistry; burn ENERGY '
                 'self-fueling in practice, excluded v1). RHA wins '
                 'on process TEMPERATURE, not on $/kg vs sand.',
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
    {
        'name': 'waterglass-hydrothermal-v0',
        'display_name': 'Waterglass via sand + NaOH digestion v0 '
                        '(28/15/57)',
        'product_item_ref': 'sodium-silicate-solution',
        'components_json': json.dumps([
            {'item_ref': 'silica-sand', 'role': 'silica-source',
             'fraction': 0.28},
            {'item_ref': 'sodium-hydroxide-lye', 'role': 'alkali',
             'fraction': 0.15},
            {'item_ref': 'tap-water', 'role': 'water',
             'fraction': 0.57},
        ]),
        'status': 'candidate',
        'is_prior': True,
        'provenance_id': 'src-5',
        'notes': 'Hydrothermal digestion recipe guess (~MR 2.5, 40% '
                 'solids) — NOT bench-validated; digestion ENERGY '
                 'EXCLUDED from v1 cost. Exists so the intermediary '
                 'make-vs-buy has a number.',
    },
    {
        'name': 'solgel-community-v0',
        'display_name': 'Silica xerogel via waterglass + citric v0 '
                        '(55/15/30, yield 0.16)',
        'product_item_ref': 'silica-xerogel',
        'components_json': json.dumps([
            {'item_ref': 'sodium-silicate-solution',
             'role': 'silicate-precursor', 'fraction': 0.55},
            {'item_ref': 'citric-acid', 'role': 'acid-catalyst',
             'fraction': 0.15},
            {'item_ref': 'tap-water', 'role': 'water',
             'fraction': 0.30},
        ]),
        'yield_fraction': 0.16,
        'status': 'candidate',
        'is_prior': True,
        'provenance_id': 'src-6',
        'notes': 'sg-community route recipe guess; yield 0.16 kg '
                 'xerogel per kg wet sol is an ESTIMATE (solids '
                 'math, not bench-measured); drying energy '
                 'excluded. Cascades onto self-made waterglass.',
    },
    {
        'name': 'magnetite-coprecipitation-v0',
        'display_name': 'Magnetite via coprecipitation v0 '
                        '(65/15/20, yield 0.30)',
        'product_item_ref': 'magnetite-powder',
        'components_json': json.dumps([
            {'item_ref': 'ferrous-sulfate', 'role': 'iron-salt',
             'fraction': 0.65},
            {'item_ref': 'sodium-hydroxide-lye', 'role': 'alkali',
             'fraction': 0.15},
            {'item_ref': 'tap-water', 'role': 'water',
             'fraction': 0.20},
        ]),
        'yield_fraction': 0.30,
        'status': 'candidate',
        'is_prior': True,
        'provenance_id': 'src-6',
        'notes': 'DELIBERATELY refuses to cost until ferrous '
                 'sulfate is cited — the refusal IS the research '
                 'ask. Buy-side magnetite stays the effective '
                 'price meanwhile.',
    },
    {
        'name': 'mwcnt-dispersion-2wt-v0',
        'display_name': 'MWCNT water dispersion 2wt% v0 (2/98)',
        'product_item_ref': 'cnt-water-dispersion',
        'components_json': json.dumps([
            {'item_ref': 'mwcnt-powder', 'role': 'cnt',
             'fraction': 0.02},
            {'item_ref': 'tap-water', 'role': 'water',
             'fraction': 0.98},
        ]),
        'yield_fraction': 1.0,
        'status': 'candidate',
        'is_prior': True,
        'provenance_id': 'src-6',
        'notes': 'Disperse BOUGHT industrial MWCNT — sonication '
                 'energy/equipment excluded v1; surfactant-free = '
                 'settles (surfactant route is the uncited gap). '
                 'Exists to price the make-vs-buy on dispersions.',
    },
    {
        'name': 'metakaolin-calcined-v0',
        'display_name': 'Metakaolin by calcining EPK (yield 0.86)',
        'product_item_ref': 'metakaolin',
        'components_json': json.dumps([
            {'item_ref': 'kaolin-raw', 'role': 'kaolin',
             'fraction': 1.0},
        ]),
        'yield_fraction': 0.86,
        'status': 'candidate',
        'is_prior': True,
        'provenance_id': 'src-7',
        'notes': 'Calcine ~700C to dehydroxylate; kiln energy '
                 'excluded v1. Standard pottery practice (calcined '
                 'kaolin), reactivity should be verified per batch.',
    },
    {
        'name': 'rha-burned-v0',
        'display_name': 'Rice husk ash by controlled burn '
                        '(yield 0.18)',
        'product_item_ref': 'rice-husk-ash',
        'components_json': json.dumps([
            {'item_ref': 'rice-hulls', 'role': 'hulls',
             'fraction': 1.0},
        ]),
        'yield_fraction': 0.18,
        'status': 'candidate',
        'is_prior': True,
        'provenance_id': 'src-7',
        'notes': 'Ash yield ~18% of hull mass (typical); burn is '
                 'self-fueling. Amorphous-silica quality depends on '
                 'burn temperature control.',
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
