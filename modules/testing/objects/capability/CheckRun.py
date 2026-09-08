"""
@module testing.objects.capability.CheckRun

Row class CheckRun of the testing module — one class per file (design §7), split
from capability_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class CheckRun(treeObject):
    """One execution of the matrix (or a category/name slice).
    results_json rows carry the same fields the YAML report projects
    — the report is a projection of this object, never a second
    bookkeeping system."""

    @treeObjectInit
    def __init__(self, name: str = '', started_at: str = '',
                 finished_at: str = '', build_json: str = '{}',
                 environment_json: str = '{}', totals_json: str = '{}',
                 blocking_green: bool = False,
                 results_json: str = '[]', report_path: str = '',
                 manager=None):
        self.name = name
        self.started_at = started_at
        self.finished_at = finished_at
        self.build_json = build_json
        self.environment_json = environment_json
        self.totals_json = totals_json
        self.blocking_green = blocking_green
        self.results_json = results_json
        self.report_path = report_path
