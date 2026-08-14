"""
@cross-cutting
@module reticulum.reticulum_api
@tags @xc:bindings @xc:accessControl

HTTP surface for ret-1. Rows are plain CRUDE for create/list/read;
this adds what CRUDE can't:

  GET  /api/reticulum/capability
        honest availability, *_remote-style: sidecar URL resolved
        (knob → topology), reachable, the LICENCE PINS surfaced (so
        nobody has to remember why rns is 0.9.4), operator-licence
        states, and RECEIVE-FIRST posture stated — RX needs no
        licence and is the default (§5i).
  GET  /api/reticulum/arch
        `.arch` — who we can ACTUALLY reach right now: every node
        with measured reachability (fresh within the horizon) split
        from hopeful names. The declared-vs-measured split as an
        endpoint.
  POST /api/reticulum/inbound
        THE ret-8 SEAM (LiveKit §2 rule inherited VERBATIM): nothing
        arriving from another isle may mutate Polari state. The
        sidecar/gateway POSTs inbound app data here; it becomes a
        PROPOSAL ('rns_inbound', level 4 network-service — above the
        auto-approve ceiling, so applying is ALWAYS a confirmed act).

Deliberately ABSENT: any endpoint that writes rows from mesh data,
and any transmit control on an rx-only surface.

@consumers
  - ret-3 gateway (inbound seam), frontend reticulum page (later arc)
@see reticulum.rns_remote (ladder), collab.collab_api (idiom walked
     before this one; commit_drag is the seam's first walk)
"""

import json
import time

import falcon

from objectTreeDecorators import treeObject, treeObjectInit
from reticulum.arch_basis import reachable_now
from reticulum.operator_basis import license_state, license_warning


class ReticulumAPI(treeObject):
    """ret-1 endpoints."""

    @treeObjectInit
    def __init__(self, polServer, manager=None):
        self.polServer = polServer
        self.apiName = '/api/reticulum'
        if polServer is not None:
            add = polServer.falconServer.add_route
            add('/api/reticulum/capability', self, suffix='capability')
            add('/api/reticulum/arch', self, suffix='arch')
            add('/api/reticulum/arch-topology', self,
                suffix='arch_topology')
            add('/api/reticulum/resolve/{name}', self, suffix='resolve')
            add('/api/reticulum/peers', self, suffix='peers')
            add('/api/reticulum/meshsim', self, suffix='meshsim')
            add('/api/reticulum/peers/{name}/adjudicate', self,
                suffix='adjudicate')
            add('/api/reticulum/inbound', self, suffix='inbound')

    # ---- helpers ----------------------------------------------------

    def _rows(self, class_name):
        table = (self.manager.objectTables or {}).get(class_name, {})
        return list(table.values())

    def _refuse(self, response, error, status=falcon.HTTP_400,
                suggestion=None):
        response.status = status
        body = {'ok': False, 'error': error}
        if suggestion:
            body['suggestion'] = suggestion
        response.media = body

    # ---- routes -----------------------------------------------------

    def on_get_capability(self, request, response):
        from reticulum import rns_remote as rr
        url = rr.server_url()
        alive = rr.reachable() if url else None
        today = time.strftime('%Y-%m-%d')
        licenses = []
        for row in self._rows('OperatorLicense'):
            state = license_state(getattr(row, 'expiry_date', ''), today)
            licenses.append({
                'name': row.name,
                'callsign': getattr(row, 'callsign', ''),
                'state': state,
                'warning': license_warning(
                    state, getattr(row, 'callsign', '')) or None,
            })
        report = {
            'ok': True,
            'sidecarUrl': url or None,
            'sidecarReachable': alive,
            'stackPins': rr.STACK_PINS,
            'posture': 'receive-first: RX needs no licence and is the '
                       'default; transmit is a deliberate, per-'
                       'interface enablement (§5i)',
            'operatorLicenses': licenses,
            'licenseNote': ('states are the operator\'s own recorded '
                            'assertion — tracked and surfaced, never '
                            'validated online, never a transmit gate '
                            '(an emergency tool cannot depend on a '
                            'reachable server)'),
        }
        if not licenses:
            report['licenseWarning'] = license_warning('none')
        gaps = []
        if not url:
            gaps.append('RETICULUM_URL unset and the topology resolves '
                        "no provider for 'reticulum.mesh'")
        elif alive is False:
            gaps.append(f'{url} did not answer /status')
        if gaps:
            report['suggestion'] = rr.unavailable_suggestion(
                '; '.join(gaps))
        response.media = report

    def on_get_arch(self, request, response):
        """Who can I actually reach RIGHT NOW — measured, timestamped,
        split from hopeful names."""
        now_ms = int(time.time() * 1000)
        reachable, stale = [], []
        for row in self._rows('ArchipelagoNode'):
            fact = {'last_heard_ms': getattr(row, 'last_heard_ms', 0)}
            entry = {
                'name': row.name,
                'archName': getattr(row, 'arch_name', ''),
                'kind': getattr(row, 'node_kind', ''),
                'destination': getattr(row, 'destination_name', ''),
                'lastHeardMs': fact['last_heard_ms'],
                'hopCount': getattr(row, 'hop_count', 0),
                'linkQuality': getattr(row, 'link_quality', ''),
                'trust': getattr(row, 'trust_name', ''),
                'fidelity': getattr(row, 'fidelity', 'declared'),
            }
            (reachable if reachable_now(fact, now_ms)
             else stale).append(entry)
        response.media = {
            'ok': True, 'nowMs': now_ms,
            'reachable': reachable,
            'unmeasuredOrStale': stale,
            'note': ('reachability is a MEASUREMENT with a timestamp; '
                     'past the freshness horizon the honest answer is '
                     '"unknown, measure first", not the last good '
                     'number'),
        }

    #: Which row fields the arch-topology assembly reads, per class —
    #: rows are handed over as plain dicts (the netledger idiom).
    _ARCH_FIELDS = {
        'ReticulumInterface': (
            'name', 'bearer', 'direction', 'regulatory_domain',
            'idle_policy', 'enabled', 'declared_params_json'),
        'DeviceLink': ('name', 'interface_name', 'device_model_name'),
        'DeviceModel': ('name', 'display_name', 'interop'),
        'TransportBinding': (
            'name', 'app_name', 'app_protocol', 'destination_name',
            'encoding', 'max_message_bytes', 'max_rate_per_min',
            'enabled'),
        'AirtimeBudget': ('name', 'interface_name', 'window_seconds',
                          'budget_ms', 'consumed_ms'),
        'LinkMeasurement': (
            'name', 'destination_name', 'bearer_path_json',
            'hop_count', 'worst_hop_bearer', 'throughput_bps',
            'rtt_ms', 'loss_rate', 'measured_at_ms', 'fidelity'),
        'ArchipelagoNode': ('name', 'arch_name', 'node_kind',
                            'last_heard_ms', 'hop_count',
                            'trust_name'),
        'IsleDevice': ('name',),
    }

    def _dicts(self, class_name):
        fields = self._ARCH_FIELDS[class_name]
        return [{f: getattr(row, f, None) for f in fields}
                for row in self._rows(class_name)]

    def on_get_arch_topology(self, request, response):
        """ret-1b: the .arch topology view — isles as blocks, radios
        and apps inside, measured paths between, demand vs capacity
        with an honest verdict (plan §5m)."""
        from reticulum.arch_topology import assemble_arch_topology
        instance = getattr(self.polServer, 'serverName', '') \
            or 'this-isle'
        tables = {
            'interfaces': self._dicts('ReticulumInterface'),
            'device_links': self._dicts('DeviceLink'),
            'device_models': self._dicts('DeviceModel'),
            'bindings': self._dicts('TransportBinding'),
            'budgets': self._dicts('AirtimeBudget'),
            'measurements': self._dicts('LinkMeasurement'),
            'arch_nodes': self._dicts('ArchipelagoNode'),
            # islemesh names only for now — the coherence apps join
            # is the next stitch; an empty block is honest.
            'isle_devices': self._dicts('IsleDevice'),
        }
        response.media = assemble_arch_topology(
            tables, instance, int(time.time() * 1000))

    def on_get_resolve(self, request, response, name):
        """ret-3: THE NAME REGISTRY as an endpoint — what the isle's
        resolver (router-side, isle-core's half) queries before
        answering a *.rns.isle / .arch name with a synthetic IP.
        An unmapped name is refused BY NAME — never guessed, never a
        silent black hole (§3)."""
        # A destination row by name, or an .arch node by arch_name.
        for row in self._rows('ReticulumDestination'):
            if getattr(row, 'name', '') == name:
                return self._respond_resolved(response, name, row.name,
                                              row)
        for node in self._rows('ArchipelagoNode'):
            if getattr(node, 'arch_name', '') == name \
                    or getattr(node, 'name', '') == name:
                dest_name = getattr(node, 'destination_name', '')
                for row in self._rows('ReticulumDestination'):
                    if getattr(row, 'name', '') == dest_name:
                        return self._respond_resolved(
                            response, name, dest_name, row,
                            arch=getattr(node, 'arch_name', ''))
                return self._refuse(
                    response, f'.arch node {name!r} names destination '
                              f'{dest_name!r}, which has no row — the '
                              'mapping is incomplete, not guessed',
                    falcon.HTTP_404)
        return self._refuse(
            response, f'no mapping for {name!r} — unmapped names are '
                      'refused by name, never routed hopefully',
            falcon.HTTP_404,
            suggestion={
                'evidence': f'{name!r} matches no ReticulumDestination '
                            'name and no ArchipelagoNode arch_name',
                'knob': 'ReticulumDestination / ArchipelagoNode rows '
                        '(CRUDE)',
                'action': 'create the destination row (and its .arch '
                          'node if it is a peer), then resolve again',
            })

    def _respond_resolved(self, response, asked, dest_name, row,
                          arch=''):
        response.media = {
            'ok': True, 'asked': asked, 'destination': dest_name,
            'archName': arch,
            'destHash': getattr(row, 'dest_hash', ''),
            'destType': getattr(row, 'dest_type', ''),
            'scope': getattr(row, 'scope', ''),
            'direction': getattr(row, 'direction', ''),
            'note': ('the synthetic IP for this name comes from the '
                     'netledger-reserved pool on the resolving host '
                     '(ret-3); this endpoint answers WHAT the name '
                     'is, the resolver answers WHERE to send packets'),
        }

    def on_post_meshsim(self, request, response):
        """ret-1e (§5p): the mesh planning computation — pure math,
        writes nothing, needs no auth. Body:

          {bearerSet: name from SCENARIO_BEARER_SETS (or a custom
           list via 'bearers'),
           deviceModels: {bearer: 'model-row-name'
                          | {model: name, capacityBps: N}},
           meshSizeNodes, targetPerPeerBps, areaM2?,
           propagationMode? ('flat-assumed' default | 'measured';
           elevation modes refuse with the terrain disclaimer),
           practicalMarginDb?, utilization?, spatialReuse?,
           reachSamples?: [{bearing_deg, distance_m, success}]}

        capacityBps override wins; else the model row is consulted;
        'ham-broadcast' has no catalog row and reports broadcast-only.
        """
        from reticulum import meshsim_basis as ms
        try:
            body = request.media or {}
        except Exception:
            body = {}
        mode = body.get('propagationMode') or 'flat-assumed'
        ok, why = ms.mode_supported(mode)
        if not ok:
            return self._refuse(response, why, falcon.HTTP_400,
                                suggestion={
                                    'evidence': why,
                                    'knob': 'propagationMode',
                                    'action': "use 'flat-assumed' or "
                                              "'measured' for now"})
        bearers = body.get('bearers') \
            or ms.SCENARIO_BEARER_SETS.get(body.get('bearerSet', ''))
        if not bearers:
            return self._refuse(
                response, 'no bearer set: name one of %s via '
                          'bearerSet, or pass a bearers list'
                          % sorted(ms.SCENARIO_BEARER_SETS))
        n_nodes = int(body.get('meshSizeNodes') or 0)
        target = float(body.get('targetPerPeerBps') or 0)
        area = float(body.get('areaM2') or 0)
        margin = float(body.get('practicalMarginDb') or 30.0)
        util = float(body.get('utilization') or 0.5)
        reuse = float(body.get('spatialReuse') or 1.0)
        models = {m.get('name'): m for m in [
            {f: getattr(row, f, None) for f in (
                'name', 'declared_range_m', 'rx_sensitivity_dbm',
                'tx_power_dbm_max', 'freq_mhz_lo', 'display_name')}
            for row in self._rows('DeviceModel')]}
        device_models = body.get('deviceModels') or {}
        per_bearer = {}
        assumptions = []
        predicted_range = None
        for bearer in bearers:
            spec = device_models.get(bearer)
            if isinstance(spec, dict):
                model_name = spec.get('model', '')
                capacity_override = spec.get('capacityBps')
            else:
                model_name = spec or ''
                capacity_override = None
            if bearer == 'ham-broadcast':
                per_bearer[bearer] = {
                    'kind': 'broadcast-only',
                    'note': 'one-way public broadcast core (§5g) — '
                            'no range math without a catalog row, '
                            'and reach is the operator\'s '
                            'station/antenna question',
                }
                continue
            model = models.get(model_name)
            if model is None:
                per_bearer[bearer] = {
                    'kind': 'unknown',
                    'note': 'no DeviceModel row named %r — the '
                            'catalog answers what devices ARE; add '
                            'the row (with evidence) to simulate '
                            'this bearer' % (model_name,),
                }
                continue
            entry = {'kind': 'radio', 'model': model_name,
                     'displayName': model.get('display_name')}
            range_m, fidelity, evidence = ms.flat_range_m(
                model, practical_margin_db=margin)
            if mode == 'measured':
                fresh = [m for m in self._dicts('LinkMeasurement')
                         if m.get('throughput_bps')]
                if fresh:
                    best = max(fresh,
                               key=lambda m: m['throughput_bps'])
                    capacity_override = capacity_override \
                        or best['throughput_bps']
                    entry['measuredNote'] = (
                        'capacity anchored on a measured row (%s '
                        'bps); measured RANGE anchoring needs '
                        'distance-tagged measurements — an honest '
                        'gap, rows carry no distance yet'
                        % best['throughput_bps'])
            if range_m is None:
                entry['range'] = {'rangeM': None,
                                  'fidelity': fidelity,
                                  'evidence': evidence}
            else:
                entry['range'] = {'rangeM': range_m,
                                  'fidelity': fidelity,
                                  'evidence': evidence}
                predicted_range = predicted_range or range_m
                plan = ms.spacing_plan(range_m, area)
                entry['spacing'] = plan
                assumptions.extend(plan.pop('assumptions'))
            if capacity_override and n_nodes >= 2:
                relay = ms.relay_allowance(
                    n_nodes, target, float(capacity_override),
                    utilization=util, spatial_reuse=reuse)
                if relay.get('assumptions'):
                    assumptions.extend(relay.pop('assumptions'))
                entry['relay'] = relay
            elif capacity_override is None:
                entry['relayNote'] = ('no capacityBps known for this '
                                      'bearer — pass deviceModels.'
                                      '%s.capacityBps or measure'
                                      % bearer)
            per_bearer[bearer] = entry
        result = {
            'ok': True, 'mode': mode,
            'disclaimer': ms.TERRAIN_DISCLAIMER,
            'perBearer': per_bearer,
            'assumptions': sorted(set(assumptions)),
        }
        samples = body.get('reachSamples')
        if samples and predicted_range:
            result['interference'] = ms.interference_suspicions(
                samples, predicted_range)

        # ---- ret-1f (§5q): placement + population sections ---------
        placement = body.get('placement')
        if placement:
            from reticulum import meshsim_placement as mp
            pmode = placement.get('mode', 'cheapest-coverage')
            polygon = placement.get('polygon')
            if not polygon:
                return self._refuse(
                    response, 'placement without a polygon',
                    falcon.HTTP_400, suggestion={
                        'evidence': 'placement.mode %r asked but no '
                                    'polygon given' % pmode,
                        'knob': 'placement.polygon (geojson Polygon, '
                                'lon/lat or local meters)',
                        'action': 'draw/pass the shape to simulate '
                                  'on'})
            ring_m, area_m2, ring_notes = mp.to_local_meters(polygon)
            if ring_m is None:
                return self._refuse(response, '; '.join(ring_notes),
                                    falcon.HTTP_400)
            # device options resolve from catalog rows by name; a
            # capacityBps override rides per option.
            catalog = {getattr(r, 'name', ''): r
                       for r in self._rows('DeviceModel')}
            options = []
            for spec in (placement.get('deviceOptions')
                         or [{'model': m} for m in device_models
                             .values() if isinstance(m, str)]):
                spec = spec if isinstance(spec, dict) \
                    else {'model': spec}
                row = catalog.get(spec.get('model', ''))
                option = {'name': spec.get('model')} if row is None \
                    else {f: getattr(row, f, None) for f in (
                        'name', 'declared_range_m',
                        'declared_range_min_m', 'declared_range_max_m',
                        'rx_sensitivity_dbm', 'tx_power_dbm_max',
                        'freq_mhz_lo', 'freq_mhz_hi', 'price_usd')}
                if spec.get('capacityBps'):
                    option['capacityBps'] = spec['capacityBps']
                # §5q loadouts: units per node cap (capacity x units
                # on distinct channels; the row's channel count also
                # ceilings it).
                if spec.get('unitsMax'):
                    option['unitsMax'] = spec['unitsMax']
                options.append(option)
            if pmode == 'cheapest-coverage':
                out = mp.plan_cheapest_coverage(
                    ring_m, options, target,
                    reach_mode=placement.get('reachMode',
                                             'max-spread'),
                    range_scenario=placement.get('rangeScenario',
                                                 'typical'),
                    range_override_m=placement.get('rangeOverrideM'))
            elif pmode in ('fixed-locations', 'resilience'):
                nodes_m, node_refusals = mp.nodes_to_local(
                    placement.get('nodes') or [], polygon)
                if node_refusals:
                    return self._refuse(
                        response, '; '.join(node_refusals),
                        falcon.HTTP_400)
                fn = (mp.assess_fixed_locations
                      if pmode == 'fixed-locations'
                      else mp.failure_resilience)
                out = fn(ring_m, nodes_m, options, target) \
                    if pmode == 'fixed-locations' \
                    else fn(ring_m, nodes_m, options)
            else:
                return self._refuse(
                    response, 'unknown placement mode %r' % pmode)
            out['areaM2'] = area_m2
            out.setdefault('assumptions', []).extend(ring_notes)
            result['placement'] = out
        population = body.get('population')
        if population and population.get('cohorts') is not None:
            # counts-first (§5q, the primary form): specific numbers
            # of people per kit configuration; profile names resolve
            # from KitProfile rows; percentages are derived analytics.
            # (import here too — a population-only request never runs
            # the placement branch's import, and a function-local
            # name used before ITS import is an UnboundLocalError:
            # the AppsNavSeed lesson.)
            from reticulum import meshsim_placement as mp
            profiles = {}
            for row in self._rows('KitProfile'):
                try:
                    profiles[getattr(row, 'name', '')] = json.loads(
                        getattr(row, 'devices_json', '') or '{}')
                except ValueError:
                    pass
            result['population'] = mp.population_cohorts_report(
                population['cohorts'], profiles=profiles)
        elif population:
            from reticulum import meshsim_placement as mp
            result['population'] = mp.population_mix_report(
                population.get('mix') or {},
                int(population.get('n') or 0))
        response.media = result

    def on_get_peers(self, request, response):
        """ret-1d: potential peers — sighting ROWS merged with what
        the sidecar is hearing RIGHT NOW, bucketed by adjudication
        status. Hearing is not admitting; the buckets say which is
        which."""
        from reticulum import rns_remote as rr
        from reticulum.discovery_basis import merge_heard
        now_ms = int(time.time() * 1000)
        rows = {getattr(r, 'name', ''): {
            'name': r.name,
            'identity_hash': getattr(r, 'identity_hash', ''),
            'dest_hash': getattr(r, 'dest_hash', ''),
            'aspects': getattr(r, 'aspects', ''),
            'heard_via': getattr(r, 'heard_via', ''),
            'first_heard_ms': getattr(r, 'first_heard_ms', 0),
            'last_heard_ms': getattr(r, 'last_heard_ms', 0),
            'announce_count': getattr(r, 'announce_count', 0),
            'status': getattr(r, 'status', 'unadjudicated'),
            'adjudicated_by': getattr(r, 'adjudicated_by', ''),
            'arch_node_name': getattr(r, 'arch_node_name', ''),
        } for r in self._rows('PeerSighting')}
        live = []
        status = rr.sidecar_status()
        if status.get('ok'):
            live = status['status'].get('peersHeard', [])
        for heard in live:
            key = heard.get('destHash', '')
            if key in rows:
                rows[key] = dict(
                    rows[key], **{k: v for k, v in merge_heard(
                        rows[key], heard, now_ms).items()
                        if k in ('last_heard_ms', 'announce_count',
                                 'heard_via')})
                rows[key]['hearingNow'] = True
            else:
                fresh = merge_heard(None, heard, now_ms)
                fresh.update({'name': key, 'hearingNow': True,
                              'persisted': False})
                rows[key] = fresh
        buckets = {'unadjudicated': [], 'archipelago': [], 'mesh': [],
                   'ignored': []}
        for entry in rows.values():
            buckets.setdefault(entry.get('status', 'unadjudicated'),
                               []).append(entry)
        response.media = {
            'ok': True, 'nowMs': now_ms,
            'sidecarLive': bool(status.get('ok')),
            'peers': buckets,
            'note': ('hearing is not admitting: unadjudicated peers '
                     'are a question, .arch is ours by a named '
                     'human\'s decision, .mesh is the wider mesh '
                     '(mesh rung only), ignored stays recorded'),
        }

    def on_post_adjudicate(self, request, response, name):
        """The adjudication ACT: a KC-verified human decides what a
        heard peer becomes. Identity before existence (the standing
        401-vs-404 rule)."""
        from reticulum.discovery_basis import PeerSighting, adjudicate
        user = getattr(request.context, 'user_info', None)
        if not user or not user.get('sub'):
            return self._refuse(
                response, 'adjudicating a peer requires a Keycloak-'
                          'verified caller — admission is a human act '
                          'with a name on it', falcon.HTTP_401)
        try:
            body = request.media or {}
        except Exception:
            body = {}
        decision = (body.get('decision') or '').strip()
        arch_name = (body.get('archName') or '').strip()
        row = None
        for r in self._rows('PeerSighting'):
            if getattr(r, 'name', '') == name:
                row = r
                break
        sighting = ({'status': getattr(row, 'status', 'unadjudicated'),
                     'dest_hash': getattr(row, 'dest_hash', ''),
                     'last_heard_ms': getattr(row, 'last_heard_ms', 0)}
                    if row is not None else None)
        if sighting is None:
            # a live-heard, never-persisted peer may be adjudicated
            # directly from the sidecar's report
            live = (body.get('heard') or {})
            if not live.get('destHash'):
                return self._refuse(
                    response, f'no PeerSighting named {name!r} and no '
                              'heard payload to adjudicate from',
                    falcon.HTTP_404)
            sighting = {'status': 'unadjudicated',
                        'dest_hash': live.get('destHash', ''),
                        'last_heard_ms': live.get('lastHeardMs', 0)}
        who = user.get('username') or user['sub']
        ok, result = adjudicate(sighting, decision, who, arch_name)
        if not ok:
            return self._refuse(response, result['evidence'],
                                falcon.HTTP_400, suggestion=result)
        stamp = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
        arch_node = result.pop('createArchNode', None)
        created = None
        if arch_node is not None:
            from reticulum.arch_basis import ArchipelagoNode
            node = ArchipelagoNode(manager=self.manager, **arch_node)
            try:
                self.manager.db.saveInstanceInDB(node)
            except Exception:
                pass
            created = arch_node['arch_name']
        if row is None:
            from reticulum.discovery_basis import merge_heard
            fresh = merge_heard(None, body.get('heard') or {},
                                int(time.time() * 1000))
            fresh.update(result)
            row = PeerSighting(manager=self.manager, name=name,
                              **{k: v for k, v in fresh.items()
                                 if k != 'name'})
        else:
            for field, value in result.items():
                setattr(row, field, value)
        row.adjudicated_at = stamp
        if created:
            row.arch_node_name = created
        try:
            self.manager.db.saveInstanceInDB(row)
        except Exception:
            pass
        response.media = {
            'ok': True, 'peer': name, 'decision': decision,
            'by': who, 'at': stamp,
            'archNodeCreated': created,
            'note': ('admission is routing and naming, never '
                     'authority — trust grades are separate rows '
                     '(§5c), and .mesh peers stay at the mesh '
                     'rung'),
        }

    def on_post_inbound(self, request, response):
        """ret-8: inbound mesh data becomes a PROPOSAL, never a write.

        The caller is the LOCAL sidecar/gateway (KC-verified service
        account or user) — a remote isle is not authorized merely by
        being on the mesh, and its trust grade only raises what may be
        auto-approved LATER, on the proposal side; it buys no direct
        write here or anywhere."""
        user = getattr(request.context, 'user_info', None)
        if not user or not user.get('sub'):
            # Identity FIRST, shape second (401-vs-400/404 must not
            # leak which watched objects exist).
            return self._refuse(
                response, 'inbound mesh data requires a Keycloak-'
                          'verified LOCAL caller — arrival on the mesh '
                          'is not authorization', falcon.HTTP_401)
        try:
            body = request.media or {}
        except Exception:
            body = {}
        arch_name = (body.get('archName') or '').strip()
        kind = (body.get('kind') or '').strip()
        payload = body.get('payload')
        if not arch_name or not kind:
            return self._refuse(
                response, 'archName (the sending .arch node) and kind '
                          '(what this data claims to be) are required')
        if not isinstance(payload, dict) or not payload:
            return self._refuse(
                response, 'payload must be a non-empty object — the '
                          'data as received, verbatim')
        try:
            from polariApiServer.ai_actions import kernel
        except Exception as exc:
            return self._refuse(
                response, f'the proposal kernel is unavailable: {exc}',
                falcon.HTTP_503)
        who = user.get('username') or user['sub']
        proposal = kernel.propose(
            'rns_inbound',
            f'mesh data ({kind}) from {arch_name!r} via {who}',
            {'archName': arch_name, 'kind': kind, 'payload': payload,
             'watchedName': (body.get('watchedName') or '').strip()})
        response.status = falcon.HTTP_202
        response.media = {
            'ok': True, 'applied': False, 'proposal': proposal,
            'from': arch_name, 'by': who,
            'note': ('PROPOSED, not applied. Nothing arriving over '
                     'Reticulum mutates Polari state; applying is a '
                     'separate confirmed act in the same provenance '
                     'log as every other change (level 4 — above the '
                     'auto-approve ceiling by design).'),
        }
