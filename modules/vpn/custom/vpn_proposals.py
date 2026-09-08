"""
@module vpn.custom.vpn_proposals

The PROPOSAL half of D9: Polari never configures a VPN — it writes a
VpnProposal row (the isle's inbox) that a local operator applies with
`isle vpn apply <id>`. This module is the validator + row builder
shared by `POST /api/vpn/proposals` and the no-code form solutions
(`propose` is the AnalysisCall callable: fn(manager, **params) ->
{'proposals': [row], 'message': str} — the mealplan form contract).

A proposal is validated against the MIRROR (existing networks / peers
/ gateway presence) so an operator is never handed nonsense, and is
refused outright when it carries any key material (FORBIDDEN_KEYS).
It never mutates a mirror row — the selftest pins that.

@consumers
  - vpn.vpn_api (POST /api/vpn/proposals)
  - the `vpn-propose-*` SolutionDefinitions (vpn_seed) via the
    AnalysisDefinition `vpn-proposal`
  - vpn.vpn_selftest
"""

import json
import re
import uuid

from datetime import datetime, timezone

from vpn.custom.vpn_constants import (
    EXPOSURE_ROLES, GATEWAY_KINDS, KIND_INFO, KINDS, LABEL_ENDPOINT,
    NETWORK_MODES, PROPOSAL_KINDS, PROVIDERS, RELAY_KINDS, RULE_ACTIONS,
    label_for_kind, provider_for_kind,
)
from vpn.custom.vpn_engine import (
    allocate_address, allocate_cidr, allocate_udp_port,
    forbidden_key_paths, is_key_shaped,
)

_SLUG_RE = re.compile(r'^[a-z0-9][a-z0-9\-]{0,62}$')
_CIDR_RE = re.compile(r'^\d{1,3}(\.\d{1,3}){3}/\d{1,2}$')
_ENDPOINT_RE = re.compile(r'^[A-Za-z0-9\.\-\[\]:]+:\d{1,5}$')


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


def new_proposal_id():
    return 'vp-%s' % uuid.uuid4().hex[:12]


def _as_list(value):
    """csv or JSON list or list -> list of stripped strings."""
    if value is None or value == '':
        return []
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    text = str(value).strip()
    if text.startswith('['):
        try:
            return [str(v).strip() for v in json.loads(text)
                    if str(v).strip()]
        except ValueError:
            pass
    return [v.strip() for v in text.split(',') if v.strip()]


def _as_bool(value):
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in ('1', 'true', 'yes', 'on')


# ---- the mirror view a validation needs --------------------------------

def _rows(manager, class_name):
    tables = getattr(manager, 'objectTables', None) or {}
    return list((tables.get(class_name) or {}).values())


def mirror_view(manager, device):
    """What the validator needs about one isle, from the mirror rows:
    its networks (name, cidr, port, mode), peers per network
    (name, address, public_key), the docker pools + published ports
    the IsleDevice row reports (the netledger), and whether a
    gateway-kind app is installed (IsleEngine provides vpn-gateway,
    or a VpnNetwork row of gateway kind)."""
    networks = {}
    for row in _rows(manager, 'VpnNetwork'):
        if getattr(row, 'device_name', '') != device:
            continue
        networks[getattr(row, 'network_name', '')] = {
            'cidr': getattr(row, 'cidr', ''),
            'listen_port': getattr(row, 'listen_port', 0),
            'mode': getattr(row, 'mode', 'mesh'),
            'provider': getattr(row, 'provider', 'link'),
            'kind': getattr(row, 'kind', ''),
        }
    peers = {}
    for row in _rows(manager, 'VpnPeer'):
        if getattr(row, 'device_name', '') != device:
            continue
        peers.setdefault(getattr(row, 'network_name', ''), []).append({
            'peer_name': getattr(row, 'peer_name', ''),
            'address': getattr(row, 'address', ''),
            'public_key': getattr(row, 'public_key', ''),
        })
    pools, ports = [], []
    for row in _rows(manager, 'IsleDevice'):
        if getattr(row, 'name', '') == device:
            try:
                pools = json.loads(getattr(row, 'pools_json', '[]') or '[]')
                ports = json.loads(getattr(row, 'ports_json', '[]') or '[]')
            except ValueError:
                pools, ports = [], []
            break
    gateway = any(
        getattr(row, 'device_name', '') == device
        and getattr(row, 'provides', '') == 'vpn-gateway'
        for row in _rows(manager, 'IsleEngine')) or any(
        n['kind'] in GATEWAY_KINDS for n in networks.values())
    all_cidrs = [getattr(r, 'cidr', '') for r in _rows(manager, 'VpnNetwork')]
    return {'networks': networks, 'peers': peers, 'pools': pools,
            'ports': ports, 'gateway_present': gateway,
            'all_cidrs': all_cidrs}


# ---- validation per kind ------------------------------------------------

def validate_proposal(kind, payload, view):
    """(problems, normalized). `view` = mirror_view(...). Empty
    problems = the proposal is sound; `normalized` is what the row
    stores (allocations filled in, lists as lists, knobs as bools)."""
    problems = []
    p = dict(payload or {})
    leaked = forbidden_key_paths(p)
    if leaked:
        return (['refused: key material in the proposal (%s) — private '
                 'and preshared keys are made on the device and never '
                 'travel' % ', '.join(leaked)], {})
    if kind not in PROPOSAL_KINDS:
        return (['unknown proposal kind %r (one of %s)'
                 % (kind, ', '.join(PROPOSAL_KINDS))], {})
    networks = view.get('networks', {})
    out = {}

    def need(field, label=None):
        value = str(p.get(field, '') or '').strip()
        if not value:
            problems.append('%s is required' % (label or field))
        return value

    if kind == 'network':
        name = need('network_name')
        if name and not _SLUG_RE.match(name):
            problems.append('network_name must be a slug (a-z, 0-9, -)')
        if name in networks:
            problems.append('network %r already exists on this isle '
                            '— propose a peer or a rule instead' % name)
        provider = str(p.get('provider') or 'link').strip()
        if provider not in PROVIDERS:
            problems.append('provider must be one of %s'
                            % ', '.join(PROVIDERS))
        app_kind = str(p.get('app_kind') or '').strip()
        if app_kind not in KINDS:
            problems.append('app_kind must be one of the ten kinds '
                            '(GET /api/vpn/kinds)')
        elif provider_for_kind(app_kind) != provider:
            problems.append('app_kind %s is not a %s kind'
                            % (app_kind, provider))
        mode = str(p.get('mode') or 'mesh').strip()
        if mode not in NETWORK_MODES:
            problems.append('mode must be one of %s'
                            % ', '.join(NETWORK_MODES))
        cidr = str(p.get('cidr') or '').strip()
        if cidr and not _CIDR_RE.match(cidr):
            problems.append('cidr %r is not A.B.C.D/N' % cidr)
        if not cidr:
            cidr = allocate_cidr(
                view.get('all_cidrs', [])
                + [pl.get('cidr', '') for pl in view.get('pools', [])])
            if cidr is None:
                problems.append('address plan exhausted (10.60.0.0/16)')
        port = p.get('listen_port') or 0
        try:
            port = int(port)
        except (TypeError, ValueError):
            problems.append('listen_port must be an integer')
            port = 0
        if not port:
            port = allocate_udp_port(
                view.get('ports', [])
                + [{'port': n['listen_port']} for n in networks.values()])
            if port is None:
                problems.append('no free UDP port in the ledger window')
        out = {'network_name': name, 'provider': provider,
               'app_kind': app_kind, 'mode': mode, 'cidr': cidr,
               'listen_port': port,
               'forward_allowed': _as_bool(p.get('forward_allowed')),
               'masquerade': _as_bool(p.get('masquerade')),
               'preshared_default': _as_bool(p.get('preshared_default')),
               'mtu': int(p.get('mtu') or 1420)}
        if out['masquerade'] and not KIND_INFO.get(app_kind, {}).get('exit'):
            problems.append('masquerade needs an exit kind (vpn-link-exit '
                            '/ vpn-bridge-exit); %s cannot exit' % app_kind)

    elif kind == 'peer':
        net = need('network_name')
        if net and net not in networks:
            problems.append('no network %r on this isle (propose the '
                            'network first)' % net)
        peer_name = need('peer_name')
        if peer_name and not _SLUG_RE.match(peer_name):
            problems.append('peer_name must be a slug')
        existing = view.get('peers', {}).get(net, [])
        if any(e['peer_name'] == peer_name for e in existing):
            problems.append('peer %r already exists on %s' % (peer_name, net))
        peer_kind = str(p.get('kind') or 'vpn-link-node').strip()
        if peer_kind not in KINDS:
            problems.append('kind must be one of the ten kinds')
        pub = need('public_key')
        if pub and not is_key_shaped(pub):
            problems.append('public_key must be a 44-char base64 key')
        if any(e['public_key'] == pub for e in existing):
            problems.append('that public key is already a peer on %s' % net)
        address = str(p.get('address') or '').strip()
        if net in networks and not address:
            address = allocate_address(
                networks[net]['cidr'],
                [e['address'] for e in existing]) or ''
            if not address:
                problems.append('network %s is full' % net)
        endpoint = str(p.get('endpoint') or '').strip()
        if endpoint and not _ENDPOINT_RE.match(endpoint):
            problems.append('endpoint must be host:port')
        carried = _as_list(p.get('carried_cidrs'))
        for c in carried:
            if not _CIDR_RE.match(c):
                problems.append('carried cidr %r is not A.B.C.D/N' % c)
        if carried and not KIND_INFO.get(peer_kind, {}).get('carries_subnet'):
            problems.append('kind %s carries no subnet — drop '
                            'carried_cidrs or use a gateway/peer kind'
                            % peer_kind)
        try:
            keepalive = int(p.get('persistent_keepalive_s') or 25)
        except (TypeError, ValueError):
            keepalive = 25
            problems.append('persistent_keepalive_s must be an integer')
        out = {'network_name': net, 'peer_name': peer_name,
               'kind': peer_kind, 'public_key': pub, 'address': address,
               'endpoint': endpoint, 'carried_cidrs': carried,
               'persistent_keepalive_s': keepalive,
               'has_preshared': _as_bool(p.get('has_preshared')),
               'remote_device': str(p.get('remote_device') or '').strip()}

    elif kind == 'rule':
        net = need('network_name')
        if net and net not in networks:
            problems.append('no network %r on this isle' % net)
        action = str(p.get('action') or 'allow').strip()
        if action not in RULE_ACTIONS:
            problems.append('action must be allow or deny')
        out = {'network_name': net, 'from_tag': need('from_tag'),
               'to_target': need('to_target'), 'action': action,
               'ports': str(p.get('ports') or '').strip(),
               'order': int(p.get('order') or 0)}

    elif kind == 'link':
        net = need('network_name')
        if net and net not in networks:
            problems.append('no network %r on this isle' % net)
        remote_device = need('remote_device')
        remote_network = need('remote_network')
        agreement = need('agreement_id',
                         'agreement_id (an approved PeerAgreement — a '
                         'federation link exists only behind consent)')
        pub = need('remote_gateway_public_key')
        if pub and not is_key_shaped(pub):
            problems.append('remote_gateway_public_key must be a 44-char '
                            'base64 key')
        cidrs = _as_list(p.get('remote_cidrs'))
        if not cidrs:
            problems.append('remote_cidrs is required (what the remote '
                            'gateway carries)')
        for c in cidrs:
            if not _CIDR_RE.match(c):
                problems.append('remote cidr %r is not A.B.C.D/N' % c)
            elif net in networks and networks[net]['cidr'] == c:
                problems.append('remote cidr %s collides with this '
                                'network\'s own cidr' % c)
        relay = str(p.get('relay_kind') or 'blind').strip()
        if relay not in RELAY_KINDS:
            problems.append('relay_kind must be one of %s'
                            % ', '.join(RELAY_KINDS))
        endpoint = str(p.get('remote_endpoint') or '').strip()
        if endpoint and not _ENDPOINT_RE.match(endpoint):
            problems.append('remote_endpoint must be host:port')
        out = {'network_name': net, 'remote_device': remote_device,
               'remote_network': remote_network, 'agreement_id': agreement,
               'remote_gateway_public_key': pub, 'remote_cidrs': cidrs,
               'relay_kind': relay, 'remote_endpoint': endpoint,
               'arch_name': str(p.get('arch_name') or '').strip(),
               'gateway_peer': str(p.get('gateway_peer')
                                   or ('%s-gw' % remote_device)).strip()}

    elif kind == 'exposure':
        if not view.get('gateway_present'):
            problems.append('the .vpn rung is not available on this isle '
                            '— no gateway-kind VPN app is installed '
                            '(install a Link Gateway / Hub / Exit or a '
                            'Bridge Server / Span / Exit first)')
        net = need('network_name')
        if net and net not in networks:
            problems.append('no network %r on this isle' % net)
        app = need('app_name')
        role = str(p.get('role') or 'server').strip()
        if role not in EXPOSURE_ROLES:
            problems.append('role must be one of %s'
                            % ', '.join(EXPOSURE_ROLES))
        out = {'network_name': net, 'app_name': app, 'role': role,
               'vpn_name': '%s.vpn' % app if app else ''}

    elif kind == 'revoke':
        target = str(p.get('target') or '').strip()
        if target not in ('peer', 'link', 'exposure'):
            problems.append('target must be peer, link or exposure')
        out = {'target': target, 'name': need('name'),
               'network_name': str(p.get('network_name') or '').strip(),
               'reason': str(p.get('reason') or '').strip()}

    return problems, out


def proposal_row(device, kind, normalized, proposed_by='', note='',
                 is_mock=False):
    """The VpnProposal row dict (GenerateEvent-ready: `name` is the
    id, dedupe by name)."""
    app_kind = normalized.get('app_kind') or normalized.get('kind') or ''
    provider = provider_for_kind(app_kind) or normalized.get('provider') \
        or 'link'
    return {
        'name': new_proposal_id(), 'device_name': device, 'kind': kind,
        'provider': provider, 'app_kind': app_kind,
        'label': label_for_kind(app_kind) if app_kind else LABEL_ENDPOINT,
        'network_name': normalized.get('network_name', ''),
        'payload_json': json.dumps(normalized, sort_keys=True),
        'status': 'proposed', 'proposed_by': proposed_by,
        'proposed_at': _now_iso(), 'applied_by': '', 'applied_at': '',
        'note': note, 'is_mock': bool(is_mock),
    }


def propose(manager, device='', kind='', proposed_by='', note='',
            **fields):
    """The AnalysisCall callable behind every propose form and the
    API: validate against the mirror, return the row to write and a
    plain-words message. Refusals return proposals=[] and the
    problems in the message (the form shows it; nothing is written)."""
    device = (device or '').strip()
    if not device:
        return {'ok': False, 'proposals': [],
                'message': 'Refused: device (the isle that will apply '
                           'this) is required.'}
    view = mirror_view(manager, device)
    problems, normalized = validate_proposal(kind, fields, view)
    if problems:
        return {'ok': False, 'proposals': [],
                'message': 'Refused: ' + '; '.join(problems)}
    row = proposal_row(device, kind, normalized, proposed_by=proposed_by,
                       note=note, is_mock=_as_bool(fields.get('mock_network')))
    what = {
        'network': 'network %s (%s, %s, %s, port %s)' % (
            normalized.get('network_name'), normalized.get('app_kind'),
            normalized.get('mode'), normalized.get('cidr'),
            normalized.get('listen_port')),
        'peer': 'peer %s on %s at %s' % (
            normalized.get('peer_name'), normalized.get('network_name'),
            normalized.get('address')),
        'rule': 'rule %s -> %s %s on %s' % (
            normalized.get('from_tag'), normalized.get('to_target'),
            normalized.get('action'), normalized.get('network_name')),
        'link': 'federation link %s -> %s/%s (%s relay, agreement %s)' % (
            normalized.get('network_name'), normalized.get('remote_device'),
            normalized.get('remote_network'), normalized.get('relay_kind'),
            normalized.get('agreement_id')),
        'exposure': 'exposure %s on %s (role %s)' % (
            normalized.get('vpn_name'), normalized.get('network_name'),
            normalized.get('role')),
        'revoke': 'revoke %s %s' % (normalized.get('target'),
                                    normalized.get('name')),
    }[kind]
    return {'ok': True, 'proposals': [row],
            'message': 'Proposed %s for %s. Apply on the isle with '
                       '`isle vpn apply %s` — nothing changes until an '
                       'operator there does.' % (what, device, row['name'])}
