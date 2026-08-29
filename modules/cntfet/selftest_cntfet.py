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
import math
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


def seq_lib(seq):
    try:
        return open(seq['libertyPath']).read()
    except Exception:
        return ''


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
                                       'named-graph-panel',
                                       'evidence-browser'}   # evidence
          and page_components.count('named-graph-panel') == 10
          and len(page_components) == 22)   # + evidence-browser
    from cntfet.cnt_device_viz import SEED_CNT_DEVICE_GRAPHS
    from cntfet.cnt_figures import SEED_CNTFET_FIGURE_GRAPHS
    graph_names = ({g['name'] for g in SEED_CNTFET_FIGURE_GRAPHS}
                   | {g['name'] for g in SEED_CNT_DEVICE_GRAPHS})
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

    # ---- fet-viz: per-device curves + characterization ------------
    from cntfet.cnt_device_viz import (
        curve_rows_from_fn, device_characterization,
        device_curve_points,
    )
    fake_id = lambda vg, vd: 1e-6 * vg * vd + 1e-12
    t_rows = curve_rows_from_fn(fake_id, 'transfer')
    o_rows = curve_rows_from_fn(fake_id, 'output')
    check('fet-viz: curve families are long-form rows matching '
          'the seeded graph dimensions (series/style/x/y), Id in '
          'uA, 3 drain series x 31-pt sweep / 5 gate series',
          len(t_rows) == 3 * 31 and len(o_rows) == 5 * 31
          and {r['series'] for r in t_rows}
          == {'Vd = 0.05 V', 'Vd = 0.3 V', 'Vd = 0.6 V'}
          and all(set(r) == {'series', 'style', 'dash', 'x', 'y'}
                  for r in t_rows)
          and abs(t_rows[-1]['y'] - 0.6 * 0.6 - 1e-6 * 1e6 * 0)
          < 0.5)
    live_curves = device_curve_points(mgr, device.name)
    live_char = device_characterization(mgr, device.name)
    check('fet-viz: the DERIVED seed device serves transfer '
          'points + a characterization whose every value carries '
          'the F1 fidelity string and whose refusals are '
          'verbatim (none expected on S1)',
          live_curves['ok'] and len(live_curves['rows']) == 93
          and 'F1' in live_curves['fidelity']
          and live_char['ok']
          and live_char['metrics']['on_off_ratio'] > 1e3
          and live_char['metrics']['refusals'] == {},
          f'curves={live_curves.get("error")}, '
          f'char={live_char.get("error")}')
    mgr.objectTables['AlignedCNTFETDevice']['underived-x'] = \
        types.SimpleNamespace(name='underived-x', polarity='n',
                              derived_at='')
    check('fet-viz: refusals name the affordance — unknown '
          'device, underived device, unknown curve, managerless',
          not device_curve_points(mgr, 'no-such-device')['ok']
          and 'no device'
          in device_curve_points(mgr, 'no-such-device')['error']
          and 'derive' in device_curve_points(
              mgr, 'underived-x')['error']
          and 'unknown curve' in device_curve_points(
              mgr, device.name, curve='sideways')['error']
          and not device_characterization(None, 'x')['ok'])

    # ---- fi-0: operating states + qualifying criteria ------------
    from cntfet.cnt_device_viz import device_model
    from cntfet.cnt_states import (
        SEED_FET_STATES, device_states_report, frame_at,
        state_at_bias, state_band_rows, transfer_boundaries,
        transitions_on_sweep,
    )
    _id, p_dev, dev_row, _ref = device_model(mgr, device.name)
    b = transfer_boundaries(p_dev, 0.6)
    f0 = frame_at(p_dev, 0.0, 0.6)
    check('fi-0: states are DATA — 5 seeded rows, each with '
          'criteria_json predicates over the frame and a governing '
          'equation; boundaries ordered Vt < Vt+Vov_min with Vov_min '
          '= vov_decades·SS from the model\'s own n_ss·φt·ln10',
          len(SEED_FET_STATES) == 5
          and all(json.loads(s['criteria_json'])
                  and s['governing_equation']
                  for s in SEED_FET_STATES)
          and b[0]['x'] < b[1]['x']
          and abs((b[1]['x'] - b[0]['x'])
                  - 3.0 * f0['ss_v_per_dec']) < 1e-9
          and 0.0 < f0['ss_v_per_dec'] < 0.2,
          f'boundaries={b}, ss={f0["ss_v_per_dec"]}')
    s_off = state_at_bias(p_dev, 0.0, 0.6)
    s_lin = state_at_bias(p_dev, 0.6, 0.05)
    s_sat = state_at_bias(p_dev, 0.6, 0.6)
    check('fi-0: the S1 device qualifies as off at (0, 0.6), '
          'on-linear at (0.6, 0.05) and on-saturation at (0.6, 0.6) '
          '— every evaluation lists each inequality with both '
          'numbers and its margin',
          s_off['state'] == 'off' and s_lin['state'] == 'on-linear'
          and s_sat['state'] == 'on-saturation'
          and all('margin' in c and 'lhs_value' in c
                  for e in s_sat['evaluations'] for c in e['criteria']),
          f'off={s_off["state"]}, lin={s_lin["state"]}, '
          f'sat={s_sat["state"]}, '
          f'frame_sat={ {k: round(v, 4) for k, v in s_sat["frame"].items() if isinstance(v, float)} }')
    ev_r = transitions_on_sweep(p_dev, 0.6, 'rising')
    ev_f = transitions_on_sweep(p_dev, 0.6, 'falling')
    check('fi-0: a rising Vgs sweep walks off -> transition-on -> '
          'on-saturation and names the criterion that flipped at '
          'each event; the falling sweep mirrors it through '
          'transition-off (F1 is hysteresis-free, so bounds match)',
          [e['to'] for e in ev_r]
          == ['off', 'transition-on', 'on-saturation']
          and all(e['flipped'] for e in ev_r[1:])
          and [e['to'] for e in ev_f]
          == ['on-saturation', 'transition-off', 'off']
          and abs(ev_r[1]['vgs'] - ev_f[2]['vgs']) <= 0.005 + 1e-9,
          f'rising={[(e["vgs"], e["to"]) for e in ev_r]}, '
          f'falling={[(e["vgs"], e["to"]) for e in ev_f]}')
    knob = state_at_bias(p_dev, b[1]['x'] - 0.01, 0.6,
                         knobs={'vov_decades': 1.0})
    tb = frame_at(p_dev, 0.6, 0.6, knobs={'vdsat_criterion':
                                          'textbook'})
    check('fi-0: knobs are explicit and change the verdict — '
          'vov_decades=1 turns a near-threshold point "on"; '
          'vdsat_criterion=textbook swaps Vdsat for Vgs-Vt and '
          'echoes the knob in the frame',
          knob['state'].startswith('on')
          and knob['knobs']['vov_decades'] == 1.0
          and abs(tb['vdsat'] - tb['vdsat_textbook']) < 1e-12
          and tb['knobs']['vdsat_criterion'] == 'textbook')
    rep = device_states_report(p_dev, dev_row, vds_v=0.6, vgs_v=0.3)
    band = state_band_rows(p_dev, 0.6, 1e-3, 100.0)
    ts_rows = device_curve_points(mgr, device.name,
                                  curve='transfer-states')['rows']
    os_rows = device_curve_points(mgr, device.name,
                                  curve='output-states')['rows']
    check('fi-0: the /states payload carries definitions, '
          'boundaries, events, output Vdsat boundaries and the '
          'point; the transfer-states curve = the Id line + band '
          'rows (lo/hi) per state + guide rows at the boundaries; '
          'output-states adds the dashed Vdsat locus',
          rep['ok'] and len(rep['states']) == 5
          and rep['point']['state'] in ('transition-on', 'off',
                                        'on-saturation')
          and all(ob['x'] is not None
                  for ob in rep['output_boundaries'])
          and any(r['style'] == 'band' for r in band)
          and sum(1 for r in band if r['style'] == 'guide') == 2
          and len([r for r in ts_rows if r['style'] == 'line'])
          == 31
          and any(r['series'] == 'Vdsat locus' for r in os_rows),
          f'point={rep["point"]["state"]}, '
          f'ob={[ob["x"] for ob in rep["output_boundaries"]]}, '
          f'bands={sorted({r["series"] for r in band})}')
    check('fet-viz: device graph seeds round-trip the Graphs '
          'editor shape; transfer is log-Y (subthreshold decades '
          'visible)',
          {g['name'] for g in SEED_CNT_DEVICE_GRAPHS}
          == {'cnt-device-transfer', 'cnt-device-output',
              'cnt-device-transfer-states',
              'cnt-device-output-states',
              'cnt-device-score-terms',
              'cnt-device-transfer-envelope',
              'cnt-device-cell-scores', 'cnt-device-compare'}
          and json.loads(SEED_CNT_DEVICE_GRAPHS[0]['definition'])
          ['graphConfig']['options']['yType'] == 'log'
          and all(json.loads(g['definition'])['graphConfig']
                  ['seriesDimension'] == 'series'
                  for g in SEED_CNT_DEVICE_GRAPHS))

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

    # ---- fi-2: scoring by characteristic equations ----------------
    from cntfet.cnt_scoring import (
        FET_TERMS, SEED_FET_SCORE_CONCEPTS, SEED_FET_SCORE_TERMS,
        figures_of_merit, score_device, score_term_rows,
        seed_subjects_and_values,
    )
    sc = score_device(mgr, device.name)
    by_term = {t['term']: t for t in sc['terms']}
    check('fi-2: every FET term is a seeded ScoreTerm with an '
          'explicit min-max range, a stated equation and an ideal '
          'that is COMPUTED from the model frame (SS ideal = φt·ln10, '
          'on/off ceiling = Vdd/SS_ideal) — never typed',
          {t['name'] for t in SEED_FET_SCORE_TERMS} == set(FET_TERMS)
          and all(json.loads(t['normalization_json'])['method']
                  == 'min-max' for t in SEED_FET_SCORE_TERMS)
          and sc['ok'] and not sc['termsMissing']
          and abs(by_term['fet-ss']['ideal']
                  - p_dev['phit_v'] * math.log(10) * 1e3) < 1e-9
          and abs(by_term['fet-on-off-decades']['ideal']
                  - 0.6 / (p_dev['phit_v'] * math.log(10))) < 1e-9
          and all(0.0 <= t['normalized'] <= 1.0 for t in sc['terms']),
          f'missing={sc.get("termsMissing")}, '
          f'ideals={ {k: v.get("ideal") for k, v in by_term.items()} }')
    check('fi-2: the score is the generic weighted-mean (Σw·v/Σw, '
          'AGGREGATION_NOTE stamped) with every term carrying raw, '
          'ideal, distance and its applied normalization spec; the '
          'ideal table mirrors it',
          abs(sc['score'] - sum(t['weighted'] for t in sc['terms'])
              / sc['totalWeight']) < 1e-9
          and 'weighted-mean' in sc['aggregationNote']
          and all({'raw', 'ideal', 'distance', 'normalization',
                   'equation'} <= set(t) for t in sc['terms'])
          and len(sc['idealTable']) == len(FET_TERMS)
          and 0.0 < sc['score'] < 1.0,
          f'score={sc["score"]}')
    sc_cc = score_device(mgr, device.name,
                         {'vt_definition': 'constant-current'})
    check('fi-2: knobs are explicit and echoed — vt_definition '
          'swaps the model Vt(Vdd) for the 1 nA crossing (which '
          'sits at the Ioff level on S1, so the term drops); the '
          'frame carries both Vt definitions and the target window',
          sc['knobs']['vt_definition'] == 'model'
          and sc_cc['knobs']['vt_definition'] == 'constant-current'
          and sc_cc['frame']['vt_used_v'] == sc_cc['frame']['vt_cc_sat_v']
          and sc['frame']['vt_used_v'] == sc['frame']['vt_model_v']
          and sc['frame']['vt_window_v'][0] < sc['frame']['vt_target_v']
          < sc['frame']['vt_window_v'][1]
          and by_term['fet-vt-distance']['normalized']
          > {t['term']: t for t in sc_cc['terms']}
          ['fet-vt-distance']['normalized'])
    fom = figures_of_merit(mgr, device.name)
    device.figures_of_merit = fom   # the live property on real rows
    subjects, values = seed_subjects_and_values([device.name])
    mgr.objectTables['ScoreTerm'] = {}
    mgr.objectTables['ScoreContext'] = {}
    mgr.objectTables['ScoreSubject'] = {}
    mgr.objectTables['ContextualizedValue'] = {}
    mgr.objectTables['ScoreConcept'] = {}
    for table, seeds in (('ScoreTerm', SEED_FET_SCORE_TERMS),
                         ('ScoreSubject', subjects),
                         ('ContextualizedValue', values),
                         ('ScoreConcept', SEED_FET_SCORE_CONCEPTS)):
        for seed in seeds:
            _row_factory(mgr, table)(**seed)
    from scoring.scoring_engine import score_concept
    generic = score_concept(mgr, 'fet-switching-quality')
    gsub = generic['subjects'][0] if generic.get('ok') else {}
    check('fi-2: the GENERIC scoring engine scores the device through '
          'objectRef bindings into AlignedCNTFETDevice.figures_of_merit '
          '(no stored numbers) and lands on the SAME score as the '
          'device endpoint; an underived device answers the binding '
          'with a named refusal',
          generic.get('ok') and gsub.get('subject') == f'fet-{device.name}'
          and not gsub.get('termsMissing')
          and abs(gsub['initialScore'] - sc['score']) < 1e-6
          and 'refusal' in figures_of_merit(mgr, 'underived-x')
          and 'derive' in figures_of_merit(mgr, 'underived-x')['refusal'],
          f'generic={generic.get("error")}, sub={gsub}')
    rows_sc = score_term_rows(sc)
    check('fi-2: score-terms rows are long-form with a CATEGORICAL x '
          '(the term label), one dot per term and an hguide at 1.0 '
          '(the ideal) — config-rendered, no chart code',
          sum(1 for r in rows_sc if r['style'] == 'dot')
          == len(FET_TERMS)
          and all(isinstance(r['x'], str) for r in rows_sc
                  if r['style'] == 'dot')
          and [r for r in rows_sc if r['style'] == 'hguide'][0]['y']
          == 1.0)

    # ---- fi-3: best / worst case from the stochastic definitions --
    sc_mc = rep_mc['score']
    env = rep_mc['envelope']
    check('fi-3: the MC run scores every FUNCTIONAL sample with the '
          'fi-2 terms — score quantiles, per-term spread, best/worst '
          'case carrying their sampled process values and a per-term '
          'attribution vs the nominal device (largest delta first)',
          sc_mc['worst']['score'] <= sc_mc['quantiles']['p05']
          <= sc_mc['quantiles']['p50'] <= sc_mc['quantiles']['p95']
          <= sc_mc['best']['score']
          and sc_mc['scoredSamples'] == rep_mc['yield']['functional']
          and set(sc_mc['best']['sampled']) >= {'d_nm', 'rc_ohm',
                                                'vt0_v', 'lg_eff_nm'}
          and sc_mc['worst']['movedMostBy'] in FET_TERMS
          and abs(sc_mc['worst']['attribution'][0]['deltaVsNominal'])
          >= abs(sc_mc['worst']['attribution'][-1]['deltaVsNominal'])
          and set(sc_mc['termSpread']) == set(FET_TERMS)
          and rep_mc['population']['score']['p50'] == sc_mc['quantiles']['p50'],
          f'score={sc_mc}')
    check('fi-3: the Id(Vg) envelope brackets the nominal curve '
          'point-for-point on the viz grid (min ≤ p05 ≤ p50 ≤ p95 ≤ max)',
          env is not None and len(env['vgs']) == 31
          and all(env['min'][i] <= env['p05'][i] <= env['p50'][i]
                  <= env['p95'][i] <= env['max'][i]
                  for i in range(31))
          and env['samples'] == rep_mc['yield']['functional'])
    env_rows = device_curve_points(mgr, device.name,
                                   curve='transfer-envelope',
                                   samples=30, seed=3)
    st_rows = device_curve_points(mgr, device.name,
                                  curve='score-terms', samples=30,
                                  seed=3)
    check('fi-3: transfer-envelope = nominal line + two band series '
          '(p05–p95, min–max); score-terms with samples>0 adds the '
          'MC interval (lo/hi) and best/worst-case dots; sample '
          'count is a knob',
          env_rows['ok']
          and {r['series'] for r in env_rows['rows']
               if r['style'] == 'band'}
          == {'MC p05–p95', 'MC min–max'}
          and sum(1 for r in env_rows['rows'] if r['style'] == 'line')
          == 31
          and st_rows['ok']
          and any('lo' in r for r in st_rows['rows']
                  if r['series'] == 'nominal')
          and {'best case (MC)', 'worst case (MC)'}
          <= {r['series'] for r in st_rows['rows']},
          f'env={env_rows.get("error")}, st={st_rows.get("error")}')

    # ---- fi-4: the FET-validity gate + competitive ranking --------
    from cntfet.cnt_scoring import fet_validity
    from cntfet.cnt_compare import (
        compare_devices, compare_rows, score_pages,
    )
    val = fet_validity(_id, p_dev)
    check('fi-4 gate: the S1 device PROVES it is a FET — all five '
          'characteristic-equation proofs pass with their evidence '
          '(states traversed, gate modulation, monotone Id(Vg), SS '
          'measurable, output saturation) and the score stands',
          val['valid'] and len(val['checks']) == 5
          and all(c['evidence'] is not None for c in val['checks'])
          and sc['validity']['valid'] and sc['score'] > 0,
          f'failed={val["failed"]}')
    dead_p = {**p_dev, 'vt0_v': 3.0}   # threshold far above the supply
    dead_fn = lambda vg, vd: vs.vs_terminal_current(vg, vd, dead_p)['id_a']
    val_dead = fet_validity(dead_fn, dead_p)
    flat_fn = lambda vg, vd: 1e-6
    val_flat = fet_validity(flat_fn, p_dev)
    check('fi-4 gate: a model whose Vt sits above the supply never '
          'switches (states not traversed → invalid); a gate-blind '
          'constant current fails modulation + SS (invalid) — each '
          'names the failed proofs',
          not val_dead['valid'] and 'states-traversed' in val_dead['failed']
          and not val_flat['valid']
          and {'gate-modulation', 'subthreshold-measurable'}
          <= set(val_flat['failed']),
          f'dead={val_dead["failed"]}, flat={val_flat["failed"]}')
    lg30 = cd.get_row(mgr, 'AlignedCNTFETDevice', 'cnt-aligned-s1-lg30')
    mgr.objectTables['AlignedCNTFETDevice'].pop('underived-x', None)
    cmp0 = compare_devices(mgr, device.name)
    unproven = next(r for r in cmp0['ranking'] if r['device'] == lg30.name)
    check('fi-4: the seeded Lg=30 comparator is UNDERIVED → scores 0 '
          'as unproven and ranks last with the derive affordance '
          'named; S1 leads (levelized 100)',
          cmp0['ok'] and cmp0['leader'] == device.name
          and unproven['score'] == 0.0 and unproven['unproven']
          and 'derive' in unproven['reason']
          and all(r['score'] == 0.0 and r['unproven']
                  for r in cmp0['ranking'][1:])   # every comparator
          and cmp0['of'] == len(SEED_CNT_DEVICES)
          and cmp0['ranking'][0]['levelized'] == 100.0,
          f'cmp={[(r["device"], r["score"]) for r in cmp0["ranking"]]}')
    cd.derive_device(mgr, lg30, parameter_factory=pfac)
    cmp1 = compare_devices(mgr, lg30.name)
    sc30 = score_device(mgr, lg30.name)
    by30 = {t['term']: t for t in sc30['terms']}
    check('fi-4: once derived, Lg=30 nm is a valid FET and competes — '
          'better DIBL (longer channel), lower gm/G0 (lower v_xo); the '
          'focus device carries its rank, levelized score and per-term '
          'gap to the leader (most-negative first)',
          sc30['validity']['valid'] and sc30['score'] > 0
          and cmp1['ok'] and cmp1['of'] == len(SEED_CNT_DEVICES)
          and all(r['valid'] for r in cmp1['ranking']
                  if r['device'] in (device.name, lg30.name))
          and by30['fet-dibl']['raw'] < by_term['fet-dibl']['raw']
          and by30['fet-gm-over-g0']['raw'] < by_term['fet-gm-over-g0']['raw']
          and cmp1['focusRank'] in (1, 2)
          and len(cmp1['gapToLeader']) == len(FET_TERMS)
          and (cmp1['gapToLeader'][0]['delta']
               <= cmp1['gapToLeader'][-1]['delta']),
          f'lg30 score={sc30["score"]} s1={sc["score"]} '
          f'rank={cmp1.get("focusRank")} gap={cmp1.get("gapToLeader")}')
    c_rows = device_curve_points(mgr, device.name, curve='compare')
    pages = score_pages([d['name'] for d in SEED_CNT_DEVICES])
    page_defs = [json.loads(pg['definition']) for pg in pages]
    check('fi-4: compare rows put every device on a categorical x with '
          'the focus marked ◀ + hguide at 1.0; one scoring PAGE is '
          'seeded PER FET (its own route, per-KIND graphs pointed at '
          'its own paths, ranking + validity panels)',
          c_rows['ok']
          and {r['x'] for r in c_rows['rows'] if r['series'] == 'score'}
          >= {f'{device.name} ◀', lg30.name}
          and len({r['x'] for r in c_rows['rows']
                   if r['series'] == 'score'}) == len(SEED_CNT_DEVICES)
          and len(pages) == len(SEED_CNT_DEVICES)
          and all(pg['pageRoute'] == f'cntfet-score-{pg["name"][13:]}'
                  and pg['source_class'] == 'AlignedCNTFETDevice'
                  for pg in pages)
          and all(len(pd['rows']) == 5 for pd in page_defs)   # + proof + links rows
          and any(lg30.name in item['componentProps']['inputs']
                  .get('dataPath', '')
                  for pd in page_defs[1:] for row in pd['rows']
                  for item in row['items']),
          f'rows={sorted({r["x"] for r in c_rows["rows"] if r["x"]})}')

    # ---- fv-3: the characteristic registry + fv curve plug-ins -----
    from cntfet.cnt_characteristics import (
        SEED_FET_CHARACTERISTICS, characteristic_detail,
        characteristics_index,
    )
    from cntfet.cnt_device_viz import extra_curve_builders, extra_graph_seeds
    idx = characteristics_index(mgr, device.name)
    keys = [c['key'] for c in idx['characteristics']]
    detail = characteristic_detail(mgr, device.name, 'regime-map')
    bad = characteristic_detail(mgr, device.name, 'no-such')
    check('fv-3: the characteristic registry is DATA — ≥ 20 seeded '
          'rows across iv/switching/transport/fields/quality, each '
          'with a physics description, a performance meaning, an '
          'equation and ≥ 1 view; details resolve {device} into the '
          'device\'s own paths and never drop a view (unbuilt ones '
          'are named with their owning phase); unknown keys refuse',
          idx['ok'] and len(keys) >= 20 and len(set(keys)) == len(keys)
          and all(c['description'] and c['performance_meaning']
                  and c['equation'] and json.loads(c['views_json'])
                  for c in SEED_FET_CHARACTERISTICS)
          and detail['ok']
          and all(device.name in v['dataPath'] for v in detail['views'])
          and all(v['status'] in ('ready', 'unbuilt')
                  for v in detail['views'])
          and not bad['ok'] and 'known' in bad,
          f'keys={len(keys)} unbuilt={detail.get("unbuiltViews")}')
    builders = extra_curve_builders()
    fv_graphs = {g['name'] for g in extra_graph_seeds()}
    rm = device_curve_points(mgr, device.name, curve='regime-map')
    tr = device_curve_points(mgr, device.name, curve='transport-vs-lg')
    from cntfet.cnt_transport import transport_report
    trep = transport_report(mgr, device, p_dev, vgs=0.6, vds=0.6)
    trep_lo = transport_report(mgr, device, p_dev, vgs=0.6, vds=0.05)
    check('fv-2 plug-in: transport rows come through the same registry '
          '(tuple builders honoured) and the report names the regime '
          'with its criteria — S1 is ballistic at low bias and the '
          'optical-phonon branch pulls it down at Vdd',
          'transport-vs-lg' in builders and tr['ok'] and len(tr['rows']) > 20
          and trep['ok'] and trep_lo['ok']
          and trep_lo['regime']['name'] == 'ballistic'
          and trep['transmission'] < trep_lo['transmission']
          and trep['topContributor'] == 'optical-phonon',
          f'tr={tr.get("error")} lo={trep_lo.get("regime")} '
          f'hi={trep.get("regime")} top={trep.get("topContributor")}')
    check('fv-1 plug-in: sibling modules contribute curve builders + '
          'graph seeds through one registry — regime-map rows come '
          'back through device_curve_points and the regime graphs '
          'are in the seed pass',
          'regime-map' in builders and rm['ok'] and len(rm['rows']) > 100
          and {'cnt-device-regime-map', 'cnt-device-exponent',
               'cnt-device-output-regimes'} <= fv_graphs,
          f'builders={sorted(builders)} graphs={sorted(fv_graphs)} '
          f'rm={rm.get("error")}')

    from cntfet.cnt_compare import detail_pages
    from cntfet.cnt_scene import scene_name
    fp = device_curve_points(mgr, device.name, curve='field-potential')
    pot = characteristic_detail(mgr, device.name, 'potential-at-instant',
                                scene_names={scene_name(device.name)})
    scene_view = next(v for v in pot['views'] if v['kind'] == 'simspace')
    dpages = detail_pages([device.name])
    dcomps = [i['componentProps']['componentName']
              for r in json.loads(dpages[0]['definition'])['rows']
              for i in r['items']]
    check('fv-4/fv-5 plug-in: field-potential rows come through the '
          'registry; the potential characteristic resolves its scene '
          'to THIS device\'s cnt-device-3d-{device} with the field\'s '
          'run ref (ready when the scene row exists); the detail page '
          'seeds the explorer + one sim-space viewer per scalar field',
          fp['ok'] and len(fp['rows']) > 100
          and scene_view['simSpaceName'] == scene_name(device.name)
          and scene_view['run'] == f'fet-fields:{device.name}:potential'
          and scene_view['status'] == 'ready'
          and dpages[0]['pageRoute'] == f'cntfet-detail-{device.name}'
          and dcomps.count('fet-characteristic-explorer') == 1
          and dcomps.count('sim-space-viewer') == 3,
          f'fp={fp.get("error")} view={scene_view} comps={dcomps}')

    # ---- fp-6: datasheet categories, plain language, the weave -----
    from cntfet.cnt_links import device_links
    idx6 = characteristics_index(mgr, device.name)
    cats = {c['category'] for c in idx6['characteristics']}
    links = device_links(mgr, device)
    p_dev_row = cd.get_row(mgr, 'AlignedCNTFETDevice', 'cnt-aligned-s1-p')
    cd.derive_device(mgr, p_dev_row, parameter_factory=pfac)
    _pid, p_p, _prow, _pref = device_model(mgr, p_dev_row.name)
    check('fp-6: every characteristic carries a datasheet category '
          '(input / output / transfer / structure) and a plain-'
          'language explanation; the index states what each category '
          'means; /links weaves pages + partner + cells + comparators; '
          'the p device\'s model carries ptype 1 and names its '
          'mirrored frame',
          cats == {'input', 'output', 'transfer', 'structure'}
          and all(c['explain'] for c in idx6['characteristics'])
          and len(idx6['categories']) == 4
          and links['ok'] and len(links['pages']) == 3
          and links['cells_built_from_it']
          and device.name in links['start_here']['route']
          and p_p['ptype'] == 1 and 'mirrored' in p_p['polarity_frame']
          and p_dev['ptype'] == 0,
          f'cats={cats} links={links.get("error")} '
          f'pp={p_p.get("polarity_frame")}')

    # ---- fp arc: power, taxonomy, silicon dispatch, logic, cells page
    from cntfet.cnt_power import (
        budget_report, cell_leakage_states, fet_power,
    )
    from cntfet.cnt_taxonomy import device_taxonomy_report, score_signal
    from cntfet.cnt_logic import cell_logic_report, library_logic_report
    from sifet.si_basis import SEED_TABLES as SI_SEED_TABLES
    from sifet.si_device import derive_si_device
    fpw = fet_power(_id, p_dev, device)
    pw = budget_report(mgr, device.name)
    nand = cell_leakage_states('cnand2', 1, 1e-9, 1e-9)
    leak = {s['when']: s['i_leak_a'] for s in nand['states']}
    check('fp-1: FET static power = Vdd·Ioff with gate/GIDL leakage '
          'named as unmodelled gaps, dynamic C·Vdd²; NAND2 leakage per '
          'input state shows the stack effect (00 < 11); budget '
          'checks carry per-limit results',
          abs(fpw['static_w'] - 0.6 * fpw['ioff_a']) < 1e-18
          and 'gate' in fpw['leakage_components']
          and fpw['dynamic']['e_switch_j'] > 0
          and pw['ok'] and pw['results']
          and len(leak) == 4
          and min(leak.values()) < max(leak.values()),
          f'pw={ {k: pw.get(k) for k in ("ok", "error")} } leak={leak}')
    tx = device_taxonomy_report(mgr, device.name)
    sig = score_signal(mgr, device.name)
    check('fp-3: taxonomy names the shape (cnt-gaa), the optimization '
          'class S1 suits (switching, with the signal score beside it), '
          'the complementary partner with evaluated conditions, and the '
          'three regions with numeric boundaries (Vt, Vt+Vov_min, '
          'Vdsat = BdSat per Vg)',
          tx.get('ok', True) and sig.get('ok', True)
          and 0.0 < sig['score'] < 1.0
          and tx['optimization']['suited_to'] == 'switching-optimized'
          and tx['complementary'] and len(tx['regions']) >= 3,
          f'tx={ {k: tx.get(k) for k in ("error", "shape")} } '
          f'sig={sig.get("score")}')
    for table, seeds in SI_SEED_TABLES:
        mgr.objectTables.setdefault(table, {})
        for s in seeds:
            _row_factory(mgr, table)(**s)
    for n in ('si-nmos-planar-90', 'si-pmos-planar-90'):
        derive_si_device(mgr, cd.get_row(mgr, 'SiliconMOSFET', n))
    si_id, si_p, si_dev, si_ref = device_model(mgr, 'si-nmos-planar-90')
    si_score = score_device(mgr, 'si-nmos-planar-90')
    xcmp = compare_devices(mgr, 'si-nmos-planar-90')
    check('fp-2: a SiliconMOSFET row (sol-gel or thermal oxide) answers '
          'the SAME device_model contract — it is a valid FET under the '
          'gate, scores on the same terms and competes in the cross-'
          'technology ranking with the CNT devices; CNT-only surfaces '
          '(transport context, field regions) refuse by name',
          si_ref is None and si_score['validity']['valid']
          and 0.0 < si_score['score'] < 1.0
          and xcmp['ok'] and any(r['device'].startswith('cnt-')
                                 for r in xcmp['ranking'])
          and any(r['device'].startswith('si-')
                  for r in xcmp['ranking'])
          and not device_curve_points(mgr, 'si-nmos-planar-90',
                                      curve='transport-vs-lg')['ok'],
          f'ref={si_ref} score={si_score.get("score")} '
          f'of={xcmp.get("of")}')
    lg = cell_logic_report('cnand2')
    lib = library_logic_report()
    cells_page = SEED_CNTFET_PAGE_DISPLAYS[1]
    cp_comps = [i['componentProps']['componentName']
                for r in json.loads(cells_page['definition'])['rows']
                for i in r['items']]
    check('fp-5: every combinational cell PROVES (boolean function == '
          'switch-level netlist over every vector; zero contention / '
          'floating); NAND2 payload carries the gate DAG, truth table, '
          'placed netlist and the state space; the cells page seeds a '
          'logic diagram + schematic per cell over the generic '
          'registry',
          lg['ok'] and lg['proof']['proven'] and lg['gateDag']['nodes']
          and lg['truthTable']['count'] == 4
          and len(lg['netlist']['devices']) == 4
          and lib['allProven']
          and cells_page['pageRoute'] == 'cntfet-cells'
          and cp_comps.count('cell-logic-diagram') == 19
          and cp_comps.count('cell-schematic') == 19,
          f'lg={lg.get("refusal")} allProven={lib.get("allProven")}')

    # ---- ip: licensing / FTO tracked like everything else ----------
    from cntfet.cnt_ip import (
        DISCLAIMER, SEED_TECHNOLOGY_IP, device_ip_report, library_ip_report,
    )
    ip_s1 = device_ip_report(mgr, device.name)
    ip_si = device_ip_report(mgr, 'si-nmos-planar-90')
    ip_lib = library_ip_report(mgr)
    ip_rows = device_curve_points(mgr, device.name, curve='ip-verdicts')
    check('ip: every technology carries an FTO record (verdict, patents '
          'with expiry, what we own, self-manufacture note, verify_next, '
          'confidence); S1 = amber (aligned-array process may be active), '
          'the planar Si NMOS = green (MOSFET/CMOS/planar expired), no '
          'red anywhere, the disclaimer rides every payload, and the '
          'verdict graph comes through the registry',
          len(SEED_TECHNOLOGY_IP) >= 20
          and all(r['verdict'] in ('green', 'amber', 'red')
                  and r['fto_reasoning'] and r['self_manufacture_note']
                  and r['verify_next'] for r in SEED_TECHNOLOGY_IP)
          and ip_s1['ok'] and ip_s1['worst_verdict'] == 'amber'
          and 'does not' in ip_s1['self_manufacture_answer'].lower()
          and ip_si['ok'] and ip_si['worst_verdict'] == 'green'
          and ip_lib['ok'] and ip_lib['verdict_counts'].get('red', 0) == 0
          and DISCLAIMER and ip_s1.get('disclaimer') == DISCLAIMER
          and ip_rows['ok'] and len(ip_rows['rows']) >= 3,
          f's1={ip_s1.get("worst_verdict")} si={ip_si.get("worst_verdict")} '
          f'counts={ip_lib.get("verdict_counts")} rows={ip_rows.get("error")}')

    # ---- evidence: proof-of-freedom as first-class, embedded ----------
    from cntfet.cnt_evidence import (
        SEED_EVIDENCE, evidence_detail, freedom_proof, library_proof,
    )
    mgr.objectTables.setdefault('EvidenceItem', {})
    for seed in SEED_EVIDENCE:
        _row_factory(mgr, 'EvidenceItem')(**seed)
    pf_s1 = freedom_proof(mgr, 'device', device.name)
    pf_si = freedom_proof(mgr, 'device', 'si-nmos-planar-90')
    pf_inv = freedom_proof(mgr, 'cell', 'cinv')
    ev = evidence_detail(mgr, 'pat-us-3102230')
    lib_pf = library_proof(mgr)
    sc_prov = score_device(mgr, 'si-nmos-planar-90').get('provenance')
    cmp_prov = next(r for r in compare_devices(mgr, device.name)['ranking']
                    if r['isFocus']).get('provenance')
    lg_prov = cell_logic_report('cinv').get('provenance')
    check('evidence: patents / papers / licences are first-class rows '
          'joined to every IP record; the proof chain (US) makes the '
          'planar Si NMOS PROVEN-FREE (expired patents verified online: '
          'US 3,102,230 / 3,356,858 / 3,025,589), every cell proven-free, '
          'and S1 ENCUMBERED with the active aligned-array patent named '
          'as the gap; the Kahng patent detail lists what it supports; '
          'provenance blocks (verdict, status, top evidence, click-through '
          'detailPath) ride the score, compare and cell-logic payloads',
          len(SEED_EVIDENCE) >= 60
          and pf_si['status'] == 'proven-free' and not pf_si['gaps']
          and pf_inv['status'] == 'proven-free'
          and pf_s1['status'] == 'encumbered'
          and any('9825229' in g or '9,825,229' in g for g in pf_s1['gaps'])
          and pf_s1['jurisdiction'] == 'US' and pf_s1.get('disclaimer')
          and ev['ok'] and ev['item']['verified']
          and any(r.get('record') == 'mosfet-generic'
                  for r in ev['supports']['records'])
          and lib_pf['counts'].get('proven-free', 0) >= 26
          and sc_prov and sc_prov['proofStatus'] == 'proven-free'
          and sc_prov['detailPath'].endswith('/proof')
          and cmp_prov and cmp_prov['proofStatus'] == 'encumbered'
          and lg_prov and lg_prov['proofStatus'] == 'proven-free',
          f's1={pf_s1.get("status")} si={pf_si.get("status")} '
          f'inv={pf_inv.get("status")} counts={lib_pf.get("counts")} '
          f'sc={sc_prov} lg={lg_prov}')

    # ---- usable vs reference (his binary) + cells x FETs coverage ----
    from cntfet.cnt_cell_coverage import cells_coverage, device_cell_coverage
    u_si = freedom_proof(mgr, 'device', 'si-nmos-planar-90')['usage']
    u_s1 = freedom_proof(mgr, 'device', device.name)['usage']
    u_ref = freedom_proof(mgr, 'record', 'tfet')['usage']
    lp = library_proof(mgr)
    cov = cells_coverage(mgr)
    dcov = device_cell_coverage(mgr, device.name)
    check('usable-vs-reference: every proof states the binary — the '
          'planar Si NMOS is USABLE in open chips (candidate + proven '
          'free), S1 is a CANDIDATE NOT YET USABLE (encumbered), TFET is '
          'REFERENCE ONLY; evidence items carry a role (patents / papers '
          '= reference, open licences / formats = usable); the cells x '
          'FETs coverage matrix lists 26 cells per device (incl. cdff) '
          'with the POST that fills each gap',
          u_si['usable_in_open_chips'] and 'USABLE' in u_si['statement']
          and not u_s1['usable_in_open_chips']
          and 'NOT YET' in u_s1['statement']
          and u_ref['intended_use'] == 'reference-only'
          and 'REFERENCE ONLY' in u_ref['statement']
          and lp['usableCount'] >= 26
          and {s['role'] for s in SEED_EVIDENCE} == {'reference', 'usable'}
          and cov['ok'] and len(cov['cells']) == 25
          and dcov['cellsTotal'] == 26
          and any(c['cell'] == 'cdff' for c in dcov['cells'])
          and all('characterize' in c['fill'] for c in dcov['cells']
                  if not c['covered']),
          f'si={u_si} s1={u_s1.get("statement")} ref={u_ref.get("statement")} '
          f'usable={lp.get("usableCount")} cov={dcov.get("cellsTotal")}')

    # ---- fi-2 (cells): the library scored vs intrinsic limits ------
    from cntfet.cnt_cell_scoring import (
        CELL_TERMS, SEED_CELL_SCORE_TERMS, cell_frames, cell_score_rows,
        parse_liberty, score_cells,
    )
    mgr.objectTables.setdefault('CellCharacterizationRun', {})
    no_lib = score_cells(mgr, device.name)
    check('fi-2 cells: without a library run the score REFUSES naming '
          'the characterize affordance; terms are ratios to the '
          'driving FET\'s own intrinsic limits (ideal 1)',
          not no_lib['ok'] and 'characterize-cells' in no_lib['error']
          and {t['name'] for t in SEED_CELL_SCORE_TERMS}
          == set(CELL_TERMS)
          and all(v['ideal'] == 1.0 for v in CELL_TERMS.values()))
    # a synthetic 2-cell Liberty in the emitter's own format
    from cntfet.cnt_cell_library import _liberty_library
    tau_fake = 0.1e-12
    def _pt(scale):
        return {'cell_rise_s': 5 * tau_fake * scale,
                'cell_fall_s': 5 * tau_fake * scale,
                'rise_transition_s': 6 * tau_fake * scale,
                'fall_transition_s': 6 * tau_fake * scale,
                'energy_rise_j': 2e-18 * scale,
                'energy_fall_j': 0.0}
    blocks = [{'libertyName': 'INVX1', 'function': '(!A)',
               'inputs': ['A'], 'inputCap_f': 1e-17,
               'arcs': {'A': {'pin': 'A', 'sense': 'negative',
                              'tables': [[_pt(1)] * 3] * 3}}},
              {'libertyName': 'NAND2X4', 'function': '(!(A*B))',
               'inputs': ['A', 'B'], 'inputCap_f': 4e-17,
               'arcs': {'A': {'pin': 'A', 'sense': 'negative',
                              'tables': [[_pt(2)] * 3] * 3},
                        'B': {'pin': 'B', 'sense': 'negative',
                              'tables': [[_pt(2)] * 3] * 3}}}]
    lib_text = _liberty_library(0.6, [1e-12, 2e-12, 4e-12],
                                [1e-17, 2e-17, 4e-17], blocks)
    parsed = parse_liberty(lib_text)
    frames = cell_frames(parsed, tau_fake, 0.6)
    check('fi-2 cells: the emitter\'s Liberty parses back (cells, '
          'arcs, 6 tables each, grid indices) and the mid-grid frame '
          'reads delay/τ = 5, transition/τ = 6, energy/C·V² = '
          '1 + E_int/(C_L·Vdd²), FETs/min = 4 for the x4 NAND',
          set(parsed['cells']) == {'INVX1', 'NAND2X4'}
          and len(parsed['cells']['NAND2X4']['arcs']['B']) == 6
          and parsed['index_2_ff'] == [0.01, 0.02, 0.04]
          and abs(frames['INVX1']['delay_over_tau'] - 5.0) < 1e-3
          and abs(frames['INVX1']['transition_over_tau'] - 6.0) < 1e-3
          # E_int 2 aJ over C_L·Vdd² = 0.02 fF · 0.36 V² = 7.2 aJ
          and abs(frames['INVX1']['energy_over_cv2']
                  - (1 + 2.0 / 7.2)) < 1e-3
          and frames['NAND2X4']['fets_over_min'] == 4.0
          and frames['NAND2X4']['cell'] == 'cnand2',
          f'frames={frames}')
    _row_factory(mgr, 'CellCharacterizationRun')(
        name='lib-test', device=device.name, cell='library:INVX1',
        liberty_text=lib_text, ran_at='2026-08-26T00:00:00', vdd_v=0.6)
    cs = score_cells(mgr, device.name)
    cs_rows = device_curve_points(mgr, device.name, curve='cell-scores')
    check('fi-2 cells: the latest library row scores every cell '
          '(ranked; the x4 NAND loses on FET count and its 2x '
          'slower arcs), the curve is long-form with categorical x '
          '= cell + hguide at 1.0',
          cs['ok'] and cs['run'] == 'lib-test'
          and [r['cell'] for r in cs['ranking']] == ['INVX1', 'NAND2X4']
          and all(not c['termsMissing'] for c in cs['cells'])
          and cs_rows['ok']
          and {r['x'] for r in cs_rows['rows'] if r['style'] == 'dot'}
          == {'INVX1', 'NAND2X4'}
          and any(r['style'] == 'hguide' for r in cs_rows['rows']),
          f'cs={cs.get("error")} ranking={cs.get("ranking")}')

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
        # ---- cell-2: richer combinationals, x4, energy, sequential --
        from cntfet.cnt_cell_library import (
            COMBINATIONAL, cell_arcs, liberty_cell_name,
        )
        from cntfet.cnt_sequential import (
            characterize_sequential, lctime_status,
        )
        x4 = subckt_text('caoi21', 4)
        mux_arcs = cell_arcs('cmux2')
        aoi_arcs = {a['id']: a for a in cell_arcs('caoi21')}
        check('cell-2: AOI21/OAI21/MUX2 join the library as DATA — '
              'x4 is GENERATED (4 parallel devices per position), '
              'per-arc ties depend on the pin under test, MUX2 '
              'carries both S senses as `when` arcs',
              4 in DRIVES
              and x4.count('cntn') == 12 and x4.count('cntp') == 12
              and fet_count('cmux2', 4) == 24
              and len(SEED_CNT_CELLS)
              == len(CELL_LIBRARY) * len(DRIVES)
              and set(COMBINATIONAL) <= set(CELL_LIBRARY)
              and aoi_arcs['A|B*!C']['ties'] == {'B': 1, 'C': 0}
              and aoi_arcs['C|!A*!B']['ties'] == {'A': 0, 'B': 0}
              and [a['id'] for a in mux_arcs]
              == ['A|!S', 'B|S', 'S|!A*B', 'S|A*!B']
              and {a['sense'] for a in mux_arcs}
              == {'positive', 'negative'}
              and liberty_cell_name('coai21', 4) == 'OAI21X4')
        lib2 = characterize_cells(
            mgr, device, cells=['coai21', 'cmux2'], drives=(4,),
            result_factory=_row_factory(
                mgr, 'CellCharacterizationRun'))
        cells2 = {c['libertyName']: c for c in lib2.get('cells', [])}
        oai = cells2.get('OAI21X4', {})
        mux = cells2.get('MUX2X4', {})
        lib2_text = open(lib2['libertyPath']).read() \
            if lib2.get('ok') else ''
        check('cell-2: OAI21X4 + MUX2X4 characterize in ONE Liberty '
              'with state-dependent `when` arcs, every arc monotone '
              'in load, zero failed points, and the multi-cell '
              'staGate reflects the live binary',
              lib2.get('ok')
              and oai.get('arcs') == ['A|!B*C', 'B|!A*C', 'C|A*!B']
              and mux.get('arcs') == ['A|!S', 'B|S', 'S|!A*B',
                                      'S|A*!B']
              and all(m['monotoneInLoad'] for m in lib2['monotone'])
              and not lib2['failures']
              and 'when : "!A*C";' in lib2_text
              and 'timing_sense : positive_unate' in lib2_text
              and 'timing_sense : negative_unate' in lib2_text
              and ((lib2['staGate'].get('ran')
                    and lib2['staGate'].get('accepted'))
                   or (not lib2['staGate'].get('ran')
                       and lib2['staGate'].get('refusal'))),
              f'lib2={lib2.get("cells")}, '
              f'failures={lib2.get("failures")}, '
              f'sta={lib2.get("staGate")}')
        oai_e = oai.get('energy', {}).get('C|A*!B', {})
        mux_e = mux.get('energy', {})
        check('cell-2: energy-per-transition rides the SAME '
              'transients into internal_power tables — a rail-driven '
              'arc has positive internal rise energy below its '
              'supply energy (load CV^2 removed), and the pass-gate '
              'MUX data arcs are honestly ~0 and FLAGGED clamped '
              '(their charge comes from the input driver)',
              lib2.get('ok')
              and 0.0 < oai_e.get('rise_aJ', -1.0)
              < oai_e.get('supplyRise_aJ', 0.0)
              and not oai_e.get('clamped')
              and mux_e.get('B|S', {}).get('clamped') is True
              and mux_e.get('B|S', {}).get('rise_aJ') == 0.0
              and 'internal_power ()' in lib2_text
              and 'rise_power (pwr_tpl_3x3)' in lib2_text
              and 'leakage_power_unit : "1uW";' in lib2_text,
              f'oai={oai_e}, mux={mux_e}')
        seq = characterize_sequential(
            mgr, device, iters=4,
            result_factory=_row_factory(
                mgr, 'CellCharacterizationRun'))
        su, ho, cq = (seq.get('setup', {}), seq.get('hold', {}),
                      seq.get('clkToQ', {}))
        tau_s = seq.get('point', {}).get('tau_s', 1.0)
        check('cell-2: sequential characterization by the OWN-LOOP '
              'executor — setup/hold found by bisection on the cdff '
              '(both D senses), setup > hold, clk->Q positive, all '
              'on the tau scale with the bracket resolution '
              'recorded, x1 only, and a DFFX1 Liberty with ff() + '
              'setup_rising/hold_rising constraint arcs',
              seq.get('ok') and seq['executor'] == 'polari-own-loop'
              and all(su[k]['ok'] and ho[k]['ok']
                      for k in ('rise', 'fall'))
              and all(su[k]['value_s'] > ho[k]['value_s']
                      for k in ('rise', 'fall'))
              and all(0.0 < cq[k]['delay_s'] < 40.0 * tau_s
                      for k in ('rise', 'fall'))
              and all(abs(su[k]['value_s']) < 40.0 * tau_s
                      and abs(ho[k]['value_s']) < 40.0 * tau_s
                      for k in ('rise', 'fall'))
              and all(su[k]['resolution_s'] is not None
                      for k in ('rise', 'fall'))
              and seq['transients'] >= 4 * (2 + 4)
              and 'ff (IQ, IQN)' in seq_lib(seq)
              and 'timing_type : setup_rising;' in seq_lib(seq)
              and 'timing_type : hold_rising;' in seq_lib(seq)
              and seq['cell'] == 'DFFX1',
              f'seq={ {k: seq.get(k) for k in ("ok", "error", "refusal", "setup", "hold", "clkToQ", "transients")} }')
        cc = seq.get('staConstraintCheck', {})
        check('cell-2: OpenSTA CONSUMES the sequential constraints — '
              'a reg->reg path reports OUR setup as its library '
              'setup time (or the check refuses by name without '
              'sta; never a silent middle)',
              (cc.get('ran') and cc.get('accepted'))
              or (not cc.get('ran') and 'refusal' in cc),
              f'cc={cc}')
        lc = characterize_sequential(mgr, device, executor='lctime')
        st = lctime_status()
        check('cell-2 D14: the lctime executor is a KNOB LADDER, not '
              'code — absent by default, refusing with the rung '
              'named (knob / binary / ratification), AGPL stated, '
              'the own-loop named as the exit path; nothing '
              'vendored or pinned',
              not lc.get('ok') and 'refusal' in lc
              and lc['executor'] == 'lctime'
              and st['licence'] == 'AGPL-3.0-or-later'
              and st['rung'] in ('absent-by-default',
                                 'knob-on-binary-absent',
                                 'knob-on-binary-present-'
                                 'invocation-unwired')
              and 'own-loop' in st['exitPath']
              and lc['lctime']['rung'] == st['rung']
              and ('D14' in lc['refusal'] or 'PATH' in lc['refusal']
                   or 'ratification' in lc['refusal']),
              f'lc={lc}')

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
