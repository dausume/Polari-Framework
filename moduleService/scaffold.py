"""
@module moduleService.scaffold

The Standardized Polari App scaffold for HUMANS (design §7, sap-2c):
one class per file under objects/, taxonomy folders, an index per
concept, a manifest, a README and a passing selftest from minute one.

    python3 -m moduleService.scaffold new <id> [--title T] [--kind library|polari-app|isle-app|hardware-app] [--description D]
    python3 -m moduleService.scaffold add-object <module> <ClassName> [--under <taxonomy/path>] [--base <BaseClass>] [--fields "a:str,b:float=0.0"]

`new` writes modules/<id>/ with __init__.py, polari-app.json, README.md,
objects/ (+ a first row class), <id>_basis.py (the index), <id>_seed.py,
<id>_page.py (one configured table — the no-raw-JSON rule met from the
start), <id>_api.py (one GET), <id>_selftest.py, custom/.
`add-object` writes ONE per-class file with the treeObject boilerplate and
the docstring template (what it is / related concepts / how measured or
derived), creates or updates the taxonomy folder's __init__ re-export,
and adds the index line. Registration into the core tables stays the
manifest's job (sap-3) — until then `pol modules conform` names what the
hand-written tables still need.
"""
import json
import os
import re
import sys

from moduleService import manifests as M

FW = M._FW
MODULES = M._MODULES


def _snake(name):
    return re.sub(r'(?<!^)(?=[A-Z])', '_', name).lower()


def _fields(spec):
    out = []
    for item in [x.strip() for x in (spec or '').split(',') if x.strip()]:
        name, _, rest = item.partition(':')
        typ, _, default = rest.partition('=')
        typ = typ.strip() or 'str'
        if not default:
            default = {'str': "''", 'int': '0', 'float': '0.0', 'bool': 'False'}.get(typ, 'None')
        out.append((name.strip(), typ, default.strip()))
    return out


def class_source(pkg, cls, group, base='treeObject', fields=None, docstring=None):
    fields = fields or []
    doc = docstring or ('%s\n\n    What it is: <one paragraph — the concept this row records>.\n'
                        '    Related concepts: <the rows/classes it points at or is pointed at by>.\n'
                        '    How it is measured or derived: <where the numbers come from; cite or derive, never type>.' % cls)
    sig = ['name: str = \'\'']
    body = ['self.name = name']
    for n, t, d in fields:
        sig.append('%s: %s = %s' % (n, t, d))
        body.append('self.%s = %s' % (n, n))
    base_import = '' if base == 'treeObject' else 'from %s.%s_basis import %s\n' % (pkg, pkg, base)
    return ('"""\n@module %s.objects.%s.%s\n\n%s — one class per file (design §7).\n"""\n'
            'from objectTreeDecorators import treeObject, treeObjectInit\n%s\n\n'
            'class %s(%s):\n    """%s\n    """\n\n    @treeObjectInit\n    def __init__(self, %s):\n        %s\n'
            % (pkg, group.replace('/', '.'), cls, cls, base_import, cls, base, doc, ', '.join(sig), '\n        '.join(body)))


def _ensure_pkg_init(path, doc):
    if not os.path.exists(os.path.join(path, '__init__.py')):
        os.makedirs(path, exist_ok=True)
        open(os.path.join(path, '__init__.py'), 'w').write('"""%s"""\n' % doc)


def add_object(pkg, cls, under='', base='treeObject', fields='', docstring=None):
    d = M.module_dir(pkg)
    if not d:
        raise SystemExit('no module %r (pol modules manifests list)' % pkg)
    group = (under or pkg).strip('/')
    objdir = os.path.join(d, 'objects', *group.split('/'))
    _ensure_pkg_init(os.path.join(d, 'objects'), '@module %s.objects — row classes, one class per file (design §7).' % pkg)
    # every taxonomy level is a package that re-exports + explains
    cur = os.path.join(d, 'objects')
    for part in group.split('/'):
        cur = os.path.join(cur, part)
        _ensure_pkg_init(cur, '@module %s.objects.%s\n\n<Explain this taxonomy: what belongs here, how it is organised.>\n' % (pkg, os.path.relpath(cur, os.path.join(d, 'objects')).replace(os.sep, '.')))
    path = os.path.join(objdir, cls + '.py')
    if os.path.exists(path):
        raise SystemExit('%s exists' % path)
    open(path, 'w').write(class_source(pkg, cls, group, base, _fields(fields), docstring))
    dotted = '%s.objects.%s.%s' % (pkg, group.replace('/', '.'), cls)
    line = 'from %s import %s  # noqa: F401\n' % (dotted, cls)
    with open(os.path.join(objdir, '__init__.py'), 'a') as fh:
        fh.write(line)
    index = os.path.join(d, pkg + '_basis.py')
    if not os.path.exists(index):
        open(index, 'w').write('"""\n@module %s.%s_basis\n\nThe INDEX of %s rows (design §7): classes live one-per-file under objects/;\nthis file re-exports them and holds what they share.\n"""\n' % (pkg, pkg, pkg))
    with open(index, 'a') as fh:
        fh.write(line)
    if M.load(pkg) is not None:   # keep the manifest current (conform must stay OK after add-object)
        manifest, _err = M.generate(pkg)
        if manifest:
            old = M.load(pkg)
            for k in ('title', 'description', 'app', 'version', 'repo'):
                manifest[k] = old.get(k, manifest[k])
            M.write(pkg, manifest)
    return path


def new_module(mid, title='', kind='polari-app', description=''):
    d = os.path.join(MODULES, mid)
    if os.path.exists(d):
        raise SystemExit('%s exists' % d)
    os.makedirs(os.path.join(d, 'custom'))
    title = title or ' '.join(w.capitalize() for w in mid.split('_'))
    cls = ''.join(w.capitalize() for w in mid.split('_')) + 'Record'
    open(os.path.join(d, '__init__.py'), 'w').write('"""\n@module %s\n\n%s — %s\n"""\nfrom %s.%s_basis import *  # noqa: F401,F403\n' % (mid, title, description or 'what this module is for.', mid, mid))
    open(os.path.join(d, 'custom', '__init__.py'), 'w').write('"""@module %s.custom — code that fits no concept file."""\n' % mid)
    add_object(mid, cls, fields='value:float=0.0,unit:str')
    open(os.path.join(d, mid + '_seed.py'), 'w').write('"""\n@module %s.%s_seed\n\nSeed rows (upserted by name — never insert-by-name).\n"""\n\nSEED_%s = [\n    {\'name\': \'example-%s\', \'value\': 1.0, \'unit\': \'x\'},\n]\n' % (mid, mid, mid.upper(), mid))
    open(os.path.join(d, mid + '_page.py'), 'w').write('"""\n@module %s.%s_page\n\n/display/%s — configured tables only (no raw JSON on screens).\n"""\nfrom polariApiServer.module_pages_seed import _page, _row, _table\n\nSEED_%s_PAGE_DISPLAYS = [\n    _page(\'%s\', \'%s\', \'%s\', \'%s\', [\n        _row(0, [_table(\'%s-rows\', 0, 12, \'%s rows\', \'%s\', columns=\'name,value,unit\')]),\n    ]),\n]\n' % (mid, mid, mid.replace('_', '-'), mid.upper(), mid.replace('_', '-'), mid.replace('_', '-'), title, cls, mid, title, cls))
    open(os.path.join(d, mid + '_api.py'), 'w').write('"""\n@module %s.%s_api\n\n/api/%s/summary — one GET; add routes in __init__.\n"""\nfrom objectTreeDecorators import treeObject, treeObjectInit\n\n\nclass %sAPI(treeObject):\n    @treeObjectInit\n    def __init__(self, polServer=None, manager=None):\n        self.polServer = polServer\n        self.manager = manager\n        if polServer is not None and getattr(polServer, \'falconServer\', None) is not None:\n            polServer.falconServer.add_route(\'/api/%s/summary\', self, suffix=\'summary\')\n\n    def _rows(self, class_name):\n        return list(((self.manager.objectTables or {}).get(class_name, {}) or {}).values())\n\n    def on_get_summary(self, request, response):\n        response.media = {\'ok\': True, \'rows\': len(self._rows(\'%s\'))}\n' % (mid, mid, mid.replace('_', '-'), ''.join(w.capitalize() for w in mid.split('_')), mid.replace('_', '-'), cls))
    open(os.path.join(d, mid + '_selftest.py'), 'w').write('"""%s_selftest — the module constructs, its seed is well-formed, its page has no raw JSON."""\nimport sys\n\npassed = total = 0\n\n\ndef check(label, cond, extra=\'\'):\n    global passed, total\n    total += 1\n    passed += bool(cond)\n    print(\'  [%%s] %%s %%s\' %% (\'PASS\' if cond else \'FAIL\', label, extra if not cond else \'\'))\n\n\ndef main():\n    from %s.%s_basis import %s\n    from %s.%s_seed import SEED_%s\n    from %s.%s_page import SEED_%s_PAGE_DISPLAYS\n    check(\'row class constructs\', %s(name=\'x\').name == \'x\')\n    check(\'seed rows carry names\', all(r.get(\'name\') for r in SEED_%s))\n    check(\'page has no api-json-panel\', \'api-json-panel\' not in SEED_%s_PAGE_DISPLAYS[0][\'definition\'])\n    print(\'\\n%%d/%%d checks passed\' %% (passed, total))\n    return 0 if passed == total else 1\n\n\nif __name__ == \'__main__\':\n    sys.exit(main())\n' % (mid, mid, mid, cls, mid, mid, mid.upper(), mid, mid, mid.upper(), cls, mid.upper(), mid.upper()))
    manifest, err = M.generate(mid)
    if manifest:
        manifest['title'] = title
        manifest['description'] = description or manifest['description']
        manifest['app']['kind'] = kind
        M.write(mid, manifest)
        open(os.path.join(d, 'README.md'), 'w').write(M.render_readme(manifest))
    return d


def main(argv):
    if not argv or argv[0] in ('-h', '--help'):
        print(__doc__)
        return 0
    verb, args = argv[0], argv[1:]
    opts = {}
    pos = []
    i = 0
    while i < len(args):
        if args[i].startswith('--'):
            opts[args[i][2:]] = args[i + 1] if i + 1 < len(args) else ''
            i += 2
        else:
            pos.append(args[i]); i += 1
    if verb == 'new':
        print('scaffolded', new_module(pos[0], opts.get('title', ''), opts.get('kind', 'polari-app'), opts.get('description', '')))
        return 0
    if verb == 'add-object':
        print('wrote', add_object(pos[0], pos[1], opts.get('under', ''), opts.get('base', 'treeObject'), opts.get('fields', '')))
        return 0
    print('unknown verb', verb)
    return 2


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
