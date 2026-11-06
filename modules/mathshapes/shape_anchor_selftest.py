"""
@module mathshapes.shape_anchor_selftest

ms-anchor selftests (MECH_FREECAD_INTERCHANGE_PLAN §8.5). Everything
asserted here is HAND-COMPUTED first:

  unit sphere x²+y²+z² = 1, ray (0, 0, 3) → −z: F(s) = (3−s)² − 1
    crosses at s = 2 → p₀ = (0, 0, 1); ∇F = 2p = (0, 0, 2) → n = +z.
  box [-1,3]×[-1,1]×[-1,1] (size 4,2,2 centre (1,0,0)), oblique ray
    from (6, 0, 3) along (−1, 0, −1)/√2: the +x face x = 3 is met at
    s = 3√2 → p₀ = (3, 0, 0), n = +x; −d = (1, 0, 1)/√2, its part in
    the face plane is (0, 0, 1)/√2 → t₁ = +z. So the four references
    are a = +x, −x, +z, −z; for toward: b = t₁ = +z (n × a = 0),
    c = a × b = (+x) × (+z) = −y.
  square pad side 2, t = 0.5, toward, on that face: the pad is
    3 ≤ x ≤ 3.5, |z| ≤ 1 (u along b = +z), |y| ≤ 1 (v along c = −y);
    box ∪ pad = 16 + 2·2·0.5 = 18 cm³, EXACT on a grid whose cells
    align with x = 3 and 3.5 (bounds [-1, 3.5] in 36 cells of 0.125).
  disk pad R = 0.5, t = 2 on the same face: 16 + π·0.25·2 = 17.5708.
  conform on the unit sphere by t = 0.5: |p| < 1.5 exactly
    ((|p| − t)² − 1 < 0) — exact; on the 2×1×1 ellipsoid: approx.
  thread on eq-cyl (r 3, h 4, z ∈ [−2, 2]), anchor on the top cap
    looking down the axis, 'away' → w = 2 − z: P = 0.8, h = 0.2
    (half-width → ridge = P/2 per pitch), band r = 2 .. 2.4, w ∈ [0, 4]:
    at θ = 0 the ridge is where frac(w/P) ∈ (0.25, 0.75) → 5 ridges
    centred at w = 0.4, 1.2, 2.0, 2.8, 3.6 (= 4/0.8 turns); at
    θ = π the ridge is shifted by P/2 (centre w = 0.8, not 0.4).
    Subtracting it from the solid cylinder removes about half of the
    band's volume π(2.4² − 2²)·4 = 22.1 → ~11 cm³ (grid, loose).

Run from polari-framework/:
  PYTHONPATH=.:modules python3 -m mathshapes.shape_anchor_selftest
"""

import json
import math
import types

from mathshapes.custom.shape_anchor import (
    anchor_frame, anchor_payload, evaluate_offset, local_coords,
    offset_equation_rows, offset_field, pick_anchor, result_shape_rows,
    sample_offset,
)
from mathshapes.custom.shape_equations import (
    eval_field_expr, field_value, finite_difference_gradient,
    gradient_rows, gradient_value, rewrite_field_functions,
)
from mathshapes.shape_anchor_seed import (
    SEED_ANCHORED_OFFSETS, SEED_SHAPE_ANCHOR_ANALYSES,
    SEED_SHAPE_ANCHOR_SOLUTIONS, SEED_SHAPE_ANCHORS, THREAD_EXPR,
)
from mathshapes.shape_seed import SEED_MATH_SHAPES

PASS = '\033[92mPASS\033[0m'
FAIL = '\033[91mFAIL\033[0m'
_results = []


def check(label, cond, extra=''):
    _results.append(bool(cond))
    print(f'{PASS if cond else FAIL}: {label}'
          + (f'  [{extra}]' if extra and not cond else ''))


def _close(a, b, tol=1e-9):
    return all(abs(float(x) - float(y)) <= tol for x, y in zip(a, b))


_SHAPE_BASE = {'name': '', 'family': 'primitive', 'primitive_kind': '',
               'parameters_json': '{}', 'quadric_matrix_json': '',
               'csg_json': '', 'bounds_json': ''}


def _shape(**kw):
    return types.SimpleNamespace(**{**_SHAPE_BASE, **kw})


SHAPES = [
    _shape(name='eq-sphere', family='quadric',
           quadric_matrix_json=json.dumps(
               [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, -1]),
           bounds_json=json.dumps([[-1, 1], [-1, 1], [-1, 1]])),
    _shape(name='eq-ellipsoid', family='quadric',
           quadric_matrix_json=json.dumps(
               [0.25, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, -1]),
           bounds_json=json.dumps([[-2, 2], [-1, 1], [-1, 1]])),
    _shape(name='eq-box', primitive_kind='box',
           parameters_json=json.dumps({'size': [4.0, 2.0, 2.0],
                                       'center': [1.0, 0.0, 0.0]})),
    _shape(name='eq-cyl', primitive_kind='cylinder',
           parameters_json=json.dumps({'radius': 3.0, 'height': 4.0,
                                       'axis': 'z',
                                       'center': [0.0, 0.0, 0.0]})),
    _shape(name='eq-mesh', family='mesh'),
]


def _mgr(shapes, anchors=(), offsets=()):
    return types.SimpleNamespace(objectTables={
        'MathShapeDefinition': {s.name: s for s in shapes},
        'ShapeAnchor': {a.name: a for a in anchors},
        'AnchoredOffset': {o.name: o for o in offsets},
    })


def _row(d):
    return types.SimpleNamespace(**d)


def _anchor(name, shape, origin, direction, reference):
    pick = pick_anchor(mgr, shape, origin, direction)
    assert pick.get('ok'), pick
    return _row(anchor_payload(pick, name, shape, reference)), pick


def _offset(name, anchor, mode, t, op, extent=None, offset_eq='',
            expr='', knobs=None):
    return _row({
        'name': name, 'anchor_ref': anchor, 'mode': mode, 't': t,
        'offset_eq': offset_eq,
        'extent_json': json.dumps(extent or {}),
        'surface_eq_ref': '',
        'surface_eq_json': json.dumps({'expr': expr, 'operands': {}})
        if expr else '',
        'parameters_json': json.dumps(knobs or {}), 'op': op,
        'result_shape_ref': '', 'approx_reason': ''})


mgr = _mgr(SHAPES)

print('== suite: ms-anchor executor additions ==')
e = rewrite_field_functions('lmax(abs(frac(x) - 0.5) - 0.25, '
                            'atan2(y, x), mod(x, 3)) + pi')
check('friendly spelling rewrites to the executor\'s numpy spelling',
      e == 'np.max(np.stack([np.abs(np.mod(x, 1.0) - 0.5) - 0.25, '
           'np.arctan2(y, x), np.mod(x, 3)])) + np.pi', e)
check('pure-python leg: atan2(1,0)=π/2, frac(−0.25)=0.75, '
      'mod(−1,3)=2, lmin/lmax over a list',
      abs(eval_field_expr(rewrite_field_functions('atan2(1, 0)'), {})
          - math.pi / 2) < 1e-12
      and abs(eval_field_expr(rewrite_field_functions('frac(-0.25)'),
                              {}) - 0.75) < 1e-12
      and abs(eval_field_expr(rewrite_field_functions('mod(-1, 3)'),
                              {}) - 2.0) < 1e-12
      and eval_field_expr(rewrite_field_functions('lmin(3, 1, 2)'),
                          {}) == 1.0
      and eval_field_expr(rewrite_field_functions('lmax(3, 1, 2)'),
                          {}) == 3.0)
g = gradient_value(mgr, 'eq-sphere', 0.0, 0.0, 1.0)
check('∇F operand: the unit sphere\'s gradient at (0,0,1) is 2p = '
      '(0,0,2), exact', g.get('ok') and _close(g['gradient'], [0, 0, 2]))
g_box = gradient_value(mgr, 'eq-box', 2.9, 0.1, 0.2)
check('∇F of a box near its +x face is the ACTIVE plane\'s normal '
      '(1,0,0)', _close(g_box['gradient'], [1, 0, 0]))
grows = gradient_rows(mgr, 'eq-box')
check('gradient_rows emits one --grad-- row per surface and ONE '
      '<shape>--grad selecting the active branch by np.argmax',
      grows.get('ok')
      and grows['equationRefs']['gradient'] == 'eq-box--grad'
      and sum(1 for r in grows['equationRows']
              if '--grad--' in r['name']) == 6
      and 'argmax' in grows['equationRows'][-1]['operation_json'])
check('mesh family refuses the gradient as a named absence',
      not gradient_value(mgr, 'eq-mesh', 0, 0, 0).get('ok'))

print('== suite: ms-anchor step 1 — pick by ray ==')
pick = pick_anchor(mgr, 'eq-sphere', [0, 0, 3], [0, 0, -1])
check('ray (0,0,3) → −z onto the unit sphere picks p₀ = (0,0,1) and '
      'n = +z, basis exact, normal row named',
      pick.get('ok') and _close(pick['hit'], [0, 0, 1], 1e-9)
      and _close(pick['normal'], [0, 0, 1], 1e-9)
      and pick['basis'] == 'exact'
      and pick['normalEqRef'] == 'eq-sphere--grad',
      json.dumps(pick)[:200])
fd = finite_difference_gradient(
    lambda x, y, z: field_value(mgr, 'eq-sphere', x, y, z)['value'],
    *pick['hit'])
check('finite-difference normal agrees with the exact 2Qp to 1e-6',
      _close(fd, [0, 0, 2], 1e-6))
check('a ray that misses refuses, naming the march step',
      not pick_anchor(mgr, 'eq-sphere', [0, 5, 3], [0, 0, -1]).get('ok')
      and 'step' in pick_anchor(mgr, 'eq-sphere', [0, 5, 3],
                                [0, 0, -1])['refusal'])
check('a shape with no field refuses the pick by name',
      'field' in pick_anchor(mgr, 'eq-mesh', [0, 0, 3],
                             [0, 0, -1]).get('refusal', ''))
check('an unnormalised ray direction is normalised; zero refuses',
      _close(pick_anchor(mgr, 'eq-sphere', [0, 0, 3],
                         [0, 0, -7])['hit'], [0, 0, 1], 1e-9)
      and not pick_anchor(mgr, 'eq-sphere', [0, 0, 3],
                          [0, 0, 0]).get('ok'))

print('== suite: ms-anchor step 2 — the four-way toggle ==')
s2 = math.sqrt(2.0)
obl = pick_anchor(mgr, 'eq-box', [6, 0, 3], [-1 / s2, 0, -1 / s2])
check('oblique ray onto the box +x face hits (3,0,0) with n = +x',
      obl.get('ok') and _close(obl['hit'], [3, 0, 0], 1e-9)
      and _close(obl['normal'], [1, 0, 0]))
frames = {m: anchor_frame(obl, m) for m in
          ('toward', 'away', 'tangent_toward', 'tangent_away')}
check('toward → a = +x ; away → a = −x',
      _close(frames['toward']['a'], [1, 0, 0])
      and _close(frames['away']['a'], [-1, 0, 0]))
check('tangent_toward → a = +z (the viewer direction projected onto '
      'the face) ; tangent_away → a = −z',
      _close(frames['tangent_toward']['a'], [0, 0, 1])
      and _close(frames['tangent_away']['a'], [0, 0, -1]))
check('every frame is right-handed and orthonormal',
      all(abs(sum(f['a'][i] * (f['b'][(i + 1) % 3] * f['c'][(i + 2) % 3]
                               - f['b'][(i + 2) % 3] * f['c'][(i + 1) % 3])
                  for i in range(3)) - 1.0) < 1e-9
          for f in frames.values()))
check('toward frame: b = t₁ = +z, c = a × b = −y, and (u,v,w) of '
      '(3.5, −0.25, 0.75) is (0.75, 0.25, 0.5) — w along a',
      _close(frames['toward']['b'], [0, 0, 1])
      and _close(frames['toward']['c'], [0, -1, 0])
      and _close(local_coords(frames['toward'], 3.5, -0.25, 0.75),
                 [0.75, 0.25, 0.5]))
check('the frame records the tangent assumption for Dustin',
      'awaiting' in frames['toward']['assumption'])
check('an unknown reference refuses',
      not anchor_frame(obl, 'sideways').get('ok'))
axial = pick_anchor(mgr, 'eq-cyl', [0, 0, 10], [0, 0, -1])
check('ray along the normal: frame flags that no "most toward" '
      'tangent exists', 'arbitrary' in anchor_frame(axial, 'away')['note'])

print('== suite: ms-anchor step 3 — planar offsets on a box face ==')
a_tow, _ = _anchor('box-face-toward', 'eq-box', [6, 0, 3],
                   [-1 / s2, 0, -1 / s2], 'toward')
pad = _offset('pad', 'box-face-toward', 'planar_square', 0.5, 'add',
              extent={'side': 2.0})
disk = _offset('disk', 'box-face-toward', 'planar_disk', 2.0, 'add',
               extent={'radius': 0.5})
pocket = _offset('pocket', 'box-face-toward', 'planar_square', -0.5,
                 'subtract', extent={'side': 2.0})
mgr = _mgr(SHAPES, [a_tow], [pad, disk, pocket])
ev = {p: evaluate_offset(mgr, 'pad', *p) for p in
      ((3.25, 0, 0), (3.75, 0, 0), (3.25, 0, 1.5), (3.25, 0.9, 0.9),
       (2.9, 0, 0))}
check('square pad side 2, t 0.5: (3.25,0,0) inside; (3.75,0,0) past '
      'the offset plane; (3.25,0,1.5) past the side; (3.25,.9,.9) '
      'inside; (2.9,0,0) is parent-only',
      ev[(3.25, 0, 0)]['insideOffset']
      and not ev[(3.75, 0, 0)]['insideOffset']
      and not ev[(3.25, 0, 1.5)]['insideOffset']
      and ev[(3.25, 0.9, 0.9)]['insideOffset']
      and not ev[(2.9, 0, 0)]['insideOffset']
      and ev[(2.9, 0, 0)]['insideParent'])
check('composed add: the pad point is inside the RESULT, the '
      'parent-only point too, the far point not',
      ev[(3.25, 0, 0)]['insideResult'] and ev[(2.9, 0, 0)]['insideResult']
      and not ev[(3.75, 0, 0)]['insideResult'])
rs = result_shape_rows(mgr, 'pad', persist=True)
from mathshapes.custom.shape_analysis import shape_properties   # noqa: E402
vol = shape_properties(mgr, 'pad--result', resolution=36)
check('the pad\'s result rides the EXISTING csg path: 6 world-frame '
      'quadric rows + solid + result; grid volume = 16 + 2 = 18 '
      'EXACTLY (cells align with the planes)',
      rs.get('ok') and len(rs['surfaceShapes']) == 6
      and vol.get('ok') and abs(vol['volumeCm3'] - 18.0) < 1e-9,
      json.dumps(vol)[:200])
sd = sample_offset(mgr, 'disk', resolution=40)
check('disk pad R 0.5, t 2: sampled result volume ≈ 16 + π·0.25·2 '
      '= 17.571 within 3 %',
      sd.get('ok') and abs(sd['resultVolume'] - (16 + math.pi * 0.5))
      / (16 + math.pi * 0.5) < 0.03, json.dumps(sd)[:200])
pk = evaluate_offset(mgr, 'pocket', 2.75, 0, 0)
check('pocket (t = −0.5, subtract): a point 0.25 under the face is '
      'inside the pocket solid and OUT of the result',
      pk['insideOffset'] and pk['insideParent'] and not pk['insideResult'])

print('== suite: ms-anchor step 3 — conform ==')
a_sph, _ = _anchor('sphere-top', 'eq-sphere', [0, 0, 3], [0, 0, -1],
                   'toward')
a_ell, _ = _anchor('ell-top', 'eq-ellipsoid', [0, 0, 3], [0, 0, -1],
                   'toward')
conf = _offset('shell', 'sphere-top', 'conform', 0.5, 'add')
conf_e = _offset('shell-e', 'ell-top', 'conform', 0.5, 'add')
mgr = _mgr(SHAPES, [a_sph, a_ell], [conf, conf_e])
c_in = evaluate_offset(mgr, 'shell', 0.8, 0.8, 0.8)      # |p| = 1.386
c_out = evaluate_offset(mgr, 'shell', 0.9, 0.9, 0.9)     # |p| = 1.559
check('conform on the unit sphere by 0.5 IS the sphere r = 1.5: '
      '|p| 1.386 inside, 1.559 outside, marked exact',
      c_in['insideOffset'] and not c_out['insideOffset']
      and c_in['approxReason'] == '')
check('conform on the 2×1×1 ellipsoid is marked approx, naming '
      '8.3 item 6', '8.3' in evaluate_offset(mgr, 'shell-e', 0, 0,
                                             1.2)['approxReason'])
check('conform has no row form yet — offset_equation_rows refuses by '
      'name', offset_equation_rows(mgr, 'shell').get('kind')
      == 'no-row-form')
check('conform has no MathShapeDefinition row form either — refused',
      not result_shape_rows(mgr, 'shell').get('ok'))

print('== suite: ms-anchor step 4 — the thread ==')
a_ax, _ = _anchor('cyl-top-axis', 'eq-cyl', [0, 0, 10], [0, 0, -1],
                  'away')
thread = _offset('thread', 'cyl-top-axis', 'custom', 0.0, 'subtract',
                 extent={'w': [0.0, 4.0]}, expr=THREAD_EXPR,
                 knobs={'P': 0.8, 'h': 0.2, 'r': 2.0, 'depth': 0.4})
mgr = _mgr(SHAPES, [a_ax], [thread])
built = offset_field(mgr, 'thread')
fr = built['frame']
check('anchor on the cap, away: w = 2 − z runs down the axis',
      _close(fr['a'], [0, 0, -1])
      and abs(local_coords(fr, 0, 0, 1.5)[2] - 0.5) < 1e-9)
G = built['G_local']
ridges, prev = 0, False
for i in range(0, 4001):
    w = i * 0.001
    inside = G(2.2, 0.0, w) < 0.0
    if inside and not prev:
        ridges += 1
    prev = inside
check('thread P 0.8 over w ∈ [0, 4] at θ = 0: FIVE ridges = 4/0.8 '
      'turns', ridges == 5, str(ridges))
check('ridge centres at w = 0.4 and 1.2 are inside; w = 0.8 (between) '
      'is out; outside the band (ρ = 1.9, 2.5) is out',
      G(2.2, 0, 0.4) < 0 and G(2.2, 0, 1.2) < 0 and G(2.2, 0, 0.8) > 0
      and G(1.9, 0, 0.4) > 0 and G(2.5, 0, 0.4) > 0)
check('it is a HELIX: at θ = π the ridge centre has moved by P/2 '
      '(w = 0.8 inside, 0.4 out)',
      G(-2.2, 0.0, 0.8) < 0 and G(-2.2, 0.0, 0.4) > 0)
check('the w clip holds: w = −0.1 and 4.1 are outside',
      G(2.2, 0, -0.1) > 0 and G(2.2, 0, 4.1) > 0)
sm = sample_offset(mgr, 'thread', resolution=48)
band = math.pi * (2.4 ** 2 - 2.0 ** 2) * 4.0
check('CSG cut of the thread REDUCES the sampled volume, by 30–70 % '
      'of the band π(2.4²−2²)·4 (a 50 % duty ridge, coarse grid)',
      sm.get('ok') and sm['resultVolume'] < sm['parentVolume']
      and 0.3 * band < -sm['deltaVolume'] < 0.7 * band,
      json.dumps({k: sm[k] for k in ('parentVolume', 'resultVolume',
                                     'deltaVolume')}))
rows = offset_equation_rows(mgr, 'thread')
check('the thread emits frame / local / G / field rows; G is written '
      'in q with every knob a scalar operand',
      rows.get('ok')
      and rows['equationRefs']['field'] == 'thread--field'
      and 'np.arctan2(q[1], q[0])' in rows['equationRows'][-2]
      ['operation_json']
      and json.loads(rows['equationRows'][-2]['operands_json'])['P']
      == {'kind': 'scalar', 'value': 0.8})

try:
    import numpy                             # noqa: F401
    from matrices.matrix_equation_executor import evaluate_equation
    _HAVE_NUMPY = True
except ImportError:
    _HAVE_NUMPY = False

if _HAVE_NUMPY:
    class _Row:
        def __init__(self, d):
            for k, v in d.items():
                setattr(self, k, v)

    exec_mgr = types.SimpleNamespace(objectTables={
        'MatrixDefinition': {r['name']: _Row(r)
                             for r in rows['matrixRows']},
        'MatrixEquationDefinition': {r['name']: _Row(r)
                                     for r in rows['equationRows']},
    })
    field_row = _Row(rows['equationRows'][-1])
    agree = True
    for p in ((2.2, 0, 1.6), (2.2, 0, 1.2), (-2.2, 0, 1.2),
              (0.5, 0.5, 0), (2.9, 0.1, -1.9), (5, 5, 5)):
        via_rows = float(evaluate_equation(
            field_row, {'p': [p[0], p[1], p[2], 1.0]},
            manager=exec_mgr))
        if abs(via_rows - built['composed'](*p)) > 1e-9:
            agree = False
    check('PARITY: the thread rows evaluated by the REAL matrix '
          'executor equal the python field at every probe',
          agree)
    grad_row = _Row([r for r in rows['equationRows']
                     if r['name'] == 'eq-cyl--grad'][0])
    gp = evaluate_equation(grad_row, {'p': [1.0, 2.0, 1.9, 1.0]},
                           manager=exec_mgr).tolist()
    check('PARITY: the ∇F row through the executor equals '
          'gradient_value (lateral surface active at (1,2,1.9))',
          _close(gp, gradient_value(mgr, 'eq-cyl', 1.0, 2.0, 1.9)
                 ['gradient'], 1e-9), str(gp))
else:
    check('executor parity SKIPPED — numpy not importable here', True)

print('== suite: ms-anchor seeds ==')
seed_mgr = _mgr(
    [_shape(**{**_SHAPE_BASE, **s}) for s in SEED_MATH_SHAPES],
    [_row(a) for a in SEED_SHAPE_ANCHORS],
    [_row(o) for o in SEED_ANCHORED_OFFSETS])
re_pick = pick_anchor(seed_mgr, 'demo-cylinder', [0, 0, 10], [0, 0, -1])
seed_frame = anchor_frame(re_pick, 'away')
stored = json.loads(SEED_SHAPE_ANCHORS[0]['frame_json'])
check('re-picking the seeded anchor reproduces its hand-computed hit, '
      'normal and frame matrix',
      _close(re_pick['hit'], json.loads(SEED_SHAPE_ANCHORS[0]['hit_json']),
             1e-9)
      and _close(seed_frame['matrix'], stored['matrix'], 1e-9))
m5 = offset_field(seed_mgr, 'demo-m5-internal-thread')
Gm = m5['G_local']
turns, prev = 0, False
for i in range(0, 40001):
    w = i * 0.0001
    inside = Gm(0.23, 0.0, w) < 0.0
    if inside and not prev:
        turns += 1
    prev = inside
check('the seeded M5 internal thread: 50 turns over 4 cm at P = 0.8 mm, '
      'band 2.067..2.5 mm', m5.get('ok') and turns == 50, str(turns))
bore = result_shape_rows(seed_mgr, 'demo-m5-bore', persist=True)
check('the seeded bore (disk, constant t) persists a --result csg row '
      'and sets result_shape_ref on the offset',
      bore.get('ok')
      and seed_mgr.objectTables['AnchoredOffset']['demo-m5-bore']
      .result_shape_ref == 'demo-m5-bore--result'
      and 'demo-m5-bore--result' in seed_mgr.objectTables
      ['MathShapeDefinition'])
bv = evaluate_offset(seed_mgr, 'demo-m5-bore', 0.1, 0.0, 0.0)
check('a point on the bore axis is OUT of the bored result, in the '
      'parent', bv['insideParent'] and not bv['insideResult'])

print('== suite: ms-anchor as Polari rows (analyses + solutions) ==')
from polariNoCode import graph_builder as gb                 # noqa: E402
from polariNoCode.analysis_calls import (                    # noqa: E402
    call_analysis, resolve_callable,
)
check('6 analyses seeded, every callable_ref resolves to a function',
      len(SEED_SHAPE_ANCHOR_ANALYSES) == 6
      and all(callable(resolve_callable(a['callable_ref']))
              for a in SEED_SHAPE_ANCHOR_ANALYSES))
check('6 solutions seeded, each DirectInvocation → AnalysisCall → '
      'ReturnValue', len(SEED_SHAPE_ANCHOR_SOLUTIONS) == 6 and all(
          [st['stateClass'] for st in
           json.loads(sol['definition'])['stateInstances']]
          == ['DirectInvocation', 'AnalysisCall', 'ReturnValue']
          for sol in SEED_SHAPE_ANCHOR_SOLUTIONS))
row_mgr = _mgr(
    [_shape(**{**_SHAPE_BASE, **s}) for s in SEED_MATH_SHAPES]
    + [SHAPES[0]],
    [_row(a) for a in SEED_SHAPE_ANCHORS],
    [_row(o) for o in SEED_ANCHORED_OFFSETS])
row_mgr.objectTables['AnalysisDefinition'] = {
    a['name']: _row(a) for a in SEED_SHAPE_ANCHOR_ANALYSES}
row_mgr.objectTables['SolutionDefinition'] = {
    s_['name']: _row(s_) for s_ in SEED_SHAPE_ANCHOR_SOLUTIONS}
row_mgr.idList = []
pa = call_analysis(row_mgr, 'ms-anchor-pick',
                   {'shape': 'eq-sphere', 'ray_origin': [0, 0, 3],
                    'ray_dir': [0, 0, -1], 'reference': 'tangent_toward'})
check('ms-anchor-pick by name: the sphere ray → (0,0,1), n = +z, frame '
      'a = t₁, provenance stamped, nothing saved',
      pa.get('ok') and _close(pa['pick']['hit'], [0, 0, 1], 1e-9)
      and _close(pa['frame']['a'], pa['pick']['tangentToward'])
      and pa['_analysis']['name'] == 'ms-anchor-pick'
      and pa['saved'] is False, json.dumps(pa)[:200])
pb = call_analysis(row_mgr, 'ms-anchor-pick',
                   {'shape': 'eq-sphere', 'ray_origin': [0, 0, 3],
                    'ray_dir': [0, 0, -1], 'reference': 'away',
                    'name': 'sphere-top-away', 'persist': True})
check('ms-anchor-pick persist=true lands the ShapeAnchor row by name '
      '(and a second call updates, not duplicates)',
      pb.get('ok') and pb['saved'] and pb['created']
      and 'sphere-top-away' in row_mgr.objectTables['ShapeAnchor']
      and call_analysis(row_mgr, 'ms-anchor-pick',
                        {'shape': 'eq-sphere', 'ray_origin': [0, 0, 3],
                         'ray_dir': [0, 0, -1], 'reference': 'toward',
                         'name': 'sphere-top-away', 'persist': True})
      ['created'] is False
      and getattr(row_mgr.objectTables['ShapeAnchor']['sphere-top-away'],
                  'reference') == 'toward')
pm = call_analysis(row_mgr, 'ms-anchor-pick', {'shape': 'no-such-shape'})
check('unknown shape refuses by name with a suggestion',
      pm['ok'] is False and 'no-such-shape' in pm['error']
      and 'suggestion' in pm)
pmiss = call_analysis(row_mgr, 'ms-anchor-pick',
                      {'shape': 'eq-sphere', 'ray_origin': [0, 5, 3],
                       'ray_dir': [0, 0, -1]})
check('a missing ray refuses with the march step as evidence',
      pmiss['ok'] is False and 'step' in pmiss['suggestion']['evidence'])
fa = call_analysis(row_mgr, 'ms-anchor-frame',
                   {'anchor': 'demo-cylinder-top-axis', 'mode': 'toward'})
check('ms-anchor-frame: the seeded anchor re-framed toward gives a = +z; '
      'an unknown anchor refuses by name',
      fa.get('ok') and _close(fa['a'], [0, 0, 1])
      and call_analysis(row_mgr, 'ms-anchor-frame',
                        {'anchor': 'nope'})['ok'] is False)
ea = call_analysis(row_mgr, 'ms-offset-evaluate',
                   {'offset': 'demo-m5-internal-thread',
                    'points': [[0.23, 0, 1.96], [0, 0, 0]]})
check('ms-offset-evaluate over two points: the ridge point is cut from '
      'the result, the axis point is parent-only',
      ea.get('ok') and ea['count'] == 2
      and not ea['points'][0]['insideResult']
      and ea['points'][1]['insideParent']
      and call_analysis(row_mgr, 'ms-offset-evaluate',
                        {'offset': 'nope'})['ok'] is False)
sa = call_analysis(row_mgr, 'ms-offset-sample',
                   {'offset': 'demo-cylinder-top-pad', 'grid': 12})
check('ms-offset-sample: the pad ADDS volume to demo-cylinder',
      sa.get('ok') and sa['resultVolume'] > sa['parentVolume'])
qa = call_analysis(row_mgr, 'ms-offset-equations',
                   {'offset': 'demo-cylinder-top-pad'})
check('ms-offset-equations: the --field row is named; the parent ∇F row '
      'rides along', qa.get('ok')
      and qa['equationRefs']['field'] == 'demo-cylinder-top-pad--field'
      and qa['equationRefs']['parentGradient'] == 'demo-cylinder--grad')
ra = call_analysis(row_mgr, 'ms-offset-result',
                   {'offset': 'demo-cylinder-top-pad', 'persist': True})
check('ms-offset-result persist=true: JSON rows, --result landed, '
      'result_shape_ref set; the custom thread refuses by name',
      ra.get('ok') and ra['rowNames'][-1] == 'demo-cylinder-top-pad--result'
      and isinstance(ra['rows'][0], dict)
      and 'demo-cylinder-top-pad--result'
      in row_mgr.objectTables['MathShapeDefinition']
      and row_mgr.objectTables['AnchoredOffset']['demo-cylinder-top-pad']
      .result_shape_ref == 'demo-cylinder-top-pad--result'
      and call_analysis(row_mgr, 'ms-offset-result',
                        {'offset': 'demo-m5-internal-thread'})['ok']
      is False)
sol = next(s_ for s_ in SEED_SHAPE_ANCHOR_SOLUTIONS
           if s_['name'] == 'ms-run-anchor-pick')
trace = gb.execute(json.loads(sol['definition']), manager=row_mgr,
                   params={'shape': 'eq-sphere', 'ray_origin': [0, 0, 3],
                           'ray_dir': [0, 0, -1], 'reference': 'toward'})
ret = getattr(trace, 'final_return_value', None)
check('ms-run-anchor-pick through the REAL SolutionExecutionEngine '
      'returns the same hit (0,0,1)',
      isinstance(ret, dict) and ret.get('ok')
      and _close(ret['pick']['hit'], [0, 0, 1], 1e-9),
      f'{type(trace).__name__} {str(ret)[:160]}')

failed = _results.count(False)
print(f'\n{len(_results) - failed}/{len(_results)} checks passed')
raise SystemExit(1 if failed else 0)
