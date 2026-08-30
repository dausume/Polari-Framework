"""
@module moduleService.json_seeds

THE module data convention, implemented (Dustin 2026-08-30: "the whole
point of having seed in json format was so that all modules can be
installed both via pulling projects from github or by hitting apis
that provide the module data").

Every module package may carry `initialData/<ClassName>.json`:

    {"schema": "module-initial-data/1", "class": "<ClassName>",
     "source": "<where it was exported from>", "count": N,
     "rows": [ {constructor kwargs, name required}, ... ]}

Plain JSON, small (the rule in cntfet.cnt_snapshot: only what code
cannot regenerate; never binaries / vendored inputs). The SAME files
are:
  - loaded at boot for every admitted module (polariServer pass) and by
    `POST /modules/seed {"moduleId"}` (the module's `seedData.py`
    delegates here), through composition.seed_upsert — a customized row
    (is_prior False) is never clobbered; missing rows insert; prior
    rows converge field-by-field;
  - SERVED by `GET /modules/{module_id}/initial-data` so another
    instance can install the module's data from this API instead of a
    git pull: `POST /modules/seed {"moduleId", "source": "<api base>"}`.

@consumers polariServer (boot pass), modulesAPI, modules/*/seedData.py
"""

import importlib
import inspect
import json
import os

SCHEMA = 'module-initial-data/1'
DATA_DIR = 'initialData'
META_KEYS = {'id', 'class', 'varsLimited', 'inTree', 'branch', 'manager',
             'polariId', 'objectTypingDict'}

_HERE = os.path.dirname(os.path.abspath(__file__))
MODULES_ROOT = os.path.join(os.path.dirname(_HERE), 'modules')


def package_dir(package):
    """The on-disk dir of a module package (modules/<pkg> first, then
    the importable package's own location)."""
    cand = os.path.join(MODULES_ROOT, package)
    if os.path.isdir(cand):
        return cand
    try:
        mod = importlib.import_module(package)
        return os.path.dirname(os.path.abspath(mod.__file__))
    except Exception:  # noqa: BLE001
        return None


def resolve_package(module_id):
    """A module id names its package directly when modules/<id> exists
    (the polari-modules.json modules); else the legacy
    polari<Pascal>Module rule."""
    if os.path.isdir(os.path.join(MODULES_ROOT, module_id)):
        return module_id
    try:
        from moduleService.moduleDiscovery import module_id_to_package
        return module_id_to_package(module_id)
    except Exception:  # noqa: BLE001
        return module_id


def data_dir(package):
    d = package_dir(package)
    return os.path.join(d, DATA_DIR) if d else None


def list_files(package):
    d = data_dir(package)
    if not d or not os.path.isdir(d):
        return []
    return sorted(os.path.join(d, f) for f in os.listdir(d)
                  if f.endswith('.json'))


def read_file(path):
    with open(path, encoding='utf-8') as f:
        payload = json.load(f)
    if not isinstance(payload, dict) or 'rows' not in payload:
        raise ValueError(f'{path}: not a module-initial-data payload')
    payload.setdefault('class', os.path.basename(path)[:-5])
    return payload


def write_file(package, class_name, rows, source=''):
    """Write rows in the convention (indented, sorted — git-diffable)."""
    d = data_dir(package)
    os.makedirs(d, exist_ok=True)
    path = os.path.join(d, f'{class_name}.json')
    rows = sorted(rows, key=lambda r: str(r.get('name', '')))
    payload = {'schema': SCHEMA, 'class': class_name, 'source': source,
               'count': len(rows), 'rows': rows}
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(payload, f, indent=1, sort_keys=True, ensure_ascii=False)
        f.write('\n')
    return path


def constructor_fields(cls):
    try:
        params = inspect.signature(cls.__init__).parameters
    except (TypeError, ValueError):
        return None
    return [p for p in params if p not in ('self', 'manager', 'args', 'kwargs')]


def to_seed(row, fields):
    return {k: v for k, v in row.items()
            if k not in META_KEYS and (fields is None or k in fields)}


def _class_lookup(manager, class_name, package):
    """The class object: the manager's typing dict first (booted), else
    scan the package's modules for a class of that name."""
    typing = getattr(manager, 'objectTypingDict', None) or {}
    t = typing.get(class_name)
    for attr in ('classObject', 'cls', 'objectClass'):
        c = getattr(t, attr, None)
        if inspect.isclass(c):
            return c
    d = package_dir(package)
    if not d:
        return None
    for fname in sorted(os.listdir(d)):
        if not fname.endswith('.py') or fname.startswith('selftest'):
            continue
        try:
            mod = importlib.import_module(f'{package}.{fname[:-3]}')
        except Exception:  # noqa: BLE001
            continue
        c = getattr(mod, class_name, None)
        if inspect.isclass(c):
            return c
    return None


def seed_pairs(package, manager=None, payloads=None):
    """[(class_name, cls, rows)] in FILE ORDER (name your files so
    dependencies sort first, or keep them independent) + skipped
    [(class, why)]. `payloads` (from an API) replaces the files."""
    pairs, skipped = [], []
    payloads = payloads if payloads is not None else [
        read_file(p) for p in list_files(package)]
    for payload in payloads:
        class_name = payload['class']
        cls = _class_lookup(manager, class_name, package)
        if cls is None:
            skipped.append((class_name, 'class not importable / not booted'))
            continue
        fields = constructor_fields(cls)
        rows = [to_seed(r, fields) for r in payload.get('rows', [])]
        pairs.append((class_name, cls, [r for r in rows if r.get('name')]))
    return pairs, skipped


def apply(package, manager, payloads=None, tag='JsonSeeds'):
    """Upsert the package's initialData into the live tables. Returns
    {'reports': [...], 'skipped': [...], 'created': {cls: [names]}} —
    `created` is the seedData.seed_initial_data contract."""
    from composition.seed_upsert import upsert_seed_pairs
    pairs, skipped = seed_pairs(package, manager, payloads)
    reports = upsert_seed_pairs(manager, pairs, tag=tag) if pairs else []
    created = {r['class']: list(r.get('inserted', [])) for r in reports
               if not r.get('skipped')}
    return {'reports': reports, 'skipped': skipped, 'created': created}


def serve(package):
    """The payloads as an API body: {'schema', 'package', 'files':
    [payload, ...], 'totalBytes'} — what GET /modules/{m}/initial-data
    returns and POST /modules/seed {"source"} consumes."""
    files = list_files(package)
    return {'schema': SCHEMA, 'package': package,
            'files': [read_file(p) for p in files],
            'totalBytes': sum(os.path.getsize(p) for p in files)}


def fetch(source_api, module_id, timeout=120):
    """Pull another instance's initial-data payloads for a module."""
    import ssl
    import urllib.request
    ctx = ssl._create_unverified_context()
    url = f'{source_api.rstrip("/")}/modules/{module_id}/initial-data'
    with urllib.request.urlopen(url, context=ctx, timeout=timeout) as r:
        body = json.loads(r.read().decode())
    if body.get('schema') != SCHEMA:
        raise ValueError(f'{url}: schema {body.get("schema")!r} != {SCHEMA}')
    return body['files']


def packages_with_data():
    """Every modules/<pkg> carrying an initialData/ dir (boot pass)."""
    if not os.path.isdir(MODULES_ROOT):
        return []
    return sorted(p for p in os.listdir(MODULES_ROOT)
                  if os.path.isdir(os.path.join(MODULES_ROOT, p, DATA_DIR)))
