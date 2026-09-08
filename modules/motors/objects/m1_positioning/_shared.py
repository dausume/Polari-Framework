"""@module motors.objects.m1_positioning._shared — what the m1_positioning row classes share (constants, seeds, helpers); split from m1_positioning_basis.py (sap-2c)."""
from motors.custom.m1_sequencing import (
    STEP_DEG, holding_torque, pull_in_load_limit, sequence_sim,
)
import math
from composition.custom.data_refs import rows

M1_DESIGN = 'reluctance-6s4p-m1'
PROV = 'm1-5'
STEPS_PER_REV = int(round(360.0 / STEP_DEG))
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
    pil = pull_in_load_limit(manager, design_name)
    if not pil.get('ok'):
        return pil
    supply_nm = pil['holdingTorqueNm']
    limit_nm = pil['pullInLimitNm']
    # PULL-IN is the duty criterion: a motor that HOLDS a load it
    # cannot STEP under does not position anything (the m1-1
    # finding — the limit is ~0.32x holding on this design).
    capable = limit_nm > demand_nm
    knobs = []
    better = pull_in_load_limit(
        manager, design_name,
        stator_material='opt-galvanized-bio-steel',
        rotor_material='opt-galvanized-bio-steel')
    if better.get('ok'):
        knobs.append({
            'knob': 'bio-steel stator + rotor (the m1-6 fork)',
            'pullInLimitNm': better['pullInLimitNm'],
            'gain': round(better['pullInLimitNm'] / limit_nm, 1)
            if limit_nm else None,
            'closes': better['pullInLimitNm'] > demand_nm,
            'evidence': 'pull-in limit re-solved live with '
                        'opt-galvanized-bio-steel via material '
                        'override — same engine, same geometry'})
    ratio = demand_nm / limit_nm if limit_nm > 0 else None
    if ratio and ratio > 1.0:
        knobs.append({
            'knob': 'gear reduction between motor and screw',
            'requiredRatio': math.ceil(ratio * 1.5),
            'evidence': f'demand/pull-in = {ratio:.0f}x, times '
                        f'the 1.5 drive margin — sized by the '
                        f'PULL-IN limit, never holding torque; '
                        f'the gears module (gr-1) has the train '
                        f'machinery',
            'cost': 'resolution IMPROVES by the same ratio; '
                    'travel speed falls by it — at the ASSUMED '
                    '5 Hz step rate this ratio is honestly very '
                    'slow, and the dynamic model that would '
                    'permit faster stepping is a named gap'})
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
        'pullInLimitNm': limit_nm,
        'dutyVerdict': ('capable' if capable else 'not-capable'),
        'shortfall': (None if capable
                      else round(demand_nm / limit_nm, 1)),
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
        band = sim.get('alignmentBand', {})
        offset_mm = float(band.get('halfBandDeg', 0.0)) * mm_per_deg
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
            'restBandOffsetMm': round(offset_mm, 5),
            'errorBeyondBandMm': round(
                abs(error_a) - offset_mm, 5),
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
    # THE EXACTNESS CLAIM, restated for a machine with a rest
    # band: the error lies inside the band and does not GROW —
    # run the same control at twice the steps and it must not
    # double. (Before cons-3 the claim was a bare zero; the band
    # is real geometry, so the claim now has to survive it.)
    double = sequence_sim(manager, design_name,
                          steps=int(commanded_steps) * 2,
                          load_torque_nm=0.0, direction=direction)
    double_ledger = ledger(double) if double.get('ok') else {}
    exact = (control_ledger['stepsMissed'] == 0
             and control_ledger['errorBeyondBandMm'] <= 0.0)
    accumulates = (
        abs(double_ledger.get('positionErrorMm', 1.0)
            - control_ledger['positionErrorMm']) > 1e-6
        if double_ledger else None)
    band = control.get('alignmentBand', {})
    headline = [
        {'label': 'unloaded control',
         'value': ('exact' if exact else 'NOT exact'),
         'verdict': 'ok' if exact else 'bad',
         'note': f'{control_ledger["stepsMissed"]} missed steps; '
                 f'the whole error sits inside the rest band, '
                 f'and it is the same at twice the distance'},
        {'label': 'rest band (beta_r - beta_s)',
         'value': f'{band.get("bandDeg", 0):.2f} deg',
         'note': 'a flat, zero-torque alignment straight out of '
                 'the two shape rows — rest is a band, not a '
                 'point'},
        {'label': 'reversal backlash it causes',
         'value': f'{control_ledger["restBandOffsetMm"] * 2:.4f} '
                  f'mm',
         'verdict': ('ok' if float(band.get('bandDeg', 0))
                     * mm_per_deg < axis['toleranceMm']
                     else 'warn'),
         'note': f'against the {axis["toleranceMm"]} mm tolerance '
                 f'row — lost motion from geometry, with no gear '
                 f'involved'},
        {'label': 'under the axis duty',
         'value': ('lands' if duty_ledger['stepsMissed'] == 0
                   else 'loses position'),
         'verdict': ('ok' if duty_ledger['stepsMissed'] == 0
                     else 'bad'),
         'note': f'{duty_ledger["stepsMissed"]} missed, '
                 f'{len(duty_ledger["slippedSteps"])} of them '
                 f'backward SLIPS (no detent to catch them)'},
    ]
    return {
        'ok': True, 'design': design_name,
        'headline': headline,
        'target': 'wax-3d-printer axis '
                  '(manufacturing-devices tree, powered-by '
                  'electric-motors/m1-switched-reluctance)',
        'mmPerStep': axis['mmPerStep'],
        'loadTorqueNm': load,
        'unloadedControl': {
            **control_ledger,
            'exact': exact,
            'accumulates': accumulates,
            'atDoubleTheSteps': {
                'steps': double_ledger.get('steps'),
                'positionErrorMm': double_ledger.get(
                    'positionErrorMm')},
            'claim': 'zero missed steps -> every step advances '
                     'exactly one step angle, so the position '
                     'error stays INSIDE the rest band and is '
                     'the same at 2N steps as at N (a one-time '
                     'home offset, not drift). Anything outside '
                     'the band, or any growth with distance, is '
                     'a solver bug rather than a tolerance.'},
        'restBand': {
            **band,
            'offsetMm': control_ledger['restBandOffsetMm'],
            'reversalBacklashMm': round(
                float(band.get('bandDeg', 0.0)) * mm_per_deg, 5),
            'vsToleranceMm': axis['toleranceMm'],
            'insideTolerance': (
                float(band.get('bandDeg', 0.0)) * mm_per_deg
                < axis['toleranceMm']),
            'note': 'the axis inherits the motor\'s zero-torque '
                    'alignment band as LOST MOTION on reversal — '
                    'backlash with no gear involved, straight '
                    'out of beta_r - beta_s. It is a one-way-'
                    'move product unless the ratio or the arcs '
                    'change, and the gear train the m1-6 product '
                    'ships divides this band by its ratio.'},
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
