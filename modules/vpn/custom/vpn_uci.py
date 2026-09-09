"""
@module vpn.custom.vpn_uci

OpenWrt UCI for the VPN kinds that live on OpenWrt guests: the router
extensions (vpn-gateway, vpn-span — on the woven router) and the Link
hub / exit guests (vpn-hub, vpn-exit). Rendered from a
HardwareAppDefinition's `uci_profile` + `uci_params_json`, dispatched by
hardwareapps.custom.uci_profiles.render_uci for any `vpn-*` profile.

Rules that hold (D9/D11): private keys are generated ON the guest
(`wg genkey` at apply time — never rendered here, never pushed); the
only hooks are the templated toggles (forward / masquerade), each a
named knob; an exit renders with masquerade OFF unless `exit_enabled`
is true. Pure: (script, refusals).
"""
import ipaddress
import json
import re

PROFILES = ('vpn-gateway', 'vpn-span', 'vpn-hub', 'vpn-exit')
_LINK = ('vpn-gateway', 'vpn-hub', 'vpn-exit')     # WireGuard-based
_L2 = ('vpn-span',)                                 # OpenVPN tap bridge


def _params(defn):
    raw = defn.get('uci_params_json', '{}') if isinstance(defn, dict) else getattr(defn, 'uci_params_json', '{}')
    try:
        return json.loads(raw or '{}')
    except ValueError:
        return None


def render_vpn_uci(defn):
    profile = defn.get('uci_profile', '') if isinstance(defn, dict) else getattr(defn, 'uci_profile', '')
    p = _params(defn)
    refusals = []
    if profile not in PROFILES:
        return '', ['vpn uci_profile must be one of %s (got %r)' % (PROFILES, profile)]
    if p is None:
        return '', ['uci_params_json is not JSON']
    uci = p.get('uci', profile.replace('-', '_'))
    if not re.match(r'^[a-z][a-z0-9_]{0,14}$', uci):
        refusals.append('uci section name %r must be [a-z][a-z0-9_]{0,14}' % uci)
    port = int(p.get('listen_port', 0) or 0)
    if not 1 <= port <= 65535:
        refusals.append('listen_port must be 1..65535 (got %s)' % port)
    net = None
    if profile in _LINK:
        try:
            net = ipaddress.ip_network(p.get('cidr', ''), strict=True)
        except ValueError:
            refusals.append('cidr %r is not a valid network' % p.get('cidr', ''))
    if profile in _L2 and not p.get('vlan_device'):
        refusals.append('vpn-span needs vlan_device (the isle VLAN device, e.g. eth1.10)')
    if refusals:
        return '', refusals
    lines = ['#!/bin/sh', '# Polari isle-vpn UCI profile %r — rendered from HardwareAppDefinition; idempotent' % profile,
             '# private keys are made HERE at apply time and never leave this guest (D9)', 'set -e']
    if profile in _LINK:
        gw = str(list(net.hosts())[0])
        lines += ['opkg list-installed | grep -q "^wireguard-tools" || opkg install wireguard-tools luci-proto-wireguard',
                  '[ -s /etc/isle-mesh/%s.key ] || (umask 077; wg genkey > /etc/isle-mesh/%s.key)' % (uci, uci),
                  "uci -q delete network.%s 2>/dev/null || true" % uci,
                  "uci set network.%s=interface" % uci, "uci set network.%s.proto='wireguard'" % uci,
                  "uci set network.%s.private_key=\"$(cat /etc/isle-mesh/%s.key)\"" % (uci, uci),
                  "uci set network.%s.listen_port='%d'" % (uci, port),
                  "uci add_list network.%s.addresses='%s/%d'" % (uci, gw, net.prefixlen),
                  'uci commit network',
                  "uci -q delete firewall.%s 2>/dev/null || true" % uci, 'uci add firewall zone',
                  "uci set firewall.@zone[-1].name='%s'" % uci, "uci set firewall.@zone[-1].network='%s'" % uci,
                  "uci set firewall.@zone[-1].input='ACCEPT'", "uci set firewall.@zone[-1].output='ACCEPT'"]
        if profile == 'vpn-gateway':
            lines += ["uci set firewall.@zone[-1].forward='REJECT'   # members reach exposed apps via the .vpn rung only",
                      '# the listen port opens on the WAN-facing zone the isle designates (never the isle zone)',
                      'uci add firewall rule', "uci set firewall.@rule[-1].name='%s-listen'" % uci,
                      "uci set firewall.@rule[-1].src='wan'", "uci set firewall.@rule[-1].dest_port='%d'" % port,
                      "uci set firewall.@rule[-1].proto='udp'", "uci set firewall.@rule[-1].target='ACCEPT'"]
        else:
            fwd = 'ACCEPT' if p.get('forward', True) else 'REJECT'
            lines += ["uci set firewall.@zone[-1].forward='%s'   # hub: members route between each other (knob forward)" % fwd]
            if profile == 'vpn-exit':
                masq = '1' if p.get('exit_enabled') else '0'
                lines += ["# exit knob: masquerade to WAN — %s" % ('ON' if masq == '1' else 'OFF (turn it on from the isle side)'),
                          'uci add firewall forwarding', "uci set firewall.@forwarding[-1].src='%s'" % uci,
                          "uci set firewall.@forwarding[-1].dest='wan'",
                          "uci set firewall.wan.masq='%s'" % masq]
        lines += ['uci commit firewall', '/etc/init.d/network reload', '/etc/init.d/firewall reload',
                  'echo "%s: wg %s listening on %d, public key $(wg pubkey < /etc/isle-mesh/%s.key)"' % (profile, uci, port, uci)]
    else:   # vpn-span: OpenVPN tap bridged into the isle VLAN
        dev = p.get('vlan_device')
        lines += ['opkg list-installed | grep -q "^openvpn-openssl" || opkg install openvpn-openssl',
                  '# certificate material is issued by the Bridge server and installed by `isle vpn apply` (never rendered)',
                  "uci -q delete openvpn.%s 2>/dev/null || true" % uci, "uci set openvpn.%s=openvpn" % uci,
                  "uci set openvpn.%s.enabled='1'" % uci, "uci set openvpn.%s.dev='tap_%s'" % (uci, uci[:10]),
                  "uci set openvpn.%s.proto='%s'" % (uci, p.get('proto', 'tcp-client')),
                  "uci set openvpn.%s.port='%d'" % (uci, port),
                  "uci set openvpn.%s.ca='/etc/isle-mesh/%s/ca.crt'" % (uci, uci),
                  "uci set openvpn.%s.cert='/etc/isle-mesh/%s/client.crt'" % (uci, uci),
                  "uci set openvpn.%s.key='/etc/isle-mesh/%s/client.key'" % (uci, uci),
                  'uci commit openvpn',
                  '# bridge the tap into the isle VLAN so the far site is this isle at layer 2',
                  "uci add_list network.@device[0].ports='tap_%s' 2>/dev/null || true" % uci[:10],
                  '# (the isle VLAN device is %s; the bridge member list is the isle-vlan-router-config bridge)' % dev,
                  'uci commit network', '/etc/init.d/network reload', '/etc/init.d/openvpn restart']
    return '\n'.join(lines) + '\n', []
