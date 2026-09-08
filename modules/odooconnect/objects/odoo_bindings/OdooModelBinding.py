"""
@module odooconnect.objects.odoo_bindings.OdooModelBinding

Row class OdooModelBinding of the odooconnect module — one class per file (design §7), split
from odoo_bindings_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit
from odooconnect.objects.odoo_bindings._shared import BINDING_DIRECTIONS

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
