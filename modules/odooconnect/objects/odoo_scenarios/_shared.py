"""@module odooconnect.objects.odoo_scenarios._shared — what the odoo_scenarios row classes share (constants, seeds, helpers); split from odoo_scenarios_basis.py (sap-2c)."""
import json

SEED_BUSINESS_SCENARIOS = [
    {
        'name': 'wax-mold-goods-v1',
        'display_name': 'Wax-printed molds -> geopolymer goods '
                        '(commercial feedstock)',
        'instance_ref': 'odoo-sim',
        'scenario_db': 'odoo_scn_wax_mold_goods_v1',
        'required_modules': 'product,mrp,sale_management,purchase,stock',
        'assumptions_json': json.dumps([
            'feedstock bought from a purely commercial supplier '
            '(local hydroponic wax-source farm = scenario 2)',
            'a working wax 3D printer already exists (tools-we-have)',
            'printer energy, labor and machine amortization EXCLUDED '
            'from v1 unit economics',
            'molds survive ~10 casts (0.1 mold consumed per pot)',
            'geopolymer cure losses ignored in v1',
            'prices REPINNED from citations 2026-07-28 (Dustin '
            'delegated the deliberate edit): soy 4.81/kg = '
            'aztec-lp402-soy-50lb-2026-07-28 exact; drymix 4.85/kg '
            '= gpi-geocement-50lb-2026-07-28 (range-mapped '
            'estimate) — the commercial-buyer assumption priced '
            'honestly; self-made geopolymer (1.11/kg cascaded) is '
            'the scenario-3 upside',
        ]),
        'seed_spec_json': json.dumps({
            'partners': [
                {'ref': 'vendor-commercial-wax',
                 'name': 'Commercial Wax Supplies Co',
                 'supplier_rank': 1},
                {'ref': 'vendor-geopolymer',
                 'name': 'Geopolymer Drymix Wholesale',
                 'supplier_rank': 1},
                {'ref': 'customer-local-goods',
                 'name': 'Local Goods Buyer Collective',
                 'customer_rank': 1},
            ],
            'products': [
                {'ref': 'soy-wax-pellets', 'item_ref': 'soy-wax',
                 'name': 'Soy wax pellets (commercial)',
                 'storable': True, 'purchase_ok': True,
                 'sale_ok': False, 'uom': 'kg',
                 'standard_price': 4.81, 'list_price': 4.81},
                {'ref': 'geopolymer-drymix', 'item_ref': 'geopolymer-kit',
                 'name': 'Geopolymer dry mix',
                 'storable': True, 'purchase_ok': True,
                 'sale_ok': False, 'uom': 'kg',
                 'standard_price': 4.85, 'list_price': 4.85},
                {'ref': 'wax-mold-planter',
                 'name': 'Wax-printed mold (planter)',
                 'storable': True, 'purchase_ok': False,
                 'sale_ok': False, 'uom': 'unit',
                 'standard_price': 0.0, 'list_price': 0.0},
                {'ref': 'geopolymer-planter-pot',
                 'name': 'Geopolymer planter pot',
                 'storable': True, 'purchase_ok': False,
                 'sale_ok': True, 'uom': 'unit',
                 'standard_price': 0.0, 'list_price': 18.0},
            ],
            'boms': [
                {'product_ref': 'wax-mold-planter', 'qty': 1.0,
                 'lines': [{'ref': 'soy-wax-pellets', 'qty': 0.35}]},
                {'product_ref': 'geopolymer-planter-pot', 'qty': 1.0,
                 'lines': [{'ref': 'geopolymer-drymix', 'qty': 2.0},
                           {'ref': 'wax-mold-planter', 'qty': 0.1}]},
            ],
        }),
        'driver_spec_json': json.dumps({
            'cycles': 2,
            'per_cycle': {
                'purchases': [
                    {'vendor_ref': 'vendor-commercial-wax',
                     'lines': [{'ref': 'soy-wax-pellets', 'qty': 10.0,
                                'price_unit': 4.81}]},
                    {'vendor_ref': 'vendor-geopolymer',
                     'lines': [{'ref': 'geopolymer-drymix',
                                'qty': 40.0, 'price_unit': 4.85}]},
                ],
                'manufacture': [
                    {'ref': 'wax-mold-planter', 'qty': 3.0},
                    {'ref': 'geopolymer-planter-pot', 'qty': 20.0},
                ],
                'sales': [
                    {'customer_ref': 'customer-local-goods',
                     'lines': [{'ref': 'geopolymer-planter-pot',
                                'qty': 20.0, 'price_unit': 18.0}]},
                ],
            },
        }),
        'outcome_spec_json': json.dumps({
            'business_model': 'wax-mold-goods-microbusiness',
            'business_model_scale': 'one-person',
            'metrics': ['revenue', 'material_cost', 'margin',
                        'pots_made', 'molds_made'],
        }),
        'is_prior': True,
        'provenance_id': 'od-5',
        'notes': 'First end-to-end proof that the economy tree gets '
                 'NUMBERS: buy commercial feedstock, print molds, '
                 'cast geopolymer pots, sell — margin + throughput '
                 'harvested to BusinessOutcome.',
    },
    {
        'name': 'hydroponic-wax-farm-v1',
        'display_name': 'Hydroponic wax-source farm (the mutual '
                        'loop, scenario 2)',
        'instance_ref': 'odoo-sim',
        'scenario_db': 'odoo_scn_hydro_wax_farm_v1',
        'required_modules': 'product,mrp,sale_management,purchase,stock',
        'assumptions_json': json.dumps([
            'growing is modeled as manufacturing (a grow-batch BOM) '
            '— biology abstracted to inputs->biomass yield',
            'water, lighting energy and labor EXCLUDED from v1 '
            'economics',
            'the wax-mold business is ONE partner playing BOTH '
            'roles: customer for biomass AND supplier of geopolymer '
            'self-watering pots at its 18.00 price (the mutual '
            'supply loop from the sourcing profiles)',
            'biomass transfer price 3.50/kg is a MARKET-SEEDING '
            'guess, not a citation — price discovery is the point',
            'pot purchases booked per cycle as replacement rate '
            '(2/cycle), not amortized capex',
        ]),
        'seed_spec_json': json.dumps({
            'partners': [
                {'ref': 'vendor-hydro-supplies',
                 'name': 'Hydro Grow Supplies Inc',
                 'supplier_rank': 1},
                {'ref': 'partner-wax-mold-business',
                 'name': 'Wax-Mold Goods Microbusiness',
                 'supplier_rank': 1, 'customer_rank': 1},
            ],
            'products': [
                {'ref': 'hydro-nutrient-mix',
                 'name': 'Hydroponic nutrient mix',
                 'storable': True, 'purchase_ok': True,
                 'sale_ok': False, 'uom': 'kg',
                 'standard_price': 3.5, 'list_price': 3.5},
                {'ref': 'wax-crop-seed',
                 'name': 'Wax-crop seed stock',
                 'storable': True, 'purchase_ok': True,
                 'sale_ok': False, 'uom': 'kg',
                 'standard_price': 15.0, 'list_price': 15.0},
                {'ref': 'geopolymer-self-watering-pot',
                 'name': 'Geopolymer self-watering pot (bought '
                         'from the wax business)',
                 'storable': True, 'purchase_ok': True,
                 'sale_ok': False, 'uom': 'unit',
                 'standard_price': 18.0, 'list_price': 18.0},
                {'ref': 'wax-source-biomass',
                 'name': 'Wax-source biomass (grown)',
                 'storable': True, 'purchase_ok': False,
                 'sale_ok': True, 'uom': 'kg',
                 'standard_price': 0.0, 'list_price': 3.5},
            ],
            'boms': [
                {'product_ref': 'wax-source-biomass', 'qty': 10.0,
                 'lines': [{'ref': 'hydro-nutrient-mix',
                            'qty': 1.2},
                           {'ref': 'wax-crop-seed', 'qty': 0.1}]},
            ],
        }),
        'driver_spec_json': json.dumps({
            'cycles': 2,
            'per_cycle': {
                'purchases': [
                    {'vendor_ref': 'vendor-hydro-supplies',
                     'lines': [{'ref': 'hydro-nutrient-mix',
                                'qty': 12.0, 'price_unit': 3.5},
                               {'ref': 'wax-crop-seed', 'qty': 1.0,
                                'price_unit': 15.0}]},
                    {'vendor_ref': 'partner-wax-mold-business',
                     'lines': [{'ref':
                                'geopolymer-self-watering-pot',
                                'qty': 2.0, 'price_unit': 18.0}]},
                ],
                'manufacture': [
                    {'ref': 'wax-source-biomass', 'qty': 30.0},
                ],
                'sales': [
                    {'customer_ref': 'partner-wax-mold-business',
                     'lines': [{'ref': 'wax-source-biomass',
                                'qty': 30.0, 'price_unit': 3.5}]},
                ],
            },
        }),
        'outcome_spec_json': json.dumps({
            'business_model': 'hydroponic-wax-source-farm',
            'business_model_scale': 'one-person',
            'metrics': ['revenue', 'material_cost', 'margin'],
        }),
        'is_prior': True,
        'provenance_id': 'od-5b',
        'notes': 'Scenario 2: the alternate-source business model '
                 'from the sourcing profiles becomes a running sim '
                 '— the farm supplies wax-source biomass to the '
                 'wax business AND buys its self-watering pots '
                 '(demands_json made transactional). Expected '
                 'economics are THIN (rev 105 vs cost 93 per '
                 'cycle) — transfer-price discovery + input-cost '
                 'pressure are what scenario 3 explores.',
    },
]
