"""
Selftest for the fg-4 Si sequential-truncation fix (cnt_sequential):
the DFF and latch own-loop characterization on a SILICON card at 0.6
and 1.0 V — the runs that used to die with 'timestep too small …
trouble with node xdut.m1' (aF CNT-sized standin caps vs ~350×
larger Si currents). The fix is a single retry with the DUT standin
caps scaled to the device's own input cap, recorded as
`numericalAid`; the CNT cards never retry and stay bit-identical.

Runs the REAL openvaf + ngspice (honest skip when absent — same
convention as the other SPICE suites). ~3–4 min.

Run from polari-framework/modules/:
  PYTHONPATH=..:../polariApiServer python3 -m sifet.selftest_si_sequential
"""

import sys

from cntfet import cnt_derive as cd
from cntfet import cnt_sequential as seq
from cntfet import selftest_cntfet as st
from cntfet.cnt_osdi import find_ngspice, find_openvaf
from cntfet.selftest_summary import _mgr, _seed_si
from sifet.si_device import derive_si_device
from sifet.si_device import get_row as si_get

_results = []


def check(label, cond, extra=''):
    _results.append((label, bool(cond)))
    print(f'{"PASS" if cond else "FAIL"}: {label}'
          + (f' — {extra}' if extra and not cond else ''))


def _arc_ok(res):
    return all(res[kind][edge].get('ok')
               and res[kind][edge].get('value_s') is not None
               for kind in ('setup', 'hold')
               for edge in ('rise', 'fall'))


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
    si = si_get(mgr, 'SiliconMOSFET', 'si-nmos-planar-90')
    cnt = cd.get_row(mgr, 'AlignedCNTFETDevice', 'cnt-aligned-s1')
    check('derive: planar-90 + S1',
          derive_si_device(mgr, si)['ok']
          and cd.derive_device(
              mgr, cnt, parameter_factory=st._row_factory(
                  mgr, 'CNTFETParameterRow'))['ok'])

    dff_06 = seq.characterize_sequential(mgr, si, vdd=0.6,
                                         result_factory=rf)
    dff_10 = seq.characterize_sequential(mgr, si, vdd=1.0,
                                         result_factory=rf)
    check('Si DFF characterizes at BOTH 0.6 and 1.0 V (the exact '
          'runs that used to TRUNCATE), all four setup/hold arcs '
          'resolved, Liberty written',
          dff_06.get('ok') and dff_10.get('ok')
          and _arc_ok(dff_06) and _arc_ok(dff_10)
          and dff_06['clkToQ']['rise'] and dff_10['clkToQ']['fall']
          and dff_06['libertyBytes'] > 0,
          f"0.6={dff_06.get('error')} 1.0={dff_10.get('error')}")
    check('the retry is RECORDED: numericalAid names the standin-cap '
          'scaling on both Si DFF reports',
          'standin caps scaled' in dff_06.get('numericalAid', '')
          and 'standin caps scaled' in dff_10.get('numericalAid', ''))
    check('physics sanity: setup at 1.0 V is faster than at 0.6 V '
          '(stronger drive, same topology)',
          dff_10['setup']['rise']['value_s']
          < dff_06['setup']['rise']['value_s'],
          f"1.0V={dff_10['setup']['rise']['value_s']:.3e} "
          f"0.6V={dff_06['setup']['rise']['value_s']:.3e}")

    latch = seq.characterize_latch(mgr, si, vdd=1.0,
                                   result_factory=rf)
    check('Si latch characterizes at 1.0 V with the aid recorded '
          'and the transparent D->Q arcs present',
          latch.get('ok') and _arc_ok(latch)
          and latch['dToQ']['rise'] and latch['dToQ']['fall']
          and 'standin caps scaled' in latch.get('numericalAid', ''),
          str(latch.get('error')))

    ctl = seq.characterize_sequential(mgr, cnt, vdd=0.6,
                                      result_factory=rf)
    check('CNT control: S1 DFF still characterizes with NO retry '
          'and NO aid — the CNT numbers are bit-identical',
          ctl.get('ok') and ctl.get('numericalAid') == '',
          f"aid={ctl.get('numericalAid')!r} err={ctl.get('error')}")
    check('result rows landed (one per characterization)',
          len(mgr.objectTables['CellCharacterizationRun']) >= 4)

    passed = sum(1 for _, ok in _results if ok)
    print(f'\n{passed}/{len(_results)} checks passed')
    return 0 if passed == len(_results) else 1


if __name__ == '__main__':
    sys.exit(main())
