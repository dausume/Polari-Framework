"""
Selftest for cntfet.cnt_regimes (fv-1: regimes as data + the IV
regime map / exponent / regime-coloured output rows).

Run from polari-framework/modules/:
  PYTHONPATH=..:../polariApiServer python3 -m cntfet.selftest_regimes
"""

import json
import math
import sys

from cntfet import cnt_derive as cd
from cntfet import cnt_regimes as rg
from cntfet import selftest_cntfet as st
from cntfet.cnt_device_viz import device_model

_results = []


def check(label, cond, extra=''):
    _results.append((label, bool(cond)))
    print(f'{"PASS" if cond else "FAIL"}: {label}'
          + (f' — {extra}' if extra and not cond else ''))


def main():
    mgr = st._mgr()
    st._seed_all(mgr)
    device = cd.get_row(mgr, 'AlignedCNTFETDevice', 'cnt-aligned-s1')
    rep = cd.derive_device(
        mgr, device,
        parameter_factory=st._row_factory(mgr, 'CNTFETParameterRow'))
    check('derive S1 for the regime checks', rep['ok'])
    id_fn, p, dev, refusal = device_model(mgr, 'cnt-aligned-s1')
    check('device_model returns (id_fn, p) without refusal',
          refusal is None and p is not None)

    # ---- seeds ----------------------------------------------------
    names = [s['name'] for s in rg.SEED_FET_REGIMES]
    ok = True
    for s in rg.SEED_FET_REGIMES:
        crit = json.loads(s['criteria_json'])
        ok = ok and all({'lhs', 'op', 'rhs', 'why'} <= set(c)
                        and c['why'] for c in crit) and bool(crit)
        ok = ok and bool(s['governing_equation'])
    check('SEED_FET_REGIMES: criteria parse, every criterion has a '
          'why, every row a governing equation',
          ok and len(set(names)) == len(names))
    check('seeds cover the requested regimes',
          {'subthreshold-exponential', 'linear-triode', 'square-law',
           'velocity-saturated', 'transition-exponent',
           'dibl-tilted-saturation'} <= set(names))
    check('FETRegime row constructs with the seed fields',
          all(hasattr(rg.FETRegime(**{**s, 'manager': None}), k)
              for s in rg.SEED_FET_REGIMES[:1]
              for k in ('criteria_json', 'order', 'fidelity')))

    # ---- point classifications on S1 -----------------------------
    pt = rg.regime_at_bias(p, 0.6, 0.6)
    m_s1 = pt['frame']['vov_exponent']
    check(f'S1 (Lg 15 nm) at (0.6, 0.6): regime {pt["regime"]} with '
          f'm = {m_s1:.3f} < 1.7 (velocity-saturated or crossover)',
          pt['regime'] in ('velocity-saturated', 'transition-exponent')
          and m_s1 is not None and m_s1 < 1.7)
    check('every criterion of the winning row carries its numbers',
          all('lhs_value' in c and 'rhs_value' in c
              for e in pt['evaluations'] if e['passed']
              for c in e['criteria']))
    pt2 = rg.regime_at_bias(p, 0.6, 0.05)
    check('S1 at (0.6, 0.05): linear-triode',
          pt2['regime'] == 'linear-triode', pt2['regime'])
    pt3 = rg.regime_at_bias(p, 0.0, 0.6)
    check('S1 at (0.0, 0.6): subthreshold-exponential',
          pt3['regime'] == 'subthreshold-exponential', pt3['regime'])

    # ---- synthetic long channel ----------------------------------
    p_long = {**p, 'lg_m': 1e-6,
              'mu_m2_per_vs': p['mu_m2_per_vs'] * 100.0,
              'rs_ohm': 0.0, 'rd_ohm': 0.0,
              'dibl_v_per_v': 0.0, 'dvt_v': 0.0}
    m_long, why = rg.vov_exponent(p_long, 0.6, 0.6)
    check(f'synthetic 1 um / Rc-free / mu×100 channel: m = '
          f'{m_long:.3f} > S1 m = {m_s1:.3f} (ORDERING only — the VS '
          f'model saturates by velocity so m ≈ 2 is unreachable; '
          f'stated on the square-law row)',
          m_long is not None and m_long > m_s1, why)

    # ---- knobs change verdicts -----------------------------------
    tilted = rg.regime_at_bias(p, 0.6, 0.6,
                               knobs={'gds_over_gm_max': 0.001,
                                      'fsat_flat': 0.5})
    check('knobs change verdicts: gds_over_gm_max 0.001 + fsat_flat '
          '0.5 flips S1 at Vdd to dibl-tilted-saturation',
          tilted['regime'] == 'dibl-tilted-saturation'
          and pt['regime'] != 'dibl-tilted-saturation',
          tilted['regime'])
    narrow = rg.regime_at_bias(p, 0.6, 0.6,
                               knobs={'m_vs_lo': m_s1 + 0.05})
    check('knobs change verdicts: raising m_vs_lo above the S1 m '
          'moves it to contact-limited-sublinear',
          narrow['regime'] == 'contact-limited-sublinear',
          narrow['regime'])
    check('knobs are echoed on the point payload',
          narrow['knobs']['m_vs_lo'] == m_s1 + 0.05
          and 'm_sq_lo' in narrow['knobs'])

    # ---- manager rows win over seeds -----------------------------
    mgr.objectTables['FETRegime'] = {}
    fac = st._row_factory(mgr, 'FETRegime')
    fac(**{**rg.SEED_FET_REGIMES[0], 'name': 'everything',
           'criteria_json': json.dumps([
               {'lhs': 'vds', 'op': '>=', 'rhs': 0, 'why': 'always'}])})
    check('manager FETRegime rows win over seeds',
          rg.regime_at_bias(p, 0.6, 0.6, manager=mgr)['regime']
          == 'everything')
    del mgr.objectTables['FETRegime']

    # ---- the map ------------------------------------------------
    rows = rg.regime_map(p)
    n = int(round(0.6 / 0.03)) + 1
    seen = {(r['x'], r['y']) for r in rows}
    check(f'regime map covers every grid point once ({n}×{n})',
          len(rows) == n * n and len(seen) == n * n
          and all(r['style'] == 'dot' for r in rows))
    check('map has no unclassified point',
          not any(r['series'] == 'unclassified' for r in rows),
          str({r['series'] for r in rows}))
    summary = rg.map_summary(rows)
    check('map summary fractions sum to 1',
          abs(sum(summary['fractions'].values()) - 1.0) < 1e-9)
    print('     S1 regime fractions:',
          {k: round(v, 3) for k, v in summary['fractions'].items()})

    # ---- exponent rows -------------------------------------------
    ex = rg.exponent_rows(p, vd=0.6)
    series = {r['series'] for r in ex}
    check('exponent rows: m line + both bands + Vt guide',
          any(r['style'] == 'line' for r in ex)
          and 'square-law band (m ≈ 2)' in series
          and 'velocity-saturated band (m ≈ 1)' in series
          and any(r['style'] == 'guide' and r['label'] == 'Vt'
                  for r in ex))
    check('exponent line only where m is defined (no NaN)',
          all(math.isfinite(r['y']) for r in ex
              if r['style'] == 'line'))

    # ---- output-regime rows --------------------------------------
    orows = rg.output_regime_rows(p)
    labels = {r['label'] for r in orows}
    check('output-regime rows span the 5 Vg curves, series = regime',
          labels == {f'Vg = {v:g} V' for v in rg.OUTPUT_VG}
          and 'linear-triode' in {r['series'] for r in orows})

    # ---- graph seeds ---------------------------------------------
    ok = True
    for g in rg.SEED_CNT_REGIME_GRAPHS:
        cfg = json.loads(g['definition'])['graphConfig']
        ok = ok and cfg['seriesDimension'] == 'series' \
            and cfg['styleDimension'] == 'style' and g['description']
    check('graph seeds round-trip (regime-map, exponent, '
          'output-regimes)',
          ok and {g['name'] for g in rg.SEED_CNT_REGIME_GRAPHS}
          == {'cnt-device-regime-map', 'cnt-device-exponent',
              'cnt-device-output-regimes'})
    check('CURVE_BUILDERS build rows for every kind',
          all(rg.CURVE_BUILDERS[k](id_fn, p, dev, mgr, None)
              for k in ('regime-map', 'exponent', 'output-regimes')))

    # ---- report --------------------------------------------------
    report = rg.device_regimes_report(p, dev, vgs=0.6, vds=0.6,
                                      manager=mgr)
    check('refusal-free report on S1 with verdict + exponent_at_vdd',
          report['ok'] and report['exponent_at_vdd']['m'] is not None
          and 'point' in report and report['verdict']
          and report['exponent_at_vdd']['refusal'] is None)
    print('     verdict:', report['verdict'])
    check('report is JSON-serialisable',
          bool(json.dumps(report)))

    passed = sum(1 for _, ok in _results if ok)
    print(f'\n{passed}/{len(_results)} checks passed')
    return 0 if passed == len(_results) else 1


if __name__ == '__main__':
    sys.exit(main())
