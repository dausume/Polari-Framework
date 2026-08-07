"""
@module islemesh.islemesh_api

IsleMeshAPI: the /api/islemesh surface — the polari-side ACCEPTOR
for isle-mesh's data (mac-1/mac-5 receiving half).

Ingest endpoints take isle's artifacts raw (registry.json, agent
nginx fragments, device facts), parse them (islemesh_parse), and
REPLACE that device's rows — isle stays authoritative; these rows
are polari's accepted copy, and every accept writes an
IsleIngestReceipt.

THE MOCK FLAG (Dustin 2026-08-07): a sender may declare
`"mock_network": true` — a field REAL isle data never carries. Mock
rows are stamped is_mock and the summary answers with a large
MOCK_BANNER so the interface can signal it at the top. Real and
mock rows never mix silently: a real ingest for a device clears
that device's mock rows and vice versa (replace semantics).

Thin Falcon shell — parsing lives in islemesh_parse.

@consumers
  - polariServer (instantiated next to the topology endpoints)
  - polari-cli scripts/isle.sh (`pol isle sync` / `pol isle mock`)
  - islemesh.selftest_islemesh (function-level)
"""

import hashlib
import json
from datetime import datetime, timezone

from objectTreeDecorators import treeObject, treeObjectInit

from islemesh.islemesh_basis import (
    IsleApp, IsleAppService, IsleDevice, IsleIngestReceipt,
    IsleProtocolPermit, IsleUplink, MeshAppRealization,
)
from islemesh.islemesh_constants import (
    AGENT_MODES, CONNECTIVITY_MODES, MOCK_BANNER, UPLINK_KINDS,
)
from islemesh.islemesh_parse import parse_fragments, parse_registry

#: Classes whose rows are per-device replaceable by ingest kind.
_REGISTRY_CLASSES = ('IsleApp', 'IsleAppService')
_FRAGMENT_CLASSES = ('IsleProtocolPermit',)
_DEVICE_CLASSES = ('IsleUplink',)


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


class IsleMeshAPI(treeObject):
    """isle-mesh ingest + read endpoints."""

    @treeObjectInit
    def __init__(self, polServer):
        self.polServer = polServer
        self.apiName = '/api/islemesh'
        if polServer is not None:
            add = polServer.falconServer.add_route
            add('/api/islemesh', self, suffix='summary')
            add('/api/islemesh/ingest/registry', self,
                suffix='ingest_registry')
            add('/api/islemesh/ingest/fragments', self,
                suffix='ingest_fragments')
            add('/api/islemesh/ingest/device', self,
                suffix='ingest_device')
            add('/api/islemesh/matrix', self, suffix='matrix')
            add('/api/islemesh/mock', self, suffix='mock')

    # ---- helpers ----------------------------------------------------

    def _payload(self, request):
        try:
            raw = request.bounded_stream.read()
            return (json.loads(raw) if raw else {}), None
        except Exception as e:
            return None, 'bad JSON payload: %s' % e

    def _table(self, class_name):
        return (getattr(self.manager, 'objectTables', None)
                or {}).get(class_name, {})

    def _save(self, row):
        try:
            self.manager.db.saveInstanceInDB(row)
        except Exception:
            pass

    def _delete(self, row):
        """Tree removal is the caller's pop; this scrubs the DB row
        (the CRUDE-DELETE discipline: deleteRowsWhere by id, failure
        reported not raised — the row would return on restart)."""
        db = getattr(self.manager, 'db', None)
        row_id = getattr(row, 'id', None)
        if db is None or not hasattr(db, 'deleteRowsWhere') \
                or not row_id:
            return
        try:
            db.deleteRowsWhere(type(row).__name__, 'id', row_id)
        except Exception as e:
            print('[islemesh] %s id=%s not scrubbed from DB (%s)'
                  % (type(row).__name__, row_id, e), flush=True)

    def _refuse(self, response, error, status='400 Bad Request'):
        response.status = status
        response.media = {'ok': False, 'error': error}

    def _replace_device_rows(self, class_names, device_name):
        """Drop a device's existing rows of the given classes (the
        replace-per-device semantics — mock or real, the newest
        ingest for a device is THE truth for it)."""
        for class_name in class_names:
            table = self._table(class_name)
            doomed = [key for key, row in list(table.items())
                      if getattr(row, 'device_name', '')
                      == device_name]
            for key in doomed:
                self._delete(table.pop(key))

    #: Fields reset when a device flips mock<->real — a real ingest
    #: must never inherit mock-era facts it didn't supply (and vice
    #: versa).
    _DEVICE_RESET = {'isle_name': '', 'agent_mode': '',
                     'agent_present': False, 'hosts_router': False,
                     'router_running': False,
                     'connectivity_mode': '', 'notes': ''}

    def _upsert_device(self, device_name, is_mock, **fields):
        table = self._table('IsleDevice')
        found = None
        for row in table.values():
            if getattr(row, 'name', '') == device_name:
                found = row
                break
        if found is None:
            found = IsleDevice(name=device_name,
                               manager=self.manager)
        elif bool(getattr(found, 'is_mock', False)) != bool(is_mock):
            for key, default in self._DEVICE_RESET.items():
                setattr(found, key, default)
        found.last_seen = _now_iso()
        found.is_mock = bool(is_mock)
        for key, value in fields.items():
            if value is not None:
                setattr(found, key, value)
        self._save(found)
        return found

    def _receipt(self, device_name, kind, payload_bytes, counts,
                 is_mock, notes=''):
        sha = hashlib.sha256(payload_bytes).hexdigest()
        row = IsleIngestReceipt(
            name='%s/%s/%s' % (device_name, kind, sha[:12]),
            device_name=device_name, kind=kind,
            payload_sha256=sha,
            row_counts_json=json.dumps(counts, sort_keys=True),
            mock_network=bool(is_mock), ingested_at=_now_iso(),
            notes=notes, manager=self.manager)
        self._save(row)
        return row

    def _ingest_header(self, payload, response):
        """Common ingest envelope: device (required) + the mock
        flag real data never carries."""
        device_name = (payload or {}).get('device', '').strip()
        if not device_name:
            self._refuse(response,
                         "ingest requires 'device' (the isle "
                         "hostname the data describes)")
            return None, False
        return device_name, bool((payload or {}).get(
            'mock_network', False))

    # ---- ingest -----------------------------------------------------

    def on_post_ingest_registry(self, request, response):
        payload, err = self._payload(request)
        if err:
            return self._refuse(response, err)
        device_name, is_mock = self._ingest_header(payload, response)
        if device_name is None:
            return
        registry = payload.get('registry')
        if not isinstance(registry, dict):
            return self._refuse(
                response, "ingest requires 'registry' (the parsed "
                "registry.json object)")
        parsed = parse_registry(registry, device_name,
                                is_mock=is_mock)
        self._replace_device_rows(_REGISTRY_CLASSES, device_name)
        for app in parsed['apps']:
            row = IsleApp(manager=self.manager, **{
                key: value for key, value in app.items()
                if key != 'modes'})
            row.modes_json = json.dumps(app['modes'])
            self._save(row)
        for svc in parsed['services']:
            self._save(IsleAppService(manager=self.manager, **svc))
        # A readable registry proves the agent is CONFIGURED, not
        # that its container runs — agent_present stays the device
        # ingest's fact; this notes the registry only.
        self._upsert_device(device_name, is_mock)
        counts = {'IsleApp': len(parsed['apps']),
                  'IsleAppService': len(parsed['services'])}
        receipt = self._receipt(
            device_name, 'registry',
            json.dumps(registry, sort_keys=True).encode(), counts,
            is_mock)
        response.media = {'ok': True, 'counts': counts,
                          'receipt': receipt.name,
                          'mock_network': is_mock}

    def on_post_ingest_fragments(self, request, response):
        payload, err = self._payload(request)
        if err:
            return self._refuse(response, err)
        device_name, is_mock = self._ingest_header(payload, response)
        if device_name is None:
            return
        fragments = payload.get('fragments')
        if not isinstance(fragments, dict):
            return self._refuse(
                response, "ingest requires 'fragments' "
                "({'<app>.conf': '<nginx text>', ...})")
        permits = parse_fragments(fragments, device_name,
                                  is_mock=is_mock)
        self._replace_device_rows(_FRAGMENT_CLASSES, device_name)
        for permit in permits:
            self._save(IsleProtocolPermit(manager=self.manager,
                                          **permit))
        self._upsert_device(device_name, is_mock)
        counts = {'IsleProtocolPermit': len(permits)}
        receipt = self._receipt(
            device_name, 'fragments',
            json.dumps(fragments, sort_keys=True).encode(), counts,
            is_mock)
        response.media = {'ok': True, 'counts': counts,
                          'receipt': receipt.name,
                          'mock_network': is_mock}

    def on_post_ingest_device(self, request, response):
        payload, err = self._payload(request)
        if err:
            return self._refuse(response, err)
        device_name, is_mock = self._ingest_header(payload, response)
        if device_name is None:
            return
        if payload.get('retire'):
            # The device left the mesh (or was ingested under a
            # wrong name): drop its row + everything attributed to
            # it. Receipts stay — they are history.
            table = self._table('IsleDevice')
            doomed = [key for key, row in list(table.items())
                      if getattr(row, 'name', '') == device_name]
            for key in doomed:
                self._delete(table.pop(key))
            self._replace_device_rows(
                _REGISTRY_CLASSES + _FRAGMENT_CLASSES
                + _DEVICE_CLASSES, device_name)
            self._receipt(device_name, 'device', b'retire',
                          {'retired': len(doomed)}, is_mock,
                          notes='device retired')
            response.media = {'ok': True,
                              'retired': bool(doomed)}
            return
        facts = payload.get('facts') or {}
        mode = facts.get('connectivity_mode')
        if mode and mode not in CONNECTIVITY_MODES:
            return self._refuse(
                response, 'unknown connectivity_mode %r (one of '
                '%s)' % (mode, ', '.join(CONNECTIVITY_MODES)))
        agent_mode = facts.get('agent_mode')
        if agent_mode and agent_mode not in AGENT_MODES:
            return self._refuse(
                response, 'unknown agent_mode %r' % agent_mode)
        self._upsert_device(
            device_name, is_mock,
            isle_name=facts.get('isle_name'),
            machine_name=facts.get('machine_name'),
            agent_mode=agent_mode,
            agent_present=facts.get('agent_present'),
            hosts_router=facts.get('hosts_router'),
            router_running=facts.get('router_running'),
            connectivity_mode=mode,
            notes=facts.get('notes'))
        uplinks = payload.get('uplinks') or []
        self._replace_device_rows(_DEVICE_CLASSES, device_name)
        kept = 0
        for uplink in uplinks:
            if not isinstance(uplink, dict):
                continue
            kind = uplink.get('kind', 'ethernet')
            if kind not in UPLINK_KINDS:
                continue
            interface = uplink.get('interface', '')
            self._save(IsleUplink(
                name='%s@%s' % (device_name, interface),
                device_name=device_name, interface=interface,
                kind=kind, link_up=bool(uplink.get('link_up')),
                latency_ms=float(uplink.get('latency_ms') or 0.0),
                jitter_ms=float(uplink.get('jitter_ms') or 0.0),
                loss_pct=float(uplink.get('loss_pct') or 0.0),
                measured_at=uplink.get('measured_at', ''),
                is_mock=is_mock, manager=self.manager))
            kept += 1
        counts = {'IsleDevice': 1, 'IsleUplink': kept}
        receipt = self._receipt(
            device_name, 'device',
            json.dumps(payload, sort_keys=True).encode(), counts,
            is_mock)
        response.media = {'ok': True, 'counts': counts,
                          'receipt': receipt.name,
                          'mock_network': is_mock}

    # ---- mock -------------------------------------------------------

    class _FakeRequest:
        """Internal re-post: wraps a payload as a Falcon-ish
        request for the ingest handlers."""

        def __init__(self, payload):
            body = json.dumps(payload).encode()

            class _Stream:
                def __init__(self, data):
                    self._data = data

                def read(self):
                    return self._data
            self.bounded_stream = _Stream(body)

    def on_post_mock(self, request, response):
        """Seed the built-in MOCK isle network (Dustin 2026-08-07):
        every payload declares mock_network=true, so the summary
        banner lights up. Re-posting is idempotent (replace
        semantics). Real syncs for a device replace its mock rows —
        mock never shadows reality."""
        from islemesh.islemesh_mock import (
            mock_ingests, mock_realizations,
        )

        class _Sink:
            status = '200 OK'
            media = None
        results = []
        for suffix, payload in mock_ingests():
            sink = _Sink()
            handler = getattr(self, 'on_post_ingest_%s' % suffix)
            handler(self._FakeRequest(payload), sink)
            results.append({'kind': suffix,
                            'device': payload.get('device'),
                            'ok': bool((sink.media or {}).get('ok'))})
        # Realizations are model-owned — seeded directly here.
        table = self._table('MeshAppRealization')
        for row in mock_realizations():
            existing = None
            for candidate in table.values():
                if getattr(candidate, 'name', '') == row['name']:
                    existing = candidate
                    break
            if existing is None:
                self._save(MeshAppRealization(manager=self.manager,
                                              **row))
            else:
                for key, value in row.items():
                    setattr(existing, key, value)
                self._save(existing)
        response.media = {'ok': True, 'mock_network': True,
                          'banner': MOCK_BANNER,
                          'ingests': results,
                          'realizations': len(mock_realizations())}

    # ---- read -------------------------------------------------------

    def _any_mock(self):
        for class_name in ('IsleDevice', 'IsleApp',
                           'IsleProtocolPermit', 'IsleUplink'):
            for row in self._table(class_name).values():
                if getattr(row, 'is_mock', False):
                    return True
        return False

    def on_get_summary(self, request, response):
        """The console's first read: counts + freshness + THE mock
        banner (large, at the top — real data never triggers it)."""
        mock = self._any_mock()
        devices = list(self._table('IsleDevice').values())
        last_seen = sorted((getattr(d, 'last_seen', '')
                            for d in devices), reverse=True)
        response.media = {
            'ok': True,
            # The interface's top-of-page signal: '' means real.
            'mock_network': mock,
            'banner': (MOCK_BANNER if mock else ''),
            'counts': {
                class_name: len(self._table(class_name))
                for class_name in (
                    'IsleDevice', 'IsleUplink', 'IsleApp',
                    'IsleAppService', 'MeshAppRealization',
                    'IsleProtocolPermit', 'IsleIngestReceipt')},
            'devices': [
                {'name': getattr(d, 'name', ''),
                 'isle_name': getattr(d, 'isle_name', ''),
                 'agent_present': getattr(d, 'agent_present',
                                          False),
                 'router_running': getattr(d, 'router_running',
                                           False),
                 'connectivity_mode': getattr(
                     d, 'connectivity_mode', ''),
                 'last_seen': getattr(d, 'last_seen', ''),
                 'is_mock': getattr(d, 'is_mock', False)}
                for d in devices],
            'freshest_ingest': (last_seen[0] if last_seen else ''),
        }

    def on_get_matrix(self, request, response):
        """The protocol matrix, pre-grouped for rendering: per
        device, per server_name → protocol/port/upstream. The
        proxies ARE the policy; this is it, readable."""
        mock = self._any_mock()
        matrix = {}
        for row in self._table('IsleProtocolPermit').values():
            device = getattr(row, 'device_name', '')
            matrix.setdefault(device, []).append({
                'server_name': getattr(row, 'server_name', ''),
                'app': getattr(row, 'app_name', ''),
                'port': getattr(row, 'listen_port', 0),
                'protocol': getattr(row, 'protocol', ''),
                'upstream': getattr(row, 'upstream', ''),
                'fragment': getattr(row, 'fragment_ref', ''),
                'is_mock': getattr(row, 'is_mock', False),
            })
        for device in matrix:
            matrix[device].sort(
                key=lambda p: (p['server_name'], p['port']))
        response.media = {'ok': True, 'mock_network': mock,
                          'banner': (MOCK_BANNER if mock else ''),
                          'matrix': matrix}
