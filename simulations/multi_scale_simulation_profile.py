"""
@module simulations.multi_scale_simulation_profile

MultiScaleSimulationProfile — the object that NAMES a FAMILY of
multi-scale simulations and declares what its members have in common:
which scale levels exist, which stage/gate shapes recur, which
fidelity/engine ladder applies, which visualization panels recur, and
how scales couple. The two existing use-cases motivated it from
opposite directions:

  - pendulum-in-wind inlines all of this as JSON literals in
    multi_scale_seed.py (the family shape exists but nothing names it);
  - materials science spreads it across module constants
    (materialsScience.materials_basis.SCALE_LEVELS,
    materialsScience.scale_execution.ENGINE_REGISTRY) and per-material
    rows — again with no object binding the family together.

HONEST SCOPE: a profile is declarative naming + conformance validation
+ a suggestion source. It does NOT instantiate msims by codegen.
Instantiating a family member = authoring a MultiScaleSimulationDefinition
with `profile_ref` set; multi_scale_profile_conformance then reports,
slot by slot, how the msim fills (or fails to fill) the family shape —
every finding evidence-bearing, nothing auto-applied
([[knobs-and-suggestions]]).

Field shapes (all pure JSON config, editable at the object):

`scale_levels_json` — ordered levels the family spans:
    [{"key": "continuum", "label": "Continuum / FEM", "units": "µm-mm",
      "order": 1}, ...]

`stage_templates_json` — recurring stage SHAPES with named slots:
    [{"key": "precondition-search", "label": "...",
      "kind": "runToCompletion",   # matches stages_json 'kind'
      "intent": "search",          # matches stages_json 'intent'
      "required": true,
      "slots": {"simulationRef": "which space proves the precondition",
                "gate": "the no-code pass/fail SolutionDefinition",
                "derive": "gate outputs -> later-stage params"}}]

`fidelity_ladder_json` — ordered rungs mapping levels to engines:
    [{"rung": 1, "level": "continuum", "engines": ["fem.conduction"],
      "costClass": "moderate",     # cheap | moderate | expensive
      "purpose": "verification"}]  # screening | verification | evidence

`panel_roster_json` — panel kinds a family member's page recurs to:
    [{"kind": "selector", "slot": "choose the subject", "required": true}]

`coupling_shapes_json` — how scales hand values to each other:
    [{"from": "micro-conditions", "to": "macro-dynamics",
      "mechanism": "derive",       # derive | coupling
      "notes": "gate outputs become initial conditions"}]

`default_search_policy_json` — the family's default candidate/stop
knobs for search stages (deviations are conformance NOTES, not
failures).

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence)
  - simulations.multi_scale_profile_seed (the two seeded families)
  - simulations.multi_scale_profile_conformance (the checker)
  - simulations.profile_api (GET .../profile-conformance)
"""

from objectTreeDecorators import treeObject, treeObjectInit


class MultiScaleSimulationProfile(treeObject):
    """One named multi-scale simulation family (see module docstring).
    Identified by `name`."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        display_name: str = '',
        description: str = '',
        # Ordered scale levels: [{key, label, units, order}]
        scale_levels_json: str = '[]',
        # Recurring stage shapes with named slots (see module docstring).
        stage_templates_json: str = '[]',
        # Ordered fidelity rungs: [{rung, level, engines, costClass, purpose}]
        fidelity_ladder_json: str = '[]',
        # Recurring page panels: [{kind, slot, required, notes}]
        panel_roster_json: str = '[]',
        # Cross-scale handoff shapes: [{from, to, mechanism, notes}]
        coupling_shapes_json: str = '[]',
        # Family default search knobs (deviations = conformance notes).
        default_search_policy_json: str = '{}',
        enabled: bool = True,
        manager=None,
    ):
        self.name = name
        self.display_name = display_name
        self.description = description
        self.scale_levels_json = scale_levels_json
        self.stage_templates_json = stage_templates_json
        self.fidelity_ladder_json = fidelity_ladder_json
        self.panel_roster_json = panel_roster_json
        self.coupling_shapes_json = coupling_shapes_json
        self.default_search_policy_json = default_search_policy_json
        self.enabled = enabled
