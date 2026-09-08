"""@module tanks.objects.tank._shared — what the tank row classes share (constants, seeds, helpers); split from tank_basis.py (sap-2c)."""

WATER_TYPES = ('fresh', 'salt')
TANK_ROLES = ('general', 'macroalgae', 'filter-feeder', 'plankton',
              'open-swim', 'hiding-breeding', 'starch')
SPECIES_ROLES = ('nutrient-regulator', 'filter-feeder', 'detritus-eater',
                 'glass-cleaner', 'nutrient-replenisher',
                 'substrate-oxygenator', 'macroalgae-food',
                 'starch-producer', 'protein-source',
                 'nuisance-algae-consumer', 'cleaner')
SUBSTRATE_KINDS = ('live-aragonite-sand', 'live-rock-rubble',
                   'aquasoil', 'inert-gravel', 'biochar-sand',
                   'marine-mud', 'planted-sand')
