"""
@module sifet.objects.si.SiliconDopingProfile

Row class SiliconDopingProfile of the sifet module — one class per file (design §7), split
from si_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class SiliconDopingProfile(treeObject):
    """One doping region: channel/body or source-drain."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        dopant_type: str = 'p',          # 'n' | 'p'
        species: str = 'B',              # P | As | B
        concentration_cm3: float = 1e17,
        method: str = 'implant',         # implant | diffusion | in-situ
        activation_fraction: float = 1.0,
        junction_depth_nm: float = 0.0,
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.dopant_type = dopant_type
        self.species = species
        self.concentration_cm3 = concentration_cm3
        self.method = method
        self.activation_fraction = activation_fraction
        self.junction_depth_nm = junction_depth_nm
        self.notes = notes
