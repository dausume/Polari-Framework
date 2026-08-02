"""
@module motors.m1_sequencing

m1-1: the M1 sequencing solver — clock_sim's analog for the 6s/4p
switched-reluctance rung. Excite phase k, the rotor settles to the
aligned (max-inductance) position, sequence the phases and the
machine walks 30 deg/step: 360/(3 phases x 4 poles), the same
number the slot/pole difference formula 360*(1/4 - 1/6) gives (the
selftest pins both).

VALIDITY, stated on every output: quasi-static co-energy on a
first-harmonic overlap modulation, amplitudes from the lumped
reluctance network at gap extremes (mag-3/mag-5 idiom, the 0.03 m
core-path prior shared with torque_curve); load torque enters as a
constant opposing tilt on the settling potential. NAMED GAPS: no
dynamics (speed is an assumption), no phase mutual coupling, mu~2
saturation unmodeled. And one honest FACT the clock never had to
state: a reluctance machine has NO UNPOWERED DETENT — de-energized
it holds nothing, which the printer product (m1-5) must design
around.

@consumers motor_api (m1-sequence / m1-holding / m1-min-current),
m1_positioning (m1-5 drives commanded steps through here)
"""

import math

from magnetics.magnetic_netlist import MU0
from motors.motor_designer import _design, _loads, _prop
from motors.local_route import DRIVE_MARGIN

#: The 6s/4p machine this solver knows. Other slot/pole counts need
#: their own alignment map and get a refusal, not a guess.
SLOTS, POLES, PHASES = 6, 4, 3
STEP_DEG = 360.0 / (PHASES * POLES)

M1_VALIDITY = ('quasi-static co-energy; first-harmonic overlap '
               'modulation with amplitudes from the lumped '
               'reluctance network at gap extremes; linear '
               'magnetostatics; load torque = constant opposing '
               'tilt; inertia/friction unmodeled — max step rate '
               '/ speed NOT predicted')

M1_NAMED_GAPS = [
    'speed is an assumption — the solver is quasi-static and the '
    'drive rate is taken from drive_json, not derived',
    'phase mutual coupling unmodeled (phases treated one at a '
    'time, exactly as the drive energizes them)',
    'saturation unmodeled — at mu~2 the core is barely better '
    'than air and the linear model is honest about being feeble',
]

NO_DETENT_FACT = ('no unpowered detent: with no magnet, a '
                  'de-energized M1 holds NOTHING — position is '
                  'kept only while a phase carries current')


def _geometry(manager, design, amps=None, stator_material='',
              rotor_material=''):
    """The lumped numbers every function here shares. One reader,
    so the calibration cannot drift between sim, holding torque
    and the bisect (two-modules-agree, inside one module).
    Material overrides exist for KNOB QUANTIFICATION (m1-5 asks
    what bio-steel would buy) — they never mutate the design row."""
    params = _loads(design, 'params_json', {})
    slots = int(params.get('slots', 0))
    poles = int(params.get('poles', 0))
    if (slots, poles) != (SLOTS, POLES):
        raise ValueError(
            f'the m1 solver knows the {SLOTS}s/{POLES}p machine; '
            f'"{getattr(design, "name", "?")}" is {slots}s/{poles}p '
            f'— other counts need their own alignment map')
    mu_s = _prop(manager, stator_material
                 or params['stator_material'], 'mu_r_eff')
    mu_r = _prop(manager, rotor_material
                 or params['rotor_material'], 'mu_r_eff')
    area = float(params['tooth_area_m2'])
    gap = float(params['gap_base_m'])
    saliency = float(params.get('saliency_ratio', 1.0))
    turns = float(params['coil_turns'])
    rated = float(params['coil_amps'])
    drive_amps = rated if amps is None else float(amps)
    # Two coils per phase in series on opposite teeth; the loop
    # crosses the gap twice. Core path prior 0.03 m total, split
    # stator 0.02 / rotor 0.01 — the same 0.03 torque_curve uses.
    return {
        'mmf': 2.0 * turns * drive_amps,
        'mod_depth': 1.0 - 1.0 / max(saliency, 1.0),
        'area': area, 'gap': gap,
        'r_core': (0.02 / (MU0 * mu_s * area)
                   + 0.01 / (MU0 * mu_r * area)),
        'ratedAmps': rated, 'driveAmps': drive_amps,
        'saliency': saliency,
    }


def _phase_coenergy(geo, phase_idx, theta_deg):
    """W'_k(theta): one excited phase. Overlap is first-harmonic
    between 1 (aligned) and 1/saliency (unaligned), period
    360/POLES deg; phase k's aligned positions sit at
    k*STEP_DEG + n*(360/POLES)."""
    u = math.radians(theta_deg - phase_idx * STEP_DEG)
    overlap = ((1.0 - geo['mod_depth'])
               + geo['mod_depth'] * (1.0 + math.cos(POLES * u))
               / 2.0)
    r_gap = 2.0 * geo['gap'] / (MU0 * geo['area']
                                * max(overlap, 1e-6))
    return 0.5 * geo['mmf'] ** 2 / (r_gap + geo['r_core'])


SETTLE_GRID_DEG = 0.25


def _settle(geo, phase_idx, theta_deg, load_nm=0.0):
    """Gradient walk to the local minimum of the settling
    potential U = -W' + T_load*theta — quasi-static, the same walk
    clock_sim does, with the load as a constant tilt. load_nm > 0
    opposes +theta motion."""
    g = SETTLE_GRID_DEG

    def u_at(t):
        return (-_phase_coenergy(geo, phase_idx, t)
                + load_nm * math.radians(t))

    theta = theta_deg
    for _ in range(1200):
        here = u_at(theta)
        fwd = u_at(theta + g)
        back = u_at(theta - g)
        if fwd < here and fwd <= back:
            theta += g
        elif back < here:
            theta -= g
        else:
            return theta
    return theta


def _m1_design(manager, design_name):
    design = _design(manager, design_name)
    if getattr(design, 'topology', '') != 'radial-reluctance':
        raise ValueError(
            f'"{design_name}" is not radial-reluctance — the '
            f'sequencing sim is the M1 rung (M0 has clock-sim, '
            f'M2/M3 have torque curves)')
    return design


def sequence_sim(manager, design_name='reluctance-6s4p-m1',
                 steps=12, load_torque_nm=0.0, direction=1,
                 start_deg=0.0, amps=None):
    """THE M1 CONTROL CASE: latch phase 0, then command N phase
    advances and settle the rotor per excitation, counting
    stepped/missed under the load torque. The step history is the
    replay contract clock_sim established; thetaContinuousDeg
    carries cumulative rotation for the positioning proof, and
    every missed step is a NAMED shortfall, not a silent drift."""
    try:
        design = _m1_design(manager, design_name)
        geo = _geometry(manager, design, amps=amps)
    except (ValueError, KeyError) as exc:
        return {'ok': False, 'refusal': str(exc)}
    steps = int(steps)
    direction = 1 if int(direction) >= 0 else -1
    # Load always opposes the COMMANDED direction (the axis being
    # driven pushes back); a negative load_torque_nm assists.
    load = float(load_torque_nm) * direction

    theta = _settle(geo, 0, float(start_deg), load)
    latch = theta
    history = [{'step': 0, 'phase': 0, 'excited': 'latch',
                'thetaDeg': round(theta % 360.0, 2),
                'thetaContinuousDeg': round(theta, 2)}]
    taken = 0
    phase = 0
    for n in range(1, steps + 1):
        phase = (phase + direction) % PHASES
        before = theta
        theta = _settle(geo, phase, theta, load)
        advanced = (theta - before) * direction
        stepped = (0.5 * STEP_DEG) < advanced < (1.5 * STEP_DEG)
        if stepped:
            taken += 1
        history.append({
            'step': n, 'phase': phase, 'excited': f'phase-{phase}',
            'thetaDeg': round(theta % 360.0, 2),
            'thetaContinuousDeg': round(theta, 2),
            'advancedDeg': round(advanced, 2),
            'shortfallDeg': round(STEP_DEG - advanced, 2),
            'stepped': stepped})
    missed = steps - taken
    expected = steps * STEP_DEG
    actual = (theta - latch) * direction
    drive = _loads(design, 'drive_json', {})
    rate = float(drive.get('rate_hz', 1.0))
    return {
        'ok': True, 'design': design_name,
        'slots': SLOTS, 'poles': POLES, 'phases': PHASES,
        'stepDeg': STEP_DEG, 'direction': direction,
        'steps': steps, 'stepsTaken': taken, 'stepsMissed': missed,
        'loadTorqueNm': float(load_torque_nm),
        'positionComparison': {
            'expectedRotationDeg': round(expected, 2),
            'actualRotationDeg': round(actual, 2),
            'positionErrorDeg': round(expected - actual, 2),
            'note': 'position IS the product: the printer axis '
                    '(m1-5) turns this angle error into mm '
                    'through the leadscrew — exact when nothing '
                    'misses, and every miss is named in the '
                    'history as its shortfallDeg'},
        'speedAssumption': {
            'rateHz': rate, 'durationS': steps / rate,
            'note': 'ASSUMED drive rate, not a prediction — the '
                    'solver is quasi-static'},
        'calibration': {
            'mmfPhaseAt': geo['mmf'],
            'driveAmps': geo['driveAmps'],
            'ratedAmps': geo['ratedAmps'],
            'saliencyRatio': geo['saliency'],
            'coreReluctancePerH': geo['r_core']},
        'noUnpoweredDetent': NO_DETENT_FACT,
        'history': history,
        'namedGaps': M1_NAMED_GAPS, 'validity': M1_VALIDITY}


def holding_torque(manager, design_name='reluctance-6s4p-m1',
                   amps=None, points=361, stator_material='',
                   rotor_material=''):
    """Peak static torque of ONE energized phase over a rotor-pole
    period: numerical dW'/dtheta, scanned. This is the number the
    axis load is judged against (m1-5) and the bench measures
    (m1-7) — and at mu~2 it is honestly SMALL. Material overrides
    quantify knobs without touching the design row."""
    try:
        design = _m1_design(manager, design_name)
        geo = _geometry(manager, design, amps=amps,
                        stator_material=stator_material,
                        rotor_material=rotor_material)
    except (ValueError, KeyError) as exc:
        return {'ok': False, 'refusal': str(exc)}
    period = 360.0 / POLES
    h = math.radians(0.05)
    peak, at = 0.0, 0.0
    for i in range(points):
        th = period * i / (points - 1)
        w_plus = _phase_coenergy(geo, 0, th + math.degrees(h))
        w_minus = _phase_coenergy(geo, 0, th - math.degrees(h))
        t = (w_plus - w_minus) / (2.0 * h)
        if abs(t) > peak:
            peak, at = abs(t), th
    return {
        'ok': True, 'design': design_name,
        'peakTorqueNm': peak, 'atThetaDeg': round(at, 2),
        'driveAmps': geo['driveAmps'],
        'ratedAmps': geo['ratedAmps'],
        'honesty': 'at mu~2 the core dominates the reluctance '
                   'loop, so saliency moves the total only a '
                   'little and the torque is honestly feeble — '
                   'that is the rung, not a bug',
        'noUnpoweredDetent': NO_DETENT_FACT,
        'validity': M1_VALIDITY}


def m1_minimum_drive_current(manager,
                             design_name='reluctance-6s4p-m1',
                             load_torque_nm=None, steps=12,
                             margin=DRIVE_MARGIN):
    """DERIVE the phase current M1 needs against a stated load,
    instead of asserting coil_amps — local_route's bisect, judged
    by THIS solver. With no magnet and no friction model there is
    no detent to overcome, so a zero load bisects to zero amps:
    that is a refusal, not an answer — bring the axis load."""
    if load_torque_nm is None or float(load_torque_nm) <= 0.0:
        return {'ok': False,
                'refusal': 'nothing opposes the rotor: M1 has no '
                           'detent and this model has no friction, '
                           'so the threshold against zero load is '
                           'zero — pass the axis load torque '
                           '(m1-5) or a stated friction prior'}
    try:
        design = _m1_design(manager, design_name)
        geo = _geometry(manager, design)
    except (ValueError, KeyError) as exc:
        return {'ok': False, 'kind': 'data-gap',
                'refusal': f'the sequencing sim could not run: '
                           f'{exc}',
                'whatThisIsNot': 'this is a MISSING PROPERTY or a '
                                 'wrong-topology design, not a '
                                 'finding that the motor fails'}
    stated = geo['ratedAmps']
    load = float(load_torque_nm)

    def steps_at(a):
        out = sequence_sim(manager, design_name, steps=steps,
                           load_torque_nm=load, amps=a)
        return bool(out.get('ok')) and out.get('stepsMissed') == 0

    if not steps_at(stated):
        return {'ok': False, 'kind': 'does-not-step',
                'refusal': f'the motor misses steps even at the '
                           f'stated {stated} A under '
                           f'{load} Nm — there is no current to '
                           f'minimise, the DESIGN (or the load) '
                           f'is wrong',
                'statedAmps': stated,
                'loadTorqueNm': load}
    lo, hi = 0.0, stated
    for _ in range(40):
        mid = (lo + hi) / 2.0
        if steps_at(mid):
            hi = mid
        else:
            lo = mid
    threshold = hi
    designed = threshold * margin
    return {
        'ok': True, 'design': design_name,
        'loadTorqueNm': load,
        'statedAmps': stated,
        'thresholdAmps': float(f'{threshold:.4g}'),
        'marginFactor': margin,
        'designedAmps': float(f'{designed:.4g}'),
        'reductionVsStated': (float(f'{stated / designed:.3g}')
                              if designed else None),
        'method': f'bisection over the m1 sequencing sim across '
                  f'{steps} steps at {load} Nm load — the '
                  f'simulator that already decides whether a step '
                  f'lands is the judge, no new physics',
        'physicsNote': 'PULL-IN governs, not pull-out: the '
                       'threshold sits above the naive peak-'
                       'torque bound because the load-lagged '
                       'start position lies deep in the next '
                       'phase\'s weak-torque zone (the landscape '
                       'is nearly flat between poles), so the '
                       'weakest torque along the TRAVEL decides '
                       '— the same pull-in/pull-out distinction '
                       'real stepper datasheets carry',
        'honesty': 'only as good as the co-energy landscape it is '
                   'bisected against: first-harmonic overlap, no '
                   'friction, no dynamics, constant load. A real '
                   'axis needs MORE than this. A defensible design '
                   'current in place of an asserted one, not a '
                   'measurement.'}
