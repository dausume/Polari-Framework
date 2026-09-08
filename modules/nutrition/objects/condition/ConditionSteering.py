"""
@module nutrition.objects.condition.ConditionSteering

Row class ConditionSteering of the nutrition module — one class per file (design §7), split
from condition_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class ConditionSteering(treeObject):
    """One condition's aggravator mapping — data, extendable."""

    @treeObjectInit
    def __init__(
        self,
        # kebab-case condition key ('reflux').
        condition: str = '',
        name: str = '',
        display_name: str = '',
        # JSON list of nmp-2 tolerance SUBSTANCES that count as
        # aggravators for this condition (evaluation rides the
        # existing cited rows; substances the rollup cannot
        # compute are reported as data gaps, never guessed).
        aggravator_substances_json: str = '[]',
        # plain-language do-not-worsen guidance.
        guidance: str = '',
        citation: str = '',
        # CONFIDENCE grades follow the tolerance table's.
        confidence: str = 'low',
        is_prior: bool = True,
        provenance_id: str = '',
        notes: str = '',
        manager=None,
    ):
        self.condition = condition
        self.name = name
        self.display_name = display_name
        self.aggravator_substances_json = aggravator_substances_json
        self.guidance = guidance
        self.citation = citation
        self.confidence = confidence
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes
