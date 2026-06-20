"""
End-to-end test of the LIVE pendulum step computing the 3D embedding.

Run from polari-framework/:
    python3 -m polariNoCode.selftest_pendulum_embed

Runs the real seeded bob-integrator SolutionDefinition (now with the
MatrixEquationOperation embedding step) through SolutionExecutionEngine and
asserts the terminator outputs world_x/y/z = the 2D (x_new, y_new) embedded
into the default swing plane. This is exactly what a live run does — what was
producing world_* = 0 before.
"""

import json
import math
from types import SimpleNamespace

from polariNoCode.SolutionExecutionEngine import SolutionExecutionEngine, StepConfig
from simulations.simulation_runner import _extract_final_context
from simulations.seed_data import _BOB_INTEGRATOR_SOL_DEF, _BOB_INTEGRATOR_EQUATIONS
from matrices.seed_data import SEED_MATRIX_EQUATIONS


def _mgr():
    m = SimpleNamespace()
    m.objectTypingDict = {}
    m.objectTables = {
        'EquationDefinition': {e['name']: SimpleNamespace(**e) for e in _BOB_INTEGRATOR_EQUATIONS},
        'MatrixEquationDefinition': {e['name']: SimpleNamespace(**e) for e in SEED_MATRIX_EQUATIONS},
        'MatrixDefinition': {},
    }
    return m


PASS, FAIL = '\033[0;32mPASS\033[0m', '\033[0;31mFAIL\033[0m'
results = []


def check(label, got, expected, tol=1e-4):
    ok = False
    try:
        ok = abs(float(got) - float(expected)) <= tol
    except Exception as e:
        got = f'<err: {e}>'
    results.append(ok)
    print(f'  [{PASS if ok else FAIL}] {label}: got={got} expected≈{expected}')


def main():
    print('Live pendulum 3D-embedding step self-test\n')
    sol = json.loads(_BOB_INTEGRATOR_SOL_DEF['definition'])

    theta, omega, dt, L, g, mass = math.pi / 6, 0.0, 0.01, 1.0, 9.81, 1.0
    alpha_new = -(g / L) * math.sin(theta)         # the merged gravity Σα
    omega_new = omega + alpha_new * dt
    theta_new = theta + omega_new * dt
    x_new = L * math.sin(theta_new)
    y_new = -L * math.cos(theta_new)

    ctx = {
        'self.theta': theta, 'self.omega': omega, 'self.alpha_new': alpha_new,
        'self.dt': dt, 'self.L': L, 'self.g': g, 'self.mass': mass,
        'self.plane_nx': 0.0, 'self.plane_ny': 0.0, 'self.plane_nz': 1.0,
        # bare aliases (engine resolves either form)
        'theta': theta, 'omega': omega, 'alpha_new': alpha_new, 'dt': dt,
        'L': L, 'g': g, 'mass': mass,
        'plane_nx': 0.0, 'plane_ny': 0.0, 'plane_nz': 1.0,
    }

    engine = SolutionExecutionEngine(manager=_mgr())
    trace = engine.execute(solution_data=sol, input_params={},
                           config=StepConfig(mode='step', record_context=True),
                           target_runtime='python_backend', instance_fields=ctx)
    print('  engine status:', trace.status)
    final = _extract_final_context(trace)

    # The 2D integrator results (sanity) …
    check('x_new (2D)', final.get('x'), x_new)
    check('y_new (2D)', final.get('y'), y_new)
    # … and the 3D embedding the live step must now produce (default plane).
    check('world_x = x', final.get('world_x'), x_new)
    check('world_y = y', final.get('world_y'), y_new)
    check('world_z = 0', final.get('world_z'), 0.0)
    # normal passed through
    check('plane_nz passthrough', final.get('plane_nz'), 1.0)

    print()
    n = sum(1 for r in results if r)
    print(f'{n}/{len(results)} checks passed')
    if n != len(results):
        wx = final.get('world_x')
        print('  world_vec/world_x present?', 'world_vec' in final, '| world_x=', wx)
    return 0 if n == len(results) else 1


if __name__ == '__main__':
    import sys
    sys.exit(main())
