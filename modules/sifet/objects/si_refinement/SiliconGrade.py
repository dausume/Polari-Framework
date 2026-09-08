"""
@module sifet.objects.si_refinement.SiliconGrade

Row class SiliconGrade of the sifet module — one class per file (design §7), split
from si_refinement_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class SiliconGrade(treeObject):
    """One rung of the silicon purity ladder as a ROW."""

    @treeObjectInit
    def __init__(self, name='', display_name='', order=0,
                 purity_min_fraction=0.0, purity_n_count='',
                 dominant_impurities_json='{}', typical_use='',
                 openness='open-research', openness_reasoning='',
                 techtree_node='', citations='[]', notes='',
                 is_prior=True, manager=None):
        self.name = name
        self.display_name = display_name
        self.order = order
        self.purity_min_fraction = purity_min_fraction
        self.purity_n_count = purity_n_count
        self.dominant_impurities_json = dominant_impurities_json
        self.typical_use = typical_use
        self.openness = openness
        self.openness_reasoning = openness_reasoning
        self.techtree_node = techtree_node
        self.citations = citations
        self.notes = notes
        self.is_prior = is_prior
