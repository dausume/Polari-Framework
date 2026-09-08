"""
@module bizops.objects.bizops.ProductOrder

Row class ProductOrder of the bizops module — one class per file (design §7), split
from bizops_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit
from bizops.objects.bizops._shared import ORDER_STATUSES

class ProductOrder(treeObject):
    """The order REGISTRAR row the planner runs on. v1 rows are
    entered directly (CRUDE/UI); the od-4 sale.order binding is the
    designed feed from Odoo once orders live there."""

    @treeObjectInit
    def __init__(self, name='', product_item_ref='',
                 variant_note='', unit_volume_l=1.0, quantity=0,
                 due_days=30, status='requested', customer_note='',
                 is_prior=False, provenance_id='biz-1', notes='',
                 manager=None):
        self.name = name
        self.product_item_ref = product_item_ref
        self.variant_note = variant_note
        #: The SIZE variable — everything scales from it.
        self.unit_volume_l = unit_volume_l
        self.quantity = quantity
        self.due_days = due_days
        self.status = (status if status in ORDER_STATUSES
                       else 'requested')
        self.customer_note = customer_note
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes
