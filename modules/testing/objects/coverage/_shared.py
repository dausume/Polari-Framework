"""@module testing.objects.coverage._shared — what the coverage row classes share (constants, seeds, helpers); split from coverage_basis.py (sap-2c)."""

COVERAGE_VERDICTS = ('covered-standard', 'covered-distributed',
                     'covered-large-host', 'uncovered')
APP_NODE_KINDS = ('app', 'instance', 'module')
FIDELITY_VALUES = ('declared', 'benchmark')
SEED_STANDARD_COMPUTER_BUDGETS = [{
    'name': 'standard', 'cores': 2, 'vcpus': 4, 'ram_mb': 4096.0, 'disk_mb': 32768.0,
    'boot_timeout_s': 900,
    'notes': "PLACEHOLDER numbers (his '2 core, 4 vcpu?' 2026-09-08; RAM/disk assumed) — "
             "decision D1 of the coverage plan sets them; every verdict cites this row.",
}]
