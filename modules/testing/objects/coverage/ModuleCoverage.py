"""
@module testing.objects.coverage.ModuleCoverage

Row class ModuleCoverage of the testing module — one class per file (design §7), split
from coverage_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class ModuleCoverage(treeObject):
    @treeObjectInit
    def __init__(self, name: str = '', module: str = '', apps_json: str = '[]',
                 upstream_apps_json: str = '[]', best_app: str = '',
                 verdict: str = 'uncovered', reason: str = '', nodes_json: str = '[]',
                 computed_at: str = ''):
        self.name = name
        self.module = module
        self.apps_json = apps_json
        self.upstream_apps_json = upstream_apps_json
        self.best_app = best_app
        self.verdict = verdict
        self.reason = reason
        self.nodes_json = nodes_json
        self.computed_at = computed_at
