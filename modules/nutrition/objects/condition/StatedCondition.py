"""
@module nutrition.objects.condition.StatedCondition

Row class StatedCondition of the nutrition module — one class per file (design §7), split
from condition_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class StatedCondition(treeObject):
    """One person's own condition declaration."""

    @treeObjectInit
    def __init__(
        self,
        # unique key ('demo-alex-reflux').
        name: str = '',
        person_name: str = '',
        # ConditionSteering.condition this refers to.
        condition: str = '',
        # the person's own words ('GERD diagnosed by my doctor',
        # 'heartburn after big meals').
        stated_reason: str = '',
        # ISO date declared.
        declared_date: str = '',
        is_prior: bool = False,
        provenance_id: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.person_name = person_name
        self.condition = condition
        self.stated_reason = stated_reason
        self.declared_date = declared_date
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes
