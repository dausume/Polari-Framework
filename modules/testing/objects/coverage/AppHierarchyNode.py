"""
@module testing.objects.coverage.AppHierarchyNode

Row class AppHierarchyNode of the testing module — one class per file (design §7), split
from coverage_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class AppHierarchyNode(treeObject):
    @treeObjectInit
    def __init__(self, name: str = '', kind: str = 'app', modules_json: str = '[]',
                 closure_json: str = '[]', module_count: int = 0, closure_count: int = 0,
                 unknown_modules_json: str = '[]', est_classes: int = 0,
                 est_ram_mb: float = 0.0, est_disk_mb: float = 0.0, est_boot_s: float = 0.0,
                 est_threads: int = 1, engines_json: str = '[]', fidelity: str = 'declared',
                 fits_standard: bool = False, fit_reasons_json: str = '[]',
                 chosen: bool = False, computed_at: str = '', notes: str = ''):
        self.name = name
        self.kind = kind
        self.modules_json = modules_json
        self.closure_json = closure_json
        self.module_count = module_count
        self.closure_count = closure_count
        self.unknown_modules_json = unknown_modules_json
        self.est_classes = est_classes
        self.est_ram_mb = est_ram_mb
        self.est_disk_mb = est_disk_mb
        self.est_boot_s = est_boot_s
        self.est_threads = est_threads
        self.engines_json = engines_json
        self.fidelity = fidelity
        self.fits_standard = fits_standard
        self.fit_reasons_json = fit_reasons_json
        self.chosen = chosen
        self.computed_at = computed_at
        self.notes = notes
