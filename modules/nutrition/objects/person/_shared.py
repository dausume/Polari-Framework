"""@module nutrition.objects.person._shared — what the person row classes share (constants, seeds, helpers); split from person_basis.py (sap-2c)."""

ACTIVITY_LEVELS = ('sedentary', 'light', 'moderate', 'active',
                   'very-active')
ACTIVITY_PAL = {'sedentary': 1.2, 'light': 1.375, 'moderate': 1.55,
                'active': 1.725, 'very-active': 1.9}
WEIGHT_GOALS = ('maintain', 'lose', 'gain')
EATING_PATTERNS = ('2-meal', '3-meal', '3-small-2-snacks')
LIFE_STAGES = ('', 'pregnancy', 'lactation')
