"""
@cross-cutting
@module topology.provider_registry

Provider routing (top-7): cross-instance module calls resolve their
provider FROM the topology rows (ModuleAssignment +
ModuleDependencyEdge) instead of a hardcoded env URL.

Ladder (honest at every rung):
  1. An explicit env knob (MSCI_ENGINES_URL-style) ALWAYS wins —
     routing never overrides a human's configuration.
  2. Topology resolution: enabled assignments of the module, the
     edge-named provider first, then alphabetical; first REACHABLE
     candidate wins (auto-pick among live providers is the one
     sanctioned automatic behavior — it changes no configuration).
  3. Nothing reachable → {'ok': False, 'suggestion': {knob, action,
     evidence}} — same degraded shape as materialsScience.engines.
     remote, and the failing edges are marked 'degraded' with
     evidence so the Topology tab shows amber.

MANAGER is injected by polariServer at boot (set_manager); pure
functions otherwise, so the selftest runs stdlib-only with a fake
manager and a fake probe.

@consumers
  - materialsScience.engines.remote (engines_url_for ladder)
  - topology.topology_api (degraded edges surface in /graph)
"""

import json
import os
import time

from topology.topology_analysis import _loads, _rows, _scoped, \
    active_topology_name

#: The live object-tree manager — polariServer.set at boot; None in
#: selftests/host tools (resolution then refuses honestly).
MANAGER = None

#: Service kind -> published port (registry mirror idiom; the swarm
#: routing mesh publishes these on EVERY swarm node, so the manager's
#: LOCAL_IP reaches a task wherever placement put it).
PROVIDER_PORTS = {'prf-msci-engines': 9500, 'prf-cad-engines': 9600,
                  'prf-cnt-engines': 9700,
                  'pol-livekit': 7880,
                  # ret-2: the sidecar's /status API port, NOT the RNS
                  # TCP bearer (4242) — the ladder probes status.
                  'pol-reticulum': 4285}

#: Reachability cache: url -> (checked_at, alive). Keeps per-call
#: probing off the hot path.
_PROBE_CACHE = {}
_PROBE_TTL_S = 30


def set_manager(manager):
    global MANAGER
    MANAGER = manager


def _probe(url, timeout=3):
    """GET {url}/capability with a small TTL cache. Never raises."""
    now = time.time()
    cached = _PROBE_CACHE.get(url)
    if cached and now - cached[0] < _PROBE_TTL_S:
        return cached[1]
    import urllib.request
    try:
        with urllib.request.urlopen(f'{url}/capability',
                                    timeout=timeout):
            alive = True
    except Exception:
        alive = False
    _PROBE_CACHE[url] = (now, alive)
    return alive


def _instance_url(instance, machines):
    """Base URL for a provider instance, or ('', why-not)."""
    for kind in _loads(instance, 'service_kinds_json', []):
        if kind in PROVIDER_PORTS:
            port = PROVIDER_PORTS[kind]
            target = getattr(instance, 'orchestration_target', '')
            machine = machines.get(
                getattr(instance, 'machine_name', ''))
            local = machine is not None and not getattr(
                machine, 'ssh_alias', '')
            if target == 'swarm' or local:
                # swarm routing mesh / local publish: the core host's
                # IP serves the port wherever the task landed
                host = os.environ.get('LOCAL_IP', '')
                if not host:
                    return '', ('LOCAL_IP unset on this backend — '
                                'cannot build the provider URL')
                return f'http://{host}:{port}', ''
            return '', (f'instance "{getattr(instance, "name", "")}" '
                        'runs compose on a remote machine — no '
                        'address known; set the explicit URL knob or '
                        'move it into the swarm')
    return '', (f'instance "{getattr(instance, "name", "")}" carries '
                'no known provider service kind '
                f'(PROVIDER_PORTS: {sorted(PROVIDER_PORTS)})')


def _mark_edges(manager, topology, module_name, status, evidence,
                provider=''):
    """Stamp routing evidence onto the module's dependency edges."""
    for edge in _scoped(manager, 'ModuleDependencyEdge', topology):
        if getattr(edge, 'depends_on_module', '') != module_name:
            continue
        edge.status = status
        if provider:
            edge.provider_instance_name = provider
        edge.evidence_json = json.dumps([evidence])
        try:
            manager.db.saveInstanceInDB(edge)
        except Exception:
            pass


def resolve_provider(module_name, probe=_probe):
    """A live base URL for a module's provider, or an honest refusal.

    Returns {'ok': True, 'url', 'instance', 'candidates'} or
    {'ok': False, 'error', 'suggestion': {knob, action, evidence}}.
    """
    manager = MANAGER
    if manager is None:
        return {'ok': False,
                'error': 'provider registry not initialized',
                'suggestion': {
                    'evidence': 'no object-tree manager injected '
                                '(host tool or early boot)',
                    'knob': 'the explicit URL env knob',
                    'action': 'set the module\'s URL env var '
                              '(e.g. MSCI_ENGINES_URL)'}}
    topology = active_topology_name(manager)
    machines = {getattr(m, 'name', ''): m
                for m in _rows(manager, 'PolariNodeMachine')}
    instances = {getattr(i, 'name', ''): i
                 for i in _scoped(manager, 'InstanceDefinition',
                                  topology)}
    candidates = sorted(
        getattr(a, 'instance_name', '')
        for a in _scoped(manager, 'ModuleAssignment', topology)
        if getattr(a, 'module_name', '') == module_name
        and getattr(a, 'state', '') == 'enabled')
    # res-4: cost-aware ordering — benefit-appropriate machines
    # first (single-threaded module -> smallest adequate provider).
    # Honest no-op when profiles/specs are absent.
    try:
        from resources.admission_advisor import rank_candidates_by_fit
        candidates = rank_candidates_by_fit(
            manager, module_name, candidates)
    except Exception:
        pass
    # the edge-named provider goes first: it is the CONFIGURED choice
    # — cost ranking reorders only the unconfigured remainder
    for edge in _scoped(manager, 'ModuleDependencyEdge', topology):
        if (getattr(edge, 'depends_on_module', '') == module_name
                and getattr(edge, 'provider_instance_name', '')
                in candidates):
            preferred = getattr(edge, 'provider_instance_name', '')
            candidates.remove(preferred)
            candidates.insert(0, preferred)
            break
    if not candidates:
        return {'ok': False,
                'error': f'no enabled assignment of "{module_name}"',
                'suggestion': {
                    'evidence': f'topology "{topology}" assigns '
                                f'"{module_name}" to no instance',
                    'knob': 'ModuleAssignment (Topology tab / '
                            'pol allocate)',
                    'action': f'pol allocate {module_name} '
                              '<instance>'}}
    tried = []
    for name in candidates:
        instance = instances.get(name)
        if instance is None:
            tried.append({'instance': name,
                          'why': 'instance row missing'})
            continue
        url, why_not = _instance_url(instance, machines)
        if not url:
            tried.append({'instance': name, 'why': why_not})
            continue
        if probe(url):
            _mark_edges(manager, topology, module_name, 'resolved',
                        {'routing': 'live', 'picked': name,
                         'url': url, 'candidates': candidates},
                        provider=name)
            return {'ok': True, 'url': url, 'instance': name,
                    'candidates': candidates}
        tried.append({'instance': name, 'why': f'{url} unreachable'})
    evidence = {'routing': 'all candidates failed', 'tried': tried,
                'candidates': candidates}
    _mark_edges(manager, topology, module_name, 'degraded', evidence)
    return {'ok': False,
            'error': f'no reachable provider of "{module_name}"',
            'suggestion': {
                'evidence': json.dumps(tried),
                'knob': 'the provider instance (ModuleAssignment / '
                        'placement) or the explicit URL env knob',
                'action': 'pol topology diff (is the provider '
                          'running?), pol topology apply --plan, or '
                          f'pol allocate {module_name} <instance>'}}
