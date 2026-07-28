"""
@module odooconnect.odoo_scenarios

BusinessScenarioDefinition — business simulations as DATA (od-5).
The guiding idea (Dustin 2026-07-28): businesses that do "whatever
they can" with "the tools they have". Scenario v1 is the wax-print
mold + geopolymer goods micro-business with two EXPLICIT prerequisite
assumptions (in assumptions_json, listed not hidden):
  1. feedstock is BOUGHT from a purely commercial supplier — the
     local hydroponic farm growing the wax source is scenario 2;
  2. a working wax 3D printer already exists (energy/labor/printer
     amortization excluded from v1 unit economics).

A scenario names a BASE OdooInstanceConfig that MUST be
mode=simulation — the engine refuses operations configs outright —
and runs in its own THROWAWAY database (scenario_db), so even the
sim database never accumulates scenario junk.

@consumers polariServer seed_pairs, odooconnect.odoo_scenario_engine
"""

import json

from objectTreeDecorators import treeObject, treeObjectInit


class BusinessScenarioDefinition(treeObject):
    """One runnable business simulation: seed spec, driver, outcome
    spec — all data. Lifecycle receipts land as OdooSyncReceipt rows
    (kind scenario-<phase>)."""

    @treeObjectInit
    def __init__(self, name='', display_name='', instance_ref='',
                 scenario_db='', required_modules='',
                 assumptions_json='[]', seed_spec_json='{}',
                 driver_spec_json='{}', outcome_spec_json='{}',
                 is_prior=True, provenance_id='', notes='',
                 manager=None):
        self.name = name
        self.display_name = display_name
        #: Base config (MUST be mode=simulation) whose server/auth the
        #: scenario database is reached through.
        self.instance_ref = instance_ref
        #: Throwaway database, 'odoo_scn_*' by convention — the CLI
        #: refuses to init/drop anything outside that prefix.
        self.scenario_db = scenario_db
        self.required_modules = required_modules
        self.assumptions_json = assumptions_json
        self.seed_spec_json = seed_spec_json
        self.driver_spec_json = driver_spec_json
        self.outcome_spec_json = outcome_spec_json
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes


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
                 'standard_price': 6.0, 'list_price': 6.0},
                {'ref': 'geopolymer-drymix', 'item_ref': 'geopolymer-kit',
                 'name': 'Geopolymer dry mix',
                 'storable': True, 'purchase_ok': True,
                 'sale_ok': False, 'uom': 'kg',
                 'standard_price': 1.8, 'list_price': 1.8},
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
                                'price_unit': 6.0}]},
                    {'vendor_ref': 'vendor-geopolymer',
                     'lines': [{'ref': 'geopolymer-drymix',
                                'qty': 40.0, 'price_unit': 1.8}]},
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
]
