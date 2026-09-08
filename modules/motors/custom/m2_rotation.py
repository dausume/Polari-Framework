"""
@module motors.custom.m2_rotation

m2-1: the M2 rotation solver — m1_sequencing's inverse twin for
the PM rung. M1 walks: energise a phase, the salient rotor jumps
to it, and a load that is too big means a step never lands. M2
SPINS: the commutation angle advances continuously and the magnet
FOLLOWS it, lagging by whatever angle produces the torque the load
demands — until the lag passes 90 degrees electrical and the
rotor falls out of step. Same machinery, opposite failure.

The physics is NOT re-derived here. motor_designer._phase_coenergy
already carries both terms (reluctance AND the permanent-magnet
one) and M2's design row sets saliency_ratio 1.0, which zeroes the
reluctance modulation and leaves the PM term alone — that is what
makes M2 the PM rung rather than a second reluctance machine.

VALIDITY, stated on every output: quasi-static co-energy at held
phase currents; the magnet as a constant MMF through the same
lumped loop reluctance the torque curve uses; linear
magnetostatics; load = constant opposing torque. NAMED GAPS:
start-up and pull-in-to-synchronism are unmodeled (the solver
begins already in step), no inertia, no dynamics.

AND ONE NAMED ABSENCE, deliberately: this model predicts EXACTLY
ZERO cogging torque. A slotless-ideal machine has none, and a
first-harmonic gap model cannot manufacture it. The real machine
WILL cog, from slotting. We do not fake it — the m2-7 bench
measures the real detent map, and the product's power-off holding
comes from the self-locking WORM (a geometry fact), never from a
cogging claim.

@consumers motors.motor_api (m2-rotation / m2-pull-out /
m2-back-emf), motors.m2_lift_basis (the hoist duty drives this), tests
in motors.m2_selftest
"""

import math

from magnetics.magnetic_netlist_seed import MU0
from motors.custom.motor_designer import (
    _design, _loads, _phase_coenergy, _prop, coil_and_magnet_mmf,
    reluctance_total,
)

M2_DESIGN = 'ferrite-pm-m2'
PHASES = 3
#: Electrical degrees of lag past which a synchronous machine
#: cannot make more torque: the pull-out angle. Beyond it the
#: torque FALLS as the rotor falls further behind, which is why
#: losing synchronism is a runaway rather than a droop.
PULL_OUT_LAG_DEG = 90.0

M2_VALIDITY = ('quasi-static co-energy at held phase currents; '
               'the magnet as a constant MMF through the same '
               'lumped loop reluctance the torque curve uses; '
               'linear magnetostatics; load = constant opposing '
               'torque; inertia and dynamics unmodeled — the '
               'solver starts already in step')

M2_NAMED_GAPS = [
    'start-up is unmodeled: pulling INTO synchronism from rest '
    'is the hard part of a PM synchronous drive and this solver '
    'begins in step (the M1 speed assumption\'s sibling)',
    'no inertia, no friction, no damping — the rotor settles '
    'instantly to its equilibrium lag, so nothing here predicts '
    'how fast the commutation may be advanced',
    'phase mutual coupling unmodeled (three phases summed, each '
    'through its own loop)',
]

NO_COGGING_FACT = (
    'THIS MODEL PREDICTS ZERO COGGING, BY CONSTRUCTION: a '
    'first-harmonic gap model of a round PM ring has no slotting '
    'in it, so its detent torque is exactly zero. The real '
    'machine cogs. That is a NAMED ABSENCE, not a claim of '
    'smoothness — the m2-7 bench measures the real map, and the '
    'hoist holds when dead because the WORM is self-locking, '
    'never because the motor cogs.')


def _m2_design(manager, design_name):
    design = _design(manager, design_name)
    params = _loads(design, 'params_json', {})
    if not params.get('magnet_length_m'):
        raise ValueError(
            f'"{design_name}" states no magnet_length_m — M2 is '
            f'the PM rung, and a machine with no magnet is M1: '
            f'use the m1-sequence solver')
    return design, params


def _geometry(manager, design_name=M2_DESIGN, amps=None,
              rotor_material='', stator_material=''):
    """The numbers every function here shares — one reader, so
    the sim, the pull-out bisect and k_e cannot drift apart.
    Material overrides quantify knobs (what a stronger magnet
    would buy) without ever mutating the design row."""
    design, params = _m2_design(manager, design_name)
    params = dict(params)
    if rotor_material:
        params['rotor_material'] = rotor_material
    if stator_material:
        params['stator_material'] = stator_material
    if amps is not None:
        params['coil_amps'] = float(amps)
    mu_stator = _prop(manager, params['stator_material'],
                      'mu_r_eff')
    mmf_c, mmf_m = coil_and_magnet_mmf(manager, params)
    if not mmf_m:
        raise ValueError(
            f'the rotor material "{params.get("rotor_material")}" '
            f'is not hard enough to be a magnet (H_c < 100 kA/m) '
            f'— M2 is the PM rung; a soft rotor is M1\'s machine')
    poles = int(params.get('poles', 4))
    saliency = float(params.get('saliency_ratio', 1.0))
    return {
        'design': design, 'params': params,
        'poles': poles, 'polePairs': poles / 2.0,
        'muStator': mu_stator,
        'mmfCoil': mmf_c, 'mmfMagnet': mmf_m,
        'gamma': math.radians(
            float(params.get('load_angle_deg', 0.0))),
        'saliency': saliency,
        'ratedAmps': float(params['coil_amps']),
    }


def _total_w(geo, phi_rotor, phi_current):
    """Co-energy of all three phases: GEOMETRY at the rotor angle,
    CURRENTS held at the commutation angle — the partial that
    makes the torque right (motor_designer's rule, reused)."""
    return sum(_phase_coenergy(phi_rotor, phi_current, k,
                               geo['params'],
                               (geo['mmfCoil'], geo['mmfMagnet']),
                               geo['muStator'], geo['gamma'])
               for k in range(PHASES))


def torque_at(geo, phi_rotor, phi_current, h_deg=0.25):
    """Mechanical torque at a rotor angle for a held commutation
    angle: numerical partial dW'/dtheta_mech, chained through the
    pole pairs exactly as torque_curve does."""
    h = math.radians(h_deg)
    w_plus = _total_w(geo, phi_rotor + h, phi_current)
    w_minus = _total_w(geo, phi_rotor - h, phi_current)
    return (w_plus - w_minus) / (2.0 * h) * geo['polePairs']


def load_angle(geo, phi_rotor, phi_current, direction=1):
    """THE LOAD ANGLE delta: how far the magnet sits behind where
    the current wants it, measured from the no-load equilibrium.

    Summing the PM term over three phases collapses to
    W_pm = (3/2) * MMF_coil * Phi_pm * cos(phi_c + gamma - phi_r),
    so delta = phi_c + gamma - phi_r is the whole story: torque
    goes as sin(delta), zero load rests at delta = 0, and
    delta = 90 deg is the pull-out cliff. gamma (the drive's
    stated load_angle_deg) is part of the reference, not part of
    the lag — without folding it in, a design that commutes with
    a 90 deg advance looks permanently on the edge of pull-out."""
    return (phi_current + geo['gamma'] - phi_rotor) * direction


def analytic_peak_torque(geo):
    """The same peak, in closed form: (3/2) * MMF_coil * Phi_pm *
    pole_pairs at delta = 90 deg. Derived from the three-phase sum
    above, so it is a genuinely INDEPENDENT path to the number the
    numerical sweep finds — if they disagree, one of them is
    wrong, and the disagreement is the finding."""
    r_loop = reluctance_total(geo['params'], geo['muStator'], 1.0)
    phi_pm = geo['mmfMagnet'] / r_loop
    return 1.5 * geo['mmfCoil'] * phi_pm * geo['polePairs']


SETTLE_GRID_DEG = 0.1
#: Coarse-to-fine walk: the same descent M1 does, but stepped down
#: through three grids. A single fine grid costs thousands of
#: co-energy evaluations per settle, and the pull-out bisect runs
#: forty sims of thirteen settles each — the refinement keeps the
#: semantics (descend to the local minimum) and makes the report
#: answer in a page load instead of a coffee break.
SETTLE_GRIDS_DEG = (2.0, 0.5, SETTLE_GRID_DEG)


def _settle(geo, phi_current, phi_rotor, load_nm=0.0):
    """Gradient walk to the equilibrium rotor angle under a held
    commutation angle: minimise U = -W'(phi_r) + load*theta_mech,
    the same walk M1 does (quasi-static, no inertia). phi angles
    are ELECTRICAL radians; the load acts on the MECHANICAL
    angle, hence the division by pole pairs.

    Out of synchronism there IS no local minimum ahead — the load
    beats the torque everywhere — so the walk runs to its cap and
    the caller sees a rotor that fell behind. That is the honest
    shape of losing sync in a quasi-static model, not a bug."""
    def u_at(p):
        return (-_total_w(geo, p, phi_current)
                + load_nm * p / geo['polePairs'])

    phi = phi_rotor
    for grid_deg in SETTLE_GRIDS_DEG:
        g = math.radians(grid_deg)
        for _ in range(400):
            here = u_at(phi)
            fwd = u_at(phi + g)
            back = u_at(phi - g)
            if fwd < here and fwd <= back:
                phi += g
            elif back < here:
                phi -= g
            else:
                break
    return phi


def rotation_sim(manager, design_name=M2_DESIGN, steps=12,
                 load_torque_nm=0.0, direction=1, amps=None,
                 rotor_material='', stator_material=''):
    """THE M2 CONTROL CASE: advance the commutation angle in N
    equal electrical steps and let the magnet follow. Every entry
    names its lag and whether the rotor is still IN SYNC; the
    position ledger telescopes exactly as M1's does, which is the
    point — the two rungs are the same accounting over opposite
    physics."""
    try:
        geo = _geometry(manager, design_name, amps=amps,
                        rotor_material=rotor_material,
                        stator_material=stator_material)
    except (ValueError, KeyError) as exc:
        return {'ok': False, 'refusal': str(exc)}
    steps = int(steps)
    direction = 1 if int(direction) >= 0 else -1
    load = float(load_torque_nm) * direction
    advance = direction * 2.0 * math.pi / steps
    pole_pairs = geo['polePairs']

    phi_c = 0.0
    phi_r = _settle(geo, phi_c, geo['gamma'], load)
    latch = phi_r
    history = [{'step': 0, 'phiElecDeg': 0.0,
                'phase': '0', 'stepped': False,
                'thetaDeg': round(
                    math.degrees(phi_r / pole_pairs) % 360.0, 3),
                'thetaContinuousDeg': round(
                    math.degrees(phi_r / pole_pairs), 3),
                'lagDeg': round(math.degrees(
                    load_angle(geo, phi_r, phi_c, direction)), 3),
                'inSync': True, 'excited': 'latch'}]
    in_sync = True
    mech_step_deg = 360.0 / (steps * pole_pairs)
    for n in range(1, steps + 1):
        phi_c += advance
        before = phi_r
        phi_r = _settle(geo, phi_c, phi_r, load)
        lag = load_angle(geo, phi_r, phi_c, direction)
        step_sync = lag <= math.radians(PULL_OUT_LAG_DEG) + 1e-9
        in_sync = in_sync and step_sync
        advanced = math.degrees(
            (phi_r - before) / pole_pairs) * direction
        history.append({
            'step': n,
            # 'phase' and 'stepped' exist to match the REPLAY
            # CONTRACT M0/M1 established, so the scene component
            # animates M2 with no new code: phase '0' is the
            # single group that lights all six coils (a
            # synchronous drive energises them together), and
            # 'stepped' is the synchronism verdict — the thing
            # that, on this rung, decides whether the commanded
            # motion actually happened.
            'phase': '0',
            'stepped': step_sync,
            'phiElecDeg': round(math.degrees(phi_c) * direction,
                                3),
            'thetaDeg': round(
                math.degrees(phi_r / pole_pairs) % 360.0, 3),
            'thetaContinuousDeg': round(
                math.degrees(phi_r / pole_pairs), 3),
            'advancedDeg': round(advanced, 3),
            'shortfallDeg': round(mech_step_deg - advanced, 3),
            'lagDeg': round(math.degrees(lag), 3),
            'inSync': step_sync,
            'excited': 'commutation'})
    expected = steps * mech_step_deg
    actual = math.degrees((phi_r - latch) / pole_pairs) * direction
    drive = _loads(geo['design'], 'drive_json', {})
    rate = float(drive.get('rate_hz', 1.0))
    return {
        'ok': True, 'design': design_name,
        'poles': geo['poles'], 'polePairs': pole_pairs,
        'phases': PHASES, 'direction': direction,
        'steps': steps,
        'electricalRevolutions': 1.0,
        'mechDegPerElecRev': round(360.0 / pole_pairs, 6),
        'mechDegPerStep': round(mech_step_deg, 6),
        'loadTorqueNm': float(load_torque_nm),
        'inSync': in_sync,
        'pullOutStep': next((h['step'] for h in history[1:]
                             if not h['inSync']), None),
        'positionComparison': {
            'expectedRotationDeg': round(expected, 3),
            'actualRotationDeg': round(actual, 3),
            'positionErrorDeg': round(expected - actual, 3),
            'note': 'in synchronism the magnet keeps up EXACTLY '
                    '— it lags by a constant angle that makes '
                    'the torque, and a constant lag moves no '
                    'position. Out of synchronism it does not '
                    'lag, it falls behind, and the error grows.'},
        'speedAssumption': {
            'rateHz': rate,
            'mechRpm': round(rate * 60.0 / (steps * pole_pairs),
                             3),
            'note': 'ASSUMED commutation rate, not a prediction '
                    '— the solver is quasi-static and models no '
                    'inertia'},
        'calibration': {
            'mmfCoilAt': geo['mmfCoil'],
            'mmfMagnet': geo['mmfMagnet'],
            'saliencyRatio': geo['saliency'],
            'saliencyNote': 'saliency 1.0 means the reluctance '
                            'torque term is IDENTICALLY zero — '
                            'everything below is the magnet',
            'loadAngleDeg': math.degrees(geo['gamma'])},
        'noCoggingInModel': NO_COGGING_FACT,
        'history': history,
        'namedGaps': M2_NAMED_GAPS, 'validity': M2_VALIDITY}


def back_emf_constant(manager, design_name=M2_DESIGN,
                      rotor_material=''):
    """k_e, DERIVED from the same magnet and reluctance terms the
    torque runs on — never a second copy of the magnet math.

    Flux per phase from the magnet: Phi_pm = MMF_magnet / R_loop.
    Linked by N turns, swept by pole_pairs electrical radians per
    mechanical radian: k_e = pole_pairs * N * Phi_pm, volts per
    mechanical rad/s (peak, per phase).

    THIS IS THE MEASUREMENT THAT ADJUDICATES THE MODEL: spin the
    rotor by hand, scope one phase, and k_e isolates the magnet-
    and-turns product from resistance, inductance and load. If
    the bench disagrees with this number, the magnet prior or the
    reluctance loop is wrong — nothing else can absorb it."""
    try:
        geo = _geometry(manager, design_name,
                        rotor_material=rotor_material)
    except (ValueError, KeyError) as exc:
        return {'ok': False, 'refusal': str(exc)}
    params = geo['params']
    r_loop = reluctance_total(params, geo['muStator'], 1.0)
    phi_pm = geo['mmfMagnet'] / r_loop
    turns = float(params['coil_turns'])
    k_e = geo['polePairs'] * turns * phi_pm
    rate = float(_loads(geo['design'], 'drive_json', {})
                 .get('rate_hz', 1.0))
    omega = 2.0 * math.pi * rate / geo['polePairs'] / 12.0
    try:
        b_r = _prop(manager, params['rotor_material'], 'b_r_t')
    except ValueError:
        b_r = None
    try:
        mu_rec = _prop(manager, params['rotor_material'],
                       'mu_r_eff')
        h_c = _prop(manager, params['rotor_material'], 'h_c_ka_m')
        b_from_h = MU0 * mu_rec * h_c * 1000.0
    except ValueError:
        b_from_h = None
    return {
        'ok': True, 'design': design_name,
        'rotorMaterial': params['rotor_material'],
        'magnetBrT': b_r,
        'magnetMmfAt': geo['mmfMagnet'],
        'loopReluctancePerH': r_loop,
        'fluxPerPoleWb': phi_pm,
        'turnsPerPhase': turns,
        'kEVoltSPerRad': k_e,
        'kEVoltPerKrpm': k_e * 2.0 * math.pi * 1000.0 / 60.0,
        'atAssumedRate': {
            'rateHz': rate,
            'mechRadPerS': omega,
            'phaseVoltPeak': k_e * omega,
            'note': 'the assumed commutation rate again — the '
                    'voltage scales with whatever speed the '
                    'bench actually spins'},
        'materialConsistency': {
            'statedBrT': b_r,
            'brFromHcT': (round(b_from_h, 4)
                          if b_from_h is not None else None),
            'deviationPct': (
                round(abs(b_from_h - b_r) / b_r * 100.0, 1)
                if (b_from_h is not None and b_r) else None),
            'note': 'k_e rides H_c (the magnet MMF is H_c times '
                    'the magnet length), while the datasheet '
                    'headline is B_r. The two are related by '
                    'B_r = mu0 * mu_rec * H_c, but the seeded '
                    'rows carry them as INDEPENDENT literature '
                    'values, so they do not close exactly — the '
                    'deviation above is a standing prior on '
                    'every k_e number, not a bug to round away. '
                    'The B_r bench entry measures one of them '
                    'and the disagreement becomes a finding.'},
        'derivation': 'k_e = pole_pairs * N * (MMF_magnet / '
                      'R_loop) — the SAME magnet MMF and the '
                      'SAME lumped loop reluctance the torque '
                      'uses, imported rather than restated',
        'adjudicates': 'the magnet-and-turns product, isolated '
                       'from R, L and load — the one M2 '
                       'measurement no other error can absorb',
        'honesty': 'the magnet MMF is a LITERATURE PRIOR (H_c of '
                   'the chosen grade x the magnet length) until '
                   'press-sinter-magnetize actually happens; the '
                   'B_r bench entry retires it, and it is the '
                   'SAME experiment M0 named',
        'validity': M2_VALIDITY}


def pull_out_load_limit(manager, design_name=M2_DESIGN,
                        steps=12, amps=None, rotor_material='',
                        stator_material=''):
    """The largest load torque the rotor stays IN STEP under —
    bisected with the rotation sim as judge, exactly as M1
    bisects pull-IN with the sequencing sim. The two limits are
    the same accounting over opposite failures: M1 asks whether a
    step lands, M2 asks whether the magnet keeps up."""
    try:
        geo = _geometry(manager, design_name, amps=amps,
                        rotor_material=rotor_material,
                        stator_material=stator_material)
    except (ValueError, KeyError) as exc:
        return {'ok': False, 'refusal': str(exc)}
    # An upper bracket from the peak torque the machine can make
    # at all: sweep the LOAD ANGLE over half an electrical period
    # at a held commutation angle, then check the closed form
    # agrees (two paths, one number).
    peak = 0.0
    at_lag = 0.0
    for i in range(181):
        delta = math.radians(i)
        t = torque_at(geo, geo['gamma'] - delta, 0.0)
        if t > peak:
            peak, at_lag = t, math.degrees(delta)
    closed = analytic_peak_torque(geo)
    lo, hi = 0.0, peak * 1.05
    for _ in range(40):
        mid = (lo + hi) / 2.0
        out = rotation_sim(manager, design_name, steps=steps,
                           load_torque_nm=mid, amps=amps,
                           rotor_material=rotor_material,
                           stator_material=stator_material)
        if out.get('ok') and out.get('inSync'):
            lo = mid
        else:
            hi = mid
    return {
        'ok': True, 'design': design_name,
        'pullOutLimitNm': lo,
        'peakTorqueNm': peak,
        'atLagDeg': round(at_lag, 1),
        'ratioToPeak': round(lo / peak, 3) if peak else None,
        'crossCheck': {
            'pathA_sweptCoenergyNm': peak,
            'pathB_closedFormNm': closed,
            'consistent': abs(peak - closed) < 1e-9 * max(
                1.0, abs(closed)) or abs(peak - closed)
            / max(abs(closed), 1e-30) < 1e-4,
            'note': 'the numerical partial dW\'/dtheta swept over '
                    'the load angle vs (3/2)*MMF_coil*Phi_pm*'
                    'pole_pairs — two paths to the peak torque, '
                    'and the peak must sit at 90 deg of load '
                    'angle in both'},
        'basis': f'bisection of the load against the rotation '
                 f'sim over {steps} commutation steps — the same '
                 f'judge that decides synchronism decides the '
                 f'duty limit, no second criterion',
        'note': 'size the hoist by THIS number: past it the '
                'rotor does not slow down, it falls out of step '
                'and the torque COLLAPSES (the lag walks past '
                f'{PULL_OUT_LAG_DEG:.0f} deg electrical and the '
                'available torque falls with it)',
        'noCoggingInModel': NO_COGGING_FACT,
        'validity': M2_VALIDITY}
