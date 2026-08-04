"""
@cross-cutting
@module topology.object_ownership
@tags @xc:bindings

WHO IS RESPONSIBLE FOR AN OBJECT — the chain that keeps Polari
coherent, resolved and made visible.

Dustin, 2026-08-04: "modules own responsibility for particular objects
and talk to one another for particular objects to ensure coherence.
Due to module assignments, particular prf instances hold
responsibility for different objects. So we should be able to identify
the particular prf and the particular module responsible directly for
an object. While its data, or a sub-set of data or sub-set of displays
related to it, may be on other modules dependent on it. This is how we
keep coherence in Polari."

The chain, every link of which already existed separately:

    object class
      -> OWNING MODULE      the module whose source defines the
                            treeObject (resources.profile_analysis
                            .scan_module_source)
      -> RESPONSIBLE PRF    the instance(s) that module is assigned to
                            (ModuleAssignment, state='enabled')
      -> ITS DATABASES      what that instance is bound to
                            (InstanceDefinition.db_backend)

Ownership is expected to be UNAMBIGUOUS — one module defines a class.
A class claimed by two modules is a coherence FAULT, not a merge, so
it is reported as `contested` rather than silently resolved.

Two absences are equally reportable and never guessed:
  unassigned  the owning module is on no instance here — nobody holds
              responsibility for those objects on this topology
  orphan      live rows exist for a class no scanned module claims

⚠ SQLITE IS NOT SHAREABLE. For a PRF instance `sqlite` means the
sqlite THAT INSTANCE creates locally; it is never pointed elsewhere.
So a sqlite storage identity is the instance itself, and its
co-tenancy is exactly that instance's objects. A shared relational
backend (mariadb/postgres) is the opposite: several instances can be
bound to one server, so their objects are co-resident.

@consumers topology.topology_api (/api/topology/object-ownership)
"""

from typing import Any, Dict, List

#: Which DB_BACKENDS entries mean a shared relational server rather
#: than a file local to the instance. Relational is the only storage
#: an instance is REQUIRED to declare; blob and cache tiers are
#: expected to become assignable later and are reported as absent
#: rather than assumed.
_LOCAL_BACKENDS = ('sqlite',)


def _rows(manager, class_name: str) -> List[Any]:
    return list((getattr(manager, 'objectTables', None)
                 or {}).get(class_name, {}).values())


def _row_count(manager, class_name: str) -> int:
    return len((getattr(manager, 'objectTables', None)
                or {}).get(class_name, {}) or {})


def class_owners(root: str = None) -> Dict[str, Any]:
    """class name -> the module(s) whose source defines it.

    Derived from source, not declared, so it cannot drift from the
    code the way a hand-maintained registry would.
    """
    import os
    from resources.profile_analysis import scan_module_source

    base = root or '/app'
    modules_dir = os.path.join(base, 'modules')
    if not os.path.isdir(modules_dir):
        return {'ok': False,
                'error': f'no modules directory at {modules_dir}'}
    owners: Dict[str, List[str]] = {}
    per_module: Dict[str, List[str]] = {}
    core: Dict[str, str] = {}

    for entry in sorted(os.listdir(modules_dir)):
        if entry.startswith('__') or not os.path.isdir(
                os.path.join(modules_dir, entry)):
            continue
        try:
            scanned = scan_module_source(entry)
        except Exception:
            continue
        classes = scanned.get('dataClasses') or []
        per_module[entry] = sorted(classes)
        for cls in classes:
            owners.setdefault(cls, []).append(entry)

    # CORE classes are owned by the framework itself, not by a module,
    # so they are not assignable and cannot be "unowned". Scanning only
    # modules/ made every one of them look like an orphan — 118 of them
    # on this node, which would have read as a coherence disaster
    # instead of the framework working normally.
    for entry in sorted(os.listdir(base)):
        path = os.path.join(base, entry)
        if (entry.startswith(('__', '.')) or entry == 'modules'
                or not os.path.isdir(path)
                or not os.path.isfile(os.path.join(path, '__init__.py'))):
            continue
        try:
            scanned = scan_module_source(entry)
        except Exception:
            continue
        for cls in (scanned.get('dataClasses') or []):
            if cls not in owners:
                core[cls] = entry

    return {'ok': True, 'owners': owners, 'perModule': per_module,
            'core': core}


def _storage_identity(instance) -> Dict[str, Any]:
    """The three storage tiers this instance is bound to.

    RELATIONAL is required — everything the instance owns lands there.
    For a local backend the identity IS the instance: sqlite is not
    shareable, so naming anything else would imply a choice that does
    not exist. For a shared backend the identity is the backend on
    this topology, which is as specific as the object tree currently
    gets: db_backend records the KIND, while the concrete host lives
    in config/env (MARIADB_HOST). That limit is stated, not papered
    over.

    CACHE and BLOB are optional, so an empty value means genuinely NOT
    ASSIGNED and is reported that way rather than defaulted to a
    service the instance does not run. Neither is a choice of
    technology — cache is always keydb, blob always minio — so what
    is recorded is the BINDING, not a vendor.

    The `mariadb+keydb` relational backend already binds a cache. It
    is derived here rather than duplicated into cache_backend, so the
    two can never disagree; `cacheImplied` says where it came from.
    """
    from topology.topology_constants import DB_BACKEND_IMPLIED_CACHE

    backend = getattr(instance, 'db_backend', '') or 'sqlite'
    name = getattr(instance, 'name', '')
    topology = getattr(instance, 'topology_name', '')
    local = backend in _LOCAL_BACKENDS

    implied = DB_BACKEND_IMPLIED_CACHE.get(backend, '')
    cache = implied or (getattr(instance, 'cache_backend', '') or '')
    blob = getattr(instance, 'blob_backend', '') or ''

    return {
        'relational': backend,
        'shared': not local,
        'identity': (f'{name}:{backend}' if local
                     else f'{topology}:{backend}'),
        'note': ('local to this instance — sqlite is never shared'
                 if local else
                 'shared: every instance on this backend is '
                 'co-resident. The concrete host is a deploy-time '
                 'setting (MARIADB_HOST), not a topology row — '
                 'instances on the same backend are treated as one '
                 'server'),
        'cache': cache,
        'cacheImplied': bool(implied),
        'blob': blob,
        # Which optional tiers are genuinely unbound. Named rather
        # than left for the reader to infer from an empty string.
        'unbound': [tier for tier, value in
                    (('cache', cache), ('blob', blob)) if not value],
    }


def object_ownership(manager, topology_name: str,
                     root: str = None) -> Dict[str, Any]:
    """The full chain for one topology."""
    scan = class_owners(root)
    if not scan.get('ok'):
        return scan
    owners = scan['owners']
    core = scan.get('core') or {}

    instances = [i for i in _rows(manager, 'InstanceDefinition')
                 if getattr(i, 'topology_name', '') == topology_name]
    if not instances:
        return {'ok': False,
                'error': f'no instances in topology "{topology_name}"'}

    # module -> instances actually holding it
    holders: Dict[str, List[str]] = {}
    for assignment in _rows(manager, 'ModuleAssignment'):
        if getattr(assignment, 'topology_name', '') != topology_name:
            continue
        if getattr(assignment, 'state', '') != 'enabled':
            continue
        module = getattr(assignment, 'module_name', '').split('.')[0]
        instance = getattr(assignment, 'instance_name', '')
        if module and instance:
            holders.setdefault(module, []).append(instance)

    contested = [{'class': cls, 'modules': sorted(mods)}
                 for cls, mods in owners.items() if len(mods) > 1]

    by_instance: Dict[str, List[Dict[str, Any]]] = {
        getattr(i, 'name', ''): [] for i in instances}
    unassigned: List[Dict[str, Any]] = []

    for cls, mods in owners.items():
        module = sorted(mods)[0]
        rows = _row_count(manager, cls)
        placed = sorted(set(holders.get(module, [])))
        if not placed:
            unassigned.append({'class': cls, 'module': module,
                               'rows': rows})
            continue
        for instance_name in placed:
            if instance_name in by_instance:
                by_instance[instance_name].append(
                    {'class': cls, 'module': module, 'rows': rows})

    # Framework-owned classes: real, held by the core rather than by
    # any module, and therefore not assignable.
    core_objects = [
        {'class': cls, 'package': pkg, 'rows': _row_count(manager, cls)}
        for cls, pkg in sorted(core.items())
        if _row_count(manager, cls) > 0
    ]
    core_objects.sort(key=lambda o: (-o['rows'], o['class']))

    # Live tables NOTHING claims — neither a module nor the core.
    # Only these are genuinely ownerless.
    known = set(owners) | set(core)
    orphans = [
        {'class': cls, 'rows': _row_count(manager, cls)}
        for cls in sorted((getattr(manager, 'objectTables', None) or {}))
        if cls not in known and _row_count(manager, cls) > 0
    ]

    out_instances = []
    for inst in sorted(instances, key=lambda i: getattr(i, 'name', '')):
        name = getattr(inst, 'name', '')
        objects = sorted(by_instance.get(name, []),
                         key=lambda o: (-o['rows'], o['class']))
        out_instances.append({
            'instance': name,
            'kind': getattr(inst, 'kind', ''),
            'machine': getattr(inst, 'machine_name', ''),
            'storage': _storage_identity(inst),
            'modules': sorted({o['module'] for o in objects}),
            'objectCount': len(objects),
            'rowCount': sum(o['rows'] for o in objects),
            'objects': objects,
        })

    # Group instances by the storage they share — the co-tenancy view.
    groups: Dict[str, Dict[str, Any]] = {}
    for entry in out_instances:
        key = entry['storage']['identity']
        group = groups.setdefault(key, {
            'identity': key,
            'relational': entry['storage']['relational'],
            'shared': entry['storage']['shared'],
            'instances': [], 'objectCount': 0, 'rowCount': 0,
        })
        group['instances'].append(entry['instance'])
        group['objectCount'] += entry['objectCount']
        group['rowCount'] += entry['rowCount']

    return {
        'ok': True,
        'topology': topology_name,
        'instances': out_instances,
        'storageGroups': sorted(groups.values(),
                                key=lambda g: -g['rowCount']),
        'coreObjects': core_objects,
        'contested': contested,
        'unassigned': sorted(unassigned,
                             key=lambda u: (-u['rows'], u['class'])),
        'orphans': orphans,
        'note': 'ownership is derived from module SOURCE (which module '
                'defines the treeObject), responsibility from enabled '
                'ModuleAssignment rows, and storage from the '
                "instance's db_backend. A class owned by two modules "
                'is a coherence fault and is reported, never merged. '
                'Core framework classes are owned by the framework, not '
                'by a module, so they are listed separately and are not '
                'assignable.',
    }
