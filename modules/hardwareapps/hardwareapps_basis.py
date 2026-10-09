"""
@module hardwareapps.hardwareapps_basis

The INDEX of hardwareapps rows (design §7): classes live one-per-file under
objects/; this file re-exports them and holds the seed pairs.
"""
from hardwareapps.objects.hardwareapps.HardwareAppDefinition import HardwareAppDefinition, HARDWARE_APP_KINDS, GUEST_KINDS, ROLES  # noqa: F401
from hardwareapps.objects.hardwareapps.HardwareAppState import HardwareAppState, VM_STATES  # noqa: F401
from hardwareapps.objects.hardwareapps.BridgingCapability import BridgingCapability, STATUSES as BRIDGING_CAPABILITY_STATUSES  # noqa: F401

#: ucd-2 (UNO_CORE_DEMO_PLAN.md §2/§5c, FIRMWARE_EXPORT_PLAN §2b): ONE seeded row for the Polari Firmware Installer
#: (the Hardware Bridge App ucd-4 builds) at 'never-run' — nothing proves it yet; the readiness page's `bridge` part
#: reads this row by `app` name. Never a second row seeded here: every other Bridge App earns its own at admission.
SEED_BRIDGING_CAPABILITIES = [
    {'name': 'polari-firmware-installer-bridging', 'app': 'Polari Firmware Installer',
     'transports_json': '["usb-serial"]', 'bridge_versions_json': '["button-clock"]', 'pkexec_verbs_json': '[]',
     'proven_by': '', 'proven_at': '', 'status': 'never-run',
     'notes': 'ucd-2 seed: nothing proves this yet (FIRMWARE_EXPORT_PLAN §2b is planned; the capture test §5c '
              'names what proving it means). ucd-4 builds the app and its capture test.'},
]

HARDWAREAPPS_SEED_PAIRS = [
    ('HardwareAppDefinition', HardwareAppDefinition, []),   # guest modules (isle_relay, isle_guestnet) seed their own rows
    ('HardwareAppState', HardwareAppState, []),
    ('BridgingCapability', BridgingCapability, SEED_BRIDGING_CAPABILITIES),
]
HARDWAREAPPS_CLASSES = [cls for _, cls, _ in HARDWAREAPPS_SEED_PAIRS]
