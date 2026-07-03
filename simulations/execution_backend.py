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
  * dask       — dask.distributed (lazy import). Two modes:
                 - no scheduler address → LocalCluster in this container;
                 - `scheduler_address` (param or POLARI_DASK_SCHEDULER
                   env, e.g. tcp://prf-dask-scheduler:8786) → connect to
                   an EXISTING cluster, which is how attempts distribute
                   ACROSS Polari instances (the twin test): workers on
                   any node joined to that scheduler execute the same
                   pure tasks. Version/code parity across workers is
                   guaranteed by running the same backend image.
                 Raises ExecutionBackendError with enable instructions
                 when dask isn't installed or the cluster can't
                 start/connect (memory-constrained containers).

`fn` and every item must be picklable for the parallel backends — the
pure attempt task (simulations.attempt_task) is built exactly for that;
remote workers unpickle by importing the module, so worker containers
need the framework on PYTHONPATH (the twin's dask containers set it).
Results return in item order for every backend. `attribution_out`, when
given a dict, is filled (dask only) with `workerSplit` — how many tasks
each named worker executed — so distribution across instances is
verifiable from the caller's report.

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
    scheduler_address: Optional[str] = None,
    attribution_out: Optional[dict] = None,
) -> List[Any]:
    """Map `fn` over `items` on the chosen backend; results in order.

    `scheduler_address` (dask only; default = POLARI_DASK_SCHEDULER env):
    connect to an existing distributed scheduler instead of starting a
    LocalCluster — the cross-instance path. `attribution_out` (dask
    only): filled with {'workerSplit': {workerName: taskCount}} so the
    caller can report WHERE tasks ran.
    """
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
    scheduler_address = (scheduler_address
                         or os.environ.get('POLARI_DASK_SCHEDULER') or '')
    client, cluster = _dask_client(workers, scheduler_address or None)
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
        if attribution_out is not None:
            attribution_out['workerSplit'] = _worker_split(client, futures)
        return client.gather(futures)
    finally:
        try:
            client.close()
            if cluster is not None:
                cluster.close()
        except Exception:
            pass


def _worker_split(client, futures) -> dict:
    """Per-worker task counts for a batch of futures — the proof that
    tasks distributed (e.g. across two Polari instances' workers).
    Best-effort: attribution must never fail the batch."""
    split: dict = {}
    try:
        info = client.scheduler_info() or {}
        names = {addr: (meta.get('name') or addr)
                 for addr, meta in (info.get('workers') or {}).items()}
        who = client.who_has(futures) or {}
        for _key, addrs in who.items():
            for addr in (addrs or [])[:1]:
                label = names.get(addr, addr)
                split[label] = split.get(label, 0) + 1
    except Exception:
        pass
    return split


def _dask_client(n_workers: int, scheduler_address: Optional[str] = None):
    """A Dask client: connected to `scheduler_address` when given (the
    cross-instance path; returns cluster=None), else over a fresh
    LocalCluster. Separated for testability (selftests monkeypatch this
    to simulate missing/failed dask and to capture the address)."""
    try:
        from dask.distributed import Client, LocalCluster
    except ImportError as exc:
        raise ExecutionBackendError(
            "Dask is not installed on this backend. Enable it with: "
            "pip install 'dask[distributed]' (it is listed in "
            "polari-framework/requirements.txt — rebuild the backend "
            "image to pick it up)."
        ) from exc
    if scheduler_address:
        try:
            return Client(address=scheduler_address, timeout=15), None
        except Exception as exc:
            raise ExecutionBackendError(
                f"Could not connect to the Dask scheduler at "
                f"'{scheduler_address}' ({type(exc).__name__}: {exc}). "
                f"Is the dask stack up? (./twin-polari-build.sh dask-up) "
                f"Or unset POLARI_DASK_SCHEDULER / omit daskScheduler to "
                f"use a local cluster or the 'processes' backend."
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
