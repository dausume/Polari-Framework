"""
@module testing.matrix_runner

acct-0: run the capability matrix (or a category/name slice) and
produce ONE run record — the source both the CheckRun tree objects
and the YAML report project from.

With a manager, the run is also written INTO the tree
([[object-coherence]]): every catalog entry is synced to a
CapabilityCheck row (registration layer), each row's last_* fields
are updated from its result, and the run persists as a CheckRun.
Without a manager (the CI entrypoint testing.run_matrix), the same
record still emits the YAML report — same data, no second
bookkeeping.

blocking_green: no BLOCKING check in the run has status 'fail'.
skip-honest does not fail the gate — an honestly-reported unrunnable
check is absence, not breakage; its suggestion names the knob that
would make it runnable.
"""

import json
import os
import shutil
import subprocess
import time
from datetime import datetime, timezone

from testing.check_catalog import FRAMEWORK_ROOT, catalog_checks
from testing.check_runners import run_check
from testing.report_yaml import write_report


def _now_iso():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def _git_sha(repo_dir):
    if shutil.which('git') is None:
        return 'unknown (no git binary)'
    try:
        proc = subprocess.run(
            ['git', 'rev-parse', '--short', 'HEAD'], cwd=repo_dir,
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            text=True, timeout=10)
        return proc.stdout.strip() or 'unknown'
    except Exception:
        return 'unknown'


def _containers_up():
    if shutil.which('docker') is None:
        return ['unknown (no docker binary in this environment)']
    try:
        proc = subprocess.run(
            ['docker', 'ps', '--format', '{{.Names}}'],
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            text=True, timeout=10)
        return sorted(n for n in proc.stdout.splitlines() if n)
    except Exception:
        return ['unknown (docker ps failed)']


def build_stamp():
    return {'kind': ('test' if os.environ.get('POLARI_TEST_BUILD')
                     else 'normal'),
            'deploy_env': os.environ.get('DEPLOY_ENV', ''),
            'git': {'framework': _git_sha(FRAMEWORK_ROOT)}}


def environment_stamp():
    return {'db_dialect': (os.environ.get('DATABASE_TYPE')
                           or 'sqlite').lower(),
            'polari_modules': os.environ.get('POLARI_MODULES', ''),
            'in_container': os.environ.get(
                'IN_DOCKER_CONTAINER', '') == 'true',
            'containers_up': _containers_up()}


def collect_coverage(results_dir, log=print):
    """acct-3: when POLARI_COVERAGE is on, combine the per-check
    parallel data files into test-results/coverage.json and return
    {percent, files, report} — None when the knob is off. The
    combined report only measures in-process python checks (docker
    fixtures run their own interpreters — stated, not hidden)."""
    from testing.check_runners import (
        coverage_data_file, coverage_enabled,
    )
    from testing.report_yaml import DEFAULT_RESULTS_DIR
    if not coverage_enabled():
        return None
    results_dir = results_dir or DEFAULT_RESULTS_DIR
    os.makedirs(results_dir, exist_ok=True)
    json_path = os.path.join(results_dir, 'coverage.json')
    env = dict(os.environ, COVERAGE_FILE=coverage_data_file())
    try:
        subprocess.run(['python3', '-m', 'coverage', 'combine'],
                       cwd=FRAMEWORK_ROOT, env=env, timeout=300,
                       stdout=subprocess.DEVNULL,
                       stderr=subprocess.STDOUT)
        subprocess.run(['python3', '-m', 'coverage', 'json',
                        '-o', json_path, '-q'],
                       cwd=FRAMEWORK_ROOT, env=env, timeout=300,
                       stdout=subprocess.DEVNULL,
                       stderr=subprocess.STDOUT)
        with open(json_path) as handle:
            totals = json.load(handle).get('totals', {})
        summary = {'percent': round(
                       totals.get('percent_covered', 0.0), 2),
                   'files': len(json.load(open(json_path))
                                .get('files', {})),
                   'report': json_path}
        log(f"[matrix] coverage {summary['percent']}% across "
            f"{summary['files']} files -> {json_path}")
        return summary
    except Exception as exc:
        log(f'[matrix] coverage collection failed: {exc}')
        return {'percent': None, 'files': 0,
                'error': f'{type(exc).__name__}: {exc}'}


def select_checks(category=None, names=None):
    entries = catalog_checks()
    if category:
        entries = [e for e in entries if e['category'] == category]
    if names:
        wanted = set(names)
        entries = [e for e in entries if e['name'] in wanted]
    return entries


def compute_totals(results):
    totals = {'pass': 0, 'fail': 0, 'skip_honest': 0}
    for row in results:
        totals[row['status'].replace('-', '_')] = totals.get(
            row['status'].replace('-', '_'), 0) + 1
    return totals


def compute_blocking_green(results):
    return not any(row['status'] == 'fail'
                   for row in results
                   if row['criticality'] == 'blocking')


def run_matrix(category=None, names=None, manager=None,
               results_dir=None, live_base_url=None, timeout=None,
               log=print):
    """Run the selected checks sequentially -> run record dict:
    {id, started_at, finished_at, build, environment, totals,
     blocking_green, results, report_path}."""
    entries = select_checks(category=category, names=names)
    run_id = time.strftime('%Y%m%d-%H%M%S') + f'-{os.getpid()}'
    started_at = _now_iso()
    log(f'[matrix] run {run_id}: {len(entries)} checks'
        + (f' (category={category})' if category else ''))
    results = []
    for index, entry in enumerate(entries, 1):
        row = run_check(entry, timeout=timeout,
                        live_base_url=live_base_url)
        results.append(row)
        log(f"[matrix] {index}/{len(entries)} {row['status']:11s} "
            f"{row['name']} ({row['duration_ms']}ms)")
    record = {'id': run_id, 'started_at': started_at,
              'finished_at': _now_iso(), 'build': build_stamp(),
              'environment': environment_stamp(),
              'totals': compute_totals(results),
              'blocking_green': compute_blocking_green(results),
              'results': results, 'report_path': '',
              'coverage': collect_coverage(results_dir, log=log)}
    record['report_path'] = write_report(record,
                                         results_dir=results_dir)
    if manager is not None:
        persist_run(manager, record)
    log(f"[matrix] totals {record['totals']} "
        f"blocking_green={record['blocking_green']} "
        f"report={record['report_path']}")
    return record


def sync_capability_checks(manager):
    """Registration layer: ensure every catalog entry has exactly one
    CapabilityCheck row (matched by name). Returns {name: row}."""
    from testing.capability_basis import CapabilityCheck
    existing = manager.objectTables.get('CapabilityCheck', {}) or {}
    by_name = {getattr(row, 'name', None): row
               for row in existing.values()}
    for entry in catalog_checks():
        if entry['name'] in by_name:
            continue
        by_name[entry['name']] = CapabilityCheck(
            manager=manager, name=entry['name'],
            category=entry['category'], kind=entry['kind'],
            criticality=entry['criticality'],
            runner_ref=entry['runner_ref'],
            description=entry['description'])
    return by_name


def _save(manager, instance):
    db = getattr(manager, 'db', None)
    if db is None:
        return
    try:
        db.saveInstanceInDB(instance)
    except Exception as exc:
        print(f'[matrix] persist {type(instance).__name__} failed: '
              f'{exc}', flush=True)


def persist_run(manager, record):
    """Write the run into the tree: CheckRun row + per-check last_*
    updates on the CapabilityCheck rows."""
    from testing.capability_basis import CheckRun
    rows = sync_capability_checks(manager)
    for result in record['results']:
        row = rows.get(result['name'])
        if row is None:
            continue
        row.last_status = result['status']
        row.last_evidence = result['evidence']
        row.last_run_at = record['finished_at']
        row.last_duration_ms = result['duration_ms']
        _save(manager, row)
    run = CheckRun(
        manager=manager, name=f"run-{record['id']}",
        started_at=record['started_at'],
        finished_at=record['finished_at'],
        build_json=json.dumps(record['build']),
        environment_json=json.dumps(record['environment']),
        totals_json=json.dumps(record['totals']),
        blocking_green=record['blocking_green'],
        results_json=json.dumps(record['results']),
        report_path=record['report_path'])
    _save(manager, run)
    return run


def exit_code_for(record):
    """The test-build runner's exit code mirrors blocking_green."""
    return 0 if record['blocking_green'] else 1
