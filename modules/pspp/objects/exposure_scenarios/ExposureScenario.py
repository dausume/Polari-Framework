"""
@module pspp.objects.exposure_scenarios.ExposureScenario

Row class ExposureScenario of the pspp module — one class per file (design §7), split
from exposure_scenarios_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class ExposureScenario(treeObject):
    """One named environment a material can sit in."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        display_name: str = '',
        description: str = '',
        # JSON environment dict — temperature_c, relative_humidity,
        # water_contact ('none'|'humid'|'immersed'|'flowing'),
        # co2_exposure, chemical, uv, vacuum, thermal_cycling...
        environment_json: str = '{}',
        provenance_id: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.display_name = display_name
        self.description = description
        self.environment_json = environment_json
        self.provenance_id = provenance_id
        self.notes = notes
