"""@module casting.objects.sprue._shared — what the sprue row classes share (constants, seeds, helpers); split from sprue_basis.py (sap-2c)."""

GATE_STYLES = ('top-gate', 'bottom-gate-riser', 'side-gate')
VENT_PLACEMENTS = ('high-points', 'manual')
REMOVAL_MODES = ('snap', 'cut', 'melt-with-master')
NECK_RATIO_LIMITS = {'brittle': 0.25, 'ductile': 0.40}
