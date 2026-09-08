"""
@module sifet.objects.si.SolGelProcess

Row class SolGelProcess of the sifet module — one class per file (design §7), split
from si_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class SolGelProcess(treeObject):
    """How the sol-gel film is laid down and cured."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        deposition: str = 'spin',        # spin | dip
        spin_rpm: float = 3000.0,
        layers: int = 1,
        cure_profile_json: str = '{}',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.deposition = deposition
        self.spin_rpm = spin_rpm
        self.layers = layers
        self.cure_profile_json = cure_profile_json
        self.notes = notes
