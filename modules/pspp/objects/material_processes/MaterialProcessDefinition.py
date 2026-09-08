"""
@module pspp.objects.material_processes.MaterialProcessDefinition

Row class MaterialProcessDefinition of the pspp module — one class per file (design §7), split
from material_processes_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class MaterialProcessDefinition(treeObject):
    """One process concept — what it accepts, what it changes."""

    @treeObjectInit
    def __init__(
        self,
        # Kebab-case key ('sealed-cure', 'heating-microwave').
        name: str = '',
        display_name: str = '',
        description: str = '',
        # Vocabulary grouping ('mixing', 'heating', 'crystallization').
        process_type: str = '',
        # Invariant I2: declared, never inferred.
        execution_effect: str = 'TRANSFORMATIVE',
        # '' unless a heating variant — one of ENERGY_DEPOSITION_MODELS
        # (kinetics differ; chemistry does not).
        energy_deposition_model: str = '',
        # Family that coined it ('general' = cross-family).
        material_family: str = 'general',
        # JSON admissibility constraints, e.g.
        # {"thermal_window_components": ["beeswax"],
        #  "max_schedule_temperature_c": 180}.
        accepted_input_constraints_json: str = '{}',
        # JSON schema-ish dict of expected parameter keys.
        parameter_schema_json: str = '{}',
        # Engines that execute the transformation (ENGINE_REGISTRY
        # keys / model definitions) — '' rows are vocabulary-only.
        transformation_engine_refs_json: str = '[]',
        # What the output state(s) look like (stage, expected
        # structure deltas) — documentation for the edge.
        output_state_schema_json: str = '{}',
        provenance_id: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.display_name = display_name
        self.description = description
        self.process_type = process_type
        self.execution_effect = execution_effect
        self.energy_deposition_model = energy_deposition_model
        self.material_family = material_family
        self.accepted_input_constraints_json = \
            accepted_input_constraints_json
        self.parameter_schema_json = parameter_schema_json
        self.transformation_engine_refs_json = \
            transformation_engine_refs_json
        self.output_state_schema_json = output_state_schema_json
        self.provenance_id = provenance_id
        self.notes = notes
