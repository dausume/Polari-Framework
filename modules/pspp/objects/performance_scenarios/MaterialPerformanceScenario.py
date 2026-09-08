"""
@module pspp.objects.performance_scenarios.MaterialPerformanceScenario

Row class MaterialPerformanceScenario of the pspp module — one class per file (design §7), split
from performance_scenarios_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class MaterialPerformanceScenario(treeObject):
    """One in-service question about one material state."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        # The MaterialState under test ('<material>#<state>').
        initial_state_key: str = '',
        # Part geometry reference ('' = bulk material question).
        geometry_ref: str = '',
        # ExposureScenario.name.
        exposure_scenario: str = '',
        loads_json: str = '{}',
        duration_hours: float = 0.0,
        # PERFORMANCE_ENGINES key.
        performance_engine: str = '',
        parameters_json: str = '{}',
        provenance_id: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.initial_state_key = initial_state_key
        self.geometry_ref = geometry_ref
        self.exposure_scenario = exposure_scenario
        self.loads_json = loads_json
        self.duration_hours = duration_hours
        self.performance_engine = performance_engine
        self.parameters_json = parameters_json
        self.provenance_id = provenance_id
        self.notes = notes
