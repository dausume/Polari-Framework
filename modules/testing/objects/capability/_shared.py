"""@module testing.objects.capability._shared — what the capability row classes share (constants, seeds, helpers); split from capability_basis.py (sap-2c)."""

CHECK_CATEGORIES = (
    'substrate', 'transport', 'format', 'twin', 'nocode', 'engine',
    'module',
)
CHECK_KINDS = ('in-process', 'live', 'compose')
CHECK_STATUSES = ('pass', 'fail', 'skip-honest', 'never-run')
CRITICALITIES = ('blocking', 'informational')
