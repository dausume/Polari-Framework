"""
@module gears.objects.gear.ShaftNodeDefinition

Row class ShaftNodeDefinition of the gears module — one class per file (design §7), split
from gear_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class ShaftNodeDefinition(treeObject):
    """One shaft = one angular speed. The graph node. Declared rows
    are documentation + drift visibility; a gear may reference an
    undeclared shaft and that is a SUGGESTION (declare it, or fix
    the typo), never a silent pass — the mag-3 flux-node rule."""

    @treeObjectInit
    def __init__(self, name='', train_ref='', shaft='',
                 is_input=False, is_output=False, is_fixed=False,
                 bearing_item_ref='', description='',
                 is_prior=True, provenance_id='', notes='',
                 manager=None):
        self.name = name
        self.train_ref = train_ref
        self.shaft = shaft
        self.is_input = is_input
        self.is_output = is_output
        #: A GROUNDED member (a fixed ring gear, a stationary
        #: carrier). Speed pinned to zero; it is how planetary
        #: ratios are chosen.
        self.is_fixed = is_fixed
        #: mag-1 already cites 608 bearings + 8 mm shaft.
        self.bearing_item_ref = bearing_item_ref
        self.description = description
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes
