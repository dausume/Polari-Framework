"""
@cross-cutting
@module simulations.sim_variable
@tags @xc:bindings

SimVariable — declarative metadata about one variable on a `*SimState`
class. Pairs (sim_state_class_name, field_name) with domain semantics
that polyTypedVars can't carry: physical unit, role (state / derived /
energy / diagnostic), and a human description.

These rows are read-only documentation for the UI today (binding tab
preview, tooltip headers, future plotting axis labels) and a hook for
later: binding validation (only let users bind position to length-typed
variables), unit conversion, and per-variable display formatting.

@consumers
  - polariServer.defClassList (auto-CRUDE)
  - simulations.seed_data (the pendulum demo seeds 8 of these)
  - (future) SimSpace binding editor — surface units when picking fields
@see /OVERLAP_MAP.md
"""

from objectTreeDecorators import treeObject, treeObjectInit


class SimVariable(treeObject):
    """Per-field metadata about a variable on a *SimState class.

    `name` is a unique identifier — convention is
    "<SimStateClassName>.<fieldName>" so the row is locatable without
    a composite key (e.g. "PendulumBobSimState.theta").
    """

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        # Which *SimState class this variable lives on.
        sim_state_class_name: str = '',
        # The field name on that class (e.g. 'theta', 'omega', 'x').
        field_name: str = '',
        # The SimulationDefinition this variable participates in. Lets
        # the simulation-detail page list "variables tracked by this
        # simulation" without scanning every SimState class.
        simulation_definition_name: str = '',
        # SI / domain unit string. Free-form for now (e.g. 'radian',
        # 'rad/s', 'm', 'J', 'N'); a future unit catalog can constrain.
        unit: str = '',
        # Semantic role for grouping / filtering:
        #   state      — an integrator state variable (theta, omega)
        #   derived    — computed from state vars (x, y from theta)
        #   energy     — KE / PE / total — conservation monitor
        #   diagnostic — debug-only, not driving the physics
        role: str = 'state',
        # One-line human description for tooltips and the binding editor.
        description: str = '',
        manager=None,
    ):
        self.name = name
        self.sim_state_class_name = sim_state_class_name
        self.field_name = field_name
        self.simulation_definition_name = simulation_definition_name
        self.unit = unit
        self.role = role
        self.description = description
