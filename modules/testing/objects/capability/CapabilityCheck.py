"""
@module testing.objects.capability.CapabilityCheck

Row class CapabilityCheck of the testing module — one class per file (design §7), split
from capability_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class CapabilityCheck(treeObject):
    """One named check on the capability matrix."""

    @treeObjectInit
    def __init__(self, name: str = '', category: str = 'module',
                 kind: str = 'in-process',
                 criticality: str = 'informational',
                 runner_ref: str = '', description: str = '',
                 last_status: str = 'never-run',
                 last_evidence: str = '', last_run_at: str = '',
                 last_duration_ms: int = 0, manager=None):
        self.name = name
        self.category = category
        self.kind = kind
        self.criticality = criticality
        self.runner_ref = runner_ref
        self.description = description
        self.last_status = last_status
        self.last_evidence = last_evidence
        self.last_run_at = last_run_at
        self.last_duration_ms = last_duration_ms
