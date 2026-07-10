"""
@module materialsScience.md_model_definition

MDModelDefinition — the MD-SPECIFIC simulation interface (msci-26):
one configured molecular-dynamics run, sectioned the way MD tools
structure their decks (LAMMPS input / GROMACS .mdp / HOOMD scripts):

    System -> Thermodynamic State -> Integration -> Results

Values may be literals or component_binding BINDINGS (objectRef /
stageDerived) exactly like FEM/DFT models. `physics_ref` names the
md-* EngineModelTemplate. The last result persists ON the row.

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence)
  - materialsScience.component_binding / model_execution
  - materialsScience.l2_l3_models_seed
"""

from objectTreeDecorators import treeObject, treeObjectInit


class MDModelDefinition(treeObject):
    """One configured MD run (see module docstring)."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        display_name: str = '',
        description: str = '',
        # The EngineModelTemplate this run instantiates (md-*).
        physics_ref: str = '',
        # {"nParticles": ...} or {"chainLength": ..., "nChains": ...}
        system_json: str = '{}',
        # {"density": ..., "temperature": ...}
        thermodynamic_state_json: str = '{}',
        # {"steps": ..., "equilibration": ..., "dt": ...,
        #  "thermostat": ..., "seed": ...}
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
        self.thermodynamic_state_json = thermodynamic_state_json
        self.integration_json = integration_json
        self.last_result_json = last_result_json
        self.last_executed_at = last_executed_at
        self.notes = notes
        self.enabled = enabled
