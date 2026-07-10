"""
@module simulationLocks.run_context

The ambient run context (xsim-2): the gated entry point pushes
{run_id, lease_token}; every tied child (subModel stages, engine-model
executions, stage searches, nested solution engines) reads it and
NEVER re-acquires — presenting the parent's token instead.

contextvars is correct here because all simulation execution today is
synchronous within one request thread (seam survey 2026-07-10:
simulation_api loops run_step inline; SolutionExecutionEngine.execute
is a plain call). Cross-PROCESS children (Dask/worker jobs) need the
context passed explicitly — that lands with xsim-4's remote writes.
"""

import contextvars
from typing import Dict, Optional

_RUN_CONTEXT: contextvars.ContextVar = contextvars.ContextVar(
    'polari_run_context', default=None)

# The key used to piggyback the run context on stage_context dicts
# (flat stageDerived keys never collide with a dunder name).
STAGE_CONTEXT_KEY = '__polariRun__'


def current_run() -> Optional[Dict]:
    return _RUN_CONTEXT.get()


def push_run(run_context: Dict):
    return _RUN_CONTEXT.set(run_context)


def pop_run(token) -> None:
    _RUN_CONTEXT.reset(token)


def from_stage_context(stage_context) -> Optional[Dict]:
    """A run context riding a stage-context dict (or the ambient one)."""
    if isinstance(stage_context, dict):
        carried = stage_context.get(STAGE_CONTEXT_KEY)
        if isinstance(carried, dict):
            return carried
    return current_run()
