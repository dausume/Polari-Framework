"""
@module nutrition.objects.exclusion.PersonExclusion

Row class PersonExclusion of the nutrition module — one class per file (design §7), split
from exclusion_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class PersonExclusion(treeObject):
    """One person's DECLARED exclusion (never inferred)."""

    @treeObjectInit
    def __init__(
        self,
        # unique key ('demo-alex-tree-nut').
        name: str = '',
        person_name: str = '',
        # exactly one of these two is set.
        allergen_class: str = '',
        food_name: str = '',
        # EXCLUSION_SEVERITIES entry.
        severity: str = 'allergy-hard',
        # the person's own words ('diagnosed peanut allergy 2019',
        # 'dairy makes me ill', 'I just hate mushrooms').
        stated_reason: str = '',
        is_prior: bool = False,
        provenance_id: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.person_name = person_name
        self.allergen_class = allergen_class
        self.food_name = food_name
        self.severity = severity
        self.stated_reason = stated_reason
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes
