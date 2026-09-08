"""
@module cntfet.cnt_calibration_seed

S1 calibration against the Franklin & Chen 2010 device set — the
VS-CNFET v_xo anchor (S0 gate CORRECTION: [FC10], NOT Franklin
2012). Anchors are DATA rows (CNTCalibrationAnchor) with full D18
provenance; the calibrate act evaluates the model AT the anchor
conditions and records residuals. Residuals are the deliverable —
they are never silently minimized away.

Honesty structure:
  - The scalar anchors here are REPORTED/TABLE values quoted in
    [VS1] Sec.II.D/Sec.V and [FC10] text — extraction_method says
    exactly that. NO curve-level digitization has been performed
    yet: the raw Id-Vd point sets exist only as rasterized figures;
    digitizing them with a quantified error estimate is S2 work.
    That gap is itself a row (status='refusing') so the absence is
    queryable, per the DigitizedDataset refusal discipline.
  - eq.(9) with l ~= Lg is stated by [VS1] for Lg < 30 nm; the
    3 um anchor is OUTSIDE that domain — its residual is recorded
    and labeled out-of-domain rather than dropped.

@consumers
  - cntfet.cnt_api ({action: calibrate})
  - cntfet.cntfet_selftest
"""

import json
from datetime import datetime, timezone

from cntfet.custom.cnt_bandstructure import cinv_f_per_m, cqe_f_per_m
from cntfet.custom.cnt_constants import EQUATION_REVISION, lit_value
from cntfet.custom.cnt_vs_model import vs_terminal_current, vxo_m_per_s

_FC10 = ('Franklin & Chen, Nat. Nanotech. 5:858 (2010)')
_VS1 = ('Lee et al., IEEE TED 62(9):3061 (2015), read via '
        'arXiv:1503.04397')

# D18: every anchor keeps figure id + method + error + conditions +
# any fitted params riding it. raw_points carry the (x, y) pairs the
# value came from where there IS a curve; scalar reports say so.
SEED_CALIBRATION_ANCHORS = [
    {'name': 'fc10-vxo-lg15',
     'source_reference': f'{_VS1}; underlying data {_FC10}',
     'doi': '10.1109/TED.2015.2457453', 'figure': '[VS1] Fig.7(a)',
     'extraction_method': 'reported-value (v_xo extracted by [VS1] '
                          'fitting the VS model to the [FC10] '
                          'Id-Vds data; quoted from the paper text)',
     'digitization_error': 'n/a (reported scalar, 2 significant '
                           'figures)',
     'axis_scaling_json': '{}', 'raw_points_json': '[]',
     'normalizations_json': '{}',
     'fitted_params_json': json.dumps(
         {'fit_by': '[VS1] authors', 'equation': '[VS1] eq.(9)',
          'lambda_v_nm': 440.0, 'vB0_cm_per_s': 4.1e7,
          'd0_nm': 1.2}),
     'value': 3.8e5, 'unit': 'm/s',
     'conditions_json': json.dumps(
         {'lg_nm': 15.0, 'd_nm': 1.2, 'rs_ohm': 5500.0,
          'ss_mv_per_dec_assumed': 135.0,
          'cox_f_per_m_assumed': 0.156e-9, 'polarity_note':
          'polarity flipped to n-type by [VS1]'}),
     'status': 'ready', 'notes': 'the calibration flagship'},
    {'name': 'fc10-vxo-lg300',
     'source_reference': f'{_VS1}; underlying data {_FC10}',
     'doi': '10.1109/TED.2015.2457453', 'figure': '[VS1] Fig.7(b)',
     'extraction_method': 'reported-value (as fc10-vxo-lg15)',
     'digitization_error': 'n/a (reported scalar)',
     'axis_scaling_json': '{}', 'raw_points_json': '[]',
     'normalizations_json': '{}',
     'fitted_params_json': json.dumps(
         {'fit_by': '[VS1] authors', 'equation': '[VS1] eq.(9)'}),
     'value': 1.7e5, 'unit': 'm/s',
     'conditions_json': json.dumps(
         {'lg_nm': 300.0, 'd_nm': 1.2, 'rs_ohm': 5500.0}),
     'status': 'ready', 'notes': ''},
    {'name': 'fc10-vxo-lg3000',
     'source_reference': f'{_VS1}; underlying data {_FC10}',
     'doi': '10.1109/TED.2015.2457453', 'figure': '[VS1] Fig.7(c)',
     'extraction_method': 'reported-value (as fc10-vxo-lg15)',
     'digitization_error': 'n/a (reported scalar)',
     'axis_scaling_json': '{}', 'raw_points_json': '[]',
     'normalizations_json': '{}',
     'fitted_params_json': json.dumps(
         {'fit_by': '[VS1] authors', 'equation': '[VS1] eq.(9)'}),
     'value': 0.47e5, 'unit': 'm/s',
     'conditions_json': json.dumps(
         {'lg_nm': 3000.0, 'd_nm': 1.2,
          'domain_note': '[VS1] states l ~= Lg only for '
                         'Lg < 30 nm; eq.(9) here is '
                         'OUT-OF-DOMAIN extrapolation'}),
     'status': 'ready', 'notes': 'out-of-domain for eq.(9)'},
    {'name': 'fc10-gm-lg15',
     'source_reference': _FC10, 'doi': '10.1038/nnano.2010.220',
     'figure': '[FC10] text (record transconductance)',
     'extraction_method': 'reported-value (paper text: highest '
                          'gm of any nanotube transistor, 40 uS, '
                          'Lch = 15 nm)',
     'digitization_error': 'n/a (reported scalar)',
     'axis_scaling_json': '{}', 'raw_points_json': '[]',
     'normalizations_json': '{}', 'fitted_params_json': '{}',
     'value': 40e-6, 'unit': 'S',
     'conditions_json': json.dumps(
         {'lch_nm': 15.0, 'vds_v_magnitude': 0.4,
          'polarity': 'p (original data)'}),
     'status': 'ready', 'notes': ''},
    {'name': 'fc10-gon-lg15',
     'source_reference': _FC10, 'doi': '10.1038/nnano.2010.220',
     'figure': '[FC10] text (on-conductance)',
     'extraction_method': 'reported-value (paper text: highest '
                          'room-temperature conductance 0.7 G0)',
     'digitization_error': 'n/a (reported scalar); G0 convention '
                           'PINNED from the paper text (S2, '
                           '2026-08-21): RQ = 1/G0 = h/4e^2 ~ '
                           '6.5 kOhm, so G0 = 4e^2/h ~ 155 uS',
     'axis_scaling_json': '{}', 'raw_points_json': '[]',
     'normalizations_json': '{}', 'fitted_params_json': '{}',
     'value': 0.7, 'unit': 'G0',
     'conditions_json': json.dumps(
         {'lch_nm': 15.0, 'g0_definition': '4e^2/h',
          'g0_siemens': 155.0e-6}),
     'status': 'ready',
     'notes': 'TENSION recorded (S2): 0.7 G0 = 108.5 uS total '
              'conductance implies Rtot ~ 9.2 kOhm, but the [VS1] '
              'fit Rs = 5.5 kOhm PER TERMINAL caps G at ~91 uS '
              '(0.59 G0). The record device and the 3-length fit '
              'set cannot share both numbers — likely different '
              'devices/contacts. Carried as data, not resolved '
              'by fiat.'},
    {'name': 'fc10-tube-diameter',
     'source_reference': _FC10, 'doi': '10.1038/nnano.2010.220',
     'figure': '[FC10] Methods',
     'extraction_method': 'reported-value (Methods: diameter '
                          'between 1.0 and 1.2 nm; 1.2 nm used '
                          'as the source average by [VS1])',
     'digitization_error': 'range 1.0-1.2 nm',
     'axis_scaling_json': '{}', 'raw_points_json': '[]',
     'normalizations_json': '{}', 'fitted_params_json': '{}',
     'value': 1.2, 'unit': 'nm', 'conditions_json': '{}',
     'status': 'ready', 'notes': ''},
    {'name': 'vs1-rs-per-terminal',
     'source_reference': _VS1, 'doi': '10.1109/TED.2015.2457453',
     'figure': '[VS1] Sec.II.D extraction step (a)',
     'extraction_method': 'reported-value (Rs = 5.5 kOhm per the '
                          'reported experimental data)',
     'digitization_error': 'n/a (reported scalar)',
     'axis_scaling_json': '{}', 'raw_points_json': '[]',
     'normalizations_json': '{}', 'fitted_params_json': '{}',
     'value': 5500.0, 'unit': 'ohm', 'conditions_json': '{}',
     'status': 'ready', 'notes': ''},
    {'name': 'vs1-cox-anchor',
     'source_reference': _VS1, 'doi': '10.1109/TED.2015.2457453',
     'figure': '[VS1] Sec.II.D extraction step (b)',
     'extraction_method': 'reported-value (Cox = 0.156 fF/um '
                          'estimated by TCAD Sentaurus: metallic '
                          'cylinder on 10 nm HfO2, back gate — '
                          'no C-V data existed)',
     'digitization_error': 'TCAD estimate, not a measurement',
     'axis_scaling_json': '{}', 'raw_points_json': '[]',
     'normalizations_json': '{}', 'fitted_params_json': '{}',
     'value': 0.156e-9, 'unit': 'F/m', 'conditions_json': '{}',
     'status': 'ready',
     'notes': 'anchor-context Cox — the [FC10] devices are '
              'BACK-GATED, not GAA; residual evaluation uses THIS '
              'Cox, the seeded GAA device keeps its own'},
    {'name': 'fc10-idvd-curves',
     'source_reference': _FC10, 'doi': '10.1038/nnano.2010.220',
     'figure': '[FC10] Fig.2 / [VS1] Fig.7(b),(c) symbol sets',
     'extraction_method': 'NOT PERFORMED',
     'digitization_error': 'unquantified — that is WHY this row '
                           'refuses',
     'axis_scaling_json': '{}', 'raw_points_json': '[]',
     'normalizations_json': '{}', 'fitted_params_json': '{}',
     'value': 0.0, 'unit': '',
     'conditions_json': '{}', 'status': 'refusing',
     'notes': '[VS1] Fig.7(a) WAS digitized 2026-08-21 (S2c '
              'programmatic pass — see fc10-idvd-lg15-digitized); '
              'panels (b) 300 nm and (c) 3 um plus the [FC10] '
              'original figures still refuse until they get the '
              'same treatment.'},
]


def _digitized_fig7a_seed():
    """The S2c programmatic digitization as one D18 anchor row
    (full detail + method in cntfet.custom.cnt_digitized_fc10)."""
    from cntfet.custom.cnt_digitized_fc10 import (
        ERROR_BUDGET, FIG7A_POINTS, OVERDRIVES_V, X_CALIBRATION,
        Y_CALIBRATION,
    )
    return {
        'name': 'fc10-idvd-lg15-digitized',
        'source_reference': f'{_VS1}; underlying data {_FC10}',
        'doi': '10.1109/TED.2015.2457453',
        'figure': '[VS1] Fig.7(a) (Lg = 15 nm)',
        'extraction_method': 'programmatic: 300-dpi render -> '
                             'color-mask rims + white-interior '
                             'connected components '
                             '(scipy.ndimage) -> centroids; axis '
                             'calibration least-squares over tick '
                             'labels; overlay-verified',
        'digitization_error': f"+-{ERROR_BUDGET['sigma_vds_v']} V, "
                              f"+-{ERROR_BUDGET['sigma_id_ua']} uA "
                              f"per point (worst case "
                              f"{ERROR_BUDGET['worst_case_id_ua']}"
                              f" uA = symbol radius)",
        'axis_scaling_json': json.dumps(
            {'x': X_CALIBRATION, 'y': Y_CALIBRATION}),
        'raw_points_json': json.dumps(FIG7A_POINTS),
        'normalizations_json': json.dumps(
            {'polarity': 'flipped to n-type by [VS1]',
             'overdrives_v': OVERDRIVES_V}),
        'fitted_params_json': '{}',
        'value': float(sum(len(v) for v in FIG7A_POINTS.values())),
        'unit': 'points',
        'conditions_json': json.dumps(
            {'lg_nm': 15.0, 'd_nm': 1.2, 'rs_ohm': 5500.0,
             'ss_mv_per_dec_assumed': 135.0,
             'cox_f_per_m_assumed': 0.156e-9,
             'coverage': '22/17/13/6 symbols per curve; rims '
                         'fused with the model line are not '
                         'extracted (stated method limit)'}),
        'status': 'ready',
        'notes': 'the S1-done curve-calibration deliverable',
    }


SEED_CALIBRATION_ANCHORS.append(_digitized_fig7a_seed())


def _now():
    return datetime.now(timezone.utc).isoformat()


def seed_anchor_rows(manager, factory):
    """Idempotent: create any missing anchor rows (calibration +
    reference-paper anchors)."""
    from cntfet.cnt_reference_papers_seed import SEED_REFERENCE_ANCHORS
    tables = getattr(manager, 'objectTables', None) or {}
    table = tables.get('CNTCalibrationAnchor') or {}
    have = {getattr(r, 'name', '') for r in table.values()}
    made = []
    for seed in SEED_CALIBRATION_ANCHORS + SEED_REFERENCE_ANCHORS:
        if seed['name'] in have:
            continue
        factory(manager=manager, **seed)
        made.append(seed['name'])
    return made


def calibrate_device(manager, device, result_factory=None):
    """Evaluate the model AT each ready anchor's conditions and
    record residuals. Returns the honest report; refusing anchors
    are listed as refused, never skipped silently."""
    if not getattr(device, 'derived_at', ''):
        return {'ok': False, 'error': 'device never derived — POST '
                                      '{"action": "derive"} first'}
    tables = getattr(manager, 'objectTables', None) or {}
    anchors = list((tables.get('CNTCalibrationAnchor')
                    or {}).values())
    if not anchors:
        return {'ok': False, 'error': 'no CNTCalibrationAnchor '
                'rows — seed them first (they ship with the '
                'module)'}
    residuals, refused = [], []
    for anchor in anchors:
        name = getattr(anchor, 'name', '')
        if getattr(anchor, 'status', '') == 'refusing':
            refused.append({'anchor': name,
                            'why': getattr(anchor, 'notes', '')})
            continue
        cond = json.loads(getattr(anchor, 'conditions_json', '{}')
                          or '{}')
        if name.startswith('fc10-vxo-'):
            model = vxo_m_per_s(cond['lg_nm'], cond['d_nm'])
            entry = {
                'anchor': name, 'quantity': 'vxo_m_per_s',
                'anchorValue': anchor.value, 'modelValue': model,
                'residualFraction': (model - anchor.value)
                / anchor.value,
                'equation': '[VS1] eq.(9)'}
            if 'domain_note' in cond:
                entry['outOfDomain'] = cond['domain_note']
            residuals.append(entry)
        elif name == 'fc10-idvd-lg15-digitized':
            residuals.extend(_curve_residuals(anchor))
        elif name == 'fc10-gon-lg15':
            g_on = _gon_anchor_context()
            g0 = 4.0 * 1.602176634e-19 ** 2 / 6.62607015e-34
            residuals.append({
                'anchor': name, 'quantity': 'g_on_over_g0',
                'anchorValue': anchor.value,
                'modelValue': g_on / g0,
                'residualFraction': (g_on / g0 - anchor.value)
                / anchor.value,
                'context': 'anchor context (Cox 0.156 fF/um, Rs '
                           '5.5 kOhm/terminal); NOTE the recorded '
                           'tension: Rs alone caps the model at '
                           '0.59 G0 — this residual is expected '
                           'negative and is evidence about the '
                           'CONTACT prior, not the channel'})
        elif name == 'fc10-gm-lg15':
            # gm in the ANCHOR context: anchor Cox (back gate),
            # anchor Rs, Lg 15 nm, d 1.2 nm.
            gm = _gm_anchor_context(tables)
            residuals.append({
                'anchor': name, 'quantity': 'gm_s',
                'anchorValue': anchor.value, 'modelValue': gm,
                'residualFraction': (gm - anchor.value)
                / anchor.value,
                'context': 'evaluated with vs1-cox-anchor Cox + '
                           'vs1-rs-per-terminal Rs (the [FC10] '
                           'back-gate context), NOT the seeded '
                           'GAA stack'})
        # other ready anchors (diameter, Rs, Cox, G0) are inputs/
        # deferred comparisons, not residual targets.
    stamp = _now()
    if result_factory is None:
        from cntfet.cnt_basis import CNTFETSimResult
        result_factory = CNTFETSimResult
    row = result_factory(
        name=f'{device.name}-calibration-'
             f'{stamp[11:19].replace(":", "")}',
        device=device.name, kind='calibration',
        engine='cntfet.vs-python-reference',
        physics_fidelity='VS_MINIMAL',
        inputs_json=json.dumps({'anchors': [
            getattr(a, 'name', '') for a in anchors]}),
        series_json=json.dumps(residuals),
        metrics_json=json.dumps({
            'residualCount': len(residuals),
            'refusedCount': len(refused),
            'equationRevision': EQUATION_REVISION}),
        verdict='anchors-recorded', ran_at=stamp,
        notes='residuals are the deliverable; the 3 um point is '
              'expected to misfit (out-of-domain for eq.(9))',
        manager=manager)
    try:
        db = getattr(manager, 'db', None)
        if db is not None:
            db.saveInstanceInDB(row)
    except Exception:
        pass
    return {'ok': True, 'device': device.name,
            'residuals': residuals, 'refused': refused,
            'resultRow': row.name, 'verdict': 'anchors-recorded'}


def _curve_residuals(anchor):
    """Model-vs-digitized-curve residuals in the anchor context
    (anchor Cox + Rs; vg = vt0 + overdrive since the figure states
    |Vgs - Vt|). Per curve: RMS in uA + mean fractional where the
    signal is well above the digitization noise floor."""
    raw = json.loads(getattr(anchor, 'raw_points_json', '{}')
                     or '{}')
    overdrives = json.loads(
        getattr(anchor, 'normalizations_json', '{}')
        or '{}').get('overdrives_v', {})
    p = _anchor_context_params()
    out = []
    for curve, points in raw.items():
        ov = overdrives.get(curve)
        if ov is None or not points:
            continue
        vg = p['vt0_v'] + ov
        errs, fracs = [], []
        for point in points:
            model_ua = vs_terminal_current(
                vg, point['vds_v'], p)['id_a'] * 1e6
            err = model_ua - point['id_ua']
            errs.append(err * err)
            if point['id_ua'] > 1.0:  # above ~4x noise floor
                fracs.append(err / point['id_ua'])
        rms = (sum(errs) / len(errs)) ** 0.5
        out.append({
            'anchor': anchor.name, 'quantity': f'idvd-curve {curve}',
            'points': len(points), 'rmsErrorUa': rms,
            'meanFractional': (sum(fracs) / len(fracs))
            if fracs else None,
            'context': 'anchor context (Cox 0.156 fF/um, Rs 5.5 '
                       'kOhm); digitization noise ~0.26 uA/point'})
    return out


def _gon_anchor_context():
    """Linear-regime on-conductance in the [FC10] anchor context:
    Id(vg_on, 0.05 V)/0.05 with anchor Cox + Rs = Rd = 5.5 kOhm."""
    p = _anchor_context_params()
    vg_on = 0.3 + 0.5
    return vs_terminal_current(vg_on, 0.05, p)['id_a'] / 0.05


def _anchor_context_params():
    from cntfet.custom.cnt_bandstructure import eg_ev
    from cntfet.custom.cnt_constants import lit_value as lv
    from cntfet.custom.cnt_vs_model import mu_cm2_per_vs
    eg = eg_ev(1.2)
    cox_anchor = 0.156e-9
    cinv = cinv_f_per_m(cox_anchor, cqe_f_per_m(eg))
    return {'equation_revision': EQUATION_REVISION, 'lg_m': 15e-9,
            'cinv_f_per_m': cinv,
            'vxo_m_per_s': vxo_m_per_s(15.0, 1.2),
            'mu_m2_per_vs': mu_cm2_per_vs(15.0, 1.2) * 1e-4,
            'vt0_v': 0.3, 'dvt_v': 0.0, 'dibl_v_per_v': 0.0,
            'n_ss': 135.0 / 59.6,
            'alpha': lv('alpha_vs'), 'beta': lv('beta_vs'),
            'phit_v': 0.02585, 'rs_ohm': 5500.0, 'rd_ohm': 5500.0,
            'temperature_k': 300.0}


def _gm_anchor_context(tables):
    """Numeric gm at the [FC10] anchor context: anchor Cox in
    series with Cqe(Eg(1.2 nm)), Lg = 15 nm, Rs = Rd = 5.5 kOhm,
    |Vds| = 0.4 V, overdrive 0.5 V around vt0 = 0.3 V."""
    p = _anchor_context_params()
    vg_on = 0.3 + 0.5
    dv = 0.01
    i2 = vs_terminal_current(vg_on + dv, 0.4, p)['id_a']
    i1 = vs_terminal_current(vg_on - dv, 0.4, p)['id_a']
    return (i2 - i1) / (2.0 * dv)
