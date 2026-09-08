"""
@module pspp.objects.material_processes.MaterialProcessExecution

Row class MaterialProcessExecution of the pspp module — one class per file (design §7), split
from material_processes_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class MaterialProcessExecution(treeObject):
    """One run of a process — the self-documenting DAG edge: inputs,
    parameters, schedule, device, outputs, observations, evidence."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        definition_name: str = '',
        # JSON list of input MaterialState keys.
        input_state_ids_json: str = '[]',
        parameter_values_json: str = '{}',
        # JSON schedule (e.g. [{"holdC": 60, "hours": 24}]).
        schedule_json: str = '[]',
        # MaterialRelatedDevice id ('' = unrecorded).
        device_id: str = '',
        # JSON list of output MaterialState keys (MUST be empty for
        # OBSERVATIONAL executions — validate_execution enforces I2).
        output_state_ids_json: str = '[]',
        measured_observations_json: str = '{}',
        # 'planned' | 'executed' | 'refused'
        status: str = 'planned',
        provenance_id: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.definition_name = definition_name
        self.input_state_ids_json = input_state_ids_json
        self.parameter_values_json = parameter_values_json
        self.schedule_json = schedule_json
        self.device_id = device_id
        self.output_state_ids_json = output_state_ids_json
        self.measured_observations_json = measured_observations_json
        self.status = status
        self.provenance_id = provenance_id
        self.notes = notes
