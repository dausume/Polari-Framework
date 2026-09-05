"""
@module topology.placement_truth

dyn-2b (DYNAMIC_MODULES_PLAN): ONE placement truth, tied together.

Placement lives in three places that historically nothing reconciled:
the POLARI_MODULES env a backend booted with, ModuleAssignment rows,
and the isle agent registry's 'modules:...' modes strings. The rule
here: **ModuleAssignment rows are the single authority; the other two
are derived caches that KNOW they are derived.**

- the RUNNING set follows rows live (dyn-2 admit / dyn-3 put-away
  call sync_assignment_row so whichever side initiated, the change
  LANDS in rows);
- the backend reports what it actually runs as a TopologyObservation
  (observed state is reported, never guessed — same contract as
  `pol topology report`), refreshed at boot and on every live
  admission change;
- placement_report() is the authoritative READ: the isle agent (and
  anything else) refreshes its cache from here instead of maintaining
  its own truth; the STOMP /topic/PolariModule push that admission
  already emits is the refresh signal;
- coherence findings NAME drift with a suggested action and never
  auto-heal (knobs-and-suggestions).

Pure best-effort everywhere: a standalone instance with no topology
rows is 'unmanaged' (info, not drift), and every write is non-fatal.
"""

import json
import os
import time
from datetime import datetime, timezone

from polariApiServer.module_gating import (
    CORE_PACKAGES, enabled_module_names,
)
from polariApiServer.lazy_boot import top_module


def _instance_name():
    return (os.environ.get('POLARI_INSTANCE_NAME')
            or os.environ.get('POLARI_INSTANCE_ID') or 'local')


def live_module_set(polServer):
    """The modules ACTUALLY live in this process right now: owners of
    registered definition classes plus constructed endpoint modules,
    minus core (always everywhere) and minus put-away modules."""
    live = {top_module(c) for c in polServer.defClassList}
    live |= set(getattr(polServer, 'endpointConstructed', ()))
    live -= set(CORE_PACKAGES)
    registry = getattr(polServer, 'bootRegistry', None)
    if registry is not None:
        live -= set(registry.put_away_modules)
    return live


def _assignment_rows(manager, instance=None):
    rows = list(manager.objectTables.get('ModuleAssignment',
                                         {}).values())
    if instance is not None:
        rows = [r for r in rows
                if getattr(r, 'instance_name', '') == instance]
    return rows


def _topology_name(manager):
    for row in manager.objectTables.get('TopologyDefinition',
                                        {}).values():
        return getattr(row, 'name', '')
    return ''


def sync_assignment_row(manager, module, state, source):
    """Land a live admission change in the AUTHORITY. Upserts the
    local instance's ModuleAssignment row to `state`. Skipped (with
    the reason) when no topology exists here — an unmanaged
    standalone instance has no rows to keep truthful."""
    instance = _instance_name()
    topology = _topology_name(manager)
    if not topology and not _assignment_rows(manager, instance):
        return {'synced': False,
                'reason': 'no topology rows on this instance '
                          '(unmanaged/standalone) — nothing to sync'}
    try:
        found = None
        for row in _assignment_rows(manager, instance):
            if getattr(row, 'module_name', '') == module:
                found = row
                break
        if found is None:
            from topology.topology_modules import ModuleAssignment
            found = ModuleAssignment(
                name=f'{module}@{instance}', module_name=module,
                instance_name=instance, state=state,
                topology_name=topology,
                notes=f'{source} (dyn-2b row sync)',
                manager=manager)
        else:
            found.state = state
            found.notes = f'{source} (dyn-2b row sync)'
        if manager.db is not None:
            manager.db.saveInstanceInDB(found)
        return {'synced': True, 'row': found.name, 'state': state}
    except Exception as exc:
        return {'synced': False, 'reason': f'{type(exc).__name__}: '
                                           f'{exc}'}


def record_placement_observation(manager, source):
    """Refresh this instance's live-module observation row —
    observed state reported, never guessed. One row per instance
    (name 'live-modules@<instance>'), updated in place."""
    try:
        polServer = manager.polServer
        instance = _instance_name()
        payload = json.dumps([{
            'instance': instance,
            'modules': sorted(live_module_set(polServer)),
            'putAway': sorted(getattr(polServer.bootRegistry,
                                      'put_away_modules', ())),
            'envKnob': (os.environ.get('POLARI_MODULES') or ''),
        }])
        name = f'live-modules@{instance}'
        found = None
        for row in manager.objectTables.get('TopologyObservation',
                                            {}).values():
            if getattr(row, 'name', '') == name:
                found = row
                break
        stamp = datetime.now(timezone.utc).isoformat()
        if found is None:
            from topology.topology_state import TopologyObservation
            found = TopologyObservation(
                name=name, topology_name=_topology_name(manager),
                node_name=instance, observed_at=stamp,
                modules_json=payload,
                source=f'backend live report ({source})',
                manager=manager)
        else:
            found.observed_at = stamp
            found.modules_json = payload
            found.source = f'backend live report ({source})'
        if manager.db is not None:
            manager.db.saveInstanceInDB(found)
        return {'recorded': True, 'row': name}
    except Exception as exc:
        return {'recorded': False,
                'reason': f'{type(exc).__name__}: {exc}'}


def placement_report(manager):
    """The authoritative read + the three-way coherence diff.
    {instance, liveModules, putAway, envKnob, declared, isleView,
     coherence: [{level, code, message, suggestion?}]}"""
    polServer = manager.polServer
    instance = _instance_name()
    live = live_module_set(polServer)
    put_away = sorted(getattr(polServer.bootRegistry,
                              'put_away_modules', ()))
    raw_env = (os.environ.get('POLARI_MODULES') or '').strip()
    declared = {}
    for row in _assignment_rows(manager, instance):
        declared[getattr(row, 'module_name', '')] = \
            getattr(row, 'state', '')
    findings = []

    managed = bool(declared) or bool(_topology_name(manager))
    if not managed:
        findings.append({
            'level': 'info', 'code': 'unmanaged-instance',
            'message': f"'{instance}' has no topology rows — env is "
                       'the only knob here; nothing to reconcile.'})
    else:
        enabled_declared = {m for m, s in declared.items()
                            if s == 'enabled'
                            and m.split('.')[0] not in CORE_PACKAGES}
        top_declared = {m.split('.')[0] for m in enabled_declared}
        for m in sorted(top_declared - live):
            findings.append({
                'level': 'drift', 'code': 'declared-not-live',
                'message': f"rows say '{m}' is enabled on "
                           f"'{instance}' but it is not live.",
                'suggestion': f'POST /modules/{m}/admit (live), or '
                              'pol topology apply at next deploy'})
        for m in sorted(live - top_declared):
            findings.append({
                'level': 'drift', 'code': 'live-not-declared',
                'message': f"'{m}' is live on '{instance}' but no "
                           'enabled ModuleAssignment row says so.',
                'suggestion': f'pol topology assign {m} {instance} '
                              '— record the truth in rows'})

    if raw_env:
        env_set = {e.strip().split('.')[0]
                   for e in raw_env.split(',') if e.strip()} \
            - set(CORE_PACKAGES)
        if env_set != live:
            findings.append({
                'level': 'drift', 'code': 'env-cache-drift',
                'message': f'POLARI_MODULES ({sorted(env_set)}) '
                           f'disagrees with the live set '
                           f'({sorted(live)}).',
                'suggestion': 'env is a derived cache — rows are '
                              'the truth; re-derive at next deploy '
                              '(pol resolves it from rows)'})

    isle_view = []
    try:
        for row in manager.objectTables.get('IsleApp', {}).values():
            modes = json.loads(getattr(row, 'modes_json', '[]')
                               or '[]')
            mods = next((sorted(x for x in
                                str(m)[len('modules:'):].split(',')
                                if x)
                         for m in modes
                         if str(m).startswith('modules:')), None)
            if mods is None:
                continue
            entry = {'app': getattr(row, 'name', ''),
                     'modules': mods}
            isle_view.append(entry)
            if entry['app'] == instance and set(mods) != live:
                findings.append({
                    'level': 'drift', 'code': 'isle-registry-stale',
                    'message': f"the isle registry says "
                               f"'{instance}' runs {mods}; live is "
                               f'{sorted(live)}.',
                    'suggestion': 'the isle agent should refresh '
                                  'from GET /api/modules/status '
                                  '(STOMP /topic/PolariModule is '
                                  'the signal)'})
    except Exception:
        isle_view = [{'note': 'isle registry not readable here'}]

    if not any(f['level'] == 'drift' for f in findings):
        findings.append({'level': 'ok', 'code': 'coherent',
                         'message': 'rows, env, live set and isle '
                                    'view agree.'})
    return {
        'instance': instance,
        'liveModules': sorted(live),
        'putAway': put_away,
        'envKnob': raw_env or '(unset = ALL)',
        'declared': declared,
        'isleView': isle_view,
        'authority': 'ModuleAssignment rows; env + isle registry '
                     'are derived caches (dyn-2b)',
        'coherence': findings,
        'reportedAt': time.time(),
    }
