"""
@module testing.check_runners

acct-0: run ONE catalog entry and return an honest result row.

Runners WRAP the existing surfaces — zero test duplication:
  unittest    subprocess `python3 -m unittest tests.test_<x>`;
              counts parsed from the unittest summary.
  selftest    subprocess `python3 -m <pkg>.selftest_<x>`; the uniform
              convention prints 'X/Y passed' and exits nonzero on
              failure — the exit code is authoritative, the counts
              are evidence.
  live-smoke  probes the base URL first; unreachable = skip-honest
              WITH the suggestion naming the knob/compose that would
              make it runnable ([[knobs-and-suggestions]]) — never
              silently green, never silently missing.
  absence     `python3 -m testing.absence_probe` in a scrubbed env
              (no POLARI_TEST_BUILD / POLARI_MODULES): the pinned
              normal-build absence assert.

Result row: {name, category, kind, criticality, status, duration_ms,
evidence, passed, total} — the same fields CheckRun.results_json and
the YAML report carry.
"""

import os
import re
import ssl
import subprocess
import time
import urllib.request

from testing.check_catalog import DEFAULT_LIVE_BASE_URL, FRAMEWORK_ROOT

DEFAULT_TIMEOUT_S = int(
    os.environ.get('POLARI_CHECK_TIMEOUT') or 900)
_ANSI = re.compile(r'\x1b\[[0-9;]*m')
_COUNTS = re.compile(r'(\d+)\s*/\s*(\d+)')
_UNITTEST_RAN = re.compile(r'^Ran (\d+) tests? in', re.MULTILINE)
_UNITTEST_FAILED = re.compile(
    r'^FAILED \((?:failures=(\d+))?(?:, )?(?:errors=(\d+))?\)',
    re.MULTILINE)

LIVE_SMOKE_SUGGESTION = (
    'No live server reachable. Start staging '
    '(polari-rf-node: ./staging-setup.sh / '
    'docker-compose.staging-nip.yml) or point '
    'POLARI_SMOKE_BASE_URL at a running instance.')


def coverage_enabled():
    """acct-3: the coverage knob — POLARI_COVERAGE=true wraps every
    python subprocess check in `coverage run --parallel-mode` and
    the matrix combines the data files into one report per run."""
    raw = (os.environ.get('POLARI_COVERAGE') or '').strip().lower()
    return raw in ('1', 'true', 'yes', 'on')


def coverage_data_file():
    return os.path.join(FRAMEWORK_ROOT, 'test-results', '.coverage')


def _subprocess_env(scrub_test_build=False):
    env = dict(os.environ)
    env['PYTHONUNBUFFERED'] = '1'
    modules_dir = os.path.join(FRAMEWORK_ROOT, 'modules')
    env['PYTHONPATH'] = os.pathsep.join(
        [FRAMEWORK_ROOT, modules_dir]
        + ([env['PYTHONPATH']] if env.get('PYTHONPATH') else []))
    if coverage_enabled():
        env['COVERAGE_FILE'] = coverage_data_file()
    if scrub_test_build:
        env.pop('POLARI_TEST_BUILD', None)
        env.pop('POLARI_MODULES', None)
    return env


def _maybe_coverage(cmd):
    """Rewrite `python3 [-m mod | script]` to run under coverage.
    Docker-fixture checks measure nothing extra (the containers run
    their own interpreters) — honest scope: in-process python only."""
    if not coverage_enabled() or cmd[:1] != ['python3']:
        return cmd
    prefix = ['python3', '-m', 'coverage', 'run', '--parallel-mode',
              '--source', FRAMEWORK_ROOT]
    if cmd[1:2] == ['-m']:
        return prefix + ['-m'] + cmd[2:]
    return prefix + cmd[1:]


def _run(cmd, timeout, scrub_test_build=False):
    """(exit_code, merged_output, duration_ms) — never raises."""
    start = time.monotonic()
    cmd = _maybe_coverage(cmd)
    try:
        proc = subprocess.run(
            cmd, cwd=FRAMEWORK_ROOT, timeout=timeout,
            env=_subprocess_env(scrub_test_build=scrub_test_build),
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, errors='replace')
        code, output = proc.returncode, proc.stdout or ''
    except subprocess.TimeoutExpired as exc:
        raw = exc.stdout or b''
        if isinstance(raw, bytes):
            raw = raw.decode(errors='replace')
        code, output = -1, raw + f'\n[timeout after {timeout}s]'
    except OSError as exc:
        code, output = -1, f'[could not launch {cmd!r}: {exc}]'
    duration_ms = int((time.monotonic() - start) * 1000)
    return code, _ANSI.sub('', output), duration_ms


def _tail(output, limit=1200):
    output = output.strip()
    return output[-limit:] if len(output) > limit else output


def _selftest_counts(output):
    """Last 'X/Y' pair near the end of a selftest's output — the
    'X/Y passed' summary line the shared check() idiom prints."""
    tail_lines = output.strip().splitlines()[-15:]
    pairs = _COUNTS.findall('\n'.join(tail_lines))
    if not pairs:
        return None, None
    passed, total = pairs[-1]
    return int(passed), int(total)


def _row(entry, status, duration_ms, evidence, passed=None,
         total=None):
    return {'name': entry['name'], 'category': entry['category'],
            'kind': entry['kind'],
            'criticality': entry['criticality'], 'status': status,
            'duration_ms': duration_ms, 'evidence': evidence,
            'passed': passed, 'total': total}


def _run_selftest(entry, timeout, scrub_test_build=False):
    module = entry['runner_ref'].split()[-1]
    code, output, duration_ms = _run(
        ['python3', '-m', module], timeout,
        scrub_test_build=scrub_test_build)
    passed, total = _selftest_counts(output)
    if code == 0:
        counts = (f'{passed}/{total} checks passed'
                  if total is not None else 'exit 0 (no count line)')
        return _row(entry, 'pass', duration_ms, counts, passed, total)
    return _row(entry, 'fail', duration_ms,
                f'exit {code}; ' + _tail(output), passed, total)


def _run_unittest(entry, timeout):
    module = entry['runner_ref'].split()[-1]
    code, output, duration_ms = _run(
        ['python3', '-m', 'unittest', module], timeout)
    ran = _UNITTEST_RAN.search(output)
    total = int(ran.group(1)) if ran else None
    failed = _UNITTEST_FAILED.search(output)
    bad = sum(int(g) for g in failed.groups() if g) if failed else 0
    passed = (total - bad) if total is not None else None
    if code == 0:
        return _row(entry, 'pass', duration_ms,
                    f'{total} tests OK' if total is not None
                    else 'exit 0', passed, total)
    return _row(entry, 'fail', duration_ms,
                f'exit {code}; ' + _tail(output), passed, total)


def _live_server_reachable(base_url, timeout_s=5):
    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    try:
        urllib.request.urlopen(base_url + '/api/shapes',
                               timeout=timeout_s, context=context)
        return True
    except Exception:
        return False


def _run_live_smoke(entry, timeout, base_url=None):
    base_url = (base_url or os.environ.get('POLARI_SMOKE_BASE_URL')
                or DEFAULT_LIVE_BASE_URL).rstrip('/')
    if not _live_server_reachable(base_url):
        return _row(entry, 'skip-honest', 0,
                    f'{base_url} unreachable. {LIVE_SMOKE_SUGGESTION}')
    code, output, duration_ms = _run(
        ['python3', 'tests/live_api_smoke.py', base_url], timeout)
    passed, total = _selftest_counts(output)
    if code == 0:
        return _row(entry, 'pass', duration_ms,
                    f'{passed}/{total} live checks on {base_url}',
                    passed, total)
    return _row(entry, 'fail', duration_ms,
                f'exit {code}; ' + _tail(output), passed, total)


def _run_callable(entry):
    """runner_ref 'module:function' -> the callable returns a
    partial row {status, evidence[, passed, total]}; identity +
    timing added here. The callable owns its own honesty
    (skip-honest + suggestion when its substrate isn't declared)."""
    import importlib
    start = time.monotonic()
    try:
        module_name, _, fn_name = entry['runner_ref'].partition(':')
        fn = getattr(importlib.import_module(module_name), fn_name)
        partial = fn()
    except Exception as exc:
        partial = {'status': 'fail',
                   'evidence': f'check callable crashed: '
                               f'{type(exc).__name__}: {exc}'}
    duration_ms = int((time.monotonic() - start) * 1000)
    return _row(entry, partial['status'], duration_ms,
                partial.get('evidence', ''),
                partial.get('passed'), partial.get('total'))


def run_check(entry, timeout=None, live_base_url=None):
    """Execute one catalog entry -> result row. Never raises."""
    timeout = timeout or DEFAULT_TIMEOUT_S
    kind = entry['runner_kind']
    if kind == 'unittest':
        return _run_unittest(entry, timeout)
    if kind == 'selftest':
        return _run_selftest(entry, timeout)
    if kind == 'live-smoke':
        return _run_live_smoke(entry, timeout,
                               base_url=live_base_url)
    if kind == 'absence':
        return _run_selftest(entry, timeout, scrub_test_build=True)
    if kind == 'callable':
        return _run_callable(entry)
    return _row(entry, 'fail', 0,
                f"unknown runner_kind {kind!r} — catalog bug")
