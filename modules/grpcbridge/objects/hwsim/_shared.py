"""@module grpcbridge.objects.hwsim._shared — what the hwsim row classes share (constants, seeds, helpers); split from hwsim_basis.py (sap-2c)."""

SEED_SIM_RIGS = [
    {'name': 'renode-rig', 'uptime_ms': 0, 'temp_c': 20.0,
     'pwm_duty': 0, 'led_on': False, 'status': 'seeded'},
]
