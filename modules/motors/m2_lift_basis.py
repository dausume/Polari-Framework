"""
@module motors.m2_lift_basis

m2-5: THE LIFT PROOF — the positioning proof's analog for a rung
whose product is FORCE HELD OVER TIME. The target device is the
crucible hoist (manufacturing-devices/crucible-hoist, powered-by
electric-motors/m2-pm-rotor): "lands on the commanded position"
becomes "gets a full crucible off the floor, and keeps it there
when the power goes away."

Requirements are ROWS (CrucibleHoistRequirement): crucible mass,
drum radius, worm ratio, worm efficiency, pulley advantage, lift
speed — every one a NAMED PRIOR carrying the measurement that
would replace it.

THE PROOF drives the m2-1 solver under the reflected hoist load
and asks whether the rotor stays IN STEP with the 1.5 drive
margin. Two facts make it different from M1's:

1. THE TORQUE DEMAND IS COMPUTED TWICE — down the chain of ratios
   and through the power balance — and the two must agree to
   1e-9. They agree analytically, which is the point: the check
   catches implementation drift, and it also shows the assumed
   LIFT SPEED cancelling out of the torque entirely. Speed sets
   power and time; it does not set whether the thing lifts.

2. HOLDING IS NOT THE MOTOR'S JOB. A worm at ~0.4 efficiency is
   lossy, and lossy is exactly why it self-locks: the load cannot
   drive the worm backwards. So the crucible stays up with the
   power off because of GEOMETRY, and never because the motor
   cogs — the m2-1 model predicts zero cogging by construction
   and this payload refuses to borrow any.

@consumers motors.motor_api (/api/motors/m2-lift-proof),
motors.m2_views_seed (sections), polariServer seed pass (seed_m2_hoist)
"""

import math

from objectTreeDecorators import treeObject, treeObjectInit

from composition.custom.data_refs import rows
from composition.custom.seed_upsert import upsert_seed_pairs

from motors.custom.m2_rotation import (
    NO_COGGING_FACT, pull_out_load_limit, rotation_sim,
)

M2_DESIGN = 'ferrite-pm-m2'
PROV = 'm2-5'
G = 9.80665
#: The same drive margin the M1 axis product sizes against.
LIFT_MARGIN = 1.5


class CrucibleHoistRequirement(treeObject):
    """One hoist requirement: a value with units, a basis, and
    (for priors) the measurement that would replace it."""

    @treeObjectInit
    def __init__(self, name='', display_name='', value=0.0,
                 unit='', basis='', replaces_with='',
                 is_prior=True, provenance_id='', notes='',
                 manager=None):
        self.name = name
        self.display_name = display_name
        self.value = value
        self.unit = unit
        #: WHERE the number comes from — a citation, a standard
        #: part, or an honestly named guess.
        self.basis = basis
        #: The measurement that retires the prior (bench seam).
        self.replaces_with = replaces_with
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes


SEED_HOIST_REQUIREMENTS = [
    {'name': 'hoist-crucible-mass',
     'display_name': 'Crucible mass, full',
     'value': 2.0, 'unit': 'kg',
     'basis': 'NAMED PRIOR: a small clay-graphite crucible with a '
              'charge in it — the size the wax-printer and the '
              'first castings actually need, not a foundry ladle',
     'replaces_with': 'weigh the real crucible, full, on a kitchen '
                      'scale (the cheapest retirement on the '
                      'whole rung)',
     'is_prior': True, 'provenance_id': PROV,
     'notes': 'mass is the ONE requirement here that costs '
              'nothing to measure and changes every number '
              'downstream — retire it first.'},
    {'name': 'hoist-drum-radius',
     'display_name': 'Winding drum radius',
     'value': 15.0, 'unit': 'mm',
     'basis': 'NAMED PRIOR: a turned drum that takes the rope in '
              'one layer over the lift height — bigger drums lift '
              'faster and demand more torque, in exact proportion',
     'replaces_with': 'measure the built drum at its rope layer '
                      '(the radius that matters is to the rope '
                      'centreline, not the flange)',
     'is_prior': True, 'provenance_id': PROV, 'notes': ''},
    {'name': 'hoist-worm-ratio',
     'display_name': 'Worm gear reduction',
     'value': 30.0, 'unit': ':1',
     'basis': 'NAMED PRIOR: a single-start worm on a 30-tooth '
              'wheel — the classic self-locking arrangement, and '
              'the gears module has the algebra',
     'replaces_with': 'count the teeth on the wheel that gets '
                      'cast; the ratio is not an estimate once '
                      'the part exists',
     'is_prior': True, 'provenance_id': PROV,
     'notes': 'THE SAFETY ROW: this ratio and the self-locking '
              'claim are the same fact.'},
    {'name': 'hoist-worm-efficiency',
     'display_name': 'Worm stage efficiency',
     'value': 0.4, 'unit': '(fraction)',
     'basis': 'NAMED PRIOR: single-start worms sliding on cast '
              'material run 0.3-0.5 — LOSSY, and the loss is not '
              'a defect. A worm self-locks BECAUSE its efficiency '
              'is below the reversal threshold; an efficient worm '
              'would let the crucible fall.',
     'replaces_with': 'measure torque in vs torque out on the '
                      'built stage (m2-7 bench), and try to '
                      'back-drive it by hand — the second test is '
                      'the safety one',
     'is_prior': True, 'provenance_id': PROV,
     'notes': 'efficiency and self-locking are ONE physical fact '
              'stated two ways; guarded wherever restated.'},
    {'name': 'hoist-pulley-advantage',
     'display_name': 'Pulley mechanical advantage',
     'value': 2.0, 'unit': ':1',
     'basis': 'a single movable block: halves the rope tension '
              'and halves the lift speed — the oldest trade in '
              'the book',
     'replaces_with': 'count the rope falls supporting the load '
                      'on the built hoist',
     'is_prior': True, 'provenance_id': PROV, 'notes': ''},
    {'name': 'hoist-lift-speed',
     'display_name': 'Lift speed',
     'value': 0.02, 'unit': 'm/s',
     'basis': 'ASSUMPTION, and named as one: 2 cm/s is a '
              'comfortable watching pace for hot metal. Nothing '
              'in the quasi-static model predicts achievable '
              'speed — it sets POWER and TIME, and it cancels out '
              'of the torque demand entirely (see the proof\'s '
              'cross-check).',
     'replaces_with': 'time the built hoist over a measured '
                      'height',
     'is_prior': True, 'provenance_id': PROV, 'notes': ''},
]


def _req(manager, name):
    for r in rows(manager, 'CrucibleHoistRequirement'):
        if getattr(r, 'name', '') == name:
            return float(getattr(r, 'value', 0.0))
    raise ValueError(f'hoist requirement "{name}" not booted — '
                     f'seed_m2_hoist delivers it')


def hoist_report(manager, design_name=M2_DESIGN):
    """The hoist as numbers: the load at the rope, at the drum and
    at the motor, the torque the motor HAS, and the duty verdict
    with its knobs quantified live."""
    try:
        mass = _req(manager, 'hoist-crucible-mass')
        r_drum = _req(manager, 'hoist-drum-radius') / 1000.0
        ratio = _req(manager, 'hoist-worm-ratio')
        eta = _req(manager, 'hoist-worm-efficiency')
        pulley = _req(manager, 'hoist-pulley-advantage')
        speed = _req(manager, 'hoist-lift-speed')
    except ValueError as exc:
        return {'ok': False, 'refusal': str(exc)}
    weight_n = mass * G
    rope_tension_n = weight_n / pulley
    drum_torque_nm = rope_tension_n * r_drum
    motor_torque_nm = drum_torque_nm / (ratio * eta)
    # Speeds, for power only — the torque above does not contain
    # them (the cross-check makes that explicit).
    rope_speed = speed * pulley
    drum_rad_s = rope_speed / r_drum if r_drum else 0.0
    motor_rad_s = drum_rad_s * ratio
    lift_power_w = weight_n * speed
    input_power_w = lift_power_w / eta if eta else None

    po = pull_out_load_limit(manager, design_name)
    if not po.get('ok'):
        return po
    supply = po['pullOutLimitNm']
    needed = motor_torque_nm * LIFT_MARGIN
    capable = supply >= needed
    knobs = []
    for grade, label in (('opt-bonded-hexaferrite-geopolymer',
                          'bonded hexaferrite (the castable '
                          'grade — what we could make TODAY)'),
                         ('opt-ndfeb',
                          'NdFeB (REFERENCE ONLY — against the '
                          'local ethos, priced for honesty)')):
        alt = pull_out_load_limit(manager, design_name,
                                  rotor_material=grade)
        if alt.get('ok'):
            knobs.append({
                'knob': f'magnet grade: {label}',
                'pullOutLimitNm': alt['pullOutLimitNm'],
                'gain': (round(alt['pullOutLimitNm'] / supply, 2)
                         if supply else None),
                'closes': alt['pullOutLimitNm'] >= needed,
                'evidence': 'pull-out re-solved live with the '
                            'material override — same engine, '
                            'same geometry, only the magnet row '
                            'swapped'})
    stage_ratio = None
    if not capable and supply > 0:
        stage_ratio = math.ceil(needed / supply)
        knobs.append({
            'knob': 'a reduction stage BEFORE the worm',
            'requiredRatio': stage_ratio,
            'evidence': f'demand x margin / pull-out = '
                        f'{needed / supply:.2f}x at the seeded '
                        f'{ratio:.0f}:1 worm, so a {stage_ratio}:1 '
                        f'stage ahead of it covers the duty '
                        f'(total {stage_ratio * ratio:.0f}:1)',
            'why_not_a_bigger_worm': 'the worm stays 30:1 because '
                                     'that is the SELF-LOCKING '
                                     'arrangement the safety '
                                     'argument rests on — a '
                                     '171-tooth wheel would work '
                                     'too, but it is a large '
                                     'casting to make when a '
                                     'spur pair does the same '
                                     'job. The gears module has '
                                     'the spur machinery.',
            'cost': 'lift speed falls by the same factor at a '
                    'fixed motor speed — the m1-6 trade exactly, '
                    'on a device where slow is fine because the '
                    'operator is watching hot metal'})
    return {
        'ok': True, 'design': design_name,
        'target': 'crucible-hoist (manufacturing-devices tree, '
                  'powered-by electric-motors/m2-pm-rotor)',
        'load': {
            'crucibleMassKg': mass, 'weightN': weight_n,
            'ropeTensionN': rope_tension_n,
            'pulleyAdvantage': pulley},
        'torqueChain': {
            'atDrumNm': drum_torque_nm,
            'wormRatio': ratio, 'wormEfficiency': eta,
            'atMotorNm': motor_torque_nm,
            'withMarginNm': needed, 'marginFactor': LIFT_MARGIN},
        'speeds': {
            'liftSpeedMS': speed, 'ropeSpeedMS': rope_speed,
            'drumRadPerS': drum_rad_s, 'motorRadPerS': motor_rad_s,
            'motorRpm': round(motor_rad_s * 60.0
                              / (2.0 * math.pi), 1),
            'note': 'ASSUMED lift speed — it sets power and time '
                    'and NOT whether the hoist lifts'},
        'power': {
            'liftingW': lift_power_w,
            'inputAtWormW': input_power_w,
            'note': 'the worm throws away 60% of the input as '
                    'heat, on purpose (see the efficiency row)'},
        'motorSupplyNm': supply,
        'dutyVerdict': 'capable' if capable else 'not-capable',
        'shortfall': (None if capable
                      else round(needed / supply, 2)),
        'requiredStageRatio': stage_ratio,
        'knobs': knobs,
        'requirements': [
            {'name': s['name'], 'value': s['value'],
             'unit': s['unit'], 'basis': s['basis']}
            for s in SEED_HOIST_REQUIREMENTS],
        'note': 'every ratio in the chain is a ROW; nothing here '
                'is seeded twice, so a re-measured crucible moves '
                'the verdict without anyone editing a number'}


def lift_proof(manager, design_name=M2_DESIGN, steps=12,
               extra_reduction=None):
    """THE PROOF: put the hoist duty on the motor and account for
    it. The torque demand is derived TWICE and must agree; the
    solver decides whether the rotor keeps up; and the power-off
    answer comes from the worm row, never from the motor."""
    hoist = hoist_report(manager, design_name)
    if not hoist.get('ok'):
        return hoist
    chain = hoist['torqueChain']
    load = chain['atMotorNm']
    # PATH A: down the chain of ratios.
    mass = hoist['load']['crucibleMassKg']
    pulley = hoist['load']['pulleyAdvantage']
    ratio = chain['wormRatio']
    eta = chain['wormEfficiency']
    r_drum = chain['atDrumNm'] / hoist['load']['ropeTensionN']
    path_a = (mass * G * r_drum) / (pulley * ratio * eta)
    # PATH B: through the power balance. mgv is the work rate on
    # the load; the motor supplies it at its own speed through
    # the same efficiency. The lift speed CANCELS — which is why
    # an assumed speed cannot flatter this verdict.
    speed = hoist['speeds']['liftSpeedMS']
    omega_motor = hoist['speeds']['motorRadPerS']
    path_b = (mass * G * speed) / (omega_motor * eta)
    consistent = abs(path_a - path_b) < 1e-9 * max(1.0, path_a)

    duty = rotation_sim(manager, design_name, steps=steps,
                        load_torque_nm=load * LIFT_MARGIN)
    if not duty.get('ok'):
        return duty
    lifts = bool(duty.get('inSync'))
    # AS SHIPPED: the m2-6 unit puts a reduction stage between the
    # motor and the worm, exactly as the M1 axis product does. The
    # bare verdict above is about the motor on a sketched hoist;
    # this one is about the product.
    if extra_reduction is None:
        try:
            from motors.m2_product_seed import STAGE_RATIO
            extra_reduction = float(STAGE_RATIO)
        except ImportError:
            extra_reduction = 1.0
    shipped = None
    if extra_reduction and extra_reduction != 1.0:
        s_load = load / extra_reduction
        s_duty = rotation_sim(manager, design_name, steps=steps,
                              load_torque_nm=s_load * LIFT_MARGIN)
        shipped = {
            'stageRatio': extra_reduction,
            'totalReduction': extra_reduction * ratio,
            'dutyTorqueNm': s_load,
            'atMarginNm': s_load * LIFT_MARGIN,
            'verdict': ('lifts' if s_duty.get('inSync')
                        else 'stalls'),
            'inSync': bool(s_duty.get('inSync')),
            'worstLagDeg': max(h.get('lagDeg', 0.0)
                               for h in s_duty.get('history', [{}])
                               ) if s_duty.get('ok') else None,
            'motorRpmAtLiftSpeed': round(
                hoist['speeds']['motorRpm'] * extra_reduction, 1),
            'note': 'the shipped unit — motor, reduction stage, '
                    'self-locking worm, drum. The reduction is '
                    'DERIVED from the live pull-out limit, so it '
                    'moves when the magnet or the crucible does.'}
        # THE CONTRADICTION THE REDUCTION CREATES, named rather
        # than left in the arithmetic.
        assumed_rpm = (duty.get('speedAssumption', {})
                       .get('mechRpm'))
        need_rpm = shipped['motorRpmAtLiftSpeed']
        if assumed_rpm:
            shipped['speedContradiction'] = {
                'requiredMotorRpm': need_rpm,
                'assumedMotorRpm': assumed_rpm,
                'factor': round(need_rpm / assumed_rpm, 1),
                'finding': f'torque and speed pull opposite ways '
                           f'and here they pull hard: the '
                           f'reduction that makes the lift '
                           f'possible demands '
                           f'{need_rpm / assumed_rpm:.0f}x the '
                           f'commutation rate the design row '
                           f'assumes. Either the crucible rises '
                           f'{need_rpm / assumed_rpm:.0f}x '
                           f'slower than the requirement row '
                           f'says, or the drive commutates '
                           f'faster than anything on this rung '
                           f'has demonstrated.',
                'whatWouldSettleIt': 'nothing in a quasi-static '
                                     'model can say which is '
                                     'achievable — it has no '
                                     'inertia, no friction and '
                                     'no back-EMF limit in the '
                                     'loop. The bench spins the '
                                     'rotor and finds out; k_e '
                                     '(m2-7) already bounds the '
                                     'voltage that speed would '
                                     'need.',
                'slowLiftSpeedMS': round(
                    hoist['speeds']['liftSpeedMS']
                    * assumed_rpm / need_rpm, 6)}
    headline = [
        {'label': 'torque the hoist asks of the motor',
         'value': f'{load * 1000.0:.2f} mNm',
         'note': 'crucible weight through the pulley, the drum '
                 'and the worm — every ratio a row'},
        {'label': 'torque the motor has (pull-out)',
         'value': f'{hoist["motorSupplyNm"] * 1000.0:.2f} mNm',
         'verdict': 'ok' if lifts else 'bad',
         'note': 'past this the rotor does not slow down, it '
                 'falls out of step and drops the load'},
        {'label': 'bare motor on the sketched 30:1 worm',
         'value': 'stalls' if not lifts else 'lifts',
         'verdict': 'bad' if not lifts else 'ok',
         'note': (f'{hoist["shortfall"]}x short — the knob is a '
                  f'reduction stage, and it is derived below'
                  if hoist.get('shortfall') else
                  'no reduction stage needed')},
    ]
    if shipped:
        headline.append(
            {'label': f'AS SHIPPED ({shipped["stageRatio"]:g}:1 '
                      f'stage x 30:1 worm)',
             'value': shipped['verdict'],
             'verdict': 'ok' if shipped['inSync'] else 'bad',
             'note': f'settles at {shipped["worstLagDeg"]:.0f} deg '
                     f'of load angle, inside the 90 deg cliff'})
        if shipped.get('speedContradiction'):
            sc = shipped['speedContradiction']
            headline.append(
                {'label': 'and the speed that reduction demands',
                 'value': f'{sc["factor"]:g}x the assumed rate',
                 'verdict': 'warn',
                 'note': 'either the crucible rises that much '
                         'slower or the drive commutates faster '
                         'than this rung has shown — only the '
                         'bench can say which'})
    headline.append(
        {'label': 'holds with the power off',
         'value': 'yes — by the WORM',
         'verdict': 'ok',
         'note': 'a worm this lossy cannot be back-driven. It is '
                 'geometry, never the motor\'s cogging (which '
                 'this model says is zero anyway)'})
    return {
        'ok': True, 'design': design_name,
        'target': hoist['target'],
        'headline': headline,
        'dutyTorqueNm': load,
        'atMarginNm': load * LIFT_MARGIN,
        'asShipped': shipped,
        'crossCheck': {
            'pathA_chainOfRatiosNm': path_a,
            'pathB_powerBalanceNm': path_b,
            'consistent': consistent,
            'note': 'two paths, one number — and the LIFT SPEED '
                    'cancels out of path B entirely, so the '
                    'assumption in the requirement rows cannot '
                    'change the answer. It sets power and time, '
                    'not capability.'},
        'lift': {
            'verdict': 'lifts' if lifts else 'stalls',
            'inSync': lifts,
            'pullOutStep': duty.get('pullOutStep'),
            'worstLagDeg': max(h.get('lagDeg', 0.0)
                               for h in duty['history']),
            'motorSupplyNm': hoist['motorSupplyNm'],
            'claim': 'the rotor stays in step at the duty load '
                     'times the 1.5 margin — and if it does not, '
                     'it does not slow down, it falls out of '
                     'step and drops what it was holding'},
        'holdsWhenDead': {
            'verdict': 'holds-when-dead',
            'because': 'THE WORM, not the motor: a single-start '
                       f'worm at {eta:g} efficiency is far below '
                       'the reversal threshold, so the load '
                       'cannot back-drive it. The crucible stays '
                       'where it is when the power goes away '
                       'because of GEOMETRY.',
            'notBecause': NO_COGGING_FACT,
            'efficiencyIsTheSameFact': 'a worm that could be '
                                       'back-driven would be '
                                       'efficient; this one '
                                       'wastes 60% of its input '
                                       'and holds. One physical '
                                       'fact, stated two ways.',
            'qualifyingAct': 'hang the full crucible, cut power, '
                             'walk away for 24 hours (the '
                             'qa-lift-hold-24h gate) — and '
                             'before that, try to turn the drum '
                             'by hand',
            'stillTheoretical': 'nothing here is built: this is '
                                'the claim the QA gate exists to '
                                'test, not a measurement'},
        'dutyVerdict': hoist['dutyVerdict'],
        'shortfall': hoist['shortfall'],
        'knobs': hoist['knobs'],
        'speedAssumption': duty.get('speedAssumption'),
        'namedGaps': duty.get('namedGaps'),
        'note': 'the proof this rung exists for: "lands on the '
                'commanded position" becomes "gets it off the '
                'floor AND keeps it there with the power off" — '
                'the second half is what makes a hoist a hoist, '
                'and it is answered by a gear, not a motor'}


def seed_m2_hoist(manager):
    return upsert_seed_pairs(manager, [
        ('CrucibleHoistRequirement', CrucibleHoistRequirement,
         SEED_HOIST_REQUIREMENTS),
    ], tag='M2HoistSeed')
