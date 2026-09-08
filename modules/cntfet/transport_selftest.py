"""
Selftest for cntfet.cnt_transport_basis (fv-2: transport regime +
scattering contributors over time).

Run from polari-framework/modules/:
  PYTHONPATH=..:../polariApiServer python3 -m cntfet.transport_selftest
"""

import json
import sys
import types

from cntfet.custom import cnt_derive as cd
from cntfet import cnt_transport_basis as tr
from cntfet import cntfet_selftest as st
from cntfet.custom.cnt_citations import TAG_CITATIONS
from cntfet.cnt_device_viz_seed import device_model

check = st.check


def _device(mgr, name):
    device = cd.get_row(mgr, 'AlignedCNTFETDevice', name)
    cd.derive_device(mgr, device,
                     parameter_factory=st._row_factory(mgr,
                                                       'CNTFETParameterRow'))
    _id, p, dev, refusal = device_model(mgr, name)
    assert refusal is None, refusal
    return p, dev


def main():
    mgr = st._mgr()
    st._seed_all(mgr)

    # ---- seeds parse and cite -------------------------------------
    tags = set(TAG_CITATIONS)
    ok_seeds = True
    for s in tr.SEED_SCATTERING_MECHANISMS:
        for key in ('bias_condition_json', 'process_knob_json',
                    'time_profile_json', 'enforced_properties_json'):
            json.loads(s[key])
        cited = any(t in (s['description'] + s['notes']) for t in tags)
        ok_seeds = ok_seeds and cited and bool(s['lambda_formula'])
    for r in tr.SEED_TRANSPORT_REGIMES:
        crit = json.loads(r['criteria_json'])
        ok_seeds = ok_seeds and bool(crit) and bool(r['description'])
    check('fv-2: 5 mechanism + 4 regime seeds parse, every mechanism '
          'cites a registered tag and carries its λ formula as data',
          ok_seeds and len(tr.SEED_SCATTERING_MECHANISMS) == 5
          and len(tr.SEED_TRANSPORT_REGIMES) == 4)
    names = {s['name'] for s in tr.SEED_SCATTERING_MECHANISMS}
    check('fv-2: mechanisms = acoustic, optical, defect, contact, '
          'alignment; phonons do not age, defects do (time_profile '
          'PRIOR)',
          names == {'acoustic-phonon', 'optical-phonon',
                    'defect-impurity', 'contact-interface',
                    'alignment-misorientation'}
          and json.loads(next(s for s in tr.SEED_SCATTERING_MECHANISMS
                              if s['name'] == 'defect-impurity')
                         ['time_profile_json'])['kind'] == 'aging'
          and json.loads(next(s for s in tr.SEED_SCATTERING_MECHANISMS
                              if s['name'] == 'acoustic-phonon')
                         ['time_profile_json'])['kind'] == 'none')

    # ---- S1 at low and high bias -----------------------------------
    p, dev = _device(mgr, 'cnt-aligned-s1')
    lo = tr.transport_report(mgr, dev, p, vgs=0.6, vds=0.05)
    hi = tr.transport_report(mgr, dev, p, vgs=0.6, vds=0.6)
    check('fv-2: S1 (Lg 15 nm) at Vds 0.05 V is ballistic or '
          'quasi-ballistic with T stated',
          lo['ok'] and lo['regime']['name'] in ('ballistic',
                                                'quasi-ballistic')
          and 0.0 < lo['transmission'] < 1.0,
          f"regime={lo['regime']['name']} T={lo['transmission']}")
    op_lo = next(m for m in lo['mechanisms'] if m['name'] == 'optical-phonon')
    op_hi = next(m for m in hi['mechanisms'] if m['name'] == 'optical-phonon')
    check('fv-2: the optical branch flips — inactive at 0.05 V, '
          'active at 0.6 V (qVds ≥ 0.18 eV); T drops',
          (not op_lo['active']) and op_lo['lambda_nm'] is None
          and op_hi['active'] and op_hi['lambda_nm'] is not None
          and hi['transmission'] < lo['transmission'],
          f"T_lo={lo['transmission']} T_hi={hi['transmission']}")
    for rep, label in ((lo, 'low'), (hi, 'high')):
        active = [m for m in rep['mechanisms'] if m['lambda_nm']]
        total = sum(m['contribution'] for m in rep['mechanisms'])
        check(f'fv-2: contributions sum to 1 over the active '
              f'mechanisms ({label} bias) and λ_eff ≤ min active λ',
              abs(total - 1.0) < 1e-9
              and rep['lambda_eff_nm'] <= min(m['lambda_nm']
                                              for m in active) + 1e-12,
              f'sum={total} lambda_eff={rep["lambda_eff_nm"]}')
    check('fv-2: top contributor is acoustic at low bias, optical at '
          'Vdd',
          lo['topContributor'] == 'acoustic-phonon'
          and hi['topContributor'] == 'optical-phonon')
    check('fv-2: VS-model ballisticity λ_v/(λ_v+2Lg) ≈ 0.936 for '
          'Lg 15 reported BESIDE ours (both defined)',
          abs(lo['vs_model_ballisticity'] - 440.0 / 470.0) < 1e-6
          and 'two definitions' in lo['ballisticity_note'],
          f"{lo['vs_model_ballisticity']}")
    check('fv-2: enforced properties — ion_factor = B = T/(2−T), '
          'v_inj/vT = B, μ_app finite, SS untouched',
          abs(hi['enforced']['ion_factor']
              - hi['transmission'] / (2 - hi['transmission'])) < 1e-12
          and hi['enforced']['v_inj_over_vT'] == hi['enforced'][
              'ion_factor']
          and hi['enforced']['mu_app_cm2_per_vs'] > 0
          and hi['enforced']['ss_effect'].startswith('none'))
    check('fv-2: contact factor T_c = RQ/2 / Rc < 1 is reported '
          'separately (contribution 0 — not a mfp) and regime '
          'evaluations carry the numbers',
          0 < hi['contact_transmission'] < 1
          and next(m for m in hi['mechanisms']
                   if m['name'] == 'contact-interface')['contribution']
          == 0.0
          and all('lhs_value' in c for ev in hi['regime']['evaluations']
                  for c in ev['criteria']))

    # ---- long device is scattered ----------------------------------
    long_geo = st._row_factory(mgr, 'AlignedCNTFETGeometry')(
        name='cnt-lg1000', lg_nm=1000.0, l_ext_nm=0.0, l_c_nm=20.0,
        tube_count=1, pitch_nm=0.0, notes='')
    long_dev = types.SimpleNamespace(
        **{**vars(dev), 'name': 'cnt-long', 'geometry': 'cnt-lg1000',
           'derived_at': ''})
    st._insert(mgr, 'AlignedCNTFETDevice', long_dev)
    p_long, long_dev = _device(mgr, 'cnt-long')
    lg = tr.transport_report(mgr, long_dev, p_long, vds=0.05)
    check('fv-2: a Lg = 1000 nm device is scattered even at low bias',
          lg['regime']['name'] == 'scattered',
          f"regime={lg['regime']['name']} T={lg['transmission']}")

    # ---- time series ------------------------------------------------
    ts = hi['timeSeries']
    t_vals = [pt['transmission'] for pt in ts]
    mono = all(a >= b - 1e-15 for a, b in zip(t_vals, t_vals[1:]))
    k = hi['knobs']
    thresholds = (k['t_ballistic'], k['t_quasi'], k['t_semi'])

    def _band(t):
        return sum(1 for th in thresholds if t >= th)
    labels_ok = all(
        (a['regime'] == b['regime'])
        == (_band(a['transmission']) == _band(b['transmission']))
        for a, b in zip(ts, ts[1:]))
    check('fv-2: ~25-point log-spaced series, T monotone '
          'non-increasing under the aging prior; regime labels '
          'change only where T crosses a knob threshold',
          len(ts) == 25 and ts[0]['t_hours'] == 0.0
          and ts[-1]['t_hours'] == hi['horizon_hours'] and mono
          and labels_ok
          and 'ScatteringMechanism.defect-impurity' in hi['priorFlagged'])

    # ---- knobs change the verdict -----------------------------------
    strict = tr.transport_report(mgr, dev, p, vds=0.05,
                                 knobs={'t_ballistic': 0.99})
    total = tr.transport_report(mgr, dev, p, vds=0.05,
                                knobs={'regime_on': 'total'})
    check('fv-2: knobs change the verdict and are echoed (stricter '
          'ballistic threshold / classify on total transmission)',
          strict['knobs']['t_ballistic'] == 0.99
          and strict['regime']['name'] != 'ballistic'
          and total['regime']['t_regime'] < lo['regime']['t_regime']
          and total['regime']['name'] != lo['regime']['name'],
          f"lo={lo['regime']['name']} strict={strict['regime']['name']} "
          f"total={total['regime']['name']}")

    # ---- refusal without a process set ------------------------------
    keep = dev.process_set
    dev.process_set = ''
    bad = tr.transport_report(mgr, dev, p)
    dev.process_set = keep
    check('fv-2: refuses (names process_set) when the device has no '
          'process set', not bad['ok'] and 'process_set' in bad['refusal'])

    # ---- graph rows + seeds -----------------------------------------
    rows_lg, _r = tr.CURVE_BUILDERS['transport-vs-lg'](None, p, dev, mgr,
                                                        None)
    rows_c, _r = tr.CURVE_BUILDERS['scattering-contributions'](
        None, p, dev, mgr, None)
    rows_t, _r = tr.CURVE_BUILDERS['transport-over-time'](None, p, dev,
                                                           mgr, None)
    styles = lambda rows: {r['style'] for r in rows}
    check('fv-2: three row builders — T(Lg) line + regime bands + '
          'Lg guide; categorical contributions dots + hguide; '
          'time lines + threshold hguides',
          {'line', 'band', 'guide'} <= styles(rows_lg)
          and {'dot', 'hguide'} <= styles(rows_c)
          and all(isinstance(r['x'], str) for r in rows_c
                  if r['style'] == 'dot')
          and {'line', 'hguide'} <= styles(rows_t)
          and len([r for r in rows_t if r['style'] == 'line']) == 50)
    seeds_ok = True
    for g in tr.SEED_CNT_TRANSPORT_GRAPHS:
        cfg = json.loads(g['definition'])['graphConfig']
        seeds_ok = seeds_ok and g['name'].startswith('cnt-device-') \
            and cfg['xDimension'] == 'x' and cfg['options']['xLabel']
    check('fv-2: 3 GraphDefinition seeds round-trip through json in '
          'the _device_graph shape',
          seeds_ok and len(tr.SEED_CNT_TRANSPORT_GRAPHS) == 3
          and {g['name'][11:] for g in tr.SEED_CNT_TRANSPORT_GRAPHS}
          == set(tr.CURVE_BUILDERS))

    passed = sum(1 for _l, ok in st._results if ok)
    print(f'\nselftest_transport: {passed}/{len(st._results)} passed')
    print(f"S1 numbers: T_lo={lo['transmission']:.4f} "
          f"({lo['regime']['name']}), T_hi={hi['transmission']:.4f} "
          f"({hi['regime']['name']}), λ_eff lo/hi = "
          f"{lo['lambda_eff_nm']:.1f}/{hi['lambda_eff_nm']:.1f} nm, "
          f"top lo/hi = {lo['topContributor']}/{hi['topContributor']}, "
          f"T_c={hi['contact_transmission']:.3f}, "
          f"VS ballisticity={hi['vs_model_ballisticity']:.3f}")
    return passed == len(st._results)


if __name__ == '__main__':
    sys.exit(0 if main() else 1)
