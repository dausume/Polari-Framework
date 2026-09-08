"""
@module moduleService.standardize_layout

sap-2 layout migration (his rules 2026-09-08): inside every module,
POSTFIX concept names take precedence over prefix patterns and are the
standard — `<x>_basis.py`, `<x>_api.py`, `<x>_endpoints.py`,
`<x>_seed.py`, `<x>_page.py`, `<x>_catalog.py`, `<x>_remote.py`,
`<x>_selftest.py` — a module-name PREFIX is only for custom code, and
custom code that fits no concept lives in its own folder,
`modules/<pkg>/custom/`. Module directories are named by their registry
id (the two legacy `polari*Module` dirs are renamed). The overall logic
stays the same: files move, dotted references are rewritten everywhere,
nothing else changes.

    python3 -m moduleService.standardize_layout plan  [<pkg>...]   dry run: the rename map
    python3 -m moduleService.standardize_layout apply [<pkg>...]   git mv + rewrite references
    python3 -m moduleService.standardize_layout import-all         try to import every module file (baseline / verify)
    python3 -m moduleService.standardize_layout rewrite-from-git   resume the reference rewrite from git's staged renames

Classification: the file's own postfix decides when it carries one;
otherwise the AST decides (treeObject classes → _basis, add_route →
_api, construct_* → _endpoints, SEED page names → _page, SEED_* /
seedData → _seed); anything else is custom/. Subpackages inside a module
are already "their own folder" and are left alone.
"""
import ast
import os
import re
import subprocess
import sys

from moduleService import manifests as M

POSTFIXES = ('_basis', '_api', '_endpoints', '_seed', '_page', '_catalog', '_remote', '_selftest')
PAGE_ALIASES = ('_pages', '_pages_seed', '_page_displays')
DIR_RENAMES = {'polari' + 'MaterialsScienceModule': 'materials_science',   # split so the rewrite never clobbers this table
               'polari' + 'AgroForestryModule': 'agro_forestry'}
FW = M._FW
SUITE = os.path.dirname(os.path.dirname(FW))
# where dotted/path references are rewritten
REWRITE_ROOTS = [FW, os.path.join(SUITE, 'polari-cli', 'scripts'), os.path.join(SUITE, 'polari-cli', 'shells')]
REWRITE_SUFFIXES = ('.py', '.sh', '.json', '.yml', '.yaml', '.md', '.txt', '.cfg', '.ini')
SKIP_DIRS = {'__pycache__', '.git', 'node_modules', '.generated', 'venv', '.venv'}


def _new_stem(pkg, stem, facts):
    """(new_stem, subdir) — subdir '' or 'custom'."""
    if stem.startswith('selftest_'):
        topic = stem[len('selftest_'):]
        return ((topic if topic else pkg) + '_selftest'), ''
    for alias in PAGE_ALIASES:
        if stem.endswith(alias):
            base = stem[:-len(alias)]
            return (base if base else pkg) + '_page', ''
    if stem == 'pages_seed':
        return pkg + '_page', ''
    if stem == 'seedData':
        return pkg + '_data_seed', ''
    for pf in POSTFIXES:
        if stem.endswith(pf):
            return stem, ''
    f = facts.get(stem, {})
    if f.get('pages'):
        return stem + '_page', ''
    if f.get('routes'):
        return stem + '_api', ''
    if f.get('constructs'):
        return stem + '_endpoints', ''
    if f.get('classes'):
        return stem + '_basis', ''
    if f.get('seeds'):
        return stem + '_seed', ''
    return stem, 'custom'


def plan(pkgs=None):
    """{old_dotted: new_dotted} for files + {old_pkg: new_pkg} for dirs."""
    files = {}
    dirs = {}
    for pkg in (pkgs or M.all_packages()):
        d = M.module_dir(pkg)
        if not d:
            continue
        new_pkg = DIR_RENAMES.get(pkg, pkg)
        if new_pkg != pkg:
            dirs[pkg] = new_pkg
        _files, facts = M.classify(pkg, d)
        for name in sorted(os.listdir(d)):
            if not name.endswith('.py') or name == '__init__.py':
                continue
            stem = name[:-3]
            new_stem, sub = _new_stem(new_pkg, stem, facts)
            new_dotted = '.'.join(x for x in (new_pkg, sub, new_stem) if x)
            old_dotted = pkg + '.' + stem
            if new_dotted != old_dotted:
                files[old_dotted] = new_dotted
    return files, dirs


def _iter_rewrite_files():
    for root in REWRITE_ROOTS:
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [x for x in dirnames if x not in SKIP_DIRS]
            for fn in filenames:
                if fn.endswith(REWRITE_SUFFIXES):
                    yield os.path.join(dirpath, fn)


def _rewrite(files_map, dirs_map):
    """Rewrite every dotted and path reference with ONE combined regex
    per form (an alternation of all old names, longest first) and a
    dict lookup — thousands of files x hundreds of names stays fast."""
    if not files_map and not dirs_map:
        return 0
    dotted = {old: new for old, new in files_map.items()}
    paths = {old.replace('.', '/') + '.py': new.replace('.', '/') + '.py' for old, new in files_map.items()}
    forms = []
    if dotted:
        alt = '|'.join(re.escape(k) for k in sorted(dotted, key=len, reverse=True))
        forms.append((re.compile(r'(?<![\w.])(?:' + alt + r')(?![\w])'), dotted))
        alt = '|'.join(re.escape(k) for k in sorted(paths, key=len, reverse=True))
        forms.append((re.compile(r'(?<![\w/])(?:' + alt + r')\b'), paths))
    if dirs_map:
        alt = '|'.join(re.escape(k) for k in sorted(dirs_map, key=len, reverse=True))
        forms.append((re.compile(r'(?<![\w])(?:' + alt + r')(?![\w])'), dict(dirs_map)))
    touched = 0
    for path in _iter_rewrite_files():
        try:
            src = open(path, encoding='utf-8').read()
        except (UnicodeDecodeError, OSError):
            continue
        out = src
        for rx, table in forms:
            out = rx.sub(lambda m: table[m.group(0)], out)
        if out != src:
            open(path, 'w', encoding='utf-8').write(out)
            touched += 1
    return touched


def map_from_git():
    """Recover {old_dotted: new_dotted} + dir renames from the STAGED
    renames (git mv) — the resume path when a rewrite was interrupted."""
    out = subprocess.check_output(['git', '-C', FW, 'diff', '--cached', '-M', '--name-status'], text=True)
    files, dirs = {}, {}
    for line in out.splitlines():
        parts = line.split('\t')
        if not parts[0].startswith('R') or len(parts) != 3:
            continue
        old, new = parts[1], parts[2]
        if not (old.startswith('modules/') and new.startswith('modules/') and old.endswith('.py')):
            continue
        o = old[len('modules/'):-3].split('/'); n = new[len('modules/'):-3].split('/')
        if o[0] != n[0]:
            dirs[o[0]] = n[0]
        if o[-1] == '__init__':
            continue
        files['.'.join(o)] = '.'.join(n)
    return files, dirs


def apply(pkgs=None):
    files_map, dirs_map = plan(pkgs)
    moved = 0
    # 1. directories first (the file map already speaks the new names)
    for old, new in dirs_map.items():
        subprocess.run(['git', '-C', FW, 'mv', os.path.join('modules', old), os.path.join('modules', new)], check=True)
    # 2. files
    for old, new in files_map.items():
        old_pkg, old_stem = old.split('.', 1)
        parts = new.split('.')
        new_pkg, new_rel = parts[0], os.path.join(*parts[1:]) + '.py'
        src = os.path.join(FW, 'modules', dirs_map.get(old_pkg, old_pkg), old_stem + '.py')
        dst = os.path.join(FW, 'modules', new_pkg, new_rel)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        init = os.path.join(os.path.dirname(dst), '__init__.py')
        if 'custom' in parts[1:2] and not os.path.exists(init):
            open(init, 'w').write('"""@module %s.custom — custom code that fits no concept file; module-name prefixes are allowed here."""\n' % new_pkg)
            subprocess.run(['git', '-C', FW, 'add', init], check=True)
        subprocess.run(['git', '-C', FW, 'mv', src, dst], check=True)
        moved += 1
    # 3. references
    touched = _rewrite(files_map, dirs_map)
    return {'dirs': len(dirs_map), 'files': moved, 'rewrittenFiles': touched}


def import_all(pkgs=None):
    """Try to import every module file; returns {dotted: error or ''}."""
    sys.path[:0] = [FW, os.path.join(FW, 'modules')]
    import importlib
    results = {}
    for pkg in (pkgs or M.all_packages()):
        d = M.module_dir(pkg)
        for dirpath, dirnames, filenames in os.walk(d):
            dirnames[:] = [x for x in dirnames if x not in SKIP_DIRS and x != 'initialData']
            for fn in filenames:
                if not fn.endswith('.py') or fn == '__init__.py':
                    continue
                rel = os.path.relpath(os.path.join(dirpath, fn[:-3]), os.path.dirname(d))
                dotted = rel.replace(os.sep, '.')
                if dotted.split('.')[-1].endswith('_selftest') or dotted.split('.')[-1].startswith('selftest_'):
                    continue  # selftests execute on import
                try:
                    importlib.import_module(dotted)
                    results[dotted] = ''
                except BaseException as e:  # noqa: BLE001
                    results[dotted] = '%s: %s' % (type(e).__name__, str(e)[:120])
    return results


def main(argv):
    verb, args = (argv[0] if argv else 'plan'), argv[1:]
    pkgs = args or None
    if verb == 'plan':
        files_map, dirs_map = plan(pkgs)
        for old, new in dirs_map.items():
            print('DIR  %s -> %s' % (old, new))
        for old, new in files_map.items():
            print('FILE %s -> %s' % (old, new))
        print('%d dir(s), %d file(s) would move' % (len(dirs_map), len(files_map)))
        return 0
    if verb == 'apply':
        print(apply(pkgs))
        return 0
    if verb == 'rewrite-from-git':
        files_map, dirs_map = map_from_git()
        print({'files': len(files_map), 'dirs': len(dirs_map), 'rewrittenFiles': _rewrite(files_map, dirs_map),
               'fromImportsFixed': fix_from_imports(files_map), 'fileRelativeFixed': fix_file_relative_paths(files_map)})
        return 0
    if verb == 'fold-subpackages':
        for pkg in (pkgs or []):
            print(pkg, fold_subpackages(pkg))
        return 0
    if verb == 'import-all':
        r = import_all(pkgs)
        bad = {k: v for k, v in r.items() if v}
        for k, v in sorted(bad.items()):
            print('FAIL %s — %s' % (k, v))
        print('%d/%d importable' % (len(r) - len(bad), len(r)))
        return 0
    print(__doc__)
    return 2



# ---- sap-2 follow-up: `from <pkg> import <moved module>` (module-as-name
# imports) are not dotted references; rewrite them from the git map.
def fix_from_imports(files_map):
    """`from pkg import a, b` where a moved: custom → `from pkg.custom
    import a`; renamed → `from pkg import a_basis as a`. Multi-line
    parenthesised forms handled. Returns files touched."""
    by_pkg = {}
    for old, new in files_map.items():
        pkg, stem = old.split('.', 1)
        if '.' in stem:
            continue
        by_pkg.setdefault(pkg, {})[stem] = new.split('.', 1)[1]
    rx = re.compile(r'^([ \t]*)from[ \t]+([A-Za-z_][\w]*)[ \t]+import[ \t]+(\(([^)]*)\)|([^\n(]+))', re.M)
    touched = 0
    for path in _iter_rewrite_files():
        if not path.endswith('.py'):
            continue
        try:
            src = open(path, encoding='utf-8').read()
        except (UnicodeDecodeError, OSError):
            continue

        def repl(m):
            indent, pkg, body = m.group(1), m.group(2), (m.group(4) if m.group(4) is not None else m.group(5))
            moved = by_pkg.get(pkg)
            if not moved:
                return m.group(0)
            names = [n.strip() for n in body.replace('\n', ' ').split(',') if n.strip()]
            keep, extra = [], []
            for n in names:
                base = n.split(' as ')[0].strip()
                alias = n.split(' as ')[1].strip() if ' as ' in n else base
                if base in moved:
                    new = moved[base]
                    if new.startswith('custom.'):
                        extra.append('%sfrom %s.custom import %s%s' % (indent, pkg, new[len('custom.'):], (' as ' + alias) if alias != new[len('custom.'):] else ''))
                    else:
                        extra.append('%sfrom %s import %s as %s' % (indent, pkg, new, alias))
                else:
                    keep.append(n)
            if not extra:
                return m.group(0)
            lines = []
            if keep:
                lines.append('%sfrom %s import %s' % (indent, pkg, ', '.join(keep)))
            lines.extend(extra)
            return '\n'.join(lines)
        out = rx.sub(repl, src)
        if out != src:
            open(path, 'w', encoding='utf-8').write(out)
            touched += 1
    return touched


def fix_file_relative_paths(files_map):
    """Files moved into custom/ that locate data by `os.path.dirname(
    __file__)` now sit one level deeper: point them at the module root
    again (same logic, same target)."""
    touched = 0
    for old, new in files_map.items():
        parts = new.split('.')
        if 'custom' not in parts[1:2]:
            continue
        path = os.path.join(FW, 'modules', *parts) + '.py'
        try:
            src = open(path, encoding='utf-8').read()
        except OSError:
            continue
        out = src.replace('os.path.dirname(os.path.abspath(__file__))', 'os.path.dirname(os.path.dirname(os.path.abspath(__file__)))')
        out = re.sub(r'os\.path\.dirname\(__file__\)', 'os.path.dirname(os.path.dirname(__file__))', out)
        out = out.replace('Path(__file__).parent', 'Path(__file__).parent.parent').replace('Path(__file__).resolve().parent', 'Path(__file__).resolve().parent.parent')
        if out != src:
            open(path, 'w', encoding='utf-8').write(out)
            touched += 1
    return touched


# ---- sap-2b (his ruling 2026-09-08): stray subpackages fold under custom/
STANDARD_SUBDIRS = {'custom', 'initialData', '__pycache__'}


def fold_subpackages(pkg, keep=()):
    """git mv every non-standard top-level subdirectory of modules/<pkg>
    into modules/<pkg>/custom/<sub>/ and rewrite dotted + path references
    (`pkg.sub…` → `pkg.custom.sub…`). Returns the map used."""
    d = os.path.join(FW, 'modules', pkg)
    moved = {}
    for entry in sorted(os.listdir(d)):
        p = os.path.join(d, entry)
        if not os.path.isdir(p) or entry in STANDARD_SUBDIRS or entry in keep:
            continue
        custom = os.path.join(d, 'custom')
        os.makedirs(custom, exist_ok=True)
        init = os.path.join(custom, '__init__.py')
        if not os.path.exists(init):
            open(init, 'w').write('"""@module %s.custom — custom code that fits no concept file."""\n' % pkg)
            subprocess.run(['git', '-C', FW, 'add', init], check=True)
        subprocess.run(['git', '-C', FW, 'mv', p, os.path.join(custom, entry)], check=True)
        moved[pkg + '.' + entry] = pkg + '.custom.' + entry
    if moved:
        # dotted + path forms; the dirs map also covers `pkg/sub/…` paths
        touched = _rewrite(moved, {})
        paths = {old.replace('.', '/'): new.replace('.', '/') for old, new in moved.items()}
        _rewrite({}, paths)
    return moved

if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
