"""
@module magnetics.objects.field_view.FieldThresholdBand

Row class FieldThresholdBand of the magnetics module — one class per file (design §7), split
from field_view_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class FieldThresholdBand(treeObject):
    """One |field| band of a view: the threshold values as DATA,
    with the band's display color/alpha and (threshold-shapes mode)
    the user-drawn shape spec."""

    @treeObjectInit
    def __init__(self, name='', view_ref='', min_value=0.0,
                 max_value=0.0, unit='T', color='#888888',
                 alpha=0.5, label='', shape_json='{}',
                 is_prior=True, provenance_id='', notes='',
                 manager=None):
        self.name = name
        self.view_ref = view_ref
        self.min_value = min_value
        self.max_value = max_value
        self.unit = unit
        self.color = color
        #: 0..1 transparency level per band (Dustin: 'varying
        #: colors and levels of transparent').
        self.alpha = alpha
        self.label = label
        #: USER-DEFINED shape for threshold-shapes mode:
        #: {'kind': 'sphere', 'center': [..], 'r_m': r} |
        #: {'kind': 'box', 'min': [..], 'max': [..]} |
        #: {'kind': 'cylinder', 'center': [..], 'axis': [..],
        #:  'r_m': r, 'half_len_m': h}. '{}' = no shape drawn yet
        #: (the fit report says so).
        self.shape_json = shape_json
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes
