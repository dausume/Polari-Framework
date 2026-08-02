"""
@module motors.m1_relations

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

Also here, because it is a shape correlation the solver ASSUMES:
overlap_model_gap() — the EXACT pole/tooth arc overlap over a
rotor period versus the first-harmonic modulation m1_sequencing
uses. The difference is THE named model gap, now with a number on
it; the solver's model is not changed by this (deliberate — see
the plan's honesty ledger).

Marker positions DERIVE: derived_marker_positions() computes the
scene markers from the same shape parameters, retiring the
"seeded approximations" honesty note in m1_scene.

@consumers motors.motor_api (/api/motors/m1-relations),
motors.m1_scene (marker positions), polariServer seed pass
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
    from magnetics.magnet_analysis import _named
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


def overlap_model_gap(manager, design_name=M1_DESIGN, points=181):
    """EXACT pole/tooth arc overlap over one rotor-pole period vs
    the first-harmonic modulation the m1-1 solver uses — the named
    model gap, with a number. The solver is NOT changed by this
    (deliberate; model changes are decisions, not side effects)."""
    tooth = _shape_params(manager, 'motor-m1-stator-tooth')
    pole = _shape_params(manager, 'motor-m1-rotor-pole')
    if not tooth or not pole:
        return {'ok': False,
                'refusal': 'M1 tooth/pole shape rows not booted'}
    from magnetics.magnet_analysis import _named
    design = _named(manager, 'MotorDesignDefinition', design_name)
    try:
        params = json.loads(design.params_json)
        saliency = float(params.get('saliency_ratio', 1.0))
        poles = int(params.get('poles', 4))
    except (TypeError, ValueError, AttributeError):
        return {'ok': False, 'refusal': 'design params unreadable'}
    beta_s = 2.0 * math.asin(tooth['width'] / 2.0
                             / tooth['r_face'])
    beta_r = math.radians(2.0 * pole['half_angle_deg'])
    period = 2.0 * math.pi / poles
    mod_depth = 1.0 - 1.0 / max(saliency, 1.0)
    floor = 1.0 - mod_depth
    rows = []
    worst = 0.0
    for i in range(points):
        th = period * i / (points - 1) - period / 2.0
        lo = max(th - beta_r / 2.0, -beta_s / 2.0)
        hi = min(th + beta_r / 2.0, beta_s / 2.0)
        exact_frac = max(0.0, hi - lo) / min(beta_s, beta_r)
        exact = floor + mod_depth * exact_frac
        harmonic = floor + mod_depth * (1.0
                                        + math.cos(poles * th)) \
            / 2.0
        dev = abs(exact - harmonic)
        worst = max(worst, dev)
        if i % 30 == 0:
            rows.append({'thetaDeg': round(math.degrees(th), 1),
                         'exactOverlap': round(exact, 4),
                         'firstHarmonic': round(harmonic, 4)})
    return {
        'ok': True, 'design': design_name,
        'toothArcDeg': round(math.degrees(beta_s), 3),
        'poleArcDeg': round(math.degrees(beta_r), 3),
        'samples': rows,
        'worstDeviation': round(worst, 4),
        'namedGap': f'the m1-1 solver\'s first-harmonic overlap '
                    f'differs from the EXACT arc overlap by up '
                    f'to {worst:.2%} of full modulation — the '
                    f'real profile is trapezoidal (flat top '
                    f'while arcs fully overlap, linear flanks). '
                    f'A quantified prior on every torque number; '
                    f'replacing the model is a decision, not a '
                    f'side effect of this report.'}


def derived_marker_positions():
    """Scene marker positions DERIVED from the same shape
    parameters the renderer draws — retires the seeded-
    approximation note. Static import-time computation from the
    seed dicts (the same rows the scene renders)."""
    from motors.motor_shapes import SEED_M1_PART_SHAPES
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
    from composition.seed_upsert import upsert_seed_pairs
    return upsert_seed_pairs(manager, [
        ('MatrixEquationDefinition', MatrixEquationDefinition,
         SEED_M1_RELATIONS),
    ], tag='M1RelationSeed')
