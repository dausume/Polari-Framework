"""
@module vpn.custom.vpn_provision

The Debian-guest provisioner for the Bridge (OpenVPN-based) guests:
vpn-bridge-server and vpn-bridge-exit. Called by the hardwareapps render
API through the `provisioner` dotted ref (printcam idiom): returns
(script, refusals). The script is applied INSIDE the guest by `isle vm`
after define/start — idempotent.

What it does: installs openvpn (Debian package, GPLv2 — driven, never
embedded, D13) + easy-rsa, builds the CA on the guest's own disk (never
rendered, never pushed), writes server.conf from the knobs, enables the
management interface on 127.0.0.1 only (the analysis/security wrappers
talk to it; nothing outside the guest can), and leaves the exit knob
OFF unless `exit_enabled` is true. Pure.
"""
import ipaddress
import json


def _params(defn):
    raw = defn.get('uci_params_json', '{}') if isinstance(defn, dict) else getattr(defn, 'uci_params_json', '{}')
    try:
        return json.loads(raw or '{}')
    except ValueError:
        return None


def render_provision(defn):
    name = defn.get('name', '') if isinstance(defn, dict) else getattr(defn, 'name', '')
    p = _params(defn)
    refusals = []
    if p is None:
        return '', ['uci_params_json is not JSON']
    try:
        net = ipaddress.ip_network(p.get('cidr', ''), strict=True)
    except ValueError:
        refusals.append('cidr %r is not a valid network' % p.get('cidr', ''))
    port = int(p.get('listen_port', 0) or 0)
    if not 1 <= port <= 65535:
        refusals.append('listen_port must be 1..65535 (got %s)' % port)
    proto = p.get('proto', 'udp')
    if proto not in ('udp', 'tcp'):
        refusals.append("proto must be udp or tcp (got %r)" % proto)
    if refusals:
        return '', refusals
    is_exit = name.endswith('-exit')
    exit_on = bool(p.get('exit_enabled'))
    ca_name = p.get('ca_name', 'isle-bridge-%s' % name)
    lines = ['#!/bin/sh', '# isle-vpn %s — rendered provisioner; idempotent; applied inside the guest by isle vm' % name,
             '# the CA and every key live on THIS disk and never leave it (D9)', 'set -e',
             'export DEBIAN_FRONTEND=noninteractive',
             'dpkg -s openvpn >/dev/null 2>&1 || apt-get install -y --no-install-recommends openvpn easy-rsa',
             'mkdir -p /etc/openvpn/pki && cd /etc/openvpn/pki',
             '[ -d pki ] || (make-cadir . 2>/dev/null || true; ./easyrsa init-pki)',
             '[ -s pki/ca.crt ] || EASYRSA_BATCH=1 EASYRSA_REQ_CN="%s" ./easyrsa build-ca nopass' % ca_name,
             '[ -s pki/issued/server.crt ] || EASYRSA_BATCH=1 ./easyrsa build-server-full server nopass',
             '[ -s pki/dh.pem ] || ./easyrsa gen-dh',
             '[ -s pki/crl.pem ] || EASYRSA_BATCH=1 ./easyrsa gen-crl',
             '[ -s /etc/openvpn/ta.key ] || openvpn --genkey secret /etc/openvpn/ta.key',
             'cat > /etc/openvpn/server/isle.conf <<EOF',
             'port %d' % port, 'proto %s' % proto, 'dev tun',
             'ca /etc/openvpn/pki/pki/ca.crt', 'cert /etc/openvpn/pki/pki/issued/server.crt',
             'key /etc/openvpn/pki/pki/private/server.key', 'dh /etc/openvpn/pki/pki/dh.pem',
             'crl-verify /etc/openvpn/pki/pki/crl.pem', 'tls-auth /etc/openvpn/ta.key 0',
             'server %s %s' % (net.network_address, net.netmask),
             'client-config-dir /etc/openvpn/ccd', 'keepalive 10 60', 'persist-key', 'persist-tun',
             '# the management interface: local only — the analysis/security wrappers talk here, nothing outside the guest can',
             'management 127.0.0.1 7505', 'status /run/openvpn/isle-status.log 10', 'verb 3']
    for route in p.get('push_routes', []) or []:
        try:
            r = ipaddress.ip_network(route, strict=True)
            lines.append('push "route %s %s"' % (r.network_address, r.netmask))
        except ValueError:
            pass
    if is_exit and exit_on:
        lines.append('push "redirect-gateway def1"')
    lines += ['EOF', 'mkdir -p /etc/openvpn/ccd']
    if is_exit:
        lines += ['# exit knob: %s' % ('ON — masquerade to the WAN interface' if exit_on else 'OFF (turn it on from the isle side)'),
                  'sysctl -w net.ipv4.ip_forward=%d >/dev/null' % (1 if exit_on else 0)]
        if exit_on:
            lines += ['WAN=$(ip route show default | awk \'{print $5; exit}\')',
                      'nft list table ip isle_exit >/dev/null 2>&1 || nft add table ip isle_exit',
                      'nft list chain ip isle_exit post >/dev/null 2>&1 || nft add chain ip isle_exit post "{ type nat hook postrouting priority 100; }"',
                      'nft list chain ip isle_exit post | grep -q masquerade || nft add rule ip isle_exit post ip saddr %s oifname "$WAN" masquerade' % net]
    lines += ['systemctl enable --now openvpn-server@isle >/dev/null 2>&1 || systemctl restart openvpn-server@isle',
              'echo "%s: openvpn %s/%d up; CA %s; management 127.0.0.1:7505"' % (name, proto, port, ca_name)]
    return '\n'.join(lines) + '\n', []
