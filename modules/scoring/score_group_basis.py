"""
@cross-cutting
@module scoring.score_group_basis
@tags @xc:bindings

ScoreGroup — a named collection of member WORLDVIEWS (each member's
definition of a scored idea IS a ScoreConcept: their term weights +
stances). Groups are what agreement aggregation runs over (Dustin
2026-07-08: "(a) All groups - Consensus, (b) Political Groups,
(c) Professional Groups").

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence)
  - scoring.custom.group_aggregation / scoring.scoring_api
@see /OVERLAP_MAP.md
"""

from objectTreeDecorators import treeObject, treeObjectInit

#: Group kinds. 'all-groups consensus' is NOT a row — the engine
#: aggregates the union of every group's members on demand.
GROUP_TYPES = ('political', 'professional', 'civic', 'custom')


class ScoreGroup(treeObject):
    """One group of member worldview concepts."""

    @treeObjectInit
    def __init__(
        self,
        # kebab-case unique key ('labor-economists').
        name: str = '',
        display_name: str = '',
        # GROUP_TYPES entry.
        group_type: str = 'custom',
        # JSON list of ScoreConcept names — each member's definition.
        member_concept_names_json: str = '[]',
        # JSON list of ScoreSubject names — SUBJECT cohorts (scr-6:
        # a party's politicians, a committee) for cohort reads over
        # votes/scores. A group may hold worldview members, subject
        # members, or both.
        member_subject_names_json: str = '[]',
        # Contributor names belonging to this group (JSON list) —
        # scr-16: bias analysis reads the group's assertions/votes/
        # citations through its member contributors.
        member_contributor_names_json: str = '[]',
        # Optional per-member-worldview weights (JSON {name: weight})
        # — scr-8: vote-DERIVED via election apply, or hand-set;
        # empty = every member counts equally (scr-3 behavior).
        member_weights_json: str = '',
        # Where the weights came from ('vote-derived from election X
        # (ranked-condorcet, 3 ballots)') — weights without lineage
        # are just opinions.
        weights_provenance: str = '',
        description: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.display_name = display_name
        self.group_type = group_type
        self.member_concept_names_json = member_concept_names_json
        self.member_subject_names_json = member_subject_names_json
        self.member_contributor_names_json = member_contributor_names_json
        self.member_weights_json = member_weights_json
        self.weights_provenance = weights_provenance
        self.description = description
        self.notes = notes
