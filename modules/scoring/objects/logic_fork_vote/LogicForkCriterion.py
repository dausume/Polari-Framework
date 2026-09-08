"""
@module scoring.objects.logic_fork_vote.LogicForkCriterion

Row class LogicForkCriterion of the scoring module — one class per file (design §7), split
from logic_fork_vote_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class LogicForkCriterion(treeObject):
    """One proposed criterion for ONE named fork inside ONE named
    decision procedure — a candidate in a LogicForkVote."""

    @treeObjectInit
    def __init__(
        self,
        # kebab-case unique key ('reform-durability-likelihood').
        name: str = '',
        display_name: str = '',
        # The actual criterion text — what this fork would test if
        # this criterion won ("Likelihood that behavioral/
        # psychological reform durably holds for the remainder of the
        # individual's life, given documented context...").
        description: str = '',
        # Which decision procedure this fork belongs to (a human-
        # readable identifier, e.g. 'repeat-offense-sentencing-
        # framework' — NOT required to be a real SolutionDefinition
        # name, since the no-code graph link is a documented follow-
        # up, not built here).
        decision_procedure_name: str = '',
        # Which fork WITHIN that procedure this criterion is FOR
        # (e.g. 'recidivism-risk-fork') — two criteria only compete
        # against each other if they name the same fork.
        fork_name: str = '',
        # Whether this is the incumbent/baseline criterion currently
        # in use at this fork (True for exactly one criterion per
        # fork, by convention — not DB-enforced, an honest label not
        # a constraint).
        is_current_default: bool = False,
        proposed_by: str = '',
        provenance_id: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.display_name = display_name
        self.description = description
        self.decision_procedure_name = decision_procedure_name
        self.fork_name = fork_name
        self.is_current_default = is_current_default
        self.proposed_by = proposed_by
        self.provenance_id = provenance_id
        self.notes = notes
