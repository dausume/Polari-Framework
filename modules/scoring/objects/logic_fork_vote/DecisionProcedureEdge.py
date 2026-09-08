"""
@module scoring.objects.logic_fork_vote.DecisionProcedureEdge

Row class DecisionProcedureEdge of the scoring module — one class per file (design §7), split
from logic_fork_vote_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class DecisionProcedureEdge(treeObject):
    """One connection in a decision procedure's GRAPH — 'after fork X
    resolves as [outcome], go to fork Y (or a terminal outcome)'.
    Added 2026-07-14 (Dustin: "flush out a more complete logic
    graph... as a basis for going forward") — makes the procedure an
    actual connected graph, not a set of isolated forks. Same honest
    scope limit as the rest of this module: this is a READ model for
    people to understand procedure flow, not an executable graph —
    it does not drive Polari's no-code SolutionExecutionEngine."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        decision_procedure_name: str = '',
        # '' means this edge starts the procedure (no predecessor fork).
        from_fork: str = '',
        # Which outcome of from_fork this edge follows (e.g.
        # 'consent-not-established') — '' only valid when from_fork
        # is also '' (the start edge).
        from_outcome: str = '',
        # Next fork name, OR '' if this edge leads to a terminal.
        to_fork: str = '',
        # A terminal outcome label (e.g. 'ACQUITTAL',
        # 'SENTENCE_IMPOSED') — only meaningful when to_fork is ''.
        to_terminal: str = '',
        description: str = '',
        manager=None,
    ):
        self.name = name
        self.decision_procedure_name = decision_procedure_name
        self.from_fork = from_fork
        self.from_outcome = from_outcome
        self.to_fork = to_fork
        self.to_terminal = to_terminal
        self.description = description
