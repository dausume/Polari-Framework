"""
@module motors.scale_goals_basis

goal-1..3 (MOTOR_GOALS_PLAN): the M0 approach RESTRUCTURED around
GOALS AND CONSTRAINTS. Instead of analysing one fixed movement, a
goal names a TARGET SCALE (wristwatch → desk → wall → large wall →
tower) and a MATERIAL POLICY (locally-made-only / local plus
imported bare wire / anything), and the engine derives what each
known part archetype must deliver — then scores feasibility with
every blocker NAMED.

The physics is the arc's own, reused not restated:
- coil voltage = MMF·ρ·MTL/A_copper — TURNS CANCEL (mag-25), so the
  cell picks the gauge floor at every scale;
- turns = f·W/A_wound — the WINDOW picks the gauge ceiling, because
  battery life needs turns and turns need window;
- the wire LADDER rung follows from the gauge (wire_ladder), and
  the material policy says which rungs we may assume;
- hand imbalance torque m·g·r (eq-hand-imbalance-torque) is what
  scales the MMF prior between scales — stated as a CRUDE scaling,
  never silently.

Scale rows and goal rows are DATA (knobs); scoring weights are on
the goal; the engine only derives, refuses, and suggests.

@consumers motors.motor_api, motors.motors_selftest,
polariServer seed passes (via seed_scale_goals — the arch-1 upsert
path, never the legacy insert-only list)
"""

import math

from objectTreeDecorators import treeObject, treeObjectInit

from composition.custom.data_refs import resolve_named, rows
from composition.design_matrix_basis import matrix_report
from composition.custom.part_roles import role_viability
from composition.custom.seed_upsert import upsert_seed_pairs
from motors.physics_equations_seed import evaluate_named
from motors.custom.simple_first import AWG_MM, ENAMEL_MM, RHO_CU, rung_for

G = 9.80665
HOURS_PER_YEAR = 8766.0
SCRAMBLE_FILL = 0.60

#: Tolerance ladder (mag round-1): what each rung can HOLD. The
#: local ceiling is a GOAL knob, defaulting to T2 — cast, lapped and
#: fired are demonstrated in our stack; machined (T3) is not yet,
#: and watch work (T4) is jewel-grade precision beyond it.
TOLERANCE_RUNGS = ('T0', 'T1', 'T2', 'T3', 'T4')

MATERIAL_POLICIES = ('local-made-only', 'local-plus-imported-wire',
                     'any')


class ClockScaleDefinition(treeObject):
    """One point on the size ladder, with its geometry priors."""

    @treeObjectInit
    def __init__(self, name='', display_name='',
                 movement_diameter_mm=0.0, window_mm2=0.0,
                 mean_turn_mm=14.0, hand_mass_g=0.0, hand_r_mm=0.0,
                 mmf_a_turns=0.0, mmf_provenance='',
                 cell_name='', cell_v=1.5, cell_capacity_mah=0.0,
                 pulse_ms=30.0, rate_hz=1.0,
                 tolerance_rung_required='T2', gear_module_mm=0.5,
                 is_prior=True, provenance_id='', notes='',
                 manager=None):
        self.name = name
        self.display_name = display_name
        self.movement_diameter_mm = movement_diameter_mm
        #: Winding window PRIOR for this scale — the resource
        #: everything else spends.
        self.window_mm2 = window_mm2
        self.mean_turn_mm = mean_turn_mm
        #: The largest hand: its imbalance m·g·r is what the
        #: movement must beat, and what scales the MMF prior.
        self.hand_mass_g = hand_mass_g
        self.hand_r_mm = hand_r_mm
        #: MMF prior with its provenance SPELLED OUT — these are
        #: scaled/literature figures, not measurements.
        self.mmf_a_turns = mmf_a_turns
        self.mmf_provenance = mmf_provenance
        self.cell_name = cell_name
        self.cell_v = cell_v
        self.cell_capacity_mah = cell_capacity_mah
        self.pulse_ms = pulse_ms
        self.rate_hz = rate_hz
        #: Finest tolerance rung any part of this movement needs.
        self.tolerance_rung_required = tolerance_rung_required
        self.gear_module_mm = gear_module_mm
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes


class MotorGoalSpec(treeObject):
    """A goal: scale + material policy + targets + scoring weights.
    All knobs."""

    @treeObjectInit
    def __init__(self, name='', display_name='', scale_ref='',
                 material_policy='local-made-only',
                 battery_life_target_yr=4.0,
                 wire_rung_ceiling='W2', tolerance_ceiling='T2',
                 weights_json='{}', is_prior=True, provenance_id='',
                 notes='', manager=None):
        self.name = name
        self.display_name = display_name
        self.scale_ref = scale_ref
        self.material_policy = (
            material_policy if material_policy in MATERIAL_POLICIES
            else 'local-made-only')
        self.battery_life_target_yr = battery_life_target_yr
        #: The capability rungs this goal is allowed to ASSUME —
        #: W2/T2 is where our stack demonstrably stands (mag-25,
        #: tolerance ladder). Raising them is a decision, not a
        #: default.
        self.wire_rung_ceiling = wire_rung_ceiling
        self.tolerance_ceiling = tolerance_ceiling
        #: {'drive':w,'life':w,'fit':w,'capability':w,'materials':w}
        self.weights_json = weights_json
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes


def hand_imbalance_nm(mass_g, r_mm):
    """eq-hand-imbalance-torque: τ = m·g·r."""
    return (mass_g / 1000.0) * G * (r_mm / 1000.0)


def _rung_leq(a, b, ladder):
    try:
        return ladder.index(a) <= ladder.index(b)
    except ValueError:
        return False


#: The equation rows the sweep binds, in the order the design
#: matrix tunes them. Composition provides the equations; this
#: engine only binds values and follows the derived order.
SWEEP_EQUATIONS = ('eq-coil-voltage-gauge', 'eq-turns-in-window',
                   'eq-average-current', 'eq-battery-life-hours')


def _eval(manager, name, bindings):
    r = evaluate_named(name, bindings, manager=manager)
    if not (r.get('ok') and r['result'].get('success')):
        return None
    return r['result']['result_numeric']


def gauge_sweep(manager, scale):
    """Every gauge in the table, judged at this scale — each figure
    evaluated through the SAME EquationDefinition rows the
    at-coil-winding archetype references (live rows override
    seeds), never a parallel closed form."""
    out = []
    for awg in sorted(AWG_MM):
        a_cu_m2 = math.pi * (AWG_MM[awg] / 2000.0) ** 2
        v = _eval(manager, 'eq-coil-voltage-gauge',
                  {'M': scale.mmf_a_turns, 'q': RHO_CU,
                   'L': scale.mean_turn_mm / 1000.0, 'A': a_cu_m2})
        a_wound = math.pi * ((AWG_MM[awg] + ENAMEL_MM) / 2.0) ** 2
        turns = _eval(manager, 'eq-turns-in-window',
                      {'f': SCRAMBLE_FILL, 'W': scale.window_mm2,
                       'a': a_wound})
        i_avg_ma = life_yr = None
        if turns and turns >= 1:
            i_avg_a = _eval(manager, 'eq-average-current',
                            {'M': scale.mmf_a_turns, 'N': turns,
                             'p': scale.pulse_ms / 1000.0,
                             'r': scale.rate_hz})
            i_avg_ma = i_avg_a * 1000.0 if i_avg_a else None
            hours = (_eval(manager, 'eq-battery-life-hours',
                           {'C': scale.cell_capacity_mah,
                            'I': i_avg_ma})
                     if i_avg_ma else None)
            life_yr = hours / HOURS_PER_YEAR if hours else None
        if v is None or turns is None:
            return {'ok': False,
                    'refusal': 'equation evaluation failed — the '
                               'EquationDefinition rows (or the '
                               'no-code executor) are not '
                               'available, and this engine does '
                               'not carry a fallback closed form '
                               'by design'}
        out.append({
            'awg': awg, 'rung': rung_for(awg),
            'coilVoltageV': round(v, 3),
            'runsOffCell': v <= scale.cell_v,
            'turns': int(turns),
            'iAvgMa': round(i_avg_ma, 5) if i_avg_ma else None,
            'lifeYr': round(life_yr, 2) if life_yr else None,
        })
    return {'ok': True, 'rows': out,
            'equationsUsed': list(SWEEP_EQUATIONS)}


#: The slots every clock movement fills, with the roles each must
#: satisfy — known parts driving what you need. Archetype refs tie
#: back to composition's arch-5 rows.
MOVEMENT_SLOTS = [
    {'slot': 'stator', 'archetype': 'at-bobbin',
     'roles': ['static-structural', 'flux-carrying'],
     'families': ['soft-magnetic']},
    {'slot': 'rotor-magnet', 'archetype': 'at-magnet-rotor',
     'roles': ['moving', 'torque-magnet-active'],
     # Family narrows the CANDIDATE POOL (a mortar is not a magnet
     # and should not appear as an "unassessed rotor"); the roles
     # still do the judging.
     'families': ['hard-magnetic']},
    {'slot': 'coil-conductor', 'archetype': 'at-coil-winding',
     'roles': ['current-carrying'], 'wire_slot': True,
     'families': ['electric-conductor']},
    {'slot': 'pinion', 'archetype': 'at-pinion',
     'roles': ['moving', 'colliding'],
     'families': ['containment-structural']},
]


def _local_options(manager, policy, wire_slot=False):
    """Catalog options this policy may use. 'Locally made' is
    EARNED: a recipe we hold or a thing we have made — never a
    reference row."""
    out = []
    for opt in rows(manager, 'MagneticMaterialOption'):
        if getattr(opt, 'is_reference_only', False):
            continue
        level = getattr(opt, 'realization_level', '')
        local = level in ('recipe-seeded', 'made-and-measured')
        if policy == 'any':
            out.append(opt)
        elif policy == 'local-plus-imported-wire' and (
                local or wire_slot):
            out.append(opt)
        elif policy == 'local-made-only' and local:
            out.append(opt)
    return out


def screen_slot(manager, slot, policy):
    """Viable materials for one movement slot under the policy."""
    viable, unassessed = [], []
    families = slot.get('families')
    for opt in _local_options(manager, policy,
                              wire_slot=slot.get('wire_slot',
                                                 False)):
        if families and getattr(opt, 'family', '') not in families:
            continue
        name = getattr(opt, 'name', '')
        verdict = role_viability(manager, name, slot['roles'])
        if verdict['verdict'] == 'viable':
            viable.append(name)
        elif verdict['verdict'] == 'unassessed':
            unassessed.append(name)
    return {'slot': slot['slot'], 'archetype': slot['archetype'],
            'roles': slot['roles'], 'viable': viable,
            'unassessed': unassessed}


def goal_feasibility(manager, goal_name):
    """THE question: can we build this clock, at this scale, under
    this material policy — and if not, what EXACTLY blocks it."""
    goal, refusal = resolve_named(manager, 'MotorGoalSpec',
                                  goal_name)
    if refusal:
        return {'ok': False, **refusal}
    scale, refusal = resolve_named(manager, 'ClockScaleDefinition',
                                   getattr(goal, 'scale_ref', ''))
    if refusal:
        return {'ok': False, 'goal': goal_name, **refusal}
    blockers = []
    #: Evidence GAPS are not blockers: a gap is "I do not know, and
    #: here is the measurement" — reporting it as a finding is the
    #: failure mode the whole arc guarded against.
    gaps = []
    target_yr = getattr(goal, 'battery_life_target_yr', 4.0)

    # 0. THE TUNING ORDER COMES FROM COMPOSITION: the coil
    #    archetype's design matrix, classified live. This engine
    #    has no order of its own — if the matrix says coupled,
    #    sweeping it blind would be the mag-22 failure shape, so
    #    it refuses instead.
    arch, arch_refusal = resolve_named(
        manager, 'PartArchetypeDefinition', 'at-coil-winding')
    if arch_refusal:
        return {'ok': False, 'goal': goal_name, **arch_refusal}
    matrix = matrix_report(manager,
                           getattr(arch, 'design_matrix_ref', ''))
    if not matrix.get('ok'):
        return {'ok': False, 'goal': goal_name,
                'refusal': f'the coil archetype\'s design matrix '
                           f'does not resolve: '
                           f'{matrix.get("refusal", "")}'}
    if matrix['classification'] == 'coupled':
        return {'ok': False, 'goal': goal_name,
                'refusal': 'the coil design matrix classifies '
                           'COUPLED — no tuning order exists, and '
                           'optimising through a coupled matrix '
                           'silently moves requirements (mag-22). '
                           'Surface the cross-terms first',
                'findings': matrix['findings']}
    tuning_order = matrix['tuningOrder']
    # 1. GAUGE first, per that order: coarsest gauge that the cell
    #    can drive AND whose turns clear the life target in this
    #    window — every figure evaluated through the archetype's
    #    own equation rows.
    swept = gauge_sweep(manager, scale)
    if not swept.get('ok'):
        return {'ok': False, 'goal': goal_name, **swept}
    sweep = swept['rows']
    workable = [r for r in sweep
                if r['runsOffCell'] and r['lifeYr']
                and r['lifeYr'] >= target_yr]
    chosen = workable[0] if workable else None
    if chosen is None:
        drivable = [r for r in sweep if r['runsOffCell']]
        best_life = max((r['lifeYr'] or 0) for r in sweep)
        if not drivable:
            blockers.append(
                f'NO gauge in the table runs off the '
                f'{scale.cell_name} at MMF {scale.mmf_a_turns} — '
                f'every candidate coil needs more than '
                f'{scale.cell_v} V. Voltage falls with COARSER '
                f'wire, and the table floors at 24 AWG: extending '
                f'it downward (W1-easy drawing) is the first fix '
                f'to try, before a converter or a different cell — '
                f'this is a table edge, not a physics wall')
        else:
            blockers.append(
                f'no gauge clears {target_yr} yr on the '
                f'{scale.cell_name} inside {scale.window_mm2} mm² '
                f'(best {best_life} yr) — the window is too small '
                f'for the turns the life target needs. Movements '
                f'at this scale use finer wire than the table '
                f'covers (48-52 AWG with micron-scale enamel, '
                f'beyond even W3) — that capability is exactly '
                f'what the goal\'s policy excludes')
    # 2. CAPABILITY rungs vs the policy ceilings.
    wire_ceiling = getattr(goal, 'wire_rung_ceiling', 'W2')
    tol_ceiling = getattr(goal, 'tolerance_ceiling', 'T2')
    wire_ladder = ('W0', 'W1', 'W2', 'W3')
    if chosen and not _rung_leq(chosen['rung'], wire_ceiling,
                                wire_ladder):
        blockers.append(
            f'the workable gauge ({chosen["awg"]} AWG) sits on '
            f'wire rung {chosen["rung"]}, above this goal\'s '
            f'ceiling {wire_ceiling} — ultrafine drawing (diamond '
            f'dies) is exactly what mag-25 removed from the '
            f'simplest case')
    tol_req = getattr(scale, 'tolerance_rung_required', 'T2')
    if not _rung_leq(tol_req, tol_ceiling, TOLERANCE_RUNGS):
        blockers.append(
            f'this scale needs tolerance rung {tol_req} (gear '
            f'module {scale.gear_module_mm} mm), above the goal '
            f'ceiling {tol_ceiling} — the movement cannot be made '
            f'to size with the processes the policy allows')
    # 3. MATERIALS per slot, under the policy.
    policy = getattr(goal, 'material_policy', 'local-made-only')
    slots = [screen_slot(manager, s, policy)
             for s in MOVEMENT_SLOTS]
    for s in slots:
        if s['viable']:
            continue
        if s['unassessed']:
            gaps.append(
                f'the {s["slot"]} slot has no VIABLE {policy} '
                f'material yet, but {len(s["unassessed"])} '
                f'candidates are merely UNASSESSED '
                f'({", ".join(s["unassessed"][:3])}…) — a '
                f'measurement, not a redesign, decides this slot')
        else:
            blockers.append(
                f'no {policy} material is viable for the '
                f'{s["slot"]} slot (roles {s["roles"]}) and none '
                f'are even unassessed — every candidate FAILS a '
                f'predicate')
    # 3b. The wire itself, under the strict policy: realization
    # level measures EVIDENCE, not localness — copper magnet wire
    # is made-and-measured *as a bought thing*. mag-24's finding
    # stands: insulation goes local (oleoresinous varnish), DRAWING
    # to fine gauge does not, so bare fine wire is the residual
    # import and a strict-local goal must say so.
    if policy == 'local-made-only':
        blockers.append(
            'the coil WIRE is not locally made: drawing to fine '
            'gauge is the wall (mag-24) — local insulation exists '
            '(oleoresinous varnish was "plain enamel" until 1939), '
            'so BARE fine wire is the residual import. Either '
            'accept it (local-plus-imported-wire) or build the '
            'W2 drawing capability (wire-1 strain)')
    # 4. Torque context — the crude scaling, stated.
    tau = hand_imbalance_nm(scale.hand_mass_g, scale.hand_r_mm)
    m0_tau = hand_imbalance_nm(2.0, 60.0)
    # 5. Score: margins, weighted by the goal's knobs.
    import json as _json
    try:
        weights = _json.loads(getattr(goal, 'weights_json', '')
                              or '{}')
    except ValueError:
        weights = {}
    w = {'drive': 1.0, 'life': 1.0, 'fit': 1.0, 'capability': 1.0,
         'materials': 1.0}
    w.update({k: float(v) for k, v in weights.items() if k in w})
    sub = {
        'drive': (1.0 - chosen['coilVoltageV'] / scale.cell_v
                  if chosen else 0.0),
        'life': (min(2.0, chosen['lifeYr'] / target_yr) / 2.0
                 if chosen else 0.0),
        'fit': (min(1.0, chosen['turns'] / 1500.0)
                if chosen else 0.0),
        'capability': 1.0 if not any('rung' in b for b in blockers)
        else 0.0,
        'materials': (sum(1 for s in slots if s['viable'])
                      / len(slots)),
    }
    total_w = sum(w.values()) or 1.0
    score = round(sum(sub[k] * w[k] for k in sub) / total_w, 3)
    # 6. Requirements per KNOWN PART (archetype) — what you need.
    requirements = []
    for s in slots:
        req = {'archetype': s['archetype'], 'slot': s['slot'],
               'roles': s['roles'],
               'materialCandidates': s['viable'],
               'unassessed': s['unassessed']}
        if s['slot'] == 'coil-conductor' and chosen:
            req['demands'] = {
                'gauge_awg': chosen['awg'],
                'turns': chosen['turns'],
                'wire_rung': chosen['rung'],
                'coil_voltage_v': chosen['coilVoltageV'],
                'note': 'coarsest workable gauge, per the M0 '
                        'design-matrix tuning order '
                        '(gauge → window → turns)'}
        if s['slot'] == 'stator':
            req['demands'] = {
                'window_mm2': scale.window_mm2,
                'tolerance_rung': tol_req}
        if s['slot'] == 'pinion':
            req['demands'] = {
                'gear_module_mm': scale.gear_module_mm,
                'tolerance_rung': tol_req}
        if s['slot'] == 'rotor-magnet':
            req['demands'] = {
                'note': 'run the RATIO, not the numerator: a '
                        'stronger magnet raises the detent it must '
                        'itself overcome (dm-lavet-magnet '
                        'ratio-trap)'}
        requirements.append(req)
    verdict = ('blocked' if blockers else
               'unassessed' if gaps else 'feasible')
    return {
        'ok': True, 'goal': goal_name,
        'scale': getattr(scale, 'name', ''),
        'displayName': getattr(scale, 'display_name', ''),
        'materialPolicy': policy,
        'verdict': verdict,
        'score': score, 'subscores': {k: round(v, 3)
                                      for k, v in sub.items()},
        'weights': w,
        'blockers': blockers,
        'gaps': gaps,
        'tuningOrder': tuning_order,
        'matrixClassification': matrix['classification'],
        'equationsUsed': swept['equationsUsed'],
        'chosenDesignPoint': chosen,
        'gaugeSweep': sweep,
        'handImbalanceNm': round(tau, 6),
        'mmfPrior': {'aTurns': scale.mmf_a_turns,
                     'provenance': scale.mmf_provenance,
                     'crudeScalingNote':
                         f'hand imbalance here is {tau / m0_tau:.2g}'
                         f'× the M0\'s — the MMF prior should '
                         f'scale roughly with it, and this is a '
                         f'PRIOR, not a solved magnetic circuit'},
        'requirements': requirements,
        'honesty': 'scores rank options; blockers decide. A high '
                   'score with a blocker is still blocked, and an '
                   'unassessed material is a measurement away from '
                   'changing this answer — never assumed either '
                   'way.',
    }


def scale_study(manager, policy='local-made-only'):
    """Every seeded scale under one policy — the what-is-possible
    sweep."""
    out = []
    for scale in sorted(rows(manager, 'ClockScaleDefinition'),
                        key=lambda s: getattr(
                            s, 'movement_diameter_mm', 0)):
        goal_like = [g for g in rows(manager, 'MotorGoalSpec')
                     if getattr(g, 'scale_ref', '')
                     == getattr(scale, 'name', '')
                     and getattr(g, 'material_policy', '')
                     == policy]
        if goal_like:
            out.append(goal_feasibility(
                manager, getattr(goal_like[0], 'name', '')))
    return {'ok': True, 'policy': policy, 'scales': out,
            'summary': [{'scale': r['scale'],
                         'verdict': r['verdict'],
                         'score': r['score'],
                         'blockerCount': len(r['blockers']),
                         'gapCount': len(r.get('gaps', []))}
                        for r in out if r.get('ok')]}


# ---------------------------------------------------------------
# Seeds — priors with their provenance spelled out
# ---------------------------------------------------------------

PROV = 'goal-1'

SEED_CLOCK_SCALES = [
    {'name': 'sc-wristwatch', 'display_name': 'Wristwatch movement',
     'movement_diameter_mm': 26.0, 'window_mm2': 3.0,
     'mean_turn_mm': 5.0, 'hand_mass_g': 0.05, 'hand_r_mm': 12.0,
     'mmf_a_turns': 2.5,
     'mmf_provenance': 'literature order for a quartz watch '
                       'stepper (~0.25 mA pulse × ~10k turns)',
     'cell_name': 'SR626 silver-oxide', 'cell_v': 1.55,
     'cell_capacity_mah': 28.0, 'pulse_ms': 7.8, 'rate_hz': 1.0,
     'tolerance_rung_required': 'T4', 'gear_module_mm': 0.07,
     'is_prior': True, 'provenance_id': PROV,
     'notes': 'the hard case on purpose: a 3 mm² window and '
              'module-0.07 gears are jewel-grade work.'},
    {'name': 'sc-desk-clock', 'display_name': 'Desk / alarm clock',
     'movement_diameter_mm': 40.0, 'window_mm2': 150.0,
     'mean_turn_mm': 10.0, 'hand_mass_g': 0.5, 'hand_r_mm': 35.0,
     'mmf_a_turns': 8.0,
     'mmf_provenance': 'scaled from M0 by hand-imbalance ratio, '
                       'CRUDE (same circuit topology assumed)',
     'cell_name': 'one AA cell', 'cell_v': 1.5,
     'cell_capacity_mah': 2500.0, 'pulse_ms': 30.0, 'rate_hz': 1.0,
     'tolerance_rung_required': 'T2', 'gear_module_mm': 0.3,
     'is_prior': True, 'provenance_id': PROV, 'notes': ''},
    {'name': 'sc-wall-clock',
     'display_name': 'Wall clock (the proven M0)',
     'movement_diameter_mm': 55.0, 'window_mm2': 606.0,
     'mean_turn_mm': 14.0, 'hand_mass_g': 2.0, 'hand_r_mm': 60.0,
     'mmf_a_turns': 21.45,
     'mmf_provenance': 'the M0 datum (mag-22/25) — the one scale '
                       'with a live-verified control case',
     'cell_name': 'one AA cell', 'cell_v': 1.5,
     'cell_capacity_mah': 2500.0, 'pulse_ms': 30.0, 'rate_hz': 1.0,
     'tolerance_rung_required': 'T2', 'gear_module_mm': 0.5,
     'is_prior': True, 'provenance_id': PROV, 'notes': ''},
    {'name': 'sc-large-wall',
     'display_name': 'Large wall / station clock (60 cm dial)',
     'movement_diameter_mm': 120.0, 'window_mm2': 2500.0,
     'mean_turn_mm': 25.0, 'hand_mass_g': 15.0, 'hand_r_mm': 200.0,
     'mmf_a_turns': 60.0,
     'mmf_provenance': 'scaled from M0 by hand-imbalance ratio, '
                       'CRUDE',
     'cell_name': 'one D cell', 'cell_v': 1.5,
     'cell_capacity_mah': 12000.0, 'pulse_ms': 60.0, 'rate_hz': 1.0,
     'tolerance_rung_required': 'T1', 'gear_module_mm': 1.0,
     'is_prior': True, 'provenance_id': PROV,
     'notes': 'tolerances RELAX with size — the local-production '
              'story improves as the clock grows.'},
    {'name': 'sc-tower-clock',
     'display_name': 'Tower clock (2 m dial)',
     'movement_diameter_mm': 400.0, 'window_mm2': 40000.0,
     'mean_turn_mm': 80.0, 'hand_mass_g': 2000.0,
     'hand_r_mm': 900.0, 'mmf_a_turns': 400.0,
     'mmf_provenance': 'scaled from M0 by hand-imbalance ratio, '
                       'VERY crude at this extrapolation',
     'cell_name': 'one D cell', 'cell_v': 1.5,
     'cell_capacity_mah': 12000.0, 'pulse_ms': 120.0,
     'rate_hz': 0.0333,
     'tolerance_rung_required': 'T0', 'gear_module_mm': 3.0,
     'is_prior': True, 'provenance_id': PROV,
     'notes': 'a battery is the wrong drive up here — if the life '
              'check fails, weight drive or mains is the '
              'suggestion, and historically was the answer.'},
]

_WEIGHTS = '{"drive": 1.0, "life": 1.5, "fit": 0.5, ' \
           '"capability": 2.0, "materials": 2.0}'

SEED_MOTOR_GOALS = [
    {'name': 'goal-local-watch',
     'display_name': 'A locally made wristwatch',
     'scale_ref': 'sc-wristwatch',
     'material_policy': 'local-plus-imported-wire',
     'battery_life_target_yr': 1.0, 'wire_rung_ceiling': 'W2',
     'tolerance_ceiling': 'T2', 'weights_json': _WEIGHTS,
     'is_prior': True, 'provenance_id': PROV,
     'notes': 'expected BLOCKED — the point is that the blockers '
              'come out NAMED: W3 wire, T4 tolerance.'},
    {'name': 'goal-local-desk-clock',
     'display_name': 'A locally made desk clock',
     'scale_ref': 'sc-desk-clock',
     'material_policy': 'local-plus-imported-wire',
     'battery_life_target_yr': 2.0, 'wire_rung_ceiling': 'W2',
     'tolerance_ceiling': 'T2', 'weights_json': _WEIGHTS,
     'is_prior': True, 'provenance_id': PROV, 'notes': ''},
    {'name': 'goal-local-wall-clock',
     'display_name': 'The locally made wall clock (M0)',
     'scale_ref': 'sc-wall-clock',
     'material_policy': 'local-plus-imported-wire',
     'battery_life_target_yr': 4.0, 'wire_rung_ceiling': 'W2',
     'tolerance_ceiling': 'T2', 'weights_json': _WEIGHTS,
     'is_prior': True, 'provenance_id': PROV,
     'notes': 'the control case: this one must come out FEASIBLE '
              'or the engine is wrong.'},
    {'name': 'goal-local-large-wall',
     'display_name': 'A locally made station clock',
     'scale_ref': 'sc-large-wall',
     'material_policy': 'local-plus-imported-wire',
     'battery_life_target_yr': 2.0, 'wire_rung_ceiling': 'W2',
     'tolerance_ceiling': 'T2', 'weights_json': _WEIGHTS,
     'is_prior': True, 'provenance_id': PROV, 'notes': ''},
    {'name': 'goal-local-tower',
     'display_name': 'A locally made tower clock',
     'scale_ref': 'sc-tower-clock',
     'material_policy': 'local-plus-imported-wire',
     'battery_life_target_yr': 1.0, 'wire_rung_ceiling': 'W2',
     'tolerance_ceiling': 'T2', 'weights_json': _WEIGHTS,
     'is_prior': True, 'provenance_id': PROV, 'notes': ''},
    {'name': 'goal-strict-local-wall-clock',
     'display_name': 'Wall clock, NO imported wire',
     'scale_ref': 'sc-wall-clock',
     'material_policy': 'local-made-only',
     'battery_life_target_yr': 4.0, 'wire_rung_ceiling': 'W2',
     'tolerance_ceiling': 'T2', 'weights_json': _WEIGHTS,
     'is_prior': True, 'provenance_id': PROV,
     'notes': 'the mag-24 honesty case: insulation goes local, '
              'drawing does not — bare fine wire is the import.'},
]


def seed_scale_goals(manager):
    """Through the arch-1 upsert path — changed priors reach live
    rows."""
    return upsert_seed_pairs(manager, [
        ('ClockScaleDefinition', ClockScaleDefinition,
         SEED_CLOCK_SCALES),
        ('MotorGoalSpec', MotorGoalSpec, SEED_MOTOR_GOALS),
    ], tag='ScaleGoalsSeed')
