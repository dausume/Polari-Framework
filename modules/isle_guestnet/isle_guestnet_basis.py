"""
@module isle_guestnet.isle_guestnet_basis

The INDEX of isle_guestnet rows (design §7) + the seeds: the guest network,
its guest (HardwareAppDefinition) and its store row.
"""
import json

from isle_guestnet.objects.guestnet.GuestNetworkDefinition import GuestNetworkDefinition  # noqa: F401
from isle_guestnet.objects.guestnet.GuestNetworkExposure import GuestNetworkExposure  # noqa: F401
from isle_guestnet.objects.guestnet.GuestNetworkState import GuestNetworkState  # noqa: F401

SEED_GUEST_NETWORKS = [{'name': 'guest-1', 'hardware_app': 'isle-guestnet', 'uci': 'guest', 'vlan': 20, 'cidr': '10.20.0.0/24',
                        'ssid': 'isle-guest', 'client_isolation': True, 'internet': True,
                        'notes': 'guest-only WiFi: isolated from the isle; exposures are rows'}]
SEED_GUEST_EXPOSURES = []   # none by default — a guest reaches nothing on the isle until a row says so

SEED_GUESTNET_HARDWARE_APPS = [{
    'name': 'isle-guestnet', 'title': 'Isle guest network (OpenWrt guest)', 'kind': 'hardware-app', 'role': 'guestnet',
    'guest_kind': 'openwrt', 'vm_image_ref': 'openwrt-isle-router.qcow2', 'image_sha256_raw': '',
    'memory_mb': 384, 'vcpus': 1, 'bridges_json': '["br-mgmt", "isle-br-0"]', 'passthrough_json': '[]',
    'uci_profile': 'guestnet', 'uci_params_json': json.dumps(GuestNetworkDefinition(**SEED_GUEST_NETWORKS[0]).uci_params()),
    'requires_tier': 'hardware', 'hardware_needs_json': '[{"kind": "usb", "role": "wifi"}, {"kind": "pci", "role": "wifi"}]', 'notes': 'set passthrough_json to the WiFi DeviceLink name and image_sha256_raw before isle vm define'}]

SEED_GUESTNET_CATALOG = [{
    'name': 'isle-guestnet', 'title': 'Isle guest network', 'kind': 'hardware-app', 'category': 'hardware',
    'description': 'An OpenWrt guest serving a guest-only WiFi/VLAN: isolated from the isle, client isolation on, internet only, exposures as rows.',
    'source_ref': 'hardwareapps:isle-guestnet', 'requires_tier': 'hardware', 'guest_kind': 'openwrt',
    'vm_image_ref': 'openwrt-isle-router.qcow2', 'memory_mb': 384, 'vcpus': 1, 'published': True}]

ISLE_GUESTNET_SEED_PAIRS = [('GuestNetworkDefinition', GuestNetworkDefinition, SEED_GUEST_NETWORKS),
                            ('GuestNetworkExposure', GuestNetworkExposure, SEED_GUEST_EXPOSURES),
                            ('GuestNetworkState', GuestNetworkState, [])]
ISLE_GUESTNET_CLASSES = [cls for _, cls, _ in ISLE_GUESTNET_SEED_PAIRS]
