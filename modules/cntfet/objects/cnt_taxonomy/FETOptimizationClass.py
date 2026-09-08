"""
@module cntfet.objects.cnt_taxonomy.FETOptimizationClass

Row class FETOptimizationClass of the cntfet module — one class per file (design §7), split
from cnt_taxonomy_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class FETOptimizationClass(treeObject):
    """What a FET is optimized FOR, as a row: the figures of merit it
    maximises/minimises (with why), the operating region it prefers,
    and the score concept that measures it."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        display_name: str = '',
        aliases_json: str = '[]',
        description: str = '',
        # JSON list of {figure, direction: 'maximise'|'minimise', why}
        optimizes_json: str = '[]',
        # state/regime names from fi-0 / fv-1 the class lives in
        preferred_region: str = '',
        score_concept: str = '',
        design_rules_json: str = '[]',
        notes: str = '',
        origin: str = 'seeded',
        is_prior: bool = True,
        manager=None,
    ):
        self.name = name
        self.display_name = display_name
        self.aliases_json = aliases_json
        self.description = description
        self.optimizes_json = optimizes_json
        self.preferred_region = preferred_region
        self.score_concept = score_concept
        self.design_rules_json = design_rules_json
        self.notes = notes
        self.origin = origin
        self.is_prior = is_prior
