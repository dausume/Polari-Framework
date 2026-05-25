"""
@cross-cutting
@module simulations.simulation_execution_solution
@tags @xc:bindings

SimulationExecutionSolution — a simulation-flavored variant of
SolutionDefinition. Same `definition` JSON shape so the existing
no-code engine + editor work without modification; the split exists
because:

  * filtering — binding dropdowns can show ONLY simulation-flavored
    solutions when the user is wiring a SimStateStepBinding's
    step_solution_ref, hiding general-purpose solutions that aren't
    valid step functions;
  * validation — `expected_inputs_json` / `expected_outputs_json`
    declare the field set this solution must consume + produce, so
    the editor can warn (or block save) when the solution graph
    doesn't read every declared input or write every declared output;
  * discovery — the simulation-detail page reverse-scans this table to
    list "which step solutions exist for me" without trawling the
    whole SolutionDefinition table.

Many SimulationExecutionSolution rows can map to a single
SimulationDefinition (one per participating SimState class — bob's
step solution + string's step solution + …), and a single
SimulationDefinition can have multiple competing solutions for the
same SimState class (e.g. "small-angle approximation" vs "full ODE"
for PendulumBobSimState); the SimStateStepBinding chooses which one
runs.

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence)
  - simulations.simulation_runner (_load_solution_data lookup)
  - frontend simulation editor — solution picker for each SimState binding
@see /OVERLAP_MAP.md
"""

from objectTreeDecorators import treeObject, treeObjectInit


class SimulationExecutionSolution(treeObject):
    """Metadata linking a no-code SolutionDefinition to a simulation
    role. The actual solution graph lives in `SolutionDefinition`
    (where the existing no-code editor reads + writes it without
    modification); this class declares "SolutionDefinition X is used
    as a step solution for SimulationDefinition Y's SimStateClass Z."

    Identity: `name` — unique. Convention:
    "<simulation_definition_name>.<sim_state_class_slug>" with optional
    variant suffix (e.g. "pendulum-2d.bob-step.small-angle").

    Many SimulationExecutionSolutions can map to a single
    SimulationDefinition. They're listed in the SimSpace editor sidebar
    so the user can jump straight to the linked SolutionDefinition in
    the no-code editor.
    """

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        description: str = '',
        # The SimulationDefinition this solution serves.
        simulation_definition_ref: str = '',
        # The *SimState class this solution advances. Verified against
        # the binding's sim_state_class_name to prevent silent miswiring.
        sim_state_class_name: str = '',
        # The SolutionDefinition that holds the actual no-code graph.
        # Editor reads/writes that table directly; we just point at it.
        # When empty, this metadata row is treated as "scheduled but not
        # yet authored" — the runner skips with a warning.
        solution_definition_ref: str = '',
        # JSON-encoded list of input field names this solution consumes.
        # Drives editor validation: every name here must appear in the
        # context the runner builds (prev-row fields, params, dt/time/step,
        # or dep outputs). Empty = no checks performed.
        # Example: ["theta", "omega", "dt", "g", "L", "mass"]
        expected_inputs_json: str = '[]',
        # JSON-encoded list of output field names this solution writes.
        # The SimStepNextState node should cover all of these; the runner
        # then projects them onto the new *SimState row.
        # Example: ["theta", "omega", "x", "y", "energy_total"]
        expected_outputs_json: str = '[]',
        manager=None,
    ):
        self.name = name
        self.description = description
        self.simulation_definition_ref = simulation_definition_ref
        self.sim_state_class_name = sim_state_class_name
        self.solution_definition_ref = solution_definition_ref
        self.expected_inputs_json = expected_inputs_json
        self.expected_outputs_json = expected_outputs_json
