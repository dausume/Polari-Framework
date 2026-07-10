"""
@cross-cutting
@module resources.node_resources
@tags @xc:bindings

Node resource inventory (res-1): every PolariNodeMachine carries the
REAL resources of the device it represents — cores, RAM, disk —
bridging the previously disconnected isoSys (auto-detected host
specs, `manager.hostSys`) and the topology's PolariNodeMachine rows
(manual `mem_gb 0.0` until now).

Three honest acquisition paths, each labeled in `resource_source`:
  - observed-local  — this backend reads its own isoSys +
                      simulations.resource_monitor budget.
  - observed-remote — pulled from the node's `system_info_url` knob
                      (swarm's routing mesh makes bare ip:port
                      ambiguous, so a human names the address).
  - observed-push   — the node reported itself (pol-CLI over ssh,
                      mirroring `pol topology report`).
Anything else stays 'unknown' with a reason — never fabricated.

REUSE, not re-probe: memory budget comes from
simulations.resource_monitor.system_resources() (cgroup-aware — the
container budget IS what admission must respect), hardware counts
from isoSys (psutil). shutil.disk_usage supplies the disk total the
budget probe doesn't carry.

@consumers
  - resources.node_resources_api (/api/topology/resources*)
  - topology.topology_analysis.graph_payload (machine_dict fields)
  - resources.selftest_node_resources
@see /OVERLAP_MAP.md
"""

import json
import platform
import shutil
from datetime import datetime, timezone

_MB = 1024.0 * 1024.0

#: Normalized spec keys — the shared vocabulary of all three paths
#: and the ingest payload contract.
SPEC_KEYS = (
    'logical_cpus', 'physical_cpus', 'total_ram_mb',
    'available_ram_mb', 'total_disk_mb', 'free_disk_mb',
    'cgroup_ram_limit_mb', 'cpu_pct', 'ram_pct', 'arch',
)


def _mb(value):
    try:
        return round(float(value) / _MB, 1)
    except (TypeError, ValueError):
        return 0.0


def _first(value):
    """isoSys stores live metrics as (value, timestamp) tuples."""
    if isinstance(value, (list, tuple)) and value:
        return value[0]
    return value


def _now():
    return datetime.now(timezone.utc).isoformat()


def local_node_specs(manager, db_dir='/app/data'):
    """This device's specs from isoSys + the resource_monitor budget.

    One source of truth: hardware counts/totals from
    `manager.hostSys` (isoSys, psutil-backed), memory budget from
    `resource_monitor.system_resources()` (cgroup v2/v1/meminfo),
    disk from shutil. Missing pieces stay 0 (honest absence).
    """
    specs = {k: 0 for k in SPEC_KEYS}
    specs['arch'] = platform.machine()

    host = getattr(manager, 'hostSys', None)
    if host is not None:
        try:
            host.refreshMetrics()
        except Exception:
            pass  # stale isoSys numbers beat fabricated ones
        specs['logical_cpus'] = int(
            getattr(host, 'numLogicalCPUs', 0) or 0)
        specs['physical_cpus'] = int(
            getattr(host, 'numPhysicalCPUs', 0) or 0)
        specs['total_ram_mb'] = _mb(
            getattr(host, 'totalMainMemoryInBytes', 0))
        specs['available_ram_mb'] = _mb(_first(
            getattr(host, 'availableMainMemoryInBytes', 0)))
        specs['cpu_pct'] = float(
            getattr(host, 'currentCpuPercent', 0) or 0)
        specs['ram_pct'] = float(_first(
            getattr(host, 'percentMainMemoryUsed', 0)) or 0)

    try:
        from simulations.resource_monitor import system_resources
        budget = system_resources(db_dir=db_dir)
        mem = budget.get('memory') or {}
        if mem.get('limitBytes'):
            specs['cgroup_ram_limit_mb'] = _mb(mem['limitBytes'])
            # inside a limited container the cgroup budget is the
            # honest 'available' — the host view overstates it
            specs['available_ram_mb'] = _mb(mem.get('availableBytes'))
        elif not specs['available_ram_mb']:
            specs['available_ram_mb'] = _mb(mem.get('availableBytes'))
    except Exception:
        pass

    try:
        usage = shutil.disk_usage(db_dir)
        specs['total_disk_mb'] = _mb(usage.total)
        specs['free_disk_mb'] = _mb(usage.free)
    except OSError:
        pass
    return specs


def _machines(manager):
    tables = getattr(manager, 'objectTables', None) or {}
    return list((tables.get('PolariNodeMachine') or {}).values())


def _find_machine(manager, node_name=''):
    """By name; '' = the local host row (ssh_alias == '' convention)."""
    for m in _machines(manager):
        if node_name and getattr(m, 'name', '') == node_name:
            return m
        if not node_name and not getattr(m, 'ssh_alias', ''):
            return m
    return None


def _save(manager, row):
    try:
        manager.db.saveInstanceInDB(row)
    except Exception:
        pass  # in-memory row stays authoritative until next save


def apply_specs(machine, specs, source, observed_at=''):
    """Write normalized specs onto a PolariNodeMachine row."""
    machine.logical_cpus = int(specs.get('logical_cpus', 0) or 0)
    machine.physical_cpus = int(specs.get('physical_cpus', 0) or 0)
    machine.total_ram_mb = float(specs.get('total_ram_mb', 0) or 0)
    machine.available_ram_mb = float(
        specs.get('available_ram_mb', 0) or 0)
    machine.total_disk_mb = float(specs.get('total_disk_mb', 0) or 0)
    machine.free_disk_mb = float(specs.get('free_disk_mb', 0) or 0)
    machine.cgroup_ram_limit_mb = float(
        specs.get('cgroup_ram_limit_mb', 0) or 0)
    machine.load_snapshot_json = json.dumps({
        'cpuPct': specs.get('cpu_pct', 0),
        'ramPct': specs.get('ram_pct', 0),
        'ts': observed_at or _now()})
    if specs.get('arch') and not getattr(machine, 'arch', ''):
        machine.arch = specs['arch']
    # back-compat mirror: mem_gb was the only capacity field before
    if machine.total_ram_mb:
        machine.mem_gb = round(machine.total_ram_mb / 1024.0, 2)
    machine.resource_source = source
    machine.resource_observed_at = observed_at or _now()


def refresh_local_machine(manager, node_name='', db_dir='/app/data'):
    """Observe THIS device onto its PolariNodeMachine row."""
    machine = _find_machine(manager, node_name)
    if machine is None:
        which = f'"{node_name}"' if node_name else 'local (ssh_alias=="")'
        return {'ok': False,
                'error': f'no PolariNodeMachine row for {which}'}
    specs = local_node_specs(manager, db_dir=db_dir)
    if not specs['logical_cpus'] and not specs['total_ram_mb']:
        return {'ok': False, 'node': getattr(machine, 'name', ''),
                'error': 'no isoSys/hostSys on this manager — '
                         'nothing observed, row left unchanged'}
    apply_specs(machine, specs, 'observed-local')
    _save(manager, machine)
    return {'ok': True, 'node': getattr(machine, 'name', ''),
            'source': 'observed-local', 'specs': specs}


def parse_system_info(document):
    """Normalize a /system-info response (backend or worker shape).

    Accepts the backend's `[{"system-info": {...}}]`, a bare
    `{"system-info": {...}}`, or the inner dict itself. Absent
    blocks (old nodes without disk reporting) stay 0 — honest.
    """
    doc = document
    if isinstance(doc, list) and doc:
        doc = doc[0]
    if isinstance(doc, dict) and 'system-info' in doc:
        doc = doc['system-info']
    if not isinstance(doc, dict):
        return None
    cpu = doc.get('cpu') or {}
    mem = doc.get('memory') or {}
    disk = doc.get('disk') or {}
    plat = doc.get('platform') or {}
    return {
        'logical_cpus': int(cpu.get('numLogicalCPUs', 0) or 0),
        'physical_cpus': int(cpu.get('numPhysicalCPUs', 0) or 0),
        'total_ram_mb': _mb(mem.get('total')),
        'available_ram_mb': _mb(mem.get('available')),
        'total_disk_mb': _mb(disk.get('totalBytes')),
        'free_disk_mb': _mb(disk.get('freeBytes')),
        'cgroup_ram_limit_mb': _mb(mem.get('cgroupLimitBytes')),
        'cpu_pct': float(cpu.get('currentUsagePercent', 0) or 0),
        'ram_pct': float(mem.get('percentUsed', 0) or 0),
        'arch': plat.get('arch', ''),
    }


def _default_fetch(url, timeout=5):
    import urllib.request
    with urllib.request.urlopen(url, timeout=timeout) as resp:
        return json.loads(resp.read().decode('utf-8'))


def fetch_remote_specs(manager, node_name, fetch=_default_fetch):
    """Pull a remote node's /system-info onto its row.

    Requires the machine's `system_info_url` knob — the swarm
    routing mesh publishes every port on every node, so a bare
    ip:port cannot honestly identify WHICH host answered; the knob
    makes the address a human's explicit statement. Failure leaves
    the row untouched (prior observations are not clobbered) and
    returns the reason.
    """
    machine = _find_machine(manager, node_name)
    if machine is None:
        return {'ok': False,
                'error': f'no PolariNodeMachine row named "{node_name}"'}
    url = (getattr(machine, 'system_info_url', '') or '').strip()
    if not url:
        return {'ok': False, 'node': node_name,
                'error': 'system_info_url knob is empty',
                'suggestion': {
                    'evidence': 'remote pull needs an explicit '
                                'address; swarm mesh routing makes '
                                'ip:port ambiguous',
                    'knob': 'PolariNodeMachine.system_info_url',
                    'action': f'POST /api/topology/machine '
                              f'{{"name": "{node_name}", '
                              f'"system_info_url": "http://<host>:'
                              f'<port>"}} — or push specs from the '
                              f'node itself (pol topology report '
                              f'idiom)'}}
    if not url.rstrip('/').endswith('/system-info'):
        url = url.rstrip('/') + '/system-info'
    try:
        document = fetch(url)
    except Exception as e:
        return {'ok': False, 'node': node_name,
                'error': f'{url} unreachable: {e}',
                'sourceUnchanged': getattr(
                    machine, 'resource_source', 'unknown')}
    specs = parse_system_info(document)
    if specs is None:
        return {'ok': False, 'node': node_name,
                'error': f'{url} answered with an unrecognized shape'}
    apply_specs(machine, specs, 'observed-remote')
    _save(manager, machine)
    return {'ok': True, 'node': node_name,
            'source': 'observed-remote', 'url': url, 'specs': specs}


def ingest_node_specs(manager, node_name, payload):
    """A node reported its own specs (push path, pol-CLI over ssh)."""
    machine = _find_machine(manager, node_name)
    if machine is None:
        return {'ok': False,
                'error': f'no PolariNodeMachine row named "{node_name}"'}
    if not isinstance(payload, dict):
        return {'ok': False, 'error': 'payload must be a JSON object'}
    specs = parse_system_info(payload)
    if specs is None or (not specs['logical_cpus']
                         and not specs['total_ram_mb']):
        # also accept the normalized flat shape directly
        flat = {k: payload.get(k, 0) for k in SPEC_KEYS}
        if not flat['logical_cpus'] and not flat['total_ram_mb']:
            return {'ok': False, 'node': node_name,
                    'error': 'payload carries no cpu/ram specs '
                             '(neither system-info nor flat shape)'}
        specs = flat
    apply_specs(machine, specs, 'observed-push',
                observed_at=str(payload.get('observed_at', '') or ''))
    _save(manager, machine)
    return {'ok': True, 'node': node_name, 'source': 'observed-push',
            'specs': specs}


def machine_resources_dict(machine):
    """One node's resource view (the API/graph serialization)."""
    total_ram = float(getattr(machine, 'total_ram_mb', 0) or 0)
    avail_ram = float(getattr(machine, 'available_ram_mb', 0) or 0)
    total_disk = float(getattr(machine, 'total_disk_mb', 0) or 0)
    free_disk = float(getattr(machine, 'free_disk_mb', 0) or 0)
    has_specs = bool(
        getattr(machine, 'logical_cpus', 0) or total_ram)
    try:
        load = json.loads(
            getattr(machine, 'load_snapshot_json', '{}') or '{}')
    except (TypeError, ValueError):
        load = {}
    return {
        'name': getattr(machine, 'name', ''),
        'hasSpecs': has_specs,
        'logicalCpus': int(getattr(machine, 'logical_cpus', 0) or 0),
        'physicalCpus': int(getattr(machine, 'physical_cpus', 0) or 0),
        'totalRamMb': total_ram,
        'availableRamMb': avail_ram,
        'totalDiskMb': total_disk,
        'freeDiskMb': free_disk,
        'cgroupRamLimitMb': float(
            getattr(machine, 'cgroup_ram_limit_mb', 0) or 0),
        'headroom': {
            'ramFraction': round(avail_ram / total_ram, 3)
            if total_ram else None,
            'diskFraction': round(free_disk / total_disk, 3)
            if total_disk else None,
        },
        'load': load,
        'resourceSource': getattr(
            machine, 'resource_source', 'unknown'),
        'resourceObservedAt': getattr(
            machine, 'resource_observed_at', ''),
        'systemInfoUrl': getattr(machine, 'system_info_url', ''),
    }


def inventory(manager):
    """All nodes' resource rows + how each was (or wasn't) observed."""
    nodes = [machine_resources_dict(m) for m in _machines(manager)]
    return {'ok': True,
            'nodes': sorted(nodes, key=lambda n: n['name']),
            'observed': sum(1 for n in nodes if n['hasSpecs']),
            'unknown': [n['name'] for n in nodes if not n['hasSpecs']]}
