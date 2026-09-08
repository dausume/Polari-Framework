"""
@module magnetics.objects.field_view.FieldViewGroup

Row class FieldViewGroup of the magnetics module — one class per file (design §7), split
from field_view_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class FieldViewGroup(treeObject):
    """Named ordered set of views — the UI cycles/alternates
    between them (B-flow vs E-flow vs flux tubes of one device)."""

    @treeObjectInit
    def __init__(self, name='', display_name='',
                 view_refs_json='[]', is_prior=True,
                 provenance_id='', notes='', manager=None):
        self.name = name
        self.display_name = display_name
        self.view_refs_json = view_refs_json
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes
