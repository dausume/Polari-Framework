"""
@module motors.m1_relations_seed

mq-3: INTER-PART CORRELATIONS AS NO-CODE ROWS — the point of the
whole matrix-shape arc. A relation between two parts is a
MatrixEquationDefinition whose operands REFERENCE the parts' mq-1
surface matrices; the EXISTING matrix_equation_executor evaluates
it. Nothing here re-states a dimension: the numbers come OUT of
the quadrics (a cylinder's Q carries -r² in Q[3,3]; a plane's Q
carries -d), so if a shape row changes, every relation moves with
it and the agreement report catches any drift against the design
row — live, not at seed time.

Seeded relations (each with the fact it must agree with):
- m1-rel-working-gap: tooth arc-face radius minus pole tip radius,
  FROM their matrices == the design row's gap_base_m. The air gap
  as a correlation between two parts' equations.
- m1-rel-coil-clearance: the coil bore's inner rim plane minus the
  pole swing radius — the second designed non-contact interface
  (ifm1-coil-clearance), as algebra.
- m1-rel-tooth-yoke-merge: tooth back-plane distance minus yoke
  bore radius == 0 — the MOLD-FUSED boundary is only real if the
  two castings' surfaces coincide exactly.

Also here, because it is the shape correlation the solver RUNS ON:
arc_overlap_fraction() — the EXACT pole/tooth arc overlap over a
rotor period. cons-3 (2026-08-02) ADOPTED it: m1_sequencing's
co-energy now calls this function, so the overlap profile the
torque comes from and the overlap profile the shapes imply are
ONE object. overlap_model_gap() consequently changed job — it
used to name the deviation of the retired first-harmonic model,
and now GUARDS that the solver still rides the exact arcs (the
harmonic stays in the report as the third column, so what was
retired stays visible).

And the rule the adoption made binding: arc_rule_report() — the
switched-reluctance arc feasibility conditions (beta_s >= the
step angle, beta_r >= beta_s, beta_s + beta_r <= the rotor pole
pitch) checked against the LIVE shape rows. The first of those is
what caught the seeded M1 geometry: a 27.55 deg tooth arc has
literally zero overlap 30 deg away, so the exact model's rotor
felt no torque at the moment each step began (see cons-3 in the
git log — the arcs were widened to 32/36 deg because of this).

Marker positions DERIVE: derived_marker_positions() computes the
scene markers from the same shape parameters, retiring the
"seeded approximations" honesty note in m1_scene.

@consumers motors.motor_api (/api/motors/m1-relations),
motors.m1_scene_seed (marker positions), polariServer seed pass
(seed_m1_relations), selftest_m1
"""

import json
import math

M1_DESIGN = 'reluctance-6s4p-m1'
PROV = 'mq-3'

#: matrix-row names from the mq-1 emission (name-convention link).
_Q_TOOTH_FACE = 'motor-m1-stator-tooth--Q--arc-face'
_Q_TOOTH_BACK = 'motor-m1-stator-tooth--Q--back'
_Q_POLE_TIP = 'motor-m1-rotor-pole--Q--lateral-outer'
_Q_YOKE_BORE = 'motor-m1-yoke-bore--Q--lateral'
_Q_COIL_BORE_RIM = 'motor-m1-coil-bore--Q--cap-base'


def _rel(name, latex, expr, operands, agrees_with, description):
    return {
        'name': name,
        'description': description + ' | AGREES WITH: '
        + agrees_with,
        'latex': latex,
        'operation_json': json.dumps({'kind': 'expr',
                                      'expr': expr}),
        'operands_json': json.dumps(operands),
    }


SEED_M1_RELATIONS = [
    _rel('m1-rel-working-gap',
         r'g = \sqrt{Q_t[3,3]} - \sqrt{-Q_p[3,3]}',
         'np.sqrt(Qt[3, 3]) - np.sqrt(-Qp[3, 3])',
         {'Qt': {'kind': 'matrix', 'ref': _Q_TOOTH_FACE},
          'Qp': {'kind': 'matrix', 'ref': _Q_POLE_TIP}},
         'MotorDesignDefinition.gap_base_m (x1000, mm)',
         'THE AIR GAP as a correlation between two parts\' '
         'equations: the tooth\'s ground arc-face radius (its '
         'bore-side quadric carries +r² in Q[3,3]) minus the '
         'pole tip radius (its lateral quadric carries -r²).'),
    _rel('m1-rel-coil-clearance',
         r'c = Q_c[3,3] - \sqrt{-Q_p[3,3]}',
         'Qc[3, 3] - np.sqrt(-Qp[3, 3])',
         {'Qc': {'kind': 'matrix', 'ref': _Q_COIL_BORE_RIM},
          'Qp': {'kind': 'matrix', 'ref': _Q_POLE_TIP}},
         'ifm1-coil-clearance stays POSITIVE (a rub is a short)',
         'The coil bore\'s inner rim plane (its cap quadric '
         'carries -d, d = the rim\'s distance from the machine '
         'axis) minus the pole swing radius — the second '
         'designed non-contact interface, as algebra.'),
    _rel('m1-rel-tooth-yoke-merge',
         r'\Delta = -Q_b[3,3] - \sqrt{-Q_y[3,3]}',
         '-Qb[3, 3] - np.sqrt(-Qy[3, 3])',
         {'Qb': {'kind': 'matrix', 'ref': _Q_TOOTH_BACK},
          'Qy': {'kind': 'matrix', 'ref': _Q_YOKE_BORE}},
         'ifm1-teeth-yoke: EXACTLY ZERO — a mold-fused boundary '
         'is only real if the surfaces coincide',
         'Tooth back-plane distance minus yoke bore radius: the '
         'one-pour claim, checkable from the two shapes\' own '
         'matrices.'),
]

#: What each relation must equal, resolved LIVE in the report.
_EXPECTATIONS = {
    'm1-rel-working-gap': 'design-gap-mm',
    'm1-rel-coil-clearance': 'positive',
    'm1-rel-tooth-yoke-merge': 'zero',
}


def _shape_params(manager, shape_name):
    table = (getattr(manager, 'objectTables', None)
             or {}).get('MathShapeDefinition', {})
    row = table.get(shape_name) if isinstance(table, dict) \
        else None
    if row is None:
        for r in (table.values()
                  if isinstance(table, dict) else []):
            if getattr(r, 'name', '') == shape_name:
                row = r
                break
    if row is None:
        return None
    try:
        return json.loads(getattr(row, 'parameters_json', '')
                          or '{}')
    except (TypeError, ValueError):
        return None


def relation_report(manager, design_name=M1_DESIGN):
    """Evaluate every seeded relation THROUGH the matrix executor
    (over the mq-1 emitted rows) and judge it against the design
    row / interface expectation — the drift alarm, live."""
    try:
        from matrices.matrix_equation_executor import (
            evaluate_equation,
        )
    except ImportError:
        return {'ok': False,
                'refusal': 'the matrices module (numpy) is not '
                           'importable here — relations evaluate '
                           'in-container'}
    from magnetics.custom.magnet_analysis import _named
    design = _named(manager, 'MotorDesignDefinition', design_name)
    if design is None:
        return {'ok': False,
                'refusal': f'no design "{design_name}"'}
    try:
        gap_mm = json.loads(design.params_json)['gap_base_m'] \
            * 1000.0
    except (TypeError, ValueError, KeyError):
        return {'ok': False,
                'refusal': 'design row carries no gap_base_m'}
    eq_table = (getattr(manager, 'objectTables', None)
                or {}).get('MatrixEquationDefinition', {})
    eq_rows = (list(eq_table.values())
               if isinstance(eq_table, dict) else list(eq_table))
    # live tables key by id, fixtures by name — match on the
    # row's own name either way.
    by_name = {getattr(r, 'name', ''): r for r in eq_rows}
    out = []
    for seed in SEED_M1_RELATIONS:
        row = by_name.get(seed['name'])
        if row is None:
            out.append({'relation': seed['name'], 'ok': False,
                        'refusal': 'relation row not booted '
                                   '(seed_m1_relations delivers '
                                   'it)'})
            continue
        try:
            value = float(evaluate_equation(row, {},
                                            manager=manager))
        except Exception as e:
            out.append({'relation': seed['name'], 'ok': False,
                        'refusal': f'executor: {e}'})
            continue
        expect = _EXPECTATIONS[seed['name']]
        if expect == 'design-gap-mm':
            consistent = abs(value - gap_mm) < 1e-6
            expected = gap_mm
        elif expect == 'zero':
            consistent = abs(value) < 1e-9
            expected = 0.0
        else:
            consistent = value > 0.0
            expected = '> 0'
        out.append({'relation': seed['name'],
                    'ok': True, 'valueMm': value,
                    'expected': expected,
                    'consistent': consistent})
    all_consistent = all(r.get('consistent') for r in out
                         if r.get('ok'))
    return {
        'ok': True, 'design': design_name, 'relations': out,
        'allConsistent': all_consistent,
        'note': 'every value comes OUT of the parts\' emitted '
                'quadrics through the no-code executor — nothing '
                'here re-states a dimension, so drift between a '
                'shape row and the design row cannot hide'}


def arc_overlap_fraction(u_rad, beta_s, beta_r, poles):
    """THE overlap profile, exact: what fraction of the smaller
    arc a rotor pole shares with a stator tooth when the pole
    centre sits u_rad away from the tooth centre. Trapezoidal by
    construction — flat 1.0 while the narrower arc is wholly
    inside the wider one, linear flanks as it slides out, and
    EXACTLY ZERO once they are further apart than (beta_s +
    beta_r)/2. Periodic in the rotor pole pitch 2*pi/poles.

    ONE copy of this logic, called by both the m1-1 solver (the
    torque comes from it) and overlap_model_gap (the report that
    guards it). cons-3 adopted it; before that the solver rode a
    first-harmonic stand-in."""
    period = 2.0 * math.pi / poles
    u = ((u_rad + period / 2.0) % period) - period / 2.0
    lo = max(u - beta_r / 2.0, -beta_s / 2.0)
    hi = min(u + beta_r / 2.0, beta_s / 2.0)
    return max(0.0, hi - lo) / min(beta_s, beta_r)


def _seed_shape_params(shape_name):
    """The same parameters the seed pass delivers — the fallback
    when a caller has no booted shape table (fixtures, in-process
    probes before the seed pass)."""
    from motors.motor_shapes_seed import SEED_M1_PART_SHAPES
    for s in SEED_M1_PART_SHAPES:
        if s.get('name') == shape_name and s.get('parameters_json'):
            return json.loads(s['parameters_json'])
    return None


def shape_arcs(manager=None):
    """(beta_s, beta_r) in radians, OUT of the tooth and pole shape
    rows — live rows when the manager carries them, else the seed
    dicts those rows come from. Nothing here restates an arc: the
    tooth's is the chord/r_face subtense of its ground face, the
    pole's is twice its half-angle."""
    tooth = (_shape_params(manager, 'motor-m1-stator-tooth')
             if manager is not None else None) \
        or _seed_shape_params('motor-m1-stator-tooth')
    pole = (_shape_params(manager, 'motor-m1-rotor-pole')
            if manager is not None else None) \
        or _seed_shape_params('motor-m1-rotor-pole')
    if not tooth or not pole:
        return None
    return {
        'beta_s': 2.0 * math.asin(tooth['width'] / 2.0
                                  / tooth['r_face']),
        'beta_r': math.radians(2.0 * pole['half_angle_deg']),
    }


def arc_rule_report(manager=None, design_name=M1_DESIGN):
    """The switched-reluctance ARC FEASIBILITY RULES, checked
    against the shapes themselves. These only became binding when
    cons-3 adopted the exact overlap: under a first-harmonic
    stand-in every geometry produces torque everywhere, so a
    machine that physically cannot start looks fine.

    1. beta_s >= the step angle 360/(phases*poles). The rotor
       begins each step one step angle away from the tooth about
       to be energised; if the arcs do not still overlap there,
       the torque at the start of the step is ZERO and the step
       never begins. This is the rule the seeded M1 broke
       (27.55 deg tooth arc, 30 deg step) — caught by the model
       change, fixed by widening the arcs.
    2. beta_r >= beta_s — the wider rotor arc gives a flat-topped
       aligned region instead of a single point.
    3. beta_s + beta_r <= 360/poles, the rotor pole pitch, or
       there is no fully-unaligned position and the saliency the
       machine runs on is never realised."""
    arcs = shape_arcs(manager)
    if arcs is None:
        return {'ok': False,
                'refusal': 'M1 tooth/pole shape rows not booted'}
    from magnetics.custom.magnet_analysis import _named
    design = _named(manager, 'MotorDesignDefinition', design_name) \
        if manager is not None else None
    try:
        params = json.loads(design.params_json)
        poles = int(params.get('poles', 4))
        slots = int(params.get('slots', 6))
    except (TypeError, ValueError, AttributeError):
        poles, slots = 4, 6
    phases = slots // 2
    step_deg = 360.0 / (phases * poles)
    pitch_deg = 360.0 / poles
    bs = math.degrees(arcs['beta_s'])
    br = math.degrees(arcs['beta_r'])
    checks = [
        {'rule': 'beta_s >= step angle',
         'valueDeg': round(bs, 3), 'limitDeg': step_deg,
         'holds': bs >= step_deg,
         'why': 'each step starts one step angle away from the '
                'tooth being energised — no overlap there means '
                'no starting torque, so the step never begins'},
        {'rule': 'beta_r >= beta_s',
         'valueDeg': round(br, 3), 'limitDeg': round(bs, 3),
         'holds': br >= bs,
         'why': 'the wider rotor arc gives a flat-topped aligned '
                'region rather than a knife-edge alignment'},
        {'rule': 'beta_s + beta_r <= rotor pole pitch',
         'valueDeg': round(bs + br, 3), 'limitDeg': pitch_deg,
         'holds': (bs + br) <= pitch_deg,
         'why': 'otherwise there is no fully-unaligned position '
                'and the saliency the machine runs on is never '
                'realised'},
    ]
    return {
        'ok': True, 'design': design_name,
        'toothArcDeg': round(bs, 3), 'poleArcDeg': round(br, 3),
        'stepAngleDeg': step_deg, 'rotorPolePitchDeg': pitch_deg,
        'checks': checks,
        'allHold': all(c['holds'] for c in checks),
        'note': 'these are conditions on the SHAPES, read out of '
                'the shape rows — they became checkable (and one '
                'of them, false) only once the solver ran on the '
                'exact arc overlap instead of a smooth stand-in'}


def overlap_model_gap(manager, design_name=M1_DESIGN, points=181):
    """ADOPTED 2026-08-02 (cons-3): the m1-1 solver's overlap IS
    this exact arc overlap, so this report's job changed from
    naming a model gap to GUARDING that adoption — it evaluates
    the solver's own overlap term and the exact arc form and the
    deviation must stay ~0. The retired first-harmonic curve stays
    in the samples as the third column: what the torque numbers
    used to ride on, kept visible rather than deleted."""
    arcs = shape_arcs(manager)
    if arcs is None:
        return {'ok': False,
                'refusal': 'M1 tooth/pole shape rows not booted'}
    from magnetics.custom.magnet_analysis import _named
    design = _named(manager, 'MotorDesignDefinition', design_name)
    try:
        params = json.loads(design.params_json)
        saliency = float(params.get('saliency_ratio', 1.0))
        poles = int(params.get('poles', 4))
    except (TypeError, ValueError, AttributeError):
        return {'ok': False, 'refusal': 'design params unreadable'}
    from motors.custom.m1_sequencing import solver_overlap
    beta_s, beta_r = arcs['beta_s'], arcs['beta_r']
    period = 2.0 * math.pi / poles
    mod_depth = 1.0 - 1.0 / max(saliency, 1.0)
    floor = 1.0 - mod_depth
    rows = []
    worst = 0.0
    worst_harmonic = 0.0
    for i in range(points):
        th = period * i / (points - 1) - period / 2.0
        exact = floor + mod_depth * arc_overlap_fraction(
            th, beta_s, beta_r, poles)
        solver = solver_overlap(manager, th, design_name)
        harmonic = floor + mod_depth * (1.0
                                        + math.cos(poles * th)) \
            / 2.0
        worst = max(worst, abs(exact - solver))
        worst_harmonic = max(worst_harmonic, abs(exact - harmonic))
        if i % 30 == 0:
            rows.append({'thetaDeg': round(math.degrees(th), 1),
                         'exactOverlap': round(exact, 4),
                         'solverOverlap': round(solver, 4),
                         'retiredFirstHarmonic': round(harmonic, 4)})
    return {
        'ok': True, 'design': design_name,
        'toothArcDeg': round(math.degrees(beta_s), 3),
        'poleArcDeg': round(math.degrees(beta_r), 3),
        'samples': rows,
        'worstDeviation': round(worst, 6),
        'adopted': True,
        'retiredModelDeviation': round(worst_harmonic, 4),
        'namedGap': f'ADOPTED 2026-08-02: the m1-1 solver runs on '
                    f'the EXACT arc overlap (deviation '
                    f'{worst:.2e} — this report now guards the '
                    f'adoption instead of naming a gap). The '
                    f'retired first-harmonic stand-in differs '
                    f'from the exact profile by up to '
                    f'{worst_harmonic:.2%} of full modulation, '
                    f'and its smoothness hid a machine that '
                    f'could not start: at the 30 deg step angle '
                    f'the old 27.55 deg tooth arc had zero real '
                    f'overlap. See arc_rule_report.'}


def derived_marker_positions():
    """Scene marker positions DERIVED from the same shape
    parameters the renderer draws — retires the seeded-
    approximation note. Static import-time computation from the
    seed dicts (the same rows the scene renders)."""
    from motors.motor_shapes_seed import SEED_M1_PART_SHAPES
    p = {s['name']: json.loads(s['parameters_json'])
         for s in SEED_M1_PART_SHAPES
         if s.get('parameters_json')}
    tooth = p['motor-m1-stator-tooth']
    pole = p['motor-m1-rotor-pole']
    core = p['motor-m1-rotor-core']
    shaft = p['motor-m1-shaft']
    coil_bore = p['motor-m1-coil-bore']
    z_top = tooth['height'] / 2.0 + 2.0
    gap_r = (tooth['r_face'] + pole['r_outer']) / 2.0
    coil_rim = (coil_bore['center'][0]
                - coil_bore['height'] / 2.0)
    return {
        'ifm1-rotor-shaft': [0.0, 0.0,
                             shaft['height'] / 4.0],
        'ifm1-poles-core': [core['radius'], 0.0, z_top],
        'ifm1-teeth-yoke': [tooth['r_back'], 0.0, z_top],
        'ifm1-working-gap': [gap_r, 0.0, z_top],
        'ifm1-coil-clearance': [(coil_rim + pole['r_outer'])
                                / 2.0, 3.0, z_top],
        'ifm1-winding-tooth': [coil_bore['center'][0], 3.0,
                               z_top],
    }


def seed_m1_relations(manager):
    try:
        from matrices.matrix_equation_definition import (
            MatrixEquationDefinition,
        )
    except ImportError:
        return [{'class': 'MatrixEquationDefinition',
                 'inserted': [], 'updated': [],
                 'errors': ['matrices module not importable']}]
    from composition.custom.seed_upsert import upsert_seed_pairs
    return upsert_seed_pairs(manager, [
        ('MatrixEquationDefinition', MatrixEquationDefinition,
         SEED_M1_RELATIONS),
    ], tag='M1RelationSeed')
