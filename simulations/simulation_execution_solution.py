"""
@cross-cutting
@module simulations.simulation_execution_solution
@tags @xc:bindings

SimulationExecutionSolution — the wiring row that links a no-code
SolutionDefinition into a SimulationDefinition as a step solution for
ONE participating *SimState class. The runner discovers solutions by
querying this table at run_step time (sim_def_ref + sim_state_class_name);
there is no separate binding table anymore.

Why a wrapper row and not a flag on SolutionDefinition itself:

  * filtering — solution-pickers can show ONLY simulation-flavored
    rows hiding general-purpose solutions;
  * validation — `expected_inputs_json` / `expected_outputs_json`
    declare the field set this solution consumes + produces, so the
    editor can warn (or block save) when the solution graph doesn't
    read every declared input or write every declared output;
  * orchestration — `order_index` + `depends_on_json` live here so the
    runner can compose multiple solutions per class (Partial+Composition)
    and order classes by cross-class deps without a separate binding
    table.

Many rows can map to a single SimulationDefinition (one per
participating *SimState class, or several when a class is decomposed
into Partial + Composition solutions).

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence)
  - simulations.simulation_runner (walk by (sim, class) → ordered solutions)
  - simulations.simulation_api (`/{sim_ref}/solutions` endpoint)
  - frontend simulation editor sidebar
@see /OVERLAP_MAP.md
"""

from objectTreeDecorators import treeObject, treeObjectInit


class SimulationExecutionSolution(treeObject):
    """One step-solution wiring entry for a SimulationDefinition.

    Identity: `name` — unique. Convention:
    "<simulation_definition_name>.<sim_state_class_slug>[.<variant>]"
    (e.g. "pendulum-2d.bob.gravity-force",
    "pendulum-2d.bob.integrator").

    Many rows can map to a single SimulationDefinition: one per
    participating *SimState class minimum, more when a class is
    decomposed into Partial(s)+Composition. The runner pulls them
    sorted by `order_index` within a class, and topo-sorts CLASSES by
    the union of their solutions' `depends_on_json`.
    """

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        description: str = '',
        # The SimulationDefinition this solution serves.
        simulation_definition_ref: str = '',
        # The *SimState class this solution advances. Must appear in
        # the SimulationDefinition's
        # `participating_sim_state_classes_json`.
        sim_state_class_name: str = '',
        # The SolutionDefinition that holds the actual no-code graph.
        # Editor reads/writes that table directly; we just point at it.
        # When empty, this row is "scheduled but not yet authored" —
        # the runner skips it with a warning.
        solution_definition_ref: str = '',
        # JSON-encoded list of input field names this solution consumes.
        # Drives editor validation: every name here must appear in the
        # context the runner builds (prev-row fields, params, dt/time/step,
        # or dep outputs). Empty = no checks performed.
        expected_inputs_json: str = '[]',
        # JSON-encoded list of output field names this solution writes.
        # The SimStepNextState/SimStepContribution node should cover all
        # of these; the runner projects them onto the new *SimState row.
        expected_outputs_json: str = '[]',
        # Per-class ordering. When multiple solutions target the SAME
        # (sim, class) pair (e.g. "gravity Partial" followed by
        # "integrator Composition"), the runner runs them in ascending
        # order_index. Solutions in the same group share a context:
        # each solution's output context becomes the next solution's
        # input. The final solution's output is what gets projected
        # onto the new *SimState row.
        # Across DIFFERENT *SimState classes, the cross-class topo sort
        # uses `depends_on_json` instead.
        order_index: int = 0,
        # JSON-encoded list of *SimState class names whose CURRENT step
        # output this solution reads. Drives topological ordering — a
        # class can't run until its deps' new rows for the same step
        # exist. Empty = no cross-class deps; runs in parallel with
        # peers. Cycles fail loudly at runtime.
        # Example: '["PendulumBobSimState"]' — the string reads the
        # bob's current θ/ω to compute tension.
        depends_on_json: str = '[]',
        # Turn off without deleting the row. Handy when one class's
        # step solution is broken and would block the rest of the run.
        enabled: bool = True,
        manager=None,
    ):
        self.name = name
        self.description = description
        self.simulation_definition_ref = simulation_definition_ref
        self.sim_state_class_name = sim_state_class_name
        self.solution_definition_ref = solution_definition_ref
        self.expected_inputs_json = expected_inputs_json
        self.expected_outputs_json = expected_outputs_json
        self.order_index = order_index
        self.depends_on_json = depends_on_json
        self.enabled = enabled
