"""
@module sifet.objects.si.SiliconFETShape

Row class SiliconFETShape of the sifet module — one class per file (design §7), split
from si_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class SiliconFETShape(treeObject):
    """The electrostatic shape: planar bulk / SOI / FinFET / GAA.
    scale_length_formula is DATA (the equation the derive uses)."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        kind: str = 'planar-bulk',       # planar-bulk | soi | finfet | gaa-nanosheet
        channel_width_nm: float = 1000.0,
        fin_height_nm: float = 0.0,
        fin_width_nm: float = 0.0,
        n_fins: int = 1,
        gate_all_around: bool = False,
        scale_length_formula: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.kind = kind
        self.channel_width_nm = channel_width_nm
        self.fin_height_nm = fin_height_nm
        self.fin_width_nm = fin_width_nm
        self.n_fins = n_fins
        self.gate_all_around = gate_all_around
        self.scale_length_formula = scale_length_formula
        self.notes = notes
