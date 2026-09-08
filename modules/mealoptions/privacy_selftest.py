"""
@module mealoptions.privacy_selftest

mo-3 privacy selftest — proves no person / household / place / day
field can leave the instance through the export path (the reverse
of seed): a fake manager holds mealoptions rows — a user-authored
MealTemplate (kept), a prior one (excluded, D5), a template that
picked up household_name='x' (DROPPED and reported), a user
BulkStaple observed at a named place on a day (pointers blanked +
stripped), a user Recipe, and a PriceReference row (kept regardless
of is_prior — a computed reference). export_rows writes to a temp
dir; the files are then read as TEXT.

Asserts: no stripped field name appears as a key anywhere in any
written file; month strings match ^\\d{4}-\\d{2}$; no is_prior=True
MealTemplate exported; counts and the dropped report are exact; and
STATICALLY no class in MEALOPTIONS_CLASSES declares a stripped field
except BulkStaple's declared instance-pointer trio (nor does
PriceReference, when mo-2 has landed).

Run from polari-framework/modules/:
  PYTHONPATH=..:../polariApiServer python3 -m mealoptions.privacy_selftest
"""

import inspect
import json
import os
import re
import sys
import tempfile
from types import SimpleNamespace

from mealoptions import MEALOPTIONS_CLASSES
from mealoptions.custom import export_hook
from mealoptions.meal_basis import MealTemplate
from mealoptions.recipe_basis import Recipe
from mealoptions.staple_basis import INSTANCE_POINTER_FIELDS, BulkStaple
from moduleService import json_seeds

PASS, FAIL = '\033[0;32mPASS\033[0m', '\033[0;31mFAIL\033[0m'
failures = []
MONTH_RE = re.compile(r'^\d{4}-\d{2}$')


def check(label, cond, extra=''):
    print(f'  [{PASS if cond else FAIL}] {label}'
          + (f'  ({extra})' if extra and not cond else ''))
    if not cond:
        failures.append(label)


def _fields(cls):
    return [p for p in inspect.signature(cls.__init__).parameters
            if p not in ('self', 'manager')]


def _price_reference_class():
    try:
        from mealoptions.price_reference_basis import PriceReference
        return PriceReference
    except Exception:  # noqa: BLE001 — mo-2 not landed yet
        return None


def _fake_price_reference():
    """A PriceReference-shaped row: the real class when mo-2 has
    landed, else a plain object with the plan's columns."""
    cls = _price_reference_class()
    kwargs = dict(name='pr:rice-white:2026-08:chain:kroger:dmv',
                  food_name='rice-white', month='2026-08',
                  source_kind='chain', chain_name='kroger',
                  region_label='dmv', median_price_per_kg=2.1,
                  min_price_per_kg=1.9, max_price_per_kg=2.4,
                  sample_count=3, is_prior=True)
    if cls is not None:
        allowed = set(_fields(cls))
        try:
            return cls(**{k: v for k, v in kwargs.items() if k in allowed})
        except Exception:  # noqa: BLE001
            pass
    return SimpleNamespace(**kwargs)


def build_manager():
    user_tpl = MealTemplate(name='tpl:user-lentil-bowl', is_prior=False)
    prior_tpl = MealTemplate(name='tpl:seeded-oats', is_prior=True)
    leaky_tpl = MealTemplate(name='tpl:leaky', is_prior=False)
    leaky_tpl.household_name = 'x'          # a value stuck on a row
    staple = BulkStaple(name='staple:user-rice', food_name='rice-white',
                        household_name='demo-household',
                        bulk_location_name='costco-sterling',
                        observed_date='2026-09-01', bulk_price=18.5,
                        bulk_package_quantity=25, is_prior=False)
    recipe = Recipe(name='recipe:user-dal', is_prior=False)
    price = _fake_price_reference()
    tables = {
        'MealTemplate': {1: user_tpl, 2: prior_tpl, 3: leaky_tpl},
        'BulkStaple': {4: staple},
        'Recipe': {5: recipe},
        'PriceReference': {6: price},
    }
    return SimpleNamespace(objectTables=tables, objectTypingDict={})


def main():
    print('mo-3 privacy line: the export path')
    stripped = export_hook.strip_fields()
    check('strip_fields() covers the local private tuple',
          set(export_hook.LOCAL_PRIVATE_FIELDS) <= set(stripped), str(stripped))
    price_cls = _price_reference_class()
    if price_cls is not None:
        from mealoptions.price_reference_basis import PRIVACY_STRIPPED_FIELDS
        check('strip_fields() includes PriceReference.PRIVACY_STRIPPED_FIELDS (mo-2 landed)',
              set(PRIVACY_STRIPPED_FIELDS) <= set(stripped))
        check('PriceReference declares no stripped field',
              not [f for f in _fields(price_cls) if f in stripped],
              str([f for f in _fields(price_cls) if f in stripped]))
        check('include_classes() names PriceReference; exported regardless of is_prior',
              'PriceReference' in export_hook.include_classes()
              and 'PriceReference' in export_hook.include_prior_classes())
    else:
        print('  [skip] PriceReference not importable yet (mo-2) — hook falls back to the local tuple')
        check('include_prior_classes() empty before mo-2', export_hook.include_prior_classes() == ())

    # the static line: no class declares a stripped field but BulkStaple's trio
    for cls in MEALOPTIONS_CLASSES:
        compat = set(INSTANCE_POINTER_FIELDS) if cls is BulkStaple else set()
        leaked = [f for f in _fields(cls) if f in stripped and f not in compat]
        check(f'{cls.__name__}: declares no stripped field'
              + (' (beyond the declared trio)' if compat else ''), not leaked, str(leaked))

    # filter_row directly (belt and braces)
    check('filter_row drops a row carrying a private value',
          export_hook.filter_row('MealTemplate', {'name': 't', 'person_name': 'alex'}) is None)
    blanked = export_hook.filter_row('BulkStaple', {
        'name': 's', 'bulk_location_name': 'costco', 'observed_date': '2026-09-01',
        'household_name': 'demo', 'bulk_price': 1.0})
    check('filter_row blanks BulkStaple\'s trio and keeps the row',
          blanked is not None and all(blanked.get(f) == '' for f in INSTANCE_POINTER_FIELDS)
          and blanked['bulk_price'] == 1.0, str(blanked))
    check('filter_row keeps a clean row unchanged',
          export_hook.filter_row('Recipe', {'name': 'r', 'is_prior': False}) == {'name': 'r', 'is_prior': False})

    # the export itself, into a temp dir
    manager = build_manager()
    with tempfile.TemporaryDirectory() as tmp:
        res = json_seeds.export_rows(manager, 'mealoptions', out_dir=tmp,
                                     source='selftest fake manager')
        classes = res['classes']
        check('MealTemplate: 1 exported (user kept; prior excluded; leaky dropped)',
              classes.get('MealTemplate') == 1, str(classes))
        check('BulkStaple: 1 exported', classes.get('BulkStaple') == 1, str(classes))
        check('Recipe: 1 exported', classes.get('Recipe') == 1, str(classes))
        expect_price = 1 if price_cls is not None else 0
        check(f'PriceReference: {expect_price} exported '
              + ('(is_prior True kept — computed reference)' if expect_price else
                 '(not in include_classes before mo-2)'),
              classes.get('PriceReference', 0) == expect_price, str(classes))
        check('dropped report names the leaky template',
              res['dropped'].get('MealTemplate') == ['tpl:leaky'], str(res['dropped']))
        check('stripped_fields reported', set(res['stripped_fields']) == set(stripped))
        with_tables = {'MealTemplate', 'BulkStaple', 'Recipe', 'PriceReference'}
        check('every class without a live table is skipped loudly, none of the four',
              set(classes) == with_tables
              and {n for n, _why in res['skipped']} == set(export_hook.include_classes()) - with_tables,
              str(res['skipped']))
        files = sorted(os.listdir(tmp))
        expected_files = {'MealTemplate.json', 'BulkStaple.json', 'Recipe.json'}
        if expect_price:
            expected_files.add('PriceReference.json')
        check('files written only for classes with rows', set(files) == expected_files, str(files))
        check('files written to the temp dir, not modules/mealoptions/initialData',
              not [f for f in os.listdir(json_seeds.data_dir('mealoptions')) if f.endswith('.json')])

        for fname in files:
            path = os.path.join(tmp, fname)
            with open(path, encoding='utf-8') as f:
                text = f.read()
            present = [f for f in stripped if f'"{f}"' in text]
            check(f'{fname}: no stripped field name appears anywhere in the file',
                  not present, str(present))
            payload = json.loads(text)
            check(f'{fname}: module-initial-data/1 header + count matches rows',
                  payload['schema'] == json_seeds.SCHEMA
                  and payload['class'] == fname[:-5]
                  and payload['count'] == len(payload['rows']))
            if fname == 'MealTemplate.json':
                check('no is_prior=True MealTemplate exported',
                      all(r.get('is_prior') is False for r in payload['rows']),
                      str([(r['name'], r.get('is_prior')) for r in payload['rows']]))
                check('the user-authored template is the one exported',
                      [r['name'] for r in payload['rows']] == ['tpl:user-lentil-bowl'])
            if fname == 'BulkStaple.json':
                row = payload['rows'][0]
                check('BulkStaple row keeps its offer + food, loses place / day / household',
                      row['food_name'] == 'rice-white' and row['bulk_price'] == 18.5
                      and not any(f in row for f in INSTANCE_POINTER_FIELDS), str(row))
            if fname == 'PriceReference.json':
                months = [r.get('month', '') for r in payload['rows']]
                check('PriceReference month strings match ^\\d{4}-\\d{2}$ (no day, D1)',
                      months and all(MONTH_RE.match(m) for m in months), str(months))
            meta = [k for r in payload['rows'] for k in r if k in json_seeds.META_KEYS]
            check(f'{fname}: no tree bookkeeping keys', not meta, str(meta))

        # the round trip stays privacy-clean: what apply would load
        payloads = [json_seeds.read_file(os.path.join(tmp, f)) for f in files]
        pairs, skipped = json_seeds.seed_pairs('mealoptions', manager, payloads)
        loaded = {n: rows for n, _c, rows in pairs}
        check('seed_pairs resolves every exported class from the package',
              set(loaded) == {f[:-5] for f in files if f != 'PriceReference.json'} | (
                  {'PriceReference'} if price_cls is not None else set()), str(skipped))
        check('to_seed keeps only constructor fields — nothing private survives the load side',
              not [k for rows in loaded.values() for r in rows for k in r if k in stripped])

    print(f'\n{len(failures)} failure(s)' if failures else '\nall mealoptions privacy checks passed')
    return 1 if failures else 0


if __name__ == '__main__':
    sys.exit(main())
