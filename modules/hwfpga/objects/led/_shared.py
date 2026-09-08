"""@module hwfpga.objects.led._shared — what the led row classes share (constants, seeds, helpers); split from led_basis.py (sap-2c)."""

SEED_LED_MATRICES = [
    {'name': 'renode-led-grid', 'pixels': 0, 'driver': 'mcu',
     'width': 4, 'height': 4},
]
