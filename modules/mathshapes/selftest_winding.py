"""
Selftest for the winding math object (ws-1).

Run from polari-framework/:  python3 -m mathshapes.selftest_winding

Covers: coherence (valid tunings form the math object with
hand-checkable derived numbers; incoherent tunings REFUSE naming
the knob), the exit-orientation phase, decimation as segments
(never a phantom jump wire), the mesh point cap, and — the one that
matters most — MATRIX-EQUATION PARITY: the emitted
MatrixEquationDefinition spec evaluates to exactly the points the
generator draws, so the object shown IS the equation.
"""

import math
import types

from mathshapes.winding_geometry import (
    _local_point, _world, winding_coherence, winding_matrix_equation,
    winding_segments, winding_tube_mesh,
)

_results = []


def check(label, cond, extra=''):
    _results.append((label, bool(cond)))
    print(f'{"PASS" if cond else "FAIL"}: {label}'
          + (f' — {extra}' if extra and not cond else ''))


GOOD = {'center': [4.0, 0.0, 0.0], 'axis': [1, 0, 0],
        'exit_dir': [0, -1, 0], 'bore_radius': 1.0,
        'wire_diameter': 0.5, 'turns': 10, 'window_length': 2.0}

if __name__ == '__main__':
    print('== suite: coherence — the math object ==')
    c = winding_coherence(GOOD)
    check('coherent tuning forms the object', c['ok'])
    d = c['derived']
    check('derived by hand: tpl=4, layers=3, outer=2.5',
          d['turnsPerLayer'] == 4 and d['layers'] == 3
          and abs(d['outerRadius'] - 2.5) < 1e-9)
    expect_len = 2 * math.pi * (1.25 * 4 + 1.75 * 4 + 2.25 * 2)
    check('wire length = sum of per-turn circumferences, exact',
          abs(d['wireLength'] - expect_len) < 1e-2,
          f"{d['wireLength']} vs {expect_len}")
    check('frame is orthonormal (M rows u,v,w)',
          all(abs(sum(a * b for a, b in zip(r1, r2))
                  - (1.0 if i == j else 0.0)) < 1e-9
              for i, r1 in enumerate(c['object']['M'])
              for j, r2 in enumerate(c['object']['M'])))
    p0 = [a - b for a, b in zip(
        _world(c['object'], _local_point(c['object'], 0.0)),
        c['object']['C'])]
    check('t=0 radial direction is the exit direction',
          p0[1] < -0.9 and abs(p0[2]) < 1e-9)

    print('== suite: refusals — cannot form a math object ==')
    for label, bad, needle in (
        ('zero axis', {**GOOD, 'axis': [0, 0, 0]}, 'zero vector'),
        ('exit parallel to axis',
         {**GOOD, 'exit_dir': [2, 0, 0]}, 'parallel'),
        ('wire fatter than the window',
         {**GOOD, 'wire_diameter': 3.0}, 'window'),
        ('fractional turns', {**GOOD, 'turns': 2.5}, 'whole'),
        ('negative bore', {**GOOD, 'bore_radius': -1}, '> 0'),
    ):
        r = winding_coherence(bad)
        check(f'{label} REFUSES naming the knob',
              not r['ok'] and any(needle in x
                                  for x in r['refusals']),
              str(r.get('refusals')))

    print('== suite: decimation as segments ==')
    segs = winding_segments(c['object'], samples_per_turn=8,
                            turn_stride=1)
    check('stride 1 = one continuous polyline',
          len(segs) == 1 and len(segs[0]) >= 8 * 10)
    segs3 = winding_segments(c['object'], samples_per_turn=8,
                             turn_stride=3)
    check('stride 3 = separate one-turn segments (no phantom '
          'jump wire)',
          len(segs3) == 4
          and all(len(s) <= 8 + 2 for s in segs3))
    mesh = winding_tube_mesh(
        {**c['object'], 'N': 1500, 'tpl': 232},
        samples_per_turn=16, n_ring=6)
    check('mesh auto-decimates under the point cap and SAYS what '
          'was dropped',
          len(mesh['points']) <= 42000
          and 'of 1500 turns rendered' in mesh['method'],
          mesh['method'])

    print('== suite: matrix-equation parity — the drawn object IS '
          'the equation ==')
    spec = winding_matrix_equation(c['object'])
    try:
        import json

        import numpy as np

        from matrices.matrix_equation_executor import (
            evaluate_equation,
        )
        eq_def = types.SimpleNamespace(
            name=spec['name'],
            operation_json=json.dumps(spec['operation_json_obj']),
            operands_json=json.dumps(
                {s: s for s in spec['operands']}))
        ts = [0.0, 0.25, 1.0, 3.7, 6.5, 9.99]
        bindings = {'t': ts, **spec['bindings_from_object']}
        world = evaluate_equation(eq_def, bindings)
        expected = np.asarray(
            [_world(c['object'], _local_point(c['object'], t))
             for t in ts])
        check('equation evaluates to EXACTLY the generator points '
              '(6 sample turns, 1e-9)',
              world.shape == (6, 3)
              and float(np.max(np.abs(world - expected))) < 1e-9,
              f'max diff {np.max(np.abs(world - expected))}')
    except ImportError as e:
        check('matrix executor importable for the parity proof',
              False, str(e))

    failed = [label for label, ok in _results if not ok]
    print(f'\n{len(_results) - len(failed)}/{len(_results)} checks '
          f'passed' + (f'; FAILED: {failed}' if failed else ''))
    raise SystemExit(1 if failed else 0)
