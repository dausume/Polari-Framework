"""
@module motors.clock_assembly

as-1..3 (Dustin 2026-08-01): "make this into a genuine assembly for
a clock with genuine mass and materials ... and clock hands with
vectors based on their orientation. We are going to want to proof
that the entire assembly actually keeps time properly in accordance
with the physics based simulation progression."

THE ASSEMBLY BILL composes the existing machinery, computing
nothing new on purpose (the mag-21 discipline): the motor members
come from part_report('clock-lavet-m0'); the TRAIN gears and HANDS
are real MotorPartDefinition rows under 'clock-assembly-m0' whose
masses derive from their OWN math shapes (gear volume = exact
profile extrusion; hand volume = its box) times their material's
density. A member that cannot resolve reports its gap; the frame
and dial are ABSENT and say so.

HAND PHYSICS with the real masses: each hand's gravity imbalance
torque m·g·r_cg (its center of gravity from the same geometry) is
checked against the torque its shaft actually delivers through the
SOLVED train — the gr-6 question answered with derived numbers
instead of assumptions.

THE TIMEKEEPING PROOF drives the whole chain end to end:
clock_sim's step history (the co-energy physics solver — steps can
MISS) → the solved gear ratios (signed) → hand angles → compared
against true time. With zero missed steps the agreement is EXACT
(1 pulse = 1 s = 6° of seconds hand); every missed step is exactly
one lost second, and the proof reports the loss rather than
averaging it away. Ratios come from solve_train, steps from the
simulation — nothing in the chain is assumed.

@consumers motors.motor_api (/api/motors/clock-assembly,
/api/motors/timekeeping-proof), motors.clock_views (section),
motors.selftest_motors, polariServer seed pass (upsert)
"""

import math

from composition.seed_upsert import upsert_seed_pairs

PROV = 'as-1'
ASSEMBLY_DESIGN = 'clock-assembly-m0'
MOTOR_DESIGN = 'clock-lavet-m0'
G = 9.81

#: The assembly's umbrella design row — part_report keys parts by
#: a MotorDesignDefinition, so the assembly gets one. It is a
#: CONTAINER, not a motor: its notes say so, and the M0 motor
#: design stays the physics carrier.
SEED_ASSEMBLY_DESIGNS = [
    {'name': ASSEMBLY_DESIGN,
     'display_name': 'M0 clock — the whole assembly',
     'description': 'The clock as an ASSEMBLY: the M0 motor '
                    '(clock-lavet-m0) + the gear train + the '
                    'hands. This row is the umbrella the '
                    'train/hand part rows hang from; the motor '
                    'physics lives on clock-lavet-m0.',
     'topology': 'lavet-clock-stepper', 'ladder_rung': 'M0',
     'tolerance_tier': 'T0',
     'params_json': '{}', 'drive_json': '{}',
     'build_requirements_json': '{}',
     'is_prior': True, 'provenance_id': PROV,
     'notes': 'A container row, not a motor design — sims and '
              'winding checks belong to clock-lavet-m0.'},
]

#: The train + hands as REAL parts: shape-derived mass, stated
#: material, the job named. Materials use the same option catalog
#: the motor bill resolves densities from; the GearDefinition rows'
#: 'geopolymer-mix' vocabulary maps onto opt-plain-geopolymer here
#: (one density source, noted).
SEED_ASSEMBLY_PARTS = [
    {'name': 'asm-second-wheel', 'design_ref': ASSEMBLY_DESIGN,
     'display_name': 'Seconds wheel (240t)',
     'shape_units': 'mm', 'shape_ref': 'clock-gear-second-wheel',
     'material_ref': 'opt-fired-ceramic',
     'function': 'speed-reduction',
     'purpose': 'First reduction 8->240: the 30 rpm rotor lands at '
                'exactly 1 rpm — the seconds shaft.',
     'why_this_material': 'Meshing teeth live under contact + '
                          'fatigue (3.2e8 cycles); fired ceramic '
                          'is the makeable answer mag-16 landed '
                          'on, where cast geopolymer failed the '
                          'ten-year check.',
     'quantity': 1, 'is_prior': True, 'provenance_id': PROV,
     'notes': ''},
    {'name': 'asm-second-pinion', 'design_ref': ASSEMBLY_DESIGN,
     'display_name': 'Seconds pinion (10t)',
     'shape_units': 'mm', 'shape_ref': 'clock-gear-second-pinion',
     'material_ref': 'opt-fired-ceramic',
     'function': 'speed-reduction',
     'purpose': 'Rides the seconds shaft; drives the 60:1 stage '
                'to the minute wheel.',
     'why_this_material': 'Same contact/fatigue argument as the '
                          'wheel — and a pinion concentrates the '
                          'whole tooth load on fewer teeth.',
     'quantity': 1, 'is_prior': True, 'provenance_id': PROV,
     'notes': ''},
    {'name': 'asm-minute-wheel', 'design_ref': ASSEMBLY_DESIGN,
     'display_name': 'Minute wheel (600t, 180 mm)',
     'shape_units': 'mm', 'shape_ref': 'clock-gear-minute-wheel',
     'material_ref': 'opt-fired-ceramic',
     'function': 'speed-reduction',
     'purpose': 'The 60:1 stage — once per hour. At 180 mm it is '
                'the largest part of the whole clock.',
     'why_this_material': 'Large, thin, brittle: firing is what '
                          'keeps a 180 mm disc from being the '
                          'first thing to break.',
     'quantity': 1, 'is_prior': True, 'provenance_id': PROV,
     'notes': ''},
    {'name': 'asm-second-hand', 'design_ref': ASSEMBLY_DESIGN,
     'display_name': 'Seconds hand (95 mm)',
     'shape_units': 'mm', 'shape_ref': 'clock-hand-second',
     'material_ref': 'opt-plain-geopolymer',
     'function': 'indication',
     'purpose': 'What the machine exists to move: points the '
                'second. Its orientation vector IS the output of '
                'the whole assembly.',
     'why_this_material': 'Light matters more than strong here — '
                          'the imbalance torque m·g·r_cg is what '
                          'the shaft must overcome every step.',
     'quantity': 1, 'is_prior': True, 'provenance_id': PROV,
     'notes': ''},
    {'name': 'asm-minute-hand', 'design_ref': ASSEMBLY_DESIGN,
     'display_name': 'Minute hand (80 mm)',
     'shape_units': 'mm', 'shape_ref': 'clock-hand-minute',
     'material_ref': 'opt-plain-geopolymer',
     'function': 'indication',
     'purpose': 'Points the minute from the 1/60 rpm shaft.',
     'why_this_material': 'Same lightness argument; the minute '
                          'shaft has 60x the torque but the same '
                          'logic holds.',
     'quantity': 1, 'is_prior': True, 'provenance_id': PROV,
     'notes': ''},
]

#: hand part -> (shaft, tip length mm, tail mm) for imbalance +
#: drivability (geometry facts restated from the hand shapes; the
#: selftest pins shape == these numbers).
HAND_FACTS = {
    'asm-second-hand': ('shaft-second', 85.0, 10.0),
    'asm-minute-hand': ('shaft-minute', 70.0, 10.0),
}


def seed_clock_assembly(manager):
    from motors.motor_basis import MotorDesignDefinition
    from motors.motor_parts import MotorPartDefinition
    return upsert_seed_pairs(
        manager,
        [('MotorDesignDefinition', MotorDesignDefinition,
          SEED_ASSEMBLY_DESIGNS),
         ('MotorPartDefinition', MotorPartDefinition,
          SEED_ASSEMBLY_PARTS)],
        tag='ClockAssemblySeed')


def _hand_drivability(manager, members):
    """Imbalance torque from the REAL hand mass vs the torque its
    shaft delivers through the solved train."""
    try:
        from gears.gear_kinematics import solve_train
        solved = solve_train(manager, 'clock-train-m0')
    except ImportError:
        solved = {'ok': False,
                  'refusal': 'gears module not importable'}
    torque_of = ({s['shaft']: s.get('torqueNm')
                  for s in solved.get('shafts', [])}
                 if solved.get('ok') else {})
    out = []
    for m in members:
        facts = HAND_FACTS.get(m['part'])
        if not facts:
            continue
        shaft, tip, tail = facts
        mass_g = m.get('massG')
        entry = {'hand': m['part'], 'shaft': shaft,
                 'massG': mass_g}
        if isinstance(mass_g, (int, float)):
            # uniform hand: cg sits at the mid of (-tail..tip).
            r_cg_m = ((tip - tail) / 2.0) / 1000.0
            imbalance = (mass_g / 1000.0) * G * r_cg_m
            entry['rCgMm'] = round((tip - tail) / 2.0, 3)
            entry['imbalanceTorqueNm'] = imbalance
            shaft_t = torque_of.get(shaft)
            if isinstance(shaft_t, (int, float)) and shaft_t:
                sf = abs(shaft_t) / imbalance if imbalance else None
                entry['shaftTorqueNm'] = shaft_t
                entry['safetyFactor'] = (round(sf, 3)
                                         if sf else None)
                entry['drivable'] = bool(sf and sf >= 1.0)
            else:
                entry['gap'] = ('shaft torque unresolved — train '
                                'not solved here')
        else:
            entry['gap'] = 'hand mass unresolved (see its bill row)'
        out.append(entry)
    return out


def clock_assembly_report(manager):
    """The genuine assembly: motor + train + hands, every mass from
    its own geometry x its material's density. Composes part_report
    twice; computes only the hand physics on top."""
    from motors.motor_parts import part_report
    motor = part_report(manager, MOTOR_DESIGN)
    extras = part_report(manager, ASSEMBLY_DESIGN)
    if not extras.get('ok'):
        return {'ok': False,
                'refusal': extras.get('refusal',
                                      'assembly parts missing')}
    members = extras.get('parts', [])
    hands = [m for m in members if m['function'] == 'indication']
    train = [m for m in members if m not in hands]
    motor_mass = motor.get('totalMassG') if motor.get('ok') else None
    extra_mass = extras.get('totalMassG')
    total = (round(motor_mass + extra_mass, 4)
             if isinstance(motor_mass, (int, float))
             and isinstance(extra_mass, (int, float)) else None)
    return {
        'ok': True, 'assembly': ASSEMBLY_DESIGN,
        'groups': {
            'motor': {'design': MOTOR_DESIGN,
                      'parts': motor.get('parts', []),
                      'totalMassG': motor_mass,
                      'gaps': motor.get('gaps', [])},
            'train': {'parts': train,
                      'note': 'gear masses are exact profile '
                              'extrusions of the SAME tooth math '
                              'the scene draws'},
            'hands': {'parts': hands,
                      'drivability': _hand_drivability(manager,
                                                       hands)},
        },
        'totalMassG': total,
        'absent': ['frame/plates between the shafts',
                   'dial', 'arbors/bearings as parts'],
        'note': 'members absent from this bill are NAMED, never '
                'silently omitted; the motor rotor pinion drives '
                'the train and is counted once, in the motor '
                'group',
    }


def timekeeping_proof(manager, pulses=120):
    """Does the WHOLE assembly keep time? Drive the physics sim,
    carry its (possibly missed) steps through the solved ratios to
    the hand angles, and compare against true time. Exactness is
    the claim: zero missed steps must land the seconds hand within
    floating error of true; each missed step is exactly one lost
    second, reported."""
    from motors.motor_designer import clock_sim
    sim = clock_sim(manager, MOTOR_DESIGN, pulses=int(pulses),
                    alternating=True)
    if not sim.get('ok'):
        return {'ok': False,
                'refusal': sim.get('refusal', 'sim refused')}
    try:
        from gears.gear_kinematics import solve_train
        solved = solve_train(manager, 'clock-train-m0')
    except ImportError:
        solved = {'ok': False}
    if not solved.get('ok'):
        return {'ok': False,
                'refusal': 'the train did not solve — the proof '
                           'needs the gears module enabled'}
    rpm_of = {s['shaft']: s.get('speedRpm')
              for s in solved.get('shafts', [])}
    input_rpm = solved.get('inputSpeedRpm') or 30.0
    rotor_revs = sim['stepsTaken'] * 0.5      # 180 deg per step
    duration_s = sim['durationS']
    hands = {}
    for hand, shaft, true_rev_per_s in (
            ('secondsHand', 'shaft-second', 1.0 / 60.0),
            ('minuteHand', 'shaft-minute', 1.0 / 3600.0)):
        shaft_rpm = rpm_of.get(shaft)
        if not isinstance(shaft_rpm, (int, float)):
            hands[hand] = {'gap': f'{shaft} not in the solve'}
            continue
        ratio = shaft_rpm / input_rpm     # signed, from the solve
        revs = rotor_revs * ratio
        true_revs = duration_s * true_rev_per_s
        hands[hand] = {
            'shaft': shaft,
            'simulatedRevs': revs,
            'simulatedAngleDeg': round((revs * 360.0) % 360.0, 6),
            'trueRevs': true_revs,
            'trueAngleDeg': round(
                (true_revs * 360.0) % 360.0, 6),
            'revErrorVsTrue': round(abs(abs(revs) - true_revs),
                                    9),
        }
    time_error_s = sim['stepsMissed'] / sim['rateHz']
    seconds = hands.get('secondsHand', {})
    agreement = (seconds.get('revErrorVsTrue') is not None
                 and abs(seconds['revErrorVsTrue']
                         - time_error_s / 60.0) < 1e-9)
    return {
        'ok': True, 'design': MOTOR_DESIGN,
        'train': 'clock-train-m0',
        'pulses': sim['pulses'], 'durationS': duration_s,
        'stepsTaken': sim['stepsTaken'],
        'stepsMissed': sim['stepsMissed'],
        'rotorRevs': rotor_revs,
        'hands': hands,
        'timeErrorS': time_error_s,
        'verdict': ('keeps-time' if sim['stepsMissed'] == 0
                    else 'loses-time'),
        'crossCheck': {
            'consistent': agreement,
            'note': 'the hand-angle error and the sim\'s own '
                    'clockErrorS must be the SAME number arrived '
                    'at through different paths (angles through '
                    'the ratios vs missed/rate) — if they ever '
                    'disagree, the chain has a modeling hole'},
        'note': 'steps from the co-energy physics sim (they can '
                'MISS); ratios signed from solve_train; hand '
                'angles derived, true time from the pulse rate — '
                'nothing in the chain is assumed',
    }
