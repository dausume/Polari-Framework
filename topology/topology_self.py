"""
@cross-cutting
@module topology.topology_self

tpl-0 (AI-Notes/plans/TOPOLOGY_LAYERS_PLAN.md): a backend DESCRIBES ITSELF in the Polari topology, with no isle and no
`pol` CLI. Every fresh backend used to carry the 2026-07-09 dev snapshot (topology_seed) as reality and called itself
'local'; now it knows its own name and writes its own rows at boot, idempotently:

    TopologyDefinition   the active one if any, else one named after this instance (status applied, active)
    PolariNodeMachine    the device it runs on, when known (created if absent; resources stay unobserved until reported)
    InstanceDefinition   this instance (created if absent; an existing row is left as its owner wrote it)
    ModuleAssignment     one per module ACTUALLY live here (placement_truth.sync_assignment_row, the dyn-2b authority path)

Knobs (labelled; every value derived or said in words):
    POLARI_INSTANCE_NAME   this instance's name. Absent -> derived from the first https://<name>.isle CORS origin (the isle
                           instance generator writes that origin first), else 'local'.
    POLARI_MACHINE_NAME    the device this instance runs on. Absent -> ISLE_HOSTNAME, else '' (unknown, never a container id).
    POLARI_TOPOLOGY_SEED   'example' seeds the 2026-07-09 dev snapshot (topology_seed); 'none' does not. Absent -> 'example'
                           only when this instance is one the snapshot itself describes (the compose suite's prf-a), else
                           'none'. So a compose stack spun up from its own files keeps its page; an isle backend shows itself.

    instance_name() / machine_name() / seed_mode()
    describe_self(manager, live_modules, source) -> {ok, instance, topology, machine, assignments, created, words}
    describe_links(manager, live_modules, source) -> tpl-1: engine bindings + frontend origins as rows {engines, frontends, created, retired, words}
    on_binding_changed(manager, source)           the single entry point for a binding saved/removed (never raises)
"""
import os
from urllib.parse import urlsplit

SEED_MODES = ('example', 'none')
_DEPLOY_TIERS = {'development': 'dev', 'dev': 'dev', 'staging': 'staging', 'production': 'prod', 'prod': 'prod', 'test': 'test'}


def instance_name():
    explicit = (os.environ.get('POLARI_INSTANCE_NAME') or os.environ.get('POLARI_INSTANCE_ID') or '').strip()
    if explicit:
        return explicit
    for origin in (os.environ.get('CORS_ORIGINS') or '').split(','):
        host = (urlsplit(origin.strip()).hostname or '')
        if host.endswith('.isle') and host.count('.') == 1:
            return host[:-len('.isle')]
    return 'local'


def machine_name():
    return (os.environ.get('POLARI_MACHINE_NAME') or os.environ.get('ISLE_HOSTNAME') or '').strip()


def _example_instances():
    try:
        from topology.topology_seed import SEED_INSTANCE_DEFINITIONS
        return {s.get('name') for s in SEED_INSTANCE_DEFINITIONS}
    except Exception:  # noqa: BLE001 - no seed module = nothing to describe
        return set()


def seed_mode():
    knob = (os.environ.get('POLARI_TOPOLOGY_SEED') or '').strip().lower()
    if knob in SEED_MODES:
        return knob
    return 'example' if instance_name() in _example_instances() else 'none'


def _rows(manager, cls):
    return list((getattr(manager, 'objectTables', None) or {}).get(cls, {}).values())


def _save(manager, row):
    db = getattr(manager, 'db', None)
    if db is not None:
        db.saveInstanceInDB(row)


def describe_self(manager, live_modules, source='boot'):
    me = instance_name()
    machine = machine_name()
    created = []
    topologies = _rows(manager, 'TopologyDefinition')
    topo = next((t for t in topologies if getattr(t, 'is_active', False)), None) or (topologies[0] if topologies else None)
    if topo is None:
        from topology.topology_state import TopologyDefinition
        topo = TopologyDefinition(name=me, description='This backend as it describes itself (tpl-0): its own instance and the '
                                  'modules live on it. Peers and the isle add their rows beside it.',
                                  status='applied', is_active=True, notes='self-described at %s (tpl-0)' % source, manager=manager)
        _save(manager, topo)
        created.append('TopologyDefinition:%s' % topo.name)
    if machine and not any(getattr(r, 'name', '') == machine for r in _rows(manager, 'PolariNodeMachine')):
        from topology.topology_basis import PolariNodeMachine
        _save(manager, PolariNodeMachine(name=machine, source='self-described', notes='the device %s runs on, self-described at %s '
                                         '(tpl-0); its resources come from an observation, never guessed' % (me, source),
                                         manager=manager))
        created.append('PolariNodeMachine:%s' % machine)
    inst = next((i for i in _rows(manager, 'InstanceDefinition') if getattr(i, 'name', '') == me), None)
    if inst is None:
        from topology.topology_basis import InstanceDefinition
        tier = _DEPLOY_TIERS.get((os.environ.get('DEPLOY_ENV') or '').strip().lower(), 'dev')
        inst = InstanceDefinition(name=me, kind='prf', service_kinds_json='["prf-backend"]', env_tier=tier, machine_name=machine,
                                  topology_name=topo.name, notes='self-described at %s (tpl-0)' % source, manager=manager)
        _save(manager, inst)
        created.append('InstanceDefinition:%s' % me)
    from topology.placement_truth import sync_assignment_row
    synced = [m for m in sorted(live_modules)
              if sync_assignment_row(manager, m, 'enabled', 'self-described at %s (tpl-0)' % source).get('synced')]
    return {'ok': True, 'instance': me, 'topology': topo.name, 'machine': machine, 'assignments': synced, 'created': created,
            'words': '%s describes itself in topology %s: %d live module%s%s%s'
                     % (me, topo.name, len(synced), '' if len(synced) == 1 else 's',
                        ' on %s' % machine if machine else ' (its device unknown: set POLARI_MACHINE_NAME)',
                        '; created ' + ', '.join(created) if created else '')}


def after_boot(manager, source='boot'):
    """The end-of-boot hook (lazy boot and the monolithic seed pass): describe this backend, pull the isle's engine registry
    when a consumer exists (islemesh.custom.islemesh_engines.sync_from_registry, fix 11), describe its links, then let a
    module that ships boot-time data finish it (cmod: the Bench topology specs, manual fix 13). Best-effort: each part reports in words and a
    failure never stops the boot. -> {self, benches}"""
    out = {}
    try:
        from topology.placement_truth import live_module_set
        out['self'] = describe_self(manager, live_module_set(manager.polServer), source)
    except Exception as exc:  # noqa: BLE001 - a standalone/host-tool manager may have no topology classes
        out['self'] = {'ok': False, 'words': 'self-description skipped: %s: %s' % (type(exc).__name__, exc)}
    # fix 11 (econ Claude owns the consumer): pull the isle's engine registry and bind its entries BEFORE the links are
    # described, so a fresh backend's topology shows the engines on its first boot. Absent function = nothing to pull.
    try:
        from islemesh.custom.islemesh_engines import sync_from_registry
    except ImportError:
        out['registry'] = {'ok': True, 'words': 'no engine registry consumer on this instance'}
    else:
        try:
            out['registry'] = sync_from_registry(manager, source)
        except Exception as exc:  # noqa: BLE001 - a registry outage must never stop the boot
            out['registry'] = {'ok': False, 'words': 'engine registry pull failed: %s: %s' % (type(exc).__name__, exc)}
    try:
        from topology.topology_peering import start_peer_puller
        out['peers'] = {'ok': True, 'words': start_peer_puller(manager)}
    except Exception as exc:  # noqa: BLE001 - peering never stops the boot
        out['peers'] = {'ok': False, 'words': 'peer puller not started: %s: %s' % (type(exc).__name__, exc)}
    try:
        from topology.placement_truth import live_module_set
        out['links'] = describe_links(manager, live_module_set(manager.polServer), source)
    except Exception as exc:  # noqa: BLE001
        out['links'] = {'ok': False, 'words': 'links skipped: %s: %s' % (type(exc).__name__, exc)}
    try:
        from cmod.custom.bench_topology_spec import apply_shipped
        out['benches'] = apply_shipped(manager)
    except ImportError:
        out['benches'] = []
    except Exception as exc:  # noqa: BLE001
        out['benches'] = [{'applied': False, 'words': 'bench specs skipped: %s: %s' % (type(exc).__name__, exc)}]
    return out


# tpl-1: which module CONSUMES an engine kind, derived from the readers of the binding row (cited): board -> board.custom.
# board_engines.binding_url_for (avr + esp families), scope -> instruments.custom.scope_engines.binding_url, cad ->
# mathshapes.cad_remote, msci -> materialsScience's remote ladder (islemesh_engines._BINDERS note). A kind with no verified
# reader gets its worker and capability rows but no dependency edge, said in the result.
ENGINE_CONSUMERS = {'board': 'board', 'esp': 'board', 'scope': 'instruments', 'cad': 'mathshapes', 'msci': 'materialsScience'}
_TAG = '(tpl-1)'


def _worker_name(kind, url):
    host = urlsplit(url or '').hostname or ''
    return host[:-len('.isle')] if host.endswith('.isle') and host.count('.') == 1 else (host or '%s-engines' % kind)


def _upsert(manager, cls_name, module, cls, name, created, **fields):
    row = next((r for r in _rows(manager, cls_name) if getattr(r, 'name', '') == name), None)
    if row is None:
        mod = __import__(module, fromlist=[cls])
        row = getattr(mod, cls)(name=name, manager=manager, **fields)
        created.append('%s:%s' % (cls_name, name))
    elif _TAG in (getattr(row, 'notes', '') or '') or '(tpl-2 peer:' in (getattr(row, 'notes', '') or ''):
        # only rows this pass wrote follow it (a row a person wrote is left as it is); a PEER'S COPY of the same row (tpl-2:
        # two backends bound to one isle engine worker) becomes this backend's own, because local truth outranks a copy
        for k, v in fields.items():
            setattr(row, k, v)
    _save(manager, row)
    return row


def frontend_evidence(origin, me, fetch=None, timeout=5):
    """Codex's review of tpl-1: a CORS origin only AUTHORIZES a frontend; it proves nothing about one existing or using this
    backend. Evidence joins when the frontend's own runtime config names this backend (api.<me>.isle). Knob
    POLARI_TOPOLOGY_VERIFY=off skips the read. -> (verified: bool, words). Never raises; TLS verified (the outbound seam)."""
    if (os.environ.get('POLARI_TOPOLOGY_VERIFY') or '').strip().lower() == 'off':
        return False, 'configured by CORS_ORIGINS; not checked (POLARI_TOPOLOGY_VERIFY=off)'
    url = origin.rstrip('/') + '/assets/runtime-config.json'
    try:
        if fetch is not None:
            cfg = fetch(url)
        else:
            import json
            from polariApiServer import outbound
            with outbound.http_request('peer', 'frontend-runtime-config', 'GET', url, means='rest', timeout=timeout,
                                       lib='urllib') as resp:
                cfg = json.loads(resp.read().decode('utf-8'))
    except Exception as exc:  # noqa: BLE001 - an absent or unreachable frontend is a finding in words, never a crash
        return False, 'configured by CORS_ORIGINS; UNVERIFIED: %s unreadable (%s: %s)' % (url, type(exc).__name__, exc)
    backend = ((cfg or {}).get('backend') or {}) if isinstance(cfg, dict) else {}
    hosts = {str((backend.get(k) or {}).get('url') or '') for k in ('https', 'http', 'ws')} - {''}
    want = 'api.%s.isle' % me
    if want in hosts:
        return True, 'VERIFIED: %s names %s' % (url, want)
    return False, 'configured by CORS_ORIGINS; UNVERIFIED: %s names %s, not %s' % (url, ', '.join(sorted(hosts)) or 'no backend', want)


def describe_links(manager, live_modules, source='boot', fetch=None):
    """tpl-1: the backend's links as topology rows, idempotent.
    - every EngineProviderBinding: the worker it points at (InstanceDefinition kind worker, api_base_url = the bound url), the
      capability there (ModuleAssignment '<kind>.engines@<worker>') and, when the consuming module is live here, the
      dependency edge '<module>@<me>-><kind>.engines' resolved to that worker with the binding as evidence;
    - every other https://<name>.isle CORS origin: that frontend (InstanceDefinition kind prf, service prf-frontend) and its
      prf-runtime-config ServiceConnection to this backend, each marked VERIFIED only when the frontend's own runtime config
      names this backend (frontend_evidence), else configured/UNVERIFIED with the reason;
    - a row this pass wrote whose binding or origin is gone: the assignment disabled, the edge unresolved, with the reason.
    -> {ok, engines, frontends, created, retired, words}"""
    import json
    me = instance_name()
    topo = next((t for t in _rows(manager, 'TopologyDefinition') if getattr(t, 'is_active', False)), None)
    topo_name = getattr(topo, 'name', '') if topo else ''
    created, engines, frontends, no_edge = [], [], [], []
    live_edges, live_assignments = set(), set()
    for b in _rows(manager, 'EngineProviderBinding'):
        kind, url = getattr(b, 'name', ''), getattr(b, 'url', '')
        if not kind or not url:
            continue
        worker = _worker_name(kind, url)
        _upsert(manager, 'InstanceDefinition', 'topology.topology_basis', 'InstanceDefinition', worker, created, kind='worker',
                service_kinds_json='["prf-engine-worker"]', api_base_url=url, topology_name=topo_name,
                notes='engine worker bound by EngineProviderBinding:%s %s' % (kind, _TAG))
        cap = '%s.engines' % kind
        a_name = '%s@%s' % (cap, worker)
        _upsert(manager, 'ModuleAssignment', 'topology.topology_modules', 'ModuleAssignment', a_name, created, module_name=cap,
                instance_name=worker, state='enabled', topology_name=topo_name,
                notes='the %s engines at %s (EngineProviderBinding:%s) %s' % (kind, url, kind, _TAG))
        live_assignments.add(a_name)
        consumer = ENGINE_CONSUMERS.get(kind)
        if consumer and consumer in live_modules:
            e_name = '%s@%s->%s' % (consumer, me, cap)
            _upsert(manager, 'ModuleDependencyEdge', 'topology.topology_modules', 'ModuleDependencyEdge', e_name, created,
                    module_name=consumer, consumer_instance_name=me, depends_on_module=cap, provider_instance_name=worker,
                    status='resolved', is_primary=True, topology_name=topo_name,
                    evidence_json=json.dumps([{'source': 'EngineProviderBinding:%s' % kind, 'url': url,
                                               'boundFrom': getattr(b, 'bound_from', ''), 'boundAt': getattr(b, 'bound_at', '')}]),
                    notes='%s on %s resolves %s through its binding row %s' % (consumer, me, cap, _TAG))
            live_edges.add(e_name)
        else:
            no_edge.append('%s (%s)' % (kind, 'no verified consumer module' if not consumer else '%s not live here' % consumer))
        engines.append({'kind': kind, 'worker': worker, 'url': url, 'consumer': consumer if consumer in live_modules else ''})
    for origin in (os.environ.get('CORS_ORIGINS') or '').split(','):
        host = urlsplit(origin.strip()).hostname or ''
        if not (host.endswith('.isle') and host.count('.') == 1) or host[:-len('.isle')] == me:
            continue
        fe = host[:-len('.isle')]
        verified, evidence = frontend_evidence(origin.strip(), me, fetch)
        _upsert(manager, 'InstanceDefinition', 'topology.topology_basis', 'InstanceDefinition', fe, created, kind='prf',
                service_kinds_json='["prf-frontend"]', public_base_url=origin.strip(), api_base_url='', topology_name=topo_name,
                notes='frontend allowed by CORS_ORIGINS on %s; %s %s' % (me, evidence, _TAG))
        _upsert(manager, 'ServiceConnection', 'topology.topology_links', 'ServiceConnection',
                'prf-frontend->prf-backend:prf-runtime-config@%s->%s' % (fe, me), created, interconnect_key='prf-runtime-config',
                from_kind='prf-frontend', to_kind='prf-backend', from_instance_name=fe, to_instance_name=me,
                artifact='%s/assets/runtime-config.json' % origin.strip(), topology_name=topo_name,
                notes='%s -> %s: %s %s' % (origin.strip(), me, evidence, _TAG))
        frontends.append({'name': fe, 'origin': origin.strip(), 'verified': verified, 'words': evidence})
    retired = []
    for r in _rows(manager, 'ModuleAssignment'):
        if _TAG in (getattr(r, 'notes', '') or '') and r.name not in live_assignments and getattr(r, 'state', '') != 'disabled':
            r.state, r.notes = 'disabled', 'its binding row is gone (%s) %s' % (source, _TAG)
            _save(manager, r)
            retired.append('ModuleAssignment:%s' % r.name)
    for r in _rows(manager, 'ModuleDependencyEdge'):
        if _TAG in (getattr(r, 'notes', '') or '') and r.name not in live_edges and getattr(r, 'status', '') != 'unresolved':
            r.status, r.provider_instance_name, r.notes = 'unresolved', '', 'its binding row is gone (%s) %s' % (source, _TAG)
            _save(manager, r)
            retired.append('ModuleDependencyEdge:%s' % r.name)
    return {'ok': True, 'engines': engines, 'frontends': frontends, 'created': created, 'retired': retired,
            'words': '%s: %d engine link%s (%s), %d frontend%s (%s)%s%s'
                     % (me, len(engines), '' if len(engines) == 1 else 's',
                        ', '.join('%s -> %s' % (e['kind'], e['worker']) for e in engines) or 'none',
                        len(frontends), '' if len(frontends) == 1 else 's',
                        ', '.join('%s %s' % (f['name'], 'verified' if f['verified'] else 'unverified') for f in frontends) or 'none',
                        '; no edge for ' + ', '.join(no_edge) if no_edge else '',
                        '; retired ' + ', '.join(retired) if retired else '')}


def on_binding_changed(manager, source='engine bound'):
    """The one entry point for whatever saves or removes an EngineProviderBinding row (islemesh ingest, the fix-11 consumer):
    refresh the engine links in the topology now instead of at the next boot. Never raises; -> describe_links' result, or
    {ok: False, words} when the topology side is unavailable here."""
    try:
        from topology.topology_peering import local_changed
        local_changed()                      # tpl-2: this backend's peers hear about the change now
    except Exception:  # noqa: BLE001
        pass
    try:
        from topology.placement_truth import live_module_set
        return describe_links(manager, live_module_set(manager.polServer), source)
    except Exception as exc:  # noqa: BLE001 - a bind must never fail because the topology refresh did
        return {'ok': False, 'words': 'topology refresh skipped: %s: %s' % (type(exc).__name__, exc)}
