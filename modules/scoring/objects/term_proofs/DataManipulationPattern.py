"""
@module scoring.objects.term_proofs.DataManipulationPattern

Row class DataManipulationPattern of the scoring module — one class per file (design §7), split
from term_proofs_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class DataManipulationPattern(treeObject):
    """One recognizable shape of statistical manipulation — a
    VOTABLE catalog row (what counts as suspect framing is
    contestable), with the counter-presentation that exposes it and
    a computable exposure check where one honestly exists."""

    @treeObjectInit
    def __init__(self, name: str = '', display_name: str = '',
                 description: str = '',
                 counter_presentation: str = '',
                 # 'module:function' for implemented checks, '' else.
                 exposure_check: str = '',
                 computability: str = 'judgment-only',
                 proposed_by: str = '', notes: str = '',
                 manager=None):
        self.name = name
        self.display_name = display_name
        self.description = description
        self.counter_presentation = counter_presentation
        self.exposure_check = exposure_check
        self.computability = computability
        self.proposed_by = proposed_by
        self.notes = notes
