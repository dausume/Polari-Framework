"""
@module vpn.custom.vpn_engine

The VPN ENGINE (vpn-1): pure functions over plain dicts — key
generation (returned ONCE, never stored), address + port allocation
from the islemesh netledger, config rendering for the Link kinds
(node / gateway / hub / exit — mesh and hub modes), the honest
refusals for the Bridge kinds until the suite CA lands, access rules
as nftables text, and federation route injection.

Security invariants this module enforces by construction:
  - nothing here ever renders a private key: a Link conf carries the
    PRIVATE_KEY_PLACEHOLDER token the isle-side app substitutes from
    /etc/isle-mesh/vpn/<network>/private.key at apply time;
  - forwarding / masquerade lines appear ONLY when the network's knob
    is on AND the peer's kind can do it (a node never masquerades);
  - PostUp/PostDown are the HOOK_TOGGLES templates only (D11).

We DRIVE WireGuard and OpenVPN as separate programs (§7.1): this
module produces the text they read; no GPLv2 source is copied here.

@consumers
  - vpn.vpn_api (render endpoint, ingest sanity), vpn.custom.vpn_proposals
  - vpn.custom.vpn_demo (the two-isle acceptance flow)
  - vpn.vpn_selftest
"""

import base64
import os
import re

from islemesh.custom.islemesh_netledger import cidrs_overlap, free_port

from vpn.custom.vpn_constants import (
    ADDRESS_PLAN_PREFIX, DEFAULT_KEEPALIVE_S, DEFAULT_MTU,
    FORBIDDEN_KEYS, KIND_INFO, UDP_PORT_HI, UDP_PORT_LO,
)

#: The token a rendered Link conf carries where wg-quick expects the
#: private key. The isle app replaces it locally; Polari never sees
#: the value. A conf that still carries the token is NOT applyable —
#: that is the point.
PRIVATE_KEY_PLACEHOLDER = '@@DEVICE_PRIVATE_KEY@@'

#: A base64 X25519 key: 32 bytes -> 44 chars ending in '='.
_KEY_RE = re.compile(r'^[A-Za-z0-9+/]{43}=$')
#: A PrivateKey line carrying an actual key (what must never appear).
_PRIVATE_LINE_RE = re.compile(r'PrivateKey\s*=\s*[A-Za-z0-9+/]{43}=',
                              re.IGNORECASE)


# ---- keys -------------------------------------------------------------

def keygen():
    """A fresh X25519 keypair as (private_b64, public_b64) — the
    remote.sh idiom in python. The caller hands the private half to
    the device ONCE and forgets it; nothing in this module stores it.
    Honest RuntimeError when the `cryptography` package is absent."""
    try:
        from cryptography.hazmat.primitives.asymmetric.x25519 import (
            X25519PrivateKey)
        from cryptography.hazmat.primitives import serialization as s
    except Exception as e:  # noqa: BLE001
        raise RuntimeError(
            'keygen needs the python "cryptography" package (or run '
            '`wg genkey` on the device): %s' % e)
    k = X25519PrivateKey.generate()
    priv = k.private_bytes(s.Encoding.Raw, s.PrivateFormat.Raw,
                           s.NoEncryption())
    pub = k.public_key().public_bytes(s.Encoding.Raw,
                                      s.PublicFormat.Raw)
    return (base64.b64encode(priv).decode(),
            base64.b64encode(pub).decode())


def public_key_of(private_b64):
    """Derive the public key from a private one (device-side use)."""
    from cryptography.hazmat.primitives.asymmetric.x25519 import (
        X25519PrivateKey)
    from cryptography.hazmat.primitives import serialization as s
    k = X25519PrivateKey.from_private_bytes(base64.b64decode(private_b64))
    return base64.b64encode(k.public_key().public_bytes(
        s.Encoding.Raw, s.PublicFormat.Raw)).decode()


def opaque_public_key():
    """A shape-valid PUBLIC-looking key for mocks and demos when no
    keypair can be made (random 32 bytes, base64). Never a secret —
    nothing was derived from it."""
    return base64.b64encode(os.urandom(32)).decode()


def is_key_shaped(value):
    return bool(isinstance(value, str) and _KEY_RE.match(value))


def private_key_lines(text):
    """Every line of a conf that carries a REAL private key. An
    empty list is the invariant every render must satisfy."""
    return [ln for ln in (text or '').splitlines()
            if _PRIVATE_LINE_RE.search(ln)]


def forbidden_key_paths(obj, path=''):
    """Dot-paths of every FORBIDDEN_KEYS field found anywhere in a
    payload (dicts/lists, any depth). The acceptor refuses the whole
    payload when this is non-empty."""
    found = []
    if isinstance(obj, dict):
        for key, value in obj.items():
            here = '%s.%s' % (path, key) if path else str(key)
            if str(key).lower().replace('-', '_') in FORBIDDEN_KEYS:
                found.append(here)
            found.extend(forbidden_key_paths(value, here))
    elif isinstance(obj, list):
        for i, value in enumerate(obj):
            found.extend(forbidden_key_paths(value, '%s[%d]' % (path, i)))
    return found


# ---- allocation -------------------------------------------------------

def allocate_cidr(existing_cidrs, prefix=ADDRESS_PLAN_PREFIX, lo=1,
                  hi=255):
    """The next free 10.60.<n>.0/24 (D5) that overlaps none of the
    cidrs already in use (VpnNetwork rows + the device's docker pools
    — the caller passes both). None when the plan is exhausted."""
    taken = [c for c in (existing_cidrs or []) if c]
    for n in range(lo, hi):
        cand = '%s.%d.0/24' % (prefix, n)
        if not any(cidrs_overlap(cand, t) for t in taken):
            return cand
    return None


def _cidr_parts(cidr):
    ip, _, bits = (cidr or '').partition('/')
    parts = ip.split('.')
    if len(parts) != 4:
        return None, None
    try:
        return [int(p) for p in parts], int(bits or 24)
    except ValueError:
        return None, None


def allocate_address(cidr, taken_addresses, start=2):
    """The next free host address in `cidr` as 'A.B.C.n/32'. Host .1
    is reserved for the gateway/hub (start=1 asks for it). Only /24
    networks are planned (D5); other prefixes still work within the
    last octet. None when full."""
    parts, bits = _cidr_parts(cidr)
    if parts is None:
        return None
    taken = {(a or '').split('/')[0] for a in (taken_addresses or [])}
    for n in range(start, 255):
        cand = '%d.%d.%d.%d' % (parts[0], parts[1], parts[2], n)
        if cand not in taken:
            return cand + '/32'
    return None


def allocate_udp_port(published_ports, lo=UDP_PORT_LO, hi=UDP_PORT_HI):
    """A listen port from the islemesh netledger's window: the same
    free_port scan LiveKit's UDP publish uses, so conflicts are the
    ledger's business. `published_ports` = [{port, ...}] as the
    device's IsleDevice.ports_json reports. None when the window is
    full."""
    return free_port(published_ports or [], lo=lo, hi=hi)


# ---- Link (WireGuard-based) rendering ---------------------------------

def _info(kind):
    return KIND_INFO.get(kind, {})


def peers_visible(network, me, peers):
    """Which of `peers` the conf for `me` carries:
      mesh -> every other peer (N-1);
      p2p  -> every other peer (there is one);
      hub  -> a member carries the authority peer(s) only; the
              authority (hub/exit) carries every member.
    Peers never carry themselves."""
    mode = (network or {}).get('mode', 'mesh')
    my_name = (me or {}).get('peer_name', '')
    others = [p for p in (peers or []) if p.get('peer_name') != my_name]
    if mode != 'hub':
        return others
    if _info(me.get('kind', '')).get('authority'):
        return others
    return [p for p in others if _info(p.get('kind', '')).get('authority')]


def federation_routes(links):
    """{gateway_peer: [remote cidrs]} — what a federation link adds to
    its gateway peer's AllowedIPs (routes exchanged, never renumbered).
    Only ACTIVE links inject; a pending or revoked link adds nothing."""
    out = {}
    for link in links or []:
        if link.get('status', 'pending') != 'active':
            continue
        peer = link.get('gateway_peer', '')
        if not peer:
            continue
        out.setdefault(peer, [])
        for cidr in link.get('remote_cidrs') or []:
            if cidr and cidr not in out[peer]:
                out[peer].append(cidr)
    return out


def allowed_ips_for(peer, routes=None):
    """A peer's AllowedIPs: its own /32, the subnets it carries (a
    gateway's isle subnet; a Bridge Peer's foreign subnet), and the
    remote cidrs of any active federation link it fronts."""
    out = []
    own = (peer.get('address') or '').split('/')[0]
    if own:
        out.append(own + '/32')
    for cidr in (peer.get('carried_cidrs') or []):
        if cidr and cidr not in out:
            out.append(cidr)
    for cidr in (routes or {}).get(peer.get('peer_name', ''), []):
        if cidr not in out:
            out.append(cidr)
    return out


def render_hooks(network, me):
    """The templated PostUp/PostDown lines (HOOK_TOGGLES, D11):
      forward    -> only if network.forward_allowed AND me relays;
      masquerade -> only if network.masquerade AND me is an exit kind;
      route-add  -> only for carried cidrs of a gateway (kernel adds
                    AllowedIPs routes itself under wg-quick; the
                    explicit toggle is for Table = off setups).
    Anything else is a comment naming the knob that is off."""
    info = _info(me.get('kind', ''))
    iface = network.get('interface', 'wg-arch')
    up, down = [], []
    if network.get('forward_allowed') and info.get('relay'):
        up.append('PostUp = sysctl -w net.ipv4.ip_forward=1')
        down.append('PostDown = sysctl -w net.ipv4.ip_forward=0')
    else:
        up.append('# forwarding OFF (knob forward_allowed=%s, kind %s '
                  'relays=%s)' % (bool(network.get('forward_allowed')),
                                  me.get('kind', ''),
                                  bool(info.get('relay'))))
    if network.get('masquerade') and info.get('exit'):
        up.append('PostUp = nft add table inet isle_vpn_exit; nft add '
                  'chain inet isle_vpn_exit postrouting { type nat hook '
                  'postrouting priority 100 ; }; nft add rule inet '
                  'isle_vpn_exit postrouting iifname "%s" masquerade'
                  % iface)
        down.append('PostDown = nft delete table inet isle_vpn_exit')
    else:
        up.append('# masquerade OFF (knob masquerade=%s, kind %s '
                  'exit=%s)' % (bool(network.get('masquerade')),
                                me.get('kind', ''), bool(info.get('exit'))))
    return up + down


def render_link_conf(network, me, peers, links=None):
    """A wg-quick style conf for `me` on `network` (Link kinds). The
    PrivateKey line carries PRIVATE_KEY_PLACEHOLDER — the device
    substitutes its own key; Polari never holds it. Returns text."""
    routes = federation_routes(links)
    visible = peers_visible(network, me, peers)
    lines = [
        '# isle-vpn Link conf — %s on %s (kind %s, %s)' % (
            me.get('peer_name', '?'), network.get('network_name', '?'),
            me.get('kind', '?'), _info(me.get('kind', '')).get('label')
            or 'endpoint'),
        '# Rendered by Polari (mirror); applied on the isle by '
        '`isle vpn apply`. The private key is read on the device.',
        '[Interface]',
        'Address = %s' % (me.get('address') or ''),
        'PrivateKey = %s' % PRIVATE_KEY_PLACEHOLDER,
    ]
    if network.get('listen_port') and (
            _info(me.get('kind', '')).get('authority')
            or _info(me.get('kind', '')).get('gateway')
            or network.get('mode') != 'hub'):
        lines.append('ListenPort = %d' % int(network['listen_port']))
    lines.append('MTU = %d' % int(network.get('mtu') or DEFAULT_MTU))
    dns = network.get('dns')
    if dns:
        lines.append('DNS = %s' % dns)
    lines.extend(render_hooks(network, me))
    for peer in visible:
        lines.append('')
        lines.append('[Peer]')
        lines.append('# %s (%s, %s)' % (
            peer.get('peer_name', '?'), peer.get('kind', '?'),
            _info(peer.get('kind', '')).get('label') or 'endpoint'))
        lines.append('PublicKey = %s' % peer.get('public_key', ''))
        if peer.get('has_preshared'):
            lines.append('# PresharedKey: set on the device (never '
                         'rendered here)')
        lines.append('AllowedIPs = %s'
                     % ', '.join(allowed_ips_for(peer, routes)))
        if peer.get('endpoint'):
            lines.append('Endpoint = %s' % peer['endpoint'])
        keepalive = peer.get('persistent_keepalive_s',
                             DEFAULT_KEEPALIVE_S)
        if keepalive:
            lines.append('PersistentKeepalive = %d' % int(keepalive))
    text = '\n'.join(lines) + '\n'
    assert not private_key_lines(text)
    return text


# ---- access rules (nftables text) -------------------------------------

def _resolve_target(target, tag_map):
    """A tag -> its cidr list from tag_map; a cidr -> itself."""
    if not target or target == 'any':
        return ['any']
    if '/' in target:
        return [target]
    return list((tag_map or {}).get(target) or [])


def _ports_expr(ports):
    """'tcp:443,udp:53' -> nft expressions per protocol."""
    out = []
    for item in (ports or '').split(','):
        item = item.strip()
        if not item:
            continue
        proto, _, port = item.partition(':')
        if port:
            out.append('%s dport %s' % (proto, port))
    return out


def render_access_rules(network, rules, tag_map=None):
    """nftables text for one network's VpnAccessRule rows: a forward
    chain with policy DROP (nothing forwards unless allowed) and one
    rule per row, ordered by `order`. A tag no peer resolves is
    rendered as a comment, never silently dropped. The router applies
    this text (isle-side I-2); Polari only renders."""
    iface = network.get('interface', 'wg-arch')
    lines = [
        '# isle-vpn access rules — %s (rendered by Polari, applied by '
        'the router)' % network.get('network_name', '?'),
        'table inet isle_vpn_%s {' % re.sub(
            r'[^a-z0-9_]', '_', network.get('network_name', 'net').lower()),
        '  chain forward {',
        '    type filter hook forward priority 0; policy drop;',
        '    ct state established,related accept',
    ]
    for rule in sorted(rules or [], key=lambda r: r.get('order', 0)):
        verdict = 'accept' if rule.get('action', 'allow') == 'allow' \
            else 'drop'
        sources = _resolve_target(rule.get('from_tag', ''), tag_map)
        targets = _resolve_target(rule.get('to_target', ''), tag_map)
        if not sources or not targets:
            lines.append('    # UNRESOLVED rule %s: from=%r to=%r (no '
                         'peer carries that tag)' % (
                             rule.get('name', '?'), rule.get('from_tag'),
                             rule.get('to_target')))
            continue
        ports = _ports_expr(rule.get('ports', '')) or ['']
        for src in sources:
            for dst in targets:
                for pexpr in ports:
                    parts = ['iifname "%s"' % iface]
                    if src != 'any':
                        parts.append('ip saddr %s' % src)
                    if dst != 'any':
                        parts.append('ip daddr %s' % dst)
                    if pexpr:
                        parts.append(pexpr)
                    parts.append(verdict)
                    lines.append('    ' + ' '.join(parts)
                                 + '  # %s' % rule.get('name', ''))
    lines.extend(['  }', '}'])
    return '\n'.join(lines) + '\n'


# ---- Bridge (OpenVPN-based) rendering — honest until the CA lands --

def _ca_ready(ca):
    """The suite CA path: step-ca issuance (CENTRALIZED_CA_PLAN). Until
    it lands, self-signed roots cannot issue per-client certs both
    sides trust, so Bridge configs are refused with the reason."""
    if not isinstance(ca, dict):
        return False, ('no certificate authority configured — Bridge '
                       'kinds need step-ca issuance (CENTRALIZED_CA_PLAN); '
                       'not built yet')
    if ca.get('mode') != 'step-ca':
        return False, ('CERT_MODE is %r — Bridge kinds refuse until '
                       'CERT_MODE=step-ca issues per-client certificates'
                       % ca.get('mode', ''))
    if not ca.get('ca_cert_path'):
        return False, 'step-ca configured but no ca_cert_path given'
    return True, ''


def render_bridge_server_conf(network, ca=None):
    """OpenVPN-class server.conf text for a Bridge Server / Exit /
    Span. Returns {'ok', 'text', 'reason'}; refuses honestly until
    the CA can issue. Keys/certs are PATHS on the device, never
    contents."""
    ok, reason = _ca_ready(ca)
    if not ok:
        return {'ok': False, 'text': '', 'reason': reason}
    dev = 'tap' if network.get('l2') else 'tun'
    port = int(network.get('listen_port') or 1194)
    proto = network.get('proto', 'udp')
    lines = [
        '# isle-vpn Bridge server — %s (rendered by Polari; applied '
        'on the isle)' % network.get('network_name', '?'),
        'port %d' % port, 'proto %s' % proto, 'dev %s' % dev,
        'ca %s' % ca['ca_cert_path'],
        'cert /etc/isle-mesh/vpn/%s/server.crt' % network.get('network_name'),
        'key /etc/isle-mesh/vpn/%s/server.key' % network.get('network_name'),
        'dh none', 'tls-server', 'tls-version-min 1.3',
        'crl-verify %s' % ca.get('crl_path', '/etc/isle-mesh/vpn/crl.pem'),
        'topology subnet',
        'server %s' % (network.get('cidr', '').replace('/24', ' 255.255.255.0')),
        'keepalive 10 60', 'persist-key', 'persist-tun',
        'management 127.0.0.1 7505',
        'client-config-dir /etc/isle-mesh/vpn/%s/ccd' % network.get('network_name'),
    ]
    if network.get('masquerade') and _info(network.get('kind', '')).get('exit'):
        lines.append('push "redirect-gateway def1"')
    else:
        lines.append('# no redirect-gateway (exit knob off)')
    return {'ok': True, 'text': '\n'.join(lines) + '\n', 'reason': ''}


def render_bridge_client_ovpn(network, client, ca=None):
    """A client .ovpn for a Bridge Client / Peer: refuses until the CA
    can issue; certs are referenced by device path, never inlined."""
    ok, reason = _ca_ready(ca)
    if not ok:
        return {'ok': False, 'text': '', 'reason': reason}
    lines = [
        '# isle-vpn Bridge client — %s on %s' % (
            client.get('peer_name', '?'), network.get('network_name', '?')),
        'client', 'dev %s' % ('tap' if network.get('l2') else 'tun'),
        'proto %s' % network.get('proto', 'udp'),
        'remote %s' % (client.get('endpoint') or 'SERVER:1194').replace(':', ' '),
        'ca %s' % ca['ca_cert_path'],
        'cert /etc/isle-mesh/vpn/%s/client.crt' % network.get('network_name'),
        'key /etc/isle-mesh/vpn/%s/client.key' % network.get('network_name'),
        'remote-cert-tls server', 'tls-version-min 1.3',
        'persist-key', 'persist-tun', 'nobind',
    ]
    return {'ok': True, 'text': '\n'.join(lines) + '\n', 'reason': ''}


def render_for(network, me, peers, links=None, ca=None):
    """Provider dispatch: Link -> conf text; Bridge -> the server or
    client render (or its honest refusal)."""
    kind = me.get('kind', '')
    if _info(kind).get('provider') == 'bridge':
        if _info(kind).get('authority') or _info(kind).get('l2'):
            return render_bridge_server_conf(dict(network, kind=kind), ca)
        return render_bridge_client_ovpn(network, me, ca)
    return {'ok': True, 'text': render_link_conf(network, me, peers, links),
            'reason': ''}
