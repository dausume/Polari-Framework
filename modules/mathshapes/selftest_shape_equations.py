"""
@module mathshapes.selftest_shape_equations

mq-1 selftests: quadric builders hand-checked, the implicit field
(inside<0/surface=0/outside>0) across families incl. CSG, the
DRAWN-surface parity (winding rule generalized), the emitted
no-code rows evaluating IDENTICALLY through the real
matrix_equation_executor (numpy leg), the M1 motor shapes all
emitting, and the honest refusals (winding = parametric curve,
unknown family = named absence).

Run from polari-framework/: python3 -m mathshapes.selftest_shape_equations
"""

import json
import types

from mathshapes.shape_equations import (
    equation_parity, field_value, seed_shape_equations,
    shape_equation_rows, surface_quadrics,
)
from mathshapes.shape_geometry import (
    box_plane_quadrics, plane_quadric_matrix, quadric_value,
    sphere_quadric_matrix,
)

PASS = '\033[92mPASS\033[0m'
FAIL = '\033[91mFAIL\033[0m'
_results = []


def check(label, cond, extra=''):
    _results.append(bool(cond))
    print(f'{PASS if cond else FAIL}: {label}'
          + (f'  [{extra}]' if extra and not cond else ''))


def _shape(**kw):
    base = {'name': '', 'family': 'primitive',
            'primitive_kind': '', 'parameters_json': '{}',
            'quadric_matrix_json': '', 'csg_json': '',
            'bounds_json': ''}
    base.update(kw)
    return types.SimpleNamespace(**base)


FIXTURE_SHAPES = [
    _shape(name='eq-box', primitive_kind='box',
           parameters_json=json.dumps(
               {'size': [4.0, 2.0, 2.0],
                'center': [1.0, 0.0, 0.0]})),
    _shape(name='eq-cyl', primitive_kind='cylinder',
           parameters_json=json.dumps(
               {'radius': 3.0, 'height': 4.0, 'axis': 'z',
                'center': [0.0, 0.0, 0.0]})),
    _shape(name='eq-bore', primitive_kind='cylinder',
           parameters_json=json.dumps(
               {'radius': 2.0, 'height': 5.0, 'axis': 'z',
                'center': [0.0, 0.0, 0.0]})),
    _shape(name='eq-tube', family='csg',
           csg_json=json.dumps({'op': 'difference',
                                'shapes': ['eq-cyl', 'eq-bore']}),
           bounds_json=json.dumps([[-3.5, 3.5], [-3.5, 3.5],
                                   [-2.5, 2.5]])),
    _shape(name='eq-quadric', family='quadric',
           quadric_matrix_json=json.dumps(
               [1.0, 0, 0, 0, 0, 1.0, 0, 0, 0, 0, 1.0, 0,
                0, 0, 0, -1.0]),
           bounds_json=json.dumps([[-1, 1], [-1, 1], [-1, 1]])),
    _shape(name='eq-mesh', family='mesh'),
    _shape(name='eq-winding', family='winding'),
]


def _mgr(shapes):
    m = types.SimpleNamespace()
    m.objectTables = {'MathShapeDefinition':
                      {s.name: s for s in shapes}}
    return m


mgr = _mgr(FIXTURE_SHAPES)

print('== suite: mq-1 quadric builders (hand math) ==')
P = plane_quadric_matrix([0, 1, 0], [0, 5, 0])
check('plane quadric: inside/outside/surface signs by hand',
      quadric_value(P, 0, 0, 0) == -5.0
      and quadric_value(P, 0, 7, 0) == 2.0
      and quadric_value(P, 9, 5, 9) == 0.0)
S = sphere_quadric_matrix([1, 2, 3], 2.0)
check('sphere quadric: center -r², surface 0, symmetric',
      quadric_value(S, 1, 2, 3) == -4.0
      and abs(quadric_value(S, 3, 2, 3)) < 1e-12
      and all(abs(S[i][j] - S[j][i]) < 1e-12
              for i in range(4) for j in range(4)))
B = box_plane_quadrics([1, 0, 0], [4, 2, 2])
check('box: six planes; field max() is -1 at a point 1 inside, '
      '0 on a face, positive outside',
      len(B) == 6
      and max(quadric_value(Q, 1, 0, 0) for _, Q in B) == -1.0
      and max(quadric_value(Q, 3, 0, 0) for _, Q in B) == 0.0
      and max(quadric_value(Q, 4, 0, 0) for _, Q in B) == 1.0)

print('== suite: mq-1 the implicit field across families ==')
for name, inside, surface, outside in (
        ('eq-box', (1, 0, 0), (3, 0, 0), (9, 9, 9)),
        ('eq-cyl', (0, 0, 0), (3, 0, 0), (9, 0, 0)),
        ('eq-quadric', (0, 0, 0), (1, 0, 0), (2, 0, 0)),
        ('eq-tube', (2.5, 0, 0), (3, 0, 0), (0, 0, 0))):
    fi = field_value(mgr, name, *inside)['value']
    fs = field_value(mgr, name, *surface)['value']
    fo = field_value(mgr, name, *outside)['value']
    check(f'{name}: F<0 inside, F=0 on surface, F>0 outside '
          f'(the tube counts its BORE as outside)',
          fi < 0 and abs(fs) < 1e-9 and fo > 0,
          f'{fi} {fs} {fo}')

check('winding refuses as a PARAMETRIC CURVE naming ws-1',
      not field_value(mgr, 'eq-winding', 0, 0, 0).get('ok')
      and 'parametric' in field_value(
          mgr, 'eq-winding', 0, 0, 0)['refusal'].lower())
check('mesh family refuses as a named absence',
      'named absence' in field_value(
          mgr, 'eq-mesh', 0, 0, 0).get('refusal', ''))

print('== suite: mq-1 the emitted no-code rows ==')
rows = shape_equation_rows(mgr, 'eq-tube')
check('the csg tube emits matrices + surface equations for BOTH '
      'children and ONE --field equation referencing them',
      rows.get('ok')
      and len(rows['matrixRows']) == 6      # 2x (lateral + 2 caps)
      and rows['equationRows'][-1]['name'] == 'eq-tube--field'
      and all('--Q--' in r['name'] for r in rows['matrixRows'])
      and 'matrixEquation' in rows['equationRows'][-1]
      ['operands_json'])
check('every matrix row is a FLAT 16-element literal the '
      'executor can load',
      all(len(json.loads(r['values_json'])) == 16
          and r['shape_json'] == '[4, 4]'
          for r in rows['matrixRows']))

try:
    import numpy as np                       # noqa: F401
    from matrices.matrix_equation_executor import (
        evaluate_equation,
    )
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
                                     for r in
                                     rows['equationRows']},
    })
    field_row = _Row(rows['equationRows'][-1])
    agree = True
    for p in ((2.5, 0, 0), (3, 0, 0), (0, 0, 0), (1.7, 1.7, 1.0),
              (5, 5, 5)):
        via_rows = float(evaluate_equation(
            field_row, {'p': [p[0], p[1], p[2], 1.0]},
            manager=exec_mgr))
        via_python = field_value(mgr, 'eq-tube', *p)['value']
        if abs(via_rows - via_python) > 1e-9:
            agree = False
    check('PARITY (the winding rule): the emitted rows evaluated '
          'by the REAL matrix executor equal the pure-python '
          'field at every probe — the rows ARE the shape',
          agree)
else:
    check('executor parity SKIPPED — numpy not importable here '
          '(runs in-container)', True)

print('== suite: mq-1 drawn-surface parity + the M1 shapes ==')
par = equation_parity(mgr, 'eq-cyl', n=24)
check('drawn-surface parity: signs correct, median residual of '
      'the sampled mesh ~0 relative to scale²',
      par.get('ok') and par['signsCorrect']
      and par['surfaceSamples'] > 10
      and par['medianResidual'] < 0.02,
      json.dumps(par)[:200])

from motors.motor_shapes import (        # noqa: E402
    SEED_M1_PART_SHAPES,
)
m1_mgr = _mgr([types.SimpleNamespace(
    **{**{'family': 'primitive', 'primitive_kind': '',
          'parameters_json': '{}', 'quadric_matrix_json': '',
          'csg_json': '', 'bounds_json': ''}, **s})
    for s in SEED_M1_PART_SHAPES])
m1_emitted, m1_refused = [], []
for s in SEED_M1_PART_SHAPES:
    out = shape_equation_rows(m1_mgr, s['name'])
    (m1_emitted if out.get('ok') else m1_refused).append(s['name'])
check('EVERY M1 motor shape emits its equations — the real '
      'machine is matrix-defined end to end, no refusals',
      len(m1_refused) == 0 and len(m1_emitted)
      == len(SEED_M1_PART_SHAPES), str(m1_refused))
yoke = shape_equation_rows(m1_mgr, 'motor-m1-yoke')
check('the M1 yoke (csg annulus) fields as outer minus bore, '
      'and its emitted refs follow the name convention',
      yoke.get('ok')
      and yoke['equationRefs']['field'] == 'motor-m1-yoke--field'
      and field_value(m1_mgr, 'motor-m1-yoke', 22.0, 0, 0)['value']
      < 0
      and field_value(m1_mgr, 'motor-m1-yoke', 0, 0, 0)['value']
      > 0)

print('== suite: mq-1 seed pass ==')
seed_mgr = _mgr(FIXTURE_SHAPES)
reports = seed_shape_equations(seed_mgr)
by_class = {r['class']: r for r in reports}
check('seed emits both classes via the upsert path and REPORTS '
      'the refused shapes by name instead of dropping them',
      'MatrixDefinition' in by_class
      and 'MatrixEquationDefinition' in by_class
      and {r['shape'] for r in
           by_class['MatrixDefinition']['shapeRefusals']}
      == {'eq-mesh', 'eq-winding'})

failed = _results.count(False)
print(f'\n{len(_results) - failed}/{len(_results)} checks passed')
raise SystemExit(1 if failed else 0)
