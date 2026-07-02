"""
@cross-cutting
@module simulations.simulation_definition
@tags @xc:bindings

SimulationDefinition — a simulation recipe. Names the participating
*SimState classes, sim-level constants (g, L, mass…), step config (dt,
duration, recording interval), and any per-class initial-condition
overrides on top of each class's `default_initial_field_values`.

Step solutions are NOT wired here anymore — every
SimulationExecutionSolution row that names this sim in
`simulation_definition_ref` (and a participating class in
`sim_state_class_name`) is picked up automatically by the runner.
Ordering + cross-class dependencies live on those solution rows
(`order_index`, `depends_on_json`).

@consumers
  - polariServer.defClassList
  - simulations.simulation_runner (binds at run_step time)
  - simulations.simulation_api (storage prediction, solutions endpoint)
  - simulations.seed_data (the pendulum demo)
@see /OVERLAP_MAP.md
"""

from objectTreeDecorators import treeObject, treeObjectInit


class SimulationDefinition(treeObject):
    """A reusable simulation configuration.

    Composition: a SimulationDefinition is the recipe; the actual recorded
    rows live across one or more `*SimState` classes that each declare
    `simulation_definition_name = '<this.name>'` as a class attribute.
    `participating_sim_state_classes_json` makes that membership
    EXPLICIT (so the runner knows which classes to walk without
    scanning the whole type registry, and the editor can list them in
    one place).
    """

    @treeObjectInit
    def __init__(
        self,
        # Unique identity. Conventionally "<system>-<variant>" e.g.
        # "pendulum-2d", "double-pendulum-chaotic", etc.
        name: str = '',
        description: str = '',
        # What this simulation is FOR, declared first — it drives the
        # per-intent required-definitions checklist in the authoring
        # wizard and constrains where the space can plug into a
        # multi-scale composition (see simulations.simulation_intents):
        #   observe | search | feasibility | optimize | calibrate |
        #   validate | sensitivity | compare
        # A stage using this sim declares its own role-intent, checked
        # for compatibility against this declaration.
        intent: str = 'observe',
        # JSON-encoded list of *SimState class names this simulation
        # advances. Explicit roster so the runner can walk it without
        # reverse-scanning the type registry, and so the editor knows
        # which classes to surface in the "participating classes"
        # section. Empty = no participants (the simulation does
        # nothing).
        # Example: '["PendulumBobSimState","PendulumStringSimState"]'
        participating_sim_state_classes_json: str = '[]',
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
        # JSON dict, keyed BY CLASS NAME, of per-class initial-condition
        # OVERRIDES. The runner merges these on top of each class's
        # `default_initial_field_values` (sim overrides win) when
        # writing the step-0 row. Empty/missing = use class defaults
        # straight.
        # Example:
        #   '{"PendulumBobSimState": {"theta": 1.047}}'
        # (override the bob's release angle to 60° while leaving the
        #  string's defaults untouched.)
        initial_conditions_overrides_json: str = '{}',
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
        # OPTIONAL: name of a SolutionDefinition whose graph starts with
        # an `InitialConditionsValidatorEntry` and terminates at a
        # `ValidationResult`. The runner invokes it before writing the
        # step=0 row with the merged initial conditions in context
        # (class defaults + sim overrides + per-run overrides). Empty
        # string = no validator; step 0 writes unconditionally.
        # Used by both the runner (gate step 0) and the
        # `/validate-initial-conditions` endpoint (live UI feedback).
        initial_conditions_validator_ref: str = '',
        # JSON dict keyed by '<ClassName>.<fieldName>' of per-field save
        # rules that override the class-level `field_save_policy`. Each
        # entry: { policy?: 'core'|'derivable'|'skip', interval?: int }.
        # `policy` overrides the class declaration; `interval` (when >
        # 0) overrides recording_interval_steps for THIS field only.
        # `skip` means the field is never persisted regardless of what
        # the class says (use sparingly — readers may break).
        # Per-run overrides on SimulationRun.field_save_overrides_json
        # layer on top of this dict.
        # Example:
        #   '{"PendulumBobSimState.x": {"policy": "derivable"},
        #     "PendulumBobSimState.energy_total": {"policy": "core", "interval": 1}}'
        field_save_overrides_json: str = '{}',
        manager=None,
    ):
        self.name = name
        self.description = description
        self.intent = intent
        self.participating_sim_state_classes_json = participating_sim_state_classes_json
        self.time_step_seconds = time_step_seconds
        self.duration_seconds = duration_seconds
        self.recording_interval_steps = recording_interval_steps
        self.initial_conditions_overrides_json = initial_conditions_overrides_json
        self.parameters_json = parameters_json
        self.termination_predicate = termination_predicate
        self.time_unit = time_unit
        self.initial_conditions_validator_ref = initial_conditions_validator_ref
        self.field_save_overrides_json = field_save_overrides_json
