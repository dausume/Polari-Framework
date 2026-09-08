"""
@module scoring.objects.term_proofs.TermProof

Row class TermProof of the scoring module — one class per file (design §7), split
from term_proofs_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class TermProof(treeObject):
    """One structured, re-runnable demonstration backing a term
    claim — accepted or rejected DEMOCRATICALLY, per context scope."""

    @treeObjectInit
    def __init__(self, name: str = '', proof_kind: str = '',
                 claim: str = '', subject_term: str = '',
                 comparison_term: str = '',
                 for_concept_name: str = '',
                 # ScoreContext names the proof claims validity for —
                 # acceptance is PER SCOPE, never silently wider.
                 context_scope_json: str = '[]',
                 # Ordered steps: {kind: 'reading'|'computation'|
                 # 'comparison', description, inputs: [value names or
                 # '$<stepIndex>' refs], operation?, threshold?,
                 # result}. Re-runnable by rerun_demonstration.
                 demonstration_json: str = '[]',
                 # DataManipulationPattern name, for
                 # misleading-contextualization proofs ('' otherwise).
                 manipulation_pattern: str = '',
                 depends_on_json: str = '[]',
                 status: str = 'draft',
                 # Append-only trail (the tamper-evidence idiom).
                 history_json: str = '[]',
                 proposed_by: str = '',
                 on_behalf_of_group: str = '',
                 notes: str = '', manager=None):
        self.name = name
        self.proof_kind = proof_kind
        self.claim = claim
        self.subject_term = subject_term
        self.comparison_term = comparison_term
        self.for_concept_name = for_concept_name
        self.context_scope_json = context_scope_json
        self.demonstration_json = demonstration_json
        self.manipulation_pattern = manipulation_pattern
        self.depends_on_json = depends_on_json
        self.status = status
        self.history_json = history_json
        self.proposed_by = proposed_by
        self.on_behalf_of_group = on_behalf_of_group
        self.notes = notes
