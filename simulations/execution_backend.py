"""
@cross-cutting
@module simulations.execution_backend
@tags @xc:bindings

Execution backends for parallelizable no-code work (DISTRIBUTED_COMPUTE
_PLAN.md track 1). One entry point — `parallel_map(fn, items)` — with
three backends:

  * serial     — a list comprehension. THE DEFAULT; zero behavior change.
  * processes  — stdlib ProcessPoolExecutor. Always available; the
                 dependable parallel path on any install.
  * dask       — dask.distributed LocalCluster (lazy import). The scale-
                 out path: the same call later points at a distributed
                 cluster. Raises ExecutionBackendError with enable
                 instructions when dask isn't installed or the cluster
                 can't start (memory-constrained containers).

`fn` and every item must be picklable for the parallel backends — the
pure attempt task (simulations.attempt_task) is built exactly for that.
Results return in item order for every backend.

@consumers
  - simulations.multi_scale_search (parallel attempt batches)
@see /OVERLAP_MAP.md
"""

import os
from typing import Any, Callable, List, Optional

BACKENDS = ('serial', 'processes', 'dask')

# Hard ceiling on one dask batch — a starved cluster fails structurally
# instead of hanging the HTTP request that triggered it.
DASK_WAIT_SECONDS = 120


class ExecutionBackendError(RuntimeError):
    """A backend is unavailable/misconfigured — carries a plain-language
    message including how to enable it."""


def parallel_map(
    fn: Callable[[Any], Any],
    items: List[Any],
    backend: str = 'serial',
    max_workers: Optional[int] = None,
) -> List[Any]:
    """Map `fn` over `items` on the chosen backend; results in order."""
    backend = (backend or 'serial').strip().lower()
    if backend not in BACKENDS:
        raise ExecutionBackendError(
            f"Unknown execution backend '{backend}'. "
            f"Choose one of: {', '.join(BACKENDS)}.")
    if not items:
        return []
    if backend == 'serial':
        return [fn(item) for item in items]
    workers = max(1, min(len(items),
                         int(max_workers or 0) or (os.cpu_count() or 2)))
    if backend == 'processes':
        from concurrent.futures import ProcessPoolExecutor
        with ProcessPoolExecutor(max_workers=workers) as pool:
            return list(pool.map(fn, items))
    # dask — bounded: a memory-starved cluster must FAIL structurally,
    # never hang the calling request.
    client, cluster = _dask_client(workers)
    try:
        from dask.distributed import wait as dask_wait
        futures = client.map(fn, items)
        try:
            done_info = dask_wait(futures, timeout=DASK_WAIT_SECONDS)
        except Exception as exc:
            raise ExecutionBackendError(
                f"Dask workers did not finish within {DASK_WAIT_SECONDS}s "
                f"({type(exc).__name__}) — in memory-constrained containers "
                f"the cluster's workers are often OOM-killed. Use the "
                f"'processes' backend, or give the container more memory."
            ) from exc
        if getattr(done_info, 'not_done', None):
            raise ExecutionBackendError(
                f"Dask left {len(done_info.not_done)} of {len(items)} tasks "
                f"unfinished within {DASK_WAIT_SECONDS}s — likely OOM-killed "
                f"workers. Use the 'processes' backend, or give the "
                f"container more memory."
            )
        return client.gather(futures)
    finally:
        try:
            client.close()
            cluster.close()
        except Exception:
            pass


def _dask_client(n_workers: int):
    """Start a local Dask cluster. Separated for testability (selftests
    monkeypatch this to simulate a missing/failed dask)."""
    try:
        from dask.distributed import Client, LocalCluster
    except ImportError as exc:
        raise ExecutionBackendError(
            "Dask is not installed on this backend. Enable it with: "
            "pip install 'dask[distributed]' (it is listed in "
            "polari-framework/requirements.txt — rebuild the backend "
            "image to pick it up)."
        ) from exc
    try:
        cluster = LocalCluster(
            n_workers=n_workers,
            threads_per_worker=1,
            processes=True,
            dashboard_address=None,
        )
        return Client(cluster), cluster
    except Exception as exc:
        raise ExecutionBackendError(
            f"Dask is installed but its local cluster could not start "
            f"({type(exc).__name__}: {exc}). This is common in memory-"
            f"constrained containers — use the 'processes' backend, or "
            f"give the container more memory."
        ) from exc
