"""
Self-test for run-scoped live evaluation (the "stuck at initial" bug).

Run from polari-framework/:
    python3 -m simulations.selftest_eval_run_scoping

Reproduces the exact failure: a STALE frozen run (py=-0.866 at every step,
left over from before the physics fix) sits in the DB beside the LIVE run
(py varying). The run-scoped renderer shows motion, but the unscoped eval
interleaved both runs by step index and let the frozen run's rows win
last-writer-wins — pinning every readout to -0.866.

Asserts:
  1. With run_filter='live', the eval reads the LIVE run's varying py.
  2. With NO run_filter, the dominant-run picker scopes to one run rather
     than interleaving (no frozen value leaks into the live steps).
  3. The time selector still picks the right step within the scoped run.
"""

from types import SimpleNamespace

from simulations.equation_evaluation import (
    _intersect_rows_by_step, _pick_target_row, _dominant_run,
)

PASS, FAIL = '\033[0;32mPASS\033[0m', '\033[0;31mFAIL\033[0m'
results = []


def check(label, cond, extra=''):
    results.append(bool(cond))
    print(f'  [{PASS if cond else FAIL}] {label}{("  " + extra) if extra else ""}')


def _bob(run, step, py):
    # Minimal stand-in for a NewtonianPendulumBobSimState row.
    return SimpleNamespace(
        name=f'{run}-bob-{step}', simulation_run_ref=run,
        step=step, time=step * 0.01, py=py,
    )


def _mgr():
    DOWN0 = -0.8660254037844387          # 30° release y
    # LIVE run: py swings up from the release point.
    live = [_bob('live', s, DOWN0 + 0.02 * s) for s in range(6)]
    # STALE frozen run: identical step indices, py pinned at the release y.
    stale = [_bob('stale', s, DOWN0) for s in range(6)]
    table = {r.name: r for r in (live + stale)}
    m = SimpleNamespace()
    m.objectTables = {'NewtonianPendulumBobSimState': table}
    return m


CLS = ['NewtonianPendulumBobSimState']


def main():
    print('Live evaluation — run scoping (stuck-at-initial regression)\n')
    m = _mgr()
    w = []

    # 1. Explicit run_filter='live' → varying py, never the frozen value.
    rows = _intersect_rows_by_step(m, CLS, w, 'pe', run_filter='live')
    pys = [getattr(cr['NewtonianPendulumBobSimState'], 'py') for _, _, cr in rows]
    check('run_filter=live yields 6 live steps', len(rows) == 6, f'n={len(rows)}')
    check('live py varies (not pinned to release)',
          len(set(round(p, 6) for p in pys)) == 6, f'py={[round(p,3) for p in pys]}')

    # The step at t≈0.05 must be the LIVE py, not the stale -0.866.
    picked = _pick_target_row(rows, target_step=None, target_time=0.05)
    py_at = getattr(picked[0][2]['NewtonianPendulumBobSimState'], 'py')
    check('time=0.05 picks live step 5 (py≈-0.766)', abs(py_at - (-0.7660254)) < 1e-6,
          f'py={py_at:.6f}')

    # 2. No run_filter → dominant-run scoping, no interleaving. Both runs
    #    have 6 rows (a tie); whichever wins, the picked step must come from
    #    ONE run — i.e. its py must be internally consistent with that run,
    #    never a frozen value bleeding into a live step.
    dom = _dominant_run(m, CLS)
    check('dominant run resolves to a single run', dom in ('live', 'stale'), f'run={dom}')
    rows_nf = _intersect_rows_by_step(m, CLS, [], 'pe', run_filter=None)
    refs = {getattr(cr['NewtonianPendulumBobSimState'], 'simulation_run_ref')
            for _, _, cr in rows_nf}
    check('unfiltered scan does NOT interleave runs', len(refs) == 1, f'runs={refs}')

    # 2b. Regression guard: a run_filter that matches NO row must NOT go
    #     blank — it degrades to the dominant single run, never empty.
    w3 = []
    rows_bad = _intersect_rows_by_step(m, CLS, w3, 'pe', run_filter='does-not-exist')
    refs_bad = {getattr(cr['NewtonianPendulumBobSimState'], 'simulation_run_ref')
                for _, _, cr in rows_bad}
    check('mismatched run_filter falls back, never blank',
          len(rows_bad) == 6 and len(refs_bad) == 1, f'n={len(rows_bad)} runs={refs_bad}')

    # 3. Legacy single-run DB (no run refs) still works.
    m1 = SimpleNamespace(objectTables={'NewtonianPendulumBobSimState': {
        f'b{s}': SimpleNamespace(name=f'b{s}', simulation_run_ref=None,
                                 step=s, time=s * 0.01, py=0.1 * s)
        for s in range(4)
    }})
    rows1 = _intersect_rows_by_step(m1, CLS, [], 'pe', run_filter=None)
    check('legacy single implicit run still intersects', len(rows1) == 4, f'n={len(rows1)}')

    print()
    n = sum(1 for r in results if r)
    print(f'{n}/{len(results)} checks passed')
    return 0 if n == len(results) else 1


if __name__ == '__main__':
    import sys
    sys.exit(main())
