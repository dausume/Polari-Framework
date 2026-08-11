"""
@module topology.device_resources

dyn-9 (DYNAMIC_MODULES_PLAN): devices connected via agents appear in
TOPOLOGY carrying the resources they grant, and the suite gets one
CONSUMED-vs-AVAILABLE view across every device.

Dustin's ask (2026-08-11): "devices connected via agents appear in
topology along with the resources they grant the use of... so the
isle topology lets us know resources per device, and so we can also
have a resources overall (consumed vs available) in terms of both
threads and processing power as well as memory consumed due to
container presence or code being put onto a device."

Two halves, both pure reads over rows:

  bridge  — IsleDevice rows (what the AGENTS report: which devices
            exist, whether an agent is present, what each grants)
            join PolariNodeMachine rows (what res-1 OBSERVED: cores,
            RAM, disk). A device with an agent but no machine row is
            NAMED as unmirrored rather than silently missing; a
            machine with no observation is 'capacity unknown', never
            a fabricated number.

  ledger  — per device: capacity (threads / RAM / disk) vs the claims
            against it. Claims come from the two things that actually
            consume a device: CONTAINER PRESENCE (a service placed
            there — its image + running footprint) and CODE PUT ONTO
            IT (modules admitted to an instance on that device, each
            costing its ModuleResourceProfile floor).

Honesty rules kept from res-1..4:
  - every number carries its FIDELITY ('observed' | 'declared' |
    'unknown'); declared floors are what a module SAYS it needs, not
    a measurement, and the ledger says so;
  - a device that reported nothing gets capacity None and is
    EXCLUDED from the totals rather than counted as zero — zero
    capacity would read as "full", the opposite of the truth;
  - nothing here allocates, evicts, or moves. It reports, and the
    admission advisor (res-4) is where suggestions already live.
"""


def _rows(manager, class_name):
    table = (getattr(manager, 'objectTables', None) or {}).get(
        class_name, {})
    return list(table.values()) if isinstance(table, dict) \
        else list(table or [])


def _num(value, default=0.0):
    try:
        return float(value or 0.0)
    except (TypeError, ValueError):
        return default


def device_inventory(manager):
    """Every device the agents know about, joined to its observed
    machine resources. The isle says WHICH devices exist; res-1 says
    WHAT they have; this is the seam made visible."""
    machines = {getattr(m, 'name', ''): m
                for m in _rows(manager, 'PolariNodeMachine')}
    seen_machines = set()
    devices = []
    for row in _rows(manager, 'IsleDevice'):
        if getattr(row, 'is_mock', False):
            continue
        name = getattr(row, 'name', '')
        machine_name = getattr(row, 'machine_name', '') or name
        machine = machines.get(machine_name)
        seen_machines.add(machine_name)
        devices.append(_device_entry(row, machine, machine_name))
    # Machines with no IsleDevice row still belong in topology — they
    # are polari nodes the agents have not (or cannot) report.
    for machine_name, machine in machines.items():
        if machine_name in seen_machines:
            continue
        devices.append(_device_entry(None, machine, machine_name))
    devices.sort(key=lambda d: d['device'])
    return devices


def _device_entry(isle_row, machine, machine_name):
    grants = _capacity(machine)
    entry = {
        'device': getattr(isle_row, 'name', '') or machine_name,
        'machine': machine_name if machine is not None else '',
        'agentPresent': bool(getattr(isle_row, 'agent_present',
                                     False)) if isle_row else False,
        'agentMode': getattr(isle_row, 'agent_mode', '')
        if isle_row else '',
        'lastSeen': getattr(isle_row, 'last_seen', '')
        if isle_row else '',
        'hostsRouter': bool(getattr(isle_row, 'hosts_router', False))
        if isle_row else False,
        'grants': grants,
    }
    if isle_row is None:
        entry['note'] = ('polari machine with no agent-reported '
                         'device row — present in topology, not '
                         'reported by the isle')
    elif machine is None:
        entry['note'] = ('agent-reported device with no '
                         'PolariNodeMachine row — capacity unknown '
                         'until it is mirrored (pol topology '
                         'machine) or observed')
    return entry


def _capacity(machine):
    """What a device GRANTS: threads, RAM, disk — with the label of
    how it was learned. None (not zero) when unobserved."""
    if machine is None:
        return {'known': False, 'fidelity': 'unknown',
                'threads': None, 'ramMb': None, 'diskMb': None,
                'why': 'no machine row'}
    threads = int(_num(getattr(machine, 'logical_cpus', 0)))
    ram = _num(getattr(machine, 'total_ram_mb', 0))
    disk = _num(getattr(machine, 'total_disk_mb', 0))
    source = getattr(machine, 'resource_source', '') or ''
    if not threads and not ram:
        return {'known': False, 'fidelity': 'unknown',
                'threads': None, 'ramMb': None, 'diskMb': None,
                'why': 'machine row carries no observation yet — '
                       'pol topology observe / refresh-resources'}
    return {
        'known': True,
        'fidelity': 'observed' if source.startswith('observed')
        else (source or 'declared'),
        'threads': threads or None,
        'physicalCpus': int(_num(getattr(machine, 'physical_cpus',
                                         0))) or None,
        'ramMb': ram or None,
        'availableRamMb': _num(getattr(machine, 'available_ram_mb',
                                       0)) or None,
        'diskMb': disk or None,
        'freeDiskMb': _num(getattr(machine, 'free_disk_mb', 0))
        or None,
        'observedAt': getattr(machine, 'resource_observed_at', ''),
        'source': source,
    }


def _instances_by_machine(manager):
    """InstanceDefinition.name -> hosting machine name."""
    mapping = {}
    for row in _rows(manager, 'InstanceDefinition'):
        machine = (getattr(row, 'machine_name', '')
                   or getattr(row, 'host_machine', '')
                   or getattr(row, 'node_name', ''))
        mapping[getattr(row, 'name', '')] = machine
    return mapping


def _profiles(manager):
    """subject_name -> ModuleResourceProfile row."""
    return {getattr(p, 'subject_name', ''): p
            for p in _rows(manager, 'ModuleResourceProfile')}


def _verdict(entry):
    """An evidence-bearing read of one device's headroom. Never an
    action — res-4's admission advisor owns suggestions."""
    available = entry.get('available') or {}
    used = entry.get('utilization') or {}
    threads_left = available.get('threads')
    ram_left = available.get('ramMb')
    fidelity = entry['consumed']['fidelity']
    if (threads_left is not None and threads_left < 0) or \
            (ram_left is not None and ram_left < 0):
        return {
            'level': 'over-committed',
            'message': 'declared floors exceed what this device '
                       'grants — placements here are already '
                       'promising more than exists',
            'evidence': {'threadsAvailable': threads_left,
                         'ramMbAvailable': ram_left}}
    ram_pct = used.get('ramPct')
    if ram_pct is not None and ram_pct >= 85:
        level, message = 'tight', ('little headroom left — admitting '
                                   'more here risks contention')
    elif not entry['consumed']['moduleFootprint']['modules']:
        level, message = 'idle', ('nothing placed here yet — full '
                                  'capacity available')
    else:
        level, message = 'ok', 'headroom available'
    verdict = {'level': level, 'message': message,
               'evidence': {'ramPct': ram_pct,
                            'threadsPct': used.get('threadsPct')}}
    if fidelity == 'declared':
        verdict['caveat'] = ('these are DECLARED floors, not '
                             'measurements — res-3 '
                             '(profile_measure) flips them to '
                             'measured')
    unprofiled = entry['consumed']['unprofiledModules']
    if unprofiled:
        verdict['blindSpot'] = (
            f'{len(unprofiled)} placed module(s) have no '
            f'ModuleResourceProfile, so their cost is NOT in this '
            f'ledger: {unprofiled[:6]}')
    return verdict


def resource_ledger(manager):
    """Consumed vs available across every device.

    CONSUMED has two named components, because they are two
    different physical facts:
      - containerFootprint: services placed on the device (image +
        declared runtime floor) — the cost of CONTAINER PRESENCE;
      - moduleFootprint: modules admitted to instances on the device
        — the cost of CODE PUT ONTO IT.
    """
    devices = device_inventory(manager)
    by_machine = {d['machine'] or d['device']: d for d in devices}
    instances = _instances_by_machine(manager)
    profiles = _profiles(manager)

    claims = {name: {'modules': [], 'instances': set(),
                     'threads': 0.0, 'ramMb': 0.0, 'diskMb': 0.0,
                     'imageMb': 0.0, 'declaredCount': 0,
                     'unprofiled': []}
              for name in by_machine}

    for row in _rows(manager, 'ModuleAssignment'):
        if getattr(row, 'state', '') != 'enabled':
            continue
        instance = getattr(row, 'instance_name', '')
        module = (getattr(row, 'module_name', '') or '').split('.')[0]
        machine = instances.get(instance, '')
        bucket = claims.get(machine)
        if bucket is None or not module:
            continue
        bucket['instances'].add(instance)
        profile = profiles.get(module)
        if profile is None:
            if module not in bucket['unprofiled']:
                bucket['unprofiled'].append(module)
            continue
        if module in bucket['modules']:
            continue
        bucket['modules'].append(module)
        bucket['threads'] += _num(getattr(profile, 'min_threads', 0))
        bucket['ramMb'] += _num(getattr(profile, 'min_ram_mb', 0))
        bucket['diskMb'] += _num(getattr(profile, 'min_disk_mb', 0))
        bucket['imageMb'] += (_num(getattr(profile, 'image_mb', 0))
                              + _num(getattr(profile, 'deps_mb', 0)))
        if (getattr(profile, 'fidelity', 'declared')
                != 'measured'):
            bucket['declaredCount'] += 1

    entries, totals = [], {
        'devicesCounted': 0, 'devicesUnknown': 0,
        'threadsCapacity': 0.0, 'threadsClaimed': 0.0,
        'ramMbCapacity': 0.0, 'ramMbClaimed': 0.0,
    }
    for device in devices:
        key = device['machine'] or device['device']
        bucket = claims.get(key, {'modules': [], 'instances': set(),
                                  'threads': 0.0, 'ramMb': 0.0,
                                  'diskMb': 0.0, 'imageMb': 0.0,
                                  'declaredCount': 0,
                                  'unprofiled': []})
        grants = device['grants']
        consumed = {
            'moduleFootprint': {
                'modules': sorted(bucket['modules']),
                'threads': round(bucket['threads'], 2),
                'ramMb': round(bucket['ramMb'], 2),
                'diskMb': round(bucket['diskMb'], 2)},
            'containerFootprint': {
                'instances': sorted(bucket['instances']),
                'imageAndDepsMb': round(bucket['imageMb'], 2)},
            'ramMbTotal': round(bucket['ramMb'] + bucket['imageMb'],
                                2),
            'threadsTotal': round(bucket['threads'], 2),
            'fidelity': ('declared' if bucket['declaredCount']
                         else 'measured' if bucket['modules']
                         else 'none'),
            'unprofiledModules': sorted(bucket['unprofiled']),
        }
        entry = {'device': device['device'],
                 'machine': device['machine'],
                 'agentPresent': device['agentPresent'],
                 'grants': grants, 'consumed': consumed}
        if grants['known']:
            threads_cap = _num(grants.get('threads'))
            ram_cap = _num(grants.get('ramMb'))
            entry['available'] = {
                'threads': round(threads_cap
                                 - consumed['threadsTotal'], 2),
                'ramMb': round(ram_cap - consumed['ramMbTotal'], 2)}
            entry['utilization'] = {
                'threadsPct': (round(100.0 * consumed['threadsTotal']
                                     / threads_cap, 1)
                               if threads_cap else None),
                'ramPct': (round(100.0 * consumed['ramMbTotal']
                                 / ram_cap, 1) if ram_cap else None)}
            entry['verdict'] = _verdict(entry)
            totals['devicesCounted'] += 1
            totals['threadsCapacity'] += threads_cap
            totals['threadsClaimed'] += consumed['threadsTotal']
            totals['ramMbCapacity'] += ram_cap
            totals['ramMbClaimed'] += consumed['ramMbTotal']
        else:
            entry['available'] = None
            entry['verdict'] = {
                'level': 'unknown',
                'message': 'capacity unobserved — excluded from the '
                           'totals (counting it as zero would read '
                           'as "full")'}
            totals['devicesUnknown'] += 1
        if device.get('note'):
            entry['note'] = device['note']
        entries.append(entry)

    for axis, cap, used in (('threads', 'threadsCapacity',
                             'threadsClaimed'),
                            ('ramMb', 'ramMbCapacity',
                             'ramMbClaimed')):
        capacity = totals[cap]
        totals[f'{axis}Available'] = round(capacity - totals[used], 2)
        totals[f'{axis}Pct'] = (round(100.0 * totals[used] / capacity,
                                      1) if capacity else None)
        totals[cap] = round(capacity, 2)
        totals[used] = round(totals[used], 2)

    return {
        'ok': True,
        'devices': entries,
        'totals': totals,
        'meaning': {
            'moduleFootprint': 'code put onto the device — the '
                               'declared floor of each module '
                               'admitted to an instance there',
            'containerFootprint': 'container presence — image + '
                                  'deps of the instances placed '
                                  'there',
            'fidelity': "'declared' numbers are what a module SAYS "
                        'it needs (res-2), not a measurement; '
                        'res-3 flips them to measured',
        },
        'note': 'reports only — placement suggestions live in the '
                'admission advisor (POST /api/topology/admission)',
    }
