"""
@cross-cutting
@module vpn.custom.vpn_placement

WHERE each of the ten isle-vpn kinds runs and AT WHICH LEVELS it is
usable (his ask 2026-09-09: "those would need to be KVMs in some cases
or containers in others — as apps or OpenWRT extensions — usable at
all three levels, isle, archipelago and mesh").

Three placements, chosen by one rule each:

  kvm                a guest of its own (hardware-app, `isle vm define`)
                     — every kind that SEES TRAFFIC and holds authority
                     (hub, server, exit): its own failure domain, its own
                     NIC/bridge, WAN masquerade, keys and CA on its own
                     disk; never inside the router, never a container
                     sharing the host's network namespace.
  openwrt-extension  packages on the isle's router guest
                     (hardware-extension-app extending `isle-router`)
                     — every kind that carries THE ISLE'S subnet or VLAN
                     (gateway, span): the subnet, DHCP, DNS and firewall
                     live on the router, so the tunnel that carries them
                     must too.
  container          an isle-app container on any member device — every
                     endpoint, client, peer and the blind relay: it
                     carries no subnet, holds no one else's keys (a relay
                     holds none at all), and is fine on rented hardware.

Levels (RETICULUM plan §5n ladder `.isle → .arch → .vpn → .mesh → web`):
  isle          own LAN, fully trusted
  archipelago   `.arch` — isles federated as one network while the
                measured path meets the floor (§5c-b: rtt/loss/bitrate)
  mesh          `.mesh` — zero-trust relays; consumers are not peers
Per level a kind has a ROLE or nothing ('' = not used there).

Pure data + pure functions: no framework imports (vpn_constants rule).
@consumers
  - vpn.vpn_catalog (store rows carry placement + guest fields; install plan)
  - vpn.vpn_api (/api/vpn/placements, /api/vpn/topology/{level})
  - vpn.vpn_basis (VpnPlacement seed rows)
  - hardwareapps (SEED_VPN_HARDWARE_APPS via vpn.__init__)
  - polari-cli scripts/vpn.sh
"""
import json

from vpn.custom.vpn_constants import KIND_INFO, KINDS, PROVIDER_TITLES

PLACEMENTS = ('kvm', 'openwrt-extension', 'container')
LEVELS = ('isle', 'archipelago', 'mesh')
LEVEL_RUNG = {'isle': '.isle', 'archipelago': '.arch', 'mesh': '.mesh'}
LEVEL_DEFINITION = {
    'isle': 'Your own LAN behind the isle router: one VLAN, fully trusted, '
            '.isle names never leave it. A VPN here extends the isle to a '
            'device that is elsewhere, or joins two sites as one isle.',
    'archipelago': 'A set of isles federated as one network (.arch) while the '
                   'measured path meets the service floor (default rtt <= 150 ms, '
                   'loss <= 1 %, bitrate >= 1000 kbps). VPN links are the '
                   'internet-grade bearer between isle gateways; blind relays '
                   'by default, routing hubs only on hardware you own.',
    'mesh': 'Zero-trust state relays (.mesh): consumers are not peers and are '
            'not trusted — they receive state and send returns through the '
            'proposal seam. VPN kinds here are relay bodies, TCP/443 '
            'rendezvous and opt-in exits; never a membership authority.',
}
#: The archipelago floor (RETICULUM §5c-b; his numbers to set — D15).
ARCH_FLOOR = {'max_rtt_ms': 150, 'max_loss_pct': 1, 'min_bitrate_kbps': 1000}

#: The woven router guest the extensions extend (isle-side name).
ROUTER_GUEST = 'isle-router'
#: The image chain the OpenWrt guests come from (same as isle-relay).
OPENWRT_IMAGE = 'openwrt-isle-router.qcow2'

PLACEMENT_INFO = {
    'vpn-link-node': {
        'placement': 'container', 'body': 'docker image isle-vpn-link (WireGuard kernel via NET_ADMIN, wireguard-go fallback)',
        'extends': '', 'requires_tier': 'member',
        'levels': {'isle': 'member endpoint: this device on the household Link network',
                   'archipelago': 'member of a federated Link network — roams between isles over .vpn',
                   'mesh': ''},
        'rationale': 'carries only its own /32; no subnet, no authority — a container on any member device'},
    'vpn-link-gateway': {
        'placement': 'openwrt-extension', 'body': 'router packages wireguard-tools + luci-proto-wireguard; wg interface in the isle firewall zone',
        'extends': ROUTER_GUEST, 'requires_tier': 'core',
        'levels': {'isle': "the isle's gateway: carries the isle subnet, makes the .vpn rung available",
                   'archipelago': 'federation endpoint: gateway-to-gateway links (blind relay by default, D10)',
                   'mesh': ''},
        'rationale': "carries THE ISLE'S subnet — the subnet, DHCP, DNS and firewall live on the router, so the tunnel does too"},
    'vpn-link-relay': {
        'placement': 'container', 'body': 'docker image isle-vpn-relay (UDP datagram forwarder, no keys); may also ride the isle-relay guest as an extension',
        'extends': '', 'requires_tier': 'member',
        'levels': {'isle': 'reach-through for members behind NAT',
                   'archipelago': 'the default federation relay (blind — holds no keys, sees nothing)',
                   'mesh': 'zero-trust relay body (blind) — the transport under a MeshAppRelay'},
        'rationale': 'holds no keys and sees no plaintext — safe on a rented box; a container is the smallest honest body'},
    'vpn-link-hub': {
        'placement': 'kvm', 'body': 'OpenWrt guest (uci profile vpn-hub): wg server, member admission, routes between members',
        'extends': '', 'requires_tier': 'hardware',
        'levels': {'isle': "membership authority for the household's Link network",
                   'archipelago': 'routing relay hub that carries other isles\' subnets — sees traffic, own hardware only',
                   'mesh': ''},
        'rationale': 'sees traffic and holds authority — its own guest, own failure domain, own bridge; never in the router'},
    'vpn-link-exit': {
        'placement': 'kvm', 'body': 'OpenWrt guest (uci profile vpn-exit): a Link hub plus WAN masquerade (knob, off by default)',
        'extends': '', 'requires_tier': 'hardware',
        'levels': {'isle': "members' internet exit through this isle's connection (knob)",
                   'archipelago': "federated members' exit (knob) — sees traffic",
                   'mesh': 'opt-in exit for consumers on restrictive networks (knob)'},
        'rationale': 'masquerades to WAN — needs its own WAN-facing bridge and its own guest'},
    'vpn-bridge-client': {
        'placement': 'container', 'body': 'docker image isle-vpn-bridge (openvpn client, certificate from the server)',
        'extends': '', 'requires_tier': 'member',
        'levels': {'isle': 'joins this device or isle to a Bridge server',
                   'archipelago': 'TCP/443 path into an archipelago hub where UDP is blocked',
                   'mesh': 'consumer path over TCP/443 where UDP is blocked'},
        'rationale': 'an endpoint with one certificate — a container on any member device'},
    'vpn-bridge-server': {
        'placement': 'kvm', 'body': 'Debian guest (provisioner vpn.custom.vpn_provision): openvpn server + CA/CRL + management interface on 127.0.0.1',
        'extends': '', 'requires_tier': 'hardware',
        'levels': {'isle': 'x509 hub for household clients — CA + CRL, PeerAgreement as consent',
                   'archipelago': 'x509 hub for federation joins',
                   'mesh': 'TCP/443 rendezvous for consumers — sees traffic, own hardware only'},
        'rationale': 'issues certificates and sees traffic — its own guest with the CA on its own disk'},
    'vpn-bridge-span': {
        'placement': 'openwrt-extension', 'body': 'router packages openvpn-openssl (tap) bridged into the isle VLAN (br-lan)',
        'extends': ROUTER_GUEST, 'requires_tier': 'core',
        'levels': {'isle': "one isle across two sites at layer 2",
                   'archipelago': 'L2 span between member isles (the vpn-mesh-host prototype idea)',
                   'mesh': ''},
        'rationale': "stretches THE ISLE'S VLAN — the VLAN is the router's, so the tap bridge must be there"},
    'vpn-bridge-exit': {
        'placement': 'kvm', 'body': 'Debian guest (provisioner vpn.custom.vpn_provision): a Bridge server plus WAN masquerade (knob, off by default)',
        'extends': '', 'requires_tier': 'hardware',
        'levels': {'isle': "clients' internet exit through this isle's connection (knob)",
                   'archipelago': "federated clients' exit (knob) — sees traffic",
                   'mesh': 'opt-in exit for consumers (knob)'},
        'rationale': 'masquerades to WAN — its own WAN-facing bridge and its own guest'},
    'vpn-bridge-peer': {
        'placement': 'container', 'body': 'docker image isle-vpn-bridge in peer mode: joins an outside OpenVPN-only box as a gateway peer',
        'extends': '', 'requires_tier': 'member',
        'levels': {'isle': 'an OpenVPN-only box (YunoHost-class) as a gateway peer of this isle',
                   'archipelago': 'an outside network joined as a member through its own OpenVPN',
                   'mesh': ''},
        'rationale': 'speaks to something we do not run — a container we can replace without touching the router'},
}

#: Guest sizing for the KVM kinds (HardwareAppDefinition fields).
_GUEST = {
    'vpn-link-hub': {'guest_kind': 'openwrt', 'vm_image_ref': OPENWRT_IMAGE, 'memory_mb': 512, 'vcpus': 2,
                     'uci_profile': 'vpn-hub', 'provisioner': ''},
    'vpn-link-exit': {'guest_kind': 'openwrt', 'vm_image_ref': OPENWRT_IMAGE, 'memory_mb': 512, 'vcpus': 2,
                      'uci_profile': 'vpn-exit', 'provisioner': ''},
    'vpn-bridge-server': {'guest_kind': 'debian', 'vm_image_ref': 'debian-12-genericcloud.qcow2', 'memory_mb': 1024, 'vcpus': 2,
                          'uci_profile': '', 'provisioner': 'vpn.custom.vpn_provision:render_provision'},
    'vpn-bridge-exit': {'guest_kind': 'debian', 'vm_image_ref': 'debian-12-genericcloud.qcow2', 'memory_mb': 1024, 'vcpus': 2,
                        'uci_profile': '', 'provisioner': 'vpn.custom.vpn_provision:render_provision'},
}
#: UCI profiles the router extensions push onto the woven router.
_EXTENSION_UCI = {'vpn-link-gateway': 'vpn-gateway', 'vpn-bridge-span': 'vpn-span'}


def placement_for(kind):
    return PLACEMENT_INFO[kind]


def levels_for(kind):
    return [lvl for lvl in LEVELS if PLACEMENT_INFO[kind]['levels'].get(lvl)]


def kinds_at(level):
    """[(kind, role)] usable at that level, guide order."""
    return [(k, PLACEMENT_INFO[k]['levels'][level]) for k in KINDS
            if PLACEMENT_INFO[k]['levels'].get(level)]


def install_plan(kind):
    """The isle-side commands for one kind, by placement (the `isle vm`
    contract for guests + extensions; `isle vpn install` for containers)."""
    p = PLACEMENT_INFO[kind]
    if p['placement'] == 'kvm':
        return ['isle vm define %s --from-polari' % kind, 'isle vm start %s' % kind,
                'isle vpn install %s --in %s' % (kind, kind), 'isle vm status %s' % kind]
    if p['placement'] == 'openwrt-extension':
        return ['isle vm status %s' % ROUTER_GUEST, 'isle vm extend %s --with %s' % (ROUTER_GUEST, kind),
                'isle vpn install %s --on-router' % kind]
    return ['isle vpn install %s' % kind]


def placement_rows():
    """VpnPlacement seed rows, one per kind."""
    rows = []
    for kind in KINDS:
        info, p = KIND_INFO[kind], PLACEMENT_INFO[kind]
        rows.append({
            'name': kind, 'kind': kind, 'provider': info['provider'],
            'title': info['title'],
            'placement': p['placement'], 'body': p['body'], 'extends': p['extends'],
            'requires_tier': p['requires_tier'],
            'sees_traffic': info['label'] == 'Sees traffic', 'blind': info['label'] == 'Blind',
            'level_isle': p['levels'].get('isle', ''),
            'level_archipelago': p['levels'].get('archipelago', ''),
            'level_mesh': p['levels'].get('mesh', ''),
            'levels_json': json.dumps(levels_for(kind)),
            'install_plan_json': json.dumps(install_plan(kind)),
            'rationale': p['rationale'],
        })
    return rows


SEED_VPN_PLACEMENTS = placement_rows()


def hardware_app_rows():
    """HardwareAppDefinition rows for the KVM kinds (own guests) and the
    router extensions (extend the woven router guest)."""
    rows = []
    for kind, g in _GUEST.items():
        info = KIND_INFO[kind]
        rows.append({
            'name': kind, 'title': '%s (own guest — sees traffic)' % info['title'], 'kind': 'hardware-app',
            'role': 'vpn-exit' if info['exit'] else ('vpn-server' if info['provider'] == 'bridge' else 'vpn-hub'),
            'extends': '', 'guest_kind': g['guest_kind'], 'vm_image_ref': g['vm_image_ref'],
            'image_sha256_raw': '', 'memory_mb': g['memory_mb'], 'vcpus': g['vcpus'],
            # mgmt + isle bridge always; an exit also needs the WAN-facing bridge
            'bridges_json': json.dumps(['br-mgmt', 'isle-br-0'] + (['br-wan'] if info['exit'] else [])),
            'passthrough_json': '[]', 'uci_profile': g['uci_profile'],
            'uci_params_json': json.dumps({'uci': kind.replace('-', '_')[:15], 'cidr': '10.66.0.0/24',
                                           'listen_port': 51820 if info['provider'] == 'link' else 1194,
                                           'exit_enabled': False}),
            'provisioner': g['provisioner'], 'requires_tier': 'hardware',
            'hardware_needs_json': '[]',
            'notes': 'sees traffic — own hardware only (D10); image sha pinned at deploy from the image chain; '
                     'exit_enabled stays false until the operator turns the knob on the isle',
        })
    for kind, uci in _EXTENSION_UCI.items():
        info = KIND_INFO[kind]
        rows.append({
            'name': kind, 'title': '%s (extension of the isle router)' % info['title'], 'kind': 'hardware-extension-app',
            'role': 'vpn-gateway' if info['gateway'] else 'vpn-span', 'extends': ROUTER_GUEST,
            'guest_kind': 'openwrt', 'vm_image_ref': '', 'image_sha256_raw': '', 'memory_mb': 0, 'vcpus': 0,
            'bridges_json': '[]', 'passthrough_json': '[]', 'uci_profile': uci,
            'uci_params_json': json.dumps({'uci': uci.replace('-', '_'), 'cidr': '10.66.0.0/24',
                                           'listen_port': 51820 if info['provider'] == 'link' else 1194,
                                           'vlan_device': 'eth1.10'}),
            'provisioner': '', 'requires_tier': 'core', 'hardware_needs_json': '[]',
            'notes': "carries the isle's subnet/VLAN — lives on the router guest; configured from the isle side only (D9)",
        })
    return rows


SEED_VPN_HARDWARE_APPS = hardware_app_rows()


def topology(level):
    """The per-level structured summary (the page's top panel)."""
    if level not in LEVELS:
        return None
    out = {'level': level, 'rung': LEVEL_RUNG[level], 'definition': LEVEL_DEFINITION[level],
           'placements': [{'kind': k, 'title': KIND_INFO[k]['title'], 'line': PROVIDER_TITLES[KIND_INFO[k]['provider']],
                           'placement': PLACEMENT_INFO[k]['placement'], 'label': KIND_INFO[k]['label'] or 'endpoint',
                           'role': role} for k, role in kinds_at(level)]}
    if level == 'archipelago':
        out['floor'] = dict(ARCH_FLOOR)
    return out
