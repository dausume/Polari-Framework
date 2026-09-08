"""
@module cntfet.custom.cnt_inverter

S4a: the FIRST circuit rung — a complementary CNFET inverter built
from TWO OSDI instances of the clean-room model (the n-device plus
its mirrored p-twin, r2 polarity), swept in ngspice for the VTC.
Plan D10's minimal cell set starts at INV; this is its DC half
(delay/energy need the charge model — S4b+).

Measured from the VTC (definitions ride the result):
  VM      the Vout = Vin crossing (switching threshold)
  gain    max |dVout/dVin| (central difference on the sweep)
  VIL/VIH the unity-gain points; NML = VIL - VOL, NMH = VOH - VIH
  swing   VOH - VOL (VOH = Vout at Vin=0, VOL = Vout at Vin=VDD)

Honesty: the p-device is the SAME device mirrored ([VS1] premise
ii) with the same Rc prior — a real line's p/n asymmetry (work
functions, contact metals) is variability work that rides the S3
process objects when measured. Refuses when openvaf/ngspice are
absent (capability endpoint says the same).

@consumers
  - cntfet.cnt_api ({action: inverter})
  - cntfet.cntfet_selftest (honest-skip leg)
"""

import json
import os
import subprocess
import tempfile
from datetime import datetime, timezone

from cntfet.custom.cnt_derive import resolve_components
from cntfet.custom.cnt_osdi import (
    _model_card, compile_osdi, find_ngspice, run_ngspice,
)
from cntfet.custom.cnt_vs_model import build_vs_params


def _vtc_netlist(osdi_path, p_n, p_p, vdd, step):
    card_n, _ = _model_card(p_n)
    card_p, _ = _model_card(p_p)
    card_n = card_n.replace('.model cntmod ', '.model cntn ')
    card_p = card_p.replace('.model cntmod ', '.model cntp ')
    return '\n'.join([
        '* cntfet S4a complementary inverter VTC', card_n, card_p,
        '* ports: d g s',
        'Np out in vddnode cntp',
        'Nn out in 0 cntn',
        f'vdd vddnode 0 {vdd:.10g}',
        'vin in 0 0.0',
        '.options reltol=1e-6 abstol=1e-12 vntol=1e-6',
        '.control',
        f'pre_osdi {osdi_path}',
        f'dc vin 0 {vdd:.10g} {step:.10g}',
        'wrdata vtc.dat v(out)',
        'quit', '.endc', '.end', ''])


def _vtc_metrics(vin, vout, vdd):
    voh, vol = vout[0], vout[-1]
    # VM: Vout - Vin crossing by linear interpolation.
    vm = None
    for i in range(1, len(vin)):
        d0, d1 = vout[i-1] - vin[i-1], vout[i] - vin[i]
        if d0 >= 0.0 >= d1:
            frac = d0 / (d0 - d1) if d0 != d1 else 0.0
            vm = vin[i-1] + frac * (vin[i] - vin[i-1])
            break
    gains = []
    for i in range(1, len(vin) - 1):
        gains.append((vout[i+1] - vout[i-1])
                     / (vin[i+1] - vin[i-1]))
    peak_gain = min(gains) if gains else 0.0  # most negative
    # unity-gain points bracket the transition
    vil = vih = None
    for i, gain in enumerate(gains):
        if gain <= -1.0:
            vil = vin[i + 1]
            break
    for i in range(len(gains) - 1, -1, -1):
        if gains[i] <= -1.0:
            vih = vin[i + 1]
            break
    nml = (vil - vol) if vil is not None else None
    nmh = (voh - vih) if vih is not None else None
    return {'vm_v': vm, 'peakGain': peak_gain,
            'voh_v': voh, 'vol_v': vol, 'swing_v': voh - vol,
            'vil_v': vil, 'vih_v': vih,
            'nml_v': nml, 'nmh_v': nmh}


def run_inverter_vtc(manager, device, vdd=0.6, step=0.005,
                     workdir=None, result_factory=None):
    """Compile the twin once, sweep the complementary pair."""
    if not getattr(device, 'derived_at', ''):
        return {'ok': False, 'error': 'device never derived — POST '
                                      '{"action": "derive"} first'}
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
    workdir = workdir or tempfile.mkdtemp(prefix='cntfet-inv-')
    os.makedirs(workdir, exist_ok=True)
    compiled = compile_osdi(workdir)
    if not compiled.get('ok'):
        return compiled
    netlist = os.path.join(workdir, 'inverter-vtc.sp')
    with open(netlist, 'w') as fh:
        fh.write(_vtc_netlist(compiled['osdiPath'], p_n, p_p,
                              vdd, step))
    run = run_ngspice(ngspice_path, workdir, netlist, timeout=300)
    data = os.path.join(workdir, 'vtc.dat')
    if not os.path.isfile(data):
        return {'ok': False, 'error': 'ngspice produced no VTC',
                'stderr': run.stderr[-1500:]}
    vin, vout = [], []
    with open(data) as fh:
        for line in fh:
            parts = line.split()
            if len(parts) >= 2:
                vin.append(float(parts[0]))
                vout.append(float(parts[1]))
    if len(vin) < 10:
        return {'ok': False, 'error': f'VTC too short '
                                      f'({len(vin)} points)'}
    metrics = _vtc_metrics(vin, vout, vdd)
    stamp = datetime.now(timezone.utc).isoformat()
    inverts = (metrics['voh_v'] > 0.9 * vdd
               and metrics['vol_v'] < 0.1 * vdd)
    verdict = ('inverter-works' if inverts and metrics['vm_v']
               else 'NOT-INVERTING — check the pair')
    report = {
        'ok': bool(inverts), 'device': device.name, 'vdd_v': vdd,
        'points': len(vin), 'metrics': metrics,
        'verdict': verdict,
        'engine': f"ngspice OSDI ({compiled['compiler']})",
        'honesty': 'p-device = same device mirrored (r2); real '
                   'p/n asymmetry enters with measured process '
                   'data (S3 objects)',
        'workdir': workdir,
    }
    if result_factory is None:
        from cntfet.cnt_basis import CNTFETSimResult
        result_factory = CNTFETSimResult
    row = result_factory(
        name=f'{device.name}-inverter-'
             f'{stamp[11:19].replace(":", "")}',
        device=device.name, kind='inverter-vtc',
        engine=report['engine'], physics_fidelity='VS_MINIMAL',
        inputs_json=json.dumps({'vdd_v': vdd, 'step_v': step}),
        series_json=json.dumps(
            {'vin': vin[::4], 'vout': vout[::4]}),
        metrics_json=json.dumps(metrics), verdict=verdict,
        ran_at=stamp, notes=report['honesty'], manager=manager)
    try:
        db = getattr(manager, 'db', None)
        if db is not None:
            db.saveInstanceInDB(row)
    except Exception:
        pass
    report['resultRow'] = row.name
    return report
