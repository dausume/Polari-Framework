"""
Selftest for resources.custom.node_resources (res-1).

Run from polari-framework/:
  python3 -m resources.node_resources_selftest

Stdlib-only: a fake manager with a duck-typed hostSys and
SimpleNamespace PolariNodeMachine rows — no DB, no falcon, no
treeObject machinery. Covers: local specs from isoSys, local refresh
onto the row (observed-local + mem_gb mirror), remote pull via a
mocked /system-info (observed-remote), honest failure paths
(unreachable URL leaves the row untouched; missing system_info_url
names the knob), the push-ingest path, response-shape parsing, the
inventory rollup, and graph_payload carrying the new fields.
"""

import copy
import types

from resources.custom.node_resources import (
    fetch_remote_specs, ingest_node_specs, inventory, local_node_specs,
    machine_resources_dict, parse_system_info, refresh_local_machine,
)
from topology.topology_analysis import graph_payload
from topology.topology_seed import (
    SEED_INSTANCE_DEFINITIONS, SEED_MODULE_ASSIGNMENTS,
    SEED_MODULE_DEPENDENCY_EDGES, SEED_NODE_MACHINES,
    SEED_ORCHESTRATION_TARGETS, SEED_SERVICE_CONNECTIONS,
    SEED_TOPOLOGY_DEFINITIONS,
)

_results = []


def check(label, cond, extra=''):
    _results.append((label, bool(cond)))
    print(f'{"PASS" if cond else "FAIL"}: {label}'
          + (f' — {extra}' if extra and not cond else ''))


class FakeHostSys:
    """Duck-typed isoSys: tuple-valued live metrics, refreshMetrics."""

    def __init__(self):
        self.numLogicalCPUs = 8
        self.numPhysicalCPUs = 4
        self.totalMainMemoryInBytes = 16 * 1024 ** 3
        self.availableMainMemoryInBytes = (6 * 1024 ** 3, 'ts')
        self.percentMainMemoryUsed = (62.5, 'ts')
        self.currentCpuPercent = 12.0
        self.refreshed = 0

    def refreshMetrics(self):
        self.refreshed += 1


class FakeDB:
    def __init__(self):
        self.saved = []

    def saveInstanceInDB(self, row):
        self.saved.append(getattr(row, 'name', ''))


def _rows(seed_list):
    out = {}
    for s in seed_list:
        row = types.SimpleNamespace(**copy.deepcopy(s))
        # class defaults the fake rows would get from treeObject init
        for field, default in (
                ('logical_cpus', 0), ('physical_cpus', 0),
                ('total_ram_mb', 0.0), ('available_ram_mb', 0.0),
                ('total_disk_mb', 0.0), ('free_disk_mb', 0.0),
                ('cgroup_ram_limit_mb', 0.0),
                ('load_snapshot_json', '{}'),
                ('resource_source', 'unknown'),
                ('resource_observed_at', ''),
                ('system_info_url', '')):
            if not hasattr(row, field):
                setattr(row, field, default)
        out[s['name']] = row
    return out


def _mgr():
    return types.SimpleNamespace(
        hostSys=FakeHostSys(),
        db=FakeDB(),
        objectTables={
            'PolariNodeMachine': _rows(SEED_NODE_MACHINES),
            'OrchestrationTarget': _rows(SEED_ORCHESTRATION_TARGETS),
            'TopologyDefinition': _rows(SEED_TOPOLOGY_DEFINITIONS),
            'InstanceDefinition': _rows(SEED_INSTANCE_DEFINITIONS),
            'ModuleAssignment': _rows(SEED_MODULE_ASSIGNMENTS),
            'ModuleDependencyEdge': _rows(SEED_MODULE_DEPENDENCY_EDGES),
            'ServiceConnection': _rows(SEED_SERVICE_CONNECTIONS),
            'TopologyObservation': {},
        })


REMOTE_DOC = [{'system-info': {
    'platform': {'arch': 'x86_64', 'systemType': 'Linux'},
    'cpu': {'numLogicalCPUs': 6, 'numPhysicalCPUs': 6,
            'currentUsagePercent': 3.5},
    'memory': {'total': 8 * 1024 ** 3, 'available': 5 * 1024 ** 3,
               'percentUsed': 37.5, 'cgroupLimitBytes': 0},
    'disk': {'totalBytes': 200 * 1024 ** 3,
             'freeBytes': 120 * 1024 ** 3},
}}]


def main():
    mgr = _mgr()

    # --- local specs from the duck-typed isoSys ----------------------
    specs = local_node_specs(mgr, db_dir='.')
    check('local specs: cores > 0', specs['logical_cpus'] == 8)
    check('local specs: physical cores carried',
          specs['physical_cpus'] == 4)
    check('local specs: RAM > 0 (MB)',
          specs['total_ram_mb'] == 16 * 1024)
    check('local specs: disk > 0 (real shutil probe)',
          specs['total_disk_mb'] > 0 and specs['free_disk_mb'] > 0)
    check('local specs: isoSys refreshed, not re-probed',
          mgr.hostSys.refreshed >= 1)

    # --- local refresh onto the row -----------------------------------
    report = refresh_local_machine(mgr, db_dir='.')
    row = mgr.objectTables['PolariNodeMachine']['staging-a']
    check('refresh_local: ok + picked the ssh_alias=="" row',
          report.get('ok') and report.get('node') == 'staging-a')
    check('refresh_local: row populated',
          row.logical_cpus == 8 and row.total_ram_mb == 16 * 1024)
    check('refresh_local: source flipped to observed-local',
          row.resource_source == 'observed-local'
          and row.resource_observed_at != '')
    check('refresh_local: mem_gb back-compat mirror',
          row.mem_gb == 16.0)
    check('refresh_local: row saved to DB',
          'staging-a' in mgr.db.saved)

    # --- honest refusal without a hostSys -----------------------------
    bare = _mgr()
    bare.hostSys = None
    bare_report = refresh_local_machine(bare, db_dir='/nonexistent')
    bare_row = bare.objectTables['PolariNodeMachine']['staging-a']
    check('refresh_local without isoSys: honest error, row untouched',
          not bare_report.get('ok')
          and bare_row.resource_source == 'unknown')

    # --- remote pull ---------------------------------------------------
    isle = mgr.objectTables['PolariNodeMachine']['isle-core']
    isle.system_info_url = ''  # seed carries the knob; test without it
    no_url = fetch_remote_specs(mgr, 'isle-core')
    check('remote pull without the knob: refused, names the knob',
          not no_url.get('ok')
          and 'system_info_url' in str(no_url.get('suggestion', {})))

    isle.system_info_url = 'http://192.168.0.24:9500'
    pulled = fetch_remote_specs(
        mgr, 'isle-core', fetch=lambda url, timeout=5: REMOTE_DOC)
    check('remote pull: ok + observed-remote',
          pulled.get('ok') and isle.resource_source == 'observed-remote')
    check('remote pull: specs mapped (6 cores / 8G / 200G disk)',
          isle.logical_cpus == 6
          and isle.total_ram_mb == 8 * 1024
          and isle.total_disk_mb == 200 * 1024)
    check('remote pull: /system-info suffix appended to the base URL',
          pulled.get('url', '').endswith('/system-info'))
    check('remote pull: mem_gb mirrored', isle.mem_gb == 8.0)

    def _boom(url, timeout=5):
        raise OSError('connection refused')

    before = (isle.logical_cpus, isle.resource_source)
    failed = fetch_remote_specs(mgr, 'isle-core', fetch=_boom)
    check('remote pull failure: honest error, prior observation kept',
          not failed.get('ok')
          and (isle.logical_cpus, isle.resource_source) == before)

    missing = fetch_remote_specs(mgr, 'no-such-node')
    check('remote pull of an unknown node: honest 404-style error',
          not missing.get('ok') and 'no PolariNodeMachine'
          in missing.get('error', ''))

    # --- push ingest ----------------------------------------------------
    light = mgr.objectTables['PolariNodeMachine']['lightweight']
    pushed = ingest_node_specs(mgr, 'lightweight', REMOTE_DOC[0])
    check('push ingest (system-info shape): observed-push',
          pushed.get('ok') and light.resource_source == 'observed-push'
          and light.logical_cpus == 6)
    flat = ingest_node_specs(mgr, 'lightweight', {
        'logical_cpus': 4, 'physical_cpus': 4,
        'total_ram_mb': 7680.0, 'available_ram_mb': 5000.0,
        'total_disk_mb': 100000.0, 'free_disk_mb': 60000.0})
    check('push ingest (flat shape): accepted',
          flat.get('ok') and light.logical_cpus == 4)
    empty = ingest_node_specs(mgr, 'lightweight', {'noise': 1})
    check('push ingest of an empty payload: refused',
          not empty.get('ok'))

    # --- parsing shapes --------------------------------------------------
    inner = REMOTE_DOC[0]['system-info']
    check('parse: list / bare / inner shapes all normalize the same',
          parse_system_info(REMOTE_DOC)
          == parse_system_info(REMOTE_DOC[0])
          == parse_system_info(inner))
    check('parse: unrecognized document -> None',
          parse_system_info('nonsense') is None
          and parse_system_info(None) is None)

    # --- inventory + serialization ---------------------------------------
    inv = inventory(mgr)
    check('inventory: all 3 seeded nodes present',
          len(inv['nodes']) == 3 and inv['ok'])
    check('inventory: observed count == 3 after the observations above',
          inv['observed'] == 3 and inv['unknown'] == [])
    isle_view = machine_resources_dict(isle)
    check('node view: headroom fractions computed',
          isle_view['headroom']['ramFraction'] == 0.625
          and isle_view['headroom']['diskFraction'] == 0.6)
    fresh_inv = inventory(_mgr())
    check('inventory before observation: honest unknown list',
          fresh_inv['observed'] == 0
          and len(fresh_inv['unknown']) == 3)

    # --- topology graph carries the fields --------------------------------
    graph = graph_payload(mgr, 'staging-a')
    machines = {m['name']: m for m in graph['machines']}
    check('graph_payload: resource fields surface for the Topology tab',
          machines['staging-a']['resourceSource'] == 'observed-local'
          and machines['staging-a']['totalRamMb'] == 16 * 1024
          and machines['isle-core']['logicalCpus'] == 6)

    failures = [label for label, ok in _results if not ok]
    print(f'\n{len(_results) - len(failures)}/{len(_results)} checks '
          f'passed' + (f'; FAILURES: {failures}' if failures else ''))
    raise SystemExit(1 if failures else 0)


if __name__ == '__main__':
    main()
