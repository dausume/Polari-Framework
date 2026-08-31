"""
Selftest for cntfet.cnt_block_pages (rank 3 of the ladder): general
block summaries, the BlockFETConfiguration grid, the composition
linkage down to CellFETConfiguration, the catalogue and the generic
block-detail page seed. Timing/power run LIVE (they need a Liberty);
here readiness + refusal honesty are proven.

Run from polari-framework/modules/:
  PYTHONPATH=..:../polariApiServer python3 -m cntfet.selftest_block_pages
"""

import json
import sys

from cntfet import selftest_cntfet as st
from cntfet.cnt_block_pages import (
    BlockFETConfiguration, SEED_BLOCK_PAGES, block_config_name,
    block_config_summary, block_summary, blocks_catalogue,
    seed_block_configs,
)
from cntfet.cnt_cell_pages import used_in_blocks
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

    grid = seed_block_configs(['cnt-aligned-s1', 'si-nmos-planar-90'])
    check('BlockFETConfiguration: one row per block × device (4 '
          'blocks), rows construct',
          len(grid) == 8
          and block_config_name('alu4', 'si-nmos-planar-90')
          in {g['name'] for g in grid}
          and hasattr(BlockFETConfiguration(**{**grid[0],
                                               'manager': None}),
                      'block'))

    s = block_summary(mgr, 'alu4')
    check('block-summary/1 (general): identity (cells composition, '
          'FET count 358, ports), exhaustive proof stated device-'
          'independent, one configuration per device with '
          'missing-cells honesty',
          s['ok'] and s['schema'] == 'block-summary/1'
          and s['identity']['fet_count'] == 358
          and s['identity']['cells']
          and s['proof']['proven'] is True
          and len(s['configurations']) >= 10
          and all('cellsReady' in c and 'missingCells' in c
                  for c in s['configurations'])
          and 'FET → cell → BLOCK' in s['ladder'],
          str({k: s.get('identity', {}).get(k)
               for k in ('fet_count', 'cell_count')}))
    check('unknown block refuses naming the library',
          not block_summary(mgr, 'nope')['ok'])

    c = block_config_summary(mgr, 'alu4', 'si-nmos-planar-90',
                             with_timing=False)
    check('block-config-summary/1: the COMPOSITION is the level-up '
          'linkage — every cell with its CellFETConfiguration name '
          'and ?device= page link; no runs on this manager → '
          'cellsReady False with the cells-advance act named',
          c['ok'] and c['schema'] == 'block-config-summary/1'
          and c['composition']
          and all(x['cellConfig'].startswith('cellcfg-')
                  and '&device=si-nmos-planar-90' in x['page']
                  for x in c['composition'])
          and not c['cellsReady']
          and 'cells/advance' in c['acts']['fillCells']
          and 'rule' in c['proof'],
          str(c.get('composition', [])[:1]))
    check('block config: unknown device refuses',
          not block_config_summary(mgr, 'alu4', 'nope')['ok'])

    check('upward weave: cinv knows the blocks built from it, with '
          'device-carrying page links',
          any(b['block'] == 'alu4'
              for b in used_in_blocks('cinv'))
          and all('&device=d1' in b['page']
                  for b in used_in_blocks('cinv', 'd1')))

    cat = blocks_catalogue(mgr)
    check('catalogue: 4 blocks with detailPage + summary paths',
          cat['ok'] and len(cat['blocks']) == 4
          and all(r['detailPage']
                  == f"/display/block-detail?object={r['block']}"
                  for r in cat['blocks']))
    page = SEED_BLOCK_PAGES[0]
    pdef = json.loads(page['definition'])
    comps = [i['componentProps']['componentName']
             for r in pdef['rows'] for i in r['items']]
    inputs = [str(v) for r in pdef['rows'] for i in r['items']
              for v in i['componentProps']['inputs'].values()]
    check('the generic block-detail page: route block-detail, '
          '{object}-addressed, /api/fet paths only',
          page['pageRoute'] == 'block-detail'
          and comps.count('block-detail-panel') == 1
          and any('{object}' in v for v in inputs)
          and not any('/api/cntfet/' in v for v in inputs),
          str(comps))

    passed = sum(1 for _, ok in _results if ok)
    print(f'\n{passed}/{len(_results)} checks passed')
    return 0 if passed == len(_results) else 1


if __name__ == '__main__':
    sys.exit(main())
