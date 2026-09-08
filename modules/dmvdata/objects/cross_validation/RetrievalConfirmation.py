"""
@module dmvdata.objects.cross_validation.RetrievalConfirmation

Row class RetrievalConfirmation of the dmvdata module — one class per file (design §7), split
from cross_validation_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class RetrievalConfirmation(treeObject):
    """One independent re-pull compared against a recorded
    retrieval — the cross-validation unit."""

    @treeObjectInit
    def __init__(self, name: str = '',
                 subject_retrieval_name: str = '',
                 confirming_retrieval_name: str = '',
                 confirmed_by: str = '',
                 confirmed_by_group: str = '',
                 compared_at: str = '',
                 rows_compared: int = 0, matches: int = 0,
                 mismatches: int = 0,
                 mismatch_detail_json: str = '[]',
                 verdict: str = '', notes: str = '',
                 manager=None):
        self.name = name
        self.subject_retrieval_name = subject_retrieval_name
        self.confirming_retrieval_name = confirming_retrieval_name
        self.confirmed_by = confirmed_by
        self.confirmed_by_group = confirmed_by_group
        self.compared_at = compared_at
        self.rows_compared = rows_compared
        self.matches = matches
        self.mismatches = mismatches
        self.mismatch_detail_json = mismatch_detail_json
        self.verdict = verdict
        self.notes = notes
