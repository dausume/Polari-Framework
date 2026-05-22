"""
@cross-cutting
@module simulations.sim_space_evaluation_equation
@tags @xc:render-shared, @xc:bindings

SimSpaceEvaluationEquation — a live-evaluated equation overlay rendered
atop a SimSpace. References an existing `EquationDefinition` row for
the LaTeX expression (built on top of the existing equation
infrastructure — same parser, same executor, same KaTeX renderer), and
adds the per-symbol value sources needed to plug simulation data into
the equation at every scrubber tick.

Three views are derived from one row:
  1. The equation in math-symbol form (uses `EquationDefinition`'s
     latexExpression as-authored).
  2. The equation in software-variable form (replaces each math symbol
     with the software variable name it's bound to, so analysts can see
     how the math maps to the code).
  3. The equation with current values substituted in, plus the final
     computed value (unit + precision come from the referenced
     SimVariable so we don't duplicate display config).

Unit + precision deliberately live on the referenced SimVariable, not
here. One source of truth: a SimVariable carries everything we know
about how to display a particular quantity.

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence)
  - simSpace.compilers.compile_2d / compile_3d (pre-evaluation during
    snapshot compile — each evaluation gets one value per recorded step
    so the viewer can scrub without backend roundtrips)
  - SimSpaceEvaluationOverlay frontend component (three-view rendering)
@see /OVERLAP_MAP.md
"""

from objectTreeDecorators import treeObject, treeObjectInit


class SimSpaceEvaluationEquation(treeObject):
    """One live-evaluated equation overlay attached to a SimSpace.

    Identity: `name` (unique across the table). Convention:
    "<sim_space_name>.<short-slug>" so rows are locatable without
    cross-referencing.
    """

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        description: str = '',
        # Which SimSpace this overlay belongs to (matches
        # SimSpaceDefinition.name).
        sim_space_ref: str = '',
        # Which EquationDefinition row provides the LaTeX expression
        # + operation type. The new field type is "an evaluation built
        # on top of an equation" — the LaTeX itself stays in
        # EquationDefinition so it's editable by the calculus tools.
        equation_ref: str = '',
        # Variable bindings, JSON-encoded. Each entry maps one symbol
        # in the equation to a runtime value source:
        #
        # [
        #   {"symbol": "m", "softwareName": "mass",
        #    "source": {"kind": "param", "name": "mass"}},
        #   {"symbol": "L", "softwareName": "L",
        #    "source": {"kind": "param", "name": "L"}},
        #   {"symbol": "\\omega", "softwareName": "omega",
        #    "source": {"kind": "simState",
        #               "class": "PendulumBobSimState", "field": "omega"}},
        #   {"symbol": "g", "softwareName": "g",
        #    "source": {"kind": "const", "value": 9.81}}
        # ]
        #
        # source.kind:
        #   "const"    — literal numeric value
        #   "param"    — reads SimulationDefinition.parameters_json[name]
        #   "simState" — reads <class>.<field> at the current scrubber step
        #                (resolved against the snapshot's pre-computed
        #                per-step row set during snapshot compile)
        variable_bindings_json: str = '[]',
        # Optional reference to a SimVariable that owns the unit +
        # precision for this equation's output (e.g. "kinetic_energy" →
        # unit "J", precision 2). When empty, the viewer renders the
        # raw number without a unit suffix.
        result_variable_ref: str = '',
        # Anchor: where the overlay attaches in the viewer.
        #   "screen" — fixed corner of the canvas (anchor_data_json
        #              shape: {"corner": "top-right"} etc.)
        #   "world"  — fixed coordinates in space (anchor_data_json
        #              shape: {"position": [x, y]} or [x, y, z])
        anchor_kind: str = 'screen',
        anchor_data_json: str = '{"corner": "top-right"}',
        # Display order — lower draws first (top of stack). Tie-broken by
        # name so the rendering is stable.
        sort_order: int = 0,
        # Toggle per overlay so the user can hide one without deleting.
        enabled: bool = True,
        manager=None,
    ):
        self.name = name
        self.description = description
        self.sim_space_ref = sim_space_ref
        self.equation_ref = equation_ref
        self.variable_bindings_json = variable_bindings_json
        self.result_variable_ref = result_variable_ref
        self.anchor_kind = anchor_kind
        self.anchor_data_json = anchor_data_json
        self.sort_order = sort_order
        self.enabled = enabled
