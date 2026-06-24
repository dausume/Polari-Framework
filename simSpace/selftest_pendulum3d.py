"""
Smoke test: the seeded pendulum-3d-viz scene compiles to renderable 3D
objects/connections. No server, no sudo.

Run from polari-framework/:
    python3 -m simSpace.selftest_pendulum3d

Builds a fake manager from the REAL pendulum seed data and runs compile_3d,
asserting the bob emits a sphere at its world position and the string emits
a connection from the pivot to the bob.
"""

from types import SimpleNamespace

from simSpace.compilers.compile_3d import compile_3d
from simulations.seed_data import (
    SEED_PENDULUM_SIMSPACES, SEED_PENDULUM_BINDINGS,
    SEED_PENDULUM_BOB_ROWS, SEED_PENDULUM_STRING_ROWS,
)


def _ns_rows(rows):
    return {r['name']: SimpleNamespace(**r) for r in rows}


def _mgr():
    m = SimpleNamespace()
    m.objectTypingDict = {}
    m.objectTables = {
        'PendulumBobSimState': _ns_rows(SEED_PENDULUM_BOB_ROWS),
        'PendulumStringSimState': _ns_rows(SEED_PENDULUM_STRING_ROWS),
        'SimSpaceBindingDefinition': {
            b['name']: SimpleNamespace(**b) for b in SEED_PENDULUM_BINDINGS
        },
    }
    return m


PASS, FAIL = '\033[0;32mPASS\033[0m', '\033[0;31mFAIL\033[0m'
results = []


def check(label, cond, extra=''):
    results.append(bool(cond))
    print(f'  [{PASS if cond else FAIL}] {label}{("  " + extra) if extra else ""}')


def main():
    print('pendulum-3d-viz compile smoke test\n')
    scene = next((s for s in SEED_PENDULUM_SIMSPACES if s['name'] == 'pendulum-3d-viz'), None)
    check('pendulum-3d-viz scene is seeded', scene is not None)
    if not scene:
        print('\n0 — scene missing'); return 1
    check("scene dimensionality == '3d'", scene.get('dimensionality') == '3d')

    row = SimpleNamespace(**scene)
    warnings, resolved = [], []
    objects, connections, _vectors = compile_3d(_mgr(), row, warnings, resolved, run_filter=None)

    spheres = [o for o in objects if o.get('shapeRef') == 'sphere']
    bobs = [o for o in objects if o.get('classRef', {}).get('className') == 'PendulumBobSimState']
    pivot = [o for o in objects if o.get('id', '').endswith('pivot') or o.get('label') == 'Pivot']
    check('freestanding pivot sphere emitted', len(pivot) >= 1)
    check('bob objects emitted (sphere)', len(bobs) > 0 and all(b['shapeRef'] == 'sphere' for b in bobs),
          f'count={len(bobs)}')
    check('bob carries scale (sized down)', bobs and bobs[0].get('scale') == 0.12,
          f"scale={bobs[0].get('scale') if bobs else None}")
    check('string connections emitted', len(connections) > 0, f'count={len(connections)}')
    if connections:
        c = connections[0]
        check('connection source at pivot [0,0,0]', list(c.get('sourcePosition') or []) == [0, 0, 0])
        check('connection target is 3D (len 3)', len(c.get('targetPosition') or []) == 3,
              f"target={c.get('targetPosition')}")

    # The step-0 bob should sit at the default-plane embedding (x, y, 0).
    step0 = next((o for o in bobs if o['id'].endswith('-bob-0')), bobs[0] if bobs else None)
    if step0:
        pos = step0['position']
        check('step-0 bob world pos ≈ (0.5, -0.866, 0)',
              abs(pos[0] - 0.5) < 1e-3 and abs(pos[1] + 0.8660254) < 1e-3 and abs(pos[2]) < 1e-9,
              f'pos={pos}')

    print()
    n = sum(1 for r in results if r)
    print(f'{n}/{len(results)} checks passed')
    if warnings:
        print('warnings:', warnings[:5])
    return 0 if n == len(results) else 1


if __name__ == '__main__':
    import sys
    sys.exit(main())
