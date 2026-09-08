"""
@module nutrition.objects.threshold.EatingPatternDefinition

Row class EatingPatternDefinition of the nutrition module — one class per file (design §7), split
from threshold_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class EatingPatternDefinition(treeObject):
    """One eating pattern and its per-slot calorie fractions."""

    @treeObjectInit
    def __init__(
        self,
        # matches PersonProfile.eating_pattern ('3-meal').
        name: str = '',
        display_name: str = '',
        # JSON list of {"slot": name, "fraction": 0-1} — fractions
        # sum to 1; slots come from the decision-5 vocabulary
        # (breakfast/lunch/dinner/brunch/linner/snack).
        slot_fractions_json: str = '[]',
        # convention priors, not literature findings — say so.
        is_prior: bool = True,
        source: str = 'convention prior (Q5, Dustin-proposed splits)',
        provenance_id: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.display_name = display_name
        self.slot_fractions_json = slot_fractions_json
        self.is_prior = is_prior
        self.source = source
        self.provenance_id = provenance_id
        self.notes = notes
