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

Plain JSON, small (the rule in cntfet.custom.cnt_snapshot: only what code
cannot regenerate; never binaries / vendored inputs). The SAME files
are:
  - loaded at boot for every admitted module (polariServer pass) and by
    `POST /modules/seed {"moduleId"}` (the module's `seedData.py`
    delegates here), through composition.custom.seed_upsert — a customized row
    (is_prior False) is never clobbered; missing rows insert; prior
    rows converge field-by-field;
  - SERVED by `GET /modules/{module_id}/initial-data` so another
    instance can install the module's data from this API instead of a
    git pull: `POST /modules/seed {"moduleId", "source": "<api base>"}`;
  - WRITTEN by the reverse path (mo-3, MEAL_OPTIONS_MODULE_PLAN D5):
    `export_rows` / `POST /modules/export {"moduleId"}` /
    `pol modules export <module>` takes the live tables' USER-AUTHORED
    rows (is_prior False — seeds stay in code) back into the files,
    minus META_KEYS and every field the module's privacy strip names.

The export hook protocol — a module may carry `export_hook.py`
(discovered by importlib; every function optional):
    include_classes()       -> class names to export (else <PKG>_CLASSES)
    include_prior_classes() -> names exported REGARDLESS of is_prior
                               (computed reference rows, e.g. PriceReference)
    strip_fields()          -> field names removed from every row
    filter_row(class_name, row) -> the row (possibly edited) or None to
                               drop it; runs BEFORE the strip so it can
                               see (and refuse) a leaking value.

@consumers polariServer (boot pass), modulesAPI, modules/*/seedData.py,
modules/*/export_hook.py
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
    """A payload in the convention, or a LEGACY bare list (pre-convention
    files such as materials_science/initialData/*.json, named
    by collection not class) marked `legacy: True` with class None — kept
    loadable-by-listing, skipped loudly by seed_pairs until renamed to
    <ClassName>.json with the schema header."""
    with open(path, encoding='utf-8') as f:
        payload = json.load(f)
    if isinstance(payload, list):
        return {'schema': 'legacy-list', 'class': None, 'legacy': True,
                'file': os.path.basename(path), 'count': len(payload),
                'rows': payload}
    if not isinstance(payload, dict) or 'rows' not in payload:
        raise ValueError(f'{path}: not a module-initial-data payload')
    payload.setdefault('class', os.path.basename(path)[:-5])
    return payload


def _json_default(value):
    """Live rows may hold non-JSON values (dates, sets, objects); a
    seed file is plain text, so they degrade to their str form."""
    if isinstance(value, (set, frozenset, tuple)):
        return sorted(value, key=str)
    return str(value)


def write_file(package, class_name, rows, source='', out_dir=None):
    """Write rows in the convention (indented, sorted — git-diffable).
    `out_dir` replaces the package's initialData/ dir (tests)."""
    d = out_dir or data_dir(package)
    os.makedirs(d, exist_ok=True)
    path = os.path.join(d, f'{class_name}.json')
    rows = sorted(rows, key=lambda r: str(r.get('name', '')))
    payload = {'schema': SCHEMA, 'class': class_name, 'source': source,
               'count': len(rows), 'rows': rows}
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(payload, f, indent=1, sort_keys=True, ensure_ascii=False,
                  default=_json_default)
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
        # selftests are programs (they may SystemExit at import) — never
        # scanned; and a broken module file must not take the server
        # down (2026-09-09: foodstate's selftest raised SystemExit here).
        if (not fname.endswith('.py') or fname.startswith('selftest')
                or fname.endswith('_selftest.py')):
            continue
        try:
            mod = importlib.import_module(f'{package}.{fname[:-3]}')
        except BaseException:  # noqa: BLE001
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
        class_name = payload.get('class')
        if payload.get('legacy') or not class_name:
            skipped.append((payload.get('file', '?'),
                            'legacy bare-list file — rename to <ClassName>.json '
                            'with the module-initial-data/1 header to load'))
            continue
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
    from composition.custom.seed_upsert import upsert_seed_pairs
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


# ---------------------------------------------------------------------------
# The EXPORT path (mo-3): live tables -> initialData/<Class>.json
# ---------------------------------------------------------------------------

#: `source` prefix of every file export_rows writes — the only files
#: it will ever delete (a class whose user rows all went away).
EXPORT_SOURCE_PREFIX = 'export_rows:'


def load_export_hook(package):
    """The module's `export_hook` module, or None when it has none.
    A hook that exists but fails to import is an error worth seeing."""
    try:
        try:
            return importlib.import_module(f'{package}.export_hook')
        except ModuleNotFoundError:
            # sap-2: concept-less code lives in custom/ — the hook moved there
            return importlib.import_module(f'{package}.custom.export_hook')
    except ModuleNotFoundError as exc:
        if exc.name == f'{package}.export_hook':
            return None
        raise


def _hook_call(hook, fn_name, *args, default=None):
    fn = getattr(hook, fn_name, None) if hook is not None else None
    return fn(*args) if callable(fn) else default


def package_class_names(package):
    """The class names a package registers, from its `<PKG>_CLASSES`
    list (class objects or names); [] when it has none."""
    try:
        mod = importlib.import_module(package)
    except Exception:  # noqa: BLE001
        return []
    classes = getattr(mod, f'{package.upper()}_CLASSES', None) or []
    return [c if isinstance(c, str) else getattr(c, '__name__', str(c))
            for c in classes]


def row_dict(obj):
    """A live object as a plain dict: every public attribute except the
    tree bookkeeping (META_KEYS). Extra attributes a row picked up are
    KEPT so a privacy hook can see them; the load side re-filters to
    constructor fields (to_seed)."""
    if isinstance(obj, dict):
        items = obj.items()
    else:
        items = vars(obj).items()
    return {k: v for k, v in items
            if k not in META_KEYS and not k.startswith('_')
            and not callable(v)}


def _table_rows(manager, class_name):
    table = (getattr(manager, 'objectTables', None) or {}).get(class_name)
    if table is None:
        return None
    return list(table.values()) if isinstance(table, dict) else list(table)


def export_rows(manager, package, class_names=None, only_non_prior=True,
                strip_fields=(), hook=None, out_dir=None, source=''):
    """Write the package's live rows to initialData/<Class>.json.

    Class list: `class_names` > hook.include_classes() > <PKG>_CLASSES.
    Rows kept: is_prior EXPLICITLY False when `only_non_prior` (D5:
    user-authored; seeds stay in code) — except classes the hook's
    include_prior_classes() names, exported whole. Then per row:
    hook.filter_row (None drops it), then META_KEYS + `strip_fields` +
    hook.strip_fields() removed. Files are written only for classes
    with rows; a stale file this exporter wrote earlier is removed.

    Returns {'package', 'classes': {cls: count}, 'files': [paths],
    'removed': [paths], 'stripped_fields': [...], 'dropped': {cls:
    [names]}, 'skipped': [(cls, why)], 'total'}.
    """
    hook = hook if hook is not None else load_export_hook(package)
    names = list(class_names or _hook_call(hook, 'include_classes', default=None)
                 or package_class_names(package))
    if not names:
        raise ValueError(
            f'{package}: nothing to export — no class list given, no '
            f'{package}.export_hook with include_classes(), and no '
            f'{package.upper()}_CLASSES in the package')
    whole = set(_hook_call(hook, 'include_prior_classes', default=()) or ())
    stripped = set(strip_fields) | set(_hook_call(hook, 'strip_fields', default=()) or ())
    label = f'{EXPORT_SOURCE_PREFIX} {package} from {source or "live tables"}; ' \
            f'{"is_prior=False rows only" if only_non_prior else "all rows"}; ' \
            f'stripped: {", ".join(sorted(stripped)) or "-"}'
    result = {'package': package, 'classes': {}, 'files': [], 'removed': [],
              'stripped_fields': sorted(stripped), 'dropped': {},
              'skipped': [], 'total': 0}
    target_dir = out_dir or data_dir(package)
    for class_name in names:
        objs = _table_rows(manager, class_name)
        if objs is None:
            result['skipped'].append((class_name, 'no live table (class not booted?)'))
            continue
        kept, dropped = [], []
        for obj in objs:
            row = row_dict(obj)
            if only_non_prior and class_name not in whole:
                flag = row.get('is_prior', True)
                if flag is None or flag:
                    continue
            filtered = _hook_call(hook, 'filter_row', class_name, row, default=row)
            if filtered is None:
                dropped.append(str(row.get('name', '?')))
                continue
            kept.append({k: v for k, v in filtered.items() if k not in stripped})
        result['classes'][class_name] = len(kept)
        result['total'] += len(kept)
        if dropped:
            result['dropped'][class_name] = dropped
        path = os.path.join(target_dir, f'{class_name}.json') if target_dir else None
        if kept:
            result['files'].append(write_file(package, class_name, kept,
                                              source=label, out_dir=out_dir))
        elif path and os.path.isfile(path):
            try:
                stale = read_file(path).get('source', '')
            except Exception:  # noqa: BLE001
                stale = ''
            if str(stale).startswith(EXPORT_SOURCE_PREFIX):
                os.remove(path)
                result['removed'].append(path)
    return result
