"""
@module scoring.objects.system_choice_implications.SystemChoiceInForce

Row class SystemChoiceInForce of the scoring module — one class per file (design §7), split
from system_choice_implications_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class SystemChoiceInForce(treeObject):
    """Ground truth: which LogicForkCriterion is actually deployed in
    one jurisdiction, over what date range. The real-world anchor
    `compare_outcomes_by_system_choice()` groups by — separate from
    any specific vote's resolution, since real jurisdictions adopt on
    their own schedules, not in lockstep with any one vote."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        decision_procedure_name: str = '',
        fork_name: str = '',
        # Which LogicForkCriterion this jurisdiction actually uses.
        criterion_name: str = '',
        # The jurisdiction — a ScoreSubject name (e.g. a state).
        jurisdiction_subject_name: str = '',
        effective_from: str = '',
        # '' = still in force.
        effective_to: str = '',
        source: str = '',
        provenance_id: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.decision_procedure_name = decision_procedure_name
        self.fork_name = fork_name
        self.criterion_name = criterion_name
        self.jurisdiction_subject_name = jurisdiction_subject_name
        self.effective_from = effective_from
        self.effective_to = effective_to
        self.source = source
        self.provenance_id = provenance_id
        self.notes = notes
