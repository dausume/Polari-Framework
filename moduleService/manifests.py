"""
@module moduleService.manifests

The Standardized Polari App manifest — `modules/<pkg>/polari-app.json`
(schema `polari-app/1`; AI-Notes/designs/STANDARD_POLARI_APP.md §2).

sap-1 (2026-09-08, his go: "make the polari-app.json entries so we can
have a standard format and ensure that concept wise we are consistent"):
ONE declaration per module, in the module, naming every concept file
(basis / api / endpoints / seed / page / engine / remote / catalog /
selftests / initialData) and everything the TEN hand-written core tables
currently hold for it (registry row, FEATURE_MODULES, FEATURE_REQUIRES,
FEATURE_IMPORT_BLOCKS, MODULE_ENDPOINT_CONSTRUCTORS, feature_derived,
seed pairs, page seeds, ENGINE_MAP).

Two directions, both here so they cannot drift:
  generate  — DERIVE a manifest from the tables + an AST scan of the
              package (the first, complete, consistent set; also the
              refresh path while the tables are still hand-written)
  conform   — REPORT what the manifest claims vs what the files contain
              vs what the tables say (never a gate; parity is sap-3)

    python3 -m moduleService.manifests generate [<module>...|--all]
    python3 -m moduleService.manifests conform  [<module>...|--all]
    python3 -m moduleService.manifests list
    python3 -m moduleService.manifests readme   [<module>...|--all]   first README.md from the manifest (never overwrites)

Nothing here imports a module's code: classification is by AST, so a
manifest can be generated for a module whose dependencies are absent.
"""
import ast
import json
import os
import re
import sys

SCHEMA = 'polari-app/1'
MANIFEST_NAME = 'polari-app.json'
CONCEPTS = ('basis', 'api', 'endpoints', 'seed', 'page', 'catalog',
            'remote', 'selftests', 'custom', 'other')
#: app.kind (his rule 2026-09-08): a hardware KVM app is a KIND beside the
#: others — library (objects only), polari-app (pages/API inside a Polari
#: instance), isle-app (a container app deployed on the isle), hardware-app
#: (a QEMU/KVM guest owning hardware; POLARI_TREE_PLAN / STANDARD_POLARI_APP §3).
APP_KINDS = ('library', 'polari-app', 'isle-app', 'hardware-app')
POSTFIXES = {'_basis': 'basis', '_api': 'api', '_endpoints': 'endpoints', '_seed': 'seed',
             '_page': 'page', '_catalog': 'catalog', '_remote': 'remote', '_selftest': 'selftests'}
AGENT_TIERS = ('reach', 'member', 'hardware', 'core')

_FW = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_MODULES = os.path.join(_FW, 'modules')


# ---------------------------------------------------------------- paths

def module_dir(pkg):
    for root in (_MODULES, _FW):
        d = os.path.join(root, pkg)
        if os.path.isfile(os.path.join(d, '__init__.py')):
            return d
    return None


def manifest_path(pkg):
    d = module_dir(pkg)
    return os.path.join(d, MANIFEST_NAME) if d else None


def all_packages():
    out = []
    for entry in sorted(os.listdir(_MODULES)):
        d = os.path.join(_MODULES, entry)
        if os.path.isfile(os.path.join(d, '__init__.py')):
            out.append(entry)
    return out


def load(pkg):
    p = manifest_path(pkg)
    if not p or not os.path.isfile(p):
        return None
    with open(p) as fh:
        return json.load(fh)


def all_manifests():
    return {pkg: m for pkg in all_packages() for m in [load(pkg)] if m}


# ------------------------------------------------------------- the tables

def _registry():
    with open(os.path.join(_MODULES, 'polari-modules.json')) as fh:
        reg = json.load(fh)['modules']
    by_path = {}
    for mid, entry in reg.items():
        by_path[os.path.basename(entry.get('path', 'modules/' + mid))] = (mid, entry)
    return reg, by_path


def _tables():
    """The core tables, read without booting anything."""
    t = {'feature_modules': set(), 'feature_requires': {}, 'core_required': set(),
         'import_blocks': {}, 'endpoint_ctors': set(), 'derived': set(), 'engine_map': {}}
    try:
        from moduleService import module_loading as ml
        t['feature_modules'] = set(ml.FEATURE_MODULES)
        t['feature_requires'] = {k: list(v) for k, v in ml.FEATURE_REQUIRES.items()}
        t['core_required'] = set(ml.CORE_REQUIRED_MODULES)
    except Exception as e:  # noqa: BLE001
        t['error_loading'] = str(e)
    try:
        from polariApiServer.feature_imports import FEATURE_IMPORT_BLOCKS
        for mod, blocks in FEATURE_IMPORT_BLOCKS:
            t['import_blocks'].setdefault(mod, []).extend(
                [path, list(symbols)] for path, symbols in blocks)
    except Exception as e:  # noqa: BLE001
        t['error_imports'] = str(e)
    src = os.path.join(_FW, 'polariApiServer', 'module_endpoints.py')
    if os.path.isfile(src):
        t['endpoint_ctors'] = set(re.findall(r"^\s+'([a-z_0-9]+)':\s*construct_", open(src).read(), re.M))
    src = os.path.join(_FW, 'polariApiServer', 'feature_derived.py')
    if os.path.isfile(src):
        t['derived'] = set(re.findall(r"'feature_derived:%s' % '([a-z_0-9]+)'", open(src).read()))
    try:
        sys.path.insert(0, _MODULES)
        from appstore.custom.module_requirements import ENGINE_MAP
        t['engine_map'] = {k: [dict(e) for e in v] for k, v in ENGINE_MAP.items()}
    except Exception as e:  # noqa: BLE001
        t['error_engines'] = str(e)
    return t


# ------------------------------------------------------- the AST scan

def _scan_file(path):
    """Facts about one .py file: treeObject classes, SEED_ names,
    page-seed names, add_route, construct_* defs, imports of the
    package."""
    facts = {'classes': [], 'seeds': [], 'pages': [], 'routes': False,
             'constructs': [], 'imports_pkg': set(), 'module_doc': ''}
    try:
        tree = ast.parse(open(path, encoding='utf-8').read(), path)
    except Exception as e:  # noqa: BLE001
        facts['parse_error'] = str(e)
        return facts
    doc = ast.get_docstring(tree) or ''
    m = re.search(r'@module\s+(\S+)', doc)
    facts['module_doc'] = m.group(1) if m else ''
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            bases = [getattr(b, 'id', getattr(b, 'attr', '')) for b in node.bases]
            if 'treeObject' in bases:
                facts['classes'].append(node.name)
        elif isinstance(node, ast.Assign) and tree.body and node in tree.body:
            for tgt in node.targets:
                if isinstance(tgt, ast.Name):
                    if re.match(r'SEED_\w*(PAGE|PAGES)\w*$', tgt.id):
                        facts['pages'].append(tgt.id)
                    elif tgt.id.startswith('SEED_'):
                        facts['seeds'].append(tgt.id)
        elif isinstance(node, ast.FunctionDef) and node.name.startswith('construct_'):
            facts['constructs'].append(node.name)
        elif isinstance(node, ast.Attribute) and node.attr == 'add_route':
            facts['routes'] = True
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            mod = getattr(node, 'module', None) or ''
            names = [a.name for a in node.names] if isinstance(node, ast.Import) else [mod]
            for n in names:
                facts['imports_pkg'].add(n.split('.')[0])
    return facts


def classify(pkg, d):
    """{concept: [file, ...]} + the per-file facts. POSTFIX FIRST (the
    standard): a file's own `_basis/_api/_endpoints/_seed/_page/_catalog/
    _remote/_selftest` postfix decides; the legacy `selftest_` prefix is
    still recognised; `custom/<file>.py` is the custom concept; anything
    else at the top level is classified by AST and reported as 'other'
    (a name the standard would rename)."""
    files = {c: [] for c in CONCEPTS}
    facts = {}
    for name in sorted(os.listdir(d)):
        if not name.endswith('.py') or name == '__init__.py':
            continue
        stem = name[:-3]
        f = _scan_file(os.path.join(d, name))
        facts[stem] = f
        concept = None
        for pf, c in POSTFIXES.items():
            if stem.endswith(pf):
                concept = c
                break
        if concept is None and stem.startswith('selftest_'):
            concept = 'selftests'
        if concept is None:
            concept = 'other'
        files[concept].append(stem)
    custom = os.path.join(d, 'custom')
    if os.path.isdir(custom):
        for name in sorted(os.listdir(custom)):
            if name.endswith('.py') and name != '__init__.py':
                stem = 'custom/' + name[:-3]
                facts[stem] = _scan_file(os.path.join(custom, name))
                files['custom'].append(stem)
    return files, facts


# ---------------------------------------------------------- generate

def _title(pkg):
    return ' '.join(w.capitalize() for w in re.split(r'[_\-]', pkg))


def generate(pkg, tables=None, registry=None):
    d = module_dir(pkg)
    if not d:
        return None, 'no package dir for %r' % pkg
    tables = tables or _tables()
    reg, by_path = registry or _registry()
    mid, entry = by_path.get(os.path.basename(d), (pkg, reg.get(pkg, {})))
    files, facts = classify(pkg, d)
    classes = sorted({c for f in facts.values() for c in f['classes']})
    seed_pairs = None
    pages = []
    catalog_kinds = set()
    for stem, f in facts.items():
        src = open(os.path.join(d, stem + '.py'), encoding='utf-8').read()
        if re.search(r'^%s_SEED_PAIRS\s*=' % pkg.upper(), src, re.M):
            seed_pairs = '%s.%s:%s_SEED_PAIRS' % (pkg, stem, pkg.upper())
        for p in f['pages']:
            pages.append('%s.%s:%s' % (pkg, stem, p))
        if stem in files['catalog']:
            catalog_kinds.update(re.findall(r"'kind':\s*'([a-z][a-z0-9-]+)'", src))
    init_src = open(os.path.join(d, '__init__.py'), encoding='utf-8').read()
    if re.search(r'^%s_SEED_PAIRS\s*=' % pkg.upper(), init_src, re.M):
        seed_pairs = '%s:%s_SEED_PAIRS' % (pkg, pkg.upper())
    init_doc = ast.get_docstring(ast.parse(init_src)) or ''
    endpoints = None
    if mid in tables['endpoint_ctors']:
        endpoints = 'polariApiServer.module_endpoints:construct_%s_endpoints' % mid
    for stem in files['endpoints']:
        for c in facts[stem]['constructs']:
            endpoints = '%s.%s:%s' % (pkg, stem, c)
    has_api = bool(files['api']) or endpoints is not None
    app_kind = 'polari-app' if has_api else 'library'
    requires_mods = sorted(set(entry.get('requires', [])) | set(tables['feature_requires'].get(mid, [])))
    manifest = {
        'schema': SCHEMA,
        'id': mid,
        'package': pkg,
        'title': _title(mid),
        'description': entry.get('description', '') or init_doc.strip().split('\n')[0][:200],
        'version': '0.1.0',
        'kind': entry.get('kind', 'official'),
        'wave': entry.get('wave'),
        'repo': entry.get('repo', ''),
        'app': {
            'kind': app_kind,
            'family': '',
            'catalogKinds': sorted(catalog_kinds),
            'agentTier': 'member',
        },
        'requires': {
            'modules': requires_mods,
            'libraries': [],
            'engines': tables['engine_map'].get(mid, []),
        },
        'files': {c: v for c, v in files.items() if v},
        'classes': classes,
        'imports': tables['import_blocks'].get(mid, []),
        'endpoints': endpoints,
        'seedPairs': seed_pairs,
        'pages': sorted(pages),
        'derivedSeeds': mid in tables['derived'],
        'initialData': os.path.isdir(os.path.join(d, 'initialData')),
        'selftests': files['selftests'],
        'featureModule': mid in tables['feature_modules'],
        'coreRequired': mid in tables['core_required'] or bool(entry.get('required_by_core')),
        'legacyDynamicModule': os.path.isfile(os.path.join(d, '_module_metadata.json'))
                               or 'def initialize(' in init_src,
    }
    return manifest, None


def write(pkg, manifest):
    p = os.path.join(module_dir(pkg), MANIFEST_NAME)
    with open(p, 'w', encoding='utf-8') as fh:
        json.dump(manifest, fh, indent=1, ensure_ascii=False)
        fh.write('\n')
    return p


# ---------------------------------------------------------- validate

def validate(manifest):
    """Static rules; returns a list of problems (empty = valid)."""
    problems = []
    if not isinstance(manifest, dict):
        return ['manifest is not an object']
    if manifest.get('schema') != SCHEMA:
        problems.append('schema must be %r' % SCHEMA)
    for key in ('id', 'package', 'title', 'app', 'requires', 'files', 'classes'):
        if key not in manifest:
            problems.append('missing %r' % key)
    app = manifest.get('app') or {}
    if app.get('kind') not in APP_KINDS:
        problems.append('app.kind must be one of %s' % (APP_KINDS,))
    if app.get('agentTier') not in AGENT_TIERS:
        problems.append('app.agentTier must be one of %s' % (AGENT_TIERS,))
    pkg = manifest.get('package', '')
    for path, _symbols in manifest.get('imports', []):
        if path.split('.')[0] != pkg:
            problems.append('import path %r is not inside package %r' % (path, pkg))
    for ref in [manifest.get('endpoints'), manifest.get('seedPairs')] + list(manifest.get('pages', [])):
        if ref and not ref.startswith(('polariApiServer.', pkg + '.', pkg + ':')):
            problems.append('reference %r is not inside package %r' % (ref, pkg))
    for concept in manifest.get('files', {}):
        if concept not in CONCEPTS:
            problems.append('unknown concept %r' % concept)
    return problems


# ----------------------------------------------------------- conform

def conform(pkg, tables=None, registry=None):
    """The report: manifest vs files vs tables. Returns a dict with
    'ok' (manifest present + valid + no drift) and 'findings'."""
    findings = []
    m = load(pkg)
    if m is None:
        return {'package': pkg, 'ok': False, 'findings': ['no polari-app.json (legacy: generate it)']}
    findings += ['invalid: ' + p for p in validate(m)]
    d = module_dir(pkg)
    files, facts = classify(pkg, d)
    declared = {f for v in m.get('files', {}).values() for f in v}
    present = {f for v in files.values() for f in v}
    for f in sorted(present - declared):
        findings.append('file not in manifest: %s.py' % f)
    for f in files.get('other', []):
        findings.append('%s.py has no concept postfix (standard: _basis/_api/_seed/_page/... or custom/)' % f)
    for f in sorted(declared - present):
        findings.append('manifest names a missing file: %s.py' % f)
    for concept, names in m.get('files', {}).items():
        for f in names:
            actual = next((c for c, v in files.items() if f in v), None)
            if actual and actual != concept:
                findings.append('%s.py: manifest says %s, scan says %s' % (f, concept, actual))
    scanned_classes = sorted({c for f in facts.values() for c in f['classes']})
    if scanned_classes != sorted(m.get('classes', [])):
        findings.append('classes drift: manifest %d, files %d' % (len(m.get('classes', [])), len(scanned_classes)))
    fresh, _ = generate(pkg, tables, registry)
    for key in ('imports', 'endpoints', 'seedPairs', 'pages', 'derivedSeeds', 'featureModule', 'coreRequired'):
        if fresh and fresh.get(key) != m.get(key):
            findings.append('%s drift vs the core tables' % key)
    if fresh and sorted(fresh['requires']['modules']) != sorted(m.get('requires', {}).get('modules', [])):
        findings.append('requires.modules drift vs registry/FEATURE_REQUIRES')
    if not m.get('selftests'):
        findings.append('no selftest_*.py (the standard requires one)')
    if not os.path.isfile(os.path.join(d, 'README.md')):
        findings.append('no README.md (the standard asks for one)')
    return {'package': pkg, 'id': m.get('id'), 'kind': m['app']['kind'],
            'ok': not findings, 'findings': findings}


# ------------------------------------------------------------ readme

def render_readme(m):
    """A first README.md from the manifest — what it is, its kind, the
    objects, the concept files, how to run its selftest. Written only
    when the module has none (never overwrites a hand-written one)."""
    files = m.get('files', {})
    lines = ['# %s (`%s`)' % (m.get('title', m['id']), m['id']), '',
             (m.get('description') or '').strip() or '_No description in the registry yet._', '',
             '**Kind:** %s · **agent tier:** %s · **requires:** %s' % (
                 m['app']['kind'], m['app'].get('agentTier', 'member'),
                 ', '.join(m['requires'].get('modules', [])) or 'nothing'), '']
    if m['app'].get('catalogKinds'):
        lines += ['**Catalog kinds this module adds:** ' + ', '.join(m['app']['catalogKinds']), '']
    if m.get('classes'):
        lines += ['## Objects', '', ', '.join('`%s`' % c for c in m['classes']), '']
    lines += ['## Layout (the Standardized Polari App, postfix names)', '']
    for concept in ('basis', 'api', 'endpoints', 'seed', 'page', 'catalog', 'remote', 'custom', 'selftests', 'other'):
        if files.get(concept):
            lines.append('- **%s** — %s' % (concept, ', '.join('`%s.py`' % f for f in files[concept])))
    if m.get('initialData'):
        lines.append('- **initialData/** — module-initial-data/1 rows (non-regenerable data only)')
    lines += ['', '`polari-app.json` is the manifest the core reads; `custom/` holds code that fits no concept file.', '']
    if m.get('pages'):
        lines += ['## Pages', ''] + ['- `%s`' % p for p in m['pages']] + ['']
    lines += ['## Selftest', '', '```', 'pol modules selftest %s        # in the running backend' % m['id'],
              'PYTHONPATH=.:modules python3 -m %s.%s   # on the host, from polari-framework/' % (
                  m.get('package', m['id']), (m.get('selftests') or ['<none yet>'])[0]),
              '```', '', 'Conformance: `pol modules conform %s`' % m['id'], '']
    return '\n'.join(lines)


# --------------------------------------------------------------- cli

def main(argv):
    if not argv or argv[0] in ('-h', '--help'):
        print(__doc__)
        return 0
    verb, args = argv[0], argv[1:]
    pkgs = all_packages() if (not args or args == ['--all']) else args
    if verb == 'list':
        for p in pkgs:
            m = load(p)
            print('%-32s %s' % (p, ('%s kind=%s classes=%d' % (m['id'], m['app']['kind'], len(m['classes']))) if m else '(no manifest)'))
        return 0
    tables, registry = _tables(), _registry()
    if verb == 'generate':
        n = 0
        for p in pkgs:
            m, err = generate(p, tables, registry)
            if err:
                print('%s: %s' % (p, err))
                continue
            problems = validate(m)
            if problems:
                print('%s: generated manifest INVALID: %s' % (p, problems))
                continue
            print('%s -> %s (%s, %d classes, %d files)' % (p, os.path.relpath(write(p, m), _FW),
                  m['app']['kind'], len(m['classes']), sum(len(v) for v in m['files'].values())))
            n += 1
        print('%d manifest(s) written' % n)
        return 0
    if verb == 'readme':
        n = 0
        for p in pkgs:
            m = load(p)
            d = module_dir(p)
            if not m or os.path.isfile(os.path.join(d, 'README.md')):
                continue
            open(os.path.join(d, 'README.md'), 'w', encoding='utf-8').write(render_readme(m))
            n += 1
        print('%d README.md written (existing ones untouched)' % n)
        return 0
    if verb == 'conform':
        bad = 0
        for p in pkgs:
            r = conform(p, tables, registry)
            flag = 'OK  ' if r['ok'] else 'DRIFT'
            print('%s %-28s %s' % (flag, p, '' if r['ok'] else '; '.join(r['findings'])[:220]))
            bad += 0 if r['ok'] else 1
        print('%d/%d conform' % (len(pkgs) - bad, len(pkgs)))
        return 1 if bad else 0
    print('unknown verb %r' % verb)
    return 2


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
