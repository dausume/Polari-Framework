"""
@module testing.objects.coverage.AppBenchmark

Row class AppBenchmark of the testing module — one class per file (design §7), split
from coverage_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class AppBenchmark(treeObject):
    @treeObjectInit
    def __init__(self, name: str = '', app: str = '', modules_json: str = '[]',
                 host: str = '', budget: str = 'standard', cpu_limit: float = 0.0,
                 mem_limit_mb: float = 0.0, boot_seconds: float = 0.0,
                 peak_rss_mb: float = 0.0, classes: int = 0, image_mb: float = 0.0,
                 code_mb: float = 0.0, ok: bool = False, oom_killed: bool = False,
                 health_http: int = 0, measured_at: str = '', notes: str = ''):
        self.name = name
        self.app = app
        self.modules_json = modules_json
        self.host = host
        self.budget = budget
        self.cpu_limit = cpu_limit
        self.mem_limit_mb = mem_limit_mb
        self.boot_seconds = boot_seconds
        self.peak_rss_mb = peak_rss_mb
        self.classes = classes
        self.image_mb = image_mb
        self.code_mb = code_mb
        self.ok = ok
        self.oom_killed = oom_killed
        self.health_http = health_http
        self.measured_at = measured_at
        self.notes = notes
