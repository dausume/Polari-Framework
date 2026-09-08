"""
@module bizops.objects.bizops.QualityCheckDefinition

Row class QualityCheckDefinition of the bizops module — one class per file (design §7), split
from bizops_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class QualityCheckDefinition(treeObject):
    """One QA check for a kind of product: what to check, how, the
    acceptance criterion, and how often."""

    @treeObjectInit
    def __init__(self, name='', display_name='', product_kind='',
                 method='', acceptance='', frequency='per-batch',
                 is_prior=True, provenance_id='biz-4', notes='',
                 manager=None):
        self.name = name
        self.display_name = display_name
        self.product_kind = product_kind
        self.method = method
        self.acceptance = acceptance
        #: every-unit | per-batch | periodic.
        self.frequency = frequency
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes
