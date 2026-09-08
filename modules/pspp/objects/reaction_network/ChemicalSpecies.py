"""
@module pspp.objects.reaction_network.ChemicalSpecies

Row class ChemicalSpecies of the pspp module — one class per file (design §7), split
from reaction_network_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class ChemicalSpecies(treeObject):
    """One species/motif the reaction network trades in."""

    @treeObjectInit
    def __init__(
        self,
        # Kebab-case key ('hydroxide-ion', 'siloxonate-q2').
        name: str = '',
        display_name: str = '',
        formula: str = '',
        charge: int = 0,
        # 'ion' | 'molecule' | 'motif' (Q-species are motifs over an
        # underlying network — never complete structures) |
        # 'framework' (crystalline/amorphous product families).
        species_kind: str = 'molecule',
        # Q-state for silicate motifs (-1 = not applicable).
        qn: int = -1,
        provenance_id: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.display_name = display_name
        self.formula = formula
        self.charge = charge
        self.species_kind = species_kind
        self.qn = qn
        self.provenance_id = provenance_id
        self.notes = notes
