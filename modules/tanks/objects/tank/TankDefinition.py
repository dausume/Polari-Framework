"""
@module tanks.objects.tank.TankDefinition

Row class TankDefinition of the tanks module — one class per file (design §7), split
from tank_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class TankDefinition(treeObject):
    """One tank in the modular food-forest system."""

    @treeObjectInit
    def __init__(
        self,
        # kebab-case unique key ('saltwater-tank-1').
        name: str = '',
        display_name: str = '',
        # WATER_TYPES entry.
        water_type: str = 'salt',
        volume_gal: float = 30.0,
        # TANK_ROLES entry.
        role: str = 'general',
        # Room-temperature target (the whole design premise).
        temperature_c: float = 22.0,
        # Connector bore (in) — >=3in for sardine/anchovy schools.
        connector_diameter_in: float = 3.0,
        # The substrate bed (a TankSubstrateDefinition by name) + how
        # much of it (litres) — sets the tank's denitrification +
        # buffering contribution. '' / 0 = a bare-bottom tank.
        substrate_name: str = '',
        substrate_volume_l: float = 0.0,
        provenance_id: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.display_name = display_name
        self.water_type = water_type
        self.volume_gal = volume_gal
        self.role = role
        self.temperature_c = temperature_c
        self.connector_diameter_in = connector_diameter_in
        self.substrate_name = substrate_name
        self.substrate_volume_l = substrate_volume_l
        self.provenance_id = provenance_id
        self.notes = notes
