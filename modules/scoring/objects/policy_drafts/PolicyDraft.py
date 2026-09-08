"""
@module scoring.objects.policy_drafts.PolicyDraft

Row class PolicyDraft of the scoring module — one class per file (design §7), split
from policy_drafts_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class PolicyDraft(treeObject):
    """One developing policy — scoreable BEFORE it becomes law."""

    @treeObjectInit
    def __init__(self, name: str = '', display_name: str = '',
                 description: str = '',
                 # DRAFT_STATUSES entry; move via transition_draft.
                 status: str = 'draft',
                 drafted_by: str = '',
                 sponsoring_group: str = '',
                 jurisdiction_subject_name: str = '',
                 text_url: str = '',
                 # '' until enacted — then the real policy
                 # ScoreSubject this draft became.
                 enacted_policy_subject_name: str = '',
                 # Append-only [{'from','to','by','note','at'}].
                 history_json: str = '[]',
                 notes: str = '', manager=None):
        self.name = name
        self.display_name = display_name
        self.description = description
        self.status = status
        self.drafted_by = drafted_by
        self.sponsoring_group = sponsoring_group
        self.jurisdiction_subject_name = jurisdiction_subject_name
        self.text_url = text_url
        self.enacted_policy_subject_name = enacted_policy_subject_name
        self.history_json = history_json
        self.notes = notes
