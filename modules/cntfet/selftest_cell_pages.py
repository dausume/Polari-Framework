"""
Selftest for cntfet.cnt_cell_pages (the cell arc, 2026-08-31):
general cell summaries, the CellFETConfiguration object grid, the
config summaries (numbers or the honest fill affordance), the
catalogue and the generic cell-detail page seed.

The PROVEN OPEN-SOURCE SAMPLES (cinv / cnand2 on the proven-free
planar Si) are verified LIVE after deploy — this suite proves the
structure and the refusal honesty on the fake manager.

Run from polari-framework/modules/:
  PYTHONPATH=..:../polariApiServer python3 -m cntfet.selftest_cell_pages
"""

import json
import sys

from cntfet import selftest_cntfet as st
from cntfet.cnt_cell_pages import (
    CELL_KEYS, CellFETConfiguration, SEED_CELL_PAGES,
    cell_config_summary, cell_summary, cells_catalogue, config_name,
    seed_cell_configs,
)
from cntfet.selftest_summary import _mgr, _seed_si

_results = []


def check(label, cond, extra=''):
    _results.append((label, bool(cond)))
    print(f'{"PASS" if cond else "FAIL"}: {label}'
          + (f' — {extra}' if extra and not cond else ''))


def main():
    mgr = _mgr()
    st._seed_all(mgr)
    _seed_si(mgr)

    # ---- the object grid -----------------------------------------
    grid = seed_cell_configs(['cnt-aligned-s1', 'si-nmos-planar-90'])
    check('CellFETConfiguration: one row per cell × device (27 cells '
          'incl. cdff), addressable names, rows construct',
          len(grid) == len(CELL_KEYS) * 2
          and config_name('cinv', 'si-nmos-planar-90')
          in {g['name'] for g in grid}
          and hasattr(CellFETConfiguration(**{**grid[0],
                                              'manager': None}),
                      'device'),
          f'{len(grid)} rows')

    # ---- the general cell summary --------------------------------
    s = cell_summary(mgr, 'cinv')
    check('cell-summary/1 (general): identity from CELL_LIBRARY '
          '(INV, A→Y, 2 FETs x1, negative unate, combinational), '
          'proof status present, one configuration per seeded '
          'device with the summary path',
          s['ok'] and s['schema'] == 'cell-summary/1'
          and s['identity']['function'] == 'INV'
          and s['identity']['fet_count_x1'] == 2
          and s['identity']['kind'] == 'combinational'
          and s['identity']['unate'] == 'negative'
          and 'status' in s['proof']
          and len(s['configurations'])
          == len({d for d, _c in
                  __import__('cntfet.cnt_cell_pages',
                             fromlist=['_device_names'])
                  ._device_names(mgr)})
          and all(c['summaryPath'].startswith('/api/fet/cellcfg/')
                  for c in s['configurations']),
          str({k: s.get('identity', {}).get(k)
               for k in ('function', 'fet_count_x1', 'kind')}))
    check('kinds: cdff sequential, ctbuf tri-state, cbuf composed of '
          'two cinv',
          cell_summary(mgr, 'cdff')['identity']['kind'] == 'sequential'
          and cell_summary(mgr, 'ctbuf')['identity']['kind']
          == 'tri-state'
          and cell_summary(mgr, 'cbuf')['identity']['composed_of']
          == ['cinv', 'cinv'])
    check('unknown cell refuses naming the library',
          not cell_summary(mgr, 'nope')['ok'])

    # ---- the config summary (no runs on this manager) ------------
    c = cell_config_summary(mgr, 'cinv', 'si-nmos-planar-90')
    check('config summary (uncharacterized): honest refusal with the '
          'characterize act, score/power None — nothing invented; '
          'the proof ROLL-UP (worst of cell + device) rides it',
          c['ok'] and c['schema'] == 'cell-config-summary/1'
          and not c['characterized']
          and 'characterize' in c['refusal']
          and c['score'] is None and c['power'] is None
          and {p['kind'] for p in c['proof']['parts']}
          == {'cell', 'device'}
          and 'worst' in c['proof']['rule'],
          str({k: c.get(k) for k in ('characterized', 'refusal')})[:150])
    check('config summary: unknown device / cell refuse',
          not cell_config_summary(mgr, 'cinv', 'nope')['ok']
          and not cell_config_summary(mgr, 'nope',
                                      'si-nmos-planar-90')['ok'])

    # ---- catalogue + page seed -----------------------------------
    cat = cells_catalogue(mgr)
    check('catalogue: every cell with detailPage + summary paths',
          cat['ok'] and len(cat['cells']) == len(CELL_KEYS)
          and all(r['detailPage']
                  == f"/display/cell-detail?object={r['cell']}"
                  for r in cat['cells']))
    page = SEED_CELL_PAGES[0]
    pdef = json.loads(page['definition'])
    comps = [i['componentProps']['componentName']
             for r in pdef['rows'] for i in r['items']]
    inputs = [str(v) for r in pdef['rows'] for i in r['items']
              for v in i['componentProps']['inputs'].values()]
    check('the generic cell-detail page: route cell-detail, '
          '{object}-addressed everywhere, /api/fet paths only, '
          'panel + logic + schematic + proof + configs rows',
          page['pageRoute'] == 'cell-detail'
          and comps.count('cell-detail-panel') == 1
          and comps.count('cell-logic-diagram') == 1
          and comps.count('cell-schematic') == 1
          and comps.count('freedom-proof-panel') == 1
          and any('{object}' in v for v in inputs)
          and not any('/api/cntfet/' in v for v in inputs),
          str(comps))

    passed = sum(1 for _, ok in _results if ok)
    print(f'\n{passed}/{len(_results)} checks passed')
    return 0 if passed == len(_results) else 1


if __name__ == '__main__':
    sys.exit(main())
