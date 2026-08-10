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
    IsleApp, IsleAppService, IsleDevice, IsleEngine,
    IsleIngestReceipt, IsleProtocolPermit, IsleUplink,
    MeshAppRealization,
)
from islemesh.islemesh_engines import bind_engine
from islemesh.islemesh_catalog import install_plan, instances_of
from islemesh.islemesh_coherence import assess_topology
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
            add('/api/islemesh/graph', self, suffix='graph')
            add('/api/islemesh/ingest/engine', self,
                suffix='ingest_engine')
            add('/api/islemesh/engines', self, suffix='engines')
            add('/api/islemesh/catalog', self, suffix='catalog')
            add('/api/islemesh/catalog/{entry}', self,
                suffix='catalog_entry')
            add('/api/islemesh/coherence', self, suffix='coherence')
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
        # Same dedup discipline for APPS: a (name, device) pair may
        # appear ONCE — concurrent pushes or deferred-flush
        # resurrection can double-insert; keep the newest.
        app_table = self._table('IsleApp')
        seen_pairs = set()
        doomed_apps = []
        for key, row in sorted(list(app_table.items()),
                               reverse=True):
            pair = (getattr(row, 'name', ''),
                    getattr(row, 'device_name', ''))
            if pair in seen_pairs:
                doomed_apps.append(key)
            else:
                seen_pairs.add(pair)
        for key in doomed_apps:
            self._delete(app_table.pop(key))
        # Referential sweep: a service must belong to a live app AND
        # carry its device (deviceless rows are pre-schema orphans or
        # restart-flush resurrections — every legit row has one). A
        # name may appear ONCE: replace-then-insert guarantees it,
        # resurrected duplicates from deferred sqlite flushes break
        # it, so dedup keeps the newest.
        app_names = {getattr(row, 'name', '')
                     for row in self._table('IsleApp').values()}
        svc_table = self._table('IsleAppService')
        seen_names = set()
        orphans = []
        for key, row in sorted(list(svc_table.items()),
                               reverse=True):
            svc_name = getattr(row, 'name', '')
            if (getattr(row, 'app_name', '') not in app_names
                    or not getattr(row, 'device_name', '')
                    or svc_name in seen_names):
                orphans.append(key)
            else:
                seen_names.add(svc_name)
        for key in orphans:
            self._delete(svc_table.pop(key))
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
        # exposures: a device may report its outside doors + whether
        # it is a designated entrypoint (the URL-manager surface)
        exposures = payload.get('exposures')
        exposures_json = (json.dumps(exposures)
                          if isinstance(exposures, list) else None)
        # network resource ledger (pools + published ports)
        net = payload.get('net') or {}
        pools = net.get('pools')
        ports = net.get('ports')
        pools_json = (json.dumps(pools)
                      if isinstance(pools, list) else None)
        ports_json = (json.dumps(ports)
                      if isinstance(ports, list) else None)
        self._upsert_device(
            device_name, is_mock,
            isle_name=facts.get('isle_name'),
            machine_name=facts.get('machine_name'),
            agent_mode=agent_mode,
            agent_present=facts.get('agent_present'),
            hosts_router=facts.get('hosts_router'),
            router_running=facts.get('router_running'),
            connectivity_mode=mode,
            is_entrypoint=facts.get('is_entrypoint'),
            exposures_json=exposures_json,
            pools_json=pools_json,
            ports_json=ports_json,
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

    # ---- engines (§20.4) --------------------------------------------

    def on_post_ingest_engine(self, request, response):
        """An isle app declares it provides a polari engine. Record
        the IsleEngine row AND bind it into the consuming module's
        provider config (odoo → OdooInstanceConfig.base_url). Absent
        consumer = recorded available-but-unbound (honest)."""
        payload, err = self._payload(request)
        if err:
            return self._refuse(response, err)
        device_name, is_mock = self._ingest_header(payload, response)
        if device_name is None:
            return
        app_name = (payload or {}).get('app', '').strip()
        provides = (payload or {}).get('provides', '').strip()
        url = (payload or {}).get('url', '').strip()
        if not (app_name and provides and url):
            return self._refuse(
                response, "engine ingest requires 'app', "
                "'provides', and 'url'")
        bound, bound_to, note = bind_engine(
            self.manager, app_name, provides, url, self._save)
        key = '%s@%s' % (app_name, provides)
        table = self._table('IsleEngine')
        row = None
        for candidate in table.values():
            if getattr(candidate, 'name', '') == key:
                row = candidate
                break
        if row is None:
            row = IsleEngine(name=key, manager=self.manager)
        row.app_name = app_name
        row.device_name = device_name
        row.provides = provides
        row.url = url
        row.bound = bound
        row.bound_to = bound_to
        row.is_mock = is_mock
        row.notes = note
        self._save(row)
        self._receipt(device_name, 'engine',
                      json.dumps(payload, sort_keys=True).encode(),
                      {'IsleEngine': 1, 'bound': int(bound)},
                      is_mock, notes=note)
        response.media = {'ok': True, 'engine': key, 'bound': bound,
                          'bound_to': bound_to, 'note': note,
                          'mock_network': is_mock}

    def on_get_engines(self, request, response):
        rows = []
        for row in self._table('IsleEngine').values():
            rows.append({
                'name': getattr(row, 'name', ''),
                'app': getattr(row, 'app_name', ''),
                'provides': getattr(row, 'provides', ''),
                'url': getattr(row, 'url', ''),
                'bound': getattr(row, 'bound', False),
                'bound_to': getattr(row, 'bound_to', ''),
                'note': getattr(row, 'notes', ''),
                'is_mock': getattr(row, 'is_mock', False),
            })
        rows.sort(key=lambda r: r['name'])
        response.media = {'ok': True, 'engines': rows}

    # ---- catalog (§20.1/§20.3) --------------------------------------

    def _entry_dict(self, row):
        return {
            'name': getattr(row, 'name', ''),
            'title': getattr(row, 'title', ''),
            'description': getattr(row, 'description', ''),
            'kind': getattr(row, 'kind', ''),
            'source_ref': getattr(row, 'source_ref', ''),
            'service': getattr(row, 'service', ''),
            'port': getattr(row, 'port', 0),
            'domain': getattr(row, 'domain', ''),
            'provides_engine': getattr(row, 'provides_engine', ''),
            'category': getattr(row, 'category', ''),
            'source': getattr(row, 'source', ''),
            'published': getattr(row, 'published', True),
        }

    def _instances_of(self, entry_name):
        """Running INSTANCES of one catalog entry across the isle:
        IsleApp rows (per-device, from each device's registry
        ingest) matched by the pure catalog helper."""
        rows = []
        for r in self._table('IsleApp').values():
            try:
                modes = json.loads(getattr(r, 'modes_json', '[]'))
            except Exception:
                modes = []
            rows.append({'name': getattr(r, 'name', ''),
                         'device_name': getattr(r, 'device_name',
                                                 ''),
                         'domain': getattr(r, 'domain', ''),
                         'modes': modes,
                         'is_mock': getattr(r, 'is_mock', False)})
        return instances_of(rows, entry_name)

    def on_get_catalog(self, request, response):
        """The browsable store: published entries, both variants —
        each annotated with its running instances (count + which
        devices), so a second install is a CHOSEN duplicate."""
        entries = []
        for r in self._table('IsleCatalogEntry').values():
            if not getattr(r, 'published', True):
                continue
            info = self._entry_dict(r)
            info['instances'] = self._instances_of(info['name'])
            info['instance_count'] = len(info['instances'])
            entries.append(info)
        entries.sort(key=lambda e: (e['category'], e['name']))
        response.media = {'ok': True, 'count': len(entries),
                          'entries': entries}

    def on_get_catalog_entry(self, request, response, entry):
        """One entry + its INSTALL PLAN (host commands the isle CLI
        runs — the backend never deploys, the mover-on-host rule)."""
        row = None
        for candidate in self._table('IsleCatalogEntry').values():
            if getattr(candidate, 'name', '') == entry:
                row = candidate
                break
        if row is None:
            return self._refuse(response,
                                'no catalog entry %r' % entry,
                                '404 Not Found')
        info = self._entry_dict(row)
        info['install_plan'] = install_plan(info)
        info['instances'] = self._instances_of(info['name'])
        info['instance_count'] = len(info['instances'])
        response.media = {'ok': True, 'entry': info}

    def on_get_coherence(self, request, response):
        """The JOINED topology: isle (devices/agents — where packets
        go) x polari (instances — what runs where), with
        evidence-bearing assessments. Suggests, never acts."""
        devices = []
        for d in self._table('IsleDevice').values():
            try:
                doors = json.loads(getattr(d, 'exposures_json',
                                           '[]') or '[]')
            except Exception:
                doors = []
            def _j(attr):
                try:
                    return json.loads(getattr(d, attr, '[]')
                                      or '[]')
                except Exception:
                    return []
            devices.append({
                'name': getattr(d, 'name', ''),
                'agent_present': getattr(d, 'agent_present', False),
                'last_seen': getattr(d, 'last_seen', ''),
                'is_entrypoint': getattr(d, 'is_entrypoint', False),
                'exposures': doors,
                'pools': _j('pools_json'),
                'ports': _j('ports_json'),
                'is_mock': getattr(d, 'is_mock', False)})
        apps = [{'name': getattr(a, 'name', ''),
                 'device_name': getattr(a, 'device_name', ''),
                 'domain': getattr(a, 'domain', ''),
                 'is_mock': getattr(a, 'is_mock', False)}
                for a in self._table('IsleApp').values()]
        services = [{'app_name': getattr(s, 'app_name', ''),
                     'subdomain': getattr(s, 'subdomain', ''),
                     'device_name': getattr(s, 'device_name', ''),
                     'is_mock': getattr(s, 'is_mock', False)}
                    for s in self._table('IsleAppService').values()]
        result = assess_topology(devices, apps, services)
        result['ok'] = True
        result['mock_network'] = self._any_mock()
        response.media = result

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
                    'IsleProtocolPermit', 'IsleEngine',
                    'IsleCatalogEntry', 'IsleIngestReceipt')},
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

    def on_get_graph(self, request, response):
        """The D3 topology payload (Dustin 2026-08-07): nginx
        proxies and the apps they serve as NODES; each permit is an
        EDGE proxy→app whose label IS the access URL. Devices are
        group nodes; apps also link to their hosting device.
        Everything carries is_mock so the view can dash/tint mock
        elements and show the banner."""
        nodes, links, seen = [], [], set()

        def add_node(node_id, kind, label, device='', is_mock=False,
                     **meta):
            if node_id in seen:
                return
            seen.add(node_id)
            node = {'id': node_id, 'kind': kind, 'label': label,
                    'device': device, 'is_mock': bool(is_mock)}
            node.update(meta)
            nodes.append(node)

        for row in self._table('IsleDevice').values():
            name = getattr(row, 'name', '')
            add_node('device:%s' % name, 'device', name,
                     device=name,
                     is_mock=getattr(row, 'is_mock', False),
                     agent_present=getattr(row, 'agent_present',
                                           False),
                     router_running=getattr(row, 'router_running',
                                            False),
                     connectivity_mode=getattr(
                         row, 'connectivity_mode', ''))
            if getattr(row, 'agent_present', False):
                # the nginx proxy is the device's EDGE — every packet
                # in/out of this device's isle apps passes it. role
                # 'device-edge' tells the renderer to draw it at the
                # device's boundary (bottom), not as a free node.
                add_node('proxy:%s' % name, 'proxy',
                         'nginx (isle-agent)', device=name,
                         role='device-edge',
                         is_entrypoint=getattr(row, 'is_entrypoint',
                                               False),
                         is_mock=getattr(row, 'is_mock', False))
                links.append({'source': 'device:%s' % name,
                              'target': 'proxy:%s' % name,
                              'kind': 'edge-of', 'label': '',
                              'is_mock': getattr(row, 'is_mock',
                                                 False)})
            # outside doors (exposures) hang OFF the proxy, OUTSIDE
            # the device — the only crossings of the containment line
            try:
                doors = json.loads(getattr(row, 'exposures_json',
                                           '[]') or '[]')
            except Exception:
                doors = []
            for door in doors:
                port = door.get('port')
                door_id = 'door:%s:%s' % (name, port)
                acc = door.get('access', {})
                add_node(door_id, 'exposure',
                         ':%s → %s' % (port, door.get('internal',
                                                       '')),
                         device=name, placement='external',
                         access_level=acc.get('level'),
                         principal=acc.get('user')
                         or acc.get('group', ''),
                         is_mock=getattr(row, 'is_mock', False))
                links.append({'source': 'proxy:%s' % name,
                              'target': door_id, 'kind': 'exposes',
                              'label': ':%s' % port,
                              'is_mock': getattr(row, 'is_mock',
                                                 False)})
            if getattr(row, 'router_running', False):
                add_node('router:%s' % name, 'router',
                         'OpenWRT router (.isle DNS)', device=name,
                         is_mock=getattr(row, 'is_mock', False))
                links.append({'source': 'device:%s' % name,
                              'target': 'router:%s' % name,
                              'kind': 'hosts', 'label': '',
                              'is_mock': getattr(row, 'is_mock',
                                                 False)})

        # The L2 segment (the switch): devices whose isle-candidate
        # uplink has carrier hang off it — edge label = interface.
        # Ethernet-up counts; wifi counts only when the device
        # DECLARED isle membership (sole-isle) — a home-LAN wifi
        # link must never be drawn as an isle link.
        segment_added = False
        linked_devices = set()
        for row in self._table('IsleUplink').values():
            device = getattr(row, 'device_name', '')
            if device in linked_devices \
                    or not getattr(row, 'link_up', False):
                continue
            kind = getattr(row, 'kind', '')
            declared = ''
            for dev_row in self._table('IsleDevice').values():
                if getattr(dev_row, 'name', '') == device:
                    declared = getattr(dev_row, 'connectivity_mode',
                                       '')
                    break
            if kind != 'ethernet' and declared != 'sole-isle':
                continue
            if not segment_added:
                # the shared L2 segment is OUTSIDE every device —
                # honest: an unmanaged switch is invisible at L3, so
                # this is INFERRED from ≥2 devices sharing carrier,
                # not detected hardware. A genuine detected switch
                # (LLDP/bridge) would arrive as detection:'detected'.
                add_node('segment:isle', 'segment',
                         'isle L2 segment (switch)',
                         placement='external',
                         detection='inferred')
                segment_added = True
            linked_devices.add(device)
            links.append({'source': 'device:%s' % device,
                          'target': 'segment:isle',
                          'kind': 'l2',
                          'label': getattr(row, 'interface', ''),
                          'is_mock': getattr(row, 'is_mock',
                                             False)})

        for row in self._table('IsleApp').values():
            name = getattr(row, 'name', '')
            device = getattr(row, 'device_name', '')
            add_node('app:%s' % name, 'app', name, device=device,
                     is_mock=getattr(row, 'is_mock', False),
                     domain=getattr(row, 'domain', ''),
                     availability_mode=getattr(
                         row, 'availability_mode', ''),
                     status=getattr(row, 'status', ''))
            if device and ('device:%s' % device) in seen:
                links.append({'source': 'device:%s' % device,
                              'target': 'app:%s' % name,
                              'kind': 'runs-on', 'label': '',
                              'is_mock': getattr(row, 'is_mock',
                                                 False)})

        for row in self._table('IsleProtocolPermit').values():
            device = getattr(row, 'device_name', '')
            app = getattr(row, 'app_name', '')
            server = getattr(row, 'server_name', '')
            port = getattr(row, 'listen_port', 0)
            protocol = getattr(row, 'protocol', 'http')
            is_mock = getattr(row, 'is_mock', False)
            proxy_id = 'proxy:%s' % device
            if proxy_id not in seen:
                # permits prove a proxy even when the device ingest
                # missed it
                add_node(proxy_id, 'proxy', 'nginx (isle-agent)',
                         device=device, is_mock=is_mock)
            app_id = 'app:%s' % (app or server)
            if app_id not in seen:
                add_node(app_id, 'app', app or server,
                         device=device, is_mock=is_mock,
                         implied=True)
            scheme = 'https' if protocol.startswith('https') \
                else 'http'
            default = (scheme == 'http' and port == 80) or \
                (scheme == 'https' and port == 443)
            url = '%s://%s%s' % (scheme, server,
                                 '' if default else ':%d' % port)
            links.append({'source': proxy_id, 'target': app_id,
                          'kind': 'serves', 'label': url,
                          'protocol': protocol,
                          'upstream': getattr(row, 'upstream', ''),
                          'fragment': getattr(row, 'fragment_ref',
                                              ''),
                          'is_mock': is_mock})

        mock = self._any_mock()
        response.media = {'ok': True, 'mock_network': mock,
                          'banner': (MOCK_BANNER if mock else ''),
                          'nodes': nodes, 'links': links}

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
