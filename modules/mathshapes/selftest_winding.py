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

    print('== suite: ws-4 — the coupled family cascades ==')
    from mathshapes.spool_geometry import (
        derived_cylinder, spool_from_winding,
    )
    SPOOL = {'barrel_wall': 0.3, 'flange_thickness': 0.5,
             'flange_clearance': 0.5}
    sp = spool_from_winding(GOOD, SPOOL)
    check('spool derives every size from its winding '
          '(flange = outer 2.5 + clearance 0.5)',
          sp['ok']
          and abs(sp['derived']['flangeRadius'] - 3.0) < 1e-9
          and abs(sp['derived']['overallLength'] - 3.0) < 1e-9
          and sp['derived']['turnCapacity'] == 16
          and abs(sp['derived']['utilization'] - 10 / 16) < 1e-9)
    sp2 = spool_from_winding({**GOOD, 'turns': 14}, SPOOL)
    check('MODULATION CASCADES: +4 turns -> new layer -> flange '
          'radius follows the wound outer',
          sp2['ok']
          and sp2['derived']['flangeRadius']
          > sp['derived']['flangeRadius'])
    over = spool_from_winding({**GOOD, 'turns': 21},
                              {**SPOOL, 'flange_radius': 2.0})
    check('a winding that OVERFLOWS a FIXED physical flange '
          'refuses, naming capacity and the knobs (follow-mode '
          'flanges grow instead — overflow impossible by '
          'construction)',
          not over['ok']
          and 'OVERFLOWS' in over['refusals'][0]
          and 'capacity 8' in over['refusals'][0],
          str(over.get('refusals')))
    check('wall thicker than the bore refuses',
          not spool_from_winding(
              GOOD, {**SPOOL, 'barrel_wall': 1.5})['ok'])

    from mathshapes.shape_analysis import shape_properties
    _shape_rows = {
        'w': types.SimpleNamespace(
            name='w', family='winding',
            parameters_json=__import__('json').dumps(GOOD)),
        's': types.SimpleNamespace(
            name='s', family='spool',
            parameters_json=__import__('json').dumps(
                {'winding_ref': 'w', **SPOOL})),
    }
    _mgr = types.SimpleNamespace(
        objectTables={'MathShapeDefinition': _shape_rows})
    gear = derived_cylinder(
        _mgr, {'ref': 's', 'radius_from': 'flangeRadius',
               'radius_ratio': 0.5, 'height': 1.0},
        shape_properties)
    check('the gear FOLLOWS the spool: radius = flangeRadius x '
          'ratio, resolved live through the reference chain',
          gear['ok'] and abs(gear['object']['radius'] - 1.5) < 1e-9)
    _shape_rows['w'].parameters_json = __import__('json').dumps(
        {**GOOD, 'turns': 14})
    gear2 = derived_cylinder(
        _mgr, {'ref': 's', 'radius_from': 'flangeRadius',
               'radius_ratio': 0.5, 'height': 1.0},
        shape_properties)
    check('tune the WINDING and the GEAR rescales — the whole '
          'chain is live, nothing copied',
          gear2['ok']
          and gear2['object']['radius'] > gear['object']['radius'])
    check('follower naming a missing derived value refuses with '
          'the available keys',
          not derived_cylinder(
              _mgr, {'ref': 's', 'radius_from': 'nope',
                     'radius_ratio': 1.0},
              shape_properties)['ok'])

    print('== suite: ws-4 — display LOD (the equation never '
          'changes) ==')
    from mathshapes.winding_geometry import winding_display_mesh
    big = winding_coherence({**GOOD, 'turns': 5000,
                             'window_length': 500.0})
    solid = winding_display_mesh(big['object'], {})
    check('past the wire limit auto mode draws the wound annulus '
          'with a textureHint carrying the TRUE counts',
          solid['renderMode'] == 'solid'
          and solid['textureHint']['turns'] == 5000
          and solid['textureHint']['turnsPerLayer']
          == big['object']['tpl']
          and 'equation is unchanged' in solid['method'])
    wire = winding_display_mesh(big['object'],
                                {'render_mode': 'wire'})
    check('explicit wire mode still draws wire (decimated, '
          'honestly)',
          wire['renderMode'] == 'wire'
          and 'turns rendered' in wire['method'])

    print('== suite: gr-3 — the gear with real, tunable teeth ==')
    from mathshapes.gear_geometry import (
        gear_coherence, gear_mesh, gear_profile,
    )
    GEAR = {'module': 0.3, 'teeth': 8, 'pressure_angle_deg': 20.0,
            'profile_shift': 0.55, 'addendum_coeff': 0.6,
            'face_width': 1.6, 'bore_radius': 0.25,
            'center': [0, 0, 0], 'axis': 'z'}
    g = gear_coherence(GEAR)
    check('a low-count clock pinion coheres with shift + short '
          'addendum (pitch=mz/2, base=pitch cos a)',
          g['ok']
          and abs(g['derived']['pitchRadius'] - 1.2) < 1e-6
          and abs(g['derived']['baseRadius']
                  - 1.2 * math.cos(math.radians(20))) < 1e-5
          and g['derived']['tipLand'] > 0)
    check('UNDERCUT refuses at x=0 for 8 teeth, naming the shift '
          'that clears it and the cycloidal seam',
          (lambda r: not r['ok']
           and 'UNDERCUT' in r['refusals'][0]
           and 'cycloidal' in r['refusals'][0])(
              gear_coherence({**GEAR, 'profile_shift': 0.0})))
    check('a tip that sharpens to nothing refuses, naming both '
          'knobs',
          (lambda r: not r['ok']
           and 'sharpens' in r['refusals'][0])(
              gear_coherence({**GEAR, 'addendum_coeff': 1.4})))
    check('a bore swallowing the root circle refuses',
          not gear_coherence({**GEAR, 'bore_radius': 1.1})['ok'])
    prof = gear_profile(g['object'])
    radii = [math.hypot(p[0], p[1]) for p in prof]
    check('the profile SHOWS the teeth: radius oscillates '
          'root-to-tip 8 times around one revolution',
          abs(max(radii) - g['derived']['tipRadius']) < 1e-6
          and abs(min(radii) - g['derived']['rootRadius']) < 1e-6
          and sum(1 for i in range(len(radii))
                  if radii[i - 1] < g['object']['r_p'] <= radii[i])
          == 8)
    pts, tris = gear_mesh(g['object'])
    check('the gear solid meshes closed (profile + bore, top + '
          'bottom, 8n triangles)',
          len(pts) == 4 * len(prof)
          and len(tris) == 8 * len(prof))
    g12 = gear_coherence({**GEAR, 'teeth': 12,
                          'profile_shift': 0.3})
    check('teeth are TUNABLE: 12 teeth at the same module widen '
          'the pitch circle exactly (mz/2)',
          g12['ok']
          and abs(g12['derived']['pitchRadius'] - 1.8) < 1e-9)
    _shape_rows['g'] = types.SimpleNamespace(
        name='g', family='gear',
        parameters_json=__import__('json').dumps(
            {k: v for k, v in GEAR.items() if k != 'module'}
            | {'ref': 's', 'radius_from': 'flangeRadius',
               'radius_ratio': 0.5}))
    gprops = shape_properties(_mgr, 'g')
    check('the gear joins the CASCADE: module derives from the '
          'spool it follows (pitch = flangeRadius x ratio)',
          gprops.get('ok')
          and abs(gprops['derived']['pitchRadius']
                  - shape_properties(_mgr, 's')['derived'][
                      'flangeRadius'] * 0.5) < 1e-6)

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
