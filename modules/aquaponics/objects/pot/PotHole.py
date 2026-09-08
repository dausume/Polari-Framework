"""
@module aquaponics.objects.pot.PotHole

Row class PotHole of the aquaponics module — one class per file (design §7), split
from pot_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class PotHole(treeObject):
    """One bored slot in a pot's wall (a child row of its pot)."""

    @treeObjectInit
    def __init__(
        self,
        # unique key ('demo-herb-pot-input-1').
        name: str = '',
        # The PotDefinition this hole belongs to.
        pot_name: str = '',
        # HOLE_KINDS entry.
        kind: str = 'input',
        # Bore diameter (mm).
        diameter_mm: float = 10.0,
        # Height of the hole CENTER up the wall (mm from outer base).
        height_mm: float = 50.0,
        # Position around the wall (degrees, 0-360) — which side.
        azimuth_deg: float = 0.0,
        # Bore inclination (degrees from horizontal). POSITIVE = the
        # outer opening sits LOWER than the inner (downhill-out, so an
        # output drains by gravity); negative = uphill-out (would trap
        # water). Clamped to +/- MAX_ABS_ANGLE_DEG.
        angle_deg: float = 0.0,
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.pot_name = pot_name
        self.kind = kind
        self.diameter_mm = diameter_mm
        self.height_mm = height_mm
        self.azimuth_deg = azimuth_deg
        self.angle_deg = angle_deg
        self.notes = notes
