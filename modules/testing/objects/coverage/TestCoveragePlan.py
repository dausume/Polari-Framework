"""
@module testing.objects.coverage.TestCoveragePlan

Row class TestCoveragePlan of the testing module — one class per file (design §7), split
from coverage_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class TestCoveragePlan(treeObject):
    @treeObjectInit
    def __init__(self, name: str = '', budget: str = 'standard', chosen_apps_json: str = '[]',
                 total_modules: int = 0, covered_standard: int = 0, covered_distributed: int = 0,
                 covered_large_host: int = 0, uncovered: int = 0, uncovered_json: str = '[]',
                 nodes_json: str = '[]', host_json: str = '{}', computed_at: str = '',
                 notes: str = ''):
        self.name = name
        self.budget = budget
        self.chosen_apps_json = chosen_apps_json
        self.total_modules = total_modules
        self.covered_standard = covered_standard
        self.covered_distributed = covered_distributed
        self.covered_large_host = covered_large_host
        self.uncovered = uncovered
        self.uncovered_json = uncovered_json
        self.nodes_json = nodes_json
        self.host_json = host_json
        self.computed_at = computed_at
        self.notes = notes
