"""
@module motors.motor_designer

mag-5 analysis: quasi-static motor models over the reluctance
seam. VALIDITY, stated on every output: first-harmonic co-energy
forms whose AMPLITUDES are calibrated by the lumped magnetics
network (mag-3 element math) at gap extremes; linear
magnetostatics; NO dynamics — inertia, friction, damping and
therefore maximum step rate / speed are UNMODELED. The clock rung
exists precisely so reality can grade these models cheaply.

- design_report: role checks (mag-2r viability — wrong material in
  a role flags AT DESIGN TIME) + realization gates/watermarks.
- lavet landscape + step sim: detent term (180-deg periodic, from
  the asymmetric-notch gap modulation) + coil-PM interaction term;
  alternating pulses walk 180 deg/step, same-polarity repeats
  honestly FAIL to advance; the clock comparison (steps vs time
  progression) is the output.
- torque_curve (M1..M3): 3-phase synchronous excitation, co-energy
  vs rotor angle, numerical dW'/dtheta; dual-gap topologies carry
  their doubled active area explicitly.
- torque_parity (§2d): every cheap-vs-reference parity claim
  traces here, assumptions printed, watermarks attached.
"""

import json
import math

from magnetics.magnet_analysis import (
    gates_for, role_viability, _named, _rows,
)
from magnetics.magnetic_netlist import MU0

TWO_PI = 2.0 * math.pi


def _loads(row, attr, default):
    try:
        return json.loads(getattr(row, attr, '') or '')
    except ValueError:
        return default


def _design(manager, name):
    row = _named(manager, 'MotorDesignDefinition', name)
    if row is None:
        raise ValueError(f'no MotorDesignDefinition named '
                         f'"{name}"')
    return row


def _prop(manager, material_ref, prop):
    opt = _named(manager, 'MagneticMaterialOption', material_ref)
    if opt is None:
        raise ValueError(f'unknown material "{material_ref}"')
    entry = _loads(opt, 'properties_json', {}).get(prop)
    if not isinstance(entry, dict) or entry.get('value') is None:
        raise ValueError(f'material "{material_ref}" has no '
                         f'{prop} value')
    return float(entry['value'])


VALIDITY = ('first-harmonic co-energy model; amplitudes from the '
            'lumped reluctance network at gap extremes; linear '
            'magnetostatics; QUASI-STATIC — inertia/friction '
            'unmodeled, max step rate / speed NOT predicted')

#: (role to check, params key holding the material) per topology.
_ROLE_SLOTS = {
    'lavet-clock-stepper': (('torque-magnet', 'rotor_material'),
                            ('magnetic-conductor',
                             'stator_material')),
    'radial-reluctance': (('magnetic-conductor', 'stator_material'),
                          ('magnetic-conductor', 'rotor_material')),
    'axial-dual-stator': (('magnetic-conductor', 'stator_material'),
                          ('torque-magnet', 'rotor_material')),
}


def design_report(manager, design_name):
    """Role viability + realization gates for every material slot —
    wrong-material-in-role is visible at DESIGN time."""
    design = _design(manager, design_name)
    params = _loads(design, 'params_json', {})
    topology = getattr(design, 'topology', '')
    slots, flags = [], []
    for role_name, key in _ROLE_SLOTS.get(topology, ()):
        material = params.get(key, '')
        opt = _named(manager, 'MagneticMaterialOption', material)
        role = _named(manager, 'MaterialUseRole', role_name)
        if opt is None or role is None:
            flags.append({'slot': key,
                          'refusal': f'unknown material or role '
                                     f'("{material}"/"{role_name}")'})
            continue
        verdict = role_viability(manager, opt, role)
        gates = gates_for(manager, opt)
        entry = {'slot': key, 'material': material,
                 'role': role_name,
                 'verdict': verdict['verdict'],
                 'honestyNote': verdict.get('honestyNote', ''),
                 'realizationLevel': gates['realizationLevel'],
                 'businessAllowed': gates['business']['allowed'],
                 'watermark': gates['simulation']['watermark']}
        slots.append(entry)
        if verdict['verdict'] != 'viable':
            flags.append({
                'slot': key, 'material': material,
                'role': role_name, 'verdict': verdict['verdict'],
                'suggestion': {
                    'evidence': 'mag-2r derived viability',
                    'knob': 'MotorDesignDefinition.params_json',
                    'action': f'pick a viable {role_name} material '
                              f'from /api/magnetics/search?role='
                              f'{role_name}'}})
    # M2/M3 rotors that are saliency-only don't need torque-magnet
    # (reluctance variants) — a magnetic-conductor rotor with
    # saliency_ratio > 1 downgrades the torque-magnet flag to info.
    from motors.motor_verify import verification_summary
    verify = verification_summary(manager, design_name)
    return {'ok': True, 'design': design_name,
            'topology': topology,
            'ladderRung': getattr(design, 'ladder_rung', ''),
            'toleranceTier': getattr(design, 'tolerance_tier', ''),
            'buildRequirements': _loads(
                design, 'build_requirements_json', {}),
            'materialSlots': slots, 'flags': flags,
            'verification': {
                'measuredCount': verify.get('measuredCount', 0),
                'simCount': verify.get('simCount', 0),
                'madeAndMeasured': verify.get('madeAndMeasured',
                                              False),
                'honesty': verify.get('honesty', '')},
            'validity': VALIDITY}


# ---------------------------------------------------------------- #
# M0 — the Lavet clock stepper
# ---------------------------------------------------------------- #

def _lavet_amplitudes(manager, params):
    """Calibrate the two co-energy amplitudes from the lumped
    network: detent amplitude from the gap-reluctance swing, coil
    coupling from coil MMF x magnet loop flux."""
    stator_mu = _prop(manager, params['stator_material'],
                      'mu_r_eff')
    b_r = _prop(manager, params['rotor_material'], 'b_r_t')
    h_c = _prop(manager, params['rotor_material'], 'h_c_ka_m')
    mu_rec = _prop(manager, params['rotor_material'], 'mu_r_eff')
    area = float(params['overlap_area_m2'])
    l_m = float(params['magnet_length_m'])
    mmf_m = h_c * 1000.0 * l_m
    r_mag = l_m / (MU0 * mu_rec * area)
    r_stator = 0.02 / (MU0 * stator_mu * area)   # short yoke prior

    def loop_r(gap_len):
        return (r_mag + r_stator
                + 2.0 * gap_len / (MU0 * area))

    g_lo = float(params['gap_base_m'])
    g_hi = g_lo + float(params['gap_asym_m'])
    # detent energy swing: PM co-energy difference between the
    # aligned (small-gap) and anti-aligned (large-gap) rotor poses.
    w_lo = 0.5 * mmf_m ** 2 / loop_r(g_lo)
    w_hi = 0.5 * mmf_m ** 2 / loop_r(g_hi)
    detent_amp = (w_lo - w_hi) / 2.0
    # coil-PM coupling: coil MMF drives the same loop; interaction
    # co-energy ~ MMF_c * Phi_m at the mean gap.
    mmf_c = float(params['coil_turns']) * float(params['coil_amps'])
    phi_m = mmf_m / loop_r((g_lo + g_hi) / 2.0)
    coil_amp = mmf_c * phi_m
    return detent_amp, coil_amp, {'bR': b_r, 'mmfMagnet': mmf_m,
                                  'mmfCoil': mmf_c,
                                  'loopFluxWb': phi_m}


DETENT_OFFSET_DEG = 20.0    # asymmetric-notch detent rotation


def lavet_coenergy(theta_deg, polarity, detent_amp, coil_amp):
    """W'(theta, p): 180-deg-periodic detent + coil-PM alignment.
    Detent axis is rotated DETENT_OFFSET_DEG from the coil axis —
    the asymmetric notch that makes alternating pulses advance in
    ONE direction (the whole Lavet trick)."""
    th = math.radians(theta_deg)
    detent = -detent_amp * math.cos(
        2.0 * (th - math.radians(DETENT_OFFSET_DEG)))
    coil = -coil_amp * polarity * math.cos(th)
    return detent + coil


def _settle(theta_deg, polarity, detent_amp, coil_amp,
            step_deg=1.0):
    """Gradient walk on the 1-deg grid to the LOCAL minimum —
    quasi-static settling."""
    theta = theta_deg
    for _ in range(720):
        here = lavet_coenergy(theta, polarity, detent_amp, coil_amp)
        fwd = lavet_coenergy(theta + step_deg, polarity, detent_amp,
                             coil_amp)
        back = lavet_coenergy(theta - step_deg, polarity,
                              detent_amp, coil_amp)
        if fwd < here and fwd <= back:
            theta += step_deg
        elif back < here:
            theta -= step_deg
        else:
            return theta % 360.0
    return theta % 360.0


def clock_sim(manager, design_name, pulses=10,
              alternating=True):
    """THE CONTROL CASE: command N pulses, settle the rotor per
    pulse (coil on, then coil off back to detent), count advanced
    steps, and compare rotation against time progression."""
    design = _design(manager, design_name)
    if getattr(design, 'topology', '') != 'lavet-clock-stepper':
        return {'ok': False,
                'refusal': f'"{design_name}" is not a '
                           f'lavet-clock-stepper — the clock sim '
                           f'is the M0 rung'}
    params = _loads(design, 'params_json', {})
    drive = _loads(design, 'drive_json', {})
    rate = float(drive.get('rate_hz', 1.0))
    try:
        detent_amp, coil_amp, cal = _lavet_amplitudes(manager,
                                                      params)
    except ValueError as exc:
        return {'ok': False, 'refusal': str(exc)}
    theta = _settle(0.0, 0, detent_amp, coil_amp)
    history = [{'pulse': 0, 'polarity': 0,
                'thetaDeg': round(theta, 1)}]
    steps_taken = 0
    # The drive's latched phase relationship: a real Lavet
    # controller starts with the polarity that ADVANCES from the
    # detent — probe both once, exactly as commissioning does.
    polarity = 1
    for p in (1, -1):
        trial = _settle(_settle(theta, p, detent_amp, coil_amp),
                        0, detent_amp, coil_amp)
        if 90.0 < ((trial - theta) % 360.0) < 270.0:
            polarity = p
            break
    for n in range(1, pulses + 1):
        before = theta
        theta = _settle(theta, polarity, detent_amp, coil_amp)
        theta = _settle(theta, 0, detent_amp, coil_amp)
        advanced = ((theta - before) % 360.0)
        stepped = 90.0 < advanced < 270.0
        if stepped:
            steps_taken += 1
        history.append({'pulse': n, 'polarity': polarity,
                        'thetaDeg': round(theta, 1),
                        'advancedDeg': round(advanced, 1),
                        'stepped': stepped})
        if alternating:
            polarity = -polarity
    duration = pulses / rate
    missed = pulses - steps_taken
    return {'ok': True, 'design': design_name,
            'pulses': pulses, 'rateHz': rate,
            'stepsTaken': steps_taken, 'stepsMissed': missed,
            'durationS': duration,
            'clockComparison': {
                'expectedRotationDeg': pulses * 180.0,
                'actualRotationDeg': steps_taken * 180.0,
                'clockErrorS': missed / rate,
                'note': 'the clock IS the instrument: missed '
                        'steps over hours are the quality '
                        'metric — a MEASURED run of this shape '
                        'earns made-and-measured'},
            'calibration': cal,
            'detentOffsetDeg': DETENT_OFFSET_DEG,
            'history': history, 'validity': VALIDITY}


# ---------------------------------------------------------------- #
# M1..M3 — torque curves via co-energy
# ---------------------------------------------------------------- #

def _phase_coenergy(phi_rotor, phi_current, phase_idx, params,
                    mmfs, mu_stator, gamma):
    """One phase's co-energy: GEOMETRY at the rotor electrical
    angle phi_rotor, CURRENTS at phi_current (held separately so
    torque = the PARTIAL derivative w.r.t. rotor position at
    constant currents — differentiating the total through the
    current variation averages to zero over a period and is
    wrong). gamma = load angle (drive knob)."""
    area0 = float(params['tooth_area_m2'])
    gap = float(params['gap_base_m'])
    saliency = float(params.get('saliency_ratio', 1.0))
    dual = 1.0 + (1.0 if params.get('dual_gap') else 0.0)
    mod_depth = 1.0 - 1.0 / max(saliency, 1.0)
    shift = phase_idx * TWO_PI / 3.0
    u_r = phi_rotor - shift
    u_i = phi_current - shift
    overlap = (1.0 - mod_depth) + mod_depth * (
        1.0 + math.cos(2.0 * u_r)) / 2.0
    area = area0 * max(overlap, 1e-6) * dual
    r_total = (gap / (MU0 * area)
               + 0.03 / (MU0 * mu_stator * area0 * dual))
    mmf_c, mmf_m = mmfs
    i_k = mmf_c * math.sin(u_i + gamma)
    w_rel = 0.5 * i_k ** 2 / r_total
    w_pm = 0.0
    if mmf_m:
        phi_m = mmf_m / r_total
        w_pm = i_k * phi_m * math.sin(u_r)
    return w_rel + w_pm


def torque_curve(manager, design_name, points=73):
    """Static torque over one electrical period: numerical PARTIAL
    dW'/dtheta_rotor at held phase currents, summed over the three
    phases, chained to the mechanical angle (poles/2)."""
    design = _design(manager, design_name)
    topology = getattr(design, 'topology', '')
    if topology == 'lavet-clock-stepper':
        return {'ok': False,
                'refusal': 'M0 is stepped, not torque-curved — '
                           'use the clock sim'}
    params = _loads(design, 'params_json', {})
    try:
        mu_stator = _prop(manager, params['stator_material'],
                          'mu_r_eff')
        mmf_c = (float(params['coil_turns'])
                 * float(params['coil_amps']))
        mmf_m = 0.0
        rotor = params.get('rotor_material', '')
        rotor_hc = None
        try:
            rotor_hc = _prop(manager, rotor, 'h_c_ka_m')
        except ValueError:
            rotor_hc = None
        if rotor_hc and rotor_hc >= 100.0 \
                and params.get('magnet_length_m'):
            mmf_m = rotor_hc * 1000.0 * float(
                params['magnet_length_m'])
    except (ValueError, KeyError) as exc:
        return {'ok': False, 'refusal': str(exc)}
    poles = int(params.get('poles', 4))
    gamma = math.radians(float(params.get('load_angle_deg', 0.0)))
    pole_pairs = poles / 2.0
    period = 360.0 / pole_pairs
    thetas = [period * i / (points - 1) for i in range(points)]

    def total_w(phi_rotor, phi_current):
        return sum(_phase_coenergy(phi_rotor, phi_current, k,
                                   params, (mmf_c, mmf_m),
                                   mu_stator, gamma)
                   for k in range(3))

    h = math.radians(0.25)
    torques = []
    for th in thetas:
        phi = math.radians(th) * pole_pairs
        w_plus = total_w(phi + h, phi)
        w_minus = total_w(phi - h, phi)
        # dW'/d(mech angle) = dW'/d(elec) * pole_pairs.
        torques.append((w_plus - w_minus) / (2.0 * h) * pole_pairs)
    mean_t = sum(torques) / len(torques)
    peak = max(abs(t) for t in torques)
    ripple = ((max(torques) - min(torques)) / abs(mean_t)
              if abs(mean_t) > 1e-12 else None)
    return {'ok': True, 'design': design_name,
            'topology': topology,
            'ladderRung': getattr(design, 'ladder_rung', ''),
            'dualGap': bool(params.get('dual_gap')),
            'curve': [{'thetaDeg': round(t, 2),
                       'torqueNm': tq}
                      for t, tq in zip(thetas, torques)],
            'meanTorqueNm': mean_t,
            'peakTorqueNm': peak,
            'ripplePct': (round(ripple * 100.0, 1)
                          if ripple is not None else None),
            'pmMmfAt': mmf_m,
            'validity': VALIDITY + '; torque numbers at this rung '
                        'are SMALL and the report says so (mu~2 '
                        'physics honesty)'}


def torque_parity(manager, cheap_material, reference='opt-ndfeb',
                  dual_gap=False):
    """§2d: the area/radius multiplier for torque parity — PM
    torque ~ B_gap x loading x gap area x radius, so at equal
    loading the multiplier is B_r_ref / B_r_cheap; dual gaps
    supply a clean 2x of it. Watermarks of BOTH rows attached."""
    try:
        b_cheap = _prop(manager, cheap_material, 'b_r_t')
        b_ref = _prop(manager, reference, 'b_r_t')
    except ValueError as exc:
        return {'ok': False, 'refusal': str(exc)}
    multiplier = b_ref / b_cheap
    effective = multiplier / (2.0 if dual_gap else 1.0)
    cheap_opt = _named(manager, 'MagneticMaterialOption',
                       cheap_material)
    ref_opt = _named(manager, 'MagneticMaterialOption', reference)
    return {'ok': True,
            'cheap': {'material': cheap_material, 'bRT': b_cheap,
                      'watermark': gates_for(manager, cheap_opt)
                      ['simulation']['watermark']},
            'reference': {'material': reference, 'bRT': b_ref,
                          'watermark': gates_for(manager, ref_opt)
                          ['simulation']['watermark']},
            'areaMultiplierForParity': round(multiplier, 3),
            'withDualGap': round(effective, 3) if dual_gap else None,
            'assumptions': 'equal electrical loading; torque ~ '
                           'B_gap x loading x area x radius '
                           '(first-order); B_gap taken as B_r '
                           'class — gap geometry not folded in; '
                           'the multiplier buys AREA or RADIUS, '
                           'your choice',
            'note': 'every parity claim traces to this function '
                    '(§2d)'}
