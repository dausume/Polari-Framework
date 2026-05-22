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
    """Per-variable metadata for a simulation.

    Two shapes:
      - *Field-backed* (most common): describes a typed field on a `*SimState`
        class. `sim_state_class_name` + `field_name` identify the location.
      - *Derived* (computed by a SimSpaceEvaluationEquation): no class/field —
        the value is produced by evaluating an EquationDefinition over other
        SimVariables. Used to give equation outputs (kinetic_energy,
        potential_energy, …) a stable home for unit + display precision so
        that downstream consumers (overlay readouts, plots) read those
        attributes from one place.

    `name` is unique. Convention for field-backed rows is
    "<SimStateClassName>.<fieldName>"; for derived rows, a short slug
    matching the equation's output meaning ("kinetic_energy").
    """

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        # Field-backed rows: which *SimState class this variable lives on.
        # Empty for derived rows.
        sim_state_class_name: str = '',
        # Field-backed rows: the field name on that class. Empty for derived.
        field_name: str = '',
        # The SimulationDefinition this variable participates in.
        simulation_definition_name: str = '',
        # SI / domain unit string. Free-form for now (e.g. 'radian',
        # 'rad/s', 'm', 'J', 'N'); a future unit catalog can constrain.
        unit: str = '',
        # Decimal places used when this variable's value is rendered as
        # a number. 0 = integer rendering; -1 = auto/unspecified (UI
        # falls back to a sensible default).
        precision: int = 2,
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
        self.precision = precision
        self.role = role
        self.description = description
