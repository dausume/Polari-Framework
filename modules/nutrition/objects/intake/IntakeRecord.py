"""
@module nutrition.objects.intake.IntakeRecord

Row class IntakeRecord of the nutrition module — one class per file (design §7), split
from intake_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class IntakeRecord(treeObject):
    """One eaten meal (a fact, never an intention)."""

    @treeObjectInit
    def __init__(
        self,
        # unique key ('demo-alex-2026-09-01-dinner').
        name: str = '',
        person_name: str = '',
        # ISO date eaten.
        date: str = '',
        # MEAL_SLOTS entry.
        slot: str = 'dinner',
        template_name: str = '',
        variation_name: str = '',
        scale: float = 1.0,
        # clock time ('' = untimed; timing evaluations skip it).
        time_hhmm: str = '',
        # INTAKE_SOURCES entry.
        source: str = 'logged',
        # the MealEntry this confirms ('' = ad-hoc meal).
        plan_entry_name: str = '',
        is_prior: bool = False,
        provenance_id: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.person_name = person_name
        self.date = date
        self.slot = slot
        self.template_name = template_name
        self.variation_name = variation_name
        self.scale = scale
        self.time_hhmm = time_hhmm
        self.source = source
        self.plan_entry_name = plan_entry_name
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes
