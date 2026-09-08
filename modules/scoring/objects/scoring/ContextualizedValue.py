"""
@module scoring.objects.scoring.ContextualizedValue

Row class ContextualizedValue of the scoring module — one class per file (design §7), split
from scoring_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

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
        # Contributor row (scoring.contributors_basis) that supplied this
        # value — individuals and orgs are TRACKABLE for research
        # contributions (or pseudonymous by their contributor row's
        # own knob); '' = unattributed, honestly.
        contributed_by: str = '',
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
        self.contributed_by = contributed_by
        self.notes = notes
