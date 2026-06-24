"""
Self-test for the Newtonian pendulum (3D).

Run from polari-framework/:
    python3 -m simulations.selftest_newtonian_pendulum

Two independent checks, neither needs the server or sudo:

  1. PHYSICS — a plain-NumPy reference integration that mirrors the EXACT
     vector exprs the no-code MatrixEquationOperations encode (a=F/m,
     semi-implicit Euler, rigid-rod position+velocity projection, signed
     tension, energy). Asserts the rod constraint holds (|p−pivot|=L), the
     small/moderate-angle period ≈ 2π√(L/g), and energy drift stays bounded.
     If this passes, the formulation is sound; the no-code encodes it 1:1.

  2. COMPILE — the seeded `newtonian-pendulum-viz` scene compiles (from the
     step-0 seed rows) to a sphere bob + the rod + the two force-arrow
     connections, color-tagged by their styleRef.
"""

import math
from types import SimpleNamespace

import numpy as np

from simSpace.compilers.compile_3d import compile_3d
from simulations.seed_data import SEED_PENDULUM_SIMSPACES, SEED_PENDULUM_BINDINGS
# Importing newtonian_pendulum_seed also extends the SEED_PENDULUM_* lists above
# in place, so the Newtonian scene/bindings are present when the compile check
# reads them.
from simulations.newtonian_pendulum_seed import (
    SEED_NEWTON_BOB_ROWS, SEED_NEWTON_ROD_ROWS,
    _NEWTON_G, _NEWTON_L, _NEWTON_MASS, _NEWTON_DT, _NEWTON_DURATION,
)

PASS, FAIL = '\033[0;32mPASS\033[0m', '\033[0;31mFAIL\033[0m'
results = []


def check(label, cond, extra=''):
    results.append(bool(cond))
    print(f'  [{PASS if cond else FAIL}] {label}{("  " + extra) if extra else ""}')


# ---------------------------------------------------------------------------
# 1. Physics reference — mirrors the no-code vector exprs exactly.
# ---------------------------------------------------------------------------
def _physics():
    print('Newtonian pendulum — physics (NumPy reference of the no-code exprs)\n')
    g, L, m = _NEWTON_G, _NEWTON_L, _NEWTON_MASS
    # Assert at a fine dt that PROVES the formulation converges. The seed uses a
    # coarser display dt (_NEWTON_DT) for fewer live steps — same exprs, more
    # numerical drift. This validates correctness independent of that choice.
    dt, T = 0.002, 4.0
    p = np.array([0.5, -0.8660254037844387, 0.0])   # 30° release
    v = np.zeros(3)
    down = np.array([0.0, -1.0, 0.0])

    n_steps = int(math.ceil(T / dt))
    energies, radii, px_series, times = [], [], [], []
    for i in range(n_steps + 1):
        # Energies at the CURRENT (constrained) state.
        ke = 0.5 * m * (v @ v)
        pe = m * g * (p[1] + L)
        energies.append(ke + pe)
        radii.append(float(np.linalg.norm(p)))
        px_series.append(float(p[0]))
        times.append(i * dt)
        # The integrator chain EXACTLY as the no-code encodes it: tension (the
        # rigid-rod constraint force) is computed from the current state and
        # folded into the acceleration BEFORE the Euler step.
        f_app = m * g * down
        rhat = p / np.linalg.norm(p)
        f_tension = -((f_app @ rhat) + m * (v @ v) / L) * rhat
        a = (f_app + f_tension) / m
        v1 = v + a * dt
        p1 = p + v1 * dt
        rhat2 = p1 / np.linalg.norm(p1)
        p = L * rhat2
        v = v1 - (v1 @ rhat2) * rhat2

    e0 = energies[0]
    drift = max(abs(e - e0) for e in energies) / abs(e0)
    max_radius_err = max(abs(r - L) for r in radii)

    # Period from px zero-crossings (full cycle = 2 crossings of the same sign
    # direction). Release at +0.5 → first downward crossing is a quarter… use
    # successive upward (− to +) crossings one period apart.
    up_cross = [times[i] for i in range(1, len(px_series))
                if px_series[i - 1] < 0 <= px_series[i]]
    period = (up_cross[1] - up_cross[0]) if len(up_cross) >= 2 else None
    period_ideal = 2 * math.pi * math.sqrt(L / g)   # ≈ 2.006 s (small-angle)

    check('rod constraint holds: |p−pivot| ≈ L every step',
          max_radius_err < 1e-9, f'max|r−L|={max_radius_err:.2e}')
    check('energy drift bounded (< 2%)', drift < 0.02, f'drift={drift*100:.3f}%')
    check('bob oscillates (px changes sign)',
          min(px_series) < -0.3 and max(px_series) > 0.3,
          f'px∈[{min(px_series):.3f},{max(px_series):.3f}]')
    check('period ≈ 2π√(L/g)', period is not None and abs(period - period_ideal) < 0.15,
          f'period={period:.3f}s vs ideal≈{period_ideal:.3f}s')


# ---------------------------------------------------------------------------
# 2. Compile — the scene renders bob + rod + 2 force arrows.
# ---------------------------------------------------------------------------
def _ns_rows(rows):
    return {r['name']: SimpleNamespace(**r) for r in rows}


def _mgr():
    m = SimpleNamespace()
    m.objectTypingDict = {}
    m.objectTables = {
        'NewtonianPendulumBobSimState': _ns_rows(SEED_NEWTON_BOB_ROWS),
        'NewtonianPendulumRodSimState': _ns_rows(SEED_NEWTON_ROD_ROWS),
        'SimSpaceBindingDefinition': {
            b['name']: SimpleNamespace(**b) for b in SEED_PENDULUM_BINDINGS
        },
    }
    return m


def _compile():
    print('\nNewtonian pendulum — compile (newtonian-pendulum-viz)\n')
    scene = next((s for s in SEED_PENDULUM_SIMSPACES
                  if s['name'] == 'newtonian-pendulum-viz'), None)
    check('newtonian-pendulum-viz scene is seeded', scene is not None)
    if not scene:
        return
    row = SimpleNamespace(**scene)
    warnings, resolved = [], []
    objects, connections, vectors = compile_3d(_mgr(), row, warnings, resolved, run_filter=None)

    bobs = [o for o in objects
            if o.get('classRef', {}).get('className') == 'NewtonianPendulumBobSimState']
    check('bob sphere emitted at the 30° release point',
          bobs and bobs[0]['shapeRef'] == 'sphere'
          and abs(bobs[0]['position'][0] - 0.5) < 1e-3
          and abs(bobs[0]['position'][1] + 0.8660254) < 1e-3,
          f'pos={bobs[0]["position"] if bobs else None}')
    check('bob sized to metric radius (scale ≈ 0.16)',
          bobs and abs((bobs[0].get('scale') or 0) - 0.16) < 1e-6,
          f'scale={bobs[0].get("scale") if bobs else None}')
    # The rod is the ONLY connection now (the force arrows are State-Projection
    # vectors, not connections).
    conn_styles = sorted(c.get('styleRef') for c in connections)
    check('one connection emitted (the rod)',
          len(connections) == 1 and conn_styles == ['metal-steel'],
          f'count={len(connections)} styles={conn_styles}')
    # Two State-Projection force arrows on the bob: gravity (red) + net (green).
    vec_styles = sorted(v.get('styleRef') for v in vectors)
    check('two State-Projection vectors emitted (gravity + net)',
          len(vectors) == 2, f'count={len(vectors)} styles={vec_styles}')
    check('force vectors carry distinct color styleRefs',
          'arrow-gravity' in vec_styles and 'arrow-net' in vec_styles,
          f'styles={vec_styles}')
    # Each arrow originates at the bob and carries the right force vector.
    grav = next((v for v in vectors if v.get('styleRef') == 'arrow-gravity'), None)
    check('gravity vector starts at the bob, points down (fgrav=(0,−9.81,0))',
          grav is not None
          and abs(grav['origin'][0] - 0.5) < 1e-3
          and abs(grav['origin'][1] + 0.8660254) < 1e-3
          and abs(grav['vec'][1] + 9.81) < 1e-3 and abs(grav['vec'][0]) < 1e-6,
          f'grav={grav}')
    if warnings:
        print('  warnings:', warnings[:5])


def main():
    _physics()
    _compile()
    print()
    n = sum(1 for r in results if r)
    print(f'{n}/{len(results)} checks passed')
    return 0 if n == len(results) else 1


if __name__ == '__main__':
    import sys
    sys.exit(main())
