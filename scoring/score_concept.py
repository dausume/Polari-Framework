"""
@cross-cutting
@module scoring.score_concept
@tags @xc:bindings

ScoreConcept — "concepts for scores that are more complicated": a
named, weighted bundle of ScoreTerms evaluated over subjects under
required contexts (the scorecard's WorldviewBallot generalized away
from voting — a ballot is ONE source of a concept, a policy
accountability framework is another).

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence)
  - scoring.scoring_engine (the math) / scoring.scoring_api
@see /OVERLAP_MAP.md
"""

from objectTreeDecorators import treeObject, treeObjectInit

#: Supported aggregations. weighted-mean = Σ(w·v)/Σw (the scorecard
#: spreadsheet behavior; its live TS service divides by term COUNT —
#: a known divergence we do NOT copy, noted in every result).
AGGREGATIONS = ('weighted-mean',)


class ScoreConcept(treeObject):
    """One composed score definition."""

    @treeObjectInit
    def __init__(
        self,
        # kebab-case unique key ('labor-quality').
        name: str = '',
        display_name: str = '',
        description: str = '',
        # What this concept holds accountable ('policy', 'state'…) —
        # matches ScoreSubject.kind; '' = any.
        subject_kind: str = '',
        # JSON list of subject names to score ([] = every subject of
        # subject_kind).
        subject_names_json: str = '[]',
        # The weighted term bundle (JSON list):
        # [{"term": "union-participation", "weight": 5}, ...] — sign
        # comes from the term's is_positive, not the weight.
        term_weights_json: str = '[]',
        # Contexts every evaluation must hold under (JSON name list,
        # e.g. ["year-2022"]); subject-specific contexts (their state,
        # their district) come from the values themselves.
        required_context_names_json: str = '[]',
        # AGGREGATIONS entry.
        aggregation: str = 'weighted-mean',
        # Scale scores to the best subject = 100 (the scorecard's
        # levelization) — an explicit knob, not silent behavior.
        levelize: bool = True,
        provenance_id: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.display_name = display_name
        self.description = description
        self.subject_kind = subject_kind
        self.subject_names_json = subject_names_json
        self.term_weights_json = term_weights_json
        self.required_context_names_json = required_context_names_json
        self.aggregation = aggregation
        self.levelize = levelize
        self.provenance_id = provenance_id
        self.notes = notes
