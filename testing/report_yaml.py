"""
@module testing.report_yaml

acct-0: the pipeline-readable report — every CheckRun ALSO serializes
to `test-results/test-report.yaml` (plus a timestamped copy per run)
so CI can read the outcome without touching the API.

The YAML is a faithful PROJECTION of the run record the CheckRun
object carries — never a second bookkeeping system. `blocking_green`
is the single field a pipeline gates on; the test-build runner's
exit code mirrors it. Schema changes bump `report_version` so later
pipelines can evolve without breaking older readers.
"""

import os

import yaml

from testing.check_catalog import FRAMEWORK_ROOT

REPORT_VERSION = 1
DEFAULT_RESULTS_DIR = os.path.join(FRAMEWORK_ROOT, 'test-results')


def report_dict(run_record):
    """Project a matrix run record into the versioned report schema
    (plan §1)."""
    return {
        'report_version': REPORT_VERSION,
        'run': {
            'id': run_record['id'],
            'started_at': run_record['started_at'],
            'finished_at': run_record['finished_at'],
            'build': run_record['build'],
            'environment': run_record['environment'],
            'totals': run_record['totals'],
            'blocking_green': run_record['blocking_green'],
        },
        'checks': [
            {'name': row['name'], 'category': row['category'],
             'criticality': row['criticality'],
             'status': row['status'],
             'duration_ms': row['duration_ms'],
             'evidence': row['evidence']}
            for row in run_record['results']
        ],
    }


def write_report(run_record, results_dir=None):
    """Write test-report.yaml + the per-run timestamped copy.
    Returns the stable report path."""
    results_dir = results_dir or DEFAULT_RESULTS_DIR
    os.makedirs(results_dir, exist_ok=True)
    payload = yaml.safe_dump(report_dict(run_record),
                             sort_keys=False, allow_unicode=True)
    stable = os.path.join(results_dir, 'test-report.yaml')
    stamped = os.path.join(results_dir,
                           f"test-report-{run_record['id']}.yaml")
    for path in (stable, stamped):
        with open(path, 'w') as handle:
            handle.write(payload)
    return stable
