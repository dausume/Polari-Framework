"""@module casting.objects.casting._shared — what the casting row classes share (constants, seeds, helpers); split from casting_basis.py (sap-2c)."""

PART_SOURCES = ('mathshape', 'imported-cad')
MASTER_MATERIAL_KINDS = ('natural-wax', 'machinable-wax',
                         'wax-filament', 'pla')
MAKE_ROUTES = ('auger-pellet-print', 'fdm-voron', 'cnc')
REMOVAL_ROUTES = ('melt-out', 'burn-out', 'mechanical')
FEEDSTOCK_PRIORITIES = ('core', 'supported')
