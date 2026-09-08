"""
@module testing.objects.coverage.StandardComputerBudget

Row class StandardComputerBudget of the testing module — one class per file (design §7), split
from coverage_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class StandardComputerBudget(treeObject):
    """The machine a test must fit on. Defaults are PLACEHOLDERS from his
    '2 core, 4 vcpu?' — set the real numbers on the row (D1)."""
    @treeObjectInit
    def __init__(self, name: str = 'standard', cores: int = 2, vcpus: int = 4,
                 ram_mb: float = 4096.0, disk_mb: float = 32768.0,
                 boot_timeout_s: int = 900, is_prior: bool = True, notes: str = ''):
        self.name = name
        self.cores = cores
        self.vcpus = vcpus
        self.ram_mb = ram_mb
        self.disk_mb = disk_mb
        self.boot_timeout_s = boot_timeout_s
        self.is_prior = is_prior
        self.notes = notes
