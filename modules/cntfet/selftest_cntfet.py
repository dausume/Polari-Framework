"""
Selftest for cntfet (S1: one aligned CNT, DC, VS-derived compact
model + ToB F2 reference + Verilog-A/OSDI twin).

Run from polari-framework/:
  PYTHONPATH=. python3 -m cntfet.selftest_cntfet

Fake manager (SimpleNamespace rows); the OSDI equivalence leg runs
the REAL openvaf + ngspice when available (honest skip otherwise —
same convention as electrodevice's ngspice leg).
"""

import json
import sys
import types

from cntfet import cnt_bandstructure as bs
from cntfet import cnt_calibration as cal
from cntfet import cnt_capability as cap
from cntfet import cnt_derive as cd
from cntfet import cnt_osdi as osdi
from cntfet import cnt_tob as tob
from cntfet import cnt_validate as cv
from cntfet import cnt_verilog_a as va
from cntfet import cnt_vs_model as vs
from cntfet.cnt_basis import (
    SEED_CNT_CONTACTS, SEED_CNT_DEVICES, SEED_CNT_GEOMETRIES,
    SEED_CNT_MATERIALS, SEED_CNT_PARASITICS, SEED_CNT_TRANSPORT,
    SEED_GATE_STACKS,
)

_results = []


def check(label, cond, extra=''):
    _results.append((label, bool(cond)))
    print(f'{"PASS" if cond else "FAIL"}: {label}'
          + (f' — {extra}' if extra and not cond else ''))


TABLES = ('CNTMaterialState', 'AlignedCNTFETGeometry', 'GateStack',
          'CNTContact', 'CNTTransportModel', 'CNTParasitics',
          'AlignedCNTFETDevice', 'CNTFETParameterRow',
          'CNTCalibrationAnchor', 'CNTFETSimResult',
          'DeviceValidationReport')


def _mgr():
    return types.SimpleNamespace(
        objectTables={t: {} for t in TABLES}, db=None)


def _insert(mgr, table, row):
    mgr.objectTables[table][id(row)] = row
    return row


def _row_factory(mgr, table):
    def factory(**fields):
        fields.pop('manager', None)
        return _insert(mgr, table, types.SimpleNamespace(**fields))
    return factory


_CLASS_DEFAULTS = {
    'CNTMaterialState': dict(
        diameter_nm=0.0, eg_ev=0.0, vf_m_per_s=0.0,
        m_eff_over_m0=0.0, semiconducting=True, derived_at='',
        provenance_json='{}', notes=''),
    'GateStack': dict(
        geometry='gaa-cylindrical', cox_f_per_m=0.0,
        cqe_f_per_m=0.0, cinv_f_per_m=0.0, derived_at='',
        provenance_json='{}', notes=''),
    'CNTContact': dict(rq_floor_ohm=0.0, derived_at='',
                       provenance_json='{}', notes=''),
    'CNTTransportModel': dict(
        model_family='VS-CNFET-derived',
        implementation='independent',
        numerically_equivalent_to_stanford=False,
        equation_revision='', physics_fidelity='VS_MINIMAL',
        vt0_source='prior', efsd_source='prior',
        vxo_m_per_s=0.0, mu_cm2_per_vs=0.0, n_ss=0.0,
        dibl_v_per_v=0.0, dvt_v=0.0, lambda_nm=0.0,
        derived_at='', provenance_json='{}', notes=''),
    'AlignedCNTFETDevice': dict(derived_at='',
                                provenance_json='{}', notes=''),
}


def _seed_all(mgr):
    """Seed the S1 rows the way the server would."""
    for table, seeds in (
            ('CNTMaterialState', SEED_CNT_MATERIALS),
            ('AlignedCNTFETGeometry', SEED_CNT_GEOMETRIES),
            ('GateStack', SEED_GATE_STACKS),
            ('CNTContact', SEED_CNT_CONTACTS),
            ('CNTTransportModel', SEED_CNT_TRANSPORT),
            ('CNTParasitics', SEED_CNT_PARASITICS),
            ('AlignedCNTFETDevice', SEED_CNT_DEVICES)):
        for seed in seeds:
            fields = dict(_CLASS_DEFAULTS.get(table, {}))
            fields.update(seed)
            _row_factory(mgr, table)(**fields)


def main():
    # ---- S1a: bandstructure + electrostatics ----------------------
    d = bs.chirality_to_diameter_nm(16, 0)
    check('S1a: d(16,0) = 1.253 nm (zone-folding geometry)',
          abs(d - 1.2526) < 2e-3, f'd={d}')
    check('S1a: (15,0) is METALLIC, (16,0) semiconducting '
          '((n-m) mod 3 rule)',
          (not bs.is_semiconducting(15, 0))
          and bs.is_semiconducting(16, 0))
    eg = bs.eg_ev(d)
    check('S1a: Eg(1.253 nm) ~ 0.68 eV (Eg = 2 Ep a_cc/d, '
          '~0.85/d)', abs(eg - 0.680) < 5e-3, f'eg={eg}')
    mstar = bs.m_eff_over_m0(eg)
    check('S1a: m* = Eg/(2 vF^2) lands in the [GUO04] '
          '0.05-0.08 m0 window', 0.05 <= mstar <= 0.08,
          f'm*={mstar}')
    cox3 = bs.cox_gaa_f_per_m(3.0, d, 16.0)
    cox6 = bs.cox_gaa_f_per_m(6.0, d, 16.0)
    cqe = bs.cqe_f_per_m(eg)
    cinv = bs.cinv_f_per_m(cox3, cqe)
    check('S1a: GAA Cox positive and decreasing with t_ox; Cinv '
          'below both series legs',
          cox3 > cox6 > 0.0 and cinv < min(cox3, cqe))
    sce = bs.sce_parameters(15.0, 3.0, d, 16.0, eg, 0.1)
    check('S1a: scale length eq.(7) ~ 1.43 nm at t_ox 3 nm '
          '(hand-checked)', abs(sce['lambda_nm'] - 1.431) < 0.01,
          f"lambda={sce['lambda_nm']}")
    check('S1a: well-tempered Lg=15 nm: n_ss ~ 1.003 (SS ~ 60), '
          'DIBL and roll-off small',
          1.0 < sce['n_ss'] < 1.01
          and sce['dibl_v_per_v'] < 0.01 and sce['dvt_v'] < 0.01)

    # ---- S1c: VS parameters vs the calibration anchors ------------
    check('S1c: eq.(9) reproduces the [FC10] v_xo anchors in '
          'domain (15 nm within 2%, 300 nm within 3%)',
          abs(vs.vxo_m_per_s(15.0, 1.2) - 3.8e5) / 3.8e5 < 0.02
          and abs(vs.vxo_m_per_s(300.0, 1.2) - 1.7e5) / 1.7e5
          < 0.03)
    resid_3um = (vs.vxo_m_per_s(3000.0, 1.2) - 0.47e5) / 0.47e5
    check('S1c: the 3 um anchor MISFITS visibly (out-of-domain '
          'for l ~= Lg) — honesty, not accuracy',
          resid_3um < -0.2, f'residual={resid_3um}')
    p = vs.build_vs_params(
        {'diameter_nm': d, 'eg_ev': eg}, {'lg_nm': 15.0},
        {'t_ox_nm': 3.0, 'k_ox': 16.0}, {'rc_ohm': 5500.0},
        {'vt0_v': 0.3, 'efsd_ev': 0.1}, 300.0)
    ids = [vs.vs_terminal_current(vg, 0.4, p)['id_a']
           for vg in (0.0, 0.2, 0.4, 0.6)]
    check('S1c: Id-Vg monotone increasing; on-state uA-class per '
          'tube; off-state sub-nA',
          all(b > a for a, b in zip(ids, ids[1:]))
          and 1e-6 < ids[-1] < 1e-4 and ids[0] < 1e-9,
          f'ids={ids}')
    ss = vs.subthreshold_slope_mv_per_dec(p)
    check('S1c: numeric SS in the physical band (>= 59.6 n_ss, '
          '< 100 mV/dec for this electrostatics)',
          59.0 <= ss < 100.0, f'ss={ss}')
    idvd = [vs.vs_terminal_current(0.6, vd, p)['id_a']
            for vd in (0.05, 0.1, 0.2, 0.3, 0.4, 0.5)]
    check('S1c: Id-Vd monotone with smooth saturation (Fsat, '
          'no regime cliff)',
          all(b > a for a, b in zip(idvd, idvd[1:]))
          and idvd[-1] / idvd[0] < 8.0)
    p_hi_rc = dict(p, rs_ohm=20000.0, rd_ohm=20000.0)
    ids_hi = [vs.vs_terminal_current(0.6, vd, p_hi_rc)['id_a']
              for vd in (0.05, 0.1, 0.2, 0.3, 0.4, 0.5)]
    check('S1c: Rc is first-class — 20 kOhm contacts cut Ion vs '
          '5.5 kOhm, bisection stays monotone/converged (the '
          'fixed-point oscillation is FIXED)',
          ids_hi[-1] < idvd[-1]
          and all(b > a for a, b in zip(ids_hi, ids_hi[1:])))

    # ---- S1b: ToB F2 reference ------------------------------------
    pt = {'eg_ev': eg, 'vf_m_per_s': bs.fermi_velocity_m_per_s(),
          'lg_nm': 15.0, 'cox_f_per_m': cox3,
          'temperature_k': 300.0, 'eta0_ev': 0.3,
          'cd_over_cg': sce['dibl_v_per_v'],
          'transmission_mode': 'acoustic-mfp'}
    ops = [tob.tob_operating_point(vg, 0.4, pt)
           for vg in (0.0, 0.3, 0.6)]
    check('S1b: ToB self-consistency converges at every smoke '
          'point', all(op['converged'] for op in ops))
    check('S1b: ToB Id monotone in Vg; on-state within ~2x of '
          'the VS path (triangle edge sane, ToB has no Rc)',
          ops[0]['id_a'] < ops[1]['id_a'] < ops[2]['id_a']
          and 0.5 < ops[2]['id_a'] / ids[-1] < 3.0,
          f"tob={ops[2]['id_a']}, vs={ids[-1]}")
    check('S1b: charging term pushes back — |U| < alpha_G Vg '
          '(quantum-capacitance self-consistency is real)',
          abs(ops[2]['u_ev']) < 0.6)
    ii = tob.current_integral_check(ops[2]['e_top_ev'], 0.4,
                                    300.0, ops[2]['t_bar'])
    check('S1b: closed-form Landauer == numeric energy integral '
          '(rel < 1e-6)',
          abs(ops[2]['id_a'] - ii) / ii < 1e-6)
    op_bal = tob.tob_operating_point(
        0.6, 0.4, dict(pt, transmission_mode='ballistic'))
    check('S1b: ballistic T=1 exceeds acoustic-mfp T=lambda/'
          '(lambda+L) ([LUN97] lift)',
          op_bal['id_a'] > ops[2]['id_a'])

    # ---- derive act on the seeded fake manager --------------------
    mgr = _mgr()
    _seed_all(mgr)
    device = cd.get_row(mgr, 'AlignedCNTFETDevice', 'cnt-aligned-s1')
    pfac = _row_factory(mgr, 'CNTFETParameterRow')
    broken = types.SimpleNamespace(
        name='broken', polarity='n', material='no-such-tube',
        geometry='cnt-s1-lg15', gate_stack='cnt-s1-hfo2-gaa',
        contact='cnt-s1-pd-contact', transport='cnt-s1-vs-transport',
        parasitics='cnt-s1-no-parasitics', temperature_k=300.0,
        derived_at='', provenance_json='{}')
    rep = cd.derive_device(mgr, broken, parameter_factory=pfac)
    check('derive: refuses on a missing component row (no '
          'defaults invented)',
          not rep['ok'] and 'refusal' in rep)
    metal = cd.get_row(mgr, 'CNTMaterialState', 'cnt-16-0')
    metal_n = metal.chirality_n
    metal.chirality_n = 15  # (15,0) is metallic
    rep = cd.derive_device(mgr, device, parameter_factory=pfac)
    check('derive: refuses a METALLIC chirality honestly',
          not rep['ok'] and 'METALLIC' in rep.get('error', ''))
    metal.chirality_n = metal_n
    rep = cd.derive_device(mgr, device, parameter_factory=pfac)
    prow_table = mgr.objectTables['CNTFETParameterRow']
    roles = {getattr(r, 'role', '') for r in prow_table.values()}
    check('derive: succeeds and stamps role-tagged parameter rows '
          '(D8): physical + derived + compact-model + calibration '
          'all present',
          rep['ok'] and len(prow_table) >= 20
          and {'physical', 'derived', 'compact-model',
               'calibration'} <= roles,
          f'roles={roles}, rows={len(prow_table)}')
    check('derive: every parameter row carries role AND source',
          all(getattr(r, 'role', '') and getattr(r, 'source', '')
              for r in prow_table.values()))
    transport = cd.get_row(mgr, 'CNTTransportModel',
                           'cnt-s1-vs-transport')
    check('derive: D3 labels ride the transport row (family/'
          'independent/NOT-Stanford-equivalent + equation '
          'revision)',
          transport.model_family == 'VS-CNFET-derived'
          and transport.implementation == 'independent'
          and transport.numerically_equivalent_to_stanford is False
          and transport.equation_revision != '')

    # iv act through the rows
    fac_res = _row_factory(mgr, 'CNTFETSimResult')
    rep_iv = cd.run_iv(mgr, device, engine='vs',
                       result_factory=fac_res)
    rep_tob = cd.run_iv(mgr, device, engine='tob',
                        result_factory=fac_res)
    check('iv act: both engines run from the SAME device rows '
          '(validation triangle wiring)',
          rep_iv['ok'] and rep_tob['ok']
          and rep_iv['fidelity'] == 'VS_MINIMAL'
          and rep_tob['fidelity'] == 'TOB_F2')

    # ---- calibration ----------------------------------------------
    afac = _row_factory(mgr, 'CNTCalibrationAnchor')
    made = cal.seed_anchor_rows(mgr, afac)
    check('calibration: anchor rows seed idempotently with D18 '
          'provenance fields',
          len(made) == len(cal.SEED_CALIBRATION_ANCHORS)
          and cal.seed_anchor_rows(mgr, afac) == [])
    rep_cal = cal.calibrate_device(mgr, device,
                                   result_factory=fac_res)
    vxo_resids = [r for r in rep_cal['residuals']
                  if r['quantity'] == 'vxo_m_per_s']
    ood = [r for r in vxo_resids if 'outOfDomain' in r]
    check('calibration: v_xo residuals recorded for all three Lg '
          'anchors; the 3 um one is FLAGGED out-of-domain',
          rep_cal['ok'] and len(vxo_resids) == 3
          and len(ood) == 1 and '3000' in str(ood[0]['anchor']),
          f'resids={vxo_resids}')
    check('calibration: the un-digitized [FC10] curve set REFUSES '
          '(named gap, not silence)',
          any('fc10-idvd-curves' in r['anchor']
              for r in rep_cal['refused']))
    gm_res = [r for r in rep_cal['residuals']
              if r['quantity'] == 'gm_s']
    check('calibration: gm evaluated in the ANCHOR context '
          '(back-gate Cox, 5.5 kOhm) lands within 2x of the '
          '40 uS record',
          len(gm_res) == 1
          and 0.5 < (gm_res[0]['modelValue'] / 40e-6) < 2.0,
          f'gm={gm_res}')

    # ---- validator -------------------------------------------------
    findings, _rows = cv.validate_cntfet_device(mgr, device)
    by = {f['criterion']: f['status'] for f in findings}
    check('validator: judges the aligned device — components/'
          'params/roles/rc/labels/priors PASS, calibration '
          'recorded, equivalence still a warn',
          by.get('components-resolved') == 'pass'
          and by.get('params-derived') == 'pass'
          and by.get('roles-assigned') == 'pass'
          and by.get('rc-first-class') == 'pass'
          and by.get('model-labeled') == 'pass'
          and by.get('priors-honest') == 'pass'
          and by.get('calibration-recorded') == 'pass'
          and by.get('equivalence-proven') == 'warn',
          f'findings={by}')
    contact = cd.get_row(mgr, 'CNTContact', 'cnt-s1-pd-contact')
    rc_keep = contact.rc_ohm
    contact.rc_ohm = 1000.0  # below the ~3.23 kOhm quantum floor
    findings, _rows = cv.validate_cntfet_device(mgr, device)
    by = {f['criterion']: f['status'] for f in findings}
    check('validator: an Rc prior below the quantum floor FAILS '
          '(unphysical contacts cannot pass)',
          by.get('rc-first-class') == 'fail')
    contact.rc_ohm = rc_keep

    # ---- capability (D14) ------------------------------------------
    report = cap.capability()
    fids = report['fidelities']
    check('capability: F0/F1/F2 present; F3-NEGF REFUSES with a '
          'reason (thin module, D14)',
          fids['F0-analytical']['present']
          and fids['F1-VS-compact']['present']
          and fids['F2-ToB']['present']
          and not fids['F3-NEGF']['present']
          and fids['F3-NEGF']['refusal'])

    # ---- S1d: construct gate + OSDI equivalence --------------------
    gate = va.construct_gate_check(va.generate_va())
    check('S1d: generated Verilog-A passes the construct gate',
          gate['ok'], f"violations={gate['violations']}")
    bad = va.generate_va().replace(
        'idch = qxo * vxo * fsat;',
        'idch = laplace_zp(qxo, 1, 2);')
    check('S1d: the gate CATCHES a banned construct (executable '
          'gate, not aspiration)',
          not va.construct_gate_check(bad)['ok'])
    openvaf_path, _why = osdi.find_openvaf()
    ngspice_path, _why2 = osdi.find_ngspice()
    if openvaf_path and ngspice_path:
        variants = {'base': p, 'rc-20k': p_hi_rc}
        rep_eq = osdi.equivalence_regression(
            variants, vg_list=[0.0, 0.3, 0.6],
            vd_list=[0.05, 0.15, 0.25, 0.35, 0.45],
            keep_bundle=False)
        check('S1d: D3 equivalence regression — Python reference '
              '== OSDI twin in ngspice within recorded tolerances',
              rep_eq.get('ok')
              and rep_eq['verdict'] == 'EQUIVALENT'
              and rep_eq['pointsChecked'] == 30,
              f'report={ {k: rep_eq.get(k) for k in ("verdict", "worst", "failures")} }')
    else:
        print('SKIP: S1d equivalence — openvaf/ngspice not '
              'available on this host (capability endpoint reports '
              'the same refusal)')

    passed = sum(1 for _, ok in _results if ok)
    print(f'\n{passed}/{len(_results)} checks passed')
    return 0 if passed == len(_results) else 1


if __name__ == '__main__':
    sys.exit(main())
