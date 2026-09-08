"""@module microalgae.objects.reactor._shared — what the reactor row classes share (constants, seeds, helpers); split from reactor_basis.py (sap-2c)."""

WATER_TYPES = ('fresh', 'salt', 'both')
ALGAE_PRODUCTS = ('food-protein', 'starch', 'omega-oil', 'feed',
                  'biomass')
COUPLED_KINDS = ('aquaponics', 'tank', 'hydroponic')
CO2_SUPPLY_MODES = ('atmospheric', 'injected')
