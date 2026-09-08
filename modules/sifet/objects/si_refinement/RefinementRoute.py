"""
@module sifet.objects.si_refinement.RefinementRoute

Row class RefinementRoute of the sifet module — one class per file (design §7), split
from si_refinement_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class RefinementRoute(treeObject):
    """An ordered chain of RefinementStep names toward a target
    grade, with the openness verdict and — for novel-needed routes
    — the candidate directions as labelled PRIOR entries."""

    @treeObjectInit
    def __init__(self, name='', display_name='', order=0,
                 steps_json='[]', feed_grade='mg-si', target_grade='',
                 openness='open-research', reasoning='',
                 novel_directions_json='[]', citations='[]',
                 notes='', is_prior=True, manager=None):
        self.name = name
        self.display_name = display_name
        self.order = order
        self.steps_json = steps_json
        self.feed_grade = feed_grade
        self.target_grade = target_grade
        self.openness = openness
        self.reasoning = reasoning
        self.novel_directions_json = novel_directions_json
        self.citations = citations
        self.notes = notes
        self.is_prior = is_prior
