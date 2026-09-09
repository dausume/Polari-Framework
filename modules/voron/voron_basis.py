"""
@module voron.voron_basis

The INDEX of voron rows (design §7) + the seeds: one sim-mode printer, its
boards, the HardwareAppDefinition (the Debian guest) and its store row.
"""
from voron.objects.voron.PrinterDefinition import PrinterDefinition, MODELS, MODES, PROBES  # noqa: F401
from voron.objects.voron.PrinterBoard import PrinterBoard, BOARD_ROLES, BOARD_MODELS, CONNECTIONS  # noqa: F401
from voron.objects.voron.PrinterState import PrinterState, KLIPPER_STATES  # noqa: F401

#: the Debian cloud image the guest boots (pinned by RAW sha at deploy time, like the router image)
VORON_GUEST_IMAGE = 'debian-12-genericcloud-amd64.qcow2'

SEED_PRINTERS = [{
    'name': 'voron-2.4-350', 'title': 'Voron 2.4 350 (sim)', 'model': 'voron-2.4', 'kinematics': 'corexy',
    'bed_x_mm': 350, 'bed_y_mm': 350, 'bed_z_mm': 340, 'mode': 'sim', 'hardware_app': 'voron-printer',
    'toolhead': 'stealthburner', 'extruder': 'clockwork2', 'probe': 'tap', 'max_velocity': 300, 'max_accel': 3000,
    'macros_profile': 'voron-standard',
    'notes': 'seeded in mode sim on purpose: no printer is measured yet, so the stack (Klipper + Moonraker + Mainsail + '
             'the macros) runs against the Linux host MCU with no hardware and no motion physics; switch to mode real '
             'once the main board is passed through and its serial_by_id measured (pol hwmap scan)'}]

SEED_PRINTER_BOARDS = [
    {'name': 'voron-2.4-350-main', 'printer': 'voron-2.4-350', 'role': 'main', 'model': 'btt-octopus-1.1', 'mcu_name': 'mcu',
     'connection': 'usb', 'serial_by_id': '', 'vendor_id': '1d50', 'product_id': '614e', 'canbus_uuid': '',
     'firmware_flashed': False, 'notes': 'serial_by_id is empty until measured on the device (pol hwmap scan); real mode refuses without it'},
    {'name': 'voron-2.4-350-toolhead', 'printer': 'voron-2.4-350', 'role': 'toolhead', 'model': 'btt-ebb36', 'mcu_name': 'EBBCan',
     'connection': 'canbus', 'serial_by_id': '', 'vendor_id': '', 'product_id': '', 'canbus_uuid': '',
     'firmware_flashed': False, 'notes': 'canbus_uuid from klipper/scripts/canbus_query.py can0 inside the guest; real mode refuses without it'},
    {'name': 'voron-2.4-350-host', 'printer': 'voron-2.4-350', 'role': 'host', 'model': 'linux-host', 'mcu_name': 'host',
     'connection': 'linux', 'serial_by_id': '/tmp/klipper_host_mcu', 'vendor_id': '', 'product_id': '', 'canbus_uuid': '',
     'firmware_flashed': False, 'notes': 'the Linux-process MCU built by the provisioner; the ONLY board sim mode uses (as the primary [mcu])'},
]

#: the guest itself, as a hardwareapps row (domain XML from /api/hardwareapps/render/voron-printer; the provisioner is ours)
SEED_VORON_HARDWARE_APPS = [{
    'name': 'voron-printer', 'title': 'Voron printer (Debian guest: Klipper + Moonraker + Mainsail)', 'kind': 'hardware-app',
    'role': 'custom', 'guest_kind': 'debian', 'vm_image_ref': VORON_GUEST_IMAGE,
    'image_sha256_raw': '',   # pinned at deploy time from the image's RAW sha (empty = domain render refuses, on purpose)
    'memory_mb': 2048, 'vcpus': 2, 'bridges_json': '["isle-br-0"]', 'passthrough_json': '[]',
    'uci_profile': '', 'uci_params_json': '{}', 'requires_tier': 'hardware',
    # dotted path the hardwareapps API imports lazily to render the guest's provisioner
    'provisioner': 'voron.custom.provision:render_provision',
    'notes': 'mode real: set passthrough_json to the DeviceLink names of the printer boards (USB) and image_sha256_raw '
             'before isle vm define; mode sim: no passthrough — the Linux host MCU is built inside the guest'}]

#: the store row (IsleCatalogEntry) — install plan = isle vm define/start on the hardware tier
SEED_VORON_CATALOG = [{
    'name': 'voron-printer', 'title': 'Voron 3D printer (Klipper + Mainsail)', 'kind': 'hardware-app', 'category': 'hardware',
    'description': 'Klipper + Moonraker + Mainsail in a Debian KVM guest with the printer boards passed through (mode real), '
                   'or Klipper\'s Linux host MCU with no printer (mode sim — the stack runs, no motion physics).',
    'source_ref': 'hardwareapps:voron-printer', 'requires_tier': 'hardware', 'guest_kind': 'debian',
    'vm_image_ref': VORON_GUEST_IMAGE, 'memory_mb': 2048, 'vcpus': 2, 'published': True}]

VORON_SEED_PAIRS = [('PrinterDefinition', PrinterDefinition, SEED_PRINTERS),
                    ('PrinterBoard', PrinterBoard, SEED_PRINTER_BOARDS),
                    ('PrinterState', PrinterState, [])]
VORON_CLASSES = [cls for _, cls, _ in VORON_SEED_PAIRS]
