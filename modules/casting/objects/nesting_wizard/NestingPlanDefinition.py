"""
@module casting.objects.nesting_wizard.NestingPlanDefinition

Row class NestingPlanDefinition of the casting module — one class per file (design §7), split
from nesting_wizard_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class NestingPlanDefinition(treeObject):
    """One derived nesting plan: part × target material → chain +
    every step's verdict and viewable artifacts. DERIVED — re-runs
    reconverge."""

    @treeObjectInit
    def __init__(self, name: str = '', part_shape_ref: str = '',
                 target_material: str = '', chain_ref: str = '',
                 mold_ref: str = '', feedstock_ref: str = '',
                 verdict: str = '', steps_json: str = '[]',
                 report_json: str = '{}', is_prior: bool = True,
                 notes: str = '', provenance_id: str = '',
                 manager=None):
        self.name = name
        self.part_shape_ref = part_shape_ref
        self.target_material = target_material
        self.chain_ref = chain_ref
        self.mold_ref = mold_ref
        self.feedstock_ref = feedstock_ref
        self.verdict = verdict
        self.steps_json = steps_json
        self.report_json = report_json
        self.is_prior = is_prior
        self.notes = notes
        self.provenance_id = provenance_id
