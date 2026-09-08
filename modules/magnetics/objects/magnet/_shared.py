"""@module magnetics.objects.magnet._shared — what the magnet row classes share (constants, seeds, helpers); split from magnet_basis.py (sap-2c)."""

REALIZATION_LEVELS = ('theoretical', 'literature-demonstrated',
                      'recipe-seeded', 'made-and-measured')
OPTION_FAMILIES = ('soft-magnetic', 'hard-magnetic',
                   'electric-conductor', 'containment-structural',
                   'reference')
MATERIAL_FORMS = ('powder', 'castable-block', 'mortar', 'wire',
                  'potting', 'sintered-part', 'trace')
