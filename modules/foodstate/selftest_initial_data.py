"""
Selftest for foodstate's automated initialData export — the DRIFT
GUARD: the committed JSON files must equal what the seed builders
generate right now (two sources of truth is how curated data rots),
the payloads must satisfy the module-initial-data/1 convention the
json_seeds loader enforces, and rows must carry the constructor
kwargs the classes accept.

Run from polari-framework/modules/:
  PYTHONPATH=..:../polariApiServer python3 -m foodstate.selftest_initial_data
"""

import inspect
import json
import os

from foodstate.export_initial_data import (DATA_DIR, build_payloads,
                                           render)

_results = []


def check(label, cond, extra=''):
    _results.append((label, bool(cond)))
    print(f'{"PASS" if cond else "FAIL"}: {label}'
          + (f' — {extra}' if extra and not cond else ''))


payloads = build_payloads()

check('two payloads generated (FoodMaterial + curated claims)',
      set(payloads) == {'FoodMaterial.json', 'PropertyClaim.json'})
check('49 identity rows', payloads['FoodMaterial.json']['count'] == 49)
check('curated claims = pH + organic-acid rows ONLY (no '
      'FDC-derived composition claims duplicated)',
      all(r['property_meaning_name'] == 'pH'
          or r['property_meaning_name'].startswith('organic-acid-')
          for r in payloads['PropertyClaim.json']['rows']))

for filename, payload in sorted(payloads.items()):
    check(f'{filename}: convention header (schema/class/source/'
          f'count/rows)',
          payload.get('schema') == 'module-initial-data/1'
          and payload.get('class') and 'rows' in payload
          and payload['count'] == len(payload['rows'])
          and 'source' in payload)
    check(f'{filename}: every row carries a name (upsert key)',
          all(r.get('name') for r in payload['rows']))
    path = os.path.join(DATA_DIR, filename)
    if not os.path.exists(path):
        check(f'{filename}: committed file exists', False,
              'run python3 -m foodstate.export_initial_data')
        continue
    with open(path, encoding='utf-8') as f:
        on_disk = f.read()
    check(f'{filename}: committed file MATCHES the builders '
          f'(drift guard)',
          on_disk == render(payload),
          'regenerate: python3 -m foodstate.export_initial_data')

# constructor-kwarg agreement (the json_seeds loader passes rows as
# constructor kwargs — a renamed field would seed nothing, silently)
from foodstate.food_materials import FoodMaterial
from pspp.claims import PropertyClaim
for cls, filename in ((FoodMaterial, 'FoodMaterial.json'),
                      (PropertyClaim, 'PropertyClaim.json')):
    params = set(inspect.signature(cls.__init__).parameters)
    rows = payloads[filename]['rows']
    stray = {k for r in rows for k in r} - params
    check(f'{filename}: every row key is a {cls.__name__} '
          f'constructor kwarg', not stray, str(stray))

# the json_seeds reader accepts the files verbatim
from moduleService import json_seeds
listed = json_seeds.list_files('foodstate')
check('json_seeds lists the foodstate files',
      len(listed) == 2)
for path in listed:
    payload = json_seeds.read_file(path)
    check(f'{os.path.basename(path)}: json_seeds reads it '
          f'(non-legacy, class set)',
          not payload.get('legacy') and payload.get('class'))

passed = sum(1 for _, ok in _results if ok)
print(f'\n{passed}/{len(_results)} checks passed')
if passed != len(_results):
    raise SystemExit(1)
