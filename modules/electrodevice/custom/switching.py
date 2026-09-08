"""
@module electrodevice.custom.switching

Physical size + switching-speed STATE-SPACE analysis for the derived
devices (Dustin 2026-07-10).

Size: width = cross_section / film_thickness (both knobs), so every
device gets an honest footprint (L x W) with landmark comparisons —
low-sigma composite networks need WIDE geometry for switch-grade Ron,
and that truth belongs in the open.

Switching: the LED-switch stage as a piecewise-linear state-space
system x = [v_gate, v_drain]:

    dv_g/dt = (v_in - v_g) / (Rdrv * Cg)
    dv_d/dt = ((VDD' - v_d)/Rpull - v_d/Rch) / Cload

with Rch = Ron (gate above VTO) or Roff (below) — two triangular A
matrices whose EIGENVALUES are the phase time constants:

    lambda_g   = -1/(Rdrv*Cg)          gate charging
    lambda_d,on  = -(1/Rpull + 1/Ron)/Cload
    lambda_d,off = -(1/Rpull + 1/Roff)/Cload   (recovery via pull-up)

Cg = eps0 * eps_r * (W*L) / t_dielectric uses the STRUCTURED
permittivity record — and the analysis honestly compares its own
resulting max toggle rate against the frequency the eps_r was
measured at. An ngspice transient (.meas rise/fall) cross-checks the
analytic delays when the engine is available.

@consumers
  - electrodevice.device_api ({action: switching-analysis})
  - electrodevice.electrodevice_selftest
"""

import json
import math
import os
import re
import subprocess
import tempfile
from datetime import datetime, timezone

EPS0 = 8.8541878128e-12

#: Size landmarks for the physical view (meters).
LANDMARKS = [
    ('red blood cell', 8e-6), ('human hair width', 7e-5),
    ('salt grain', 3e-4), ('credit-card thickness', 7.6e-4),
    ('grain of rice', 6e-3), ('fingernail width', 1.2e-2),
]


def nearest_landmark(size_m):
    best = min(LANDMARKS, key=lambda l: abs(math.log10(size_m / l[1])))
    ratio = size_m / best[1]
    return f'{ratio:.1f}x {best[0]}'


def device_geometry(device):
    """The honest footprint from the geometry knobs."""
    length = float(device.length_m)
    area = float(device.cross_section_m2)
    thickness = float(getattr(device, 'film_thickness_m', 1e-6)
                      or 1e-6)
    width = area / thickness
    return {
        'channelLength_m': length,
        'filmThickness_m': thickness,
        'width_m': width,
        'footprint_m2': length * width,
        'lengthScale': nearest_landmark(length),
        'widthScale': nearest_landmark(width),
        'note': 'width = cross_section/film_thickness — low-sigma '
                'composite channels need WIDE geometry for '
                'switch-grade Ron',
    }


def state_space_switching(device, dielectric, rdrv_ohm=33.0,
                          cload_f=1e-11, vdd=3.3,
                          rpull_ohm=628.6):
    """Piecewise-linear state-space analysis of the low-side LED
    switch stage. Returns matrices, eigenvalues, per-phase time
    constants, on/off delays, and the honest max toggle rate."""
    geometry = device_geometry(device)
    eps_r = float(dielectric.get('epsilonR') or 3.9)
    t_ox = float(device.dielectric_thickness_m)
    gate_area = geometry['width_m'] * geometry['channelLength_m']
    c_gate = EPS0 * eps_r * gate_area / t_ox
    vto = abs(float(device.threshold_v))
    r_on = float(device.r_on_ohm)
    r_off = float(device.r_off_ohm)

    tau_g = rdrv_ohm * c_gate
    lam_g = -1.0 / tau_g
    lam_on = -(1.0 / rpull_ohm + 1.0 / r_on) / cload_f
    lam_off = -(1.0 / rpull_ohm + 1.0 / r_off) / cload_f
    tau_on = -1.0 / lam_on
    tau_off = -1.0 / lam_off

    # Gate crossing VTO: rising v_g = vdd(1-e^-t/tau); falling
    # v_g = vdd e^-t/tau. Then the drain settles (2.3 tau = 90%).
    t_gate_rise = tau_g * math.log(vdd / (vdd - vto))
    t_gate_fall = tau_g * math.log(vdd / vto)
    t_on = t_gate_rise + 2.3 * tau_on
    t_off = t_gate_fall + 2.3 * tau_off
    f_max = 1.0 / (3.0 * (t_on + t_off))

    eps_f = ((dielectric.get('measurementContext') or {})
             .get('frequency_hz'))
    freq_note = ''
    if eps_f and f_max > float(eps_f):
        freq_note = (f'max toggle {f_max:.3g} Hz EXCEEDS the '
                     f'frequency eps_r was measured at '
                     f'({float(eps_f):.3g} Hz) — the gate '
                     'capacitance number is extrapolated there')

    return {
        'geometry': geometry,
        'gateCapacitance_F': c_gate,
        'stateSpace': {
            'states': ['v_gate', 'v_drain'],
            'A_on': [[lam_g, 0.0],
                     [1.0 / (rpull_ohm * cload_f) * 0.0, lam_on]],
            'A_off': [[lam_g, 0.0], [0.0, lam_off]],
            'B': [[1.0 / (rdrv_ohm * c_gate)],
                  [1.0 / (rpull_ohm * cload_f)]],
            'eigenvalues_on': [lam_g, lam_on],
            'eigenvalues_off': [lam_g, lam_off],
            'note': 'piecewise-linear: Rch switches Ron/Roff at '
                    'v_gate = VTO; triangular A -> eigenvalues are '
                    'the diagonal rates',
        },
        'timeConstants_s': {'gate': tau_g, 'drainOn': tau_on,
                            'drainOff': tau_off},
        'delays_s': {'turnOn': t_on, 'turnOff': t_off,
                     'gateToVto_rise': t_gate_rise,
                     'gateToVto_fall': t_gate_fall},
        'maxToggle_Hz': f_max,
        'assumptions': {
            'rdrv_ohm': rdrv_ohm, 'cload_F': cload_f, 'vdd': vdd,
            'rpull_ohm': rpull_ohm,
            'model': 'level-1 switch, piecewise-linear phases; '
                     'Cload lumps LED junction + wiring',
        },
        'frequencyContextNote': freq_note,
    }


def ngspice_transient_check(binary, switch_card, resistor_card,
                            sub_switch, sub_resistor, analysis,
                            vdd=3.3):
    """Cross-check the analytic delays with a real ngspice .tran:
    pulse the gate driver, measure drain fall/rise times."""
    tau = max(analysis['delays_s']['turnOn'],
              analysis['delays_s']['turnOff'])
    stop = max(tau * 40, 1e-9)
    step = stop / 4000
    c_gate = analysis['gateCapacitance_F']
    rdrv = analysis['assumptions']['rdrv_ohm']
    cload = analysis['assumptions']['cload_F']
    netlist = '\n'.join([
        '* switching transient cross-check',
        switch_card, resistor_card,
        '.model polari_led D(Is=1e-18 N=1.8 Rs=2)',
        f'Vdd vdd 0 DC {vdd}',
        f'Vin in 0 PULSE(0 {vdd} {stop / 4:.4g} 1p 1p '
        f'{stop / 2:.4g} {stop:.4g})',
        f'Rdrv in gate {rdrv}',
        f'Cg gate 0 {c_gate:.6g}',
        f'Xr vdd anode {sub_resistor}',
        'Dled anode drain polari_led',
        f'Xsw drain gate 0 {sub_switch}',
        f'Cl drain 0 {cload:.6g}',
        '.tran ' + f'{step:.4g} {stop:.4g}',
        '.control', 'run',
        # meas as a CONTROL command: deck-level .meas does not
        # auto-execute when a .control block owns the batch run.
        # 70%/10%: the off-state drain idles ~0.7 V below vdd (the
        # Roff leakage biases the LED near its knee), so higher
        # triggers sit outside the actual swing.
        f'meas tran tfall TRIG v(drain) VAL={vdd * 0.7:.3f} FALL=1 '
        f'TARG v(drain) VAL={vdd * 0.1:.3f} FALL=1',
        'quit', '.endc', '.end', ''])
    with tempfile.TemporaryDirectory() as td:
        path = os.path.join(td, 'sw.cir')
        with open(path, 'w') as f:
            f.write(netlist)
        proc = subprocess.run([binary, '-b', path],
                              capture_output=True, text=True,
                              timeout=180)
    match = re.search(r'tfall\s*=\s*([-+0-9.eE]+)',
                      proc.stdout + proc.stderr)
    if not match:
        return {'ok': False,
                'note': 'transient ran but tfall not measured '
                        '(drain may not cross the thresholds)'}
    measured = float(match.group(1))
    return {'ok': True, 'drainFall_s': measured,
            'analyticTurnOn_s': analysis['delays_s']['turnOn'],
            'agreementNote': 'drain fall (turn-ON of the low-side '
                             'switch) vs the analytic turn-on delay '
                             '— same order expected, not identical '
                             '(pulse edge + diode nonlinearity)'}


def run_switching_analysis(manager, device, rdrv_ohm=33.0,
                           cload_f=1e-11, vdd=3.3,
                           result_factory=None):
    """The knob act: analyze, cross-check, save the row."""
    if not getattr(device, 'derived_at', ''):
        return {'ok': False,
                'error': f'device "{device.name}" has never been '
                         'derived'}
    if device.device_type not in ('nfet', 'pfet'):
        return {'ok': False,
                'error': 'switching analysis applies to transistors'}
    prov = json.loads(device.provenance_json or '{}')
    dielectric = prov.get('dielectric', {})
    from electrodevice.custom.device_derive import get_device, render_card, \
        subckt_name
    resistor = get_device(manager, 'cnt-solgel-led-resistor')
    rpull = (float(resistor.resistance_ohm)
             if resistor is not None and resistor.derived_at
             else 628.6)
    analysis = state_space_switching(device, dielectric,
                                     rdrv_ohm=rdrv_ohm,
                                     cload_f=cload_f, vdd=vdd,
                                     rpull_ohm=rpull)
    from electrodevice.custom.spice_run import ngspice_bin
    binary = ngspice_bin()
    if binary and resistor is not None:
        if device.device_type == 'nfet':
            analysis['transientCrossCheck'] = ngspice_transient_check(
                binary, render_card(device), render_card(resistor),
                subckt_name(device), subckt_name(resistor), analysis,
                vdd=vdd)
        else:
            analysis['transientCrossCheck'] = {
                'ok': False,
                'note': 'the transient cross-check topology is the '
                        'n-channel LOW-SIDE stage — a pfet needs the '
                        'high-side topology (not built yet); '
                        'analytic state-space numbers stand alone'}
    if result_factory is None:
        from electrodevice.device_basis import CircuitRunResult
        result_factory = CircuitRunResult
    stamp = datetime.now(timezone.utc).isoformat()
    row = result_factory(
        name=f'{device.name}-sw-analysis-'
             f'{stamp[11:19].replace(":", "")}',
        device_name=device.name, circuit='switching-state-space',
        inputs_json=json.dumps(analysis['assumptions']),
        outputs_json=json.dumps({k: v for k, v in analysis.items()
                                 if k != 'assumptions'}),
        verdict=f"maxToggle {analysis['maxToggle_Hz']:.3g} Hz",
        engine='state-space (+ngspice tran)' if binary
               else 'state-space (analytic only)',
        ran_at=stamp, notes='', manager=manager)
    try:
        db = getattr(manager, 'db', None)
        if db is not None:
            db.saveInstanceInDB(row)
    except Exception:
        pass
    analysis['ok'] = True
    analysis['resultRow'] = row.name
    return analysis
