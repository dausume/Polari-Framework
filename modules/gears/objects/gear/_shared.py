"""@module gears.objects.gear._shared — what the gear row classes share (constants, seeds, helpers); split from gear_basis.py (sap-2c)."""

AXIS_RELATIONS = ('parallel', 'coaxial', 'intersecting',
                  'skew', 'rotary-linear')
TOLERANCE_TIERS = ('T0', 'T1', 'T2', 'T3')
PROFILE_FAMILIES = ('involute', 'cycloidal', 'lantern', 'none')
