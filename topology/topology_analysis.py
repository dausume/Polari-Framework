"""
@cross-cutting
@module topology.topology_analysis

Pure topology logic (top-1): validation (evidence-bearing findings,
each NAMING the knob/action that fixes it — aqp-1 idiom), dependency-
edge resolution, the graph payload the Topology tab renders, and the
desired-vs-observed drift report.

NO framework imports — every function takes `manager` duck-typed as
anything with an `objectTables` dict, so selftests run stdlib-only
with SimpleNamespace rows.

Findings/drift rows are SUGGESTIONS: they carry the exact `pol`
command or row edit that fixes them and are never auto-applied
(knobs-and-suggestions).

@consumers
  - topology.topology_api / topology.selftest_topology
  - polari-cli scripts/topology.sh (top-2/3 validate/diff)
"""

import json

from topology.topology_constants import (
    DB_BACKENDS, ENV_TIERS, INTERCONNECT_KEYS, KNOWN_SERVICE_KINDS,
    ORCHESTRATION_TARGETS, SERVICE_LABEL_ALIASES,
)


def _rows(manager, class_name):
    """All rows of a class as a list (objectTables holds id->row)."""
    table = (getattr(manager, 'objectTables', None) or {}).get(
        class_name, {})
    return list(table.values()) if isinstance(table, dict) else list(table)


def _loads(row, attr, default):
    try:
        text = getattr(row, attr, '') or ''
        return json.loads(text) if text else default
    except Exception:
        return default


def _scoped(manager, class_name, topology_name):
    """Rows of a class belonging to one topology."""
    return [r for r in _rows(manager, class_name)
            if getattr(r, 'topology_name', '') == topology_name]


def active_topology_name(manager):
    """The active TopologyDefinition's name, or '' when none is."""
    for row in _rows(manager, 'TopologyDefinition'):
        if getattr(row, 'is_active', False):
            return getattr(row, 'name', '')
    return ''


def _finding(severity, check, subject, evidence, knob, action):
    return {'severity': severity, 'check': check, 'subject': subject,
            'evidence': evidence, 'knob': knob, 'action': action}


def validate_topology(manager, topology_name):
    """Evidence-bearing findings over one topology's rows.

    Structural checks only (references + vocabulary); the exporter
    adds render-level checks (port collisions, volume state) in top-3
    where the registry/manifests are on disk.
    """
    defs = [r for r in _rows(manager, 'TopologyDefinition')
            if getattr(r, 'name', '') == topology_name]
    if not defs:
        return {'ok': False,
                'error': f'no TopologyDefinition named "{topology_name}"'}
    findings = []
    machines = {getattr(m, 'name', ''): m
                for m in _rows(manager, 'PolariNodeMachine')}
    targets = {getattr(t, 'name', ''): t
               for t in _rows(manager, 'OrchestrationTarget')}
    instances = _scoped(manager, 'InstanceDefinition', topology_name)
    inst_by_name = {}
    for inst in instances:
        iname = getattr(inst, 'name', '')
        if iname in inst_by_name:
            findings.append(_finding(
                'error', 'duplicate-instance', iname,
                f'two InstanceDefinition rows named "{iname}" in '
                f'topology "{topology_name}"',
                'InstanceDefinition.name',
                'rename or delete one of the duplicate rows'))
        inst_by_name[iname] = inst

    for inst in instances:
        iname = getattr(inst, 'name', '')
        machine = getattr(inst, 'machine_name', '')
        target = (getattr(inst, 'orchestration_target', '')
                  or getattr(defs[0], 'default_target', 'compose'))
        if machine and machine not in machines:
            findings.append(_finding(
                'error', 'unknown-machine', iname,
                f'instance "{iname}" is pinned to machine "{machine}" '
                'but no PolariNodeMachine row has that name',
                'InstanceDefinition.machine_name',
                'add the machine to nodes.yml and `pol topology push`, '
                'or repoint machine_name at an existing machine'))
        if target not in ORCHESTRATION_TARGETS:
            findings.append(_finding(
                'error', 'unknown-target', iname,
                f'orchestration_target "{target}" is not one of '
                f'{ORCHESTRATION_TARGETS}',
                'InstanceDefinition.orchestration_target',
                'pick a known target'))
        elif target in targets and not getattr(
                targets[target], 'available', True):
            findings.append(_finding(
                'error', 'target-unavailable', iname,
                f'instance "{iname}" targets "{target}" which is '
                'marked unavailable '
                f'({getattr(targets[target], "description", "")})',
                'OrchestrationTarget.available',
                'use compose or swarm until that target lands'))
        if (target == 'swarm' and machine in machines
                and getattr(machines[machine], 'swarm_role',
                            'none') == 'none'):
            findings.append(_finding(
                'error', 'machine-not-in-swarm', iname,
                f'instance "{iname}" targets swarm pinned to '
                f'"{machine}" whose swarm_role is "none"',
                'PolariNodeMachine.swarm_role',
                f'`pol swarm join {machine}` (top-4), then re-validate'))
        db = getattr(inst, 'db_backend', '')
        if db not in DB_BACKENDS:
            findings.append(_finding(
                'error', 'unknown-db-backend', iname,
                f'db_backend "{db}" is not one of {DB_BACKENDS}',
                'InstanceDefinition.db_backend',
                'pick a `pol db` backend'))
        env = getattr(inst, 'env_tier', '')
        if env not in ENV_TIERS:
            findings.append(_finding(
                'warn', 'unknown-env-tier', iname,
                f'env_tier "{env}" is not one of {ENV_TIERS}',
                'InstanceDefinition.env_tier',
                'pick a render-pipeline env tier'))
        for kind in _loads(inst, 'service_kinds_json', []):
            if kind not in KNOWN_SERVICE_KINDS:
                findings.append(_finding(
                    'warn', 'unknown-service-kind', iname,
                    f'service kind "{kind}" is not in the embedded '
                    'registry mirror',
                    'topology_constants.KNOWN_SERVICE_KINDS',
                    'add the kind to pol-build/registry/services.yml '
                    'and refresh the mirror (`pol topology push`)'))

    for asg in _scoped(manager, 'ModuleAssignment', topology_name):
        aname = getattr(asg, 'name', '')
        iname = getattr(asg, 'instance_name', '')
        if iname not in inst_by_name:
            findings.append(_finding(
                'error', 'assignment-unknown-instance', aname,
                f'assignment "{aname}" targets instance "{iname}" '
                'which does not exist in this topology',
                'ModuleAssignment.instance_name',
                'repoint the assignment or add the instance'))

    enabled = {}
    for asg in _scoped(manager, 'ModuleAssignment', topology_name):
        if getattr(asg, 'state', '') == 'enabled':
            enabled.setdefault(
                getattr(asg, 'module_name', ''), []).append(
                getattr(asg, 'instance_name', ''))
    for edge in _scoped(manager, 'ModuleDependencyEdge', topology_name):
        ename = getattr(edge, 'name', '')
        dep = getattr(edge, 'depends_on_module', '')
        provider = getattr(edge, 'provider_instance_name', '')
        if not provider or provider not in inst_by_name:
            candidates = enabled.get(dep, [])
            findings.append(_finding(
                'error', 'edge-without-provider', ename,
                f'"{getattr(edge, "module_name", "")}@'
                f'{getattr(edge, "consumer_instance_name", "")}" '
                f'depends on "{dep}" but '
                + (f'its provider "{provider}" does not exist'
                   if provider else
                   f'no enabled assignment of "{dep}" exists '
                   f'(candidates: {candidates or "none"})'),
                'ModuleAssignment (module placement)',
                f'`pol allocate {dep} <instance>` or drag the '
                f'"{dep}" chip onto an instance in the Topology tab'))

    for conn in _scoped(manager, 'ServiceConnection', topology_name):
        cname = getattr(conn, 'name', '')
        key = getattr(conn, 'interconnect_key', '')
        if key not in INTERCONNECT_KEYS:
            findings.append(_finding(
                'error', 'unknown-interconnect', cname,
                f'interconnect_key "{key}" is not in the registry '
                f'mirror {INTERCONNECT_KEYS}',
                'ServiceConnection.interconnect_key',
                'use a registry interconnect, or add one to '
                'pol-build/registry/services.yml first'))
        for side in ('from_instance_name', 'to_instance_name'):
            iname = getattr(conn, side, '')
            if iname and iname not in inst_by_name:
                findings.append(_finding(
                    'error', 'connection-unknown-instance', cname,
                    f'{side} "{iname}" does not exist in this '
                    'topology',
                    f'ServiceConnection.{side}',
                    'repoint the connection or add the instance'))

    errors = [f for f in findings if f['severity'] == 'error']
    return {'ok': True, 'topology': topology_name,
            'valid': not errors, 'findings': findings,
            'errorCount': len(errors),
            'warnCount': len(findings) - len(errors)}


def resolve_edges(manager, topology_name):
    """Recompute every edge's provider from enabled assignments.

    Deterministic: keeps a still-valid existing provider, otherwise
    picks the alphabetically-first candidate. Mutates edge rows and
    returns what changed; the caller persists (API) or not (selftest).
    """
    enabled = {}
    for asg in _scoped(manager, 'ModuleAssignment', topology_name):
        if getattr(asg, 'state', '') == 'enabled':
            enabled.setdefault(
                getattr(asg, 'module_name', ''), []).append(
                getattr(asg, 'instance_name', ''))
    changed, edges = [], _scoped(
        manager, 'ModuleDependencyEdge', topology_name)
    for edge in edges:
        dep = getattr(edge, 'depends_on_module', '')
        candidates = sorted(enabled.get(dep, []))
        old = (getattr(edge, 'provider_instance_name', ''),
               getattr(edge, 'status', ''))
        if candidates:
            provider = (old[0] if old[0] in candidates
                        else candidates[0])
            status = 'resolved'
            evidence = [{'candidates': candidates,
                         'picked': provider,
                         'reason': ('kept existing provider'
                                    if provider == old[0]
                                    else 'alphabetically first among '
                                         'enabled assignments')}]
        else:
            provider, status = '', 'unresolved'
            evidence = [{'candidates': [],
                         'reason': f'no enabled assignment of "{dep}"',
                         'knob': 'ModuleAssignment',
                         'action': f'`pol allocate {dep} <instance>`'}]
        edge.provider_instance_name = provider
        edge.status = status
        edge.evidence_json = json.dumps(evidence)
        if (provider, status) != old:
            changed.append({'edge': getattr(edge, 'name', ''),
                            'from': {'provider': old[0],
                                     'status': old[1]},
                            'to': {'provider': provider,
                                   'status': status}})
    return {'ok': True, 'topology': topology_name,
            'edges': len(edges), 'changed': changed}


def graph_payload(manager, topology_name):
    """Everything the Topology tab renders, JSON fields decoded."""
    defs = [r for r in _rows(manager, 'TopologyDefinition')
            if getattr(r, 'name', '') == topology_name]
    if not defs:
        return {'ok': False,
                'error': f'no TopologyDefinition named "{topology_name}"'}
    d = defs[0]

    def machine_dict(m):
        return {'name': getattr(m, 'name', ''),
                'sshAlias': getattr(m, 'ssh_alias', ''),
                'arch': getattr(m, 'arch', ''),
                'memGb': getattr(m, 'mem_gb', 0.0),
                'roles': _loads(m, 'roles_json', []),
                'swarmRole': getattr(m, 'swarm_role', 'none'),
                'source': getattr(m, 'source', ''),
                'notes': getattr(m, 'notes', ''),
                # res-1: observed device resources (0 = not observed)
                'logicalCpus': getattr(m, 'logical_cpus', 0),
                'physicalCpus': getattr(m, 'physical_cpus', 0),
                'totalRamMb': getattr(m, 'total_ram_mb', 0.0),
                'availableRamMb': getattr(m, 'available_ram_mb', 0.0),
                'totalDiskMb': getattr(m, 'total_disk_mb', 0.0),
                'freeDiskMb': getattr(m, 'free_disk_mb', 0.0),
                'cgroupRamLimitMb':
                    getattr(m, 'cgroup_ram_limit_mb', 0.0),
                'load': _loads(m, 'load_snapshot_json', {}),
                'resourceSource':
                    getattr(m, 'resource_source', 'unknown'),
                'resourceObservedAt':
                    getattr(m, 'resource_observed_at', '')}

    def instance_dict(i):
        return {'name': getattr(i, 'name', ''),
                'kind': getattr(i, 'kind', ''),
                'serviceKinds': _loads(i, 'service_kinds_json', []),
                'replicas': getattr(i, 'replicas', 1),
                'envTier': getattr(i, 'env_tier', ''),
                'machineName': getattr(i, 'machine_name', ''),
                'placementConstraint':
                    getattr(i, 'placement_constraint', ''),
                'dbBackend': getattr(i, 'db_backend', ''),
                'imageTag': getattr(i, 'image_tag', ''),
                'orchestrationTarget':
                    getattr(i, 'orchestration_target', ''),
                'notes': getattr(i, 'notes', '')}

    # res-4: capacity vs allocated floors per machine (lazy import —
    # absent profiles simply omit the block, never guessed).
    allocations = {}
    try:
        from resources.admission_advisor import node_allocation
        allocations = {name: view.get('allocation', {})
                       for name, view in node_allocation(
                           manager, topology_name).items()}
    except Exception:
        pass

    def machine_with_allocation(m):
        d = machine_dict(m)
        alloc = allocations.get(d['name'])
        if alloc:
            d['allocation'] = alloc
        return d

    return {
        'ok': True,
        'topology': {
            'name': getattr(d, 'name', ''),
            'description': getattr(d, 'description', ''),
            'defaultTarget': getattr(d, 'default_target', ''),
            'status': getattr(d, 'status', ''),
            'isActive': getattr(d, 'is_active', False),
            'validatedAt': getattr(d, 'validated_at', ''),
            'findings': _loads(d, 'validation_findings_json', []),
            'schemaVersion': getattr(d, 'schema_version', '1'),
        },
        'machines': [machine_with_allocation(m) for m in
                     _rows(manager, 'PolariNodeMachine')],
        'instances': [instance_dict(i) for i in
                      _scoped(manager, 'InstanceDefinition',
                              topology_name)],
        'assignments': [
            {'name': getattr(a, 'name', ''),
             'moduleName': getattr(a, 'module_name', ''),
             'instanceName': getattr(a, 'instance_name', ''),
             'state': getattr(a, 'state', ''),
             'notes': getattr(a, 'notes', '')}
            for a in _scoped(manager, 'ModuleAssignment',
                             topology_name)],
        'edges': [
            {'name': getattr(e, 'name', ''),
             'moduleName': getattr(e, 'module_name', ''),
             'consumerInstanceName':
                 getattr(e, 'consumer_instance_name', ''),
             'dependsOnModule': getattr(e, 'depends_on_module', ''),
             'providerInstanceName':
                 getattr(e, 'provider_instance_name', ''),
             'status': getattr(e, 'status', ''),
             'evidence': _loads(e, 'evidence_json', [])}
            for e in _scoped(manager, 'ModuleDependencyEdge',
                             topology_name)],
        'connections': [
            {'name': getattr(c, 'name', ''),
             'interconnectKey': getattr(c, 'interconnect_key', ''),
             'fromKind': getattr(c, 'from_kind', ''),
             'toKind': getattr(c, 'to_kind', ''),
             'fromInstanceName':
                 getattr(c, 'from_instance_name', ''),
             'toInstanceName': getattr(c, 'to_instance_name', ''),
             'artifact': getattr(c, 'artifact', ''),
             'notes': getattr(c, 'notes', '')}
            for c in _scoped(manager, 'ServiceConnection',
                             topology_name)],
    }


def _latest_observations(manager, topology_name):
    """Latest TopologyObservation per node (ISO timestamps sort)."""
    latest = {}
    for obs in _rows(manager, 'TopologyObservation'):
        if getattr(obs, 'topology_name', '') != topology_name:
            continue
        node = getattr(obs, 'node_name', '')
        stamp = getattr(obs, 'observed_at', '')
        if node not in latest or stamp > getattr(
                latest[node], 'observed_at', ''):
            latest[node] = obs
    return latest


def _observed_entries(obs):
    """Normalize one observation's services to (name, kinds) pairs.

    Entries may be plain names or reporter dicts {name, service,
    state, image}. The compose/swarm service LABEL resolves to a
    registry kind (directly or via SERVICE_LABEL_ALIASES); the raw
    container name stays as a substring fallback."""
    entries = []
    for s in _loads(obs, 'services_json', []):
        if isinstance(s, dict):
            name = s.get('name', '')
            label = s.get('service', '')
        else:
            name, label = str(s), ''
        kinds = set()
        if label in KNOWN_SERVICE_KINDS:
            kinds.add(label)
        if label in SERVICE_LABEL_ALIASES:
            kinds.add(SERVICE_LABEL_ALIASES[label])
        entries.append((name, kinds))
    return entries


def drift_report(manager, topology_name):
    """Desired vs latest observations. Every row carries the
    suggested `pol` command (suggestion, never auto-run).

    Matching prefers the reporter's compose/swarm service labels
    (exact kind or alias); container-name substring is the fallback
    for label-less observations."""
    instances = _scoped(manager, 'InstanceDefinition', topology_name)
    if not instances:
        return {'ok': False,
                'error': f'no instances in topology "{topology_name}"'}
    latest = _latest_observations(manager, topology_name)
    rows = []
    desired_kinds = set()
    for inst in instances:
        machine = getattr(inst, 'machine_name', '')
        iname = getattr(inst, 'name', '')
        kinds = _loads(inst, 'service_kinds_json', [])
        desired_kinds.update(kinds)
        obs = latest.get(machine)
        if obs is None:
            rows.append({
                'kind': 'unobserved', 'subject': iname,
                'machine': machine,
                'evidence': f'no TopologyObservation for machine '
                            f'"{machine}" — desired state cannot be '
                            'compared',
                'suggestedCommand': 'pol topology report'})
            continue
        observed = _observed_entries(obs)
        for kind in kinds:
            if not any(kind in okinds or kind in name
                       for name, okinds in observed):
                rows.append({
                    'kind': 'missing-service', 'subject': iname,
                    'machine': machine, 'serviceKind': kind,
                    'evidence': f'"{kind}" not among {len(observed)} '
                                f'observed services on "{machine}" at '
                                f'{getattr(obs, "observed_at", "")}',
                    'suggestedCommand': 'pol topology apply --plan'})
    for machine, obs in latest.items():
        for name, okinds in _observed_entries(obs):
            if not (okinds & desired_kinds) and not any(
                    kind in name for kind in desired_kinds):
                rows.append({
                    'kind': 'unexpected-service', 'subject': name,
                    'machine': machine,
                    'evidence': f'"{name}" runs on "{machine}" but no '
                                'instance in the topology desires it',
                    'suggestedCommand':
                        'add it to an InstanceDefinition (Topology '
                        'tab) or stop it on the node — your call'})
    rows.extend(suggest_reallocations(manager, topology_name))
    return {'ok': True, 'topology': topology_name,
            'observedNodes': sorted(latest.keys()),
            'inDrift': bool(rows), 'rows': rows}


def suggest_reallocations(manager, topology_name):
    """Evidence-bearing reallocation SUGGESTIONS (top-8) for degraded
    dependency edges — one-click via the named `pol allocate`
    command, never auto-applied.

    An edge goes 'degraded' when provider routing exhausted every
    live candidate (provider_registry stamps the tried-list as
    evidence). The suggestion offers the enabled alternatives, or
    starting the configured provider when it is the only one."""
    rows = []
    enabled = {}
    for asg in _scoped(manager, 'ModuleAssignment', topology_name):
        if getattr(asg, 'state', '') == 'enabled':
            enabled.setdefault(
                getattr(asg, 'module_name', ''), []).append(
                getattr(asg, 'instance_name', ''))
    for edge in _scoped(manager, 'ModuleDependencyEdge',
                        topology_name):
        if getattr(edge, 'status', '') != 'degraded':
            continue
        module = getattr(edge, 'depends_on_module', '')
        provider = getattr(edge, 'provider_instance_name', '')
        alternatives = sorted(i for i in enabled.get(module, [])
                              if i != provider)
        evidence = _loads(edge, 'evidence_json', [])
        if alternatives:
            command = f'pol allocate {module} {alternatives[0]}'
            why = (f'provider "{provider}" is unreachable; '
                   f'"{module}" is also enabled on '
                   f'{alternatives} — moving the edge there is '
                   'one command')
        else:
            command = 'pol topology apply --plan'
            why = (f'provider "{provider}" is unreachable and no '
                   f'alternative instance carries "{module}" — '
                   'bring the provider back up, or '
                   f'`pol allocate {module} <instance>` to place '
                   'it elsewhere first')
        rows.append({
            'kind': 'reallocation-suggested',
            'subject': getattr(edge, 'name', ''),
            'machine': '',
            'evidence': (f'{why}. Routing evidence: '
                         f'{json.dumps(evidence)[:400]}'),
            'suggestedCommand': command})
    # res-4: resource-efficiency signal beyond degraded-only — a
    # single-threaded module holding a big node while a scaling
    # module sits cramped. Lazy import; absent profiles → no rows.
    try:
        from resources.admission_advisor import efficiency_suggestions
        rows.extend(efficiency_suggestions(manager, topology_name))
    except Exception:
        pass
    return rows
