"""
@module motors.m1_positioning

m1-5: THE POSITIONING PROOF — the timekeeping proof's analog for a
rung whose product is POSITION. The target device is the wax
printer's axis (manufacturing-devices/wax-3d-printer, powered-by
electric-motors/m1-switched-reluctance): "keeps time" becomes
"lands on the commanded position through a leadscrew."

Requirements are ROWS (PrinterAxisRequirement): leadscrew lead,
axis load force, drive efficiency, position tolerance — every one
a NAMED prior with the measurement that would replace it. Steps/mm
DERIVES (12 steps/rev from the m1-1 arithmetic, lead from the
row); it is never seeded, because seeding a derivable number is
how two copies drift.

THE PROOF runs the m1-1 solver under the axis's reflected load
torque and turns the step history into a POSITION LEDGER in mm:
- zero missed steps -> mm error EXACTLY zero (pinned);
- a missed step is not M0's gentle non-event: with no detent, a
  reluctance machine that misses SLIPS BACKWARD a full pole pitch
  (loss of synchronism, exactly as real stepper datasheets warn) —
  so the weak drive loses MORE than its missed steps, every slip
  is NAMED, and the ledger still balances exactly by two paths
  (final-position delta vs the sum of per-step shortfalls).

THE VERDICT: can this M1, with today's materials, hold the
printer's axis duty — and if not, WHICH knob moves it. The knobs
are QUANTIFIED live (bio-steel stator via material override, gear
reduction ratio derived from the shortfall), never hand-waved.

@consumers motors.motor_api, motors.m1_views (sections),
polariServer seed pass (seed_m1_axis)
"""

import math

from objectTreeDecorators import treeObject, treeObjectInit

from composition.data_refs import rows
from composition.seed_upsert import upsert_seed_pairs

from motors.m1_sequencing import (
    STEP_DEG, holding_torque, sequence_sim,
)

M1_DESIGN = 'reluctance-6s4p-m1'
PROV = 'm1-5'
STEPS_PER_REV = int(round(360.0 / STEP_DEG))


class PrinterAxisRequirement(treeObject):
    """One printer-axis requirement: a value with units, a basis,
    and (for priors) the measurement that would replace it."""

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


SEED_AXIS_REQUIREMENTS = [
    {'name': 'axis-leadscrew-lead',
     'display_name': 'Leadscrew lead (travel per revolution)',
     'value': 1.25, 'unit': 'mm/rev',
     'basis': 'M8x1.25 threaded rod — a hardware-store part, the '
              'same local-first sourcing argument as the 608 '
              'bearing (mag-1)',
     'replaces_with': 'measure actual travel over 20 turns with '
                      'calipers (bench, W2 instruments)',
     'is_prior': True, 'provenance_id': PROV,
     'notes': 'a Tr8x8 printer leadscrew moves 6.4x faster and '
              'is the COMMERCIAL route\'s part; the M8 rod is '
              'the pure-local one — m1-6 carries the fork.'},
    {'name': 'axis-load-force',
     'display_name': 'Axis load force (carriage friction + drag)',
     'value': 5.0, 'unit': 'N',
     'basis': 'NAMED PRIOR: a light printed carriage on smooth '
              'rods; friction dominates, gravity excluded (X/Y '
              'axis)',
     'replaces_with': 'spring-scale drag test on the real '
                      'carriage (m1-7 bench, W2)',
     'is_prior': True, 'provenance_id': PROV, 'notes': ''},
    {'name': 'axis-drive-efficiency',
     'display_name': 'Leadscrew drive efficiency',
     'value': 0.3, 'unit': '(fraction)',
     'basis': 'NAMED PRIOR: steel screw in a printed/brass nut, '
              'unlubricated threaded rod class — self-locking, '
              'lossy, and honest about it',
     'replaces_with': 'measure torque-to-force on the assembled '
                      'axis (m1-7)',
     'is_prior': True, 'provenance_id': PROV, 'notes': ''},
    {'name': 'axis-position-tolerance',
     'display_name': 'Position tolerance per move',
     'value': 0.2, 'unit': 'mm',
     'basis': 'wax droplet scale: the printer lays ~0.4 mm '
              'features; half a feature is the classic rule',
     'replaces_with': 'the printer\'s own first-layer QA gate',
     'is_prior': True, 'provenance_id': PROV, 'notes': ''},
]


def _req(manager, name):
    for r in rows(manager, 'PrinterAxisRequirement'):
        if getattr(r, 'name', '') == name:
            return float(getattr(r, 'value', 0.0))
    raise ValueError(f'axis requirement "{name}" not booted — '
                     f'seed_m1_axis delivers it')


def axis_report(manager, design_name=M1_DESIGN):
    """The axis as numbers: steps/mm DERIVED, the reflected load
    torque the motor must beat, the holding torque it has, and the
    DUTY VERDICT with its knobs quantified live."""
    try:
        lead = _req(manager, 'axis-leadscrew-lead')
        force = _req(manager, 'axis-load-force')
        eff = _req(manager, 'axis-drive-efficiency')
        tol = _req(manager, 'axis-position-tolerance')
    except ValueError as exc:
        return {'ok': False, 'refusal': str(exc)}
    mm_per_step = lead / STEPS_PER_REV
    # Torque to push force F through a screw of lead L at
    # efficiency eta: T = F*L/(2*pi*eta) — the standard screw
    # relation, with the lossy eta carried as its own row.
    demand_nm = force * (lead / 1000.0) / (2.0 * math.pi * eff)
    hold = holding_torque(manager, design_name)
    if not hold.get('ok'):
        return hold
    supply_nm = hold['peakTorqueNm']
    capable = supply_nm > demand_nm
    knobs = []
    better = holding_torque(
        manager, design_name,
        stator_material='opt-galvanized-bio-steel',
        rotor_material='opt-galvanized-bio-steel')
    if better.get('ok'):
        knobs.append({
            'knob': 'bio-steel stator + rotor (the m1-6 fork)',
            'holdingTorqueNm': better['peakTorqueNm'],
            'gain': round(better['peakTorqueNm'] / supply_nm, 1),
            'closes': better['peakTorqueNm'] > demand_nm,
            'evidence': 'holding_torque re-solved live with '
                        'opt-galvanized-bio-steel via material '
                        'override — same engine, same geometry'})
    ratio = demand_nm / supply_nm if supply_nm > 0 else None
    if ratio and ratio > 1.0:
        knobs.append({
            'knob': 'gear reduction between motor and screw',
            'requiredRatio': math.ceil(ratio * 1.5),
            'evidence': f'demand/supply = {ratio:.0f}x, times the '
                        f'1.5 drive margin — the gears module '
                        f'(gr-1) has the train machinery',
            'cost': 'resolution IMPROVES by the same ratio; speed '
                    'falls by it (speed is already an assumption)'})
    return {
        'ok': True, 'design': design_name,
        'stepsPerRev': STEPS_PER_REV,
        'stepsPerMm': round(STEPS_PER_REV / lead, 3),
        'mmPerStep': round(mm_per_step, 5),
        'toleranceMm': tol,
        'resolutionVerdict': (
            'mm/step < tolerance: full-step resolution suffices'
            if mm_per_step < tol else
            'mm/step EXCEEDS tolerance — full steps cannot land '
            'inside it'),
        'loadTorqueDemandNm': demand_nm,
        'holdingTorqueNm': supply_nm,
        'dutyVerdict': ('capable' if capable else 'not-capable'),
        'shortfall': (None if capable
                      else round(demand_nm / supply_nm, 1)),
        'knobs': knobs,
        'requirements': [
            {'name': s['name'], 'value': s['value'],
             'unit': s['unit'], 'basis': s['basis']}
            for s in SEED_AXIS_REQUIREMENTS],
        'note': 'steps/mm DERIVES from the m1-1 arithmetic and '
                'the leadscrew row — never seeded, so it cannot '
                'drift; every prior names the measurement that '
                'retires it'}


def positioning_proof(manager, design_name=M1_DESIGN,
                      commanded_steps=48, load_torque_nm=None,
                      direction=1):
    """Command N steps under the axis load and account for every
    mm. Runs the UNLOADED CONTROL first (exactness is the claim),
    then the axis duty case. A reluctance miss is a backward pole
    SLIP — named per step, and the ledger balances by two paths."""
    try:
        lead = _req(manager, 'axis-leadscrew-lead')
    except ValueError as exc:
        return {'ok': False, 'refusal': str(exc)}
    axis = axis_report(manager, design_name)
    if not axis.get('ok'):
        return axis
    load = (axis['loadTorqueDemandNm'] if load_torque_nm is None
            else float(load_torque_nm))
    mm_per_deg = lead / 360.0

    def ledger(sim):
        pos = sim['positionComparison']
        commanded_mm = pos['expectedRotationDeg'] * mm_per_deg
        actual_mm = pos['actualRotationDeg'] * mm_per_deg
        error_a = commanded_mm - actual_mm
        error_b = sum(h['shortfallDeg'] for h in
                      sim['history'][1:]) * mm_per_deg
        slips = [h['step'] for h in sim['history'][1:]
                 if h.get('advancedDeg', 0) < -0.5 * STEP_DEG]
        return {
            'steps': sim['steps'],
            'stepsTaken': sim['stepsTaken'],
            'stepsMissed': sim['stepsMissed'],
            'slippedSteps': slips,
            'commandedMm': round(commanded_mm, 5),
            'actualMm': round(actual_mm, 5),
            'positionErrorMm': round(error_a, 5),
            'crossCheck': {
                'pathA_finalPositionMm': round(error_a, 5),
                'pathB_sumOfShortfallsMm': round(error_b, 5),
                'consistent': abs(error_a - error_b) < 1e-3,
                'note': 'two paths, one number: the final-'
                        'position delta and the sum of per-step '
                        'named shortfalls must agree — if they '
                        'ever disagree, the ledger has a hole'},
        }

    control = sequence_sim(manager, design_name,
                           steps=int(commanded_steps),
                           load_torque_nm=0.0,
                           direction=direction)
    if not control.get('ok'):
        return control
    duty = sequence_sim(manager, design_name,
                        steps=int(commanded_steps),
                        load_torque_nm=load, direction=direction)
    control_ledger = ledger(control)
    duty_ledger = ledger(duty)
    exact = (control_ledger['stepsMissed'] == 0
             and abs(control_ledger['positionErrorMm']) < 1e-6)
    return {
        'ok': True, 'design': design_name,
        'target': 'wax-3d-printer axis '
                  '(manufacturing-devices tree, powered-by '
                  'electric-motors/m1-switched-reluctance)',
        'mmPerStep': axis['mmPerStep'],
        'loadTorqueNm': load,
        'unloadedControl': {
            **control_ledger,
            'exact': exact,
            'claim': 'zero missed steps -> position error '
                     'EXACTLY zero; anything else is a solver '
                     'bug, not a tolerance'},
        'axisDuty': {
            **duty_ledger,
            'verdict': ('lands-on-position'
                        if duty_ledger['stepsMissed'] == 0
                        else 'loses-position'),
            'slipNote': 'a reluctance miss is not a non-event: '
                        'with no detent the rotor SLIPS BACK a '
                        'pole pitch (loss of synchronism) — the '
                        'weak drive loses MORE than its missed '
                        'steps, and every slip is named above'},
        'dutyVerdict': axis['dutyVerdict'],
        'knobs': axis['knobs'],
        'speedAssumption': duty.get('speedAssumption'),
        'noUnpoweredDetent': duty.get('noUnpoweredDetent'),
        'note': 'the proof this rung exists for: "keeps time" '
                'become "lands on the commanded position" — '
                'exact when nothing misses, every miss a named '
                'mm error, and the verdict names its knob'}


def seed_m1_axis(manager):
    return upsert_seed_pairs(manager, [
        ('PrinterAxisRequirement', PrinterAxisRequirement,
         SEED_AXIS_REQUIREMENTS),
    ], tag='M1AxisSeed')
