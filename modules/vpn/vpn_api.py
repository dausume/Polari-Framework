"""
@module vpn.vpn_api

VpnAPI: the /api/vpn read surface, the proposal inbox
(`POST /api/vpn/proposals` — the ONLY write a client can make), and
the acceptor for the isle's VPN state, `POST /api/islemesh/ingest/vpn`
(the islemesh family: replace-per-device, receipts, the mock flag real
data never carries).

THE CONTRACT the isle side (Isle-Mesh, isle-core) pushes — every
field optional except `device`; no key material anywhere or the whole
payload is refused:

  {"device": "<isle hostname>", "mock_network": false,
   "schema_version": "1",
   "app": {"name": "isle-vpn", "kind": "<one of the ten kinds>",
           "version": "", "config_api": "<isle-local url>",
           "status": "up"},
   "networks": [{"network_name", "mode", "cidr", "listen_port",
                 "interface", "dns_suffix", "mtu", "forward_allowed",
                 "masquerade", "preshared_default", "status"}],
   "peers":    [{"network_name", "peer_name", "kind", "public_key",
                 "address", "endpoint", "allowed_ips": [],
                 "persistent_keepalive_s", "has_preshared",
                 "last_handshake", "rx_bytes", "tx_bytes", "status",
                 "remote_device"}],   # remote_device == device marks
                                       # the isle's OWN entry
   "rules":    [{"network_name", "name", "from_tag", "to_target",
                 "action", "ports", "order"}],
   "links":    [{"network_name", "remote_device", "remote_network",
                 "gateway_peer", "remote_cidrs": [], "agreement_id",
                 "relay_kind", "status", "arch_name"}],
   "exposures":[{"app_name", "network_name", "role", "status"}],
   "proposals":[{"id": "vp-…", "status": "applied|rejected",
                 "applied_by": "<operator>", "applied_at": "<iso>",
                 "note": ""}]}

A gateway-kind `app.kind` upserts the device's IsleEngine row
(provides `vpn-gateway`) — what makes the `.vpn` rung available
(§7.2). A proposal flips status ONLY through this push and ONLY with
`applied_by` set (D9).

@consumers
  - polariServer (instantiated next to IsleMeshAPI when vpn is available)
  - polari-cli scripts/vpn.sh (`pol vpn`)
  - Isle-Mesh polari-isle/push-to-polari.sh (the isle's push, I-4)
  - vpn.selftest_vpn (function-level, fake manager)
"""

import hashlib
import json

from datetime import datetime, timezone

from objectTreeDecorators import treeObject, treeObjectInit

from islemesh.islemesh_basis import IsleDevice, IsleEngine, IsleIngestReceipt
from islemesh.islemesh_constants import MOCK_BANNER

from vpn.vpn_basis import (
    VPN_MIRROR_CLASSES, AppVpnExposure, VpnAccessRule, VpnFederationLink,
    VpnNetwork, VpnPeer, VpnProposal,
)
from vpn.vpn_constants import (
    GATEWAY_ENGINE, KIND_INFO, KINDS, LADDER, PROPOSAL_STATUSES,
    PROVIDER_ENGINES, PROVIDER_TITLES, SCHEMA_VERSION, is_gateway_kind,
    label_for_kind, provider_for_kind,
)
from vpn.vpn_engine import (
    forbidden_key_paths, private_key_lines, render_access_rules,
    render_for,
)
from vpn.vpn_proposals import mirror_view, propose


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


def _j(value, default):
    try:
        return json.loads(value) if value else default
    except (TypeError, ValueError):
        return default


class VpnAPI(treeObject):
    """isle-vpn mirror + inbox + acceptor."""

    @treeObjectInit
    def __init__(self, polServer):
        self.polServer = polServer
        self.apiName = '/api/vpn'
        if polServer is not None:
            add = polServer.falconServer.add_route
            add('/api/vpn', self, suffix='summary')
            add('/api/vpn/kinds', self, suffix='kinds')
            add('/api/vpn/networks', self, suffix='networks')
            add('/api/vpn/peers', self, suffix='peers')
            add('/api/vpn/rules', self, suffix='rules')
            add('/api/vpn/links', self, suffix='links')
            add('/api/vpn/exposures', self, suffix='exposures')
            add('/api/vpn/proposals', self, suffix='proposals')
            add('/api/vpn/proposals/{pid}', self, suffix='proposal')
            add('/api/vpn/render/{device}/{network}/{peer}', self,
                suffix='render')
            add('/api/vpn/rules/{device}/{network}/render', self,
                suffix='render_rules')
            add('/api/vpn/exposure-options', self,
                suffix='exposure_options')
            add('/api/vpn/matrix', self, suffix='matrix')
            add('/api/vpn/demo', self, suffix='demo')
            add('/api/islemesh/ingest/vpn', self, suffix='ingest_vpn')
            # vpn-3: the trust bridge
            add('/api/vpn/join-request', self, suffix='join_request')
            add('/api/vpn/agreements', self, suffix='agreements')
        self.register_trust_bridge()

    def register_trust_bridge(self):
        """vpn-3: react to PeerAgreement approve / deny / revoke. The
        MODULE-LEVEL listener is registered, and once: polariServer
        constructs its endpoints on every boot cycle, so a bound method
        per instance would stack up (61 listeners = 61 tear-downs per
        revoke on the first live run)."""
        from polariPeers import agreements_api
        from vpn.vpn_trust import on_agreement_event
        if on_agreement_event not in agreements_api.AGREEMENT_LISTENERS:
            agreements_api.AGREEMENT_LISTENERS.append(on_agreement_event)
        return on_agreement_event

    # ---- vpn-3: join requests + the consent view ---------------------

    def on_post_join_request(self, request, response):
        payload, err = self._payload(request)
        if err:
            return self._refuse(response, err)
        from vpn.vpn_trust import file_join_request
        result, status = file_join_request(self.manager, payload,
                                           save=self._save)
        response.status = status
        response.media = result
        return result

    def on_get_agreements(self, request, response):
        """PeerAgreement rows the bridge owns (requested_role vpn-*),
        each with the proposals that hang off it."""
        from vpn.vpn_trust import proposals_of_agreement
        params = self._params(request)
        out = []
        for a in self._table('PeerAgreement').values():
            role = getattr(a, 'requested_role', '')
            if not role.startswith('vpn-'):
                continue
            if params.get('status') and getattr(a, 'status', '') \
                    != params['status']:
                continue
            aid = getattr(a, 'agreement_id', '')
            out.append({
                'agreement_id': aid, 'direction': getattr(a, 'direction', ''),
                'requester_name': getattr(a, 'requester_name', ''),
                'requester_base_url': getattr(a, 'requester_base_url', ''),
                'requested_role': role, 'status': getattr(a, 'status', ''),
                'scope': getattr(a, 'scope', ''),
                'requested_at': getattr(a, 'requested_at', ''),
                'approved_by': getattr(a, 'approved_by', ''),
                'approved_at': getattr(a, 'approved_at', ''),
                'revoked_at': getattr(a, 'revoked_at', ''),
                'proposals': ', '.join(
                    '%s (%s)' % (getattr(p, 'name', ''),
                                 getattr(p, 'status', ''))
                    for p in proposals_of_agreement(self.manager, aid)),
            })
        out.sort(key=lambda d: d['requested_at'])
        response.media = {'ok': True, 'count': len(out),
                          'knobs': 'POST /api/peers/agreements/{id}/approve '
                                   '| /deny | /revoke',
                          'agreements': out}

    # ---- helpers ----------------------------------------------------

    def _payload(self, request):
        try:
            raw = request.bounded_stream.read()
            return (json.loads(raw) if raw else {}), None
        except Exception as e:  # noqa: BLE001
            return None, 'bad JSON payload: %s' % e

    def _table(self, class_name):
        return (getattr(self.manager, 'objectTables', None)
                or {}).get(class_name, {})

    def _save(self, row):
        db = getattr(self.manager, 'db', None)
        if db is None:
            return
        try:
            db.saveInstanceInDB(row)
        except Exception:  # noqa: BLE001
            pass

    def _delete(self, row):
        db = getattr(self.manager, 'db', None)
        row_id = getattr(row, 'id', None)
        if db is None or not hasattr(db, 'deleteRowsWhere') or not row_id:
            return
        try:
            db.deleteRowsWhere(type(row).__name__, 'id', row_id)
        except Exception as e:  # noqa: BLE001
            print('[vpn] %s id=%s not scrubbed from DB (%s)'
                  % (type(row).__name__, row_id, e), flush=True)

    def _refuse(self, response, error, status='400 Bad Request'):
        response.status = status
        response.media = {'ok': False, 'error': error}

    def _rows(self, class_name, **where):
        out = []
        for row in self._table(class_name).values():
            if all(getattr(row, k, None) == v for k, v in where.items()
                   if v not in (None, '')):
                out.append(row)
        return out

    def _replace_device_rows(self, class_names, device_name):
        for class_name in class_names:
            table = self._table(class_name)
            doomed = [key for key, row in list(table.items())
                      if getattr(row, 'device_name', '') == device_name]
            for key in doomed:
                self._delete(table.pop(key))

    def _new(self, cls, **fields):
        row = cls(manager=self.manager, **fields)
        self._save(row)
        return row

    def _receipt(self, device_name, payload_bytes, counts, is_mock,
                 notes=''):
        sha = hashlib.sha256(payload_bytes).hexdigest()
        return self._new(
            IsleIngestReceipt,
            name='%s/vpn/%s' % (device_name, sha[:12]),
            device_name=device_name, kind='vpn', payload_sha256=sha,
            row_counts_json=json.dumps(counts, sort_keys=True),
            mock_network=bool(is_mock), ingested_at=_now_iso(),
            notes=notes)

    def _any_mock(self):
        for class_name in VPN_MIRROR_CLASSES:
            for row in self._table(class_name).values():
                if getattr(row, 'is_mock', False):
                    return True
        return False

    def _params(self, request):
        return getattr(request, 'params', None) or {}

    def _row_dict(self, row, fields):
        out = {}
        for f in fields:
            out[f] = getattr(row, f, '')
        return out

    # ---- ingest -----------------------------------------------------

    def on_post_ingest_vpn(self, request, response):
        payload, err = self._payload(request)
        if err:
            return self._refuse(response, err)
        return self.ingest(payload, response)

    def ingest(self, payload, response):
        """The acceptor proper (also called in-process by the demo)."""
        device = str((payload or {}).get('device', '') or '').strip()
        if not device:
            return self._refuse(response,
                                "ingest requires 'device' (the isle "
                                "hostname the data describes)")
        is_mock = bool(payload.get('mock_network', False))
        raw = json.dumps(payload, sort_keys=True).encode()
        leaked = forbidden_key_paths(payload)
        if leaked:
            self._receipt(device, raw, {'refused': 1}, is_mock,
                          notes='REFUSED: key material at %s'
                                % ', '.join(leaked))
            return self._refuse(
                response, 'refused: the payload carries key material '
                '(%s) — private and preshared keys never leave the '
                'device; nothing was accepted' % ', '.join(leaked))
        app = payload.get('app') or {}
        app_kind = str(app.get('kind', '') or '').strip()
        if app_kind and app_kind not in KINDS:
            return self._refuse(response, 'unknown app kind %r (one of %s)'
                                % (app_kind, ', '.join(KINDS)))
        provider = provider_for_kind(app_kind) or 'link'
        label = label_for_kind(app_kind)

        # mirror: replace this device's rows wholesale
        self._replace_device_rows(VPN_MIRROR_CLASSES, device)
        counts = {c: 0 for c in VPN_MIRROR_CLASSES}
        peer_counts = {}
        for peer in payload.get('peers') or []:
            if not isinstance(peer, dict):
                continue
            net = str(peer.get('network_name', ''))
            peer_counts[net] = peer_counts.get(net, 0) + 1
            kind = str(peer.get('kind') or 'vpn-link-node')
            self._new(
                VpnPeer,
                name='%s@%s/%s' % (net, device, peer.get('peer_name', '')),
                network_name=net, device_name=device,
                peer_name=str(peer.get('peer_name', '')),
                provider=provider_for_kind(kind) or provider, kind=kind,
                label=label_for_kind(kind),
                public_key=str(peer.get('public_key', '')),
                address=str(peer.get('address', '')),
                endpoint=str(peer.get('endpoint', '')),
                allowed_ips_json=json.dumps(peer.get('allowed_ips') or []),
                persistent_keepalive_s=int(
                    peer.get('persistent_keepalive_s') or 0),
                has_preshared=bool(peer.get('has_preshared', False)),
                last_handshake=str(peer.get('last_handshake', '')),
                rx_bytes=int(peer.get('rx_bytes') or 0),
                tx_bytes=int(peer.get('tx_bytes') or 0),
                status=str(peer.get('status', '')),
                remote_device=str(peer.get('remote_device', '')),
                is_mock=is_mock)
            counts['VpnPeer'] += 1
        for net in payload.get('networks') or []:
            if not isinstance(net, dict):
                continue
            name = str(net.get('network_name', ''))
            self._new(
                VpnNetwork, name='%s@%s' % (name, device),
                network_name=name, device_name=device, provider=provider,
                kind=app_kind, label=label,
                mode=str(net.get('mode') or 'mesh'),
                cidr=str(net.get('cidr', '')),
                listen_port=int(net.get('listen_port') or 0),
                interface=str(net.get('interface') or 'wg-arch'),
                dns_suffix=str(net.get('dns_suffix') or '.vpn'),
                mtu=int(net.get('mtu') or 1420),
                forward_allowed=bool(net.get('forward_allowed', False)),
                masquerade=bool(net.get('masquerade', False)),
                preshared_default=bool(net.get('preshared_default', False)),
                peer_count=peer_counts.get(name, 0),
                status=str(net.get('status', '')),
                last_pushed=_now_iso(), is_mock=is_mock,
                notes=str(net.get('notes', '')))
            counts['VpnNetwork'] += 1
        for i, rule in enumerate(payload.get('rules') or []):
            if not isinstance(rule, dict):
                continue
            net = str(rule.get('network_name', ''))
            self._new(
                VpnAccessRule,
                name='%s@%s/rule/%s' % (net, device,
                                        rule.get('name') or i),
                network_name=net, device_name=device, provider=provider,
                kind=app_kind, label=label,
                from_tag=str(rule.get('from_tag', '')),
                to_target=str(rule.get('to_target', '')),
                action=str(rule.get('action') or 'allow'),
                ports=str(rule.get('ports', '')),
                order=int(rule.get('order') or i), is_mock=is_mock)
            counts['VpnAccessRule'] += 1
        for link in payload.get('links') or []:
            if not isinstance(link, dict):
                continue
            net = str(link.get('network_name', ''))
            self._new(
                VpnFederationLink,
                name='%s@%s->%s' % (net, device, link.get('remote_device', '')),
                network_name=net, device_name=device, provider=provider,
                kind=app_kind, label=label,
                remote_device=str(link.get('remote_device', '')),
                remote_network=str(link.get('remote_network', '')),
                gateway_peer=str(link.get('gateway_peer', '')),
                remote_cidrs_json=json.dumps(link.get('remote_cidrs') or []),
                agreement_id=str(link.get('agreement_id', '')),
                relay_kind=str(link.get('relay_kind') or 'blind'),
                status=str(link.get('status') or 'pending'),
                arch_name=str(link.get('arch_name', '')), is_mock=is_mock)
            counts['VpnFederationLink'] += 1
        for exp in payload.get('exposures') or []:
            if not isinstance(exp, dict):
                continue
            app_name = str(exp.get('app_name', ''))
            self._new(
                AppVpnExposure, name='%s@%s.vpn' % (app_name, device),
                device_name=device, app_name=app_name,
                network_name=str(exp.get('network_name', '')),
                provider=provider, kind=app_kind, label=label,
                vpn_name='%s.vpn' % app_name,
                role=str(exp.get('role') or 'server'),
                status=str(exp.get('status') or 'active'), is_mock=is_mock)
            counts['AppVpnExposure'] += 1

        # the gateway engine (what makes .vpn available) — replace
        engine_table = self._table('IsleEngine')
        for key, row in list(engine_table.items()):
            if getattr(row, 'device_name', '') == device \
                    and getattr(row, 'provides', '') == GATEWAY_ENGINE:
                self._delete(engine_table.pop(key))
        if is_gateway_kind(app_kind):
            self._new(
                IsleEngine,
                name='%s@%s' % (app.get('name') or 'isle-vpn', GATEWAY_ENGINE),
                app_name=str(app.get('name') or 'isle-vpn'),
                device_name=device, provides=GATEWAY_ENGINE,
                url=str(app.get('config_api', '')), bound=True,
                bound_to='vpn:.vpn rung', is_mock=is_mock,
                notes='%s (%s) — config API isle-local only'
                      % (KIND_INFO[app_kind]['title'],
                         PROVIDER_ENGINES[provider]))
            counts['IsleEngine'] = 1

        # proposals: the ONLY path that flips proposed -> applied|rejected
        applied, proposal_errors = [], []
        for item in payload.get('proposals') or []:
            if not isinstance(item, dict):
                continue
            pid = str(item.get('id', '') or item.get('name', ''))
            status = str(item.get('status', ''))
            by = str(item.get('applied_by', '') or '').strip()
            row = next((r for r in self._table('VpnProposal').values()
                        if getattr(r, 'name', '') == pid), None)
            if row is None:
                proposal_errors.append('%s: no such proposal' % pid)
                continue
            if getattr(row, 'device_name', '') != device:
                proposal_errors.append('%s: belongs to %s, not %s'
                                       % (pid, row.device_name, device))
                continue
            if status not in ('applied', 'rejected'):
                proposal_errors.append('%s: status must be applied or '
                                       'rejected' % pid)
                continue
            if not by:
                proposal_errors.append('%s: applied_by (the operator) is '
                                       'required — an anonymous apply is '
                                       'refused' % pid)
                continue
            row.status = status
            row.applied_by = by
            row.applied_at = str(item.get('applied_at') or _now_iso())
            if item.get('note'):
                row.note = str(item['note'])
            self._save(row)
            applied.append(pid)
        counts['VpnProposal'] = len(applied)

        # the device row (minimal upsert — the device ingest owns facts)
        dev_row = next((r for r in self._table('IsleDevice').values()
                        if getattr(r, 'name', '') == device), None)
        if dev_row is None:
            dev_row = IsleDevice(name=device, manager=self.manager)
        dev_row.last_seen = _now_iso()
        dev_row.is_mock = is_mock
        self._save(dev_row)

        receipt = self._receipt(device, raw, counts, is_mock,
                                notes='app kind %s' % (app_kind or '-'))
        response.media = {'ok': True, 'device': device, 'counts': counts,
                          'app_kind': app_kind, 'label': label,
                          'proposals_applied': applied,
                          'proposal_errors': proposal_errors,
                          'receipt': receipt.name, 'mock_network': is_mock}
        return response.media

    # ---- proposals ----------------------------------------------------

    def _proposal_dict(self, row):
        d = self._row_dict(row, (
            'name', 'device_name', 'kind', 'provider', 'app_kind', 'label',
            'network_name', 'status', 'proposed_by', 'proposed_at',
            'applied_by', 'applied_at', 'note', 'is_mock'))
        d['payload'] = _j(getattr(row, 'payload_json', '{}'), {})
        return d

    def on_get_proposals(self, request, response):
        params = self._params(request)
        rows = self._rows('VpnProposal',
                          device_name=params.get('device', ''),
                          status=params.get('status', ''),
                          network_name=params.get('network', ''))
        rows.sort(key=lambda r: getattr(r, 'proposed_at', ''))
        response.media = {'ok': True, 'count': len(rows),
                          'proposals': [self._proposal_dict(r)
                                        for r in rows]}

    def on_get_proposal(self, request, response, pid):
        row = next((r for r in self._table('VpnProposal').values()
                    if getattr(r, 'name', '') == pid), None)
        if row is None:
            return self._refuse(response, 'no proposal %r' % pid,
                                '404 Not Found')
        response.media = {'ok': True, 'proposal': self._proposal_dict(row)}

    def on_post_proposals(self, request, response):
        """The one client write: validate + file a proposal. Mirror
        rows are untouched; the isle applies (or rejects) it."""
        payload, err = self._payload(request)
        if err:
            return self._refuse(response, err)
        return self.file_proposal(payload, response)

    def file_proposal(self, payload, response):
        payload = dict(payload or {})
        device = str(payload.pop('device', '') or '').strip()
        kind = str(payload.pop('kind', '') or '').strip()
        proposed_by = str(payload.pop('proposed_by', '') or 'api')
        note = str(payload.pop('note', '') or '')
        result = propose(self.manager, device=device, kind=kind,
                         proposed_by=proposed_by, note=note, **payload)
        if not result['ok']:
            return self._refuse(response, result['message'])
        row_fields = result['proposals'][0]
        row = self._new(VpnProposal, **row_fields)
        response.status = '201 Created'
        response.media = {'ok': True, 'proposal': self._proposal_dict(row),
                          'message': result['message']}
        return response.media

    # ---- read -------------------------------------------------------

    def on_get_kinds(self, request, response):
        kinds = []
        for kind in KINDS:
            info = KIND_INFO[kind]
            kinds.append({
                'kind': kind, 'title': info['title'],
                'line': PROVIDER_TITLES[info['provider']],
                'engine': PROVIDER_ENGINES[info['provider']],
                'label': info['label'] or 'endpoint',
                'carries_subnet': info['carries_subnet'],
                'makes_vpn_rung': info['gateway'],
                'relays': info['relay'], 'can_exit': info['exit'],
                'admits_members': info['authority'],
                'description': info['description']})
        response.media = {'ok': True, 'family': 'isle-vpn',
                          'rule_of_thumb': 'Link when both ends run ours; '
                                           'Bridge when joining a network '
                                           'or an OpenVPN-only box.',
                          'kinds': kinds}

    def _list(self, response, class_name, fields, params, json_fields=()):
        rows = self._rows(class_name, device_name=params.get('device', ''),
                          network_name=params.get('network', ''))
        out = []
        for row in rows:
            d = self._row_dict(row, fields)
            for jf in json_fields:
                d[jf.replace('_json', '')] = _j(getattr(row, jf, ''), [])
                d.pop(jf, None)
            out.append(d)
        out.sort(key=lambda d: (d.get('device_name', ''), d.get('name', '')))
        response.media = {'ok': True, 'count': len(out),
                          'mock_network': self._any_mock(),
                          'banner': MOCK_BANNER if self._any_mock() else '',
                          class_name: out}

    def on_get_networks(self, request, response):
        self._list(response, 'VpnNetwork', (
            'name', 'network_name', 'device_name', 'provider', 'kind',
            'label', 'mode', 'cidr', 'listen_port', 'interface',
            'dns_suffix', 'mtu', 'forward_allowed', 'masquerade',
            'preshared_default', 'peer_count', 'status', 'last_pushed',
            'is_mock', 'notes'), self._params(request))

    def on_get_peers(self, request, response):
        self._list(response, 'VpnPeer', (
            'name', 'network_name', 'device_name', 'peer_name', 'provider',
            'kind', 'label', 'public_key', 'address', 'endpoint',
            'allowed_ips_json', 'persistent_keepalive_s', 'has_preshared',
            'last_handshake', 'rx_bytes', 'tx_bytes', 'status',
            'remote_device', 'is_mock'), self._params(request),
            json_fields=('allowed_ips_json',))

    def on_get_rules(self, request, response):
        self._list(response, 'VpnAccessRule', (
            'name', 'network_name', 'device_name', 'from_tag', 'to_target',
            'action', 'ports', 'order', 'is_mock'), self._params(request))

    def on_get_links(self, request, response):
        self._list(response, 'VpnFederationLink', (
            'name', 'network_name', 'device_name', 'provider', 'kind',
            'label', 'remote_device', 'remote_network', 'gateway_peer',
            'remote_cidrs_json', 'agreement_id', 'relay_kind', 'status',
            'arch_name', 'is_mock'), self._params(request),
            json_fields=('remote_cidrs_json',))

    def on_get_exposures(self, request, response):
        self._list(response, 'AppVpnExposure', (
            'name', 'device_name', 'app_name', 'network_name', 'provider',
            'kind', 'label', 'vpn_name', 'role', 'status', 'is_mock'),
            self._params(request))

    def on_get_summary(self, request, response):
        mock = self._any_mock()
        devices = {}
        for row in self._table('VpnNetwork').values():
            dev = getattr(row, 'device_name', '')
            d = devices.setdefault(dev, {
                'device': dev, 'app_kind': getattr(row, 'kind', ''),
                'label': getattr(row, 'label', '') or 'endpoint',
                'provider': PROVIDER_TITLES.get(getattr(row, 'provider', ''),
                                                ''),
                'networks': 0, 'peers': 0, 'last_pushed': ''})
            d['networks'] += 1
            d['peers'] += int(getattr(row, 'peer_count', 0) or 0)
            d['last_pushed'] = max(d['last_pushed'],
                                   getattr(row, 'last_pushed', ''))
        proposals = list(self._table('VpnProposal').values())
        response.media = {
            'ok': True, 'mock_network': mock,
            'banner': MOCK_BANNER if mock else '',
            'family': 'isle-vpn',
            'authority': 'isle side — Polari mirrors and proposes only',
            'counts': {c: len(self._table(c)) for c in VPN_MIRROR_CLASSES},
            'proposals': {s: sum(1 for p in proposals
                                 if getattr(p, 'status', '') == s)
                          for s in PROPOSAL_STATUSES},
            'isles': sorted(devices.values(), key=lambda d: d['device']),
            'schema_version': SCHEMA_VERSION,
        }

    def on_get_matrix(self, request, response):
        """Per-isle: kind, Blind / Sees traffic, networks, `.vpn` names,
        links — flat rows so the structured panel renders a table."""
        rows = {}
        for net in self._table('VpnNetwork').values():
            dev = getattr(net, 'device_name', '')
            r = rows.setdefault(dev, {
                'isle': dev, 'app_kind': getattr(net, 'kind', ''),
                'title': KIND_INFO.get(getattr(net, 'kind', ''),
                                       {}).get('title', ''),
                'label': getattr(net, 'label', '') or 'endpoint',
                'networks': [], 'peers': 0, 'vpn_names': [],
                'links_active': 0, 'links_pending': 0, 'links_revoked': 0,
                'vpn_rung': 'no', 'is_mock': getattr(net, 'is_mock', False)})
            r['networks'].append('%s (%s)' % (getattr(net, 'network_name', ''),
                                              getattr(net, 'cidr', '')))
            r['peers'] += int(getattr(net, 'peer_count', 0) or 0)
            if is_gateway_kind(getattr(net, 'kind', '')):
                r['vpn_rung'] = 'yes'
        for exp in self._table('AppVpnExposure').values():
            r = rows.get(getattr(exp, 'device_name', ''))
            if r is not None and getattr(exp, 'status', '') != 'revoked':
                r['vpn_names'].append(getattr(exp, 'vpn_name', ''))
        for link in self._table('VpnFederationLink').values():
            r = rows.get(getattr(link, 'device_name', ''))
            if r is not None:
                key = 'links_%s' % getattr(link, 'status', 'pending')
                r[key] = r.get(key, 0) + 1
        matrix = []
        for r in sorted(rows.values(), key=lambda x: x['isle']):
            r['networks'] = ', '.join(r['networks'])
            r['vpn_names'] = ', '.join(r['vpn_names']) or '-'
            matrix.append(r)
        mock = self._any_mock()
        response.media = {'ok': True, 'mock_network': mock,
                          'banner': MOCK_BANNER if mock else '',
                          'matrix': matrix}

    def exposure_options(self, device):
        """The ladder for one isle: which rungs its exposure form may
        offer. `.vpn` appears ONLY with a gateway-kind app (§7.2)."""
        view = mirror_view(self.manager, device)
        gateway_apps = sorted({
            '%s (%s)' % (getattr(r, 'app_name', ''), getattr(r, 'notes', ''))
            for r in self._table('IsleEngine').values()
            if getattr(r, 'device_name', '') == device
            and getattr(r, 'provides', '') == GATEWAY_ENGINE})
        dev = next((r for r in self._table('IsleDevice').values()
                    if getattr(r, 'name', '') == device), None)
        entry = bool(getattr(dev, 'is_entrypoint', False)) if dev else False
        vpn_ok = bool(view['gateway_present'])
        rungs = [
            {'rung': '.isle', 'available': True,
             'why': 'always internal — never crosses'},
            {'rung': '.arch', 'available': False,
             'why': 'not built yet (vpn-4: .arch over the tunnel)'},
            {'rung': '.vpn', 'available': vpn_ok,
             'why': ('gateway-kind app installed: %s'
                     % ', '.join(gateway_apps or ['(via network rows)']))
             if vpn_ok else 'no gateway-kind VPN app on this isle — install '
                            'a Link Gateway / Hub / Exit or a Bridge Server '
                            '/ Span / Exit'},
            {'rung': '.mesh', 'available': False,
             'why': 'Reticulum state relay (ret arc) — no app exposure yet'},
            {'rung': 'web', 'available': entry,
             'why': 'designated entrypoint' if entry
             else 'not a designated entrypoint (isle url entrypoint enable)'},
        ]
        assert [r['rung'] for r in rungs] == list(LADDER)
        options = [r['rung'] for r in rungs if r['available']]
        return {'ok': True, 'device': device, 'options': options,
                'vpn_available': vpn_ok, 'rungs': rungs,
                'networks': sorted(view['networks'])}

    def on_get_exposure_options(self, request, response):
        device = str(self._params(request).get('device', '') or '').strip()
        if not device:
            return self._refuse(response, "'device' is required")
        response.media = self.exposure_options(device)

    # ---- render -------------------------------------------------------

    def _network_dict(self, row):
        return {'network_name': getattr(row, 'network_name', ''),
                'mode': getattr(row, 'mode', 'mesh'),
                'cidr': getattr(row, 'cidr', ''),
                'listen_port': getattr(row, 'listen_port', 0),
                'interface': getattr(row, 'interface', 'wg-arch'),
                'mtu': getattr(row, 'mtu', 1420),
                'forward_allowed': getattr(row, 'forward_allowed', False),
                'masquerade': getattr(row, 'masquerade', False),
                'kind': getattr(row, 'kind', ''),
                'l2': KIND_INFO.get(getattr(row, 'kind', ''), {}).get('l2')}

    def _peer_dict(self, row):
        allowed = _j(getattr(row, 'allowed_ips_json', '[]'), [])
        own = (getattr(row, 'address', '') or '').split('/')[0]
        return {'peer_name': getattr(row, 'peer_name', ''),
                'kind': getattr(row, 'kind', ''),
                'public_key': getattr(row, 'public_key', ''),
                'address': getattr(row, 'address', ''),
                'endpoint': getattr(row, 'endpoint', ''),
                'carried_cidrs': [a for a in allowed
                                  if a.split('/')[0] != own],
                'persistent_keepalive_s': getattr(row,
                                                  'persistent_keepalive_s',
                                                  25),
                'has_preshared': getattr(row, 'has_preshared', False),
                'remote_device': getattr(row, 'remote_device', '')}

    def render(self, device, network, peer):
        net_row = next((r for r in self._table('VpnNetwork').values()
                        if getattr(r, 'device_name', '') == device
                        and getattr(r, 'network_name', '') == network), None)
        if net_row is None:
            return {'ok': False, 'reason': 'no network %s on %s'
                                           % (network, device)}
        peers = [self._peer_dict(r) for r in self._table('VpnPeer').values()
                 if getattr(r, 'device_name', '') == device
                 and getattr(r, 'network_name', '') == network]
        me = next((p for p in peers if p['peer_name'] == peer), None)
        if me is None and peer == 'self':
            me = next((p for p in peers if p['remote_device'] == device),
                      None)
        if me is None:
            return {'ok': False, 'reason': 'no peer %s on %s@%s'
                                           % (peer, network, device)}
        links = [{'gateway_peer': getattr(r, 'gateway_peer', ''),
                  'remote_cidrs': _j(getattr(r, 'remote_cidrs_json', '[]'),
                                     []),
                  'status': getattr(r, 'status', 'pending')}
                 for r in self._table('VpnFederationLink').values()
                 if getattr(r, 'device_name', '') == device
                 and getattr(r, 'network_name', '') == network]
        ca = getattr(self.polServer, 'vpn_ca', None) if self.polServer \
            else None
        result = render_for(self._network_dict(net_row), me, peers, links,
                            ca=ca)
        text = result.get('text', '')
        result['device'] = device
        result['network'] = network
        result['peer'] = me['peer_name']
        result['private_key_present'] = bool(private_key_lines(text))
        result['note'] = ('the PrivateKey line is a placeholder the isle '
                          'app fills from its own key store; this text is '
                          'not applyable as-is (by design)')
        return result

    def on_get_render(self, request, response, device, network, peer):
        result = self.render(device, network, peer)
        if not result.get('ok'):
            response.status = '404 Not Found' if 'no ' in result.get(
                'reason', '') else '409 Conflict'
        response.media = result

    def on_get_render_rules(self, request, response, device, network):
        net_row = next((r for r in self._table('VpnNetwork').values()
                        if getattr(r, 'device_name', '') == device
                        and getattr(r, 'network_name', '') == network), None)
        if net_row is None:
            return self._refuse(response, 'no network %s on %s'
                                % (network, device), '404 Not Found')
        rules = [self._row_dict(r, ('name', 'from_tag', 'to_target',
                                    'action', 'ports', 'order'))
                 for r in self._table('VpnAccessRule').values()
                 if getattr(r, 'device_name', '') == device
                 and getattr(r, 'network_name', '') == network]
        # tags: every peer name -> its cidrs; 'members' -> all /32s
        tag_map = {}
        for r in self._table('VpnPeer').values():
            if getattr(r, 'device_name', '') != device \
                    or getattr(r, 'network_name', '') != network:
                continue
            allowed = _j(getattr(r, 'allowed_ips_json', '[]'), [])
            tag_map[getattr(r, 'peer_name', '')] = allowed
            tag_map.setdefault('members', []).extend(
                a for a in allowed if a.endswith('/32'))
            if getattr(r, 'remote_device', '') == device:
                tag_map['self'] = allowed
        text = render_access_rules(self._network_dict(net_row), rules,
                                   tag_map)
        response.media = {'ok': True, 'device': device, 'network': network,
                          'rules': len(rules), 'text': text}

    # ---- demo -------------------------------------------------------

    def on_post_demo(self, request, response):
        """Run the two-isle acceptance flow in-process (mock-flagged).
        See vpn.vpn_demo.run_demo."""
        from vpn.vpn_demo import run_demo
        response.media = run_demo(self)
