"""
@module magnetics.objects.field_view.FieldViewDefinition

Row class FieldViewDefinition of the magnetics module — one class per file (design §7), split
from field_view_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit
from magnetics.objects.field_view._shared import DISPLAY_MODES, FIELD_KINDS, SOURCE_KINDS

class FieldViewDefinition(treeObject):
    """One named view of ONE field of a device."""

    @treeObjectInit
    def __init__(self, name='', display_name='', field_kind='B',
                 source_kind='analytic', device_kind='analytic',
                 device_ref='', source_params_json='{}',
                 display_mode='vector-dispersion',
                 sample_json='{}', is_prior=True, provenance_id='',
                 notes='', manager=None):
        self.name = name
        self.display_name = display_name
        self.field_kind = (field_kind if field_kind in FIELD_KINDS
                           else 'B')
        self.source_kind = (source_kind
                            if source_kind in SOURCE_KINDS
                            else 'analytic')
        #: 'analytic' | 'magnetic-circuit' | 'block-layout' — what
        #: device_ref names.
        self.device_kind = device_kind
        self.device_ref = device_ref
        #: analytic: {'primitive': 'dipole', 'moment_a_m2': m,
        #: 'center': [x,y,z], 'axis': [x,y,z]} or {'primitive':
        #: 'straight-wire', 'amps': I, 'point': [..], 'direction':
        #: [..]} (infinite wire — stated).
        self.source_params_json = source_params_json
        self.display_mode = (display_mode
                             if display_mode in DISPLAY_MODES
                             else 'vector-dispersion')
        #: {'region': {'min': [x,y,z], 'max': [x,y,z]},
        #:  'per_axis': N, 'jitter_seed': int} — deterministic
        #: sampling (same seed = same dispersion).
        self.sample_json = sample_json
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes
