"""
@module scoring.objects.data_gathering.StepCredibilityAssertion

Row class StepCredibilityAssertion of the scoring module — one class per file (design §7), split
from data_gathering_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class StepCredibilityAssertion(treeObject):
    """One party's claim that one STEP of a gathering procedure adds
    or subtracts credibility, with the reason required. Status stays
    'asserted' here — validity votes adjudicate, never this row."""

    @treeObjectInit
    def __init__(self, name: str = '',
                 gathering_solution_name: str = '',
                 step_id: str = '',
                 direction: str = 'adds',
                 magnitude_note: str = '',
                 reason: str = '',
                 asserted_by: str = '',
                 on_behalf_of_group: str = '',
                 evidence_url: str = '',
                 status: str = 'asserted',
                 notes: str = '', manager=None):
        self.name = name
        self.gathering_solution_name = gathering_solution_name
        self.step_id = step_id
        self.direction = direction
        self.magnitude_note = magnitude_note
        self.reason = reason
        self.asserted_by = asserted_by
        self.on_behalf_of_group = on_behalf_of_group
        self.evidence_url = evidence_url
        self.status = status
        self.notes = notes
