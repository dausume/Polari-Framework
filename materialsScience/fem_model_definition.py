"""
@module materialsScience.fem_model_definition

FEMModelDefinition — the FEM-SPECIFIC simulation interface: one
configured finite-element problem, sectioned the way FEM tools
structure them (COMSOL physics interfaces, FreeCAD FEM, SfePy problem
descriptions):

    Domain/Geometry -> Materials (per region) -> Boundary Conditions
    -> Source terms -> Mesh -> Solver -> Results

Every VALUE inside the section JSON may be a plain literal or a
BINDING (resolved by component_binding.resolve_model):
    {"kind": "value", "value": 0.25}
  | {"kind": "objectRef", "className": "MaterialScaleDefinition",
     "name": "beeswax-carnauba-blend@L1",
     "path": "parameters_json.inputs.matrixK"}      # reads the LIVE row
  | {"kind": "stageDerived", "stage": "<stageKey>", "key": "..."}

`physics_ref` names the EngineModelTemplate (fem-* catalog row) — the
physics/study this problem instantiates. Sections the current engines
cannot honor (a non-unit-square domain, a Neumann boundary, solver
knobs) validate as honest refusals naming the gap — the sections exist
so the interface is truthful about where those choices will live.

The last execution's result persists ON the row (object coherence).

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence)
  - materialsScience.component_binding / model_execution
  - materialsScience.engine_model_seed ('wax-thermal-continuum')
  - the msim engineModel stage (msci-16) + the FEM config UI (msci-17)
"""

from objectTreeDecorators import treeObject, treeObjectInit


class FEMModelDefinition(treeObject):
    """One configured FEM problem (see module docstring). Identified
    by `name`."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        display_name: str = '',
        description: str = '',
        # The EngineModelTemplate this problem instantiates (fem-*).
        physics_ref: str = '',
        # Geometry: {"shape": "unit-square",
        #            "inclusion": {"shape": "circle",
        #                          "volumeFraction": <binding|number>}}
        domain_json: str = '{}',
        # Per-region material properties (bindings welcome):
        # {"matrix": {"thermalConductivity": ...},
        #  "inclusion": {"thermalConductivity": ...}}   (homogenization)
        # {"domain": {"thermalConductivity": ...}}      (conduction)
        materials_json: str = '{}',
        # [{"boundary": "all", "type": "dirichlet", "value": 0}] — the
        # engines' fixed set today; other types validate as refusals.
        boundary_conditions_json: str = '[]',
        # {"heatSource": <binding|number>}
        source_terms_json: str = '{}',
        # {"refine": 4}
        mesh_json: str = '{}',
        # v1: engine defaults — the section exists so solver knobs have
        # an honest home when engines grow them.
        solver_json: str = '{}',
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
        self.domain_json = domain_json
        self.materials_json = materials_json
        self.boundary_conditions_json = boundary_conditions_json
        self.source_terms_json = source_terms_json
        self.mesh_json = mesh_json
        self.solver_json = solver_json
        self.last_result_json = last_result_json
        self.last_executed_at = last_executed_at
        self.notes = notes
        self.enabled = enabled
