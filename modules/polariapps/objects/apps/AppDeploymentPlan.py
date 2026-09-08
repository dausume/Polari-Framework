"""
@module polariapps.objects.apps.AppDeploymentPlan

Row class AppDeploymentPlan of the polariapps module — one class per file (design §7), split
from apps_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class AppDeploymentPlan(treeObject):
    """A PLANNED deployment of one app onto one topology — computed,
    exportable, applied later; never executed on the spot."""

    @treeObjectInit
    def __init__(
        self,
        # Unique key, conventionally '<app>@<topology>@<created_at>'.
        name: str = '',
        app_name: str = '',
        topology_name: str = '',
        # JSON plan rows ({module, status, instances, suggested...}).
        placements_json: str = '[]',
        # PLAN_STATUSES entry.
        status: str = 'draft',
        created_at: str = '',
        applied_at: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.app_name = app_name
        self.topology_name = topology_name
        self.placements_json = placements_json
        self.status = status
        self.created_at = created_at
        self.applied_at = applied_at
        self.notes = notes
