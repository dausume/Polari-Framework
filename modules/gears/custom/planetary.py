"""
@module gears.custom.planetary

gr-6: PLANETARY RATIO ALGEBRA (the table the gr-1 solver refused to
guess) + the CONCENTRIC HAND DRIVE, and the sizing question that
falls out of it.

Dustin 2026-07-30: "if we want to put on connecting to a planetary
gear system that allows it to drive all hands on a clock face, what
would that look like? Assuming the clock is a size sensible in
respect to the motor size, I am unsure what size clock this would be
meant for."

THE HONEST ANSWER HAS THREE PARTS.

1. A PLANETARY CAN do it, and its ratio depends entirely on WHICH
   MEMBER IS HELD — which is why gr-1 refused to chain it rather
   than guessing. That table is here, as data, with the tooth and
   assembly constraints that make a set physically buildable.

2. BUT FOR A CLOCK IT IS PROBABLY THE WRONG CHOICE, and the numbers
   say so rather than taste. The hour hand needs 12:1 from the
   minute hand. A single planetary reaching 12:1 with the ring held
   needs R/S = 11 — a ring eleven times the sun diameter, which is
   enormous next to the movement it serves. The classical MOTION
   WORKS gets the same 12:1 from two small idler meshes
   (cannon pinion -> minute wheel -> minute pinion -> hour wheel)
   AND delivers the concentric output a clock face actually needs,
   because the hour wheel is a TUBE around the cannon pinion. The
   planetary's selling point is coaxial output; the motion works
   already has it, more compactly.

3. THE CLOCK SIZE IS SET BY OUR MOTOR'S TORQUE, and it is
   computable rather than a matter of preference. An unbalanced
   hand is a gravity load: T = m g r_cg. Our M0 through the 1800:1
   train delivers ~1.7e-3 Nm, and that number divided by the
   imbalance of a hand of length L is the safety factor. It runs
   out somewhere around a 300 mm face — so this movement is an
   8-inch wall clock, not a tower clock, and the calculation says
   which.

COUNTERBALANCING CHANGES THE ANSWER, and the report says so: a
balanced hand has near-zero gravity imbalance, leaving only
bearing friction, which is why real clock hands are counterweighted
on large dials. The sizing function takes it as a knob rather than
assuming either way.

@consumers gears.gear_api, gears.gears_selftest
"""

import math

from gears.custom.gear_kinematics import _named, _rows

G = 9.80665

#: Which member is HELD decides the ratio. This is the table gr-1
#: refused to guess — stated as data, with the sign convention
#: explicit because a reversed output is a real design outcome.
PLANETARY_CONFIGURATIONS = {
    'ring-fixed': {
        'input': 'sun', 'output': 'carrier', 'held': 'ring',
        'ratio_formula': '1 + N_ring / N_sun',
        'direction': 'same as input',
        'why': 'the workhorse: highest reduction of the three, '
               'output turns the same way as the input, and the '
               'load is shared over every planet',
    },
    'sun-fixed': {
        'input': 'ring', 'output': 'carrier', 'held': 'sun',
        'ratio_formula': '1 + N_sun / N_ring',
        'direction': 'same as input',
        'why': 'a mild reduction — the ring is the big member, so '
               'holding the small one buys little',
    },
    'carrier-fixed': {
        'input': 'sun', 'output': 'ring', 'held': 'carrier',
        'ratio_formula': '-N_ring / N_sun',
        'direction': 'REVERSED',
        'why': 'the planets become simple idlers; the minus sign '
               'is the point, not a bookkeeping detail',
    },
}


def planetary_ratio(n_sun, n_ring, configuration='ring-fixed',
                    n_planets=3):
    """Ratio for a planetary set, WITH the constraints that decide
    whether it can be built at all."""
    cfg = PLANETARY_CONFIGURATIONS.get(configuration)
    if cfg is None:
        return {'ok': False,
                'refusal': f'unknown configuration '
                           f'"{configuration}"',
                'suggestion': {'action': f'one of '
                               f'{sorted(PLANETARY_CONFIGURATIONS)}'}}
    n_sun = int(n_sun)
    n_ring = int(n_ring)
    if n_sun <= 0 or n_ring <= 0:
        return {'ok': False, 'refusal': 'tooth counts must be > 0'}
    # Geometry constraint: the planet must exactly fill the gap.
    planet_teeth = (n_ring - n_sun) / 2.0
    geometry_ok = float(planet_teeth).is_integer()
    # Assembly constraint: equally spaced planets only mesh if
    # (N_ring + N_sun) divides evenly by the planet count.
    assembly_ok = ((n_ring + n_sun) % int(n_planets)) == 0

    if configuration == 'ring-fixed':
        ratio = 1.0 + n_ring / n_sun
    elif configuration == 'sun-fixed':
        ratio = 1.0 + n_sun / n_ring
    else:
        ratio = -(n_ring / n_sun)

    return {
        'ok': True, 'configuration': configuration, **cfg,
        'nSun': n_sun, 'nRing': n_ring,
        'nPlanets': int(n_planets),
        'planetTeeth': (int(planet_teeth) if geometry_ok
                        else planet_teeth),
        'ratio': round(ratio, 6),
        'geometryOk': geometry_ok,
        'assemblyOk': assembly_ok,
        'buildable': geometry_ok and assembly_ok,
        'constraints': {
            'geometry': 'N_planet = (N_ring - N_sun)/2 must be a '
                        'WHOLE number, or the planet does not fit '
                        'the annulus',
            'assembly': f'(N_ring + N_sun) must divide by '
                        f'{int(n_planets)} for equally spaced '
                        f'planets to mesh at all',
        },
        'sizeNote': (
            f'a ring/sun ratio of {round(n_ring / n_sun, 2)} means '
            f'the ring is {round(n_ring / n_sun, 1)}x the sun '
            f'DIAMETER — for a 12:1 clock reduction that is 11x, '
            f'which is why the classical motion works beats a '
            f'planetary here on size'),
    }


#: The classical motion works — what a real clock uses to get 12:1
#: AND concentric hands. Tooth counts are the common set.
MOTION_WORKS = {
    'cannon_pinion': 12, 'minute_wheel': 36,
    'minute_pinion': 10, 'hour_wheel': 40,
}


def motion_works_ratio(counts=None):
    """Cannon pinion -> minute wheel -> minute pinion -> hour wheel.
    Two small meshes, 12:1, and the hour wheel is a TUBE around the
    cannon pinion, which is what makes the hands concentric."""
    c = dict(MOTION_WORKS)
    c.update(counts or {})
    stage1 = c['minute_wheel'] / c['cannon_pinion']
    stage2 = c['hour_wheel'] / c['minute_pinion']
    ratio = stage1 * stage2
    return {
        'ok': True, 'counts': c,
        'stage1': round(stage1, 6), 'stage2': round(stage2, 6),
        'ratio': round(ratio, 6),
        'exact12': abs(ratio - 12.0) < 1e-9,
        'concentric': True,
        'why': 'the hour wheel rides as a TUBE over the cannon '
               'pinion, so both hands turn about ONE axis without '
               'any coaxial gear set being needed. That is the '
               'thing a planetary would have been chosen for.',
        'sizeAdvantage': 'both meshes are small and offset; nothing '
                         'here is 11x anything, unlike the '
                         'single-stage planetary that reaches the '
                         'same 12:1',
    }


def clock_face_sizing(manager, train_name='clock-train-m0',
                      output_torque_nm=None,
                      hand_density_kg_m3=2700.0,
                      hand_thickness_mm=0.8,
                      hand_width_mm=4.0,
                      counterbalanced=False,
                      required_sf=3.0):
    """WHAT SIZE CLOCK does this motor drive?

    An unbalanced hand is a gravity load, T = m g r_cg. Sweep hand
    length, find where the available torque runs out, and report the
    face diameter that implies."""
    torque = output_torque_nm
    if torque is None:
        train = _named(manager, 'GearTrainDefinition', train_name)
        if train is None:
            return {'ok': False,
                    'refusal': f'no GearTrainDefinition named '
                               f'"{train_name}" and no torque given'}
        from gears.custom.gear_kinematics import solve_train
        sol = solve_train(manager, train_name)
        if not sol.get('ok'):
            return sol
        torque = sol['outputTorqueNm']
    if not torque or torque <= 0:
        return {'ok': False,
                'refusal': 'output torque is zero — nothing to size '
                           'against'}

    rows = []
    max_len = None
    for length_mm in (40, 60, 80, 100, 120, 150, 200, 250, 300):
        L = length_mm / 1000.0
        vol = L * (hand_width_mm / 1000.0) * (hand_thickness_mm
                                              / 1000.0)
        mass = vol * hand_density_kg_m3
        # Centre of gravity of a uniform strip at L/2; a tapered
        # hand sits nearer 0.4L, which is used as the practical
        # value and stated.
        r_cg = 0.4 * L
        imbalance = 0.0 if counterbalanced else mass * G * r_cg
        # Bearing friction floor: a real pivot always costs
        # something even when perfectly balanced.
        friction = 2.0e-5
        need = imbalance + friction
        sf = torque / need if need else None
        ok = sf is not None and sf >= required_sf
        if ok:
            max_len = length_mm
        rows.append({
            'handLengthMm': length_mm,
            'faceDiameterMm': length_mm * 2 + 20,
            'handMassG': round(mass * 1000.0, 4),
            'imbalanceTorqueNm': imbalance,
            'requiredTorqueNm': need,
            'safetyFactor': (round(sf, 2) if sf else None),
            'drivable': ok,
        })
    return {
        'ok': True, 'train': train_name,
        'outputTorqueNm': torque,
        'counterbalanced': counterbalanced,
        'handMaterialDensity': hand_density_kg_m3,
        'requiredSafetyFactor': required_sf,
        'sweep': rows,
        'maxHandLengthMm': max_len,
        'maxFaceDiameterMm': (max_len * 2 + 20 if max_len else None),
        'verdict': (
            f'at {torque:.3g} Nm the longest drivable hand is '
            f'{max_len} mm, i.e. a face about '
            f'{max_len * 2 + 20} mm across — a WALL CLOCK, not a '
            f'tower clock'
            if max_len else
            'this train cannot drive even the smallest hand in the '
            'sweep: the motor or the ratio has to change'),
        'counterbalanceNote': (
            'COUNTERBALANCING changes this answer completely: a '
            'balanced hand has ~zero gravity imbalance, leaving '
            'only bearing friction, which is why large dials use '
            'counterweighted hands. Re-run with '
            'counterbalanced=True to see the limit move.'),
        'honesty': 'gravity imbalance and a flat friction floor '
                   'only. NOT modelled: hand aerodynamics, the '
                   'starting torque needed to break stiction (a '
                   'stepper must overcome it EVERY step, and that '
                   'is the real-world limit), and the fact that a '
                   'stepper missing one step never catches up.',
    }
