"""
@cross-cutting
@module simulations.simulation_run
@tags @xc:bindings

SimulationRun — captures one execution of a SimulationDefinition.
Records lifecycle state (pending → running → complete/failed/canceled),
progress counters, and links back to the SimulationDefinition that
produced it.

Future STOMP integration will broadcast progress updates by publishing
to /topic/simulation/{run_name}/progress as recorded rows land — this
class stores the source-of-truth state subscribers eventually catch up to.

@consumers
  - polariServer.defClassList
  - simulations.seed_data (precomputed-trajectory runs)
  - (future) simulations.simulation_runner — the execution engine
  - (future) STOMP broadcaster — for live progress streaming
@see /OVERLAP_MAP.md
"""

from objectTreeDecorators import treeObject, treeObjectInit


class SimulationRun(treeObject):
    """A single execution of a SimulationDefinition.

    Identified by `name` (conventionally
    "<simulation_ref>-<timestamp>" or "<simulation_ref>-precomputed").
    Row instances of the target class link back to this via their
    `run_id` field.
    """

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        # Which SimulationDefinition was executed (by name).
        simulation_ref: str = '',
        # Lifecycle:
        #   pending     — created, not yet started
        #   running     — engine is iterating; rows landing live
        #   complete    — finished normally
        #   failed      — engine raised; see error_message
        #   canceled    — user-canceled via UI/STOMP
        #   precomputed — trajectory was baked at seed time, no engine ran
        status: str = 'pending',
        # ISO 8601 timestamps. completed_at empty when not finished.
        started_at: str = '',
        completed_at: str = '',
        # Total computed steps the engine took (≥ recorded_steps).
        total_steps: int = 0,
        # Rows actually persisted (per recording_interval_steps + min set).
        recorded_steps: int = 0,
        # Highest step index that's been persisted — drives progress bars
        # without scanning the row table.
        last_recorded_step: int = 0,
        # For status='failed' — captured exception message.
        error_message: str = '',
        # Optional human label (overrides auto-derived display name).
        label: str = '',
        manager=None,
    ):
        self.name = name
        self.simulation_ref = simulation_ref
        self.status = status
        self.started_at = started_at
        self.completed_at = completed_at
        self.total_steps = total_steps
        self.recorded_steps = recorded_steps
        self.last_recorded_step = last_recorded_step
        self.error_message = error_message
        self.label = label
