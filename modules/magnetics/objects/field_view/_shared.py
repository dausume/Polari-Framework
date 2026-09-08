"""@module magnetics.objects.field_view._shared — what the field_view row classes share (constants, seeds, helpers); split from field_view_basis.py (sap-2c)."""

FIELD_KINDS = ('B', 'H', 'E', 'J')
SOURCE_KINDS = ('analytic', 'reluctance-solve', 'fem-2d')
DISPLAY_MODES = ('vector-dispersion', 'threshold-shapes',
                 'flux-tubes')
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
