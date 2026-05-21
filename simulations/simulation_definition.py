"""
@cross-cutting
@module simulations.simulation_definition
@tags @xc:bindings

SimulationDefinition — the config tie-in that wires a target row class
to the no-code step-function that generates its rows over time. Today
the runtime engine isn't wired (Path-A simulation-kind no-code is the
next phase); this class captures everything the engine will need so
the schema is stable when the engine arrives.

@consumers
  - polariServer.defClassList
  - simulations.simulation_api (storage prediction endpoint)
  - simulations.seed_data (the pendulum demo)
  - (future) simulations.simulation_runner — the execution engine
@see /OVERLAP_MAP.md
"""

from objectTreeDecorators import treeObject, treeObjectInit


class SimulationDefinition(treeObject):
    """A reusable simulation configuration.

    Composition: a SimulationDefinition is the recipe; the actual recorded
    rows live across one or more `*SimState` classes that each declare
    `simulation_definition_name = '<this.name>'` as a class attribute.
    The simulation-detail UI reverse-scans for those classes to list
    "which sub-systems this simulation tracks." There's no single
    `target_class_name` because real simulations compose multiple
    sub-systems (e.g. PendulumBobSimState + PendulumStringSimState).
    """

    @treeObjectInit
    def __init__(
        self,
        # Unique identity. Conventionally "<system>-<variant>" e.g.
        # "pendulum-2d", "double-pendulum-chaotic", etc.
        name: str = '',
        description: str = '',
        # No-code solution name that defines the step function.
        # Empty when running with a precomputed reference trajectory
        # (the "ground truth" for visualizing while the engine is built).
        step_solution_ref: str = '',
        # Simulation step size in seconds (dt). Each step advances the
        # state by this much sim-time.
        time_step_seconds: float = 0.01,
        # Total sim-time to run. Combined with time_step_seconds gives
        # the total number of computed steps:
        #     num_steps = ceil(duration_seconds / time_step_seconds)
        duration_seconds: float = 10.0,
        # Persist every N computed steps. Minimum recorded set is always
        # {first, current, step-being-computed, last} (4 rows) regardless
        # of N — see storage_predictor.predict_storage for the math.
        recording_interval_steps: int = 10,
        # JSON dict: initial values for the target class's fields at t=0.
        # Engine merges these into the first row before iterating.
        # e.g. {"theta": 0.5236, "omega": 0.0}  (30° initial deflection)
        initial_conditions_json: str = '{}',
        # JSON dict: simulation constants the step function reads but
        # doesn't update. e.g. {"g": 9.81, "L": 1.0, "mass": 1.0}
        parameters_json: str = '{}',
        # Optional early-termination predicate — runs while expression
        # evaluates falsy, stops when truthy. Expression syntax matches
        # the existing dataset filter chain operators.
        # e.g. "abs(theta) > 1.57"  (stop if angle exceeds 90°)
        termination_predicate: str = '',
        # Display unit for the scrubber — matches TimeUnitId on the frontend.
        time_unit: str = 'second',
        manager=None,
    ):
        self.name = name
        self.description = description
        self.step_solution_ref = step_solution_ref
        self.time_step_seconds = time_step_seconds
        self.duration_seconds = duration_seconds
        self.recording_interval_steps = recording_interval_steps
        self.initial_conditions_json = initial_conditions_json
        self.parameters_json = parameters_json
        self.termination_predicate = termination_predicate
        self.time_unit = time_unit
