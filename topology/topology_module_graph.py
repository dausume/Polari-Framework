"""
@cross-cutting
@module topology.topology_module_graph

Module-level graph semantics (tt-1, TECH_TREE_TOPOLOGY_PLAN Part A):
dependency edges are stored OUTBOUND-only (ModuleDependencyEdge), so
"who depends on me" is computed here by inverting the edge set. On
top of the inverted graph:

  - per-module CLASSIFICATION from in/out degree — consumer /
    provider / hybrid / independent — with 'data-only' overriding
    when the module's PolariModule row self-declares data_only (a
    module that is just stored class/data information).
  - TRANSIENT/PRIMARY designation: a dependency used by N>1
    consumers keeps ONE primary consumer (solid border in the
    revamped renderer) and N-1 transient copies (dashed). The
    designation is deterministic like resolve_edges (keep a
    still-valid existing primary, else alphabetically-first
    consumer) and is STAMPED on the edge rows so it stays stable
    across recomputes.

Pure logic, NO framework imports: every function takes `manager`
duck-typed as anything with an `objectTables` dict, so the selftest
runs stdlib-only with SimpleNamespace rows.

@consumers
  - topology.topology_api (GET /api/topology/module-graph,
    POST /api/topology/resolve designation pass)
  - polari-platform-angular topology-graph-view (tt-2 circles/
    nesting/transient renderer)
  - topology.selftest_module_graph
"""

from topology.topology_constants import ENGINE_CAPABILITY_MODULES

#: A2 vocabulary — how a module relates to the dependency graph.
MODULE_CLASSIFICATIONS = (
    'consumer', 'provider', 'hybrid', 'independent', 'data-only')


def _rows(manager, class_name):
    table = (getattr(manager, 'objectTables', None) or {}).get(
        class_name, {})
    return list(table.values()) if isinstance(table, dict) else list(table)


def _scoped(manager, class_name, topology_name):
    return [r for r in _rows(manager, class_name)
            if getattr(r, 'topology_name', '') == topology_name]


def _data_only_modules(manager):
    """Module names whose PolariModule row self-declares data_only.

    Matches the assignment's module id exactly, and lets a top-level
    declaration cover its dotted capabilities ('materialsScience'
    covers 'materialsScience.fem') — the flag lives on the registry
    row, the graph only reads it (object-coherence)."""
    flagged = set()
    for row in _rows(manager, 'PolariModule'):
        if getattr(row, 'data_only', False):
            name = getattr(row, 'name', '')
            if name:
                flagged.add(name)
    return flagged


def _is_data_only(module_name, flagged):
    return (module_name in flagged
            or module_name.split('.')[0] in flagged)


def classify(out_degree, in_degree, data_only=False):
    """One module's classification from its degrees (A2)."""
    if data_only:
        return 'data-only'
    if out_degree and in_degree:
        return 'hybrid'
    if out_degree:
        return 'consumer'
    if in_degree:
        return 'provider'
    return 'independent'


def designate_transients(manager, topology_name):
    """Stamp is_primary / is_transient on every dependency edge (A4).

    Groups edges by depends_on_module; within a group of N consumers
    exactly ONE edge is primary (kept if an existing primary is still
    in the group, else the alphabetically-first consumer key) and the
    other N-1 are transient. A dependency with a single consumer is
    primary and never transient. Mutates edge rows and returns what
    changed; the caller persists (API) or not (selftest) — same
    contract as resolve_edges."""
    groups = {}
    for edge in _scoped(manager, 'ModuleDependencyEdge', topology_name):
        groups.setdefault(
            getattr(edge, 'depends_on_module', ''), []).append(edge)
    changed = []
    for dep, edges in sorted(groups.items()):
        def consumer_key(e):
            return (f'{getattr(e, "module_name", "")}'
                    f'@{getattr(e, "consumer_instance_name", "")}')
        edges.sort(key=consumer_key)
        existing = [e for e in edges if getattr(e, 'is_primary', False)]
        primary = existing[0] if existing else edges[0]
        for edge in edges:
            old = (getattr(edge, 'is_primary', False),
                   getattr(edge, 'is_transient', False))
            edge.is_primary = edge is primary
            edge.is_transient = edge is not primary
            if (edge.is_primary, edge.is_transient) != old:
                changed.append({
                    'edge': getattr(edge, 'name', ''),
                    'dependsOnModule': dep,
                    'isPrimary': edge.is_primary,
                    'isTransient': edge.is_transient,
                    'reason': ('kept existing primary'
                               if existing and edge is primary else
                               'alphabetically-first consumer is primary'
                               if edge is primary else
                               f'shared by {len(edges)} consumers — '
                               'transient copy'),
                })
    return {'ok': True, 'topology': topology_name,
            'groups': len(groups), 'changed': changed}


def module_graph(manager, topology_name):
    """The bidirectional module-level graph the revamped renderer
    draws (A1-A4): every module with its placements, degrees,
    dependsOn/dependents lists, classification, and per-edge
    transient/primary designation.

    Designation is computed in-pass (idempotent over already-stamped
    rows) so a plain GET always returns a coherent picture even
    before any resolve/designate POST has persisted."""
    designate_transients(manager, topology_name)

    placements = {}
    for asg in _scoped(manager, 'ModuleAssignment', topology_name):
        placements.setdefault(
            getattr(asg, 'module_name', ''), []).append({
                'instance': getattr(asg, 'instance_name', ''),
                'state': getattr(asg, 'state', ''),
            })

    edges = _scoped(manager, 'ModuleDependencyEdge', topology_name)
    depends_on, dependents = {}, {}
    for edge in edges:
        consumer = getattr(edge, 'module_name', '')
        dep = getattr(edge, 'depends_on_module', '')
        depends_on.setdefault(consumer, set()).add(dep)
        dependents.setdefault(dep, set()).add(consumer)

    names = sorted(set(placements)
                   | set(depends_on) | set(dependents))
    flagged = _data_only_modules(manager)
    modules = []
    for name in names:
        outs = sorted(depends_on.get(name, set()))
        ins = sorted(dependents.get(name, set()))
        modules.append({
            'name': name,
            # tt-14: engine capabilities only live on engine hosts —
            # the UI's move picker filters targets by this.
            'engineCapability': name in ENGINE_CAPABILITY_MODULES,
            'placements': placements.get(name, []),
            'dependsOn': outs,
            'dependents': ins,
            'outDegree': len(outs),
            'inDegree': len(ins),
            'dataOnly': _is_data_only(name, flagged),
            'classification': classify(
                len(outs), len(ins), _is_data_only(name, flagged)),
        })

    return {
        'ok': True, 'topology': topology_name,
        'modules': modules,
        'edges': [
            {'name': getattr(e, 'name', ''),
             'moduleName': getattr(e, 'module_name', ''),
             'consumerInstanceName':
                 getattr(e, 'consumer_instance_name', ''),
             'dependsOnModule': getattr(e, 'depends_on_module', ''),
             'providerInstanceName':
                 getattr(e, 'provider_instance_name', ''),
             'status': getattr(e, 'status', ''),
             'isPrimary': getattr(e, 'is_primary', False),
             'isTransient': getattr(e, 'is_transient', False)}
            for e in edges],
    }
