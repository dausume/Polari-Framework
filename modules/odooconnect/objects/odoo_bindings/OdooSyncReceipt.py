"""
@module odooconnect.objects.odoo_bindings.OdooSyncReceipt

Row class OdooSyncReceipt of the odooconnect module — one class per file (design §7), split
from odoo_bindings_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

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
