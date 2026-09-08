"""
sifet selftest (check() style, no server): seeds the fp-2 rows into a
plain manager, derives, and proves that the silicon devices drive
the cntfet fv/fi machinery unchanged.

    cd modules && PYTHONPATH=..:../polariApiServer \\
        python3 -m sifet.sifet_selftest
"""

import math
import sys
import types

from cntfet.custom.cnt_metrics import extract_metrics
from cntfet.cnt_scoring_seed import fet_validity
from cntfet.cnt_states_basis import state_at_bias, transitions_on_sweep
from sifet.custom import si_model as sm
from sifet.si_basis import SEED_TABLES
from sifet.custom.si_device import (
    SI_TABLES, capability, derive_si_device, get_row, metric_spec,
    params_from_rows, resolve_components, si_device_model,
)

_results = []


def check(label, cond, extra=''):
    _results.append((label, bool(cond)))
    print(f'{"PASS" if cond else "FAIL"}: {label}'
          + (f' — {extra}' if extra else ''))


def _mgr():
    return types.SimpleNamespace(
        objectTables={t: {} for t in SI_TABLES}, db=None)


def _seed_all(mgr):
    for table, seeds in SEED_TABLES:
        for seed in seeds:
            fields = dict(seed)
            if table == 'SiliconMOSFET':
                fields.update(vt0_v=0.0, n_ss=0.0, dibl_v_per_v=0.0,
                              dvt_v=0.0, mu_cm2_per_vs=0.0,
                              vxo_m_per_s=0.0, cinv_f_per_m=0.0,
                              lambda_nm=0.0, equation_revision='',
                              derived_at='', provenance_json='{}')
            row = types.SimpleNamespace(**fields)
            mgr.objectTables[table][id(row)] = row


def main():
    mgr = _mgr()
    _seed_all(mgr)

    # ---- seeds resolve -------------------------------------------
    names = [d['name'] for d in dict(SEED_TABLES)['SiliconMOSFET']]
    unresolved = []
    for n in names:
        _rows, missing = resolve_components(
            mgr, get_row(mgr, 'SiliconMOSFET', n))
        unresolved += missing
    check('seeds: every SiliconMOSFET seed resolves all 5 component '
          'rows', not unresolved, str(unresolved))

    # ---- refusal before derive -----------------------------------
    id_fn, p, dev, refusal = si_device_model(mgr, 'si-nmos-planar-90')
    check('refusal: underived device refuses and names the derive '
          'affordance', id_fn is None and refusal
          and 'derive' in refusal['error'],
          (refusal or {}).get('error', ''))
    check('refusal: unknown device name refuses',
          si_device_model(mgr, 'nope')[3] is not None)

    # ---- derive all seeds ----------------------------------------
    reports = {n: derive_si_device(mgr, get_row(mgr, 'SiliconMOSFET', n))
               for n in names}
    check('derive: all four seeds derive ok',
          all(r['ok'] for r in reports.values()),
          str({n: r.get('error') for n, r in reports.items()
               if not r['ok']}))
    nmos = get_row(mgr, 'SiliconMOSFET', 'si-nmos-planar-90')
    pmos = get_row(mgr, 'SiliconMOSFET', 'si-pmos-planar-90')
    hfo2 = get_row(mgr, 'SiliconMOSFET', 'si-nmos-planar-solgel-hfo2')
    fin = get_row(mgr, 'SiliconMOSFET', 'si-nmos-finfet-solgel-hfo2')
    check('derive: provenance stamped (derived_at + provenance_json '
          'with refusals + intermediates)',
          nmos.derived_at and '"refusals"' in nmos.provenance_json
          and '"intermediates"' in nmos.provenance_json)

    # ---- physics numbers -----------------------------------------
    phi_f = sm.fermi_potential(1e17, 300.0)
    check('phi_F(1e17, 300 K) ~ 0.42 V ([SZE07])',
          0.40 <= phi_f <= 0.43, f'phi_F = {phi_f:.4f} V')
    check('Vt of the 1e17 p-channel NMOS on 2 nm thermal SiO2 lands '
          'in 0.2-0.6 V', 0.2 <= nmos.vt0_v <= 0.6,
          f'Vt0 = {nmos.vt0_v:.3f} V (Vfb prior {nmos.vfb_v} V)')
    check('PMOS Vt negative', pmos.vt0_v < 0.0,
          f'Vt0 = {pmos.vt0_v:.3f} V')
    check('n_ss planar in [1.05, 1.5]; finfet lower',
          1.05 <= nmos.n_ss <= 1.5 and fin.n_ss < nmos.n_ss,
          f'planar n_ss = {nmos.n_ss:.4f}, finfet n_ss = {fin.n_ss:.4f}')
    rows_n, _ = resolve_components(mgr, nmos)
    p45 = params_from_rows(rows_n, nmos, lg_nm=45.0)
    p90 = params_from_rows(rows_n, nmos)
    check('DIBL larger at Lg 45 nm than 90 nm (temporary shorter '
          'device)', p45['dibl_v_per_v'] > p90['dibl_v_per_v'],
          f"DIBL 45 = {p45['dibl_v_per_v']*1e3:.1f} mV/V, "
          f"90 = {p90['dibl_v_per_v']*1e3:.2f} mV/V, "
          f"lambda = {p90['lambda_nm']:.1f} nm")
    mu_n = sm.mobility_caughey_thomas(1e17, 'n')
    mu_p = sm.mobility_caughey_thomas(1e17, 'p')
    check('Caughey-Thomas mu_n(1e17) in 700-900 cm^2/Vs; mu_p below',
          700.0 <= mu_n <= 900.0 and mu_p < mu_n,
          f'mu_n = {mu_n:.0f}, mu_p = {mu_p:.0f} cm^2/Vs')
    check('sol-gel HfO2 planar: HIGHER Cinv and LOWER Vt roll-off '
          'than 2 nm thermal SiO2',
          hfo2.cinv_f_per_m > nmos.cinv_f_per_m
          and hfo2.dvt_v < nmos.dvt_v,
          f'Cinv HfO2 = {hfo2.cinv_f_per_m:.3e} vs SiO2 = '
          f'{nmos.cinv_f_per_m:.3e} F/m; dVt HfO2 = '
          f'{hfo2.dvt_v*1e3:.2f} vs SiO2 = {nmos.dvt_v*1e3:.2f} mV')
    vxo90 = sm.vxo_si(90.0)
    check('v_xo(90 nm) = B v_T lands 0.5-1.0e7 cm/s ([KHA09] trend)',
          5e4 <= vxo90 <= 1e5, f'v_xo = {vxo90*1e2:.2e} cm/s, '
          f'B = {sm.ballisticity(90.0):.3f}')

    # ---- device model + downstream reuse -------------------------
    id_fn, p, dev, refusal = si_device_model(mgr, 'si-nmos-planar-90')
    check('si_device_model returns (id_fn, p, device, None) after '
          'derive', id_fn is not None and refusal is None
          and p['equation_revision'] == sm.SI_EQUATION_REVISION)
    vdd = nmos.vdd_v
    grid = [i * 0.05 for i in range(int(vdd / 0.05) + 1)]
    ids = [id_fn(vg, vdd) for vg in grid]
    check('Id-Vg monotone at Vd = Vdd', all(ids[i + 1] >= ids[i]
                                            for i in range(len(ids) - 1)))
    ion, ioff = id_fn(vdd, vdd), id_fn(0.0, vdd)
    check(f'Ion/Ioff > 1e3 at Vdd = {vdd:g} V',
          ioff > 0 and ion / ioff > 1e3,
          f'Ion = {ion*1e6:.1f} uA/um, Ioff = {ioff:.2e} A/um, '
          f'ratio = {ion/ioff:.2e}')
    m = extract_metrics(id_fn, metric_spec(nmos))
    check('cntfet.custom.cnt_metrics.extract_metrics runs: SS + DIBL '
          'measurable', m['ss_mv_per_dec'] is not None
          and m['dibl_mv_per_v'] is not None,
          f"SS = {m['ss_mv_per_dec']:.1f} mV/dec, DIBL = "
          f"{m['dibl_mv_per_v']:.1f} mV/V, Vt_cc(sat) = "
          f"{m['vt_cc_sat_v']:.3f} V, refusals = {m['refusals']}")
    st_off = state_at_bias(p, 0.0, 0.6)['state']
    st_on = state_at_bias(p, 1.0, 0.6)['state']
    check('cntfet.cnt_states_basis.state_at_bias: off at Vg 0, on at Vg 1.0',
          st_off == 'off' and st_on.startswith('on'),
          f'{st_off} -> {st_on}')
    ev = transitions_on_sweep(p, 0.6, vgs_max=1.0)
    order = [e['to'] for e in ev]
    check('transitions_on_sweep walks off -> transition-on -> on',
          order[:2] == ['off', 'transition-on'] and len(order) >= 3
          and order[2].startswith('on'), str(order))
    v = fet_validity(id_fn, p)
    check('cntfet.cnt_scoring_seed.fet_validity: the NMOS is a valid FET',
          v['valid'], f"failed = {v['failed']}")

    # ---- p device = mirror ---------------------------------------
    id_p, pp, _d, _r = si_device_model(mgr, 'si-pmos-planar-90')
    id_n_of_p = sm.polarity_aware_id_fn(pp, 'n')
    mirror_ok = all(abs(id_p(vg, vd) + id_n_of_p(-vg, -vd))
                    <= 1e-12 + 1e-9 * abs(id_p(vg, vd))
                    for vg, vd in ((-1.0, -1.0), (-0.5, -0.3),
                                   (0.0, -1.0)))
    check("p device id_fn is the mirror: Id_p(vg,vd) = -Id_n(-vg,-vd)",
          mirror_ok and id_p(-1.0, -1.0) < 0.0,
          f'Id_p(-1,-1) = {id_p(-1.0, -1.0)*1e6:.1f} uA/um')
    check('PMOS drive below NMOS at |Vdd| (hole mobility)',
          abs(id_p(-1.0, -1.0)) < ion)

    # ---- finfet sanity -------------------------------------------
    id_f, pf, _d, _r = si_device_model(mgr, 'si-nmos-finfet-solgel-hfo2')
    check('finfet: Vt positive, DIBL < planar-45, valid FET',
          fin.vt0_v > 0 and pf['dibl_v_per_v'] < p45['dibl_v_per_v']
          and fet_validity(id_f, pf)['valid'],
          f"Vt = {fin.vt0_v:.3f} V, DIBL = {pf['dibl_v_per_v']*1e3:.3f} "
          f"mV/V, lambda = {pf['lambda_nm']:.2f} nm")
    cap = capability()
    check('capability names the gate-leakage refusal and the sol-gel '
          'prior', 'gate-leakage' in cap['refusals']
          and 'PRIOR' in cap['refusals']['gate-leakage'])
    check('derive refuses a same-type channel doping',
          not derive_si_device(mgr, types.SimpleNamespace(
              **{**vars(nmos), 'channel_doping': 'si-channel-n-1e17'}))
          ['ok'])

    passed = sum(1 for _l, ok in _results if ok)
    print(f'\n{passed}/{len(_results)} checks passed')
    return 0 if passed == len(_results) else 1


if __name__ == '__main__':
    sys.exit(main())
