"""
@module cntfet.custom.cnt_ring_oscillator

S4b: the 5-stage complementary ring oscillator — the first
DYNAMIC circuit result, possible only because r3 gave the twin its
eq.(11) terminal charge (a DC-only model cannot ring). Transient
in ngspice, period measured from the Vdd/2 crossings after
settling, stage delay = T/(2N).

Honesty labels that ride the result:
  - INTRINSIC-ONLY numbers: one-tube device charges are
    attofarad-scale and CNTParasitics is 0 at S1 scope — real
    interconnect/fringe loading (S2+/[VS2]) will slow this by
    orders of magnitude. The value here is the intrinsic bound +
    the machinery, not a product claim (plan D1).
  - the 50/50 charge partition is delay-grade (cnt_charge
    PARTITION_NOTE rides along).

@consumers
  - cntfet.cnt_api ({action: ring-oscillator})
  - cntfet.cntfet_selftest (honest-skip leg)
"""

import json
import os
import subprocess
import tempfile
from datetime import datetime, timezone

from cntfet.custom.cnt_charge import PARTITION_NOTE
from cntfet.custom.cnt_derive import resolve_components
from cntfet.custom.cnt_osdi import _model_card, compile_osdi, find_ngspice, run_ngspice
from cntfet.custom.cnt_vs_model import build_vs_params


def _ro_netlist(osdi_path, p_n, p_p, vdd, stages, tstep_s, tstop_s):
    card_n, _ = _model_card(p_n)
    card_p, _ = _model_card(p_p)
    card_n = card_n.replace('.model cntmod ', '.model cntn ')
    card_p = card_p.replace('.model cntmod ', '.model cntp ')
    lines = ['* cntfet S4b ring oscillator', card_n, card_p,
             f'vdd vddnode 0 {vdd:.10g}']
    for i in range(stages):
        node_in = f'n{i}'
        node_out = f'n{(i + 1) % stages}'
        lines.append(f'Np{i} {node_out} {node_in} vddnode cntp')
        lines.append(f'Nn{i} {node_out} {node_in} 0 cntn')
    lines += [
        f'.ic v(n0)={vdd:.10g}',
        '.options reltol=1e-4 abstol=1e-12 vntol=1e-6',
        '.control',
        f'pre_osdi {osdi_path}',
        f'tran {tstep_s:.3e} {tstop_s:.3e} uic',
        'wrdata ro.dat v(n0)',
        'quit', '.endc', '.end', '']
    return '\n'.join(lines)


def _measure_period(times, volts, vdd, settle_fraction=0.4):
    """Mean period from rising Vdd/2 crossings after settling."""
    half = vdd / 2.0
    t_settle = times[-1] * settle_fraction
    crossings = []
    for i in range(1, len(times)):
        if times[i] < t_settle:
            continue
        if volts[i-1] < half <= volts[i]:
            frac = (half - volts[i-1]) / (volts[i] - volts[i-1])
            crossings.append(times[i-1]
                            + frac * (times[i] - times[i-1]))
    if len(crossings) < 3:
        return None, len(crossings)
    periods = [b - a for a, b in zip(crossings, crossings[1:])]
    return sum(periods) / len(periods), len(crossings)


def run_ring_oscillator(manager, device, vdd=0.6, stages=5,
                        workdir=None, result_factory=None):
    if not getattr(device, 'derived_at', ''):
        return {'ok': False, 'error': 'device never derived — POST '
                                      '{"action": "derive"} first'}
    if stages % 2 == 0 or stages < 3:
        return {'ok': False, 'error': 'stages must be odd and >= 3'}
    ngspice_path, why = find_ngspice()
    if ngspice_path is None:
        return {'ok': False, 'refusal': why}
    rows, missing = resolve_components(manager, device)
    if missing:
        return {'ok': False,
                'error': f'missing component rows: {missing}'}
    mat, geo = rows['material'], rows['geometry']
    gate, contact = rows['gate_stack'], rows['contact']
    transport = rows['transport']
    params = build_vs_params(
        {'diameter_nm': mat.diameter_nm, 'eg_ev': mat.eg_ev},
        {'lg_nm': geo.lg_nm},
        {'t_ox_nm': gate.t_ox_nm, 'k_ox': gate.k_ox},
        {'rc_ohm': contact.rc_ohm},
        {'vt0_v': transport.vt0_v, 'efsd_ev': transport.efsd_ev},
        device.temperature_k)
    p_n = {**params, 'ptype': 0}
    p_p = {**params, 'ptype': 1}
    workdir = workdir or tempfile.mkdtemp(prefix='cntfet-ro-')
    os.makedirs(workdir, exist_ok=True)
    compiled = compile_osdi(workdir)
    if not compiled.get('ok'):
        return compiled
    # Coarse intrinsic-delay estimate sets the time base:
    # tau ~ Cgg Lg Vdd / Ion  (+ Rc C); sweep two decades around it.
    cgg_f = params['cinv_f_per_m'] * params['lg_m']
    from cntfet.custom.cnt_vs_model import vs_terminal_current
    ion = vs_terminal_current(vdd, vdd, p_n)['id_a']
    tau_est = max(cgg_f * vdd / max(ion, 1e-12),
                  (p_n['rs_ohm'] + p_n['rd_ohm']) * cgg_f)
    tstop = 400.0 * tau_est * stages
    tstep = tau_est / 20.0
    netlist = os.path.join(workdir, 'ring-oscillator.sp')
    with open(netlist, 'w') as fh:
        fh.write(_ro_netlist(compiled['osdiPath'], p_n, p_p, vdd,
                             stages, tstep, tstop))
    run = run_ngspice(ngspice_path, workdir, netlist, timeout=600)
    data = os.path.join(workdir, 'ro.dat')
    if not os.path.isfile(data):
        return {'ok': False, 'error': 'ngspice produced no RO '
                'waveform', 'stderr': run.stderr[-1500:]}
    times, volts = [], []
    with open(data) as fh:
        for line in fh:
            parts = line.split()
            if len(parts) >= 2:
                times.append(float(parts[0]))
                volts.append(float(parts[1]))
    if len(times) < 100:
        return {'ok': False,
                'error': f'waveform too short ({len(times)} pts)',
                'stderr': run.stderr[-800:]}
    period, crossing_count = _measure_period(times, volts, vdd)
    stamp = datetime.now(timezone.utc).isoformat()
    if period is None:
        report = {'ok': False, 'device': device.name,
                  'error': f'no sustained oscillation (only '
                           f'{crossing_count} crossings) — the '
                           'ring did not ring',
                  'workdir': workdir}
        verdict = 'NOT-OSCILLATING'
        metrics = {'crossings': crossing_count}
    else:
        frequency = 1.0 / period
        stage_delay = period / (2.0 * stages)
        metrics = {'period_s': period, 'frequency_hz': frequency,
                   'stage_delay_s': stage_delay,
                   'stages': stages, 'crossings': crossing_count,
                   'tau_estimate_s': tau_est}
        verdict = 'oscillates'
        report = {'ok': True, 'device': device.name, 'vdd_v': vdd,
                  'metrics': metrics, 'verdict': verdict,
                  'engine': f"ngspice OSDI "
                            f"({compiled['compiler']})",
                  'honesty': ['INTRINSIC-ONLY: no parasitics '
                              '(S2+/[VS2]) — real loading slows '
                              'this by orders of magnitude; the '
                              'number is a bound, not a product '
                              'claim (D1)', PARTITION_NOTE],
                  'workdir': workdir}
    if result_factory is None:
        from cntfet.cnt_basis import CNTFETSimResult
        result_factory = CNTFETSimResult
    row = result_factory(
        name=f'{device.name}-ro-{stamp[11:19].replace(":", "")}',
        device=device.name, kind='ring-oscillator',
        engine=f"ngspice OSDI ({compiled['compiler']})",
        physics_fidelity='VS_MINIMAL+eq11-charge',
        inputs_json=json.dumps({'vdd_v': vdd, 'stages': stages}),
        series_json=json.dumps({'t': times[::20],
                                'v_n0': volts[::20]}),
        metrics_json=json.dumps(metrics), verdict=verdict,
        ran_at=stamp,
        notes='intrinsic-only; 50/50 charge partition '
              '(delay-grade)', manager=manager)
    try:
        db = getattr(manager, 'db', None)
        if db is not None:
            db.saveInstanceInDB(row)
    except Exception:
        pass
    report['resultRow'] = row.name
    return report
