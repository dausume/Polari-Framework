"""
@module scoring.objects.group_bias.BiasPolicy

Row class BiasPolicy of the scoring module — one class per file (design §7), split
from group_bias_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class BiasPolicy(treeObject):
    """Editable bands for the bias reads."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        display_name: str = '',
        description: str = '',
        # Bands over the dominant supports/harms fraction (0.5-1.0).
        onesidedness_bands_json: str = '[]',
        # Bands over the self-serving vote fraction (0-1).
        alignment_bands_json: str = '[]',
        # Bands over |group share − consensus share| per term.
        emphasis_bands_json: str = '[]',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.display_name = display_name
        self.description = description
        self.onesidedness_bands_json = onesidedness_bands_json
        self.alignment_bands_json = alignment_bands_json
        self.emphasis_bands_json = emphasis_bands_json
        self.notes = notes
