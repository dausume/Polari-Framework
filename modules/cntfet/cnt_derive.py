"""
@module cntfet.cnt_derive

The derive act for the S1 aligned-CNT device: resolves the
decomposed rows, EXECUTES the S1a derivations, stamps the derived
fields + one CNTFETParameterRow PER PARAMETER (D8 roles as queryable
schema), and rides full provenance on the device row. Derivations
never self-bless — grading is cnt_validate's job.

@consumers
  - cntfet.cnt_api ({action: derive | iv})
  - cntfet.selftest_cntfet
"""

import json
from datetime import datetime, timezone

from cntfet.cnt_bandstructure import (
    derive_gate_values, derive_material_values, sce_parameters,
)
from cntfet.cnt_constants import (
    EQUATION_REVISION, LIT, MODEL_LABEL, lit_value,
)
from cntfet.cnt_tob import tob_iv
from cntfet.cnt_vs_model import build_vs_params, iv_family


def _now():
    return datetime.now(timezone.utc).isoformat()


def get_row(manager, class_name, name):
    tables = getattr(manager, 'objectTables', None) or {}
    for row in (tables.get(class_name) or {}).values():
        if getattr(row, 'name', '') == name:
            return row
    return None


def _save(manager, row):
    try:
        db = getattr(manager, 'db', None)
        if db is not None:
            db.saveInstanceInDB(row)
    except Exception:
        pass


def resolve_components(manager, device):
    """All six decomposed rows, or an honest missing list."""
    wanted = {
        'material': ('CNTMaterialState', device.material),
        'geometry': ('AlignedCNTFETGeometry', device.geometry),
        'gate_stack': ('GateStack', device.gate_stack),
        'contact': ('CNTContact', device.contact),
        'transport': ('CNTTransportModel', device.transport),
        'parasitics': ('CNTParasitics', device.parasitics),
    }
    rows, missing = {}, []
    for key, (cls, name) in wanted.items():
        row = get_row(manager, cls, name)
        if row is None:
            missing.append(f'{cls} "{name}"')
        rows[key] = row
    return rows, missing


def _stamp_parameter(manager, factory, device_name, parameter, rec,
                     stamp):
    """Upsert one CNTFETParameterRow (name = device-parameter)."""
    tables = getattr(manager, 'objectTables', None) or {}
    table = tables.get('CNTFETParameterRow')
    row_name = f'{device_name}-{parameter}'
    existing = None
    for row in (table or {}).values():
        if getattr(row, 'name', '') == row_name:
            existing = row
            break
    fields = dict(
        name=row_name, device=device_name, parameter=parameter,
        value=float(rec['value']), unit=rec.get('unit', ''),
        role=rec.get('role', ''), source=rec.get('source', ''),
        confidence=rec.get('confidence', ''),
        derived_from=rec.get('derived_from', ''),
        equation=rec.get('equation', ''), stamped_at=stamp)
    if existing is not None:
        for key, val in fields.items():
            setattr(existing, key, val)
        _save(manager, existing)
        return existing
    row = factory(manager=manager, **fields)
    _save(manager, row)
    return row


def derive_device(manager, device, parameter_factory=None):
    """The S1 derive act. Returns the honest report dict."""
    rows, missing = resolve_components(manager, device)
    if missing:
        return {'ok': False,
                'error': f'missing component rows: {missing}',
                'refusal': 'derive refuses on incomplete '
                           'decomposition — no defaults invented'}
    mat, geo = rows['material'], rows['geometry']
    gate, contact = rows['gate_stack'], rows['contact']
    transport = rows['transport']
    stamp = _now()

    # S1a: material from chirality.
    mvals = derive_material_values(mat.chirality_n, mat.chirality_m)
    if mvals['semiconducting']['value'] < 1.0:
        return {'ok': False,
                'error': f'chirality ({mat.chirality_n},'
                         f'{mat.chirality_m}) is METALLIC '
                         '((n-m) mod 3 == 0) — not a FET channel',
                'refusal': 'pick a semiconducting chirality'}
    mat.diameter_nm = mvals['diameter_nm']['value']
    mat.eg_ev = mvals['eg_ev']['value']
    mat.vf_m_per_s = mvals['vf_m_per_s']['value']
    mat.m_eff_over_m0 = mvals['m_eff_over_m0']['value']
    mat.semiconducting = True
    mat.derived_at = stamp
    mat.provenance_json = json.dumps(
        {k: {kk: vv for kk, vv in v.items() if kk != 'value'}
         for k, v in mvals.items()})
    _save(manager, mat)

    # S1a: gate electrostatics.
    gvals = derive_gate_values(gate.t_ox_nm, mat.diameter_nm,
                               gate.k_ox, mat.eg_ev)
    gate.cox_f_per_m = gvals['cox_f_per_m']['value']
    gate.cqe_f_per_m = gvals['cqe_f_per_m']['value']
    gate.cinv_f_per_m = gvals['cinv_f_per_m']['value']
    gate.derived_at = stamp
    gate.provenance_json = json.dumps(
        {k: {kk: vv for kk, vv in v.items() if kk != 'value'}
         for k, v in gvals.items()})
    _save(manager, gate)

    # Contact: the quantum floor the prior can never beat (D9).
    contact.rq_floor_ohm = lit_value('rq_half_ohm')
    contact.derived_at = stamp
    contact.provenance_json = json.dumps({
        'rq_floor': LIT['rq_half_ohm']['source'],
        'rc_prior': contact.rc_source})
    _save(manager, contact)

    # SCE + VS parameters onto the transport row.
    sce = sce_parameters(geo.lg_nm, gate.t_ox_nm, mat.diameter_nm,
                         gate.k_ox, mat.eg_ev, transport.efsd_ev)
    params = build_vs_params(
        {'diameter_nm': mat.diameter_nm, 'eg_ev': mat.eg_ev},
        {'lg_nm': geo.lg_nm},
        {'t_ox_nm': gate.t_ox_nm, 'k_ox': gate.k_ox},
        {'rc_ohm': contact.rc_ohm},
        {'vt0_v': transport.vt0_v, 'efsd_ev': transport.efsd_ev},
        device.temperature_k)
    transport.vxo_m_per_s = params['vxo_m_per_s']
    transport.mu_cm2_per_vs = params['mu_m2_per_vs'] * 1e4
    transport.n_ss = sce['n_ss']
    transport.dibl_v_per_v = sce['dibl_v_per_v']
    transport.dvt_v = sce['dvt_v']
    transport.lambda_nm = sce['lambda_nm']
    transport.equation_revision = EQUATION_REVISION
    for key, val in MODEL_LABEL.items():
        if hasattr(transport, key):
            setattr(transport, key, val)
    transport.derived_at = stamp
    transport.provenance_json = json.dumps({
        'model_label': MODEL_LABEL,
        'vxo': LIT['lambda_v_nm']['source'],
        'mu': LIT['mu0_cm2_per_vs']['source'],
        'sce': '[VS1] eq.(8) via eq.(7) scale length',
        'priors': {'vt0_v': transport.vt0_source,
                   'efsd_ev': transport.efsd_source}})
    _save(manager, transport)

    # D8: one row per parameter, role-tagged.
    if parameter_factory is None:
        from cntfet.cnt_basis import CNTFETParameterRow
        parameter_factory = CNTFETParameterRow
    stamped = []

    def stamp_row(parameter, rec):
        _stamp_parameter(manager, parameter_factory, device.name,
                         parameter, rec, stamp)
        stamped.append(parameter)

    # physical inputs
    stamp_row('chirality_n', {
        'value': mat.chirality_n, 'unit': '1', 'role': 'physical',
        'source': 'seed/design choice', 'confidence': 'high'})
    stamp_row('chirality_m', {
        'value': mat.chirality_m, 'unit': '1', 'role': 'physical',
        'source': 'seed/design choice', 'confidence': 'high'})
    stamp_row('lg_nm', {
        'value': geo.lg_nm, 'unit': 'nm', 'role': 'physical',
        'source': 'design choice ([VS1] calibration flagship)',
        'confidence': 'high'})
    stamp_row('t_ox_nm', {
        'value': gate.t_ox_nm, 'unit': 'nm', 'role': 'physical',
        'source': 'design choice', 'confidence': 'high'})
    stamp_row('k_ox', {
        'value': gate.k_ox, 'unit': '1', 'role': 'physical',
        'source': '[VS1] Fig.5 context (HfO2 k=16)',
        'confidence': 'medium'})
    stamp_row('temperature_k', {
        'value': device.temperature_k, 'unit': 'K',
        'role': 'physical', 'source': 'S1: one temperature',
        'confidence': 'high'})
    # derived
    for parameter, rec in {**mvals, **gvals}.items():
        if parameter == 'semiconducting':
            continue
        stamp_row(parameter, rec)
    for parameter, value, unit in (
            ('lambda_nm', sce['lambda_nm'], 'nm'),
            ('n_ss', sce['n_ss'], '1'),
            ('dibl_v_per_v', sce['dibl_v_per_v'], 'V/V'),
            ('dvt_v', sce['dvt_v'], 'V'),
            ('vxo_m_per_s', params['vxo_m_per_s'], 'm/s'),
            ('mu_cm2_per_vs', params['mu_m2_per_vs'] * 1e4,
             'cm^2/(V s)')):
        source = ('[VS1] eq.(7)/(8)' if parameter in
                  ('lambda_nm', 'n_ss', 'dibl_v_per_v', 'dvt_v')
                  else '[VS1] eq.(9)' if parameter == 'vxo_m_per_s'
                  else '[VS1] eq.(4)')
        stamp_row(parameter, {
            'value': value, 'unit': unit, 'role': 'derived',
            'source': source, 'confidence': 'medium',
            'derived_from': 'S1a derivations'})
    # compact-model constants + calibration priors
    for parameter, key in (('alpha_vs', 'alpha_vs'),
                           ('beta_vs', 'beta_vs'),
                           ('lambda_v_nm', 'lambda_v_nm'),
                           ('vB0_m_per_s', 'vB0_m_per_s')):
        rec = LIT[key]
        stamp_row(parameter, {
            'value': rec['value'], 'unit': rec['unit'],
            'role': rec['role'], 'source': rec['source'],
            'confidence': rec['confidence']})
    stamp_row('vt0_v', {
        'value': transport.vt0_v, 'unit': 'V',
        'role': 'calibration', 'source': transport.vt0_source,
        'confidence': 'low'})
    stamp_row('efsd_ev', {
        'value': transport.efsd_ev, 'unit': 'eV',
        'role': 'calibration', 'source': transport.efsd_source,
        'confidence': 'low'})
    stamp_row('rc_ohm', {
        'value': contact.rc_ohm, 'unit': 'ohm',
        'role': 'calibration', 'source': contact.rc_source,
        'confidence': contact.rc_confidence,
        'notes': 'first-class (D9); never folded into mobility'})
    stamp_row('rq_floor_ohm', {
        'value': contact.rq_floor_ohm, 'unit': 'ohm',
        'role': 'physical', 'source': LIT['rq_half_ohm']['source'],
        'confidence': 'high'})

    device.derived_at = stamp
    device.provenance_json = json.dumps({
        'modelLabel': MODEL_LABEL,
        'components': {key: getattr(rows[key], 'name', '')
                       for key in rows},
        'parameterRows': stamped,
        'honesty': {
            'ss_interface_states': '[VS1] eq.(8) excludes '
                'oxide-CNT interface non-idealities; measured SS '
                '(135 mV/dec on [FC10]) WILL exceed the derived '
                'n_ss * 60 mV/dec',
            'vt0': 'uncalibrated prior', 'scope': 'S1: DC only, '
                'one tube; no variability, no multi-tube, no '
                'BTBT/S-D tunneling (S2+)'}})
    _save(manager, device)
    return {'ok': True, 'device': device.name, 'derivedAt': stamp,
            'parameters': params, 'sce': sce,
            'parameterRows': len(stamped),
            'modelLabel': MODEL_LABEL}


def run_iv(manager, device, engine='vs', vg_list=None, vd_list=None,
           transmission_mode='acoustic-mfp', result_factory=None):
    """One Id-Vg/Id-Vd family run -> CNTFETSimResult row. Engines:
    'vs' (F1 compact, the S1 deliverable) | 'tob' (F2 reference)."""
    if not getattr(device, 'derived_at', ''):
        return {'ok': False, 'error': 'device never derived — POST '
                                      '{"action": "derive"} first'}
    rows, missing = resolve_components(manager, device)
    if missing:
        return {'ok': False,
                'error': f'missing component rows: {missing}'}
    mat, geo = rows['material'], rows['geometry']
    gate, contact = rows['gate_stack'], rows['contact']
    transport = rows['transport']
    vg_list = vg_list or [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6]
    vd_list = vd_list or [0.05, 0.1, 0.2, 0.3, 0.4, 0.5]
    if engine == 'vs':
        params = build_vs_params(
            {'diameter_nm': mat.diameter_nm, 'eg_ev': mat.eg_ev},
            {'lg_nm': geo.lg_nm},
            {'t_ox_nm': gate.t_ox_nm, 'k_ox': gate.k_ox},
            {'rc_ohm': contact.rc_ohm},
            {'vt0_v': transport.vt0_v,
             'efsd_ev': transport.efsd_ev},
            device.temperature_k)
        family = iv_family(params, vg_list, vd_list)
        fidelity = 'VS_MINIMAL'
    elif engine == 'tob':
        p = {'eg_ev': mat.eg_ev, 'vf_m_per_s': mat.vf_m_per_s,
             'lg_nm': geo.lg_nm, 'cox_f_per_m': gate.cox_f_per_m,
             'temperature_k': device.temperature_k,
             # eta0 aligned with the vt0 prior for VS-vs-F2
             # comparability (alpha_G ~ 1) — documented mapping,
             # not a hidden fit.
             'eta0_ev': transport.vt0_v,
             'cd_over_cg': transport.dibl_v_per_v,
             'transmission_mode': transmission_mode}
        family = tob_iv(p, vg_list, vd_list)
        fidelity = 'TOB_F2'
    else:
        return {'ok': False, 'error': f'unknown engine "{engine}" '
                                      '(vs | tob)'}
    stamp = _now()
    if result_factory is None:
        from cntfet.cnt_basis import CNTFETSimResult
        result_factory = CNTFETSimResult
    verdict = ('family-computed' if family['all_converged']
               else 'NOT-CONVERGED — do not trust these points')
    row = result_factory(
        name=f'{device.name}-{engine}-iv-'
             f'{stamp[11:19].replace(":", "")}',
        device=device.name, kind='iv-family', engine=family['engine'],
        physics_fidelity=fidelity,
        inputs_json=json.dumps({'vg': vg_list, 'vd': vd_list}),
        series_json=json.dumps(family['points']),
        metrics_json=json.dumps({
            'allConverged': family['all_converged'],
            'pointCount': len(family['points'])}),
        verdict=verdict, ran_at=stamp, notes='', manager=manager)
    _save(manager, row)
    return {'ok': family['all_converged'], 'device': device.name,
            'engine': family['engine'], 'fidelity': fidelity,
            'points': family['points'], 'verdict': verdict,
            'resultRow': row.name}
