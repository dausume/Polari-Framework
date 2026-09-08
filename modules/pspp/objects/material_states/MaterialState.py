"""
@module pspp.objects.material_states.MaterialState

Row class MaterialState of the pspp module — one class per file (design §7), split
from material_states_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class MaterialState(treeObject):
    """One durable point in a material's history — the citable subject
    structure and claims attach to. The canonical '<material>#as-defined'
    state is IMPLICIT until something writes to it (sync-on-need, like
    tech-tree edges): absence of a row is not absence of the state."""

    @treeObjectInit
    def __init__(
        self,
        # Unique key: '<material>#<state>' ('metakaolin-gp#7-day-cure').
        name: str = '',
        # MaterialsScienceMaterial.name this state belongs to.
        material_name: str = '',
        # The state's short name ('as-defined', '7-day-cure').
        state_name: str = '',
        is_canonical: bool = False,
        # ProcessingStage.name ('' = not yet staged — honest absence).
        processing_stage: str = '',
        # One of THERMODYNAMIC_PHASES ('' = unknown).
        thermodynamic_phase: str = '',
        # What the material IS here (JSON: fractions, oxide ratios…).
        composition_snapshot_json: str = '{}',
        # The environment it sits in (JSON: T, RH, immersion…).
        environmental_snapshot_json: str = '{}',
        # DAG shape: JSON list of parent MaterialState.name keys
        # (edges become MaterialProcessExecution rows in pspp-4).
        parent_state_ids_json: str = '[]',
        # The TRANSFORMATIVE execution that produced this state
        # ('' until pspp-4 lands executions).
        producing_execution_id: str = '',
        # 'unvalidated' | 'measurement' | 'cross-validated'
        validation_status: str = 'unvalidated',
        provenance_id: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.material_name = material_name
        self.state_name = state_name
        self.is_canonical = is_canonical
        self.processing_stage = processing_stage
        self.thermodynamic_phase = thermodynamic_phase
        self.composition_snapshot_json = composition_snapshot_json
        self.environmental_snapshot_json = environmental_snapshot_json
        self.parent_state_ids_json = parent_state_ids_json
        self.producing_execution_id = producing_execution_id
        self.validation_status = validation_status
        self.provenance_id = provenance_id
        self.notes = notes
