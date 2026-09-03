"""
@module moduleService.selftest_json_seeds

The module data convention's EXPORT -> APPLY round trip (mo-3) on a
temporary package: export_rows writes a fake package's user-authored
rows to a temp dir; apply() loads them into a second fake manager;
a second apply is a no-op; a customized row is never clobbered; the
export hook protocol (include_classes / include_prior_classes /
strip_fields / filter_row) is discovered from `<pkg>/export_hook.py`;
a stale file the exporter wrote is removed when its rows go away;
non-JSON values degrade to text; <PKG>_CLASSES resolves class names.

Run from polari-framework/modules/ (composition must be importable):
  PYTHONPATH=..:../polariApiServer python3 -m moduleService.selftest_json_seeds
"""

import datetime
import json
import os
import sys
import tempfile
import textwrap
from types import SimpleNamespace

from moduleService import json_seeds

_results = []


def check(label, cond, extra=''):
    _results.append((label, bool(cond)))
    print(f'{"PASS" if cond else "FAIL"}: {label}'
          + (f' — {extra}' if extra and not cond else ''))


class Widget:
    """A minimal treeObject stand-in: registers itself in the manager's
    table the way the real decorator does."""
    _next = 100

    def __init__(self, name='', size=0, colour='', secret='',
                 is_prior=True, manager=None):
        self.name = name
        self.size = size
        self.colour = colour
        self.secret = secret
        self.is_prior = is_prior
        self.manager = manager
        self.id = Widget._next
        Widget._next += 1
        self.inTree = None
        self.branch = None
        if manager is not None:
            manager.objectTables.setdefault('Widget', {})[self.id] = self


def fake_manager():
    return SimpleNamespace(objectTables={},
                           objectTypingDict={'Widget': SimpleNamespace(classObject=Widget)})


HOOK_SRC = '''
def include_classes():
    return ['Widget']

def strip_fields():
    return ('secret',)

def filter_row(class_name, row):
    if row.get('name') == 'w:refused':
        return None
    return row
'''


def main():
    print('json_seeds export -> apply round trip')
    with tempfile.TemporaryDirectory() as tmp:
        # a throwaway package on sys.path carrying an export_hook
        pkg_dir = os.path.join(tmp, 'fakepkg')
        os.makedirs(pkg_dir)
        with open(os.path.join(pkg_dir, '__init__.py'), 'w') as f:
            f.write('FAKEPKG_CLASSES = ["Widget"]\n')
        with open(os.path.join(pkg_dir, 'export_hook.py'), 'w') as f:
            f.write(textwrap.dedent(HOOK_SRC))
        sys.path.insert(0, tmp)
        out = os.path.join(tmp, 'out')

        src = fake_manager()
        Widget('w:seeded', 1, 'red', is_prior=True, manager=src)
        Widget('w:user-a', 2, 'blue', secret='hunter2', is_prior=False, manager=src)
        Widget('w:user-b', 3, 'green', is_prior=False, manager=src)
        Widget('w:refused', 4, 'grey', is_prior=False, manager=src)
        src.objectTables['Widget'][999] = SimpleNamespace(
            name='w:dated', size=5, colour='', secret='', is_prior=False,
            when=datetime.date(2026, 9, 3), id=999, manager=None)

        check('package_class_names reads <PKG>_CLASSES',
              json_seeds.package_class_names('fakepkg') == ['Widget'])
        check('load_export_hook finds fakepkg.export_hook',
              json_seeds.load_export_hook('fakepkg') is not None)
        check('load_export_hook is None for a package without one',
              json_seeds.load_export_hook('moduleService') is None)

        res = json_seeds.export_rows(src, 'fakepkg', out_dir=out, source='selftest')
        check('3 user rows exported (seeded prior excluded, one refused by the hook)',
              res['classes'] == {'Widget': 3} and res['total'] == 3, str(res['classes']))
        check('dropped report names the refused row',
              res['dropped'] == {'Widget': ['w:refused']}, str(res['dropped']))
        check('one file written under out_dir',
              res['files'] == [os.path.join(out, 'Widget.json')], str(res['files']))
        payload = json_seeds.read_file(res['files'][0])
        check('file carries the header, count and the exporter source prefix',
              payload['schema'] == json_seeds.SCHEMA and payload['count'] == 3
              and payload['source'].startswith(json_seeds.EXPORT_SOURCE_PREFIX))
        names = [r['name'] for r in payload['rows']]
        check('rows sorted by name', names == sorted(names), str(names))
        check('the stripped field is absent from every row',
              not any('secret' in r for r in payload['rows']))
        check('tree bookkeeping keys absent (id, manager, inTree, branch)',
              not any(k in r for r in payload['rows'] for k in json_seeds.META_KEYS))
        dated = next(r for r in payload['rows'] if r['name'] == 'w:dated')
        check('non-JSON value degraded to text', dated['when'] == '2026-09-03', str(dated))

        # apply into a fresh manager
        dst = fake_manager()
        applied = json_seeds.apply('fakepkg', dst, payloads=[payload], tag='selftest')
        check('apply created the 3 rows', sorted(applied['created'].get('Widget', [])) == sorted(names),
              str(applied))
        loaded = {o.name: o for o in dst.objectTables['Widget'].values()}
        check('loaded rows carry the exported fields (and no secret)',
              loaded['w:user-a'].size == 2 and loaded['w:user-a'].colour == 'blue'
              and loaded['w:user-a'].secret == '')
        check('extra attribute (when) dropped on load — constructor fields only',
              not hasattr(loaded['w:dated'], 'when'))
        again = json_seeds.apply('fakepkg', dst, payloads=[payload], tag='selftest')
        rep = again['reports'][0]
        check('second apply: rows are is_prior=False so the upsert leaves them alone',
              not rep['inserted'] and not rep['updated'] and len(rep['skipped_custom']) == 3, str(rep))

        # a customized row is never clobbered even when the file changes
        loaded['w:user-b'].colour = 'hand-picked'
        payload['rows'] = [dict(r, colour='overwritten') for r in payload['rows']]
        third = json_seeds.apply('fakepkg', dst, payloads=[payload], tag='selftest')
        check('customized row keeps its value after a changed re-apply',
              loaded['w:user-b'].colour == 'hand-picked', str(third['reports']))

        # all-rows export + stale-file removal
        res_all = json_seeds.export_rows(src, 'fakepkg', only_non_prior=False, out_dir=out)
        check('only_non_prior=False exports the prior row too',
              res_all['classes'] == {'Widget': 4}, str(res_all['classes']))
        for o in list(src.objectTables['Widget'].values()):
            o.is_prior = True
        res_none = json_seeds.export_rows(src, 'fakepkg', out_dir=out)
        check('no user rows left: file removed and reported',
              res_none['classes'] == {'Widget': 0} and res_none['removed']
              and not os.path.exists(os.path.join(out, 'Widget.json')), str(res_none))
        with open(os.path.join(out, 'Widget.json'), 'w') as f:
            json.dump({'schema': json_seeds.SCHEMA, 'class': 'Widget',
                       'source': 'hand-curated', 'count': 0, 'rows': []}, f)
        json_seeds.export_rows(src, 'fakepkg', out_dir=out)
        check('a file the exporter did not write is never removed',
              os.path.exists(os.path.join(out, 'Widget.json')))

        # honest refusals
        try:
            json_seeds.export_rows(src, 'moduleService', out_dir=out)
            refused = False
        except ValueError as exc:
            refused = 'no class list' in str(exc)
        check('a package with no hook and no class list refuses, naming why', refused)
        res_missing = json_seeds.export_rows(src, 'fakepkg', class_names=['Ghost'], out_dir=out)
        check('a class with no live table is skipped loudly, not raised',
              res_missing['skipped'] == [('Ghost', 'no live table (class not booted?)')],
              str(res_missing['skipped']))
        sys.path.remove(tmp)

    failed = [l for l, ok in _results if not ok]
    print(f'\n{len(_results) - len(failed)}/{len(_results)} checks passed')
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
