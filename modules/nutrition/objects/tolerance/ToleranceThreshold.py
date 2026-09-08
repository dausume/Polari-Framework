"""
@module nutrition.objects.tolerance.ToleranceThreshold

Row class ToleranceThreshold of the nutrition module — one class per file (design §7), split
from tolerance_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class ToleranceThreshold(treeObject):
    """One cited adverse-effect threshold."""

    @treeObjectInit
    def __init__(
        self,
        # unique key ('fermenting-fiber-dose').
        name: str = '',
        # what is being dosed — a DietaryNutrient name where one
        # exists, else a substance name ('inulin-type-fiber',
        # 'sorbitol', 'glycemic-load', 'meal-acidity').
        substance: str = '',
        # TOLERANCE_PERIODS entry — what ONE unit of exposure is.
        period: str = 'dose',
        # threshold amount in `unit`; if per_kg_body_mass, the
        # amount is per kg and scales with the person.
        threshold_amount: float = 0.0,
        unit: str = 'g',
        per_kg_body_mass: bool = False,
        # the named symptom the literature associates above the
        # threshold — the warning text leads with this.
        symptom: str = '',
        citation: str = '',
        # CONFIDENCE_GRADES entry.
        confidence: str = 'moderate',
        # honest qualifier: 'utilization plateau, NOT toxicity' etc.
        qualifier: str = '',
        is_prior: bool = True,
        provenance_id: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.substance = substance
        self.period = period
        self.threshold_amount = threshold_amount
        self.unit = unit
        self.per_kg_body_mass = per_kg_body_mass
        self.symptom = symptom
        self.citation = citation
        self.confidence = confidence
        self.qualifier = qualifier
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes
