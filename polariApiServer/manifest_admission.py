"""
@module polariApiServer.manifest_admission

sap-3, first slice: admit a module FROM ITS polari-app.json when the
hand-threaded core tables (feature_imports / module_endpoints / the
seed-pairs literal / the page concat in polariServer.py) do not know
it. This is the `pol project` route — a module developed as its own
project, mounted or fetched onto a running instance, comes online
from its manifest alone:

  files.*     every listed file is imported; the treeObject subclasses
              the module itself defines become its definition classes
              (`classes` in the manifest filters them; *API classes are
              constructed by the endpoints constructor, never tabled)
  endpoints   'pkg.mod:construct_x_endpoints' → registered into
              MODULE_ENDPOINT_CONSTRUCTORS so the ordinary admission
              constructs it exactly once
  seedPairs   'pkg.mod:X_SEED_PAIRS' → [(class_name, cls, rows)]
  pages       'pkg.mod:SEED_X_PAGE_DISPLAYS' → DisplayDefinition rows

Seeds are upserted BY NAME after the tables exist (create when absent,
update changed fields when present — the seed_upsert rule, never
insert-by-name). Table-declared modules never enter this path, so
nothing here changes how a built-in module admits.
"""
import importlib
import json
import os

# module → [(class_name, cls, rows)] resolved by prepare(), applied by
# apply_seeds() once the tables exist.
MANIFEST_SEEDS = {}


def manifest_path(module):
    from moduleService.module_loading import module_code_dir
    d = module_code_dir(module)
    if not d:
        return None
    p = os.path.join(d, 'polari-app.json')
    return p if os.path.isfile(p) else None


def load_manifest(module):
    p = manifest_path(module)
    if not p:
        return None
    with open(p, encoding='utf-8') as fh:
        return json.load(fh)


def table_declared(module):
    """True when the core tables already thread this module (then the
    dyn-1..4 path owns it and the manifest is documentation only)."""
    from polariApiServer.feature_imports import FEATURE_IMPORT_BLOCKS
    from polariApiServer.module_endpoints import MODULE_ENDPOINT_CONSTRUCTORS
    if module in MODULE_ENDPOINT_CONSTRUCTORS:
        return True
    return any(entry == module for entry, _ in FEATURE_IMPORT_BLOCKS)


def _resolve(ref):
    mod, _, name = ref.partition(':')
    return getattr(importlib.import_module(mod), name)


def _file_modules(manifest):
    pkg = manifest.get('package') or manifest['id']
    files = manifest.get('files') or {}
    for concept in ('objects', 'basis', 'api', 'endpoints', 'seed', 'page',
                    'catalog', 'remote'):
        for stem in files.get(concept) or []:
            yield pkg + '.' + stem.replace('/', '.')


def prepare(polServer, module, manifest):
    """Import the module's files, extend the pre-gate class list, register
    its endpoint constructor, resolve its seeds. Raises on broken code —
    the caller turns that into a refusal (never a silent skip)."""
    import polariApiServer.polariServer as server_mod
    from objectTreeDecorators import treeObject
    from polariApiServer.lazy_boot import top_module
    from polariApiServer.module_endpoints import MODULE_ENDPOINT_CONSTRUCTORS
    classes = []
    for name in _file_modules(manifest):
        m = importlib.import_module(name)
        for value in list(vars(m).values()):
            if (isinstance(value, type) and issubclass(value, treeObject)
                    and top_module(value) == module
                    and not value.__name__.endswith('API')
                    and value not in classes):
                classes.append(value)
    declared = set(manifest.get('classes') or [])
    if declared:
        classes = [c for c in classes if c.__name__ in declared]
    known = set(getattr(polServer, 'allDefClassList', []))
    added = [c for c in classes if c not in known]
    polServer.allDefClassList.extend(added)
    endpoints = manifest.get('endpoints')
    if endpoints and module not in MODULE_ENDPOINT_CONSTRUCTORS:
        MODULE_ENDPOINT_CONSTRUCTORS[module] = _resolve(endpoints)
    seeds = []
    if manifest.get('seedPairs'):
        seeds.extend(list(_resolve(manifest['seedPairs']) or []))
    for ref in manifest.get('pages') or []:
        seeds.append(('DisplayDefinition', server_mod.DisplayDefinition,
                      list(_resolve(ref) or [])))
    MANIFEST_SEEDS[module] = seeds
    return {'source': 'polari-app.json',
            'classes': sorted(c.__name__ for c in added),
            'endpoints': endpoints or None,
            'seedTriples': len(seeds)}


def apply_seeds(manager, module):
    """Upsert the module's seed rows by name (tables must exist)."""
    created = updated = skipped = 0
    for triple in MANIFEST_SEEDS.get(module, []):
        if not isinstance(triple, (tuple, list)) or len(triple) != 3:
            skipped += 1
            continue
        class_name, cls, rows = triple
        if class_name not in (manager.objectTypingDict or {}):
            skipped += len(rows or [])
            continue
        existing = manager.objectTables.get(class_name, {}) or {}
        by_name = {getattr(o, 'name', None): o for o in existing.values()}
        for seed in rows or []:
            name = seed.get('name') if isinstance(seed, dict) else None
            if not name:
                skipped += 1
                continue
            row = by_name.get(name)
            if row is None:
                cls(**seed, manager=manager)
                created += 1
                continue
            changed = False
            for key, value in seed.items():
                if key != 'name' and getattr(row, key, None) != value:
                    setattr(row, key, value)
                    changed = True
            if changed:
                manager.db.saveInstanceInDB(row)
                updated += 1
    return {'created': created, 'updated': updated, 'skipped': skipped}
