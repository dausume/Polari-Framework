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
          'DeviceValidationReport',
          'CNTAlignmentProcess', 'CNTPlacementProcess',
          'CNTPurificationProcess', 'ContactFormationProcess',
          'LithographyProcess', 'GateStackProcess',
          'CNTFETMonteCarloRun')


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
    """Seed the S1 rows + the S3 process set the way the server
    would."""
    from cntfet.cnt_process_basis import (
        SEED_ALIGNMENT_PROCESSES, SEED_CONTACT_PROCESSES,
        SEED_GATESTACK_PROCESSES, SEED_LITHOGRAPHY_PROCESSES,
        SEED_PLACEMENT_PROCESSES, SEED_PURIFICATION_PROCESSES,
    )
    for table, seeds in (
            ('CNTMaterialState', SEED_CNT_MATERIALS),
            ('AlignedCNTFETGeometry', SEED_CNT_GEOMETRIES),
            ('GateStack', SEED_GATE_STACKS),
            ('CNTContact', SEED_CNT_CONTACTS),
            ('CNTTransportModel', SEED_CNT_TRANSPORT),
            ('CNTParasitics', SEED_CNT_PARASITICS),
            ('AlignedCNTFETDevice', SEED_CNT_DEVICES),
            ('CNTAlignmentProcess', SEED_ALIGNMENT_PROCESSES),
            ('CNTPlacementProcess', SEED_PLACEMENT_PROCESSES),
            ('CNTPurificationProcess', SEED_PURIFICATION_PROCESSES),
            ('ContactFormationProcess', SEED_CONTACT_PROCESSES),
            ('LithographyProcess', SEED_LITHOGRAPHY_PROCESSES),
            ('GateStackProcess', SEED_GATESTACK_PROCESSES)):
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
    from cntfet.cnt_reference_papers import (
        SEED_REFERENCE_ANCHORS as _REF_ANCHORS,
    )
    made = cal.seed_anchor_rows(mgr, afac)
    check('calibration: anchor rows (calibration + reference '
          'papers) seed idempotently with D18 provenance fields',
          len(made) == len(cal.SEED_CALIBRATION_ANCHORS)
          + len(_REF_ANCHORS)
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

    # ---- S2: digitized curves + residuals -------------------------
    dig = [r for r in
           mgr.objectTables['CNTCalibrationAnchor'].values()
           if getattr(r, 'name', '') == 'fc10-idvd-lg15-digitized']
    check('S2c: the Fig.7(a) digitization is a READY anchor with '
          '58 raw points + axis calibration + error budget (D18)',
          len(dig) == 1 and dig[0].status == 'ready'
          and dig[0].value == 58.0
          and 'px_per_v' in dig[0].axis_scaling_json
          and '0.26 uA' in dig[0].digitization_error)
    curve_res = [r for r in rep_cal['residuals']
                 if 'idvd-curve' in r['quantity']]
    flagship = [r for r in curve_res
                if 'ov+0.50' in r['quantity']]
    sub = [r for r in curve_res if 'ov-0.25' in r['quantity']]
    check('S2c: curve residuals recorded for all four overdrives; '
          'the flagship ov+0.50 curve lands within 2x the '
          'digitization noise floor',
          len(curve_res) == 4 and flagship
          and flagship[0]['rmsErrorUa'] < 0.52,
          f'curves={[(r["quantity"], round(r["rmsErrorUa"], 3)) for r in curve_res]}')
    check('S2c: the subthreshold curve honestly MISSES (device '
          'leakage floor unmodeled) — the residual is recorded, '
          'not hidden',
          sub and sub[0]['meanFractional'] is not None
          and sub[0]['meanFractional'] < -0.5)

    # ---- S2: metrics + validation triangle ------------------------
    from cntfet.cnt_metrics import G0_FC10_S, extract_metrics
    from cntfet.cnt_triangle import validation_triangle
    m_vs = extract_metrics(
        lambda vg, vd: vs.vs_terminal_current(vg, vd, p)['id_a'])
    check('S2a: the metric family extracts cleanly from the VS '
          'engine (SS/DIBL/Ion/Ioff/gm/G_on, no refusals)',
          not m_vs['refusals'] and 59.0 < m_vs['ss_mv_per_dec'] < 100
          and m_vs['dibl_mv_per_v'] > 0
          and m_vs['on_off_ratio'] > 1e3
          and m_vs['gm_peak_s'] > 0)
    tri = validation_triangle(
        mgr, device, result_factory=_row_factory(mgr,
                                                 'CNTFETSimResult'))
    check('S2b: the validation triangle records both edges, '
          'per-metric deltas, and the adaptive-oracle target list',
          tri['ok'] and len(tri['points']) == 25
          and tri['metrics']['tob-intrinsic']['g_on_s'] > 0
          and 'quantum_bound' in tri['honesty']
          and len(tri['oracleTargets']) > 0
          and all(t['dex'] > tri['thresholdDex']
                  for t in tri['oracleTargets']))
    check('S2b: physics sanity — ToB (which owns the quantum '
          'limit natively) stays at or below G0 = 4e^2/h',
          tri['metrics']['tob-intrinsic']['g_on_s']
          <= G0_FC10_S * 1.001)

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
    f3_state = fids['F3-NEGF']
    check('capability: F0/F1/F2 present; F3-NEGF reflects the '
          'LIVE probe — present with its limits when the kwant '
          'venv exists, refusing with a reason otherwise (D14)',
          fids['F0-analytical']['present']
          and fids['F1-VS-compact']['present']
          and fids['F2-ToB']['present']
          and ((f3_state['present'] and f3_state['limits'])
               or (not f3_state['present']
                   and f3_state['refusal'])))
    scf_state = fids['F3-NEGF-SCF']
    check('capability: F3-NEGF-SCF (D13) rides the same live '
          'probe — present with its own limits or refusing with '
          'a reason, never a silent middle',
          ((scf_state['present'] and 'Poisson' in
            scf_state['limits'])
           or (not scf_state['present'] and scf_state['refusal'])))

    # ---- figure replicas (Dustin 2026-08-25) ----------------------
    from cntfet.cnt_figures import (
        FIGURE_REGISTRY, build_figure, figures_index,
    )
    idx = figures_index()
    check('figures: the registry indexes every cited figure with '
          'an honest status, and every refusing entry NAMES its '
          'missing step',
          idx['ok'] and len(idx['figures']) == len(FIGURE_REGISTRY)
          and all(f.get('refusal')
                  for f in idx['figures']
                  if f['status'] == 'refusing')
          and {f['status'] for f in idx['figures']}
          == {'replica', 'model-only', 'refusing'})
    fig7a = build_figure('vs1-fig7a')
    flagship = next(r for r in fig7a['residuals']
                    if 'ov+0.50' in r['quantity'])
    check('figures: the vs1-fig7a REPLICA carries paper points '
          'with the D18 error budget + model curves on the paper '
          'axes + the recorded residuals (flagship curve at the '
          'digitization noise floor)',
          fig7a['ok'] and fig7a['status'] == 'replica'
          and fig7a['axes']['y']['max'] == 15.0
          and len(fig7a['paperSeries']) == 4
          and len(fig7a['modelSeries']) == 4
          and all(pt['sigmaY_ua'] > 0
                  for pt in fig7a['paperSeries'])
          and flagship['rmsErrorUa'] < 0.46,
          f'flagship={flagship}')
    vxo = build_figure('fc10-vxo-vs-lg')
    resid_3um = next(r for r in vxo['residuals']
                     if r['anchor'] == 'fc10-vxo-lg3000')
    check('figures: the vxo-vs-Lg replica PLOTS the out-of-domain '
          '3 um anchor and its ~-40% misfit — the domain edge is '
          'visible, not hidden',
          vxo['ok'] and resid_3um['fractional'] < -0.2
          and vxo['axes']['x']['scale'] == 'log',
          f'resid={resid_3um}')
    cgg_fig = build_figure('vs1-fig9-cgg')
    cgg_ys = [pt['y'] for pt in cgg_fig['modelSeries'][0]['points']]
    check('figures: the Fig.9 entry is honestly MODEL-ONLY '
          '(paper curve not digitized, said in limits) and its '
          'curve shows the pinned peak-then-decline shape',
          cgg_fig['status'] == 'model-only'
          and not cgg_fig['paperSeries']
          and any('MODEL-ONLY' in lim for lim in cgg_fig['limits'])
          and max(cgg_ys) > cgg_ys[-1],
          f'cgg range={min(cgg_ys)}..{max(cgg_ys)}')
    from cntfet.cnt_figures import figure_points
    pts = figure_points('vs1-fig7a')
    dot_rows = [r for r in pts['rows'] if r['style'] == 'dot']
    line_rows = [r for r in pts['rows'] if r['style'] == 'lineY']
    check('figures: the LONG-FORM points endpoint feeds the '
          'original graphs design — paper rows are dots carrying '
          'the error interval (y_lo/y_hi), model rows are lines, '
          'and the columns match the seeded GraphDefinition '
          'dimensions exactly',
          pts.get('ok') and dot_rows and line_rows
          and all(r['y_lo'] is not None and r['y_hi'] > r['y']
                  for r in dot_rows)
          and all(r['y_lo'] is None for r in line_rows)
          and set(dot_rows[0]) == {'series', 'style', 'dash',
                                   'x', 'y', 'y_lo', 'y_hi'},
          f'rows={len(pts.get("rows", []))}')
    refusal = build_figure('fiori05-transfer')
    missing = build_figure('no-such-figure')
    check('figures: a refusing figure returns its refusal '
          'verbatim (not ok), and an unknown id points at the '
          'registry',
          not refusal.get('ok')
          and refusal['status'] == 'refusing'
          and 'not digitized' in refusal['refusal']
          and not missing.get('ok')
          and 'registry' in missing['error'])

    # ---- citations linkage (Dustin 2026-08-21) --------------------
    from cntfet.cnt_citations import citations_report
    from cntfet.cnt_reference_papers import (
        PAPERS, SEED_REFERENCE_ANCHORS,
    )
    anchor_names = {getattr(r, 'name', '') for r in
                    mgr.objectTables['CNTCalibrationAnchor'].values()}
    check('papers: both supplied papers seeded as cited anchor '
          'rows (FIO05 NEGF-oracle + HIL19 system precedent), '
          'each with a refusal row for undigitized curves',
          {'fio05-device-d09', 'fio05-ioff-vs-itrs',
           'fio05-curves', 'hil19-cnfet-count',
           'hil19-cell-library'} <= anchor_names
          and all(s['doi'] for s in SEED_REFERENCE_ANCHORS))
    check('papers: license buckets recorded WITH the papers '
          '(both cite+link+values, PDFs off-git)',
          all('cite+link+values' in p['license_bucket']
              for p in PAPERS.values()))
    cites = citations_report(mgr)
    by_tag = {c['tag']: c for c in cites['citations']}
    check('citations: every paper tag resolves to a full '
          'citation + DOI and the linkage map names its rows '
          '(source -> constants/anchors/parameters)',
          cites['ok']
          and by_tag['[VS1]']['linkCount'] > 5
          and by_tag['[FC10]']['linkCount'] >= 4
          and by_tag['[HIL19]']['linkCount'] >= 8
          and by_tag['[FIO05]']['linkCount'] >= 6
          and 'cnt-aligned-s1-vxo_m_per_s'
          in by_tag['[VS1]']['linkedBy']['parameters'])
    check('citations: the honesty surface is clean — no unlinked '
          'anchors, no unlinked literature-sourced parameters',
          not cites['unlinked']['anchors']
          and not cites['unlinked']['parameters'],
          f"unlinked={cites['unlinked']}")

    # ---- /display/cntfet page seed --------------------------------
    from cntfet.cnt_pages_seed import SEED_CNTFET_PAGE_DISPLAYS
    page = SEED_CNTFET_PAGE_DISPLAYS[0]
    page_def = json.loads(page['definition'])
    page_components = [item['componentProps']['componentName']
                       for row in page_def['rows']
                       for item in row['items']]
    check('page: /display/cntfet seeds valid rows using only the '
          'registered generic components — figure panels ride '
          'the ORIGINAL graphs design (named-graph-panel over '
          'seeded GraphDefinition rows), not a bespoke chart',
          page['isPage'] and page['pageRoute'] == 'cntfet'
          and set(page_components) <= {'class-rows-table',
                                       'api-json-panel',
                                       'named-graph-panel'}
          and page_components.count('named-graph-panel') == 3
          and len(page_components) == 10)
    from cntfet.cnt_figures import SEED_CNTFET_FIGURE_GRAPHS
    graph_names = {g['name'] for g in SEED_CNTFET_FIGURE_GRAPHS}
    panel_refs = {item['componentProps']['inputs']['graphName']
                  for row in page_def['rows']
                  for item in row['items']
                  if item['componentProps']['componentName']
                  == 'named-graph-panel'}
    check('page: every figure panel names a SEEDED GraphDefinition '
          'row, and every seed round-trips the Graphs editor '
          'shape (wrapped graphConfig with the long-form '
          'series/style/error dimensions)',
          panel_refs <= graph_names
          and all(
              json.loads(g['definition'])['graphConfig']
              ['seriesDimension'] == 'series'
              and json.loads(g['definition'])['graphConfig']
              ['styleDimension'] == 'style'
              and json.loads(g['definition'])['graphConfig']
              ['errorLoDimension'] == 'y_lo'
              for g in SEED_CNTFET_FIGURE_GRAPHS),
          f'panels={panel_refs}, graphs={graph_names}')

    # ---- S3: process objects + Monte Carlo ------------------------
    from cntfet.cnt_montecarlo import monte_carlo
    mc_fac = _row_factory(mgr, 'CNTFETMonteCarloRun')
    rep_mc = monte_carlo(mgr, device, sample_count=40, seed=11,
                         result_factory=mc_fac)
    check('S3: MC samples the bound process set — yield fraction, '
          'population quantiles, kills counted, dominant '
          'limitation named',
          rep_mc['ok']
          and 0.0 < rep_mc['yield']['functionalFraction'] <= 1.0
          and rep_mc['population']['ion_a'] is not None
          and rep_mc['population']['rc_ohm']['sigma'] > 0
          and rep_mc['dominantLimitation'] != '')
    check('S3: prior-flagged rows are LISTED — a population built '
          'on engineering priors says so',
          len(rep_mc['priorFlagged']) >= 4
          and 'prior' in rep_mc['honesty'])
    rep_mc2 = monte_carlo(mgr, device, sample_count=40, seed=11,
                          result_factory=mc_fac)
    check('S3: deterministic under seed (reproducible rows)',
          rep_mc2['yield'] == rep_mc['yield'])
    regime_keep = device.manufacturing_regime
    device.manufacturing_regime = 'coarse_alignment'
    rep_bad = monte_carlo(mgr, device, result_factory=mc_fac)
    check('S3: regime mismatch REFUSES (D6 — a line cannot '
          'fabricate outside its regime)',
          not rep_bad['ok'] and 'regime' in rep_bad['refusal'])
    device.manufacturing_regime = regime_keep
    ps_keep = device.process_set
    device.process_set = ''
    rep_bad = monte_carlo(mgr, device, result_factory=mc_fac)
    check('S3: no bound process set REFUSES (distributions are '
          'the point)',
          not rep_bad['ok'] and 'process_set' in rep_bad['refusal'])
    device.process_set = ps_keep

    # ---- S4a: polarity + inverter ---------------------------------
    p_p = {**p, 'ptype': 1}
    i_n = vs.vs_terminal_current(0.5, 0.4, p)['id_a']
    i_p = vs.vs_terminal_current(-0.5, -0.4, p_p)['id_a']
    check('S4a: the p-twin is the EXACT mirror (r2 polarity '
          'transform, [VS1] premise ii)',
          abs((i_n + i_p) / i_n) < 1e-12)
    check('S4a: the model card carries ptype (both implementations '
          'share the revision)',
          'ptype' in osdi._model_card(p_p)[0]
          and p['equation_revision'] == 'cntfet-vs-s1-r3')

    # ---- S4b: eq.(11) charge model --------------------------------
    from cntfet.cnt_charge import cgg_f, cqinf_f_per_m
    extras = {'cinvb_f_per_m': p['cinvb_f_per_m'],
              'vtb_v': p['vtb_v']}
    check('S4b: charge parameters derive from the paper forms '
          '(Cqinf asymptote, Cinvb series, Vtb = 0.7 Eg + 0.13)',
          cqinf_f_per_m() > 0
          and 0 < p['cinvb_f_per_m'] < p['cinv_f_per_m'] * 2
          and abs(p['vtb_v'] - (0.7 * eg + 0.13)) < 1e-9
          and 'cinvb' in osdi._model_card(p)[0])
    cggs = [cgg_f(vg, 0.0, p, extras)
            for vg in (0.0, 0.2, 0.4, 0.8, 1.3)]
    peak = max(cggs)
    check('S4b: Cgg rises to a peak then DECLINES at high Vgs — '
          'the [VS1] Fig.9 quantum-capacitance signature, from '
          'eq.(11) alone',
          cggs[0] < 1e-19 and peak == max(cggs[1:4])
          and cggs[-1] < 0.95 * peak,
          f'cggs={cggs}')

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
        rep_eq_p = osdi.equivalence_regression(
            {'p-type': p_p}, vg_list=[0.0, -0.3, -0.6],
            vd_list=[-0.05, -0.2, -0.35, -0.5],
            keep_bundle=False)
        check('S4a: the p-twin passes the SAME equivalence '
              'regression over the negative-bias grid',
              rep_eq_p.get('ok')
              and rep_eq_p['verdict'] == 'EQUIVALENT')
        from cntfet.cnt_inverter import run_inverter_vtc
        inv = run_inverter_vtc(
            mgr, device, result_factory=fac_res)
        m_inv = inv.get('metrics', {})
        check('S4a: the complementary inverter INVERTS in ngspice '
              '— VM ~ VDD/2, gain well past unity, near-full '
              'swing, both noise margins recorded',
              inv.get('ok') and inv['verdict'] == 'inverter-works'
              and abs(m_inv['vm_v'] - 0.3) < 0.05
              and m_inv['peakGain'] < -5.0
              and m_inv['swing_v'] > 0.57
              and m_inv['nml_v'] and m_inv['nmh_v'],
              f'metrics={m_inv}')
        from cntfet.cnt_cells import run_cell_battery
        battery = run_cell_battery(mgr, device,
                                   result_factory=fac_res)
        cell_verdicts = {k: v.get('verdict')
                         for k, v in battery.get('cells',
                                                 {}).items()}
        check('S4c: the D10 minimal cell set is DEMONSTRATED — '
              'NAND2 truth table, BUF follow, TG-DFF edge-capture '
              '+ hold, all through the OSDI card (truncation '
              'guard armed)',
              battery.get('ok')
              and battery['verdict'] == 'cell-set-demonstrated'
              and cell_verdicts == {'nand2': 'works',
                                    'nor2': 'works',
                                    'buf': 'works',
                                    'dff': 'works'},
              f'battery={cell_verdicts or battery}')
        from cntfet.cnt_ring_oscillator import run_ring_oscillator
        ro = run_ring_oscillator(mgr, device,
                                 result_factory=fac_res)
        m_ro = ro.get('metrics', {})
        check('S4b: the 5-stage ring OSCILLATES in transient '
              '(eq.(11) charge makes dynamics possible) — '
              'frequency in the intrinsic band, honesty labels '
              'riding the result',
              ro.get('ok') and ro['verdict'] == 'oscillates'
              and 1e9 < m_ro['frequency_hz'] < 1e14
              and m_ro['stage_delay_s'] > 0
              and any('INTRINSIC' in h for h in ro['honesty']),
              f'metrics={m_ro}')
    else:
        print('SKIP: S1d/S4a OSDI legs — openvaf/ngspice not '
              'available on this host (capability endpoint reports '
              'the same refusal)')

    # ---- [VS2] extrinsics -----------------------------------------
    from cntfet.cnt_extrinsics import (
        btbt_current_a, contact_rc_ohm, rext_ohm, sdt_current_a,
        vs_full_current,
    )
    _rc, rc_detail = contact_rc_ohm(12.9, bs.eg_ev(1.2))
    check('[VS2]: the Rc(Lc,d) transmission-line model reproduces '
          'the paper pin — 2Rc ~ 70 kOhm at d=1.2, Lc=12.9 nm '
          '(Pd/p, phi_b -0.045 eV, gc 2.0 uS/nm)',
          65e3 < rc_detail['two_rc_ohm'] < 78e3
          and abs(rc_detail['phi_b_ev'] + 0.045) < 1e-3
          and abs(rc_detail['gc_s_per_nm'] - 2.0e-6) < 0.1e-6,
          f'detail={rc_detail}')
    check('[VS2]: Rc physics directions — longer contacts cheaper, '
          'smaller diameter exponentially worse; Rext scales with '
          'Lext',
          contact_rc_ohm(300.0, bs.eg_ev(1.2))[0]
          < contact_rc_ohm(12.9, bs.eg_ev(1.2))[0]
          and contact_rc_ohm(12.9, bs.eg_ev(1.0))[0]
          > 5.0 * contact_rc_ohm(12.9, bs.eg_ev(1.2))[0]
          and rext_ohm(20, 1.2, 1.0) > rext_ohm(10, 1.2, 1.0) > 0)
    dev15 = {'eg_ev': eg, 'lg_nm': 15.0, 'lof_nm': 1.0,
             'lambda_nm': sce['lambda_nm'], 'efsd_ev': 0.1,
             'vt0_v': 0.3, 'temperature_k': 300.0}
    sdt15 = sdt_current_a(0.0, 0.6, dev15)
    sdt5 = sdt_current_a(0.0, 0.6, {**dev15, 'lg_nm': 5.0})
    check('[VS2]: S/D tunneling is exponential in Lg — small at '
          '15 nm, dominant-scale at 5 nm (the paper\'s sub-10-nm '
          'warning)',
          0.0 < sdt15 < 1e-9 and sdt5 > 100.0 * sdt15,
          f'sdt15={sdt15}, sdt5={sdt5}')
    check('[VS2]: BTBT vanishes NATURALLY below Vds = Eg (D12 — '
          'no switch) and turns on above',
          btbt_current_a(0.0, 0.6, dev15) == 0.0
          and btbt_current_a(0.0, 0.9, dev15) > 0.0)
    full = vs_full_current(0.0, 0.6, p, dev15)
    check('[VS2]: VS_FULL is ADDITIVE with the decomposition '
          'reported (total = thermionic + SDT + BTBT) and the '
          'twin honesty note riding along',
          abs(full['id_a'] - (full['thermionic_a'] + full['sdt_a']
                              + full['btbt_a'])) < 1e-18
          and full['id_a'] > full['thermionic_a']
          and 'thermionic' in full['twin_note'])
    rep_full = cd.run_iv(mgr, device, engine='vs',
                         profile='VS_FULL',
                         vg_list=[0.0, 0.6], vd_list=[0.05, 0.6],
                         result_factory=fac_res)
    check('[VS2]: {action: iv, profile: VS_FULL} runs from the '
          'device rows with per-point decomposition',
          rep_full['ok'] and rep_full['fidelity'] == 'VS_FULL'
          and all('sdt_a' in pt for pt in rep_full['points']))

    # ---- S5: characterization (tools leg) -------------------------
    if openvaf_path and ngspice_path:
        from cntfet.cnt_characterization import (
            characterize_inverter,
        )
        mgr.objectTables['CellCharacterizationRun'] = {}
        char = characterize_inverter(
            mgr, device,
            result_factory=_row_factory(mgr,
                                        'CellCharacterizationRun'))
        check('S5: the own-loop executor characterizes INV over '
              'the sparse grid — monotone tables, Liberty '
              'emitted, measurement definitions recorded, STA '
              'gate honestly reported',
              char.get('ok') and char['verdict'] == 'characterized'
              and char['libertyBytes'] > 500
              and char['definitions']['delay']
              and ('accepted' in char['staGate']
                   or 'refusal' in char['staGate']),
              f"char={char.get('verdict')}, "
              f"failures={char.get('failures')}")

        # ---- S4d/S5b: cell library variants + D11 ------------------
        from cntfet.cnt_cell_library import (
            CELL_LIBRARY, DRIVES, SEED_CNT_CELLS, d11_crosscheck,
            characterize_cells, fet_count, subckt_text,
        )
        x1 = subckt_text('cnand2', 1)
        x2 = subckt_text('cnand2', 2)
        check('S4d: variants are GENERATED — x2 has exactly twice '
              'the x1 device lines, standin caps scale, and the '
              'seed rows cover every (cell, drive)',
              x2.count('cntn') == 2 * x1.count('cntn')
              and x2.count('cntp') == 2 * x1.count('cntp')
              and len(SEED_CNT_CELLS)
              == len(CELL_LIBRARY) * len(DRIVES)
              and fet_count('cbuf', 1) == 4
              and fet_count('cnor2', 2) == 8)
        nor2 = CELL_LIBRARY['cnor2']
        check('S4d: NOR2 is the NAND2 mirror — series p-stack '
              'through the mid node, parallel n to ground, '
              'non-controlling tie 0',
              ('p', 'midp', 'A', 'vddn') in nor2['devices']
              and ('n', 'Y', 'A', '0') in nor2['devices']
              and ('n', 'Y', 'B', '0') in nor2['devices']
              and nor2['noncontrolling'] == 0)
        lib = characterize_cells(
            mgr, device, cells=['cinv', 'cnor2'], drives=(1, 2),
            slews_s=None, loads_f=None,
            result_factory=_row_factory(
                mgr, 'CellCharacterizationRun'))
        lib_names = {c['libertyName'] for c in lib.get('cells', [])}
        nor2_arcs = next((c['arcs'] for c in lib.get('cells', [])
                          if c['libertyName'] == 'NOR2X1'), [])
        check('S5b: the sweep characterizes VARIANTS across cells '
              '— INVX1/INVX2/NOR2X1/NOR2X2 in ONE Liberty, both '
              'NOR2 input arcs measured (non-controlling tie), '
              'every arc monotone in load, zero failed points',
              lib.get('ok')
              and lib_names == {'INVX1', 'INVX2', 'NOR2X1',
                                'NOR2X2'}
              and nor2_arcs == ['A', 'B']
              and all(m['monotoneInLoad']
                      for m in lib['monotone'])
              and not lib['failures'],
              f'lib={lib_names}, failures={lib.get("failures")}')
        check('S5b: the multi-cell staGate reflects the live '
              'binary — accepted when sta exists, refusing with '
              'a reason otherwise (never a silent middle)',
              (lib['staGate'].get('ran')
               and lib['staGate'].get('accepted'))
              or (not lib['staGate'].get('ran')
                  and lib['staGate'].get('refusal')),
              f'staGate={lib.get("staGate")}')
        d11 = d11_crosscheck(mgr, device)
        if d11.get('ok'):
            check('D11: the MANDATORY SPICE-vs-STA composed-path '
                  'cross-check CLOSES — the same INV chain timed '
                  'by transient truth and by the Liberty '
                  'abstraction, within the stated tolerance',
                  d11['verdict'] == 'D11-CROSSCHECK-PASS'
                  and abs(d11['fractionalError'])
                  < d11['tolerance'],
                  f'd11={d11}')
        else:
            check('D11: without OpenSTA the cross-check REFUSES '
                  'with the install path named (open box stays '
                  'visibly open)',
                  'refusal' in d11 and 'OpenSTA' in d11['refusal'],
                  f'd11={d11}')

    # ---- F3: kwant oracle (venv leg) ------------------------------
    from cntfet.cnt_kwant import f3_oracle, find_kwant_python, \
        sanity as kwant_sanity
    kwant_python, _kwhy = find_kwant_python()
    if kwant_python:
        san = kwant_sanity(kwant_python)
        check('F3: the atomistic tube pins its own physics — TB '
              'gap == compact-model Eg by construction, T == 2 '
              'valleys above the edge, 0 in the gap',
              san.get('ok')
              and abs(san['eg_tb_ev'] - eg) < 1e-9
              and abs(san['t_above_edge'] - 2.0) < 1e-6
              and san['t_midgap'] == 0.0, f'sanity={san}')
        f3 = f3_oracle(mgr, device, energy_points=40,
                       bias_points=[{'vg_v': 0.0, 'vd_v': 0.6},
                                    {'vg_v': 0.6, 'vd_v': 0.6}],
                       result_factory=fac_res)
        sub = f3['comparison'][0]
        on = f3['comparison'][1]
        check('F3: the triangle third vertex — subthreshold F3 '
              'EXCEEDS thermionic-only F2 (S/D tunneling is '
              'real) and all three fidelities agree within 2x '
              'at on-state',
              f3.get('ok')
              and sub['f3_negf_a'] > 2.0 * sub['f2_tob_a']
              and 0.5 < on['f3_negf_a'] / on['f2_tob_a'] < 2.0
              and 0.5 < on['f3_negf_a'] / on['f1_vs_intrinsic_a']
              < 2.0,
              f'comparison={f3.get("comparison")}')

        # ---- D13: self-consistent Poisson -------------------------
        from cntfet.cnt_kwant import poisson_pin
        pin = poisson_pin(mgr, device)
        check('D13 pin: the discrete Poisson solve at zero charge '
              'reproduces the analytic eq.(5) profile to '
              'discretization error — the fixed potential IS the '
              'SCF Laplace limit (this pin caught the pre-D13 '
              'a1/a2 mirror swap)',
              pin.get('ok') and pin['max_dev_ev'] < 5e-4,
              f'pin={pin}')
        f3s = f3_oracle(mgr, device, energy_points=40,
                        bias_points=[{'vg_v': 0.0, 'vd_v': 0.6},
                                     {'vg_v': 0.6, 'vd_v': 0.6}],
                        result_factory=fac_res,
                        scf={'max_iter': 12, 'tol_ev': 5e-3,
                             'charge_energy_points': 48})
        subs_ = f3s['comparison'][0]
        ons_ = f3s['comparison'][1]
        check('D13 SCF: both points converge (continuation from '
              'point to point), the wave-function charge '
              'normalization pins against kwant.ldos at machine '
              'precision, and no unconverged point is silently '
              'absorbed',
              f3s.get('ok')
              and subs_['scfConverged'] and ons_['scfConverged']
              and subs_['ldosPinRel'] < 1e-9
              and 'unconverged' not in f3s
              and f3s['engine'].endswith('1D Poisson)'),
              f'sub={subs_}, on={ons_}')
        check('D13 SCF physics: channel charge RAISES the barrier '
              '(deltaEcTop > 0 both points) — in deep '
              'subthreshold that visibly LOWERS the current vs '
              'the fixed-potential run; at on-state quantum-'
              'capacitance feedback self-limits the shift, so '
              'the current stays within 1.5x of fixed (first '
              'run: within 0.3%)',
              subs_['deltaEcTop_ev'] > 0.005
              and ons_['deltaEcTop_ev'] > 0.0
              and subs_['f3_negf_a'] < sub['f3_negf_a']
              and 0.67 < ons_['f3_negf_a'] / on['f3_negf_a']
              < 1.5,
              f'scf sub={subs_["f3_negf_a"]:.3e} vs '
              f'fixed {sub["f3_negf_a"]:.3e}; '
              f'scf on={ons_["f3_negf_a"]:.3e} vs '
              f'fixed {on["f3_negf_a"]:.3e}')
        scf_rows = [r for r in mgr.objectTables[
            'CNTFETSimResult'].values()
            if getattr(r, 'physics_fidelity', '') == 'F3_NEGF_SCF']
        check('D13 SCF: the result row records its OWN fidelity '
              '(F3_NEGF_SCF), its scf knobs, and the converged '
              'potential profile — a fidelity is never a silent '
              'change to F3',
              len(scf_rows) == 1
              and 'f3scf' in scf_rows[0].name
              and json.loads(scf_rows[0].metrics_json
                             ).get('profiles'),
              f'rows={[getattr(r, "name", "?") for r in scf_rows]}')
        d13fig = build_figure('d13-scf-profile', manager=mgr)
        scf_first = next(s for s in d13fig.get('modelSeries', [])
                         if '(SCF)' in s.get('label', ''))
        lap_first = next(s for s in d13fig.get('modelSeries', [])
                         if 'Laplace' in s.get('label', ''))
        check('figures: the row-backed D13 profile chart shows '
              'the EXPECTED characteristic — the converged SCF '
              'barrier tops its dashed Laplace seed (coherence '
              'is visible in the chart data, not just asserted '
              'in a number); managerless access refuses',
              d13fig.get('ok')
              and max(p['y'] for p in scf_first['points'])
              > max(p['y'] for p in lap_first['points'])
              and lap_first.get('dashed')
              and not build_figure('d13-scf-profile').get('ok'),
              f'd13fig={d13fig.get("limits", d13fig)}')
    else:
        print('SKIP: F3 kwant legs — no kwant venv on this host '
              '(capability endpoint reports the same refusal)')

    passed = sum(1 for _, ok in _results if ok)
    print(f'\n{passed}/{len(_results)} checks passed')
    return 0 if passed == len(_results) else 1


if __name__ == '__main__':
    sys.exit(main())
