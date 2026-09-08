"""
@module testing.capability_basis

acct-0: the accountability spine — every critical capability is an
OBJECT in the tree, not a line in a log ([[object-coherence]]).

  CapabilityCheck  one named check per critical seam (a wrapped
                   existing suite/selftest, a live probe, or a gate
                   assert), carrying its category, criticality,
                   runner reference, and last observed status +
                   evidence.
  CheckRun         one execution of the matrix (or a filtered slice):
                   timestamped, environment- and build-stamped, with
                   the per-check result rows and the blocking_green
                   verdict a pipeline gates on.

TEST-BUILD ONLY: these classes register only when the `testing`
module is enabled (POLARI_TEST_BUILD / explicit POLARI_MODULES entry
— see polariApiServer.module_gating OPT_IN_PACKAGES). A normal build
has no tables, no CRUDE surface, no /api/accountability route; that
absence is itself asserted by testing.custom.absence_probe.
"""

from objectTreeDecorators import treeObject, treeObjectInit

CHECK_CATEGORIES = (
    'substrate', 'transport', 'format', 'twin', 'nocode', 'engine',
    'module',
)
CHECK_KINDS = ('in-process', 'live', 'compose')
CHECK_STATUSES = ('pass', 'fail', 'skip-honest', 'never-run')
CRITICALITIES = ('blocking', 'informational')


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
