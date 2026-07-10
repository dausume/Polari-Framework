"""
@module materialsScience.meso_model_definition

MesoModelDefinition — the MESOSCALE simulation interface (msci-26):
one configured mesoscale study (percolation MC / Brownian dynamics),
sectioned:

    System -> Sampling -> Integration -> Results

Values may be literals or component_binding BINDINGS (objectRef /
stageDerived) exactly like FEM/DFT models. `physics_ref` names the
md-* EngineModelTemplate. The last result persists ON the row.

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence)
  - materialsScience.component_binding / model_execution
  - materialsScience.l2_l3_models_seed
"""

from objectTreeDecorators import treeObject, treeObjectInit


class MesoModelDefinition(treeObject):
    """One configured mesoscale study (see module docstring)."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        display_name: str = '',
        description: str = '',
        # The EngineModelTemplate this study instantiates (meso-*).
        physics_ref: str = '',
        # {"aspectRatio": ...} or {"couplingLambda": ...,
        #  "volumeFraction": ...}
        system_json: str = '{}',
        # {"trials": ..., "iterations": ..., "seed": ...}
        sampling_json: str = '{}',
        # {"steps": ..., "dt": ..., "seed": ...}
        integration_json: str = '{}',
        last_result_json: str = '{}',
        last_executed_at: str = '',
        notes: str = '',
        enabled: bool = True,
        manager=None,
    ):
        self.name = name
        self.display_name = display_name
        self.description = description
        self.physics_ref = physics_ref
        self.system_json = system_json
        self.sampling_json = sampling_json
        self.integration_json = integration_json
        self.last_result_json = last_result_json
        self.last_executed_at = last_executed_at
        self.notes = notes
        self.enabled = enabled
