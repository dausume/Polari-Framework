"""
@module scoring.objects.scoring.ScoreTerm

Row class ScoreTerm of the scoring module — one class per file (design §7), split
from scoring_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

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
        # Temporal semantics (JSON): {"nature": "stock"|"flow"|
        # "event", "resample": "mean"|"sum"|"nearest"|"last"|"count"}
        # — how values of this metric may be combined across
        # timeframes. Undeclared + combination needed = refusal.
        temporal_json: str = '{}',
        # Loose links to related/opposing terms (JSON name lists).
        equivalent_terms_json: str = '[]',
        competitive_terms_json: str = '[]',
        # Generic-intent vocabulary this metric belongs to (JSON list,
        # e.g. ["wages", "labor-conditions"]) — the abstraction seam:
        # assertions of generic intent match terms through these tags
        # (scr-5), suggestions only, never auto-bound.
        abstract_tags_json: str = '[]',
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
        self.temporal_json = temporal_json
        self.equivalent_terms_json = equivalent_terms_json
        self.competitive_terms_json = competitive_terms_json
        self.abstract_tags_json = abstract_tags_json
        self.source = source
        self.provenance_id = provenance_id
        self.notes = notes
