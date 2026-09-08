"""
@module pspp.objects.reaction_windows.ReactionWindow

Row class ReactionWindow of the pspp module — one class per file (design §7), split
from reaction_windows_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class ReactionWindow(treeObject):
    """One empirical composition window for one derived descriptor."""

    @treeObjectInit
    def __init__(
        self,
        # Unique key ('mk-geopolymer:SiO2/Al2O3').
        name: str = '',
        # The material family / system the window was established for
        # — windows do NOT transfer between families (invariant I5).
        material_family: str = '',
        # The computed descriptor it grades ('SiO2/Al2O3', 'H2O/M2O',
        # 'Si/Al'… — pspp.custom.composition_math.oxide_ratios keys).
        descriptor: str = '',
        center: float = 0.0,
        # Widening half-tolerances around center per grade.
        ideal_tolerance: float = 0.0,
        acceptable_tolerance: float = 0.0,
        marginal_tolerance: float = 0.0,
        # What physically goes wrong outside ('too little alkali —
        # incomplete dissolution') — the evidence half of a verdict.
        behavior_note: str = '',
        source_reference: str = '',
        provenance_id: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.material_family = material_family
        self.descriptor = descriptor
        self.center = center
        self.ideal_tolerance = ideal_tolerance
        self.acceptable_tolerance = acceptable_tolerance
        self.marginal_tolerance = marginal_tolerance
        self.behavior_note = behavior_note
        self.source_reference = source_reference
        self.provenance_id = provenance_id
        self.notes = notes
