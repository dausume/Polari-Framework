"""
@module motors.clock_assembly_seed

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
/api/motors/timekeeping-proof), motors.clock_views_basis (section),
motors.motors_selftest, polariServer seed pass (upsert)
"""

import math

from composition.custom.seed_upsert import upsert_seed_pairs

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
    {'name': 'asm-second-hand-cw', 'design_ref': ASSEMBLY_DESIGN,
     'display_name': 'Seconds-hand counterweight',
     'shape_units': 'mm', 'shape_ref': 'clock-hand-second-cw',
     'material_ref': 'opt-plain-geopolymer',
     'function': 'balance',
     'purpose': 'Cancels the seconds hand\'s gravity moment so '
                'the shaft only fights friction — the fix the '
                'as-3 drivability finding demanded.',
     'why_this_material': 'Mass is the point here; the cheap '
                          'cast is exactly right.',
     'quantity': 1, 'is_prior': True, 'provenance_id': PROV,
     'notes': 'Sized so m_cw x r_cw ~ m_hand x r_cg (gr-6: a '
              'balanced hand has ~zero gravity imbalance).'},
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

#: mp0-3: the seconds hand FAILED drivability bare (SF 0.60, the
#: as-3 finding) — gr-6 says counterbalancing nearly erases the
#: imbalance, so it gets a counterweight PART whose moment nearly
#: cancels the hand's. counterweight part -> (hand part, r_cw mm).
HAND_COUNTERWEIGHTS = {
    'asm-second-hand-cw': ('asm-second-hand', 7.0),
}


def seed_clock_assembly(manager):
    from motors.motor_basis import MotorDesignDefinition
    from motors.motor_parts_basis import MotorPartDefinition
    return upsert_seed_pairs(
        manager,
        [('MotorDesignDefinition', MotorDesignDefinition,
          SEED_ASSEMBLY_DESIGNS),
         ('MotorPartDefinition', MotorPartDefinition,
          SEED_ASSEMBLY_PARTS)],
        tag='ClockAssemblySeed')


def _train_torques(manager):
    """Shaft torques for the drivability check — the REAL M0
    envelope through the gr-5 splice when it answers, else the
    train row's seeded prior, LABELED either way."""
    try:
        from gears.custom.gear_motor import motor_driven_train
        spliced = motor_driven_train(manager, 'clock-train-m0',
                                     MOTOR_DESIGN)
    except Exception:
        spliced = {'ok': False}
    if spliced.get('ok'):
        return ({s['shaft']: s.get('torqueNm')
                 for s in spliced.get('shafts', [])},
                f"gr-5 splice ({spliced.get('torqueBasis', 'M0')})")
    try:
        from gears.custom.gear_kinematics import solve_train
        solved = solve_train(manager, 'clock-train-m0')
    except ImportError:
        return {}, 'gears module not importable'
    if not solved.get('ok'):
        return {}, 'train did not solve'
    return ({s['shaft']: s.get('torqueNm')
             for s in solved.get('shafts', [])},
            'seeded train prior (1e-6 Nm input) — the gr-5 '
            'splice did not answer here')


def _hand_drivability(manager, members):
    """NET imbalance torque (hand minus its counterweight, both
    from REAL masses) vs the torque its shaft delivers."""
    torque_of, basis = _train_torques(manager)
    by_name = {m['part']: m for m in members}
    cw_of = {}
    for cw_part, (hand_part, r_cw) in HAND_COUNTERWEIGHTS.items():
        cw_of[hand_part] = (by_name.get(cw_part), r_cw)
    out = []
    for m in members:
        facts = HAND_FACTS.get(m['part'])
        if not facts:
            continue
        shaft, tip, tail = facts
        mass_g = m.get('massG')
        entry = {'hand': m['part'], 'shaft': shaft,
                 'massG': mass_g, 'torqueBasis': basis}
        if isinstance(mass_g, (int, float)):
            r_cg_mm = (tip - tail) / 2.0
            moment = mass_g * r_cg_mm          # g*mm
            cw, r_cw = cw_of.get(m['part'], (None, 0.0))
            cw_mass = (cw or {}).get('massG')
            if isinstance(cw_mass, (int, float)):
                entry['counterweight'] = {
                    'part': cw['part'], 'massG': cw_mass,
                    'rMm': r_cw}
                moment = moment - cw_mass * r_cw
            imbalance = abs(moment) / 1e6 * G   # g*mm -> kg*m
            entry['rCgMm'] = round(r_cg_mm, 3)
            entry['netImbalanceTorqueNm'] = imbalance
            shaft_t = torque_of.get(shaft)
            if isinstance(shaft_t, (int, float)) and shaft_t:
                sf = (abs(shaft_t) / imbalance if imbalance
                      else None)
                entry['shaftTorqueNm'] = shaft_t
                entry['safetyFactor'] = (round(sf, 3)
                                         if sf else None)
                entry['drivable'] = bool(sf is None or sf >= 1.0)
                if sf is None:
                    entry['note'] = ('balanced to ~zero gravity '
                                     'moment — friction (not '
                                     'modeled) is the residual '
                                     'load, said not hidden')
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
    from motors.motor_parts_basis import part_report
    motor = part_report(manager, MOTOR_DESIGN)
    extras = part_report(manager, ASSEMBLY_DESIGN)
    if not extras.get('ok'):
        return {'ok': False,
                'refusal': extras.get('refusal',
                                      'assembly parts missing')}
    members = extras.get('parts', [])
    hands = [m for m in members
             if m['function'] in ('indication', 'balance')]
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
    from motors.custom.motor_designer import clock_sim
    sim = clock_sim(manager, MOTOR_DESIGN, pulses=int(pulses),
                    alternating=True)
    if not sim.get('ok'):
        return {'ok': False,
                'refusal': sim.get('refusal', 'sim refused')}
    try:
        from gears.custom.gear_kinematics import solve_train
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
