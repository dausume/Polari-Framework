"""@module odooconnect.objects.odoo_bindings._shared — what the odoo_bindings row classes share (constants, seeds, helpers); split from odoo_bindings_basis.py (sap-2c)."""

BINDING_DIRECTIONS = ('pull', 'push', 'both')
SEED_ODOO_BINDINGS = [
    {
        'name': 'sim-partners-to-supplynodes',
        'display_name': 'odoo_sim res.partner -> SupplyNode',
        'instance_ref': 'odoo-sim',
        'odoo_model': 'res.partner',
        'polari_class': 'SupplyNode',
        'field_map_json': '{"name": "display_name"}',
        'direction': 'pull',
        'row_name_prefix': 'odoo-partner',
        'defaults_json': '{"notes": "pulled from odoo_sim (od-4)"}',
        'is_prior': True,
        'provenance_id': 'od-4',
        'notes': 'Vendors/customers as supply-chain nodes.',
    },
    {
        'name': 'sim-products-to-wax-feedstocks',
        'display_name': 'odoo_sim product.template <-> WaxFeedstockDefinition',
        'instance_ref': 'odoo-sim',
        'odoo_model': 'product.template',
        'polari_class': 'WaxFeedstockDefinition',
        'field_map_json': '{"name": "display_name"}',
        'direction': 'both',
        'row_name_prefix': 'odoo-product',
        'defaults_json': '{"notes": "pulled from odoo_sim (od-4); '
                         'material properties stay Polari-side"}',
        'is_prior': True,
        'provenance_id': 'od-4',
        'notes': 'Wax-print feedstock catalog rides the product list; '
                 'push direction feeds od-5 scenario seeding.',
    },
    {
        'name': 'sim-sale-orders',
        'display_name': 'odoo_sim sale.order lines -> ProductOrder',
        'instance_ref': 'odoo-sim',
        'odoo_model': 'sale.order',
        'polari_class': 'ProductOrder',
        'field_map_json': '{}',
        'direction': 'pull',
        'row_name_prefix': 'odoo-so',
        'defaults_json': '{"due_days": 30, '
                         '"notes": "pulled from odoo_sim (od-4b)"}',
        'is_prior': True,
        'provenance_id': 'od-4b',
        'notes': 'The order-registrar feed: one ProductOrder per '
                 'order LINE via /api/odoo/pull-orders (line '
                 'explosion + state map live in odoo_orders, not a '
                 'flat field map). Needs the sale app installed — '
                 'pulls refuse honestly until then.',
    },
    {
        'name': 'sim-boms-to-supplychains',
        'display_name': 'odoo_sim mrp.bom -> SupplyChainDefinition',
        'instance_ref': 'odoo-sim',
        'odoo_model': 'mrp.bom',
        'polari_class': 'SupplyChainDefinition',
        'field_map_json': '{"display_name": "display_name"}',
        'direction': 'pull',
        'row_name_prefix': 'odoo-bom',
        'defaults_json': '{}',
        'is_prior': True,
        'provenance_id': 'od-4',
        'notes': 'Needs the mrp app installed in odoo_sim — pulls '
                 'refuse honestly until then (od-5 installs it).',
    },
]
