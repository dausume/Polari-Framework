"""
Selftest for sifet.si_fields (fg-4, last item: the silicon field
basis — the same eq.(5) analytic barrier with silicon's own cited
scale length, charge-sheet density, row-verbatim doping; an F1
SKETCH and it says so).

Run from polari-framework/modules/:
  PYTHONPATH=..:../polariApiServer python3 -m sifet.selftest_si_fields
"""

import sys

from cntfet import cnt_derive as cd
from cntfet import selftest_cntfet as st
from cntfet.cnt_fields import field_profile
from cntfet.selftest_summary import _mgr, _seed_si
from sifet.si_device import derive_si_device, get_row

_results = []


def check(label, cond, extra=''):
    _results.append((label, bool(cond)))
    print(f'{"PASS" if cond else "FAIL"}: {label}'
          + (f' — {extra}' if extra and not cond else ''))


def main():
    mgr = _mgr()
    st._seed_all(mgr)
    _seed_si(mgr)
    nmos = get_row(mgr, 'SiliconMOSFET', 'si-nmos-planar-90')
    pmos = get_row(mgr, 'SiliconMOSFET', 'si-pmos-planar-90')
    cnt = cd.get_row(mgr, 'AlignedCNTFETDevice', 'cnt-aligned-s1')
    check('derive: planar pair + S1',
          derive_si_device(mgr, nmos)['ok']
          and derive_si_device(mgr, pmos)['ok']
          and cd.derive_device(
              mgr, cnt, parameter_factory=st._row_factory(
                  mgr, 'CNTFETParameterRow'))['ok'])

    pot = field_profile(mgr, nmos, 'potential')
    check('dispatch: field_profile on a Si row serves the si_fields '
          'sketch (no more refusal) — eV profile at the device\'s '
          'OWN Vdd, labelled F1 SKETCH, regions row-named',
          pot.get('ok') and pot['unit'] == 'eV'
          and abs(pot['vg'] - 1.0) < 1e-9
          and abs(pot['vd'] - 1.0) < 1e-9
          and 'SKETCH' in pot['fidelity']
          and {r['kind'] for r in pot['regions']}
          == {'contact', 'extension', 'channel'},
          str(pot.get('error', ''))[:200])
    check('potential physics: the drain lead sits Vds below the '
          'source lead; barrier keys reported',
          pot['barrier_top_ev'] is not None
          and abs((pot['source_lead_ev'] - pot['drain_lead_ev'])
                  - pot['frame']['vdsi']) < 0.05
          and pot['lambda_nm'] > 0,
          f"leads={pot['source_lead_ev']:.3f}/"
          f"{pot['drain_lead_ev']:.3f} vdsi={pot['frame']['vdsi']:.3f}")
    pot_off = field_profile(mgr, nmos, 'potential', vg=0.2, vd=1.0)
    check('gate action: the barrier FALLS as Vg rises (off-state '
          'barrier above the on-state one)',
          pot_off['barrier_top_ev'] > pot['barrier_top_ev'],
          f"off={pot_off['barrier_top_ev']:.3f} "
          f"on={pot['barrier_top_ev']:.3f}")

    den = field_profile(mgr, nmos, 'electron-density')
    den_off = field_profile(mgr, nmos, 'electron-density',
                            vg=0.2, vd=1.0)
    ch_vals = [v for x, v in zip(den['x_nm'], den['value'])
               if v is not None and any(
                   r['kind'] == 'channel' and r['x0'] < x < r['x1']
                   for r in den['regions'])]
    ch_off = [v for x, v in zip(den_off['x_nm'], den_off['value'])
              if v is not None and any(
                  r['kind'] == 'channel' and r['x0'] < x < r['x1']
                  for r in den_off['regions'])]
    check('density: charge-sheet cm^-2 along the barrier — the '
          'BARRIER-TOP sheet density (channel minimum) rises with '
          'Vg (past-barrier values clamp to the S/D density, the '
          'stated CNT convention), contacts refused (None), S/D '
          'areal density row-backed',
          den.get('ok') and den['unit'] == 'cm^-2'
          and min(ch_vals) > min(ch_off)
          and any(v is None for v in den['value'])
          and den['n_sd_cm2'] > 0,
          f"on={min(ch_vals):.3g} off={min(ch_off):.3g}")

    ndop = field_profile(mgr, nmos, 'n-doping')
    pdop = field_profile(mgr, nmos, 'p-doping')
    check('doping: the ROWS verbatim — S/D n+ on the n-doping '
          'field, channel p on the p-doping field, contacts '
          'refused (metal), row names cited in the formula',
          ndop.get('ok') and pdop.get('ok')
          and max(v for v in ndop['value'] if v is not None) > 0
          and max(v for v in pdop['value'] if v is not None) > 0
          and 'metal' in ' '.join(ndop['refusals'])
          and 'cm⁻³' in ndop['formula'])
    mat = field_profile(mgr, nmos, 'material')
    check('material: region lookup with the silicide/Si materials',
          mat.get('ok') and 'silicon (gated)' in mat['material'])
    check('polarity: the p device answers too (its own frame)',
          field_profile(mgr, pmos, 'potential').get('ok'))
    check('unknown field refuses by name',
          not field_profile(mgr, nmos, 'no-such').get('ok'))

    cpot = field_profile(mgr, cnt, 'potential', vg=0.6, vd=0.6)
    check('CNT unchanged: S1 still serves the CNT basis (Efsd leads, '
          'radial shells present)',
          cpot.get('ok') and cpot['radial']
          and 'Efsd' in cpot['formula'],
          str(cpot.get('error', ''))[:150])

    passed = sum(1 for _, ok in _results if ok)
    print(f'\n{passed}/{len(_results)} checks passed')
    return 0 if passed == len(_results) else 1


if __name__ == '__main__':
    sys.exit(main())
