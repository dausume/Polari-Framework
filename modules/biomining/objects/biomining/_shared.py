"""@module biomining.objects.biomining._shared — what the biomining row classes share (constants, seeds, helpers); split from biomining_basis.py (sap-2c)."""

AGENT_TYPES = ('bacteria', 'algae', 'fungi', 'biofilm', 'plant')
MECHANISMS = ('bioaccumulation', 'biosorption', 'bioleaching',
              'biomineralization', 'bioprecipitation', 'biosynthesis')
BIOMINE_VARIANTS = ('iron-ferrite', 'steel-feedstock',
                    'carbon-nanotube', 'nutrient-recovery',
                    'trace-metal', 'optical-dielectric')
SOURCE_KINDS = ('tank', 'reactor', 'aquaponics', 'feedstock')
PRODUCT_KINDS = ('ferrite-magnet', 'steel-feedstock',
                 'carbon-nanotube-feedstock', 'recovered-nutrient',
                 'metal-powder', 'electro-optic-crystal',
                 'optical-glass', 'coating-dielectric',
                 'birefringent-crystal', 'ir-window',
                 'nickel-metal', 'coated-steel')
