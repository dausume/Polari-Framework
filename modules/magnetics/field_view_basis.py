"""
@module magnetics.field_view_basis

mag-fv (§A2, Dustin 2026-07-29): E/B FIELD VIEWS of devices for
SimSpaces — two display modes:
- vector-dispersion: vector glyphs SAMPLED through the volume,
  drawn ONLY where |field| falls inside the view's threshold bands
  (sparse dispersions, threshold-gated by construction);
- threshold-shapes: per-band USER-DEFINED math-shapes (sphere/box/
  cylinder specs) with color + alpha — translucent shells the
  designer draws; the system reports HOW WELL each shape matches
  its band (precision/recall fit metrics), never pretends the
  shape IS the field.

FieldViewGroup = the alternation ask: named ordered sets of views
so the UI cycles which field flow of a device is shown (B-flow vs
E-flow vs flux paths).

Source honesty (the watermark travels on every payload):
analytic closed forms (exact, available immediately) |
reluctance-solve (per-element flux tubes along the circuit/layout
paths — 1D-per-path, no off-path field claimed) | fem-2d (REFUSED
in v1: field-map export from the fem engine is the named
follow-up).

@consumers magnetics.field_views, magnetics.magnet_api,
polariServer (registration + seed)
"""

from objectTreeDecorators import treeObject, treeObjectInit

FIELD_KINDS = ('B', 'H', 'E', 'J')
SOURCE_KINDS = ('analytic', 'reluctance-solve', 'fem-2d')
DISPLAY_MODES = ('vector-dispersion', 'threshold-shapes',
                 'flux-tubes')


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


# ------------------------------------------------------------------ #
# Seeds: a dipole's B field both ways (dispersion + shells), the
# ring-core layout as flux tubes, one group alternating all three.
# Dipole moment 1.0 A*m^2 at the origin, axis +z:
# on-axis |B| = mu0*m/(2*pi*r^3), equatorial = half that — the
# selftest pins both.
# ------------------------------------------------------------------ #

SEED_FIELD_VIEWS = [
    {
        'name': 'dipole-b-dispersion',
        'display_name': 'Dipole B — threshold-gated vector '
                        'dispersion',
        'field_kind': 'B', 'source_kind': 'analytic',
        'device_kind': 'analytic', 'device_ref': '',
        'source_params_json': '{"primitive": "dipole", '
                              '"moment_a_m2": 1.0, '
                              '"center": [0, 0, 0], '
                              '"axis": [0, 0, 1]}',
        'display_mode': 'vector-dispersion',
        'sample_json': '{"region": {"min": [-0.1, -0.1, -0.1], '
                       '"max": [0.1, 0.1, 0.1]}, "per_axis": 8, '
                       '"jitter_seed": 42}',
        'is_prior': True, 'provenance_id': 'mag-fv',
        'notes': 'Vectors appear ONLY inside the bands — the '
                 'dispersion IS the threshold gate.',
    },
    {
        'name': 'dipole-b-shells',
        'display_name': 'Dipole B — translucent threshold shells',
        'field_kind': 'B', 'source_kind': 'analytic',
        'device_kind': 'analytic', 'device_ref': '',
        'source_params_json': '{"primitive": "dipole", '
                              '"moment_a_m2": 1.0, '
                              '"center": [0, 0, 0], '
                              '"axis": [0, 0, 1]}',
        'display_mode': 'threshold-shapes',
        'sample_json': '{"region": {"min": [-0.1, -0.1, -0.1], '
                       '"max": [0.1, 0.1, 0.1]}, "per_axis": 10, '
                       '"jitter_seed": 7}',
        'is_prior': True, 'provenance_id': 'mag-fv',
        'notes': 'User-drawn spheres per band; the fit report '
                 'prints precision/recall — a dipole band is NOT '
                 'a sphere (factor-2 axis/equator anisotropy) and '
                 'the numbers say exactly how much.',
    },
    {
        'name': 'ring-core-flux-tubes',
        'display_name': 'Ring-core layout — flux tubes '
                        '(reluctance solve)',
        'field_kind': 'B', 'source_kind': 'reluctance-solve',
        'device_kind': 'block-layout',
        'device_ref': 'ring-core-demo',
        'source_params_json': '{}',
        # was 'vector-dispersion' (mag-fv seed bug caught by the
        # mag-7 fields page: DISPLAY_MODES lacked the value, so the
        # guard silently coerced it — the LIST route then disagreed
        # with the payload's own mode).
        'display_mode': 'flux-tubes',
        'sample_json': '{}',
        'is_prior': True, 'provenance_id': 'mag-fv',
        'notes': '1D-per-path honesty: tubes along the solved '
                 'elements, no off-path field claimed.',
    },
]

SEED_FIELD_BANDS = [
    # dispersion bands (values sized to the 1 A*m^2 dipole in a
    # +/-0.1 m box: |B| runs ~2e-4 T at r=0.1 axis up past 0.2 T
    # near r=0.01).
    {'name': 'disp-band-strong', 'view_ref': 'dipole-b-dispersion',
     'min_value': 2e-3, 'max_value': 1e30, 'unit': 'T',
     'color': '#d62728', 'alpha': 0.9, 'label': 'strong',
     'shape_json': '{}',
     'is_prior': True, 'provenance_id': 'mag-fv', 'notes': ''},
    {'name': 'disp-band-mid', 'view_ref': 'dipole-b-dispersion',
     'min_value': 5e-4, 'max_value': 2e-3, 'unit': 'T',
     'color': '#ff7f0e', 'alpha': 0.6, 'label': 'mid',
     'shape_json': '{}',
     'is_prior': True, 'provenance_id': 'mag-fv', 'notes': ''},
    # NOTE: no 'weak' band on purpose — field below 5e-4 T draws
    # NOTHING (that is the dispersion honesty: absence = below
    # threshold, not zero field).
    # shell bands with user-drawn spheres.
    {'name': 'shell-band-inner', 'view_ref': 'dipole-b-shells',
     'min_value': 2e-3, 'max_value': 1e30, 'unit': 'T',
     'color': '#d62728', 'alpha': 0.35, 'label': 'inner shell',
     'shape_json': '{"kind": "sphere", "center": [0, 0, 0], '
                   '"r_m": 0.046}',
     'is_prior': True, 'provenance_id': 'mag-fv',
     'notes': 'r drawn between the equatorial (0.037) and axial '
              '(0.046) 2 mT radii — the fit metrics quantify the '
              'compromise.'},
    {'name': 'shell-band-outer', 'view_ref': 'dipole-b-shells',
     'min_value': 5e-4, 'max_value': 2e-3, 'unit': 'T',
     'color': '#1f77b4', 'alpha': 0.15, 'label': 'outer shell',
     'shape_json': '{"kind": "sphere", "center": [0, 0, 0], '
                   '"r_m": 0.073}',
     'is_prior': True, 'provenance_id': 'mag-fv', 'notes': ''},
    # flux-tube band: B thresholds on the tube coloring.
    {'name': 'tube-band-active', 'view_ref': 'ring-core-flux-tubes',
     'min_value': 1e-6, 'max_value': 1e30, 'unit': 'T',
     'color': '#2ca02c', 'alpha': 0.8, 'label': 'carrying flux',
     'shape_json': '{}',
     'is_prior': True, 'provenance_id': 'mag-fv', 'notes': ''},
]

SEED_FIELD_GROUPS = [
    {
        'name': 'dipole-and-ring-group',
        'display_name': 'Dipole views + ring flux tubes '
                        '(alternate)',
        'view_refs_json': '["dipole-b-dispersion", '
                          '"dipole-b-shells", '
                          '"ring-core-flux-tubes"]',
        'is_prior': True, 'provenance_id': 'mag-fv',
        'notes': 'THE alternation ask: cycle which field flow is '
                 'shown; a group is what a SimSpace scene binds.',
    },
]
