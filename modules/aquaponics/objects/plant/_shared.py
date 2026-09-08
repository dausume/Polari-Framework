"""@module aquaponics.objects.plant._shared — what the plant row classes share (constants, seeds, helpers); split from plant_basis.py (sap-2c)."""

PLANT_PARTS = ('root', 'stem', 'leaf', 'flower', 'fruit', 'seed',
               'tuber')
PART_FATES = ('harvested', 'senesces', 'soil-incorporated',
              'standing-permanent')
