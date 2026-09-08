"""
@module casting.objects.chain.MoldNestingChain

Row class MoldNestingChain of the casting module — one class per file (design §7), split
from chain_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class MoldNestingChain(treeObject):
    """A nested casting chain (wax → … → final part). Parity and
    thermal ordering are DERIVED by chain_analysis.chain_report."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        display_name: str = '',
        # the final part this chain exists to produce.
        target_part_shape_ref: str = '',
        # the cast-1 MoldDefinition carrying the stage-1 geometry
        # (loading checks ride it).
        mold_def_ref: str = '',
        is_prior: bool = True,
        notes: str = '',
        provenance_id: str = '',
        manager=None,
    ):
        self.name = name
        self.display_name = display_name
        self.target_part_shape_ref = target_part_shape_ref
        self.mold_def_ref = mold_def_ref
        self.is_prior = is_prior
        self.notes = notes
        self.provenance_id = provenance_id
