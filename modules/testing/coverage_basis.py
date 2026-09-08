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
# sap-2c INDEX (design §7): the classes live one-per-file under objects/coverage/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

from objectTreeDecorators import treeObject, treeObjectInit

from testing.objects.coverage._shared import APP_NODE_KINDS, COVERAGE_VERDICTS, FIDELITY_VALUES, SEED_STANDARD_COMPUTER_BUDGETS  # noqa: F401
from testing.objects.coverage.StandardComputerBudget import StandardComputerBudget  # noqa: F401
from testing.objects.coverage.AppHierarchyNode import AppHierarchyNode  # noqa: F401
from testing.objects.coverage.ModuleCoverage import ModuleCoverage  # noqa: F401
from testing.objects.coverage.AppBenchmark import AppBenchmark  # noqa: F401
from testing.objects.coverage.TestCoveragePlan import TestCoveragePlan  # noqa: F401


COVERAGE_CLASSES = [StandardComputerBudget, AppHierarchyNode, ModuleCoverage,
                    AppBenchmark, TestCoveragePlan]
