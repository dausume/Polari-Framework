"""
@module mathshapes.objects.tower.AquaponicTowerDefinition

Row class AquaponicTowerDefinition of the mathshapes module — one class per file (design §7), split
from tower_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class AquaponicTowerDefinition(treeObject):
    """A vertical stack of pots as one aquaponic tower."""

    @treeObjectInit
    def __init__(
        self,
        # unique key ('demo-herb-tower').
        name: str = '',
        display_name: str = '',
        # The per-tier pot as a MathShapeDefinition name (the CSG pot
        # from pot_shape_from_definition, or a shape-1 seed like
        # 'pot-with-holes'). Every tier uses this same pot geometry.
        pot_shape_name: str = 'pot-with-holes',
        # How many tiers stacked vertically.
        n_tiers: int = 4,
        # Centre-to-centre vertical spacing between tiers (cm).
        tier_spacing_cm: float = 25.0,
        # A shared water store at the base feeding all tiers.
        shared_reservoir: bool = True,
        # Reservoir capacity (L). 0 = size it later.
        reservoir_volume_l: float = 10.0,
        # Fraction of each pot's solid bounding volume that is actually
        # GROW space (soil/root void) — the rest is wall + the drainage
        # holes. A rough packing estimate the analysis reports honestly.
        grow_fraction: float = 0.6,
        notes: str = '',
        provenance_id: str = '',
        manager=None,
    ):
        self.name = name
        self.display_name = display_name
        self.pot_shape_name = pot_shape_name
        self.n_tiers = n_tiers
        self.tier_spacing_cm = tier_spacing_cm
        self.shared_reservoir = shared_reservoir
        self.reservoir_volume_l = reservoir_volume_l
        self.grow_fraction = grow_fraction
        self.notes = notes
        self.provenance_id = provenance_id
