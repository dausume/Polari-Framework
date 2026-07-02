"""
@cross-cutting
@module simulations.initial_condition_interface_definition
@tags @xc:bindings

InitialConditionInterfaceDefinition — a CONFIGURED initial-condition-
setting view: a purpose-built interface (e.g. "pick the bob's material")
that maps user selections onto a simulation's initial conditions and
parameter overrides, with the existing debounced validator firing on
every selection (the frontend panel reuses the run IC editor's
validate-initial-conditions flow — same code path that gates step 0).

`interface_kind`:
  * 'choicePreset' — a labeled choice list; each choice carries a bundle
    of IC field values and/or parameter overrides. THE material picker.
  * 'fieldEditor'  — the raw per-field editor scoped to configured
    fields (a thin filter over the existing IC editor).

`config_json` for choicePreset:
    {
      "label": "Bob material",
      "choices": [
        {"key": "ice", "label": "Ice ball",
         "setParams": {"mass": 0.48, "bob_radius": 0.05},
         "setFields": {"<ClassName>": {"<field>": <value>}}},
        ...
      ],
      "derivedParams": {"bob_cross_section": "pi * bob_radius ** 2", ...}
    }
`derivedParams` are recomputed from the chosen bundle before validation
so downstream physics (e.g. wind drag reading bob_cross_section) stays
consistent with the selection.

Milestone-B bridge (deliberate): when the material space lands, choices
stop being hand-authored and are GENERATED from Material objects gated
by the condensation-precondition simulation — this definition's shape
stays identical; only the choice source changes.

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence)
  - simulations.multi_scale_seed (the bob-material demo picker)
  - frontend msim-ic-panel
@see /OVERLAP_MAP.md
"""

from objectTreeDecorators import treeObject, treeObjectInit


class InitialConditionInterfaceDefinition(treeObject):
    """One configured IC-setting interface. Identified by `name`."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        description: str = '',
        # The simulation whose initial conditions this interface sets.
        target_simulation_ref: str = '',
        # The *SimState class the field bundle primarily targets.
        target_class_name: str = '',
        # 'choicePreset' | 'fieldEditor' (see module docstring).
        interface_kind: str = 'choicePreset',
        # Kind-specific configuration (choices, field scoping, labels).
        config_json: str = '{}',
        enabled: bool = True,
        manager=None,
    ):
        self.name = name
        self.description = description
        self.target_simulation_ref = target_simulation_ref
        self.target_class_name = target_class_name
        self.interface_kind = interface_kind
        self.config_json = config_json
        self.enabled = enabled
