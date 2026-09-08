"""
@module cntfet.objects.cnt.AlignedCNTFETGeometry

Row class AlignedCNTFETGeometry of the cntfet module — one class per file (design §7), split
from cnt_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class AlignedCNTFETGeometry(treeObject):
    """Device geometry. tube_count is FROZEN at 1 for S1 (the plan's
    smallest-object rule); pitch exists for S2+ aggregation and is
    honestly unused today."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        lg_nm: float = 15.0,
        l_ext_nm: float = 0.0,
        l_c_nm: float = 0.0,
        tube_count: int = 1,
        pitch_nm: float = 0.0,
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.lg_nm = lg_nm
        self.l_ext_nm = l_ext_nm
        self.l_c_nm = l_c_nm
        self.tube_count = tube_count
        self.pitch_nm = pitch_nm
        self.notes = notes
