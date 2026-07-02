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
        # JSON dict keyed BY CLASS NAME of per-class field overrides
        # specific to THIS RUN. Applied on top of the SimulationDefinition's
        # `initial_conditions_overrides_json` (per-run wins) when the
        # runner composes step-0 values. Lets users tweak the starting
        # state for a one-off run without mutating the saved sim def.
        # Example: '{"PendulumBobSimState": {"theta": 1.047, "x": 0.866}}'
        initial_conditions_overrides_json: str = '{}',
        # Per-run timestep in seconds. Overrides the SimulationDefinition's
        # `time_step_seconds` when > 0. Lets a single sim def be replayed
        # at different resolutions (e.g. 1 ms for high-fidelity diagnostic
        # checks, 100 ms for a quick coarse run) without changing the
        # canonical config. 0 / unset = fall back to the sim def's value.
        time_step_seconds: float = 0.0,
        # JSON dict keyed by '<ClassName>.<fieldName>' of per-field save
        # rules specific to THIS RUN. Layers on top of the SimulationDefinition's
        # `field_save_overrides_json` (per-run wins). Same entry shape:
        #   { policy?: 'core'|'derivable'|'skip', interval?: int }
        # Lets the user mark fields as core for a one-off diagnostic
        # run without mutating the saved sim def.
        field_save_overrides_json: str = '{}',
        # JSON dict of per-run PARAMETER overrides, layered over the
        # SimulationDefinition's parameters_json (per-run wins) when the
        # runner builds each step's context. This is how configured IC
        # interfaces (e.g. the bob material picker) give one run a
        # different mass/geometry without mutating the saved sim def —
        # and how a precondition stage's derived outputs flow into a
        # later stage's run. Example: '{"mass": 16.84, "bob_radius": 0.08}'
        parameter_overrides_json: str = '{}',
        # JSON dict {source_sim_name: source_run_name} pairing THIS run
        # with the source runs feeding its SimulationCouplingDefinitions
        # (e.g. {"wind-field-3d": "wind-field-run"}). The runner's
        # coupling pre-pass lazy-pulls + samples those runs; the snapshot
        # / evaluation run scope (simulations.run_scope) also includes
        # them so coupled rows render in the same scene. Empty = an
        # UNCOUPLED run — couplings inject their declared defaults.
        coupled_run_refs_json: str = '{}',
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
        self.initial_conditions_overrides_json = initial_conditions_overrides_json
        self.time_step_seconds = time_step_seconds
        self.field_save_overrides_json = field_save_overrides_json
        self.parameter_overrides_json = parameter_overrides_json
        self.coupled_run_refs_json = coupled_run_refs_json
