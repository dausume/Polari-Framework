"""
@module testing.coverage_basis

Test coverage as rows (tcov-1, Dustin 2026-09-08): "make hierarchies out
of modules and apps so we can find the larger apps with significant
amounts of modules … identify the apps we can isolate and choose as the
means to efficiently test all of the modules … benchmark the system
requirements for these largest apps … anything larger than a 'standard
computer' we do not test [on one box] … confirm other docker swarm nodes
or isle nodes exist that our testing suite can access … or confirm we
are on a particularly large computer." The foundation for testing and
the baseline for how Jenkins operates (ci-3).

Rows:
  StandardComputerBudget  the budget a test host is held to (his numbers = D1)
  AppHierarchyNode        one app (seeded app | topology instance | module singleton)
                          with its module CLOSURE and its estimate/benchmark
  ModuleCoverage          per module: which apps contain it, the chosen app,
                          and the VERDICT (covered-standard | covered-distributed
                          | covered-large-host | uncovered) with the reason
  AppBenchmark            a MEASURED boot of one app under the budget's
                          cgroup limits (fidelity 'benchmark' beats 'declared')
  TestCoveragePlan        the result of one planning run
"""
from objectTreeDecorators import treeObject, treeObjectInit

COVERAGE_VERDICTS = ('covered-standard', 'covered-distributed',
                     'covered-large-host', 'uncovered')
APP_NODE_KINDS = ('app', 'instance', 'module')
FIDELITY_VALUES = ('declared', 'benchmark')


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


SEED_STANDARD_COMPUTER_BUDGETS = [{
    'name': 'standard', 'cores': 2, 'vcpus': 4, 'ram_mb': 4096.0, 'disk_mb': 32768.0,
    'boot_timeout_s': 900,
    'notes': "PLACEHOLDER numbers (his '2 core, 4 vcpu?' 2026-09-08; RAM/disk assumed) — "
             "decision D1 of the coverage plan sets them; every verdict cites this row.",
}]

COVERAGE_CLASSES = [StandardComputerBudget, AppHierarchyNode, ModuleCoverage,
                    AppBenchmark, TestCoveragePlan]
