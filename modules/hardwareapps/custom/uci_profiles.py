"""
@module hardwareapps.custom.uci_profiles

OpenWrt UCI profiles for the guests, rendered from a HardwareAppDefinition's
`uci_profile` + `uci_params_json` — the isle-vlan-router-config idiom
(network → dhcp → firewall zone → mDNS) as ONE script the isle pushes over
its router SSH key. Pure. Profiles:
  relay     a second isle segment on the guest's WiFi/NIC that FORWARDS to
            the isle zone (expands the isle) — plus the Reticulum bearer
            port opened for the extension app
  guestnet  an isolated guest network: own SSID/VLAN/DHCP, forward=REJECT
            to the isle, DNS forwarded for an allow-list only, client
            isolation on
"""
import ipaddress
import json
import re

PROFILES = ('relay', 'guestnet')


def _params(defn):
    raw = defn.get('uci_params_json', '{}') if isinstance(defn, dict) else getattr(defn, 'uci_params_json', '{}')
    try:
        return json.loads(raw or '{}')
    except ValueError:
        return None


def render_uci(defn):
    """Returns (script, refusals)."""
    profile = defn.get('uci_profile', '') if isinstance(defn, dict) else getattr(defn, 'uci_profile', '')
    if profile.startswith('vpn-'):
        # vpn-4: the VPN guests/extensions render their own UCI (vpn module)
        try:
            from vpn.custom.vpn_uci import render_vpn_uci
        except ImportError:
            return '', ['uci_profile %r needs the vpn module on this instance' % profile]
        return render_vpn_uci(defn)
    p = _params(defn)
    refusals = []
    if profile not in PROFILES:
        return '', ['uci_profile must be one of %s (got %r)' % (PROFILES, profile)]
    if p is None:
        return '', ['uci_params_json is not JSON']
    uci = p.get('uci', profile)
    if not re.match(r'^[a-z][a-z0-9_]{0,14}$', uci):
        refusals.append('uci section name %r must be [a-z][a-z0-9_]{0,14}' % uci)
    vlan = int(p.get('vlan', 0) or 0)
    if not 2 <= vlan <= 4094:
        refusals.append('vlan must be 2..4094 (got %s)' % vlan)
    try:
        net = ipaddress.ip_network(p.get('cidr', ''), strict=True)
    except ValueError:
        net, _ = None, refusals.append('cidr %r is not a valid network' % p.get('cidr', ''))
    ssid = p.get('ssid', '')
    if ssid and not 1 <= len(ssid) <= 32:
        refusals.append('ssid must be 1..32 characters')
    if refusals:
        return '', refusals
    dev = p.get('device', 'eth1') + '.%d' % vlan
    gw = str(list(net.hosts())[0])
    lines = ['#!/bin/sh', '# Polari hardware app UCI profile %r — rendered from HardwareAppDefinition; idempotent' % profile, 'set -e',
             'modprobe 8021q 2>/dev/null || true',
             "uci -q delete network.%s 2>/dev/null || true" % uci,
             "uci set network.%s=interface" % uci, "uci set network.%s.proto='static'" % uci,
             "uci set network.%s.device='%s'" % (uci, dev), "uci set network.%s.ipaddr='%s'" % (uci, gw),
             "uci set network.%s.netmask='%s'" % (uci, net.netmask), 'uci commit network',
             "uci -q delete dhcp.%s 2>/dev/null || true" % uci, "uci set dhcp.%s=dhcp" % uci,
             "uci set dhcp.%s.interface='%s'" % (uci, uci), "uci set dhcp.%s.start='%s'" % (uci, p.get('dhcp_start', 50)),
             "uci set dhcp.%s.limit='%s'" % (uci, p.get('dhcp_limit', 200)), "uci set dhcp.%s.leasetime='%s'" % (uci, p.get('dhcp_leasetime', '12h')),
             'uci commit dhcp',
             "uci -q delete firewall.%s 2>/dev/null || true" % uci, 'uci add firewall zone',
             "uci set firewall.@zone[-1].name='%s'" % uci, "uci set firewall.@zone[-1].network='%s'" % uci,
             "uci set firewall.@zone[-1].input='ACCEPT'", "uci set firewall.@zone[-1].output='ACCEPT'"]
    if profile == 'relay':
        lines += ["uci set firewall.@zone[-1].forward='ACCEPT'   # relay: the new segment IS the isle, extended",
                  'uci add firewall forwarding', "uci set firewall.@forwarding[-1].src='%s'" % uci, "uci set firewall.@forwarding[-1].dest='lan'",
                  'uci add firewall forwarding', "uci set firewall.@forwarding[-1].src='lan'", "uci set firewall.@forwarding[-1].dest='%s'" % uci,
                  '# the Reticulum TCP bearer for the extension app (hardware-extension-app reticulum)',
                  'uci add firewall rule', "uci set firewall.@rule[-1].name='reticulum-bearer'", "uci set firewall.@rule[-1].src='%s'" % uci,
                  "uci set firewall.@rule[-1].dest_port='%s'" % p.get('reticulum_port', 4242), "uci set firewall.@rule[-1].proto='tcp'", "uci set firewall.@rule[-1].target='ACCEPT'"]
    else:
        lines += ["uci set firewall.@zone[-1].forward='REJECT'   # guestnet: isolated from the isle",
                  '# guests reach the internet through the WAN zone only']
        lines += ['uci add firewall forwarding', "uci set firewall.@forwarding[-1].src='%s'" % uci, "uci set firewall.@forwarding[-1].dest='wan'"]
        for i, host in enumerate(p.get('allow_hosts', [])):
            lines += ['uci add firewall rule', "uci set firewall.@rule[-1].name='guest-allow-%d'" % i, "uci set firewall.@rule[-1].src='%s'" % uci,
                      "uci set firewall.@rule[-1].dest='lan'", "uci set firewall.@rule[-1].dest_ip='%s'" % host, "uci set firewall.@rule[-1].target='ACCEPT'"]
    lines += ['uci commit firewall']
    if ssid:
        lines += ["uci -q delete wireless.%s 2>/dev/null || true" % uci, "uci set wireless.%s=wifi-iface" % uci,
                  "uci set wireless.%s.device='%s'" % (uci, p.get('radio', 'radio0')), "uci set wireless.%s.network='%s'" % (uci, uci),
                  "uci set wireless.%s.mode='ap'" % uci, "uci set wireless.%s.ssid='%s'" % (uci, ssid),
                  "uci set wireless.%s.encryption='%s'" % (uci, p.get('encryption', 'sae-mixed')),
                  "uci set wireless.%s.key=\"$(cat /etc/isle-mesh/%s.psk)\"   # the PSK is deploy-time input, never rendered" % (uci, uci)]
        if profile == 'guestnet':
            lines.append("uci set wireless.%s.isolate='1'   # client isolation" % uci)
        lines += ["uci set wireless.%s.disabled='0'" % (p.get('radio', 'radio0')), 'uci commit wireless']
    lines += ['/etc/init.d/network restart || true', '/etc/init.d/dnsmasq restart || true', '/etc/init.d/firewall restart || true',
              'wifi reload 2>/dev/null || true' if ssid else 'true', '']
    return '\n'.join(lines), []
