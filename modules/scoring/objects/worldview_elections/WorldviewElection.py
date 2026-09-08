"""
@module scoring.objects.worldview_elections.WorldviewElection

Row class WorldviewElection of the scoring module — one class per file (design §7), split
from worldview_elections_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class WorldviewElection(treeObject):
    """One election over candidate worldview concepts for a group."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        display_name: str = '',
        description: str = '',
        # The ScoreGroup whose member weights this election derives.
        group_name: str = '',
        # Candidate ScoreConcept names (JSON list); [] = the group's
        # member worldviews.
        candidate_concept_names_json: str = '[]',
        # ELECTION_MODES entry.
        mode: str = 'approval',
        # ELECTION_STATUSES entry — apply requires 'closed'.
        status: str = 'open',
        opens_date: str = '',
        closes_date: str = '',
        provenance_id: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.display_name = display_name
        self.description = description
        self.group_name = group_name
        self.candidate_concept_names_json = candidate_concept_names_json
        self.mode = mode
        self.status = status
        self.opens_date = opens_date
        self.closes_date = closes_date
        self.provenance_id = provenance_id
        self.notes = notes
