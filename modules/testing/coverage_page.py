"""
@module testing.coverage_page
/display/test-coverage — the plan, the hierarchy (largest apps first),
per-module verdicts, benchmarks and nodes: configured tables and
structured panels only (no raw JSON).
"""
from polariApiServer.module_pages_seed import _page, _row, _sapi, _table

_P = '/api/testing/coverage'

SEED_TESTING_COVERAGE_PAGE_DISPLAYS = [
    _page(
        'test-coverage', 'test-coverage',
        'Test coverage by app: modules roll up into apps (seeded apps, topology '
        'instances, module singletons); each app is estimated or BENCHMARKED '
        'against the standard-computer budget; the plan picks the smallest set '
        'of fitting apps that covers every module, and hands the rest to swarm/isle '
        'nodes or a large host. Estimates are labelled declared until a benchmark '
        'row exists (pol modules testplan benchmark <app>).',
        'TestCoveragePlan',
        [
            _row(0, [
                _sapi('tcov-summary', 0, 6, 'Coverage plan (current)', _P, pick='summary', hide='largest'),
                _sapi('tcov-nodes', 1, 6, 'Nodes a distributed test could use', _P + '/nodes'),
            ]),
            _row(1, [
                _table('tcov-budget', 0, 4, 'Standard computer budget (D1)', 'StandardComputerBudget',
                       columns='name,cores,vcpus,ram_mb,disk_mb,boot_timeout_s,notes'),
                _table('tcov-apps', 1, 8, 'App hierarchy (largest closure first)', 'AppHierarchyNode',
                       columns='name,kind,module_count,closure_count,est_classes,est_ram_mb,est_boot_s,fidelity,fits_standard,chosen'),
            ]),
            _row(2, [
                _table('tcov-modules', 0, 8, 'Module coverage verdicts', 'ModuleCoverage',
                       columns='module,verdict,best_app,reason,nodes_json'),
                _table('tcov-bench', 1, 4, 'Benchmarks (measured under the budget)', 'AppBenchmark',
                       columns='app,ok,boot_seconds,peak_rss_mb,classes,oom_killed,mem_limit_mb,cpu_limit,measured_at'),
            ]),
        ]),
]
