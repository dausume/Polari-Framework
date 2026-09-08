"""
@module scoring.objects.legislation.LegislativeVoteEvent

Row class LegislativeVoteEvent of the scoring module — one class per file (design §7), split
from legislation_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class LegislativeVoteEvent(treeObject):
    """One government vote on one piece of legislation — the roster
    (who voted yes/no) travels with the tallies."""

    @treeObjectInit
    def __init__(self, name: str = '', legislation_name: str = '',
                 chamber: str = '', occurred_at: str = '',
                 result: str = '',
                 # {'yes': n, 'no': n, 'abstain': n, 'absent': n}
                 vote_counts_json: str = '{}',
                 # THE ROSTER: {legislator_subject_name: choice}.
                 votes_json: str = '{}',
                 source_name: str = '', entry_mode: str = 'manual',
                 provenance_id: str = '',
                 notes: str = '', manager=None):
        self.name = name
        self.legislation_name = legislation_name
        self.chamber = chamber
        self.occurred_at = occurred_at
        self.result = result
        self.vote_counts_json = vote_counts_json
        self.votes_json = votes_json
        self.source_name = source_name
        self.entry_mode = entry_mode
        self.provenance_id = provenance_id
        self.notes = notes
