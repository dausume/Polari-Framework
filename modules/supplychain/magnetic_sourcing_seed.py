"""
@module supplychain.magnetic_sourcing_seed

mag-1 (MAGNETIC_MATERIALS_PLAN §mag-1 + §1b Rung 1): sourcing for the
magnetic-materials arc as CITED DATA — the pottery-channel hexaferrite
feedstocks (SrCO3 + Fe2O3), magnet wire, position sensing + drive
boards, powdered-iron / soft-ferrite fillers, and the commercial
benchmarks (ceramic ring magnets, ferrite toroid cores) the make-vs-buy
verdicts compare against.

Citation honesty (all observations 2026-07-28, live web research):
is_estimate=True wherever the figure came from a search snippet, a
range, or a size-ambiguous listing rather than a fetched exact price.
Non-USD citations carry their currency and are REFUSED by
normalization (sourcing_analysis) rather than silently treated as USD.

THE HONEST HEADLINE FINDING of the hunt: the plan's §1b pre-hunt said
"under $5/kg feedstock" for SrFe12O19 — the EXACT cites land nearer
~$12/kg (glaze-grade Fe2O3 runs $5.5-6.0/lb retail, not the ~$2/lb the
pre-hunt assumed). Cheaper Fe2O3 channels (construction/pigment-grade
red iron oxide, e.g. the Alpha Chemicals channel that supplies our
magnetite) are the named follow-up hunt. Bought magnetite (9.70/kg)
remains cheaper than hexaferrite FEEDSTOCK — but magnetite is soft
(cores), hexaferrite is hard (torque magnets); they answer different
roles and the premium buys coercivity.

@consumers supplychain.sourcing_seed (list extension), polariServer
seed_pairs (indirect)
"""

import json

PROV = 'mag-1'
OBS = '2026-07-28T18:00:00'

#: New item vocabulary: strontium-carbonate, red-iron-oxide,
#: barium-carbonate, srfe12o19-powder, magnet-wire-copper,
#: as5600-encoder, simplefoc-driver-board, carbonyl-iron-powder,
#: mnzn-ferrite-powder, ceramic-ring-magnet, ferrite-toroid-core,
#: bearing-608, shaft-rod-8mm, graphite-powder,
#: magnetic-geopolymer-mix, magnetic-solgel-composite,
#: wax-ferrite-feedstock, ferrite-cnt-solgel-mortar.

SEED_MAGNETIC_SOURCES = [
    {
        'name': 'evans-ceramic-supply',
        'display_name': 'Evans Ceramic Supply (evansceramics.com)',
        'supplier_name': 'Evans Ceramic Supply',
        'url': 'https://evansceramics.com/',
        'is_open_source': False, 'is_commercial': True,
        'is_local': False, 'is_polari': False,
        'is_eco_friendly': False,
        'availability': 'available',
        'supplies_json': json.dumps(
            ['strontium-carbonate', 'red-iron-oxide']),
        'demands_json': '[]',
        'business_model_ref': '',
        'locality_note': 'Wichita KS — ships; the pottery-glaze '
                         'channel (same channel as our metakaolin)',
        'is_prior': True, 'provenance_id': PROV,
        'notes': 'Pottery-chemical supplier with clean fetchable '
                 'exact prices and 1-50 lb tiers for the §1b Rung-1 '
                 'hexaferrite feedstocks.',
    },
    {
        'name': 'bntechgo',
        'display_name': 'BNTECHGO (bntechgo.com)',
        'supplier_name': 'BNTECHGO',
        'url': 'https://bntechgo.com/',
        'is_open_source': False, 'is_commercial': True,
        'is_local': False, 'is_polari': False,
        'is_eco_friendly': False,
        'availability': 'available',
        'supplies_json': json.dumps(['magnet-wire-copper']),
        'demands_json': '[]',
        'business_model_ref': '',
        'locality_note': '',
        'is_prior': True, 'provenance_id': PROV,
        'notes': 'Small-spool enameled copper magnet wire (hobby '
                 'scale, 155C rating).',
    },
    {
        'name': 'applied-magnets',
        'display_name': 'Applied Magnets (appliedmagnets.com)',
        'supplier_name': 'Applied Magnets',
        'url': 'https://appliedmagnets.com/',
        'is_open_source': False, 'is_commercial': True,
        'is_local': False, 'is_polari': False,
        'is_eco_friendly': False,
        'availability': 'available',
        'supplies_json': json.dumps(['magnet-wire-copper']),
        'demands_json': '[]',
        'business_model_ref': '',
        'locality_note': '',
        'is_prior': True, 'provenance_id': PROV,
        'notes': 'Essex 10 lb magnet-wire spools, full 10-30 AWG '
                 'price table fetched — the bulk winding channel.',
    },
    {
        'name': 'remington-industries',
        'display_name': 'Remington Industries '
                        '(remingtonindustries.com)',
        'supplier_name': 'Remington Industries',
        'url': 'https://www.remingtonindustries.com/',
        'is_open_source': False, 'is_commercial': True,
        'is_local': False, 'is_polari': False,
        'is_eco_friendly': False,
        'availability': 'available',
        'supplies_json': json.dumps(['magnet-wire-copper']),
        'demands_json': '[]',
        'business_model_ref': '',
        'locality_note': '',
        'is_prior': True, 'provenance_id': PROV,
        'notes': 'US magnet-wire maker, 2 oz - 80 lb spools; own '
                 'site hides per-size prices behind JS (range only) '
                 '— the cite rides an eBay snippet, est-flagged.',
    },
    {
        'name': 'ebay-as5600-listing',
        'display_name': 'AS5600 encoder modules (eBay marketplace)',
        'supplier_name': '(marketplace listing)',
        'url': 'https://www.ebay.com/itm/203596548499',
        'is_open_source': False, 'is_commercial': True,
        'is_local': False, 'is_polari': False,
        'is_eco_friendly': False,
        'availability': 'available',
        'supplies_json': json.dumps(['as5600-encoder']),
        'demands_json': '[]',
        'business_model_ref': '',
        'locality_note': 'China sellers, ships US',
        'is_prior': True, 'provenance_id': PROV,
        'notes': 'The SimpleFOC-standard magnetic rotary encoder '
                 '(12-bit) in multi-packs.',
    },
    {
        'name': 'simplefoc-shop',
        'display_name': 'SimpleFOC official shop (simplefoc.com)',
        'supplier_name': 'SimpleFOC project',
        'url': 'https://simplefoc.com/shop',
        'is_open_source': True, 'is_commercial': True,
        'is_local': False, 'is_polari': False,
        'is_eco_friendly': False,
        'availability': 'potential',
        'supplies_json': json.dumps(['simplefoc-driver-board']),
        'demands_json': '[]',
        'business_model_ref': '',
        'locality_note': 'EU — prices in EUR',
        'is_prior': True, 'provenance_id': PROV,
        'notes': 'Open-source FOC driver boards (the mag-6 drive '
                 'stack). ALL boards out of stock at observation — '
                 'availability=potential says so; clones carry the '
                 'available channel.',
    },
    {
        'name': 'ebay-simplefoc-clone-listing',
        'display_name': 'SimpleFOC Shield clone (eBay marketplace)',
        'supplier_name': '(marketplace listing)',
        'url': 'https://www.ebay.com/itm/267096750251',
        'is_open_source': True, 'is_commercial': True,
        'is_local': False, 'is_polari': False,
        'is_eco_friendly': False,
        'availability': 'available',
        'supplies_json': json.dumps(['simplefoc-driver-board']),
        'demands_json': '[]',
        'business_model_ref': '',
        'locality_note': '',
        'is_prior': True, 'provenance_id': PROV,
        'notes': 'MKS-style SimpleFOC Shield V2.0.4 clone — the '
                 'open-source design sold by third parties (design '
                 'open, listing commercial).',
    },
    {
        'name': 'sciencekitstore',
        'display_name': 'Science Kit Store (sciencekitstore.com)',
        'supplier_name': 'Science Kit Store',
        'url': 'https://sciencekitstore.com/',
        'is_open_source': False, 'is_commercial': True,
        'is_local': False, 'is_polari': False,
        'is_eco_friendly': False,
        'availability': 'available',
        'supplies_json': json.dumps(['carbonyl-iron-powder']),
        'demands_json': '[]',
        'business_model_ref': '',
        'locality_note': 'ships US-48 + Canada',
        'is_prior': True, 'provenance_id': PROV,
        'notes': 'High-purity carbonyl iron powder 1-10 lb — the '
                 'affordable small-lot channel (lab suppliers run '
                 '~50x higher $/kg). "Temporarily out of stock" at '
                 'observation; prices exact.',
    },
    {
        'name': 'rmcybernetics',
        'display_name': 'RMCybernetics (rmcybernetics.com)',
        'supplier_name': 'RMCybernetics',
        'url': 'https://www.rmcybernetics.com/shop/'
               'electronic-components/coils-transformers/'
               'ferrite-powder',
        'is_open_source': False, 'is_commercial': True,
        'is_local': False, 'is_polari': False,
        'is_eco_friendly': False,
        'availability': 'available',
        'supplies_json': json.dumps(['mnzn-ferrite-powder']),
        'demands_json': '[]',
        'business_model_ref': '',
        'locality_note': 'UK — ships internationally, multi-currency '
                         'incl. USD',
        'is_prior': True, 'provenance_id': PROV,
        'notes': 'The ONLY small-lot retail soft-ferrite POWDER '
                 'channel found (MnZn 40-150um, NiZn 250nm-2um); US '
                 'suppliers (SAM/American Elements/National '
                 'Magnetics) are quote-only.',
    },
    {
        'name': 'magnetshop',
        'display_name': 'MagnetShop (magnetshop.com)',
        'supplier_name': 'MagnetShop',
        'url': 'https://www.magnetshop.com/',
        'is_open_source': False, 'is_commercial': True,
        'is_local': False, 'is_polari': False,
        'is_eco_friendly': False,
        'availability': 'available',
        'supplies_json': json.dumps(['ceramic-ring-magnet']),
        'demands_json': '[]',
        'business_model_ref': '',
        'locality_note': '',
        'is_prior': True, 'provenance_id': PROV,
        'notes': 'Sintered ceramic (hard ferrite) ring magnets with '
                 'deep quantity tiers — the finished-magnet '
                 'benchmark the §1b local route must beat (or '
                 'honestly not beat).',
    },
    {
        'name': 'amidon-corp',
        'display_name': 'Amidon (amidoncorp.com)',
        'supplier_name': 'Amidon Corp',
        'url': 'https://www.amidoncorp.com/',
        'is_open_source': False, 'is_commercial': True,
        'is_local': False, 'is_polari': False,
        'is_eco_friendly': False,
        'availability': 'available',
        'supplies_json': json.dumps(['ferrite-toroid-core']),
        'demands_json': '[]',
        'business_model_ref': '',
        'locality_note': '',
        'is_prior': True, 'provenance_id': PROV,
        'notes': 'Fair-Rite-sourced ferrite toroids — the sintered '
                 'soft-core $/kg benchmark for the composite-core '
                 'make-vs-buy verdict.',
    },
    {
        'name': 'vxb-bearings',
        'display_name': 'VXB Bearings (vxb.com)',
        'supplier_name': 'VXB',
        'url': 'https://vxb.com/',
        'is_open_source': False, 'is_commercial': True,
        'is_local': False, 'is_polari': False,
        'is_eco_friendly': False,
        'availability': 'available',
        'supplies_json': json.dumps(['bearing-608', 'shaft-rod-8mm']),
        'demands_json': '[]',
        'business_model_ref': '',
        'locality_note': '',
        'is_prior': True, 'provenance_id': PROV,
        'notes': 'Skateboard-class 608 bearings + 8mm precision '
                 'shaft — the mechanical-containment shopping list '
                 'for motor v1.',
    },
    {
        'name': 'walmart-graphite-listing',
        'display_name': 'Graphite powder (Walmart Business listing)',
        'supplier_name': '(marketplace listing)',
        'url': 'https://business.walmart.com/ip/'
               'Graphite-Powder-1-lbs/557281333',
        'is_open_source': False, 'is_commercial': True,
        'is_local': False, 'is_polari': False,
        'is_eco_friendly': False,
        'availability': 'available',
        'supplies_json': json.dumps(['graphite-powder']),
        'demands_json': '[]',
        'business_model_ref': '',
        'locality_note': '',
        'is_prior': True, 'provenance_id': PROV,
        'notes': 'The cheap common conductive filler (signal/'
                 'resistive grade — §1c electric-conductor seeds); '
                 'purity unstated on the listing.',
    },
    {
        'name': 'nanographenex',
        'display_name': 'Nanographenex (nanographenex.com)',
        'supplier_name': 'Nanographenex',
        'url': 'https://nanographenex.com/',
        'is_open_source': False, 'is_commercial': True,
        'is_local': False, 'is_polari': False,
        'is_eco_friendly': False,
        'availability': 'potential',
        'supplies_json': json.dumps(['srfe12o19-powder']),
        'demands_json': '[]',
        'business_model_ref': '',
        'locality_note': 'non-US; the only poster of ANY price for '
                         'SrFe12O19 powder found',
        'is_prior': True, 'provenance_id': PROV,
        'notes': 'US channel for SrFe12O19 powder is quote-only '
                 '(Stanford Advanced Materials / American Elements '
                 'bot-blocked or quote-request; Sigma unfetchable). '
                 'availability=potential + the GBP citation document '
                 'the quote-gap — the §1b LOCAL route is the answer '
                 'to exactly this gap.',
    },
]

SEED_MAGNETIC_CITATIONS = [
    # --- §1b Rung 1 feedstocks: the pottery channel (all exact) ---
    {
        'name': 'evans-srco3-1lb-2026-07-28',
        'source_ref': 'evans-ceramic-supply',
        'item_ref': 'strontium-carbonate',
        'price': 3.75, 'currency': 'USD',
        'amount': 1.0, 'amount_unit': 'lb',
        'observed_at': OBS,
        'citation_url': 'https://evansceramics.com/product/'
                        'strontium-carbonate-1-pound/',
        'citation_note': 'Listed exact; 5 lb $17.50 / 10 lb $32.50 '
                         'tiers also fetched.',
        'is_estimate': False,
        'is_prior': True, 'provenance_id': PROV, 'notes': '',
    },
    {
        'name': 'evans-srco3-50lb-2026-07-28',
        'source_ref': 'evans-ceramic-supply',
        'item_ref': 'strontium-carbonate',
        'price': 150.00, 'currency': 'USD',
        'amount': 50.0, 'amount_unit': 'lb',
        'observed_at': OBS,
        'citation_url': 'https://evansceramics.com/product/'
                        'strontium-carbonate-1-pound/',
        'citation_note': 'Listed exact bag tier ($3.00/lb).',
        'is_estimate': False,
        'is_prior': True, 'provenance_id': PROV, 'notes': '',
    },
    {
        'name': 'clayking-srco3-50lb-2026-07-28',
        'source_ref': 'clay-king',
        'item_ref': 'strontium-carbonate',
        'price': 128.50, 'currency': 'USD',
        'amount': 50.0, 'amount_unit': 'lb',
        'observed_at': OBS,
        'citation_url': 'https://www.clay-king.com/product/'
                        'strontium-carbonate/',
        'citation_note': 'Fetched tier price $2.57/lb at 50+ lb '
                         '(sale tier; regular $3.03/lb) — the '
                         'cheapest cited SrCO3 = 5.67 USD/kg.',
        'is_estimate': False,
        'is_prior': True, 'provenance_id': PROV, 'notes': '',
    },
    {
        'name': 'evans-fe2o3-1lb-2026-07-28',
        'source_ref': 'evans-ceramic-supply',
        'item_ref': 'red-iron-oxide',
        'price': 6.75, 'currency': 'USD',
        'amount': 1.0, 'amount_unit': 'lb',
        'observed_at': OBS,
        'citation_url': 'https://evansceramics.com/product/'
                        'domestic-red-iron-oxide-1-pound/',
        'citation_note': 'Listed exact (page carries a stale "$5.00" '
                         'text block; cart price is $6.75).',
        'is_estimate': False,
        'is_prior': True, 'provenance_id': PROV, 'notes': '',
    },
    {
        'name': 'evans-fe2o3-50lb-2026-07-28',
        'source_ref': 'evans-ceramic-supply',
        'item_ref': 'red-iron-oxide',
        'price': 300.00, 'currency': 'USD',
        'amount': 50.0, 'amount_unit': 'lb',
        'observed_at': OBS,
        'citation_url': 'https://evansceramics.com/product/'
                        'domestic-red-iron-oxide-1-pound/',
        'citation_note': 'Listed exact bag tier ($6.00/lb).',
        'is_estimate': False,
        'is_prior': True, 'provenance_id': PROV, 'notes': '',
    },
    {
        'name': 'clayking-fe2o3-5lb-2026-07-28',
        'source_ref': 'clay-king',
        'item_ref': 'red-iron-oxide',
        'price': 27.70, 'currency': 'USD',
        'amount': 5.0, 'amount_unit': 'lb',
        'observed_at': OBS,
        'citation_url': 'https://www.clay-king.com/product/'
                        'red-iron-oxide-nr-4284/',
        'citation_note': 'Fetched tier $5.54/lb at 5+ lb (NR-4284, '
                         '~81% Fe2O3 glaze grade) = 12.21 USD/kg — '
                         'the cheapest cited Fe2O3. The ~81% assay '
                         'means stoichiometric feed needs ~1.23x '
                         'mass OR a purer pigment channel: the '
                         'named follow-up hunt (Alpha Chemicals '
                         'pigment channel, uncited).',
        'is_estimate': False,
        'is_prior': True, 'provenance_id': PROV, 'notes': '',
    },
    # --- BaCO3 = the SrCO3 alternate, toxicity caveat AS DATA ---
    {
        'name': 'clayking-baco3-1lb-2026-07-28',
        'source_ref': 'clay-king',
        'item_ref': 'barium-carbonate',
        'price': 3.00, 'currency': 'USD',
        'amount': 1.0, 'amount_unit': 'lb',
        'observed_at': OBS,
        'citation_url': 'https://www.clay-king.com/product/'
                        'barium-carbonate/',
        'citation_note': 'Listed exact; tiers to $2.70/lb at 55+ lb. '
                         'TOXICITY (channel-wide caveat): barium '
                         'carbonate is toxic if ingested/inhaled — '
                         'gloves + respirator handling; BaFe12O19 '
                         'work prefers SrCO3 for exactly this '
                         'reason.',
        'is_estimate': False,
        'is_prior': True, 'provenance_id': PROV, 'notes': '',
    },
    {
        'name': 'sheffield-baco3-5lb-2026-07-28',
        'source_ref': 'sheffield-pottery',
        'item_ref': 'barium-carbonate',
        'price': 29.00, 'currency': 'USD',
        'amount': 5.0, 'amount_unit': 'lb',
        'observed_at': OBS,
        'citation_url': 'https://www.sheffield-pottery.com/products/'
                        'barium-carbonate-5-pounds-rmbarcar',
        'citation_note': 'Listed exact (Type FF). Same toxicity '
                         'caveat as the Clay King row.',
        'is_estimate': False,
        'is_prior': True, 'provenance_id': PROV, 'notes': '',
    },
    # --- magnet wire (REQUIRED for any motor) ---
    {
        'name': 'bntechgo-magnetwire-30awg-4oz-2026-07-28',
        'source_ref': 'bntechgo',
        'item_ref': 'magnet-wire-copper',
        'price': 12.29, 'currency': 'USD',
        'amount': 4.0, 'amount_unit': 'oz',
        'observed_at': OBS,
        'citation_url': 'https://bntechgo.com/bntechgo-30-awg-magnet-'
                        'wire-enameled-copper-wire-enameled-magnet-'
                        'winding-wire-4-oz-0-0098-diameter-1-spool-'
                        'coil-red-temperature-rating-155-degrees-'
                        'celsius-widely-used-for-transformers-and-'
                        'inductors/',
        'citation_note': '30 AWG enameled, 155C class — the '
                         'small-spool prototyping price (~108 '
                         'USD/kg; fine wire costs more per kg).',
        'is_estimate': False,
        'is_prior': True, 'provenance_id': PROV, 'notes': '',
    },
    {
        'name': 'appliedmagnets-magnetwire-26awg-10lb-2026-07-28',
        'source_ref': 'applied-magnets',
        'item_ref': 'magnet-wire-copper',
        'price': 219.00, 'currency': 'USD',
        'amount': 10.0, 'amount_unit': 'lb',
        'observed_at': OBS,
        'citation_url': 'https://appliedmagnets.com/magnet-wire-'
                        'magnet-wire-spools-c-6/',
        'citation_note': 'Essex 26 AWG 10 lb spool, exact '
                         '(48.3 USD/kg).',
        'is_estimate': False,
        'is_prior': True, 'provenance_id': PROV, 'notes': '',
    },
    {
        'name': 'appliedmagnets-magnetwire-22awg-10lb-2026-07-28',
        'source_ref': 'applied-magnets',
        'item_ref': 'magnet-wire-copper',
        'price': 142.00, 'currency': 'USD',
        'amount': 10.0, 'amount_unit': 'lb',
        'observed_at': OBS,
        'citation_url': 'https://appliedmagnets.com/magnet-wire-'
                        'magnet-wire-spools-c-6/',
        'citation_note': 'Essex 22 AWG 10 lb spool, exact (31.3 '
                         'USD/kg) — thicker gauge = cheaper per kg; '
                         'the motor-winding bulk anchor.',
        'is_estimate': False,
        'is_prior': True, 'provenance_id': PROV, 'notes': '',
    },
    {
        'name': 'remington-magnetwire-26awg-1lb-2026-07-28',
        'source_ref': 'remington-industries',
        'item_ref': 'magnet-wire-copper',
        'price': 12.68, 'currency': 'USD',
        'amount': 1.0, 'amount_unit': 'lb',
        'observed_at': OBS,
        'citation_url': 'https://www.remingtonindustries.com/'
                        'magnet-wire/magnet-wire-26-awg-enameled-'
                        'copper-8-spool-sizes/',
        'citation_note': 'eBay snippet price for the 1 lb spool — '
                         'maker site shows only a range ($12.43-'
                         '$1,427.81 across 2 oz-80 lb, per-size '
                         'price behind JS). ESTIMATE.',
        'is_estimate': True,
        'is_prior': True, 'provenance_id': PROV, 'notes': '',
    },
    # --- sensing + drive (piece-priced) ---
    {
        'name': 'ebay-as5600-5pack-2026-07-28',
        'source_ref': 'ebay-as5600-listing',
        'item_ref': 'as5600-encoder',
        'price': 16.25, 'currency': 'USD',
        'amount': 5.0, 'amount_unit': 'unit',
        'observed_at': OBS,
        'citation_url': 'https://www.ebay.com/itm/203596548499',
        'citation_note': 'Search-snippet price (eBay item fetches '
                         'bot-blocked) — ESTIMATE. ~$3.25/module; '
                         '10-packs run ~$2.79/module. Shipping '
                         '$3.48-8.46 extra.',
        'is_estimate': True,
        'is_prior': True, 'provenance_id': PROV, 'notes': '',
    },
    {
        'name': 'simplefoc-shield-v2-eur-2026-07-28',
        'source_ref': 'simplefoc-shop',
        'item_ref': 'simplefoc-driver-board',
        'price': 20.00, 'currency': 'EUR',
        'amount': 1.0, 'amount_unit': 'unit',
        'observed_at': OBS,
        'citation_url': 'https://simplefoc.com/shop',
        'citation_note': 'Official SimpleFOCShield v2 EUR 20.00 '
                         'exact (v3 EUR 23.00, Mini v1.1 EUR 12.00) '
                         '— ALL out of stock at observation. EUR '
                         'currency: normalization refuses rather '
                         'than pretending an exchange rate.',
        'is_estimate': False,
        'is_prior': True, 'provenance_id': PROV, 'notes': '',
    },
    {
        'name': 'ebay-simplefoc-clone-2026-07-28',
        'source_ref': 'ebay-simplefoc-clone-listing',
        'item_ref': 'simplefoc-driver-board',
        'price': 30.49, 'currency': 'USD',
        'amount': 1.0, 'amount_unit': 'unit',
        'observed_at': OBS,
        'citation_url': 'https://www.ebay.com/itm/267096750251',
        'citation_note': 'SimpleFOC Shield V2.0.4 clone, search-'
                         'snippet price + $5.99 ship — ESTIMATE '
                         '(item fetch bot-blocked).',
        'is_estimate': True,
        'is_prior': True, 'provenance_id': PROV, 'notes': '',
    },
    # --- soft fillers: carbonyl iron + soft-ferrite powder ---
    {
        'name': 'sciencekitstore-carbonyl-1lb-2026-07-28',
        'source_ref': 'sciencekitstore',
        'item_ref': 'carbonyl-iron-powder',
        'price': 39.00, 'currency': 'USD',
        'amount': 1.0, 'amount_unit': 'lb',
        'observed_at': OBS,
        'citation_url': 'https://sciencekitstore.com/carbonyl-iron-'
                        'powder-zero-valent-high-purity',
        'citation_note': 'Listed exact (86 USD/kg) but "Temporarily '
                         'Out of Stock" at observation. Lab channel '
                         '(Chem-Impex 4-8um >=99.7%) runs ~3,900-'
                         '5,200 USD/kg for scale.',
        'is_estimate': False,
        'is_prior': True, 'provenance_id': PROV, 'notes': '',
    },
    {
        'name': 'sciencekitstore-carbonyl-10lb-2026-07-28',
        'source_ref': 'sciencekitstore',
        'item_ref': 'carbonyl-iron-powder',
        'price': 260.00, 'currency': 'USD',
        'amount': 10.0, 'amount_unit': 'lb',
        'observed_at': OBS,
        'citation_url': 'https://sciencekitstore.com/carbonyl-iron-'
                        'powder-zero-valent-high-purity',
        'citation_note': 'Listed exact 10 lb tier (57.3 USD/kg); '
                         'same out-of-stock caveat.',
        'is_estimate': False,
        'is_prior': True, 'provenance_id': PROV, 'notes': '',
    },
    {
        'name': 'rmcybernetics-mnzn-1kg-2026-07-28',
        'source_ref': 'rmcybernetics',
        'item_ref': 'mnzn-ferrite-powder',
        'price': 253.02, 'currency': 'USD',
        'amount': 1.0, 'amount_unit': 'kg',
        'observed_at': OBS,
        'citation_url': 'https://www.rmcybernetics.com/shop/'
                        'electronic-components/coils-transformers/'
                        'ferrite-powder',
        'citation_note': 'Top of the fetched option range ($19.96 '
                         '40 ml - $253.02 1 kg); per-option price '
                         'sits behind a selector so the 1 kg figure '
                         'is an ESTIMATE read off the range bound. '
                         'US channel is quote-only.',
        'is_estimate': True,
        'is_prior': True, 'provenance_id': PROV, 'notes': '',
    },
    # --- benchmarks: finished ring magnets + sintered toroids ---
    {
        'name': 'magnetshop-ceramic-ring-2026-07-28',
        'source_ref': 'magnetshop',
        'item_ref': 'ceramic-ring-magnet',
        'price': 6.83, 'currency': 'USD',
        'amount': 1.0, 'amount_unit': 'unit',
        'observed_at': OBS,
        'citation_url': 'https://www.magnetshop.com/'
                        'ceramic-ferrite-ring-magnets-p-103.html',
        'citation_note': 'Grade 5 ring 2.790" OD x 1.190" ID x '
                         '0.325", exact each-price; tiers 25+ $4.95, '
                         '100+ $2.88, 1000+ $2.28. Mass ~0.13 kg '
                         'COMPUTED from dims at rho~4.9 (so ~52 '
                         'USD/kg at qty 1 is derived, not listed).',
        'is_estimate': False,
        'is_prior': True, 'provenance_id': PROV, 'notes': '',
    },
    {
        'name': 'amidon-ft140-43-2026-07-28',
        'source_ref': 'amidon-corp',
        'item_ref': 'ferrite-toroid-core',
        'price': 4.50, 'currency': 'USD',
        'amount': 1.0, 'amount_unit': 'unit',
        'observed_at': OBS,
        'citation_url': 'https://www.amidoncorp.com/ft-140-43/',
        'citation_note': 'FT-140-43 (Fair-Rite 5943002701, ui 850) '
                         'exact each-price; mass ~33 g is the '
                         'Fair-Rite NOMINAL (not on the page) so '
                         'the ~136 USD/kg benchmark is derived-est.',
        'is_estimate': False,
        'is_prior': True, 'provenance_id': PROV, 'notes': '',
    },
    # --- mechanical containment ---
    {
        'name': 'vxb-608-10pack-2026-07-28',
        'source_ref': 'vxb-bearings',
        'item_ref': 'bearing-608',
        'price': 19.99, 'currency': 'USD',
        'amount': 10.0, 'amount_unit': 'unit',
        'observed_at': OBS,
        'citation_url': 'https://vxb.com/products/10-pack-skateboard-'
                        'bearing-608-2rs-sealed-8x22x7mm',
        'citation_note': '608-2RS sealed 8x22x7mm 10-pack, displayed '
                         'cart price (page also showed a lower '
                         '"regular" figure — the $19.99 cart price '
                         'is what a buyer pays).',
        'is_estimate': False,
        'is_prior': True, 'provenance_id': PROV, 'notes': '',
    },
    {
        'name': 'vxb-shaft-8mm-2pack-2026-07-28',
        'source_ref': 'vxb-bearings',
        'item_ref': 'shaft-rod-8mm',
        'price': 49.95, 'currency': 'USD',
        'amount': 2.0, 'amount_unit': 'unit',
        'observed_at': OBS,
        'citation_url': 'https://vxb.com/search?q=8mm+shaft+300mm',
        'citation_note': '8 mm x 300 mm chrome-plated case-hardened '
                         'rod 2-pack ($49.93-49.98 across listings; '
                         'pinned mid). Search-page listing price.',
        'is_estimate': False,
        'is_prior': True, 'provenance_id': PROV, 'notes': '',
    },
    # --- cheap conductive filler ---
    {
        'name': 'walmart-graphite-1lb-2026-07-28',
        'source_ref': 'walmart-graphite-listing',
        'item_ref': 'graphite-powder',
        'price': 18.99, 'currency': 'USD',
        'amount': 1.0, 'amount_unit': 'lb',
        'observed_at': OBS,
        'citation_url': 'https://business.walmart.com/ip/'
                        'Graphite-Powder-1-lbs/557281333',
        'citation_note': 'Search-snippet price — ESTIMATE; purity '
                         'unstated. GraphiteStore lab grades run '
                         '$100s/lb.',
        'is_estimate': True,
        'is_prior': True, 'provenance_id': PROV, 'notes': '',
    },
    # --- the SrFe12O19 quote-gap, on record ---
    {
        'name': 'nanographenex-srfe12o19-25g-2026-07-28',
        'source_ref': 'nanographenex',
        'item_ref': 'srfe12o19-powder',
        'price': 50.00, 'currency': 'GBP',
        'amount': 25.0, 'amount_unit': 'g',
        'observed_at': OBS,
        'citation_url': 'https://nanographenex.com/strontium-iron-'
                        'oxide-srfe12o19-micron-powder-purity-99-9-'
                        'size-1-3-%C2%B5m/',
        'citation_note': 'Base price GBP 50.00 with SIZE-AMBIGUOUS '
                         'options (25 g assumed = worst case) — '
                         'ESTIMATE, and GBP so normalization '
                         'refuses. Documents the buy-side state: US '
                         'small-lot SrFe12O19 is QUOTE-ONLY (SAM/'
                         'American Elements/Sigma all bot-blocked '
                         'or quote-request). The §1b pottery-'
                         'channel make-route answers this gap.',
        'is_estimate': True,
        'is_prior': True, 'provenance_id': PROV, 'notes': '',
    },
]

SEED_MAGNETIC_REQUIREMENTS = [
    {
        'name': 'srfe12o19-powder-requirements',
        'display_name': 'Strontium hexaferrite powder — the LOCAL '
                        'hard-magnet feedstock space (§1b Rung 1)',
        'product_item_ref': 'srfe12o19-powder',
        'roles_json': json.dumps([
            {'role': 'strontium-source',
             'purpose': 'the Sr (or Ba) carbonate: SrCO3 + 6 Fe2O3 '
                        '-> SrFe12O19 + CO2',
             'min_fraction': 0.03, 'max_fraction': 0.20,
             'candidates': ['strontium-carbonate',
                            'barium-carbonate']},
            {'role': 'iron-source',
             'purpose': 'Fe2O3 (or dissolved iron salt for the '
                        'sol-gel route)',
             'min_fraction': 0.20, 'max_fraction': 0.90,
             'candidates': ['red-iron-oxide', 'ferric-chloride',
                            'ferrous-sulfate']},
            {'role': 'chelant-fuel',
             'purpose': 'citrate sol-gel auto-combustion route only '
                        '(Route A): chelates the metals, burns as '
                        'the gel fuel',
             'min_fraction': 0.0, 'max_fraction': 0.30,
             'candidates': ['citric-acid']},
            {'role': 'water',
             'purpose': 'solution/gel water (Route A)',
             'min_fraction': 0.0, 'max_fraction': 0.55,
             'candidates': ['tap-water']},
        ]),
        'substitutes_json': json.dumps([
            {'item_ref': 'ceramic-ring-magnet',
             'caveats': [
                 'FINISHED sintered magnet, fixed geometry — '
                 'substitutes for the end part, not the powder',
                 'custom shapes still need the powder route (or '
                 'machining, which hard ferrite resists)',
             ],
             'notes': 'The make-vs-buy benchmark for the PM rotor: '
                      'grade 5 rings ~52 USD/kg at qty 1 falling '
                      'to ~17 USD/kg at 1000+ (MagnetShop tiers).'},
        ]),
        'is_prior': True,
        'provenance_id': PROV,
        'notes': 'Both routes calcine at pottery-kiln temperatures '
                 '(Route A citrate gel ~800-1000C, Route B solid-'
                 'state 1100-1250C = cone 8-10). KILN ENERGY '
                 'EXCLUDED-LOUD as always. Feedstock honesty: exact '
                 'cites land ~12 USD/kg feed (glaze-grade Fe2O3 '
                 '$5.54/lb) — the plan pre-hunt said <$5/kg; '
                 'pigment-channel Fe2O3 is the named cheaper hunt. '
                 'Magnetizing pulse required after cure/sinter '
                 '(§1b: the magnetizer is itself a buildable tool).',
    },
    {
        'name': 'magnetic-geopolymer-mix-requirements',
        'display_name': 'Magnetic geopolymer castable — matrix + '
                        'magnetic filler',
        'product_item_ref': 'magnetic-geopolymer-mix',
        'roles_json': json.dumps([
            {'role': 'matrix',
             'purpose': 'the cast body — the cascaded self-made '
                        'geopolymer at 1.11/kg',
             'min_fraction': 0.35, 'max_fraction': 0.80,
             'candidates': ['geopolymer-mix']},
            {'role': 'magnetic-filler',
             'purpose': 'sets mu_eff (msci-22 k<->mu ladder: 35 '
                        'vol% magnetite -> mu 2.196) or B_r when '
                        'the filler is HARD (SrFe12O19 -> bonded '
                        'magnet)',
             'min_fraction': 0.20, 'max_fraction': 0.65,
             'candidates': ['magnetite-powder',
                            'carbonyl-iron-powder',
                            'srfe12o19-powder']},
        ]),
        'substitutes_json': json.dumps([
            {'item_ref': 'ferrite-toroid-core',
             'caveats': [
                 'sintered commercial part: fixed shapes, ui ~850 '
                 'vs our composite ~2 — vastly better magnetically',
                 'not castable — no free geometry, no monolith '
                 'integration',
                 '~136 USD/kg derived-est (FT-140-43 at nominal '
                 '33 g) vs composite raw materials ~6-7/kg',
             ],
             'notes': 'The honest verdict shape: buy sintered cores '
                      'where a standard shape fits; cast composite '
                      'where geometry/integration wins, knowing mu '
                      'is ~400x lower.'},
        ]),
        'is_prior': True,
        'provenance_id': PROV,
        'notes': 'Fractions are BY MASS. msci rows speak vol%: 35 '
                 'vol% magnetite (rho 5.2) in geopolymer (rho 2.0) '
                 '= 58 wt% — the conversion lives ONCE in magnetics '
                 'analysis code, densities as data.',
    },
    {
        'name': 'magnetic-solgel-composite-requirements',
        'display_name': 'Magnetic sol-gel composite — the mortar-'
                        'grade magnetic material',
        'product_item_ref': 'magnetic-solgel-composite',
        'roles_json': json.dumps([
            {'role': 'matrix',
             'purpose': 'silica xerogel binder (the mortar/potting '
                        'phase of the §2b monolith model)',
             'min_fraction': 0.30, 'max_fraction': 0.80,
             'candidates': ['silica-xerogel']},
            {'role': 'magnetic-filler',
             'purpose': 'flux-continuity mortar grade (msci-22 '
                        'sol-gel-ferrite 1.714 @25 vol%)',
             'min_fraction': 0.20, 'max_fraction': 0.70,
             'candidates': ['magnetite-powder',
                            'carbonyl-iron-powder',
                            'srfe12o19-powder']},
        ]),
        'substitutes_json': '[]',
        'is_prior': True,
        'provenance_id': PROV,
        'notes': 'Two mortar grades from day one (§2b): PLAIN '
                 'sol-gel (mu~1, magnetically a gap) is just '
                 'silica-xerogel — this row is the MAGNETIC grade. '
                 'Washed near-neutral sol-gel is also the safer '
                 'winding-potting chemistry vs alkaline geopolymer '
                 '(enamel-compatibility QA check pending).',
    },
    {
        'name': 'wax-ferrite-feedstock-requirements',
        'display_name': 'Wax-ferrite print feedstock — printable '
                        'magnetics',
        'product_item_ref': 'wax-ferrite-feedstock',
        'roles_json': json.dumps([
            {'role': 'base-wax-blend',
             'purpose': 'the printable carrier (natural print-wax '
                        'blend, cascaded 6.95/kg)',
             'min_fraction': 0.25, 'max_fraction': 0.70,
             'candidates': ['natural-print-wax-blend']},
            {'role': 'magnetic-filler',
             'purpose': 'msci-22 wax-ferrite row @30 vol%; BLCNC '
                        'alternating-ferromagnet dispersion rides '
                        'this item',
             'min_fraction': 0.30, 'max_fraction': 0.75,
             'candidates': ['magnetite-powder']},
        ]),
        'substitutes_json': '[]',
        'is_prior': True,
        'provenance_id': PROV,
        'notes': '30 vol% magnetite in wax (rho 0.93) = ~71 wt% — '
                 'heavy filler loading; auger-feed printability at '
                 'that loading is UNTESTED (a WaxPrintOperation '
                 'trial + QA check, not an assumption).',
    },
    {
        'name': 'ferrite-cnt-solgel-mortar-requirements',
        'display_name': 'Ferrite-CNT sol-gel mortar — magnetic + '
                        'signal-conductive joint material',
        'product_item_ref': 'ferrite-cnt-solgel-mortar',
        'roles_json': json.dumps([
            {'role': 'matrix',
             'purpose': 'sol-gel mortar binder',
             'min_fraction': 0.30, 'max_fraction': 0.80,
             'candidates': ['silica-xerogel']},
            {'role': 'magnetic-filler',
             'purpose': 'flux continuity through the joint',
             'min_fraction': 0.15, 'max_fraction': 0.60,
             'candidates': ['magnetite-powder']},
            {'role': 'conductive-filler',
             'purpose': 'percolated CNT network carries SIGNALS '
                        'through the monolith (msci-23: 227 S/m '
                        '@2 vol% — ~5 orders below copper: sensing/'
                        'shielding/static ONLY, never power '
                        'windings)',
             'min_fraction': 0.0, 'max_fraction': 0.30,
             'candidates': ['cnt-water-dispersion',
                            'graphite-powder']},
        ]),
        'substitutes_json': '[]',
        'is_prior': True,
        'provenance_id': PROV,
        'notes': 'The FERRITE-CNT CONDUCTION honesty scoping as a '
                 'product row: dual-property (mu + sigma) mortars '
                 'are real and simulable TODAY; every report about '
                 'them prints the copper gap. Graphite powder = the '
                 'cheap resistive-grade alternative candidate.',
    },
]

SEED_MAGNETIC_FORMULAS = [
    {
        'name': 'srfe12o19-solidstate-v0',
        'display_name': 'SrFe12O19 via solid-state (Route B: mix, '
                        'calcine cone 8-10, mill)',
        'product_item_ref': 'srfe12o19-powder',
        'components_json': json.dumps([
            {'item_ref': 'strontium-carbonate',
             'role': 'strontium-source', 'fraction': 0.134},
            {'item_ref': 'red-iron-oxide', 'role': 'iron-source',
             'fraction': 0.866},
        ]),
        'yield_fraction': 0.960,
        'status': 'candidate',
        'is_prior': True,
        'provenance_id': PROV,
        'notes': 'Stoichiometry: SrCO3 (147.63) + 6 Fe2O3 (958.14) '
                 '-> SrFe12O19 (1061.77) + CO2; feed 1.0414 kg/kg '
                 'product = yield 0.960. Fractions assume '
                 'STOICHIOMETRIC-GRADE oxides — the cited NR-4284 '
                 'is ~81% Fe2O3, so real feed runs ~1.2x on the '
                 'iron side (assay honesty in the requirement '
                 'note). Calcine 1100-1250C + milling energy '
                 'EXCLUDED-LOUD; magnetizing pulse required.',
    },
    {
        'name': 'srfe12o19-solgel-v0',
        'display_name': 'SrFe12O19 via citrate sol-gel '
                        'auto-combustion (Route A: gel, combust, '
                        'calcine ~800-1000C)',
        'product_item_ref': 'srfe12o19-powder',
        'components_json': json.dumps([
            {'item_ref': 'strontium-carbonate',
             'role': 'strontium-source', 'fraction': 0.035},
            {'item_ref': 'red-iron-oxide', 'role': 'iron-source',
             'fraction': 0.229},
            {'item_ref': 'citric-acid', 'role': 'chelant-fuel',
             'fraction': 0.228},
            {'item_ref': 'tap-water', 'role': 'water',
             'fraction': 0.508},
        ]),
        'yield_fraction': 0.254,
        'status': 'candidate',
        'is_prior': True,
        'provenance_id': PROV,
        'notes': 'NANOSCALE hexaferrite at pottery-kiln temps — the '
                 'route that matches our sol-gel stack. Fractions + '
                 'yield are ESTIMATES (citric ~1:1 by mass with '
                 'oxides, water for a workable sol). CHEMISTRY '
                 'CAVEAT stated: literature citrate routes start '
                 'from NITRATES; the dissolved-oxide/carbonate '
                 'variant needs bench validation (dissolution in '
                 'citric acid is slow) — a research ask, not a '
                 'promise. Combustion fumes: outdoor/vented step.',
    },
    {
        'name': 'magnetic-geopolymer-35vol-v0',
        'display_name': 'Magnetic geopolymer @35 vol% magnetite '
                        '(58 wt%)',
        'product_item_ref': 'magnetic-geopolymer-mix',
        'components_json': json.dumps([
            {'item_ref': 'geopolymer-mix', 'role': 'matrix',
             'fraction': 0.42},
            {'item_ref': 'magnetite-powder', 'role': 'magnetic-filler',
             'fraction': 0.58},
        ]),
        'yield_fraction': 1.0,
        'status': 'candidate',
        'is_prior': True,
        'provenance_id': PROV,
        'notes': 'THE msci-22 feasibility row as a costed recipe: '
                 '35 vol% (rho 5.2 vs 2.0 -> 58 wt%) predicts '
                 'mu_eff 2.196 (fem.effective-permeability, linear '
                 'magnetostatics only). Cure compatibility with '
                 'ferrite surfaces + moisture behavior = the msci '
                 'row\'s stated unknowns; casting trials close '
                 'them, not this seed.',
    },
    {
        'name': 'magnetic-solgel-25vol-v0',
        'display_name': 'Magnetic sol-gel mortar @25 vol% magnetite '
                        '(~46 wt%)',
        'product_item_ref': 'magnetic-solgel-composite',
        'components_json': json.dumps([
            {'item_ref': 'silica-xerogel', 'role': 'matrix',
             'fraction': 0.54},
            {'item_ref': 'magnetite-powder', 'role': 'magnetic-filler',
             'fraction': 0.46},
        ]),
        'yield_fraction': 1.0,
        'status': 'candidate',
        'is_prior': True,
        'provenance_id': PROV,
        'notes': 'The flux-continuity mortar (msci-22 sol-gel-'
                 'ferrite 1.714 @25 vol%). wt conversion uses '
                 'xerogel bulk rho ~2.0 EST (porous silica scatters '
                 '1.0-2.2; density-as-data refinement pending). '
                 'Rides the cascaded xerogel (10.67/kg self-made '
                 'waterglass route).',
    },
    {
        'name': 'wax-ferrite-30vol-v0',
        'display_name': 'Wax-ferrite print feedstock @30 vol% '
                        '(~71 wt%)',
        'product_item_ref': 'wax-ferrite-feedstock',
        'components_json': json.dumps([
            {'item_ref': 'natural-print-wax-blend',
             'role': 'base-wax-blend', 'fraction': 0.29},
            {'item_ref': 'magnetite-powder', 'role': 'magnetic-filler',
             'fraction': 0.71},
        ]),
        'yield_fraction': 1.0,
        'status': 'candidate',
        'is_prior': True,
        'provenance_id': PROV,
        'notes': 'Printable magnetics (msci-22 wax-ferrite row). 30 '
                 'vol% in wax rho 0.93 -> 71 wt% — HEAVY loading; '
                 'auger printability untested (trial-gated). Melts '
                 'back to the reclaim pool like any wax.',
    },
    {
        'name': 'ferrite-cnt-solgel-mortar-v0',
        'display_name': 'Ferrite-CNT sol-gel mortar v0 '
                        '(50/40/10 wt)',
        'product_item_ref': 'ferrite-cnt-solgel-mortar',
        'components_json': json.dumps([
            {'item_ref': 'silica-xerogel', 'role': 'matrix',
             'fraction': 0.50},
            {'item_ref': 'magnetite-powder', 'role': 'magnetic-filler',
             'fraction': 0.40},
            {'item_ref': 'cnt-water-dispersion',
             'role': 'conductive-filler', 'fraction': 0.10},
        ]),
        'yield_fraction': 1.0,
        'status': 'candidate',
        'is_prior': True,
        'provenance_id': PROV,
        'notes': 'Signal-carrying magnetic mortar: sensor wiring '
                 'disappears into the matrix (the near-term ferrite-'
                 'CNT win). sigma target rides msci-23 percolation '
                 '(227 S/m @2 vol% CNT) — 5 orders below copper, '
                 'the report prints the gap every time. CNT arrives '
                 'as the 2wt% water dispersion (cascaded 7.50/kg).',
    },
]
