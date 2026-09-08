"""
@module hardwareapps.hardwareapps_basis

The INDEX of hardwareapps rows (design §7): classes live one-per-file under
objects/; this file re-exports them and holds the seed pairs.
"""
from hardwareapps.objects.hardwareapps.HardwareAppDefinition import HardwareAppDefinition, HARDWARE_APP_KINDS, GUEST_KINDS, ROLES  # noqa: F401
from hardwareapps.objects.hardwareapps.HardwareAppState import HardwareAppState, VM_STATES  # noqa: F401

HARDWAREAPPS_SEED_PAIRS = [
    ('HardwareAppDefinition', HardwareAppDefinition, []),   # guest modules (isle_relay, isle_guestnet) seed their own rows
    ('HardwareAppState', HardwareAppState, []),
]
HARDWAREAPPS_CLASSES = [cls for _, cls, _ in HARDWAREAPPS_SEED_PAIRS]
