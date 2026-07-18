"""
@cross-cutting
@module resources.profile_analysis
@tags @xc:bindings

res-2 analysis: classify what a module IS (compute / data /
balanced) from evidence — its treeObject data classes, its heavy
compute imports, and whether it owns an engine/worker seam — then
recommend where its data belongs (redis / sqlite / mariadb) and
build/cache declared profiles.

Static/declared mirror of simulations/storage_predictor (res-3 adds
the measured mirror of StepCostProfile). Row-size estimates REUSE
storage_predictor.estimate_row_bytes — one estimator rule.

Duck-typed against the manager so the selftest runs stdlib-only.

@consumers
  - resources.profile_api / resources.profile_seed
  - resources.admission_advisor (res-4)
@see /OVERLAP_MAP.md
"""

import json
import os
import re

#: Imports that mark a module as owning heavy compute.
HEAVY_COMPUTE_LIBS = ('skfem', 'sfepy', 'pyscf', 'pymatgen', 'ase',
                      'trimesh', 'dask', 'scipy')

#: Virtual engine modules (ModuleAssignment vocabulary) -> the worker
#: service kind that carries them (PROVIDER_PORTS keys).
ENGINE_MODULES = {
    'materialsScience.fem': 'prf-msci-engines',
    'materialsScience.dft': 'prf-msci-engines',
    'mathshapes.cad': 'prf-cad-engines',
}

_CLASS_RE = re.compile(r'^class\s+(\w+)\(treeObject\)', re.MULTILINE)
_FUNC_RE = re.compile(r'^def\s+\w+', re.MULTILINE)
_IMPORT_RE = re.compile(
    r'^\s*(?:from|import)\s+([A-Za-z_][A-Za-z0-9_]*)', re.MULTILINE)


def _framework_root():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def scan_module_source(module_name, root=None):
    """Static source scan of one module directory: its treeObject
    data classes, module-level function count, and heavy imports."""
    root = root or _framework_root()
    directory = os.path.join(root, *module_name.split('.'))
    result = {'present': os.path.isdir(directory), 'dataClasses': [],
              'functionCount': 0, 'heavyImports': []}
    if not result['present']:
        return result
    heavy = set()
    for fname in sorted(os.listdir(directory)):
        if not fname.endswith('.py'):
            continue
        try:
            with open(os.path.join(directory, fname)) as f:
                text = f.read()
        except OSError:
            continue
        result['dataClasses'] += _CLASS_RE.findall(text)
        result['functionCount'] += len(_FUNC_RE.findall(text))
        heavy.update(m for m in _IMPORT_RE.findall(text)
                     if m in HEAVY_COMPUTE_LIBS)
    result['heavyImports'] = sorted(heavy)
    return result


def _rows(manager, class_name):
    tables = getattr(manager, 'objectTables', None) or {}
    return list((tables.get(class_name) or {}).values())


def _provider_kinds_for(manager, module_name):
    """Worker service kinds the module is assigned to (topology
    evidence that it owns an engine)."""
    try:
        from topology.provider_registry import PROVIDER_PORTS
    except Exception:
        PROVIDER_PORTS = {}
    instances = {getattr(i, 'name', ''): i
                 for i in _rows(manager, 'InstanceDefinition')}
    kinds = set()
    for a in _rows(manager, 'ModuleAssignment'):
        if (getattr(a, 'module_name', '') != module_name
                or getattr(a, 'state', '') != 'enabled'):
            continue
        inst = instances.get(getattr(a, 'instance_name', ''))
        if inst is None:
            continue
        try:
            service_kinds = json.loads(
                getattr(inst, 'service_kinds_json', '[]') or '[]')
        except (TypeError, ValueError):
            service_kinds = []
        kinds.update(k for k in service_kinds if k in PROVIDER_PORTS)
    return sorted(kinds)


def classify_module(manager, module_name, root=None):
    """'data' | 'compute' | 'balanced', with the evidence.

    Mostly treeObject data classes with few standalone functions →
    data. Owns an engine/worker (an ENGINE_MODULES entry, a
    PROVIDER_PORTS assignment, or heavy compute imports) → compute.
    Both → balanced.
    """
    evidence = []
    engine_kind = ENGINE_MODULES.get(module_name, '')
    if engine_kind:
        evidence.append(f'engine module — runs on the {engine_kind} '
                        'worker')
    provider_kinds = _provider_kinds_for(manager, module_name)
    if provider_kinds:
        evidence.append('assigned to provider instance(s) carrying '
                        f'{provider_kinds}')
    src = scan_module_source(module_name, root=root)
    n_data = len(src['dataClasses'])
    if src['present']:
        if n_data:
            evidence.append(f'{n_data} treeObject data classes, '
                            f'{src["functionCount"]} module-level '
                            'functions')
        if src['heavyImports']:
            evidence.append('heavy compute imports: '
                            f'{src["heavyImports"]}')
    else:
        evidence.append(f'no source directory "{module_name}" under '
                        'the framework root')

    compute_signal = bool(engine_kind or provider_kinds
                          or src['heavyImports'])
    if compute_signal and n_data >= 3:
        character = 'balanced'
    elif compute_signal:
        character = 'compute'
    elif n_data > 0:
        character = ('data'
                     if src['functionCount'] <= max(4, 4 * n_data)
                     else 'balanced')
    else:
        character = 'balanced'
        evidence.append('no data classes and no compute signal — '
                        'weak evidence, defaulting to balanced')
    return {'ok': True, 'module': module_name, 'character': character,
            'evidence': evidence, 'dataClasses': src['dataClasses'],
            'functionCount': src['functionCount'],
            'heavyImports': src['heavyImports'],
            'providerKinds': provider_kinds}


def estimate_module_row_bytes(manager, class_names):
    """Largest per-row estimate among the module's data classes —
    REUSES storage_predictor (one estimator rule)."""
    try:
        from simulations.storage_predictor import estimate_row_bytes
    except Exception:
        return 0, ''
    best, best_class = 0, ''
    for name in class_names:
        est = estimate_row_bytes(manager, name)
        if est > best:
            best, best_class = est, name
    return best, best_class


def recommend_backend(profile):
    """The storage tier for a data subject, with the reason.

    redis   — hot + ephemeral (cache-shaped, high churn)
    mariadb — shared writers, or durable + high growth (the shared
              concurrent-durable store)
    sqlite  — single-node, small, low-concurrency (SqliteAdapter)
    """
    access = getattr(profile, 'access_pattern', 'warm')
    durability = getattr(profile, 'durability', 'durable')
    concurrency = getattr(profile, 'concurrency', 'single')
    growth = getattr(profile, 'growth_rate', 'low')
    if access == 'hot' and durability == 'ephemeral':
        return {'backend': 'redis',
                'reason': 'hot access + ephemeral durability — '
                          'cache-shaped data belongs in redis/keydb'}
    if concurrency == 'shared' or growth == 'high':
        why = ('shared concurrent writers'
               if concurrency == 'shared' else 'high row growth')
        return {'backend': 'mariadb',
                'reason': f'{why} + durable — mariadb is the shared '
                          'durable concurrent store'}
    return {'backend': 'sqlite',
            'reason': f'single-writer, {growth}-growth, durable — '
                      'the SqliteAdapter path fits on any node'}


def find_profile(manager, subject_name):
    for row in _rows(manager, 'ModuleResourceProfile'):
        if getattr(row, 'subject_name', '') == subject_name:
            return row
    return None


def _save(manager, row):
    try:
        manager.db.saveInstanceInDB(row)
    except Exception:
        pass


def declared_profile(manager, module_name, factory=None, root=None):
    """The module's profile: existing row wins; else build one from
    the PolariModule manifest 'resources' knob or classification +
    conservative defaults. fidelity='declared', honestly labeled."""
    existing = find_profile(manager, module_name)
    if existing is not None:
        return {'ok': True, 'created': False, 'profile': existing}
    if factory is None:
        from resources.profile_basis import ModuleResourceProfile
        factory = ModuleResourceProfile

    manifest_block = {}
    for mod in _rows(manager, 'PolariModule'):
        if getattr(mod, 'name', '') == module_name:
            try:
                manifest = json.loads(
                    getattr(mod, 'manifest_json', '{}') or '{}')
                manifest_block = manifest.get('resources', {}) or {}
            except (TypeError, ValueError):
                pass
            break

    verdict = classify_module(manager, module_name, root=root)
    est_bytes, est_class = estimate_module_row_bytes(
        manager, verdict['dataClasses'])
    fields = {
        'name': f'{module_name}-resource-profile',
        'subject_name': module_name,
        'subject_kind': 'module',
        'character': verdict['character'],
        # conservative floor defaults — a knob, not a measurement
        'min_ram_mb': 64.0, 'min_disk_mb': 50.0, 'min_threads': 1,
        'thread_ceiling': 1, 'cpu_benefit': 'none',
        'ram_benefit': 'none',
        'est_row_bytes': est_bytes,
        'fidelity': 'declared',
        'provenance_id': 'declared-default'
        + (f'; est_row_bytes from {est_class}' if est_class else ''),
        'notes': 'auto-declared from classification: '
                 + '; '.join(verdict['evidence']),
    }
    if manifest_block:
        fields.update({k: v for k, v in manifest_block.items()
                       if k in fields or k in (
                           'growth_rate', 'access_pattern',
                           'durability', 'concurrency', 'image_mb',
                           'deps_mb', 'scales_note')})
        fields['provenance_id'] = 'PolariModule.manifest_json'
    if fields['character'] == 'data':
        fields['recommended_backend'] = recommend_backend(
            type('P', (), fields)())['backend']
    profile = factory(**fields, manager=manager)
    _save(manager, profile)
    return {'ok': True, 'created': True, 'profile': profile,
            'classification': verdict}


def _default_fetch(url, timeout=5):
    import urllib.request
    with urllib.request.urlopen(url, timeout=timeout) as resp:
        return json.loads(resp.read().decode('utf-8'))


def import_engine_profile(manager, service_kind, url='',
                          fetch=_default_fetch, factory=None):
    """Cache a live worker's /capability `resources` block into a
    ModuleResourceProfile(subject_kind='engine'). Workers without the
    block (old images) → honest refusal naming the rebuild."""
    if not url:
        try:
            from topology.provider_registry import PROVIDER_PORTS
        except Exception:
            PROVIDER_PORTS = {}
        port = PROVIDER_PORTS.get(service_kind)
        host = os.environ.get('LOCAL_IP', '')
        if not port or not host:
            return {'ok': False,
                    'error': f'no URL for "{service_kind}" — not in '
                             'PROVIDER_PORTS or LOCAL_IP unset',
                    'suggestion': {
                        'evidence': f'PROVIDER_PORTS={sorted(PROVIDER_PORTS)}, '
                                    f'LOCAL_IP={"set" if host else "unset"}',
                        'knob': 'PROVIDER_PORTS / LOCAL_IP env',
                        'action': 'pass an explicit url, or add the '
                                  'service kind to PROVIDER_PORTS'}}
        url = f'http://{host}:{port}'
    cap_url = url.rstrip('/')
    if not cap_url.endswith('/capability'):
        cap_url += '/capability'
    try:
        cap = fetch(cap_url)
    except Exception as e:
        return {'ok': False,
                'error': f'{cap_url} unreachable: {e}'}
    block = (cap or {}).get('resources') or {}
    if not block:
        return {'ok': False,
                'error': f'{cap_url} answers but carries no '
                         '"resources" block',
                'suggestion': {
                    'evidence': 'worker image predates res-2',
                    'knob': 'the worker image',
                    'action': 'rebuild + ship the worker (docker save '
                              '| ssh <node> docker load; docker '
                              'service update --force)'}}
    if factory is None:
        from resources.profile_basis import ModuleResourceProfile
        factory = ModuleResourceProfile
    fields = {
        'subject_name': service_kind,
        'subject_kind': 'engine',
        'character': 'compute',
        'min_ram_mb': float(block.get('ramMb', 0) or 0),
        'min_threads': int(block.get('minThreads', 1) or 1),
        'thread_ceiling': int(block.get('threadCeiling', 1) or 1),
        'cpu_benefit': block.get('cpuBenefit', 'none'),
        'image_mb': float(block.get('imageMb', 0) or 0),
        'fidelity': block.get('fidelity', 'declared'),
        'provenance_id': cap_url,
        'notes': f'imported from {cap_url}',
    }
    existing = find_profile(manager, service_kind)
    if existing is not None:
        if getattr(existing, 'fidelity', '') == 'measured':
            return {'ok': True, 'created': False, 'updated': False,
                    'profile': existing,
                    'note': 'measured profile kept — a declared '
                            'capability block never overrides '
                            'measurement'}
        for k, v in fields.items():
            setattr(existing, k, v)
        _save(manager, existing)
        return {'ok': True, 'created': False, 'updated': True,
                'profile': existing}
    profile = factory(name=f'{service_kind}-resource-profile',
                      **fields, manager=manager)
    _save(manager, profile)
    return {'ok': True, 'created': True, 'profile': profile}


def profile_dict(p):
    return {
        'name': getattr(p, 'name', ''),
        'subjectName': getattr(p, 'subject_name', ''),
        'subjectKind': getattr(p, 'subject_kind', ''),
        'character': getattr(p, 'character', ''),
        'floor': {
            'minRamMb': getattr(p, 'min_ram_mb', 0.0),
            'minDiskMb': getattr(p, 'min_disk_mb', 0.0),
            'minThreads': getattr(p, 'min_threads', 1),
        },
        'scalability': {
            'threadCeiling': getattr(p, 'thread_ceiling', 1),
            'cpuBenefit': getattr(p, 'cpu_benefit', 'none'),
            'ramBenefit': getattr(p, 'ram_benefit', 'none'),
            'note': getattr(p, 'scales_note', ''),
        },
        'install': {
            'imageMb': getattr(p, 'image_mb', 0.0),
            'depsMb': getattr(p, 'deps_mb', 0.0),
        },
        'data': {
            'estRowBytes': getattr(p, 'est_row_bytes', 0),
            'growthRate': getattr(p, 'growth_rate', ''),
            'accessPattern': getattr(p, 'access_pattern', ''),
            'durability': getattr(p, 'durability', ''),
            'concurrency': getattr(p, 'concurrency', ''),
            'recommendedBackend':
                getattr(p, 'recommended_backend', ''),
        },
        'fidelity': getattr(p, 'fidelity', 'declared'),
        'provenanceId': getattr(p, 'provenance_id', ''),
        'notes': getattr(p, 'notes', ''),
    }
