"""
@cross-cutting
@module resources.admission_advisor
@tags @xc:bindings

Admission advisor (res-4, the headline): a user adds a module and
Polari assesses its optimum environment against the LIVE topology:

  route-to-storage        — it's data; it belongs in redis / sqlite /
                            mariadb, no compute placement needed.
  fits-as-is              — an adequate node exists at the optimum.
                            Benefit-aware: a strictly single-threaded
                            module goes to the SMALLEST adequate node
                            (big-compute nodes stay free for work
                            that scales); a scaling module goes to
                            the biggest.
  fits-with-reallocation  — no free optimal spot, but a named move
                            frees one.
  would-break             — no placement without violating a floor;
                            the conflict, the limiting resource, and
                            what to add are named.

Every verdict is an evidence-bearing SUGGESTION pointing at the
ModuleAssignment / InstanceDefinition knobs (`pol allocate …`) —
never auto-applied (knobs-and-suggestions). Nodes without observed
specs and modules without profiles are named, not guessed
(honest absence).

@consumers
  - resources.admission_api (/api/topology/admission, /fit,
    /placement-suggestions)
  - topology.topology_analysis.suggest_reallocations (efficiency
    signal), topology.provider_registry (cost-aware ranking)
"""

import json

from resources.node_resources import machine_resources_dict
from resources.profile_analysis import declared_profile, find_profile

#: 'tight' when any dimension of a set-feasibility check uses more
#: than this fraction of the node's budget.
TIGHT_FRACTION = 0.80


def _rows(manager, class_name):
    tables = getattr(manager, 'objectTables', None) or {}
    return list((tables.get(class_name) or {}).values())


def _single_threaded(profile):
    return (int(getattr(profile, 'thread_ceiling', 1) or 1) <= 1
            or getattr(profile, 'cpu_benefit', 'none') == 'none')


def node_placements(manager, topology_name=''):
    """module -> machine placements via enabled ModuleAssignments and
    the instances' machine pins."""
    instances = {getattr(i, 'name', ''): i
                 for i in _rows(manager, 'InstanceDefinition')}
    placements = []
    for a in _rows(manager, 'ModuleAssignment'):
        if getattr(a, 'state', '') != 'enabled':
            continue
        if topology_name and getattr(
                a, 'topology_name', '') != topology_name:
            continue
        inst = instances.get(getattr(a, 'instance_name', ''))
        machine = getattr(inst, 'machine_name', '') if inst else ''
        placements.append({
            'module': getattr(a, 'module_name', ''),
            'instance': getattr(a, 'instance_name', ''),
            'machine': machine})
    return placements


def node_allocation(manager, topology_name=''):
    """Per-machine capacity vs allocated floors (+ the unprofiled
    modules named — their floors are NOT guessed)."""
    placements = node_placements(manager, topology_name)
    out = {}
    for m in _rows(manager, 'PolariNodeMachine'):
        view = machine_resources_dict(m)
        placed = [p for p in placements
                  if p['machine'] == view['name']]
        alloc_threads, alloc_ram, unprofiled = 0, 0.0, []
        for p in placed:
            profile = find_profile(manager, p['module'])
            if profile is None:
                unprofiled.append(p['module'])
                continue
            alloc_threads += int(
                getattr(profile, 'min_threads', 1) or 1)
            alloc_ram += float(
                getattr(profile, 'min_ram_mb', 0) or 0)
        view['allocation'] = {
            'modules': sorted(p['module'] for p in placed),
            'minThreads': alloc_threads,
            'minRamMb': alloc_ram,
            'freeThreads': max(0, view['logicalCpus']
                               - alloc_threads),
            'unprofiled': sorted(unprofiled),
        }
        out[view['name']] = view
    return out


def _fits_on(profile, node):
    """(fits, limiting) — the module's floor vs one observed node."""
    need_ram = float(getattr(profile, 'min_ram_mb', 0) or 0)
    need_disk = (float(getattr(profile, 'min_disk_mb', 0) or 0)
                 + float(getattr(profile, 'image_mb', 0) or 0))
    need_threads = int(getattr(profile, 'min_threads', 1) or 1)
    if need_ram > node['availableRamMb']:
        return False, (f'RAM: needs {need_ram:.0f}MB, '
                       f'{node["availableRamMb"]:.0f}MB available')
    if need_disk > node['freeDiskMb']:
        return False, (f'disk: needs {need_disk:.0f}MB, '
                       f'{node["freeDiskMb"]:.0f}MB free')
    if need_threads > node['allocation']['freeThreads']:
        return False, (f'threads: needs {need_threads}, '
                       f'{node["allocation"]["freeThreads"]} '
                       'unallocated')
    return True, ''


def _rank(profile, nodes):
    """Benefit-aware ordering of adequate nodes + the rationale."""
    if (getattr(profile, 'ram_benefit', 'none') != 'none'
            and getattr(profile, 'cpu_benefit', 'none') == 'none'):
        # RAM-bound wins over smallest-node: a single-threaded but
        # RAM-hungry module still benefits from the roomy node.
        ranked = sorted(nodes, key=lambda n: -n['availableRamMb'])
        why = 'RAM-bound — the node with the most free RAM'
    elif _single_threaded(profile):
        ranked = sorted(nodes, key=lambda n: (
            n['logicalCpus'], n['totalRamMb']))
        why = ('single-threaded (thread_ceiling 1 / no cpu benefit) '
               '— smallest adequate node, leaving big-compute nodes '
               'free for work that scales')
    else:
        ranked = sorted(nodes, key=lambda n: (
            -n['logicalCpus'], -n['availableRamMb']))
        why = (f'scales with cores (ceiling '
               f'{getattr(profile, "thread_ceiling", 1)}, '
               f'{getattr(profile, "cpu_benefit", "")}) — the '
               'biggest adequate node')
    return ranked, why


def _instances_on(manager, machine_name):
    return sorted(
        getattr(i, 'name', '')
        for i in _rows(manager, 'InstanceDefinition')
        if getattr(i, 'machine_name', '') == machine_name)


def assess_module_admission(manager, module_name, topology_name=''):
    """The verdict for adding one module to the live topology."""
    profile = find_profile(manager, module_name)
    profile_report = None
    if profile is None:
        profile_report = declared_profile(manager, module_name)
        if not profile_report.get('ok'):
            return {'ok': False, 'module': module_name,
                    'error': profile_report.get('error')}
        profile = profile_report['profile']
    base = {'ok': True, 'module': module_name,
            'profile': {'character': getattr(profile, 'character', ''),
                        'fidelity': getattr(profile, 'fidelity', ''),
                        'declaredNow': bool(profile_report)}}

    # 1. data -> the storage tier, not a compute node
    if getattr(profile, 'character', '') == 'data':
        from resources.profile_analysis import recommend_backend
        rec = recommend_backend(profile)
        backend = getattr(profile, 'recommended_backend', '') \
            or rec['backend']
        carriers = sorted(
            getattr(i, 'name', '')
            for i in _rows(manager, 'InstanceDefinition')
            if backend in (getattr(i, 'db_backend', '') or ''))
        base.update({
            'verdict': 'route-to-storage', 'backend': backend,
            'reason': rec['reason'], 'computeFootprint': 'negligible',
            'suggestion': {
                'evidence': f'character=data: {rec["reason"]}',
                'knob': 'InstanceDefinition.db_backend / '
                        'ModuleAssignment',
                'action': (f'assign "{module_name}" to an instance '
                           f'already running {backend} '
                           f'({carriers or "none seeded yet"})')}})
        return base

    # 2. compute/balanced -> fit against the observed inventory
    allocation = node_allocation(manager, topology_name)
    observed = [n for n in allocation.values() if n['hasSpecs']]
    unobserved = sorted(n['name'] for n in allocation.values()
                        if not n['hasSpecs'])
    if not observed:
        base.update({
            'ok': False, 'verdict': 'unknown',
            'error': 'no node has observed resources — observe '
                     'first, then re-ask',
            'suggestion': {
                'evidence': f'unobserved nodes: {unobserved}',
                'knob': 'PolariNodeMachine.system_info_url',
                'action': 'POST /api/topology/nodes/{name}/'
                          'refresh-resources'}})
        return base

    verdicts = []
    adequate = []
    for node in observed:
        fits, limiting = _fits_on(profile, node)
        verdicts.append({'node': node['name'], 'fits': fits,
                         'limiting': limiting})
        if fits:
            adequate.append(node)
    base['perNode'] = verdicts
    if unobserved:
        base['unobservedNodes'] = unobserved

    if adequate:
        ranked, why = _rank(profile, adequate)
        best = ranked[0]
        instances = _instances_on(manager, best['name'])
        base.update({
            'verdict': 'fits-as-is', 'node': best['name'],
            'rationale': why,
            'headroom': {
                'freeThreads': best['allocation']['freeThreads'],
                'availableRamMb': best['availableRamMb'],
                'freeDiskMb': best['freeDiskMb']},
            'suggestion': {
                'evidence': f'{why}; floor fits '
                            f'({json.dumps(verdicts)})'[:500],
                'knob': 'ModuleAssignment (Topology tab / '
                        'pol allocate)',
                'action': f'pol allocate {module_name} '
                          f'{instances[0] if instances else "<new instance on " + best["name"] + ">"}'}})
        return base

    # 3. no adequate node — can a move free one?
    placements = node_placements(manager, topology_name)
    for node in observed:
        fits, limiting = _fits_on(profile, node)
        if 'threads' not in limiting:
            continue  # only thread floors are freed by moving
        for p in placements:
            if p['machine'] != node['name']:
                continue
            moved = find_profile(manager, p['module'])
            if moved is None or not _single_threaded(moved):
                continue
            for dest in observed:
                if dest['name'] == node['name']:
                    continue
                d_fits, _ = _fits_on(moved, dest)
                if not d_fits:
                    continue
                freed = int(getattr(moved, 'min_threads', 1) or 1)
                node_after = dict(node)
                node_after['allocation'] = dict(node['allocation'])
                node_after['allocation']['freeThreads'] += freed
                ok_after, _ = _fits_on(profile, node_after)
                if not ok_after:
                    continue
                dest_instances = _instances_on(manager, dest['name'])
                move_to = (dest_instances[0] if dest_instances
                           else f'<new instance on {dest["name"]}>')
                base.update({
                    'verdict': 'fits-with-reallocation',
                    'node': node['name'],
                    'moves': [{'module': p['module'],
                               'from': p['instance'],
                               'to': move_to,
                               'machineFrom': node['name'],
                               'machineTo': dest['name']}],
                    'netEfficiencyGain':
                        f'"{p["module"]}" is single-threaded — it '
                        f'loses nothing on {dest["name"]}, freeing '
                        f'{freed} thread(s) on {node["name"]} for '
                        f'"{module_name}"',
                    'suggestion': {
                        'evidence': f'{node["name"]} blocked by '
                                    f'{limiting}; the move resolves '
                                    'it',
                        'knob': 'ModuleAssignment',
                        'action': f'pol allocate {p["module"]} '
                                  f'{move_to} && pol allocate '
                                  f'{module_name} <instance on '
                                  f'{node["name"]}>'}})
                return base

    # 4. would-break
    worst = min((v for v in verdicts), key=lambda v: v['fits'])
    limits = sorted({v['limiting'].split(':')[0]
                     for v in verdicts if v['limiting']})
    base.update({
        'verdict': 'would-break',
        'conflict': f'no node can hold the floor of '
                    f'"{module_name}" without violating existing '
                    'floors',
        'limitingResource': ', '.join(limits),
        'perNode': verdicts,
        'needed': f'free {limits[0]} on a node, move a module off, '
                  'or add a node',
        'suggestion': {
            'evidence': json.dumps(verdicts)[:500],
            'knob': 'the topology (add a node / free a floor)',
            'action': 'pol topology apply --plan after freeing '
                      f'{limits[0]}; nothing was changed'}})
    return base


def assess_set_feasibility(manager, module_names, node_name):
    """Can this SET of modules be pulled down and run on this node?"""
    allocation = node_allocation(manager)
    node = allocation.get(node_name)
    if node is None:
        return {'ok': False,
                'error': f'no PolariNodeMachine named "{node_name}"'}
    if not node['hasSpecs']:
        return {'ok': False, 'node': node_name,
                'error': 'node has no observed resources — observe '
                         'first (POST /api/topology/nodes/'
                         f'{node_name}/refresh-resources)'}
    per_module, missing = [], []
    pull_disk = run_ram = 0.0
    threads = 0
    for name in module_names:
        profile = find_profile(manager, name)
        if profile is None:
            missing.append(name)
            continue
        image = float(getattr(profile, 'image_mb', 0) or 0) \
            + float(getattr(profile, 'deps_mb', 0) or 0)
        disk = float(getattr(profile, 'min_disk_mb', 0) or 0)
        ram = float(getattr(profile, 'min_ram_mb', 0) or 0)
        th = int(getattr(profile, 'min_threads', 1) or 1)
        pull_disk += image + disk
        run_ram += ram
        threads += th
        per_module.append({'module': name, 'pullMb': image,
                           'minDiskMb': disk, 'minRamMb': ram,
                           'minThreads': th,
                           'fidelity': getattr(profile, 'fidelity',
                                               '')})
    use = {
        'disk': pull_disk / node['freeDiskMb']
        if node['freeDiskMb'] else 1e9,
        'ram': run_ram / node['availableRamMb']
        if node['availableRamMb'] else 1e9,
        'threads': threads / node['allocation']['freeThreads']
        if node['allocation']['freeThreads'] else 1e9,
    }
    limiting = max(use, key=use.get)
    if any(u > 1.0 for u in use.values()):
        feasible = 'no'
    elif any(u > TIGHT_FRACTION for u in use.values()):
        feasible = 'tight'
    else:
        feasible = 'yes'
    report = {'ok': True, 'node': node_name, 'feasible': feasible,
              'limitingResource': limiting,
              'utilization': {k: round(v, 3) if v < 1e8 else None
                              for k, v in use.items()},
              'totals': {'pullDiskMb': pull_disk,
                         'minRamMb': run_ram,
                         'minThreads': threads},
              'headroom': {
                  'freeDiskMb': node['freeDiskMb'],
                  'availableRamMb': node['availableRamMb'],
                  'freeThreads':
                      node['allocation']['freeThreads']},
              'perModule': per_module}
    if missing:
        report['unprofiled'] = sorted(missing)
        report['note'] = ('unprofiled modules NOT counted — declare '
                          'or measure them first for a full answer')
    return report


def efficiency_suggestions(manager, topology_name=''):
    """Resource-efficiency swaps beyond degraded-only (res-4): a
    single-threaded module holding the biggest node while a scaling
    module sits on a smaller one."""
    allocation = node_allocation(manager, topology_name)
    observed = [n for n in allocation.values() if n['hasSpecs']]
    if len(observed) < 2:
        return []
    biggest = max(observed, key=lambda n: n['logicalCpus'])
    placements = node_placements(manager, topology_name)
    rows = []
    for p in placements:
        if p['machine'] != biggest['name']:
            continue
        prof = find_profile(manager, p['module'])
        if prof is None or not _single_threaded(prof):
            continue
        for q in placements:
            if q['machine'] in ('', biggest['name']):
                continue
            scal = find_profile(manager, q['module'])
            if scal is None or _single_threaded(scal):
                continue
            small = allocation.get(q['machine'])
            if not small or small['logicalCpus'] \
                    >= biggest['logicalCpus']:
                continue
            rows.append({
                'kind': 'efficiency-swap-suggested',
                'subject': f'{p["module"]}@{biggest["name"]}',
                'machine': biggest['name'],
                'evidence':
                    f'"{p["module"]}" (single-threaded) occupies '
                    f'{biggest["name"]} ({biggest["logicalCpus"]}c) '
                    f'while "{q["module"]}" (thread_ceiling '
                    f'{getattr(scal, "thread_ceiling", "?")}) sits '
                    f'on {q["machine"]} '
                    f'({small["logicalCpus"]}c) — swapping gains '
                    'parallel headroom and loses nothing',
                'suggestedCommand':
                    f'pol allocate {p["module"]} {q["instance"]} && '
                    f'pol allocate {q["module"]} {p["instance"]}'})
            break
    return rows


def rank_candidates_by_fit(manager, module_name, candidate_names):
    """Order provider candidates by benefit-aware fit (cost-aware
    resolve_provider). Unknown data → original order (honest no-op)."""
    profile = find_profile(manager, module_name)
    if profile is None:
        return list(candidate_names)
    allocation = node_allocation(manager)
    instances = {getattr(i, 'name', ''): i
                 for i in _rows(manager, 'InstanceDefinition')}
    nodes = []
    by_instance = {}
    for name in candidate_names:
        inst = instances.get(name)
        machine = allocation.get(
            getattr(inst, 'machine_name', '') if inst else '')
        if machine and machine['hasSpecs']:
            by_instance[name] = machine
            nodes.append(machine)
    if not nodes:
        return list(candidate_names)
    ranked, _ = _rank(profile, nodes)
    order = {n['name']: i for i, n in enumerate(ranked)}
    return sorted(candidate_names, key=lambda c: order.get(
        by_instance.get(c, {}).get('name', ''), len(order)))
