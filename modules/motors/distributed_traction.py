"""
@module motors.distributed_traction

dt-1 (Dustin 2026-08-01): "for the train engine we can actually
just do one engine per wheel or per axle to lower the threshold we
need to meet, and simply scale up the amount of axles and wheels
as needed. We should still push to make it as capable a train as
possible but understanding of that is critical."

THE UNDERSTANDING, as computation:

1. THRESHOLD: tractive effort divides by driven-axle count, so the
   per-motor requirement falls toward the miniature-traction class
   — the sweep shows exactly where a stated train drops into a
   motor rung we can approach.
2. ADHESION: rail traction is capped by mu_adh x weight ON DRIVEN
   WHEELS. Distributing drive to every axle raises the CEILING,
   not just lowers the floor — the real reason locomotives are
   built this way.
3. WHAT STAYS HARD is named, never averaged away: coordinating N
   drives (the drive-electronics rung, N times), distributing
   power, and MANUFACTURING N identical units — which is exactly
   what the bizops batch-and-iterate loop exists to mature.

Motor-rung power classes are FLAGGED PRIORS until bench-measured
units replace them (the M0 discipline, again).

@consumers motors.motor_api (/api/motors/distributed-traction),
techtree device/motor node descriptions, motors.selftest_motors
"""

G = 9.81
#: rolling resistance, steel wheel on rail (dimensionless) — the
#: reason rail beats road by an order of magnitude.
ROLLING_RESISTANCE = 0.002
#: adhesion coefficient, dry steel on steel (prior band 0.25-0.35;
#: the conservative end travels).
MU_ADHESION = 0.25

#: Per-unit continuous power classes by motor rung — PRIORS until
#: a measured unit replaces them; the payload flags them.
RUNG_POWER_W = {
    'm2-pm-rotor (small)': 30.0,
    'miniature-traction-unit (~100 W class)': 100.0,
    'm3-axial-flux (per-axle traction)': 1000.0,
}


def distributed_traction(mass_t=2.0, speed_kmh=10.0,
                         grade_pct=2.0, wheel_radius_m=0.15,
                         max_axles=12):
    """Per-axle requirements for a stated train, swept over
    driven-axle count. Pure math, hand-checkable."""
    mass_kg = float(mass_t) * 1000.0
    v = float(speed_kmh) / 3.6
    grade = float(grade_pct) / 100.0
    # tractive effort at steady speed on the grade (acceleration
    # margin is the caller's next question, said in the note).
    force_n = mass_kg * G * (grade + ROLLING_RESISTANCE)
    power_w = force_n * v
    adhesion_all_driven = MU_ADHESION * mass_kg * G
    sweep = []
    for axles in range(1, int(max_axles) + 1):
        per_axle_force = force_n / axles
        per_axle_power = power_w / axles
        per_axle_torque = per_axle_force * float(wheel_radius_m)
        # adhesion if ONLY these axles are driven and weight is
        # even: each carries mass/axles_total... the honest simple
        # case: all axles driven, evenly loaded.
        rung = next((name for name, p in sorted(
            RUNG_POWER_W.items(), key=lambda kv: kv[1])
            if per_axle_power <= p), None)
        sweep.append({
            'drivenAxles': axles,
            'perAxleForceN': round(per_axle_force, 2),
            'perAxleTorqueNm': round(per_axle_torque, 3),
            'perAxlePowerW': round(per_axle_power, 1),
            'smallestSufficientRung': rung
            or 'beyond the stated rungs — split further or push '
               'the ladder',
        })
    adhesion_ok = force_n <= adhesion_all_driven
    single_axle_adhesion = MU_ADHESION * mass_kg * G / max(
        1, max_axles)
    return {
        'ok': True,
        'train': {'massT': mass_t, 'speedKmh': speed_kmh,
                  'gradePct': grade_pct,
                  'wheelRadiusM': wheel_radius_m},
        'tractiveEffortN': round(force_n, 1),
        'totalPowerW': round(power_w, 1),
        'adhesion': {
            'muPrior': MU_ADHESION,
            'ceilingAllDrivenN': round(adhesion_all_driven, 1),
            'satisfiedAllDriven': adhesion_ok,
            'ceilingOneDrivenAxleN': round(
                single_axle_adhesion, 1),
            'note': 'distributing drive to EVERY axle raises the '
                    'adhesion ceiling (weight on driven wheels), '
                    'not just lowers the per-motor floor — the '
                    'real reason locomotives are built this way',
        },
        'sweep': sweep,
        'whatStaysHard': [
            'coordinating N drives (the drive-electronics rung, '
            'N times over — load sharing, not just switching)',
            'distributing power to every axle',
            'MANUFACTURING N identical units — the batch-and-'
            'iterate loop is the tool for exactly this',
        ],
        'rungPowerPriorsW': RUNG_POWER_W,
        'note': 'steady-speed requirement on the stated grade; '
                'acceleration and headwind add margin on top. '
                'Rung power classes are PRIORS until a measured '
                'unit replaces them.',
    }
