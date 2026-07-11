"""
@module testing.check_catalog

acct-0: the registration layer — every existing test surface appears
in the capability matrix exactly once, by DISCOVERY, not by a hand
list that drifts:

  suite:<name>       tests/test_*.py unittest files (the container
                     suite run_tests.py discovers).
  selftest:<pkg>.<topic>
                     every <package>/selftest_*.py at package root.
  live:api-smoke     tests/live_api_smoke.py against a live server
                     (skip-honest when none is reachable).
  gate:normal-build-absence
                     the pinned assert that a NORMAL build carries
                     zero test machinery (testing.absence_probe).

Categories follow the plan's spine: substrate | transport | format |
twin | nocode | engine | module. Criticality: substrate/transport/
twin rows are blocking (plan §4) — blocking_green gates on them —
everything else is visible, non-blocking debt. New test files
auto-appear on the matrix at the defaults below; refine a row's
category/criticality here when a phase claims it.
"""

import os

FRAMEWORK_ROOT = os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))

# A package's selftests inherit its category ('module' if unlisted).
CATEGORY_BY_PACKAGE = {
    'polariDBmanagement': 'substrate',
    'polariDataTyping': 'substrate',
    'grpcbridge': 'transport',
    'polariRefs': 'twin',
    'polariPeers': 'twin',
    'simulationLocks': 'twin',
    'topology': 'twin',
    'polariNoCode': 'nocode',
    'matrices': 'engine',
    'simulations': 'engine',
    'simSpace': 'engine',
}

# tests/test_<stem>.py -> category.
CATEGORY_BY_SUITE = {
    'object_tree': 'substrate',
    'crude_api': 'transport',
    'api_contracts': 'transport',
    'api_honesty': 'transport',
    'api_sweep': 'transport',
    'api_profiler': 'transport',
    'createclass_api': 'nocode',
    'mathshapes': 'module',
    'modules_smoke': 'module',
}

BLOCKING_CATEGORIES = frozenset({'substrate', 'transport', 'twin'})

# Per-check criticality overrides (win over the category rule).
CRITICALITY_OVERRIDES = {
    # Known matcher drift (prf-test-suites 2026-07-11) — visible
    # debt, not a pipeline gate, until the profiler row is repaired.
    'suite:api-profiler': 'informational',
    # The spine must be able to test itself before anything gates
    # on it, and the normal-build absence is a Dustin non-negotiable.
    'selftest:testing.testing': 'blocking',
    'gate:normal-build-absence': 'blocking',
}

DEFAULT_LIVE_BASE_URL = 'https://api.prf.192.168.0.210.nip.io'


def _criticality(name, category):
    if name in CRITICALITY_OVERRIDES:
        return CRITICALITY_OVERRIDES[name]
    return ('blocking' if category in BLOCKING_CATEGORIES
            else 'informational')


def _entry(name, category, kind, runner_kind, runner_ref, description):
    return {'name': name, 'category': category, 'kind': kind,
            'criticality': _criticality(name, category),
            'runner_kind': runner_kind, 'runner_ref': runner_ref,
            'description': description}


def _suite_entries():
    tests_dir = os.path.join(FRAMEWORK_ROOT, 'tests')
    entries = []
    for fname in sorted(os.listdir(tests_dir)):
        if not (fname.startswith('test_') and fname.endswith('.py')):
            continue
        stem = fname[len('test_'):-len('.py')]
        entries.append(_entry(
            name='suite:' + stem.replace('_', '-'),
            category=CATEGORY_BY_SUITE.get(stem, 'module'),
            kind='in-process', runner_kind='unittest',
            runner_ref=f'python3 -m unittest tests.test_{stem}',
            description=f'Container-suite unittest file tests/{fname}.'))
    return entries


def _selftest_entries():
    entries = []
    for pkg in sorted(os.listdir(FRAMEWORK_ROOT)):
        pkg_dir = os.path.join(FRAMEWORK_ROOT, pkg)
        if (pkg.startswith('.') or pkg == 'tests'
                or not os.path.isdir(pkg_dir)
                or not os.path.isfile(
                    os.path.join(pkg_dir, '__init__.py'))):
            continue
        for fname in sorted(os.listdir(pkg_dir)):
            if not (fname.startswith('selftest_')
                    and fname.endswith('.py')):
                continue
            topic = fname[len('selftest_'):-len('.py')]
            module = f'{pkg}.selftest_{topic}'
            entries.append(_entry(
                name=f'selftest:{pkg}.{topic}',
                category=CATEGORY_BY_PACKAGE.get(pkg, 'module'),
                kind='in-process', runner_kind='selftest',
                runner_ref=f'python3 -m {module}',
                description=f'Module selftest {pkg}/{fname}.'))
    return entries


def catalog_checks():
    """The full check catalog, deterministically ordered
    (category, name). Pure data — no manager, no side effects."""
    entries = _suite_entries() + _selftest_entries()
    entries.append(_entry(
        name='live:api-smoke', category='transport', kind='live',
        runner_kind='live-smoke',
        runner_ref='python3 tests/live_api_smoke.py <base-url>',
        description='22-endpoint smoke against a LIVE server. '
                    'skip-honest when no server is reachable.'))
    entries.append(_entry(
        name='gate:normal-build-absence', category='module',
        kind='in-process', runner_kind='absence',
        runner_ref='python3 -m testing.absence_probe',
        description='Pinned: a NORMAL build (no POLARI_TEST_BUILD, '
                    'testing absent from POLARI_MODULES) registers '
                    'zero test machinery — no classes, tables, '
                    'CRUDE surface, or /api/accountability route.'))
    entries.sort(key=lambda e: (e['category'], e['name']))
    return entries


def catalog_by_name():
    return {e['name']: e for e in catalog_checks()}
