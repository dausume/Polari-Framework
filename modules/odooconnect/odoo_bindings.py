"""
@module odooconnect.odoo_bindings

OdooModelBinding — bindings are DATA (ODOO_INTEGRATION_PLAN.md od-4):
one row maps an Odoo model to a Polari class with a field map; new
mappings are new rows, never code. The external-id strategy is a
custom `x_polari_ref` field on the Odoo side (created on demand by the
sync engine on push-enabled instances) holding the Polari row name —
the idempotency key that makes pushes safe to re-run.

@consumers polariServer defClassList + seed_pairs, odooconnect.odoo_sync
"""

from objectTreeDecorators import treeObject, treeObjectInit

BINDING_DIRECTIONS = ('pull', 'push', 'both')


class OdooModelBinding(treeObject):
    """odoo_model <-> polari_class with a JSON field map (odoo field ->
    polari field). direction gates which sync verbs a binding allows;
    the WRITE knobs stay on the OdooInstanceConfig row the binding
    points at — a binding can never widen an instance's permissions."""

    @treeObjectInit
    def __init__(self, name='', display_name='', instance_ref='',
                 odoo_model='', polari_class='', field_map_json='{}',
                 direction='pull', external_ref_field='x_polari_ref',
                 row_name_prefix='', defaults_json='{}', is_prior=True,
                 provenance_id='', notes='', manager=None):
        self.name = name
        self.display_name = display_name
        #: OdooInstanceConfig row name this binding talks to.
        self.instance_ref = instance_ref
        self.odoo_model = odoo_model
        self.polari_class = polari_class
        self.field_map_json = field_map_json
        self.direction = (direction if direction in BINDING_DIRECTIONS
                          else 'pull')
        self.external_ref_field = external_ref_field
        #: Pulled rows are named '<prefix>-<odoo_id>' (deterministic,
        #: idempotent); default prefix = odoo_model with dots->dashes.
        self.row_name_prefix = row_name_prefix
        #: JSON dict of extra Polari fields stamped on CREATED rows.
        self.defaults_json = defaults_json
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes


class OdooSyncReceipt(treeObject):
    """One receipt per pull/push run — the MoveOperation receipt
    discipline applied to data: what ran, against which instance, and
    exactly which ids changed (receipt_json)."""

    @treeObjectInit
    def __init__(self, name='', kind='pull', binding_name='',
                 instance_ref='', created_count=0, updated_count=0,
                 skipped_count=0, conflict_count=0, receipt_json='{}',
                 created_at='', provenance_id='od-4', notes='',
                 manager=None):
        self.name = name
        self.kind = kind
        self.binding_name = binding_name
        self.instance_ref = instance_ref
        self.created_count = created_count
        self.updated_count = updated_count
        self.skipped_count = skipped_count
        self.conflict_count = conflict_count
        self.receipt_json = receipt_json
        self.created_at = created_at
        self.provenance_id = provenance_id
        self.notes = notes


#: Starter bindings (pull-first; sim only — ops stays read-mostly and
#: is bound deliberately later). Bindings whose Odoo model needs an
#: app that base doesn't ship (mrp) refuse honestly at pull time until
#: that app is installed in the database.
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
