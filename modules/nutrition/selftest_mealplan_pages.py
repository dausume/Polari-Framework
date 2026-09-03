"""
meal-planning pages selftest (check() style, no server): the app
pages are CONFIGURED displays, not JSON — every item is an embedded
TableDefinition / GraphDefinition or the structured reading of a
derived verdict (Dustin 2026-09-02: "there should not be any json
showing on the screens … embedded into displays that are put into
the app pages"); every embed names a seeded definition whose
columns exist on the class; the boot-time repoint resolves every
embed to an id.

    cd modules && PYTHONPATH=..:../polariApiServer \\
        python3 -m nutrition.selftest_mealplan_pages
"""

import importlib
import inspect
import json
import re
import sys
from pathlib import Path
from types import SimpleNamespace

from polariApiServer import mealplan_pages_seed as mp

_results = []
#: The only components an app page may use — nothing that dumps JSON.
ALLOWED = {'embeddedTable', 'embeddedGraph', 'embeddedCalendar', 'embeddedMap',
           'api-structured-panel'}
FORBIDDEN = {'api-json-panel'}


def check(label, cond, extra=''):
    _results.append((label, bool(cond)))
    print(f'{"PASS" if cond else "FAIL"}: {label}'
          + (f' — {extra}' if extra else ''))


def _items(page):
    for row in json.loads(page['definition'])['rows']:
        for item in row['items']:
            yield item


def _class_fields(class_name):
    """Constructor parameter names of the treeObject class called
    `class_name`, found by scanning the module packages (the seed
    must not carry columns the class does not have)."""
    root = Path(__file__).resolve().parents[1]
    pattern = re.compile(rf'^class {class_name}\(', re.M)
    # module classes live under modules/<pkg>/; the core definition +
    # event classes (CalendarEvent, EventTrigger, …) under the
    # framework's polariApiServer / polariNoCode packages.
    candidates = list(root.glob('*/*.py')) \
        + list((root.parent / 'polariApiServer').glob('*.py')) \
        + list((root.parent / 'polariNoCode').glob('*.py'))
    for py in candidates:
        if pattern.search(py.read_text(errors='ignore')):
            module = importlib.import_module(f'{py.parent.name}.{py.stem}')
            cls = getattr(module, class_name)
            return set(inspect.signature(cls.__init__).parameters) - {'self'}
    return None


def main():
    pages = mp.SEED_MEALPLAN_PAGE_DISPLAYS
    tables = {t['name']: t for t in mp.SEED_MEALPLAN_TABLES}
    graphs = {g['name']: g for g in mp.SEED_MEALPLAN_GRAPHS}

    routes = [p['pageRoute'] for p in pages]
    check('ten app pages with the nested routes the nav links',
          routes == ['mealplan', 'mealplan/meals', 'mealplan/week', 'mealplan/me',
                     'mealplan/planner', 'mealplan/pantry', 'mealplan/supply',
                     'mealplan/market', 'mealplan/household', 'mealplan/trends'],
          str(routes))

    from nutrition.calendar_seed import SEED_MEALPLAN_SOLUTIONS
    solutions = {s['name'] for s in SEED_MEALPLAN_SOLUTIONS}
    used = {}
    bad_forms = []
    for page in pages:
        for item in _items(page):
            if item.get('type') == 'form':
                used['form'] = used.get('form', 0) + 1
                if item['item'].get('linkedSolutionName') not in solutions:
                    bad_forms.append(item['id'])
                continue
            name = item['componentProps']['componentName']
            used[name] = used.get(name, 0) + 1
    check('no JSON on screens: every page item is an embedded table, an embedded graph, '
          'the structured reading, or a no-code FORM linked to a seeded solution',
          set(used) <= ALLOWED | {'form'} and not (set(used) & FORBIDDEN) and not bad_forms,
          f'{used} bad_forms={bad_forms}')

    ids = [item['id'] for page in pages for item in _items(page)]
    check('item ids are unique across the app (repoint keys on them)',
          len(ids) == len(set(ids)))

    bad_embeds = []
    for page in pages:
        for item in _items(page):
            if item.get('type') == 'form':
                continue
            inputs = item['componentProps']['inputs']
            name = item['componentProps']['componentName']
            if name == 'embeddedTable':
                target = mp.EMBED_TARGETS.get(item['id'])
                table = tables.get(target[1]) if target else None
                if (table is None
                        or table['source_class'] != inputs['className']):
                    bad_embeds.append(item['id'])
            elif name == 'embeddedGraph':
                graph = graphs.get(inputs['graphName'])
                if (graph is None
                        or graph['source_class'] != inputs['className']):
                    bad_embeds.append(item['id'])
    check('every embed names a SEEDED definition whose source_class is '
          'the class it renders', not bad_embeds, str(bad_embeds))

    bad_cols = []
    unresolved = []
    for name, table in tables.items():
        cfg = json.loads(table['definition'])['tableConfiguration']
        cols = cfg['columns']
        if not cols or not all({'name', 'displayName', 'dataType',
                                'order', 'visible'} <= set(c) for c in cols):
            bad_cols.append((name, 'column shape'))
            continue
        fields = _class_fields(table['source_class'])
        if fields is None:
            unresolved.append(table['source_class'])
            continue
        missing = [c['name'] for c in cols if c['name'] not in fields]
        if missing:
            bad_cols.append((name, missing))
    check('every TableDefinition carries ColumnConfiguration columns '
          '(name/displayName/dataType/order/visible) that EXIST on '
          'its class', not bad_cols and not unresolved,
          f'bad={bad_cols} unresolved={unresolved}')

    check('structured panels never leave a key for the JSON expander: '
          'dict-of-dicts / empty-dict keys are hidden or picked',
          all(inputs.get('hideKeys') != '' or inputs.get('pick') != ''
              or inputs['path'].endswith(('/me', '/cost', '/availability',
                                          '/suggestions', '/conditions',
                                          '/budget', '/prices',
                                          '/acidity', '/coverage',
                                          '/waste/' + mp.HOUSEHOLD,
                                          '/day/' + mp.DAY,
                                          '/fairness', '/speed-refinement'))
              or 'quick-add' in inputs['path']
              for page in pages for item in _items(page)
              if item.get('type') != 'form'
              for inputs in [item['componentProps']['inputs']]
              if item['componentProps']['componentName']
              == 'api-structured-panel'))

    # The boot-time repoint: a fake node whose TableDefinition rows
    # have this node's ids → every embed must end up pointing at one.
    saved = []
    rows = {}
    for i, t in enumerate(tables.values()):
        rows[f'td{i}'] = SimpleNamespace(id=f'td{i}', name=t['name'])
    displays = {}
    for i, p in enumerate(pages):
        displays[f'dd{i}'] = SimpleNamespace(
            id=f'dd{i}', name=p['name'], definition=p['definition'])
    manager = SimpleNamespace(
        objectTables={'TableDefinition': rows, 'DisplayDefinition': displays},
        db=SimpleNamespace(saveInstanceInDB=lambda row: saved.append(row.name)))
    repointed = mp._repoint_display_refs(manager)
    blank = [item['id'] for d in displays.values()
             for row in json.loads(d.definition)['rows']
             for item in row['items']
             if (item.get('componentProps') or {}).get('componentName') == 'embeddedTable'
             and not item['componentProps']['inputs']['tableConfigId']]
    check('repoint resolves EVERY embeddedTable to this node\'s '
          'TableDefinition id and persists each changed page',
          repointed == used.get('embeddedTable', 0) and not blank
          and sorted(saved) == sorted(p['name'] for p in pages),
          f'repointed={repointed} blank={blank} saved={len(saved)}')

    passed = sum(1 for _, ok in _results if ok)
    print(f'\n{passed}/{len(_results)} checks passed')
    return 0 if passed == len(_results) else 1


if __name__ == '__main__':
    sys.exit(main())
