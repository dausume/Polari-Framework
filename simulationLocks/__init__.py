"""
@module simulationLocks

xsim-2: single-writer multiscale simulation — the fencing-token
mutation lease, the run's object-lock working set, and the persisted
simulation queue on core polari (CROSS_INSTANCE_SIM_PLAN.md, Dustin's
directives 4-6: assume ONE mutator mesh-wide; a running multiscale sim
locks out all others except its tied children; queue on core).

Layout ([[file-size-decomposition]]):
    lease.py            — MutationLease singleton + LeaseBreakEvent:
                          monotonic fencing epochs, heartbeat,
                          TTL-breakable (never auto-broken)
    object_locks.py     — ObjectLockEntry + LockBreakEvent: the run's
                          working set, selector granularity
                          id|name|range|class-wide, generated-object
                          auto-lock, quarantine-on-failure
    sim_queue.py        — SimulationQueueEntry + the gate every sim
                          entry point calls (tied children present the
                          parent's token, never re-acquire)
    locks_api.py        — /api/simulation-locks HTTP surface
    selftest_sim_locks.py — python3 -m simulationLocks.selftest_sim_locks
"""
