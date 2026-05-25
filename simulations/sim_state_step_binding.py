"""
@cross-cutting
@module simulations.sim_state_step_binding
@tags @xc:bindings

SimStateStepBinding — the wiring between a SimulationDefinition, a
`*SimState` class, and the no-code SolutionDefinition that advances
that class by one timestep. One row per (simulation, SimState class)
pair. The SimulationRunner reads this table to know which solutions
to invoke and in what order on every tick.

Why per-SimState (vs. one solution per simulation): a complex
simulation composes multiple sub-system snapshots that each have their
own physics. The pendulum's bob and string evolve via different math;
each gets its own step solution. The runner topo-sorts by
`depends_on_json` so a binding can read the current-step output of
another binding (the string reads the bob's current angle to compute
tension, etc.).

A binding with an empty `step_solution_ref` is treated as "scheduled
but not yet authored" — the runner skips it with a warning so the
simulation-detail page can list the participating sub-systems before
their step functions are written.

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence)
  - simulations.simulation_runner (topo sort + per-tick invocation)
  - (future) frontend simulation editor — pick step solution for each
    SimState participant via dropdowns
@see /OVERLAP_MAP.md
"""

from objectTreeDecorators import treeObject, treeObjectInit


class SimStateStepBinding(treeObject):
    """One simulation×SimState wiring entry.

    Identity: `name`, conventionally
    "<simulation_definition_name>.<sim_state_class_name>" so rows are
    locatable without a composite key.
    """

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        description: str = '',
        # Which SimulationDefinition this wiring belongs to (matches
        # SimulationDefinition.name).
        simulation_definition_ref: str = '',
        # The *SimState class this binding's step solution produces.
        # The class must already declare `simulation_definition_name =
        # <simulation_definition_ref>` as a class-level attribute.
        sim_state_class_name: str = '',
        # SolutionDefinition.name — the no-code that runs once per
        # timestep to emit the new row's field values. Empty = not yet
        # authored (runner skips this binding with a warning rather
        # than erroring out).
        step_solution_ref: str = '',
        # JSON-encoded list of SimState class names whose CURRENT step
        # output this binding's solution reads. Drives topological order
        # — a binding can't run until its deps' new rows for the same
        # step exist. Empty = no cross-class deps; can run in parallel
        # with peers. Cycles fail loudly at runtime.
        # Example: '["PendulumBobSimState"]' — string reads bob's theta
        # at the current step to compute tension.
        depends_on_json: str = '[]',
        # Turn off the binding without deleting the row. Useful during
        # authoring when one SimState's solution is broken and would
        # block the rest.
        enabled: bool = True,
        # When multiple bindings target the SAME (simulation, SimState
        # class) pair — e.g. "force calculator" followed by "integrator"
        # — the runner runs them in ascending order_index. Solutions in
        # the same group share a context: each solution's output context
        # becomes the next solution's input. The final solution's output
        # is what gets projected onto the new *SimState row.
        # Across DIFFERENT SimState classes, the cross-class topo sort
        # uses depends_on_json instead (one ordering per graph layer).
        order_index: int = 0,
        manager=None,
    ):
        self.name = name
        self.description = description
        self.simulation_definition_ref = simulation_definition_ref
        self.sim_state_class_name = sim_state_class_name
        self.step_solution_ref = step_solution_ref
        self.depends_on_json = depends_on_json
        self.enabled = enabled
        self.order_index = order_index
