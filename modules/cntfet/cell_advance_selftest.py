"""
Selftest for cntfet.custom.cnt_cell_advance (the first-step service):
ladder report, skip-never-degrade, a REAL coarse characterization
(ngspice, cinv+cnand2 subset for speed) that flips the cell pages
from blank to characterized.

Run from polari-framework/modules/:
  PYTHONPATH=..:../polariApiServer python3 -m cntfet.cell_advance_selftest
"""

import json
import sys

from cntfet import cntfet_selftest as st
from cntfet.custom.cnt_cell_advance import (
    advance_device, advance_report, device_plan,
)
from cntfet.cnt_cell_page import cell_config_summary
from cntfet.custom.cnt_osdi import find_ngspice, find_openvaf
from cntfet.summary_selftest import _mgr, _seed_si
from sifet.custom.si_device import derive_si_device, get_row

_results = []


def check(label, cond, extra=''):
    _results.append((label, bool(cond)))
    print(f'{"PASS" if cond else "FAIL"}: {label}'
          + (f' — {extra}' if extra and not cond else ''))


def main():
    if find_ngspice()[0] is None or find_openvaf()[0] is None:
        print('SKIP: no ngspice/openvaf on this host — the '
              'capability endpoint reports the same refusal')
        return 0
    mgr = _mgr()
    st._seed_all(mgr)
    _seed_si(mgr)
    mgr.objectTables.setdefault('CellCharacterizationRun', {})
    rf = st._row_factory(mgr, 'CellCharacterizationRun')
    si = get_row(mgr, 'SiliconMOSFET', 'si-nmos-planar-90')
    check('derive planar-90', derive_si_device(mgr, si)['ok'])

    rep = advance_report(mgr)
    plan = device_plan(mgr, 'si-nmos-planar-90')
    check('report: every seeded device has a plan; a blank derived '
          'device plans coarse library + sequential + latch; '
          'underived devices plan derive first',
          rep['ok'] and rep['schema'] == 'cells-advance/1'
          and len(rep['devices']) >= 10
          and plan['steps'] == ['characterize-library-coarse',
                                'characterize-sequential',
                                'characterize-latch']
          and 'si-nmos-planar-90' in rep['blankDevices']
          and any('derive' in p.get('steps', [])
                  for p in rep['devices']),
          str(plan))
    check('advance refuses an underived / unknown device by name',
          not advance_device(mgr, 'si-pmos-planar-90')['ok']
          and not advance_device(mgr, 'nope')['ok'])

    # real first step (cinv+cnand2 subset, no sequential — those legs
    # are selftest_si_sequential's; ~seconds not minutes)
    adv = advance_device(mgr, 'si-nmos-planar-90',
                         include_sequential=False,
                         cells=['cinv', 'cnand2'],
                         result_factory=rf)
    runs = [r for r in mgr.objectTables['CellCharacterizationRun']
            .values()
            if str(getattr(r, 'cell', '')).startswith('library:')]
    grid = json.loads(runs[-1].grid_json) if runs else {}
    check('first step runs REAL ngspice at the coarse 2×2 corner '
          'grid, recorded on the run row, at the device\'s own Vdd',
          adv['ok'] and (adv['library'] or {}).get('ok')
          and runs and len(grid.get('slews_s', [])) == 2
          and len(grid.get('loads_f', [])) == 2
          and abs(getattr(runs[-1], 'vdd_v', 0) - 1.0) < 1e-9,
          str({'adv': adv.get('library'), 'grid': grid}))
    cfg = cell_config_summary(mgr, 'cinv', 'si-nmos-planar-90')
    check('the blank screen is gone: the cinv config summary now '
          'serves characterized numbers from the first-step run',
          cfg['characterized'] and (cfg['score'] or {}).get('score')
          and (cfg['power'] or {}).get('states'),
          str({k: bool(cfg.get(k)) for k in
               ('characterized', 'score', 'power')}))
    adv2 = advance_device(mgr, 'si-nmos-planar-90',
                          include_sequential=False,
                          result_factory=rf)
    check('never degrades: a second advance SKIPS the existing '
          'library run (the coarse service refuses to '
          're-characterize)',
          adv2['ok'] and (adv2['library'] or {}).get('skipped')
          and 'never re-characterizes'
          in (adv2['library'] or {}).get('why', ''),
          str(adv2.get('library')))

    passed = sum(1 for _, ok in _results if ok)
    print(f'\n{passed}/{len(_results)} checks passed')
    return 0 if passed == len(_results) else 1


if __name__ == '__main__':
    sys.exit(main())
