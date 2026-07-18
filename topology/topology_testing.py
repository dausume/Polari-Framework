"""
@cross-cutting
@module topology.topology_testing
@tags @xc:bindings

Testing tied into the topology (tt-11, Dustin 2026-07-18): the
topology graph doubles as the PROGRESS VISUALIZATION of testing —
module circles and hosts go red on failing tests / green when every
suite passes, and host/engine links go green when the FOUNDATIONAL
integration pings succeed (connectivity only, never functionality),
annotated with the protocol used and whether the channel is secured.

Two observed-state row classes (runs are NEVER seeded):
  TopologyTestRun  — one selftest-suite execution (module, suite,
                     parsed X/Y checks, honest output tail).
  IntegrationPing  — one connectivity check (machine / dep-edge /
                     connection) with protocol + secured + evidence.

Pure aggregation lives here (stdlib-only, manager duck-typed); the
subprocess runner + live pings live in topology_testing_api.

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence)
  - topology.topology_testing_api / topology.selftest_testing
  - polari-platform-angular /testing page + topology-graph-view
"""

import os
import re

from objectTreeDecorators import treeObject, treeObjectInit

TEST_STATUSES = ('pass', 'fail', 'error', 'timeout')
PING_STATUSES = ('ok', 'failed', 'unpingable', 'static-artifact')
MODULE_TEST_STATES = ('pass', 'fail', 'never-run', 'no-suites')


class TopologyTestRun(treeObject):
    """One executed selftest suite — observed state, never seeded."""

    @treeObjectInit
    def __init__(
        self,
        # Unique key, conventionally '<suite>@<ran_at>'.
        name: str = '',
        # Top-level module directory ('aquaponics').
        module_name: str = '',
        # Python module path of the suite
        # ('aquaponics.selftest_pot').
        suite: str = '',
        # TEST_STATUSES entry.
        status: str = 'error',
        checks_passed: int = 0,
        checks_total: int = 0,
        # Last lines of stdout/stderr — the honest receipt.
        output_tail: str = '',
        ran_at: str = '',
        topology_name: str = '',
        manager=None,
    ):
        self.name = name
        self.module_name = module_name
        self.suite = suite
        self.status = status
        self.checks_passed = checks_passed
        self.checks_total = checks_total
        self.output_tail = output_tail
        self.ran_at = ran_at
        self.topology_name = topology_name


class IntegrationPing(treeObject):
    """One foundational connectivity check — 'just pinging', never
    functionality — with the protocol and its security notated."""

    @treeObjectInit
    def __init__(
        self,
        # Unique key, conventionally '<subject>@<checked_at>'.
        name: str = '',
        # 'machine' | 'dep-edge' | 'connection'.
        kind: str = 'machine',
        # PolariNodeMachine.name / ModuleDependencyEdge.name /
        # ServiceConnection.name.
        subject: str = '',
        # The URL/address actually pinged ('' when nothing to ping).
        target: str = '',
        # 'https' | 'http' | 'in-process' | 'file' | ''.
        protocol: str = '',
        secured: bool = False,
        # Plain words on HOW it is (not) secured ('TLS',
        # 'plaintext HTTP on the docker network', ...).
        security_note: str = '',
        # PING_STATUSES entry.
        status: str = 'unpingable',
        evidence: str = '',
        checked_at: str = '',
        topology_name: str = '',
        manager=None,
    ):
        self.name = name
        self.kind = kind
        self.subject = subject
        self.target = target
        self.protocol = protocol
        self.secured = secured
        self.security_note = security_note
        self.status = status
        self.evidence = evidence
        self.checked_at = checked_at
        self.topology_name = topology_name


# ---------------------------------------------------------------------
# Pure helpers (stdlib-only; the selftest runs these directly).
# ---------------------------------------------------------------------

#: Every selftest in this codebase ends with 'X/Y checks passed'.
_RESULT_RE = re.compile(r'(\d+)\s*/\s*(\d+)\s+checks\s+passed')


def parse_suite_output(text):
    """(passed, total) from a suite's output, or None when the suite
    died before printing its tally — callers treat None as error."""
    matches = _RESULT_RE.findall(text or '')
    if not matches:
        return None
    passed, total = matches[-1]
    return int(passed), int(total)


def protocol_of(url):
    """(protocol, secured, security_note) for a ping target URL."""
    if not url:
        return '', False, ''
    if url.startswith('https://'):
        return 'https', True, 'TLS'
    if url.startswith('http://'):
        return 'http', False, 'plaintext HTTP (unencrypted)'
    return url.split(':', 1)[0], False, 'unknown scheme'


def _framework_root():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def discover_suites(root=None):
    """{module_dir: [suite python-module paths]} — the same
    selftest_*.py discovery rule the pol CLI uses. Scans BOTH import
    roots (mp-1): the framework root and modules/ (relocated feature
    modules keep their import names there)."""
    root = root or _framework_root()
    suites = {}
    scan_roots = [root, os.path.join(root, 'modules')]
    for scan_root in scan_roots:
        if not os.path.isdir(scan_root):
            continue
        for entry in sorted(os.listdir(scan_root)):
            directory = os.path.join(scan_root, entry)
            if (entry.startswith(('.', '_')) or entry == 'modules'
                    or not os.path.isdir(directory)):
                continue
            found = sorted(
                f'{entry}.{filename[:-3]}'
                for filename in os.listdir(directory)
                if filename.startswith('selftest_')
                and filename.endswith('.py'))
            if found:
                suites.setdefault(entry, found)
    return suites


def _rows(manager, class_name):
    table = (getattr(manager, 'objectTables', None) or {}).get(
        class_name, {})
    return list(table.values()) if isinstance(table, dict) else list(table)


def _latest(rows, key_attr, stamp_attr):
    latest = {}
    for row in rows:
        key = getattr(row, key_attr, '')
        stamp = getattr(row, stamp_attr, '')
        if key not in latest or stamp > getattr(
                latest[key], stamp_attr, ''):
            latest[key] = row
    return latest


def module_test_state(suites, latest_runs):
    """One module's derived state from its suites + latest runs."""
    if not suites:
        return 'no-suites'
    ran = [latest_runs.get(s) for s in suites]
    if all(r is None for r in ran):
        return 'never-run'
    if any(r is not None and getattr(r, 'status', '') != 'pass'
           for r in ran):
        return 'fail'
    if any(r is None for r in ran):
        return 'fail'  # partially run — honest: not everything passed
    return 'pass'


def testing_report(manager, topology_name, suites=None):
    """Everything the Testing tab + the colored topology draw:
    per-module derived test state, per-instance/host rollups, and
    the latest integration pings with protocol/security."""
    suites = suites if suites is not None else discover_suites()
    latest_runs = _latest(
        _rows(manager, 'TopologyTestRun'), 'suite', 'ran_at')

    # module -> instances carrying it (top-level match: the
    # assignment 'materialsScience.fem' rides the materialsScience
    # suites).
    placements = {}
    for asg in _rows(manager, 'ModuleAssignment'):
        if getattr(asg, 'topology_name', '') != topology_name:
            continue
        if getattr(asg, 'state', '') in ('disabled', 'transient'):
            continue  # transient ghosts (tt-13) are inert
        top = getattr(asg, 'module_name', '').split('.')[0]
        placements.setdefault(top, set()).add(
            getattr(asg, 'instance_name', ''))

    modules = []
    for module in sorted(set(suites) | set(placements)):
        module_suites = suites.get(module, [])
        state = module_test_state(module_suites, latest_runs)
        modules.append({
            'module': module,
            'state': state,
            'instances': sorted(placements.get(module, set())),
            'suites': [{
                'suite': s,
                'status': getattr(latest_runs.get(s), 'status',
                                  'never-run'),
                'checksPassed': getattr(latest_runs.get(s),
                                        'checks_passed', 0),
                'checksTotal': getattr(latest_runs.get(s),
                                       'checks_total', 0),
                'ranAt': getattr(latest_runs.get(s), 'ran_at', ''),
                'outputTail': getattr(latest_runs.get(s),
                                      'output_tail', ''),
            } for s in module_suites],
        })

    # Instance rollup: fail if ANY of its modules fail; pass when
    # every suite-bearing module passes (and there is at least one);
    # unknown otherwise (nothing to say — honesty over green paint).
    by_state = {m['module']: m['state'] for m in modules}
    instance_states = {}
    for module, instances in placements.items():
        for instance in instances:
            states = instance_states.setdefault(instance, [])
            states.append(by_state.get(module, 'no-suites'))

    def rollup(states):
        testable = [s for s in states if s in ('pass', 'fail',
                                               'never-run')]
        if any(s == 'fail' for s in testable):
            return 'fail'
        if testable and all(s == 'pass' for s in testable):
            return 'pass'
        return 'unknown'

    instances = {name: rollup(states)
                 for name, states in instance_states.items()}

    latest_pings = _latest(
        [p for p in _rows(manager, 'IntegrationPing')
         if getattr(p, 'topology_name', '') == topology_name],
        'subject', 'checked_at')
    links = [{
        'kind': getattr(p, 'kind', ''),
        'subject': subject,
        'target': getattr(p, 'target', ''),
        'protocol': getattr(p, 'protocol', ''),
        'secured': getattr(p, 'secured', False),
        'securityNote': getattr(p, 'security_note', ''),
        'status': getattr(p, 'status', ''),
        'evidence': getattr(p, 'evidence', ''),
        'checkedAt': getattr(p, 'checked_at', ''),
    } for subject, p in sorted(latest_pings.items())]

    # Host rollup: its instances' states + its own machine ping.
    machine_of = {getattr(i, 'name', ''): getattr(i, 'machine_name',
                                                  '')
                  for i in _rows(manager, 'InstanceDefinition')
                  if getattr(i, 'topology_name', '') == topology_name}
    host_states = {}
    for instance, state in instances.items():
        machine = machine_of.get(instance, '')
        if machine:
            host_states.setdefault(machine, []).append(state)
    hosts = {}
    ping_by_subject = {p['subject']: p for p in links
                       if p['kind'] == 'machine'}
    for machine, states in host_states.items():
        state = rollup([s for s in states if s != 'unknown']
                       or ['unknown'])
        ping = ping_by_subject.get(machine)
        if ping and ping['status'] == 'failed':
            state = 'fail'
        hosts[machine] = state

    return {'ok': True, 'topology': topology_name,
            'modules': modules, 'instances': instances,
            'hosts': hosts, 'links': links}
