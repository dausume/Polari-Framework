"""
@module tanks.objects.tank.TankSystemDefinition

Row class TankSystemDefinition of the tanks module — one class per file (design §7), split
from tank_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class TankSystemDefinition(treeObject):
    """An interconnected tank system + its species stock."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        display_name: str = '',
        description: str = '',
        water_type: str = 'salt',
        # JSON list of TankDefinition names.
        tank_names_json: str = '[]',
        # JSON {species_name: count} — the stocked population.
        species_stock_json: str = '{}',
        # Persisted balance/yield snapshot (JSON) for scoring.
        ecosystem_result_json: str = '',
        provenance_id: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.display_name = display_name
        self.description = description
        self.water_type = water_type
        self.tank_names_json = tank_names_json
        self.species_stock_json = species_stock_json
        self.ecosystem_result_json = ecosystem_result_json
        self.provenance_id = provenance_id
        self.notes = notes
