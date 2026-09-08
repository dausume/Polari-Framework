"""
@module pspp.material_states_basis

The MaterialState DAG (plan pspp-2) — a material is one identity with
a HISTORY of durable states ('raw powder' → 'activated slurry' →
'cured solid' → branches like 'carbonated'), not one property sheet.
States are the citable subjects claims attach to; edges arrive with
MaterialProcessExecution in pspp-4 (parent_state_ids_json carries the
DAG shape meanwhile).

ProcessingStage (extensible ROWS, deliberately not an enum — ChatGPT
convergence) is orthogonal to thermodynamic_phase: a geopolymer gel is
thermodynamically condensed but occupies its own place in a process
route; a polymer melt and a curing resin are both liquids in different
processing stages.

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence)
  - pspp.custom.state_resolution (canonical resolution, invariant I1)
  - pspp.claims_basis (subject_state_key = MaterialState.name)
"""

from objectTreeDecorators import treeObject, treeObjectInit

#: The canonical state every material implicitly has (invariant I1).
CANONICAL_STATE = 'as-defined'

THERMODYNAMIC_PHASES = ('solid', 'liquid', 'gas', 'plasma', 'mixed')


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


class ProcessingStage(treeObject):
    """One processing-stage concept — extensible rows, NOT an enum, so
    each material family names its own route stages."""

    @treeObjectInit
    def __init__(
        self,
        # Kebab-case key ('activated-slurry').
        name: str = '',
        display_name: str = '',
        description: str = '',
        # The family that coined it ('geopolymer', 'wax', 'general') —
        # navigation only, any material may use any stage.
        material_family: str = 'general',
        # Typical predecessor stage ('' = route start) — a HINT for
        # pages, never a constraint (routes are data, pspp-4).
        typical_prior_stage: str = '',
        provenance_id: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.display_name = display_name
        self.description = description
        self.material_family = material_family
        self.typical_prior_stage = typical_prior_stage
        self.provenance_id = provenance_id
        self.notes = notes


_STAGE_PROVENANCE = ('pspp-2 stage vocabulary '
                     '(PSPP_MATERIALS_PLAN.md §2, ChatGPT convergence '
                     '2026-07-18)')

#: Seed stages: the geopolymer route + the wax route + generic states.
#: Editable rows — families add their own without code changes.
SEED_PROCESSING_STAGES = [
    # general
    {'name': 'raw-powder', 'display_name': 'Raw powder',
     'material_family': 'general',
     'description': 'As-received particulate feedstock.'},
    {'name': 'green-body', 'display_name': 'Green body',
     'material_family': 'general', 'typical_prior_stage': 'raw-powder',
     'description': 'Shaped but not yet consolidated/fired.'},
    {'name': 'damaged', 'display_name': 'Damaged',
     'material_family': 'general',
     'description': 'Post-service degraded state (thermal, chemical, '
                    'mechanical) — still a citable state.'},
    # geopolymer route
    {'name': 'activated-slurry', 'display_name': 'Activated slurry',
     'material_family': 'geopolymer', 'typical_prior_stage': 'raw-powder',
     'description': 'Precursor + alkali activator mixed, workable.'},
    {'name': 'reactive-suspension',
     'display_name': 'Reactive suspension',
     'material_family': 'geopolymer',
     'typical_prior_stage': 'activated-slurry',
     'description': 'Dissolution under way — species depolymerizing '
                    'into solution (book §5.6.3).'},
    {'name': 'percolating-gel', 'display_name': 'Percolating gel',
     'material_family': 'geopolymer',
     'typical_prior_stage': 'reactive-suspension',
     'description': 'Network first spans the volume — setting point.'},
    {'name': 'set-gel', 'display_name': 'Set gel',
     'material_family': 'geopolymer',
     'typical_prior_stage': 'percolating-gel',
     'description': 'Demoldable gel, curing continues.'},
    {'name': 'cured-solid', 'display_name': 'Cured solid',
     'material_family': 'geopolymer', 'typical_prior_stage': 'set-gel',
     'description': 'Cure complete to spec (e.g. 7-day sealed cure).'},
    {'name': 'heat-treated-ceramic',
     'display_name': 'Heat-treated ceramic',
     'material_family': 'geopolymer',
     'typical_prior_stage': 'cured-solid',
     'description': 'Post-cure thermal conversion toward ceramic.'},
    {'name': 'carbonated', 'display_name': 'Carbonated',
     'material_family': 'geopolymer',
     'typical_prior_stage': 'cured-solid',
     'description': 'CO2-reacted surface/bulk — a durability branch.'},
    # wax route (maps the existing waxprint world in pspp-11)
    {'name': 'wax-solid', 'display_name': 'Solid wax',
     'material_family': 'wax',
     'description': 'Below melt onset — machinable regime.'},
    {'name': 'wax-softened', 'display_name': 'Softened wax',
     'material_family': 'wax', 'typical_prior_stage': 'wax-solid',
     'description': 'Inside the melt range — smears under cutters.'},
    {'name': 'wax-melt', 'display_name': 'Wax melt',
     'material_family': 'wax', 'typical_prior_stage': 'wax-softened',
     'description': 'Fully molten inside the processing window.'},
    {'name': 'wax-superheated', 'display_name': 'Superheated wax',
     'material_family': 'wax', 'typical_prior_stage': 'wax-melt',
     'description': 'Above the no-volatiles ceiling — REFUSED by the '
                    'thermal gate, named so refusals can cite it.'},
]

for _row in SEED_PROCESSING_STAGES:
    _row.setdefault('provenance_id', _STAGE_PROVENANCE)
