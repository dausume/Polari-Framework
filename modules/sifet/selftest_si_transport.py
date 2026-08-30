"""
Selftest for sifet.si_transport (fg-4: the silicon scattering
basis — mechanism mfps DERIVED from the cited Caughey-Thomas/
[TAK94] mobility chain via the [LUN97] relation).

Run from polari-framework/modules/:
  PYTHONPATH=..:../polariApiServer python3 -m sifet.selftest_si_transport
"""

import sys

from cntfet import cnt_derive as cd
from cntfet import cnt_transport as tr
from cntfet import selftest_cntfet as st
from cntfet.cnt_device_viz import device_model
from cntfet.selftest_summary import _mgr, _seed_si
from sifet import si_transport as sit
from sifet.si_device import derive_si_device, get_row
from sifet.si_model import effective_mobility

_results = []


def check(label, cond, extra=''):
    _results.append((label, bool(cond)))
    print(f'{"PASS" if cond else "FAIL"}: {label}'
          + (f' — {extra}' if extra and not cond else ''))


def main():
    mgr = _mgr()
    st._seed_all(mgr)
    _seed_si(mgr)
    names = ('si-nmos-planar-90', 'si-pmos-planar-90',
             'si-nmos-freepdk45-class')
    check('derive: the three Si devices + S1',
          all(derive_si_device(mgr, get_row(mgr, 'SiliconMOSFET', n))
              ['ok'] for n in names)
          and cd.derive_device(
              mgr, cd.get_row(mgr, 'AlignedCNTFETDevice',
                              'cnt-aligned-s1'),
              parameter_factory=st._row_factory(
                  mgr, 'CNTFETParameterRow'))['ok'])

    reports = {}
    for n in names:
        _id, p, dev, refusal = device_model(mgr, n)
        assert refusal is None, refusal
        reports[n] = tr.transport_report(mgr, dev, p)
    rep = reports['si-nmos-planar-90']
    check('dispatch: transport_report on a Si row serves the '
          'silicon basis (no more refusal) with the CNT payload '
          'key shape (regime / mechanisms / topContributor / '
          'transmission)',
          rep.get('ok') and rep.get('technology') == 'silicon'
          and rep['regime']['name']
          and rep['topContributor'] and rep['mechanisms'],
          str(rep.get('error', ''))[:200])
    mechs = {m['name']: m for m in rep['mechanisms']}
    check('mechanisms: lattice-phonon + ionized-impurity + surface-'
          'roughness, every active λ finite and cited via its μ '
          'term; the surface term is flagged PRIOR',
          set(mechs) == {'lattice-phonon', 'ionized-impurity',
                         'surface-roughness'}
          and all(m['lambda_nm'] and m['lambda_nm'] > 0
                  for m in mechs.values() if m['active'])
          and mechs['surface-roughness']['is_prior']
          and not mechs['lattice-phonon']['is_prior']
          and 'CT67' in mechs['ionized-impurity']['lambda_formula'],
          str({k: m['lambda_nm'] for k, m in mechs.items()}))
    inv = sum(1.0 / m['lambda_nm'] for m in rep['mechanisms']
              if m['lambda_nm'])
    lam_mu = sit.lambda_from_mu_nm(
        effective_mobility(rep['context']['n_channel_cm3'], 'n')[1],
        rep['temperature_k'], 'n')
    check('identity: Matthiessen over the mechanism mfps equals the '
          'mfp of the cited effective mobility (the decomposition '
          'adds nothing and hides nothing)',
          abs(rep['lambda_eff_nm'] - 1.0 / inv) < 1e-9
          and abs(rep['lambda_eff_nm'] - lam_mu) < 1e-6,
          f"λ_eff={rep['lambda_eff_nm']:.4g} vs λ(μ_eff)={lam_mu:.4g}")
    check('cross-check: λ_eff sits at the [LUN97] near-source-mfp '
          'ORDER (stated as scale, not equality) and the payload '
          'carries the comparison',
          rep['crossCheck']['consistent_scale']
          and rep['crossCheck']['lun97_near_source_mfp_nm']
          == [10.0, 20.0],
          f"λ_eff={rep['lambda_eff_nm']:.4g} nm")
    check('physics: a 90 nm silicon channel is NOT ballistic — '
          'T = λ/(λ+Lg) well below the quasi-ballistic floor, '
          'regime scattered/semi-scattered, Lundstrom vs VS-card '
          'ballisticity BOTH stated',
          rep['transmission'] < 0.6
          and rep['regime']['name'] in ('scattered', 'semi-scattered')
          and 0 < rep['vs_model_ballisticity'] < 1
          and 'both stated' in rep['ballisticity_note'],
          f"T={rep['transmission']:.3f} regime={rep['regime']['name']}")
    n90 = reports['si-nmos-planar-90']['context']['n_channel_cm3']
    n45 = reports['si-nmos-freepdk45-class']['context']['n_channel_cm3']
    lam90 = {m['name']: m['lambda_nm']
             for m in reports['si-nmos-planar-90']['mechanisms']}
    lam45 = {m['name']: m['lambda_nm']
             for m in reports['si-nmos-freepdk45-class']['mechanisms']}
    hi, lo = (('si-nmos-freepdk45-class', 'si-nmos-planar-90')
              if n45 > n90 else ('si-nmos-planar-90',
                                 'si-nmos-freepdk45-class'))
    lam_hi = {m['name']: m['lambda_nm']
              for m in reports[hi]['mechanisms']}
    lam_lo = {m['name']: m['lambda_nm']
              for m in reports[lo]['mechanisms']}
    check('doping monotonicity: the heavier-doped channel has the '
          'shorter impurity mfp (the doping ROW feeds the term)',
          n90 != n45
          and lam_hi['ionized-impurity'] < lam_lo['ionized-impurity'],
          f'N={n90:.2g}/{n45:.2g} λ_imp={lam90["ionized-impurity"]}'
          f'/{lam45["ionized-impurity"]}')
    prep = reports['si-pmos-planar-90']
    check('polarity: the p device uses the hole parameter set '
          '(shorter lattice mfp than the n device — μ_p < μ_n)',
          prep.get('ok')
          and {m['name']: m for m in prep['mechanisms']}
          ['lattice-phonon']['lambda_nm']
          < mechs['lattice-phonon']['lambda_nm'])
    _id, p_cnt, cnt_dev, _r = device_model(mgr, 'cnt-aligned-s1')
    cnt_rep = tr.transport_report(mgr, cnt_dev, p_cnt)
    check('CNT unchanged: S1 still serves the CNT basis through the '
          'same entry point (processSet key, no technology tag)',
          cnt_rep.get('ok') and 'processSet' in cnt_rep
          and 'technology' not in cnt_rep,
          str(cnt_rep.get('error', ''))[:150])
    check('honesty: no invented aging series; the contact double-'
          'count refusal is stated',
          rep['timeSeries'] == []
          and 'double count' in rep['contact_note']
          and 'gap' in rep['bias']['note'])

    passed = sum(1 for _, ok in _results if ok)
    print(f'\n{passed}/{len(_results)} checks passed')
    return 0 if passed == len(_results) else 1


if __name__ == '__main__':
    sys.exit(main())
