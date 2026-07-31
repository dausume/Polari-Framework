"""
@module composition.selftest_composition

Composition selftests (PART_ARCHETYPES_PLAN arch-1..). Standalone,
fake-manager style: python3 -m composition.selftest_composition
(from polari-framework/ with PYTHONPATH=modules).
"""

import types

from composition.seed_upsert import (
    diff_fields, upsert_seed_rows, upsert_seed_pairs,
)

PASS = '\033[92mPASS\033[0m'
FAIL = '\033[91mFAIL\033[0m'
_results = []


def check(label, cond, extra=''):
    _results.append(bool(cond))
    print(f'{PASS if cond else FAIL}: {label}'
          + (f'  [{extra}]' if extra and not cond else ''))


# ---------------------------------------------------------------
# arch-1: the seed upsert path
# ---------------------------------------------------------------

class _FakeRow:
    """Stands in for a treeObject: registers itself on the manager
    table at construction, like treeObjectInit does."""

    def __init__(self, manager=None, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)
        table = manager.objectTables.setdefault('FakeRow', {})
        table[id(self)] = self


def _mgr(rows=()):
    m = types.SimpleNamespace()
    m.objectTables = {'FakeRow': {id(r): r for r in rows}}
    m.objectTypingDict = {'FakeRow': object()}
    saved = []
    m.db = types.SimpleNamespace(saveInstanceInDB=saved.append)
    m.saved = saved
    return m


def _row(**kwargs):
    return types.SimpleNamespace(**kwargs)


def selftest_upsert():
    print('\n-- arch-1: seed upsert path --')

    # 1. Missing row is inserted.
    m = _mgr()
    rep = upsert_seed_rows(
        m, 'FakeRow', _FakeRow,
        [{'name': 'a', 'value': 1, 'is_prior': True}])
    check('missing row inserted', rep['inserted'] == ['a']
          and len(m.objectTables['FakeRow']) == 1)

    # 2. Changed field on a prior row converges; untouched fields
    #    survive; the row is persisted.
    row = _row(name='b', value=1, keep='original', is_prior=True)
    m = _mgr([row])
    rep = upsert_seed_rows(m, 'FakeRow', _FakeRow,
                           [{'name': 'b', 'value': 2}])
    check('changed field converges',
          row.value == 2 and rep['updated'] ==
          [{'name': 'b', 'fields': ['value']}])
    check('unmentioned field survives', row.keep == 'original')
    check('updated row persisted to db', m.saved == [row])

    # 3. THE gotcha case: a field added to the seed after the row
    #    exists reaches the live row (ten strikes ended here).
    row = _row(name='c', value=1, is_prior=True)
    m = _mgr([row])
    upsert_seed_rows(m, 'FakeRow', _FakeRow,
                     [{'name': 'c', 'value': 1, 'new_field': 'now'}])
    check('NEW seed field lands on existing row',
          getattr(row, 'new_field', None) == 'now')

    # 4. Customized rows (is_prior=False) are never touched.
    row = _row(name='d', value='measured', is_prior=False)
    m = _mgr([row])
    rep = upsert_seed_rows(m, 'FakeRow', _FakeRow,
                           [{'name': 'd', 'value': 'prior'}])
    check('is_prior=False row untouched',
          row.value == 'measured'
          and rep['skipped_custom'] == ['d'] and not m.saved)

    # 5. Identical row reports unchanged, no db write.
    row = _row(name='e', value=3, is_prior=True)
    m = _mgr([row])
    rep = upsert_seed_rows(m, 'FakeRow', _FakeRow,
                           [{'name': 'e', 'value': 3}])
    check('identical row unchanged, not rewritten',
          rep['unchanged'] == ['e'] and not m.saved)

    # 6. A failing row lands in errors; the rest still converge.
    class _Boom:
        def __init__(self, manager=None, **kwargs):
            raise RuntimeError('constructor refused')
    m = _mgr()
    rep = upsert_seed_rows(m, 'FakeRow', _Boom,
                           [{'name': 'f1'}, {'name': 'f2'}])
    check('per-row failure isolated',
          len(rep['errors']) == 2
          and rep['errors'][0]['op'] == 'insert')

    # 7. Gated-off class skipped loudly by the pairs runner.
    m = _mgr()
    reps = upsert_seed_pairs(
        m, [('NotBooted', _FakeRow, [{'name': 'x'}]),
            ('FakeRow', _FakeRow, [{'name': 'y'}])])
    check('gated-off class skipped, booted class seeded',
          reps[0].get('skipped') is True
          and reps[1]['inserted'] == ['y'])

    # 8. diff_fields treats a missing attribute as a difference.
    check('diff_fields flags missing attribute',
          diff_fields(_row(name='z'), {'name': 'z', 'added': 1})
          == ['added'])


def main():
    selftest_upsert()
    total, passed = len(_results), sum(_results)
    print(f'\n{passed}/{total} checks passed')
    return 0 if passed == total else 1


if __name__ == '__main__':
    raise SystemExit(main())
