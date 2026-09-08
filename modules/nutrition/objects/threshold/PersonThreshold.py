"""
@module nutrition.objects.threshold.PersonThreshold

Row class PersonThreshold of the nutrition module — one class per file (design §7), split
from threshold_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class PersonThreshold(treeObject):
    """One human-overridden threshold for (person, nutrient, period).

    Absent row = the derived value applies (threshold_analysis shows
    its derivation). A row here WINS over the derivation and is never
    touched by seeds (is_prior=False by construction — it exists
    because a human set it)."""

    @treeObjectInit
    def __init__(
        self,
        # unique key ('alex-fiber-day').
        name: str = '',
        person_name: str = '',
        nutrient_name: str = '',
        # THRESHOLD_PERIODS entry.
        period: str = 'day',
        # the override values; 0 = keep the derived value for that
        # side (min/target/max are independently overridable).
        min_amount: float = 0.0,
        target_amount: float = 0.0,
        max_amount: float = 0.0,
        unit: str = '',
        # why the human set it — their words, kept with the number.
        reason: str = '',
        is_prior: bool = False,
        provenance_id: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.person_name = person_name
        self.nutrient_name = nutrient_name
        self.period = period
        self.min_amount = min_amount
        self.target_amount = target_amount
        self.max_amount = max_amount
        self.unit = unit
        self.reason = reason
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes
