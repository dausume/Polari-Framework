"""
@module vpn.vpn_catalog

The ten `isle-vpn` catalog listings (IsleCatalogEntry rows, kind
'isle-vpn') so the isle store shows Isle Link / Isle Bridge from day
one, plus the install-plan builder the islemesh catalog dispatches to
for that kind. Gateway-capable kinds declare `provides_engine
vpn-gateway` — the IsleEngine idiom that makes the `.vpn` rung
available on the device that installs them (§7.2).

Pure data + one pure function. Never seeded is_mock.

@consumers
  - polariServer (seeded next to islemesh's SEED_CATALOG)
  - islemesh.islemesh_catalog.install_plan (kind 'isle-vpn')
  - vpn.vpn_selftest
"""

from vpn.custom.vpn_constants import (
    APP_FAMILY, GATEWAY_ENGINE, KIND_INFO, KINDS, PROVIDER_TITLES,
)
from vpn.custom.vpn_placement import (
    PLACEMENT_INFO, ROUTER_GUEST, _GUEST, install_plan as placement_plan,
)


def _entry(kind):
    info = KIND_INFO[kind]
    label = info['label']
    return {
        'name': kind,
        'title': '%s' % info['title'],
        'description': '%s%s' % (
            info['description'],
            (' [%s]' % label) if label else ''),
        'kind': 'isle-vpn',
        'source_ref': kind,
        'service': APP_FAMILY,
        'port': 0,
        'domain': '',
        'provides_engine': GATEWAY_ENGINE if info['gateway'] else '',
        'category': 'network / %s' % PROVIDER_TITLES[info['provider']],
        'source': 'official',
        'published': True,
        # vpn-4: WHERE it runs (the store shows kvm / openwrt-extension /
        # container next to every kind) + the guest fields for kvm kinds
        'placement': PLACEMENT_INFO[kind]['placement'],
        'requires_tier': PLACEMENT_INFO[kind]['requires_tier'],
        'extends': PLACEMENT_INFO[kind]['extends'],
        'guest_kind': _GUEST.get(kind, {}).get('guest_kind', ''),
        'vm_image_ref': _GUEST.get(kind, {}).get('vm_image_ref', ''),
        'memory_mb': _GUEST.get(kind, {}).get('memory_mb', 0),
        'vcpus': _GUEST.get(kind, {}).get('vcpus', 0),
    }


#: The store listings, in the guide's order.
SEED_VPN_CATALOG = [_entry(kind) for kind in KINDS]


def vpn_install_plan(entry):
    """Host commands for one isle-vpn listing: the isle CLI installs
    the app package for that kind. The plan names the authority rule
    so nobody expects Polari to deploy it."""
    kind = entry.get('source_ref') or entry.get('name', '')
    if kind not in KIND_INFO:
        return {'ok': False, 'steps': [],
                'note': 'unknown isle-vpn kind %r' % kind}
    info = KIND_INFO[kind]
    place = PLACEMENT_INFO[kind]['placement']
    steps = placement_plan(kind)
    where = {'kvm': 'as its OWN GUEST (isle vm define/start — sees traffic, own hardware only)',
             'openwrt-extension': 'as an EXTENSION of the router guest %s (it carries the isle\'s subnet/VLAN)' % ROUTER_GUEST,
             'container': 'as a CONTAINER on this device'}[place]
    note = ('installs %s (%s) %s; configured from the isle '
            'side only — Polari proposes, `isle vpn apply` applies'
            % (info['title'], info['label'] or 'endpoint', where))
    if info['gateway']:
        note += '; makes the .vpn exposure rung available here'
    return {'ok': True, 'steps': steps, 'note': note, 'placement': place}
