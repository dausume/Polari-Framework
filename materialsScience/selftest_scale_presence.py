"""
Selftest — scale-presence accountability (msci-24): the materials x
levels matrix + per-level pages behind /display/materials and
/display/materials-level-{0..4}.

Run from polari-framework/:
    python3 -m materialsScience.selftest_scale_presence

Covers: matrix shape (5 levels from SCALE_LEVEL_DETAILS, per-level
counts sum to the identity count, every material carries all 5 level
keys); absence-as-data semantics (planned rows count missing but their
rows still travel so pages can show what was declared); every missing
entry on a level page carries the evidence-bearing suggestion (knob +
action, never auto-applied); unknown level -> honest error naming the
valid range.
"""

from types import SimpleNamespace

from materialsScience.materials_basis import SCALE_LEVEL_DETAILS
from materialsScience.scale_presence import (
    level_accountability, presence_matrix,
)
from materialsScience.standard_materials_seed import (
    SEED_STANDARD_MATERIALS, SEED_STANDARD_SCALE_DEFINITIONS,
)

PASS, FAIL = '\033[0;32mPASS\033[0m', '\033[0;31mFAIL\033[0m'
_results = []


def check(label, cond, extra=''):
    _results.append(bool(cond))
    print(f'  [{PASS if cond else FAIL}] {label}'
          f'{("  " + extra) if extra else ""}')


def _mgr():
    return SimpleNamespace(objectTables={
        'MaterialsScienceMaterial': {
            i: SimpleNamespace(**m)
            for i, m in enumerate(SEED_STANDARD_MATERIALS)},
        'MaterialScaleDefinition': {
            i: SimpleNamespace(**r)
            for i, r in enumerate(SEED_STANDARD_SCALE_DEFINITIONS)},
    })


if __name__ == '__main__':
    print('\nScale-presence accountability (msci-24)\n')
    mgr = _mgr()
    matrix = presence_matrix(mgr)
    n = len(SEED_STANDARD_MATERIALS)

    check('matrix has one entry per SCALE_LEVEL_DETAILS level',
          [l['level'] for l in matrix['levels']]
          == sorted(SCALE_LEVEL_DETAILS))
    check('level entries carry the taxonomy (range, methods, earnedBy)',
          all(l['lengthRange'] and l['methods'] and l['earnedBy']
              for l in matrix['levels']))
    check('per-level counts sum to the identity count at EVERY level '
          '(nothing dropped, nothing double-counted)',
          all(l['defined'] + l['partial'] + l['missing'] == n
              for l in matrix['levels']),
          f'n={n}')
    check('every material carries all 5 level keys (absence is data, '
          'not a hole in the dict)',
          all(set(m['presence']) == {'0', '1', '2', '3', '4'}
              for m in matrix['materials']))
    check('no mesoscale/atomistic engine wired -> L2 and L3 are '
          'honestly all-missing',
          all(l['missing'] == n for l in matrix['levels']
              if l['level'] in (2, 3)))

    l4 = level_accountability(mgr, 4)
    check('L4 page: the quantum-fragment family is present (partial '
          'until executed)',
          {'carbon-nanotube', 'n-doped-carbon-nanotube',
           'b-doped-carbon-nanotube', 'silicon'}
          <= {e['material'] for e in l4['partial']})
    planned_with_rows = [e for e in l4['missing'] if e['rows']]
    check("planned rows count MISSING but travel with the entry "
          "(declared intent is not a definition — but it's shown)",
          planned_with_rows
          and all(r['status'] == 'planned'
                  for e in planned_with_rows for r in e['rows']))
    check('every missing entry carries the evidence-bearing suggestion '
          '(knob + action)',
          all(e.get('suggestion')
              and e['suggestion']['knob'] == 'MaterialScaleDefinition'
              and e['suggestion']['action']
              and e['suggestion']['evidence']
              for e in l4['missing']))
    check('suggestion action names the exact row to create',
          any('@L4' in e['suggestion']['action'] for e in l4['missing']))

    bad = level_accountability(mgr, 7)
    check('unknown level -> honest error naming the valid range',
          not bad['ok'] and '[0, 1, 2, 3, 4]' in bad['error'])

    total, passed = len(_results), sum(_results)
    print(f'\n{passed}/{total} checks passed')
    raise SystemExit(0 if passed == total else 1)
