"""
@module materialsScience.engine_model_template

EngineModelTemplate — the CATALOG of engine-backed physics/calculations:
which FEM studies and DFT calculation types exist, the typed parameter
slots each one takes (grouped by the DOMAIN SECTIONS practitioners
expect), what it outputs, what it costs, and which capability layer
must be reachable for it to execute at all.

The section vocabularies mirror how existing tools structure these
model families (Dustin's directive — FEM and DFT are complicated
families; the interface should look like the tools people know):

  FEM (COMSOL physics interfaces / FreeCAD FEM / SfePy problem
  descriptions):  domain -> materials -> boundaryConditions ->
                  sourceTerms -> mesh -> solver
  DFT (Quantum ESPRESSO namelists / ASE calculators / pymatgen input
  sets):          structure -> method -> accuracy -> calculation

A template row is pure declaration; a configured problem lives in a
FEMModelDefinition or DFTModelDefinition row referencing the template.
Today's engines fill a SUBSET of each section honestly — anything a
section offers that the engine cannot do yet refuses naming the gap
([[knobs-and-suggestions]]); new physics later = a new template row +
engine function, no interface change.

`parameter_schema_json` — the typed slots:
    [{"section": "materials", "key": "matrixK", "type": "number",
      "unit": "W/m·K", "required": true, "min": 1e-9,
      "description": "matrix-phase thermal conductivity"}, ...]
`section_map_json` — where each slot's value LIVES inside the model
definition's section JSON (dotted path, list indices numeric):
    {"matrixK": "materials.matrix.thermalConductivity", ...}
`outputs_json` — [{key, type, unit, description}] from the engine's
verified return shape.
`capability_requirements_json` — dotted capability() layers that must
report available: ["fem"] | ["dft.molecularLayer"] |
["dft.structureLayer"] | ["dft.executionLayer"].

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence)
  - materialsScience.engine_model_seed (the 5 catalog rows)
  - materialsScience.component_binding / model_execution
  - materialsScience.engine_model_api
"""

from objectTreeDecorators import treeObject, treeObjectInit


class EngineModelTemplate(treeObject):
    """One engine-backed physics/calculation catalog row (see module
    docstring). Identified by `name`."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        display_name: str = '',
        description: str = '',
        engine_kind: str = '',                 # 'fem' | 'dft'
        engine_key: str = '',                  # ENGINE_REGISTRY key
        parameter_schema_json: str = '[]',
        section_map_json: str = '{}',
        outputs_json: str = '[]',
        cost_class: str = 'moderate',          # cheap|moderate|expensive
        capability_requirements_json: str = '[]',
        notes: str = '',
        enabled: bool = True,
        manager=None,
    ):
        self.name = name
        self.display_name = display_name
        self.description = description
        self.engine_kind = engine_kind
        self.engine_key = engine_key
        self.parameter_schema_json = parameter_schema_json
        self.section_map_json = section_map_json
        self.outputs_json = outputs_json
        self.cost_class = cost_class
        self.capability_requirements_json = capability_requirements_json
        self.notes = notes
        self.enabled = enabled
