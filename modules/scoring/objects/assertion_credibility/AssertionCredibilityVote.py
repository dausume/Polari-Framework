"""
@module scoring.objects.assertion_credibility.AssertionCredibilityVote

Row class AssertionCredibilityVote of the scoring module — one class per file (design §7), split
from assertion_credibility_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class AssertionCredibilityVote(treeObject):
    """One credibility vote on one assertion — personal, or a
    group's official stance cast by a member. Rows are immutable;
    a re-vote is a NEW row and the reading takes each unit's latest
    (superseded rows stay visible — that IS the history)."""

    @treeObjectInit
    def __init__(
        self,
        # kebab-case unique key ('cred-assert-x--housing-guild-2').
        name: str = '',
        assertion_name: str = '',
        # Contributor name — every vote is accountable to a person.
        voter: str = '',
        # '' = personal vote; a ScoreGroup name = the group's
        # official stance (the GROUP is the counted unit).
        on_behalf_of_group: str = '',
        # CREDIBILITY_LEVELS entry.
        credibility: str = 'questionable',
        rationale: str = '',
        cited_evidence_url: str = '',
        cast_at: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.assertion_name = assertion_name
        self.voter = voter
        self.on_behalf_of_group = on_behalf_of_group
        self.credibility = credibility
        self.rationale = rationale
        self.cited_evidence_url = cited_evidence_url
        self.cast_at = cast_at
        self.notes = notes
