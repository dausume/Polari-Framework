"""
@module printcam.printcam_basis

The INDEX of printcam rows (design §7) + the seeds: one camera on the
seeded Voron, the extension's HardwareAppDefinition row, and its store row.
"""
from printcam.objects.printcam.CameraDefinition import CameraDefinition, STREAMERS  # noqa: F401
from printcam.objects.printcam.TimelapseRecord import TimelapseRecord  # noqa: F401

SEED_CAMERAS = [{'name': 'printcam-1', 'hardware_app': 'voron-printer', 'printer': 'voron-2.4-350', 'streamer': 'ustreamer',
                 'device': '/dev/video0', 'width': 1280, 'height': 720, 'fps': 15, 'webcam_name': 'printcam', 'timelapse': True,
                 'notes': 'a USB camera passed into the voron guest; Mainsail shows it; timelapse per print'}]

SEED_PRINTCAM_HARDWARE_APPS = [{
    'name': 'printcam', 'title': 'Print camera (extension of the Voron guest)', 'kind': 'hardware-extension-app', 'role': 'custom',
    'extends': 'voron-printer', 'guest_kind': 'debian', 'vm_image_ref': '', 'image_sha256_raw': '', 'memory_mb': 0, 'vcpus': 0,
    'bridges_json': '[]', 'passthrough_json': '[]', 'hardware_needs_json': '[{"kind": "usb", "role": "camera"}]',
    'provisioner': 'printcam.custom.provision:render_provision', 'requires_tier': 'hardware',
    'notes': 'set passthrough_json to the camera HardwarePort name (pol hwmap candidates --app printcam) before isle vm extend'}]

SEED_PRINTCAM_CATALOG = [{
    'name': 'printcam', 'title': 'Print camera', 'kind': 'hardware-extension-app', 'category': 'printing', 'extends': 'voron-printer',
    'description': 'USB camera into the Voron guest: ustreamer + Moonraker webcam + timelapse. Extends voron-printer; needs a usb camera port from the hardware map.',
    'source_ref': 'hardwareapps:printcam', 'requires_tier': 'hardware', 'published': True}]

PRINTCAM_SEED_PAIRS = [('CameraDefinition', CameraDefinition, SEED_CAMERAS), ('TimelapseRecord', TimelapseRecord, [])]
PRINTCAM_CLASSES = [cls for _, cls, _ in PRINTCAM_SEED_PAIRS]
