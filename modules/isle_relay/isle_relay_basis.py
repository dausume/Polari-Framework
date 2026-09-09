"""
@module isle_relay.isle_relay_basis

The INDEX of isle_relay rows (design §7) + the seeds: the relay segment,
its HardwareAppDefinition (the guest), and its store row.
"""
import json

from isle_relay.objects.relay.RelayNodeDefinition import RelayNodeDefinition, BEARERS  # noqa: F401
from isle_relay.objects.relay.RelayNodeState import RelayNodeState  # noqa: F401

SEED_RELAY_NODES = [{'name': 'relay-1', 'hardware_app': 'isle-relay', 'uci': 'relay', 'vlan': 30, 'cidr': '10.30.0.0/24',
                     'bearer': 'wifi-ap', 'ssid': 'isle-relay', 'reticulum_bearer': True,
                     'notes': 'the first relay segment: a second OpenWrt guest with the WiFi adapter passed through; extends the isle'}]

#: the guest itself, as a hardwareapps row (rendered by /api/hardwareapps/render/isle-relay)
SEED_RELAY_HARDWARE_APPS = [{
    'name': 'isle-relay', 'title': 'Isle relay (OpenWrt guest)', 'kind': 'hardware-app', 'role': 'relay',
    'guest_kind': 'openwrt', 'vm_image_ref': 'openwrt-isle-router.qcow2',
    'image_sha256_raw': '',   # pinned at deploy time from router-image.manifest (empty = render refuses, on purpose)
    'memory_mb': 512, 'vcpus': 2, 'bridges_json': '["br-mgmt", "isle-br-0"]', 'passthrough_json': '[]',
    'uci_profile': 'relay', 'uci_params_json': json.dumps(RelayNodeDefinition(**SEED_RELAY_NODES[0]).uci_params()),
    'requires_tier': 'hardware', 'hardware_needs_json': '[{"kind": "usb", "role": "wifi"}, {"kind": "pci", "role": "wifi"}]', 'notes': 'set passthrough_json to the WiFi DeviceLink name and image_sha256_raw before isle vm define'}]

#: the store row (IsleCatalogEntry) — install plan = isle vm define/start
SEED_RELAY_CATALOG = [{
    'name': 'isle-relay', 'title': 'Isle relay', 'kind': 'hardware-app', 'category': 'hardware',
    'description': 'A second OpenWrt guest that extends the isle across its own WiFi/NIC segment (dedicated relay); the body the Reticulum extension runs in.',
    'source_ref': 'hardwareapps:isle-relay', 'requires_tier': 'hardware', 'guest_kind': 'openwrt',
    'vm_image_ref': 'openwrt-isle-router.qcow2', 'memory_mb': 512, 'vcpus': 2, 'published': True}]

ISLE_RELAY_SEED_PAIRS = [('RelayNodeDefinition', RelayNodeDefinition, SEED_RELAY_NODES),
                         ('RelayNodeState', RelayNodeState, [])]
ISLE_RELAY_CLASSES = [cls for _, cls, _ in ISLE_RELAY_SEED_PAIRS]
