"""@module waxprint.objects.waxprint._shared — what the waxprint row classes share (constants, seeds, helpers); split from waxprint_basis.py (sap-2c)."""

CONVECTION_PRESETS = {
    'still-air': 8.0,
    'fridge-still': 12.0,
    'gentle-ducted': 30.0,
    'strong-fan': 80.0,
}
DEVICE_MATERIAL_ROLES = ('nozzle', 'auger', 'chamber', 'bed', 'multi')
