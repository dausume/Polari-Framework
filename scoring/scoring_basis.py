"""
@cross-cutting
@module scoring.scoring_basis
@tags @xc:bindings

Context-based scoring BASIS — the Political Scorecard's proven object
graph (Term → ContextualizedTerm → TermContext → weighted aggregation)
generalized into Polari as first-class objects, so scores and score
concepts can be built over ARBITRARY data (Dustin 2026-07-07: "use
arbitrary data in the political scorecard, and plug it into polari …
an accountability framework for policies").

Four data classes:
  ScoreTerm           — one 0-1-normalizable metric concept ("Union
                        Participation"): what it measures, its unit,
                        whether higher is better, provenance.
  ScoreContext        — one scenario slice (location/timeframe/
                        economic/demographic/custom) with a specificity
                        rank so the engine prefers the most specific
                        value available (scorecard idiom: City > State
                        > Country > Region).
  ScoreSubject        — the entity being scored (policy, politician,
                        state, material — anything), optionally
                        anchored to a live Polari object.
  ContextualizedValue — one term measured for one subject under N
                        contexts: raw value + explicit normalization
                        spec (never hidden math), OR an objectRef
                        binding into any Polari object (the
                        arbitrary-data seam, same binding contract as
                        the engine models).

Aggregation definitions live in score_concept.py; the math in
scoring_engine.py.

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence)
  - scoring.scoring_engine / scoring.scoring_api
@see /OVERLAP_MAP.md
"""

from objectTreeDecorators import treeObject, treeObjectInit

#: ValueMetadata.type vocabulary, mirrored from the scorecard.
VALUE_TYPES = ('percentage', 'currency', 'count', 'rate', 'index',
               'ratio', 'score', 'custom')

#: Context kinds + base specificity, mirroring the scorecard's
#: calculateContextSpecificity (City 8 > State 4 > demographic/economic
#: 3 > Country 2 > Region 1); timeframe adds granularity at match time.
CONTEXT_TYPES = {
    'location': 4,      # granularity_json refines: city 8, state 4…
    'timeframe': 5,
    'economic': 3,
    'demographic': 3,
    'custom': 1,
}

LOCATION_SPECIFICITY = {'city': 8, 'state': 4, 'country': 2,
                        'region': 1}


class ScoreTerm(treeObject):
    """One scoreable metric concept — 'a value between 0 and 1' once
    normalized (scorecard Term + ValueMetadata, one row)."""

    @treeObjectInit
    def __init__(
        self,
        # kebab-case unique key ('union-participation').
        name: str = '',
        display_name: str = '',
        description: str = '',
        category: str = '',
        # VALUE_TYPES entry.
        value_type: str = 'custom',
        unit: str = '',
        # Higher raw value = better (False → engine INVERTS at
        # normalization, the scorecard's anti-competitive idiom).
        is_positive: bool = True,
        # Default normalization spec (JSON): {"method": "min-max",
        # "min": ..., "max": ...} or {"method": "min-max-auto"} to
        # derive the range from the live value set. Explicit — the
        # breakdown always shows which spec produced a normalized
        # value.
        normalization_json: str = '{"method": "min-max-auto"}',
        # Loose links to related/opposing terms (JSON name lists).
        equivalent_terms_json: str = '[]',
        competitive_terms_json: str = '[]',
        source: str = '',
        provenance_id: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.display_name = display_name
        self.description = description
        self.category = category
        self.value_type = value_type
        self.unit = unit
        self.is_positive = is_positive
        self.normalization_json = normalization_json
        self.equivalent_terms_json = equivalent_terms_json
        self.competitive_terms_json = competitive_terms_json
        self.source = source
        self.provenance_id = provenance_id
        self.notes = notes


class ScoreContext(treeObject):
    """One scenario slice a value can be measured under."""

    @treeObjectInit
    def __init__(
        self,
        # kebab-case unique key ('state-california', 'year-2022').
        name: str = '',
        display_name: str = '',
        # CONTEXT_TYPES key.
        context_type: str = 'custom',
        # Type-specific payload (JSON): location {'granularity':
        # 'state', 'state': 'California'}; timeframe {'start': ...,
        # 'end': ...}; custom anything.
        value_json: str = '{}',
        # Optional parent context name (hierarchy: city → state →
        # country), so specificity chains are walkable.
        parent_name: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.display_name = display_name
        self.context_type = context_type
        self.value_json = value_json
        self.parent_name = parent_name
        self.notes = notes


class ScoreSubject(treeObject):
    """The entity being scored — policy, politician, jurisdiction,
    material, proposal … anything with an identity."""

    @treeObjectInit
    def __init__(
        self,
        # kebab-case unique key ('california', 'policy-min-wage-2024').
        name: str = '',
        display_name: str = '',
        # Free kind ('state', 'policy', 'politician', 'material'…).
        kind: str = '',
        # Optional anchor into a live Polari object (JSON objectRef
        # {'kind': 'objectRef', 'className': ..., 'name': ...}) so a
        # subject IS a real object, not a label (object-coherence).
        object_ref_json: str = '',
        description: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.display_name = display_name
        self.kind = kind
        self.object_ref_json = object_ref_json
        self.description = description
        self.notes = notes


class ContextualizedValue(treeObject):
    """One term, measured for one subject, under N contexts — the
    scorecard's ContextualizedTerm with the pre/post split kept
    EXPLICIT and the data source pluggable."""

    @treeObjectInit
    def __init__(
        self,
        # unique key ('union-participation@california-2022').
        name: str = '',
        term_name: str = '',
        subject_name: str = '',
        # JSON list of ScoreContext names this value holds under.
        context_names_json: str = '[]',
        # The raw measured value, in the term's real units. None/'' +
        # a data_ref → resolved live at scoring time.
        pre_normalized_value: float = None,
        # OPTIONAL objectRef binding (JSON, component_binding contract:
        # {'kind': 'objectRef', 'className', 'name', 'path'}) pulling
        # the raw value from ANY Polari object — simulation results,
        # material rows, dataset rows. THE arbitrary-data seam.
        data_ref_json: str = '',
        # Optional per-value normalization override (same spec shape
        # as ScoreTerm.normalization_json; '' = use the term's).
        normalization_json: str = '',
        source: str = '',
        provenance_id: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.term_name = term_name
        self.subject_name = subject_name
        self.context_names_json = context_names_json
        self.pre_normalized_value = pre_normalized_value
        self.data_ref_json = data_ref_json
        self.normalization_json = normalization_json
        self.source = source
        self.provenance_id = provenance_id
        self.notes = notes
