"""
@module cntfet.objects.cnt_fields.FETFieldBand

Row class FETFieldBand of the cntfet module — one class per file (design §7), split
from cnt_fields_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class FETFieldBand(treeObject):
    """One value band of a scalar field (colour is DISCRETE in the
    scene — mag-fv FieldThresholdBand precedent): [min, max) in the
    field's unit, its colour/label and the Material3DDefinition it
    wears. Editable data, not code."""

    @treeObjectInit
    def __init__(self, name='', field='', order=0, min_value=0.0,
                 max_value=0.0, unit='', color='#888888', label='',
                 style_ref='', notes='', manager=None):
        self.name = name
        self.field = field
        self.order = order
        self.min_value = min_value
        self.max_value = max_value
        self.unit = unit
        self.color = color
        self.label = label
        self.style_ref = style_ref
        self.notes = notes
