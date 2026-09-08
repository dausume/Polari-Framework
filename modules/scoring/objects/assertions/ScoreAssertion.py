"""
@module scoring.objects.assertions.ScoreAssertion

Row class ScoreAssertion of the scoring module — one class per file (design §7), split
from assertions_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class ScoreAssertion(treeObject):
    """One claim binding a target (usually a policy text span) to a
    score concept/term."""

    @treeObjectInit
    def __init__(
        self,
        # kebab-case unique key ('assert-fair-wage-min-wage').
        name: str = '',
        display_name: str = '',
        # ScoreSubject this assertion is ABOUT (policies are
        # subjects). The score-bearing anchor.
        subject_name: str = '',
        # Optional objectRef into any Polari object the assertion
        # targets (a legislation row, a ruling…).
        target_ref_json: str = '',
        # Optional text span (JSON {'start','end','quote'}) — the
        # scorecard's W3C-annotation idiom generalized. The quote
        # travels so the claim stays readable without the source.
        span_json: str = '',
        # The generic intent, free text ('raises minimum wage for
        # hourly workers') — what abstraction matching reads.
        intent: str = '',
        # ASSERTION_TYPES entry.
        assertion_type: str = 'score-impact',
        # DIRECTIONS entry (score-impact/dependency only).
        direction: str = 'supports',
        # How strongly the span bears on the concept (0-1).
        strength: float = 0.5,
        # The binding — may be EMPTY (suggestions fill it): concept
        # OR term of the concept being asserted about.
        concept_name: str = '',
        term_name: str = '',
        # dependency type: the policy subject scores carry over FROM.
        depends_on_subject: str = '',
        # MediaEvidence names cited as proof (JSON list).
        evidence_names_json: str = '[]',
        # Contributor name — who is accountable for this claim.
        asserted_by: str = '',
        # STATUSES entry; move via transition_assertion (history).
        status: str = 'asserted',
        # Append-only transition log (JSON list of {'from','to','by',
        # 'note','at'}) — tamper-evident lite.
        status_history_json: str = '[]',
        provenance_id: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.display_name = display_name
        self.subject_name = subject_name
        self.target_ref_json = target_ref_json
        self.span_json = span_json
        self.intent = intent
        self.assertion_type = assertion_type
        self.direction = direction
        self.strength = strength
        self.concept_name = concept_name
        self.term_name = term_name
        self.depends_on_subject = depends_on_subject
        self.evidence_names_json = evidence_names_json
        self.asserted_by = asserted_by
        self.status = status
        self.status_history_json = status_history_json
        self.provenance_id = provenance_id
        self.notes = notes
