"""
@module cntfet.cnt_triangle

S2b: the validation-triangle edge between F1 (VS compact) and F2
(ToB quasi-ballistic) — the two engines evaluated from the SAME
device rows over the same grid, disagreement recorded per point
and per metric. Two edges, because they answer different
questions:

  intrinsic edge   VS with Rc = 0  vs  ToB (ToB has no contacts)
                   — pure transport-model disagreement
  terminal edge    VS with the real Rc prior  vs  ToB
                   — labeled contact-dominated; NOT a model error

Adaptive-oracle groundwork (plan D12 corollary): grid points whose
intrinsic-edge disagreement exceeds the threshold become the
recorded F3 target list — when the Kwant kernel lands (S2+/D13),
NEGF spend goes exactly there, not on a blanket sweep.

@consumers
  - cntfet.cnt_api ({action: triangle})
  - cntfet.selftest_cntfet
"""

import json
import math
from datetime import datetime, timezone

from cntfet.cnt_derive import resolve_components
from cntfet.cnt_metrics import extract_metrics
from cntfet.cnt_tob import tob_operating_point
from cntfet.cnt_vs_model import build_vs_params, vs_terminal_current

#: Disagreement metric: |log10(I_vs / I_tob)| where both sides are
#: above the floor. 0.3 dex = a factor of 2.
DISAGREEMENT_THRESHOLD_DEX = 0.3
CURRENT_FLOOR_A = 1e-13


def _engines(device, rows, transmission_mode):
    """Three Id(vg, vd) callables from the shared rows."""
    mat, geo = rows['material'], rows['geometry']
    gate, contact = rows['gate_stack'], rows['contact']
    transport = rows['transport']

    def params(rc_ohm):
        return build_vs_params(
            {'diameter_nm': mat.diameter_nm, 'eg_ev': mat.eg_ev},
            {'lg_nm': geo.lg_nm},
            {'t_ox_nm': gate.t_ox_nm, 'k_ox': gate.k_ox},
            {'rc_ohm': rc_ohm},
            {'vt0_v': transport.vt0_v,
             'efsd_ev': transport.efsd_ev},
            device.temperature_k)
    p_full = params(contact.rc_ohm)
    p_intrinsic = params(0.0)
    p_tob = {'eg_ev': mat.eg_ev, 'vf_m_per_s': mat.vf_m_per_s,
             'lg_nm': geo.lg_nm, 'cox_f_per_m': gate.cox_f_per_m,
             'temperature_k': device.temperature_k,
             'eta0_ev': transport.vt0_v,
             'cd_over_cg': transport.dibl_v_per_v,
             'transmission_mode': transmission_mode}
    return {
        'vs-terminal': lambda vg, vd:
            vs_terminal_current(vg, vd, p_full)['id_a'],
        'vs-intrinsic': lambda vg, vd:
            vs_terminal_current(vg, vd, p_intrinsic)['id_a'],
        'tob-intrinsic': lambda vg, vd:
            tob_operating_point(vg, vd, p_tob)['id_a'],
    }


def _dex(i_a, i_b):
    if i_a <= CURRENT_FLOOR_A or i_b <= CURRENT_FLOOR_A:
        return None
    return abs(math.log10(i_a / i_b))


def validation_triangle(manager, device, vg_list=None, vd_list=None,
                        transmission_mode='acoustic-mfp',
                        threshold_dex=DISAGREEMENT_THRESHOLD_DEX,
                        result_factory=None):
    """Run both engines over the grid; record per-point edges,
    per-metric comparison, and the adaptive-oracle target list."""
    if not getattr(device, 'derived_at', ''):
        return {'ok': False, 'error': 'device never derived — POST '
                                      '{"action": "derive"} first'}
    rows, missing = resolve_components(manager, device)
    if missing:
        return {'ok': False,
                'error': f'missing component rows: {missing}'}
    vg_list = vg_list or [0.0, 0.15, 0.3, 0.45, 0.6]
    vd_list = vd_list or [0.05, 0.15, 0.3, 0.45, 0.6]
    engines = _engines(device, rows, transmission_mode)

    points = []
    oracle_targets = []
    worst = {'dex': 0.0, 'at': None}
    for vg in vg_list:
        for vd in vd_list:
            i_vs = engines['vs-intrinsic'](vg, vd)
            i_tob = engines['tob-intrinsic'](vg, vd)
            i_term = engines['vs-terminal'](vg, vd)
            intrinsic_dex = _dex(i_vs, i_tob)
            entry = {'vg_v': vg, 'vd_v': vd,
                     'id_vs_intrinsic_a': i_vs,
                     'id_tob_a': i_tob,
                     'id_vs_terminal_a': i_term,
                     'intrinsicEdgeDex': intrinsic_dex,
                     'belowFloor': intrinsic_dex is None}
            points.append(entry)
            if intrinsic_dex is not None:
                if intrinsic_dex > worst['dex']:
                    worst = {'dex': intrinsic_dex,
                             'at': {'vg': vg, 'vd': vd}}
                if intrinsic_dex > threshold_dex:
                    oracle_targets.append(
                        {'vg_v': vg, 'vd_v': vd,
                         'dex': intrinsic_dex})
    metrics = {name: extract_metrics(fn)
               for name, fn in engines.items()}
    deltas = {}
    for key in ('ss_mv_per_dec', 'dibl_mv_per_v', 'ion_a',
                'gm_peak_s'):
        a = metrics['vs-intrinsic'].get(key)
        b = metrics['tob-intrinsic'].get(key)
        deltas[key] = (None if a is None or b is None or not b
                       else (a - b) / b)
    stamp = datetime.now(timezone.utc).isoformat()
    report = {
        'ok': True, 'device': device.name,
        'transmissionMode': transmission_mode,
        'thresholdDex': threshold_dex,
        'points': points,
        'worstIntrinsicDex': worst,
        'oracleTargets': oracle_targets,
        'metrics': metrics,
        'metricDeltasIntrinsic': deltas,
        'honesty': {
            'edges': 'intrinsic edge = VS(Rc=0) vs ToB (fair); '
                     'terminal edge carries the Rc drop by design',
            'tob_limits': 'ToB is energy-independent-T, no OP '
                          'scattering, no BTBT — expect the '
                          'high-Vd corner to disagree; that is '
                          'what the F3 oracle is FOR',
            'oracle_status': 'F3 (Kwant) NOT built — targets are '
                             'recorded, not evaluated (D13/S2+)',
            'quantum_bound': 'VS-intrinsic G_on may EXCEED G0 — '
                             'by design the VS family carries the '
                             'quantum resistance in Rs (RQ/2 per '
                             'terminal, [VS1] Sec.IV), not in the '
                             'channel; ToB respects the bound '
                             'natively. The intrinsic edge '
                             'compares transport SHAPE, never '
                             'absolute conductance.'},
    }
    if result_factory is None:
        from cntfet.cnt_basis import CNTFETSimResult
        result_factory = CNTFETSimResult
    row = result_factory(
        name=f'{device.name}-triangle-'
             f'{stamp[11:19].replace(":", "")}',
        device=device.name, kind='validation-triangle',
        engine='vs-python-reference vs tob-f2',
        physics_fidelity='VS_MINIMAL|TOB_F2',
        inputs_json=json.dumps({'vg': vg_list, 'vd': vd_list,
                                'transmissionMode':
                                    transmission_mode}),
        series_json=json.dumps(points),
        metrics_json=json.dumps({
            'worstIntrinsicDex': worst,
            'oracleTargetCount': len(oracle_targets),
            'metricDeltasIntrinsic': deltas}),
        verdict='edges-recorded', ran_at=stamp,
        notes=report['honesty']['edges'], manager=manager)
    try:
        db = getattr(manager, 'db', None)
        if db is not None:
            db.saveInstanceInDB(row)
    except Exception:
        pass
    report['resultRow'] = row.name
    return report
