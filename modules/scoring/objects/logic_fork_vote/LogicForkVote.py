"""
@module scoring.objects.logic_fork_vote.LogicForkVote

Row class LogicForkVote of the scoring module — one class per file (design §7), split
from logic_fork_vote_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class LogicForkVote(treeObject):
    """One vote over candidate LogicForkCriterion rows FOR ONE FORK."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        display_name: str = '',
        description: str = '',
        decision_procedure_name: str = '',
        fork_name: str = '',
        # Candidate LogicForkCriterion names (JSON list) — required,
        # same reasoning as GroupDisplayVote: no "group members"
        # default exists to fall back to.
        candidate_criterion_names_json: str = '[]',
        mode: str = 'sole',
        status: str = 'open',
        opens_date: str = '',
        closes_date: str = '',
        elected_criterion_name: str = '',
        elected_provenance: str = '',
        provenance_id: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.display_name = display_name
        self.description = description
        self.decision_procedure_name = decision_procedure_name
        self.fork_name = fork_name
        self.candidate_criterion_names_json = candidate_criterion_names_json
        self.mode = mode
        self.status = status
        self.opens_date = opens_date
        self.closes_date = closes_date
        self.elected_criterion_name = elected_criterion_name
        self.elected_provenance = elected_provenance
        self.provenance_id = provenance_id
        self.notes = notes
