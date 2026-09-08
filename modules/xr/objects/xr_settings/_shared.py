"""@module xr.objects.xr_settings._shared — what the xr_settings row classes share (constants, seeds, helpers); split from xr_settings_basis.py (sap-2c)."""

XR_MODE_VALUES = ('unset', 'none', 'vr', 'ar', 'both')
XR_FRAMING_VALUES = ('unset', 'inside', 'exhibit')
XR_VARIANT_MODES = ('flat', 'vr', 'ar')
XR_GLOBAL_SETTINGS_NAME = 'xr-global-settings'
def variant_name(subject_kind: str, subject_name: str, mode: str) -> str:
    """Canonical identity for a variant row (idempotent seeding/lookup)."""
    return f'xr-variant:{subject_kind}:{subject_name}:{mode}'
SEED_XR_GLOBAL_SETTINGS = [
    {
        'name': XR_GLOBAL_SETTINGS_NAME,
        'xr_mode': 'unset',
        'xr_framing': 'unset',
    },
]
SEED_XR_TYPE_DEFAULTS = [
    {
        'name': 'xr-type-hydroponics-layout',
        'category': 'hydroponics-layout',
        'xr_mode': 'ar',
        'xr_framing': 'inside',
        'description': 'Room-layout planning spaces present in AR, '
                       'entered at person scale.',
    },
    {
        'name': 'xr-type-msim-world',
        'category': 'msim-world',
        'xr_mode': 'vr',
        'xr_framing': 'exhibit',
        'description': 'Abstract multi-scale simulation worlds present '
                       'in VR as orbitable exhibits.',
    },
    {
        'name': 'xr-type-wind-volume',
        'category': 'wind-volume',
        'xr_mode': 'vr',
        'xr_framing': 'inside',
        'description': 'Volumetric field spaces are rooms — entered at '
                       'person scale in VR.',
    },
]
