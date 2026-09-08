"""
@module scoring.objects.court_case.CourtCase

Row class CourtCase of the scoring module — one class per file (design §7), split
from court_case_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit
from scoring.objects.court_case._shared import CASE_IN_PROGRESS

class CourtCase(treeObject):
    """One case moving through a decision procedure — the persistent
    state BETWEEN fork-graph executions."""

    @treeObjectInit
    def __init__(self, name: str = '',
                 decision_procedure_name: str = '',
                 current_fork: str = '',
                 # 'in-progress' until an edge routes to a terminal;
                 # then the terminal label (e.g. 'ACQUITTAL').
                 status: str = CASE_IN_PROGRESS,
                 # The accumulated flat fact bag (ad hoc dict — the
                 # engine imposes no schema on it; verified).
                 context_json: str = '{}',
                 # Append-only audit trail: [{fork, criterion,
                 # determination, outcome, next, at}, ...]
                 execution_log_json: str = '[]',
                 adjudicator_type: str = 'judge',  # 'judge' | 'jury'
                 adjudicator_name: str = '',
                 jurisdiction_subject_name: str = '',
                 provenance_id: str = '', notes: str = '',
                 manager=None):
        self.name = name
        self.decision_procedure_name = decision_procedure_name
        self.current_fork = current_fork
        self.status = status
        self.context_json = context_json
        self.execution_log_json = execution_log_json
        self.adjudicator_type = adjudicator_type
        self.adjudicator_name = adjudicator_name
        self.jurisdiction_subject_name = jurisdiction_subject_name
        self.provenance_id = provenance_id
        self.notes = notes
