"""
@module cntfet.objects.cnt.GateStack

Row class GateStack of the cntfet module — one class per file (design §7), split
from cnt_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class GateStack(treeObject):
    """The gate dielectric + electrostatic geometry. S1 idealizes to
    the GAA cylinder ([VS1] Fig.1 + eq.(1)); cox/cinv are derived."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        geometry: str = 'gaa-cylindrical',
        dielectric_material: str = 'HfO2',
        t_ox_nm: float = 3.0,
        k_ox: float = 16.0,
        # Derived:
        cox_f_per_m: float = 0.0,
        cqe_f_per_m: float = 0.0,
        cinv_f_per_m: float = 0.0,
        derived_at: str = '',
        provenance_json: str = '{}',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.geometry = geometry
        self.dielectric_material = dielectric_material
        self.t_ox_nm = t_ox_nm
        self.k_ox = k_ox
        self.cox_f_per_m = cox_f_per_m
        self.cqe_f_per_m = cqe_f_per_m
        self.cinv_f_per_m = cinv_f_per_m
        self.derived_at = derived_at
        self.provenance_json = provenance_json
        self.notes = notes
