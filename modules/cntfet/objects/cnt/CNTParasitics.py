"""
@module cntfet.objects.cnt.CNTParasitics

Row class CNTParasitics of the cntfet module — one class per file (design §7), split
from cnt_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class CNTParasitics(treeObject):
    """S1 minimal: a single lumped parasitic capacitance prior.
    Fringe/coupling decomposition is S2+ ([VS2] extrinsics)."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        c_par_f: float = 0.0,
        source: str = 'S1 default 0 — DC-only target; [VS2] '
                      'extrinsic elements are S2+',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.c_par_f = c_par_f
        self.source = source
        self.notes = notes
