"""
@cross-cutting
@module topology.topology_example_retire

tpl-6 (AI-Notes/plans/TOPOLOGY_LAYERS_PLAN.md; Codex gate 8): retire the 2026-07-09 example snapshot (topology_seed, the
'staging-a' rows) from a backend that the snapshot does not describe, as ONE generalized operation: a dry-run plan by
default, a verified backup before anything changes, an idempotent apply bound to the reviewed plan, and a restore.
Never a wipe, never a hand delete: only rows the snapshot itself wrote and nobody changed are removed.

    provenance(manager) -> {class: {name: {kind, words}}}
        kind: 'example'         the row is the snapshot's own, field for field (comparing the snapshot's fields only, minus
                                 the ones other code legitimately recomputes, DERIVED below)
              'example-edited'  same name as a snapshot row but a person (or a pass) changed a snapshot field: KEPT
              'self' / 'link'    written by this backend describing itself (tpl-0) / its bindings and frontends (tpl-1)
              'peer'             a copy of a peer's own row (tpl-2): KEPT here, the peer is its authority
              'other'            anything else (imported, typed by a person, the isle): KEPT
    plan(manager) -> {ok, instance, retire: [{class, name}], keep: [{class, name, why}], rehome: [{class, name, from, to}],
                      planDigest, words}
        A snapshot row stays when a kept row still refers to it (an instance's machine, an assignment's instance, an
        edge's or connection's instances), to a fixpoint. Kept rows on the snapshot's topology move to a topology named
        after this instance (what a fresh boot creates, tpl-0); TopologyObservation rows move with them.
    apply(manager, plan_digest) -> receipt {ok, retired, rehomed, backup: {file, sha256, bytes}, problems, retryPlanDigest,
                                            words}
        Refuses unless plan_digest equals the digest of the plan computed NOW (so only the reviewed preview runs; a second
        apply after success finds nothing to do). Writes the backup first (a polari-topology-package document of every
        retired row + the rehome list + which topology was active), re-reads and compares it, and only then changes rows.
        DURABLE FIRST (Codex's review): every save/delete is checked (a raise, False or -1 is a failure); a row changes in
        memory only after its durable write succeeded (a failed field write is reverted; a failed delete leaves the row);
        the first failure stops the run with ok False, the words, and retryPlanDigest = the plan of the REMAINING work, so
        memory == the database at every step and a retry or a restart converges.
        The digest is a review-binding check, not an authorization boundary: operator_gate is.
    restore(manager, backup_file) -> {ok, created, kept, unrehomed, problems, words}
        Re-creates the backed-up rows through the import planner (idempotent by name: a row someone wrote since under the
        same name is KEPT, never overwritten), moves rehomed rows back only if they still sit where apply put them, and
        re-activates the old topology only if the one apply activated is still the active one. Durable first, as above.
    operator_gate(request) -> (allowed, how, words)
        Fail closed. The execute doors (retire, restore) run only for the HOST OPERATOR (a loopback call with no forwarding
        header: `docker exec` into the backend, which the isle can reach through sudo or pkexec, and which `pol` uses when run
        on the backend's own device) or a Polari administrator identity (security.custom.security_claims.is_admin, when the
        security module and Keycloak are present). Plans and backup lists stay readable. Limit, stated: a backend run with
        host networking would also accept local users on that host.

Refuses on an instance the snapshot describes (seed_mode() == 'example', e.g. the compose suite's prf-a): there the
snapshot IS the reality. Knobs (labelled):
    POLARI_TOPOLOGY_SEED         see topology_self.seed_mode
    POLARI_TOPOLOGY_BACKUP_DIR   where backups are written. Absent -> /data/topology-backups when /data exists (the backend's
                                 data volume, beside /data/managerObject_DB.db), else ./topology-backups.
OrchestrationTarget rows (compose / swarm / isle) are a vocabulary the snapshot shares with every topology, not a claim
about this backend: never retired here.
"""
import hashlib
import json
import os
from datetime import datetime, timezone

from topology.topology_io import PACKAGE_FIELDS, _VOLATILE, _row_dict, merge_topology_doc

#: snapshot section -> class, in package dependency order
SECTIONS = (
    ('SEED_NODE_MACHINES', 'PolariNodeMachine', 'machines'),
    ('SEED_TOPOLOGY_DEFINITIONS', 'TopologyDefinition', 'topology'),
    ('SEED_INSTANCE_DEFINITIONS', 'InstanceDefinition', 'instances'),
    ('SEED_MODULE_ASSIGNMENTS', 'ModuleAssignment', 'assignments'),
    ('SEED_MODULE_DEPENDENCY_EDGES', 'ModuleDependencyEdge', 'edges'),
    ('SEED_SERVICE_CONNECTIONS', 'ServiceConnection', 'connections'),
)
#: snapshot fields other code rewrites on its own (resource observation mirrors mem_gb / arch; `resolve` recomputes an
#: edge's provider and status): a difference there is not a person's edit.
DERIVED = {'PolariNodeMachine': {'mem_gb', 'arch'}, 'ModuleDependencyEdge': {'status', 'provider_instance_name'}}
#: reference fields: class -> [(field, referenced class)]
REFS = {
    'InstanceDefinition': [('machine_name', 'PolariNodeMachine')],
    'ModuleAssignment': [('instance_name', 'InstanceDefinition')],
    'ModuleDependencyEdge': [('consumer_instance_name', 'InstanceDefinition'), ('provider_instance_name', 'InstanceDefinition')],
    'ServiceConnection': [('from_instance_name', 'InstanceDefinition'), ('to_instance_name', 'InstanceDefinition')],
}
TOPOLOGY_SCOPED = ('InstanceDefinition', 'ModuleAssignment', 'ModuleDependencyEdge', 'ServiceConnection', 'TopologyObservation')
BACKUP_KNOB = 'POLARI_TOPOLOGY_BACKUP_DIR'
_PREFIX = 'retire-example-'


def _rows(manager, cls):
    return list((getattr(manager, 'objectTables', None) or {}).get(cls, {}).values())


def _classes():
    from topology.topology_basis import InstanceDefinition, PolariNodeMachine
    from topology.topology_links import ServiceConnection
    from topology.topology_modules import ModuleAssignment, ModuleDependencyEdge
    from topology.topology_state import TopologyDefinition
    return {'PolariNodeMachine': PolariNodeMachine, 'TopologyDefinition': TopologyDefinition,
            'InstanceDefinition': InstanceDefinition, 'ModuleAssignment': ModuleAssignment,
            'ModuleDependencyEdge': ModuleDependencyEdge, 'ServiceConnection': ServiceConnection}


def _snapshot():
    from topology import topology_seed as S
    return {cls: {e['name']: e for e in getattr(S, var, []) if e.get('name')} for var, cls, _ in SECTIONS}


def _same(cls, row, entry):
    """[] when the row still holds the snapshot's value for every snapshot field it travels with, else the changed fields."""
    fields = set(PACKAGE_FIELDS[cls]) - _VOLATILE - DERIVED.get(cls, set()) - {'name'}
    return sorted(f for f in fields if f in entry and getattr(row, f, '') != entry[f])


def provenance(manager):
    from topology.topology_self import _TAG as LINK_TAG
    snap = _snapshot()
    out = {}
    for _, cls, _ in SECTIONS:
        for row in _rows(manager, cls):
            name, notes = getattr(row, 'name', ''), getattr(row, 'notes', '') or ''
            entry = snap[cls].get(name)
            if '(tpl-2 peer:' in notes or str(getattr(row, 'source', '') or '').startswith('peer:'):
                kind, words = 'peer', 'a copy of a peer\'s own row (tpl-2), refreshed from that peer'
            elif '(tpl-0)' in notes or getattr(row, 'source', '') == 'self-described':
                kind, words = 'self', 'written by this backend describing itself (tpl-0)'
            elif LINK_TAG in notes:
                kind, words = 'link', 'written from a binding or frontend origin (tpl-1)'
            elif entry is not None:
                changed = _same(cls, row, entry)
                kind, words = (('example-edited', 'a 2026-07-09 example row, since changed: ' + ', '.join(changed)) if changed
                               else ('example', 'the 2026-07-09 example snapshot (topology_seed), unchanged'))
            else:
                kind, words = 'other', 'not from the example snapshot'
            out.setdefault(cls, {})[name] = {'kind': kind, 'words': words}
    return out


def _digest(retire, rehome):
    body = json.dumps({'retire': retire, 'rehome': rehome}, sort_keys=True)
    return hashlib.sha256(body.encode('utf-8')).hexdigest()


def plan(manager):
    from topology.topology_self import instance_name, seed_mode
    me = instance_name()
    if seed_mode() == 'example':
        return {'ok': False, 'instance': me, 'retire': [], 'keep': [], 'rehome': [], 'planDigest': '',
                'words': 'refused: %s is an instance the 2026-07-09 example describes (POLARI_TOPOLOGY_SEED resolves to '
                         'example), so the snapshot is its reality; set POLARI_TOPOLOGY_SEED=none there to retire it' % me}
    prov = provenance(manager)
    retire = {(cls, n) for cls, rows in prov.items() for n, p in rows.items() if p['kind'] == 'example'}
    why = {}
    for cls, rows in prov.items():
        for n, p in rows.items():
            if p['kind'] != 'example':
                why[(cls, n)] = p['words']
    by_name = {(cls, getattr(r, 'name', '')): r for _, cls, _ in SECTIONS for r in _rows(manager, cls)}
    changed = True
    while changed:                      # a kept row keeps every snapshot row it refers to
        changed = False
        for (cls, n), row in by_name.items():
            if (cls, n) in retire:
                continue
            for field, target in REFS.get(cls, ()):
                ref = getattr(row, field, '') or ''
                if (target, ref) in retire:
                    retire.discard((target, ref))
                    why[(target, ref)] = 'a 2026-07-09 example row still referred to by kept %s:%s (%s)' % (cls, n, field)
                    changed = True
    retired_topologies = {n for cls, n in retire if cls == 'TopologyDefinition'}
    rehome = []
    for cls in TOPOLOGY_SCOPED:
        for row in _rows(manager, cls):
            n, t = getattr(row, 'name', ''), getattr(row, 'topology_name', '')
            if t in retired_topologies and (cls, n) not in retire:
                rehome.append({'class': cls, 'name': n, 'from': t, 'to': me})
    retire_l = sorted(({'class': c, 'name': n} for c, n in retire), key=lambda d: (d['class'], d['name']))
    keep_l = sorted(({'class': c, 'name': n, 'why': w} for (c, n), w in why.items() if (c, n) not in retire),
                    key=lambda d: (d['class'], d['name']))
    rehome.sort(key=lambda d: (d['class'], d['name']))
    words = ('%s: retire %d unchanged example row%s, keep %d, move %d kept row%s onto topology %s'
             % (me, len(retire_l), '' if len(retire_l) == 1 else 's', len(keep_l), len(rehome), '' if len(rehome) == 1 else 's', me)
             if retire_l else '%s: nothing to retire (no unchanged example rows)' % me)
    digest = _digest(retire_l, rehome)
    out = {'ok': True, 'instance': me, 'retire': retire_l, 'keep': keep_l, 'rehome': rehome, 'planDigest': digest,
           'words': words, 'plannedAction': None}
    if retire_l or rehome:
        from topology.topology_self import machine_name
        out['plannedAction'] = planned_action(me, machine_name(), digest, len(retire_l), len(keep_l), len(rehome))
    return out


def planned_action(me, device, digest, n_retire, n_keep, n_move):
    """The user's 2026-11-07 ruling: what cannot be applied from here is a PLANNED action, run in bulk by the Isle App after
    one permission + password prompt, with a one-line summary per action in its notification. This is the shape it
    collects; executing it is the host operator's (operator_gate), never this backend's on its own.
    Codex's admission review: identity = kind + backend + device + digest (drift after review fails or replans); execute /
    operatorCommand are DATA for the client, which maps the allowlisted kind to its own door; the Isle App's bulk run is
    NOT built yet, so nothing here claims it exists (appRun)."""
    kind = 'polari.topology.retire-example'
    return {'kind': kind, 'id': '%s:%s@%s:%s' % (kind, me, device or 'unknown-device', digest), 'backend': me,
            'device': device or '', 'digest': digest, 'status': 'planned',
            'appRun': 'not built yet: the Isle App bulk run of planned actions is planned (Isle side); today run '
                      'operatorCommand on the device',
            'summary': 'retire %d unchanged July example row%s on %s (keep %d, move %d onto topology %s); backup first, '
                       'restorable' % (n_retire, '' if n_retire == 1 else 's', me, n_keep, n_move, me),
            'execute': {'method': 'POST', 'path': '/api/topology/example-rows/retire', 'body': {'planDigest': digest}},
            'operatorCommand': 'pol topology example-rows retire --digest %s' % digest,
            'undo': 'pol topology example-rows restore <backup named in the receipt>'}


def backup_dir():
    knob = (os.environ.get(BACKUP_KNOB) or '').strip()
    if knob:
        return knob
    return '/data/topology-backups' if os.path.isdir('/data') else os.path.abspath('topology-backups')


def _what(cls, row):
    return '%s:%s' % (cls or type(row).__name__, getattr(row, 'name', '?'))


def _save(manager, row, cls=''):
    """'' when the row is durable (or this manager keeps no database), else the words of the failure."""
    db = getattr(manager, 'db', None)
    if db is None:
        return ''
    try:
        result = db.saveInstanceInDB(row)
    except Exception as exc:  # noqa: BLE001 - the words are the point
        return 'save of %s raised %s: %s' % (_what(cls, row), type(exc).__name__, exc)
    if result is False or result == -1:
        return 'the database refused the save of %s (%r)' % (_what(cls, row), result)
    return ''


def _set(manager, row, field, value, cls=''):
    """Change one field durably: memory follows the database (reverted when the save fails)."""
    old = getattr(row, field, None)
    setattr(row, field, value)
    err = _save(manager, row, cls)
    if err:
        setattr(row, field, old)
    return err


def _forget(manager, cls, row):
    """Drop a row from memory only (its durable delete already succeeded)."""
    rid = getattr(row, 'id', None)
    table = manager.objectTables.get(cls) or {}
    if rid is not None and hasattr(manager, 'deleteTreeNode') and rid in table:
        manager.deleteTreeNode(className=cls, nodePolariId=rid, instancesDeleted=[], migratedInstances=[])
    for k, v in list(table.items()):
        if v is row:
            table.pop(k)


def _delete(manager, cls, row):
    """Durable delete FIRST, then memory. '' on success, else words; on failure the row stays (memory == database)."""
    db = getattr(manager, 'db', None)
    if db is not None:
        rid = getattr(row, 'id', None)
        if rid is None or not hasattr(db, 'deleteRowsWhere'):
            return 'cannot delete %s durably (no id, or a database without deleteRowsWhere)' % _what(cls, row)
        try:
            result = db.deleteRowsWhere(cls, 'id', rid)
        except Exception as exc:  # noqa: BLE001
            return 'delete of %s raised %s: %s' % (_what(cls, row), type(exc).__name__, exc)
        if result is False or result is None or (isinstance(result, int) and result < 0):
            return 'the database refused the delete of %s (%r)' % (_what(cls, row), result)
    try:
        _forget(manager, cls, row)
    except Exception as exc:  # noqa: BLE001 - durable already gone; a retry deletes 0 rows and forgets again
        return 'deleted %s durably, but dropping it from memory raised %s: %s' % (_what(cls, row), type(exc).__name__, exc)
    return ''


def _find(manager, cls, name):
    return next((r for r in _rows(manager, cls) if getattr(r, 'name', '') == name), None)


def _activate_own(manager, me):
    """The instance's own topology, saved, then made the only active one. [] or the failures (memory follows the DB)."""
    topo = _find(manager, 'TopologyDefinition', me)
    if topo is None:
        from topology.topology_state import TopologyDefinition
        topo = TopologyDefinition(name=me, description='This backend as it describes itself (tpl-0): its own instance and the '
                                  'modules live on it. Peers and the isle add their rows beside it.',
                                  status='applied', is_active=False, notes='created when the example rows were retired (tpl-6)',
                                  manager=manager)
        err = _save(manager, topo, 'TopologyDefinition')
        if err:
            _forget(manager, 'TopologyDefinition', topo)
            return [err]
    for t in _rows(manager, 'TopologyDefinition'):
        if t is not topo and getattr(t, 'is_active', False):
            err = _set(manager, t, 'is_active', False, 'TopologyDefinition')
            if err:
                return [err]
    if not getattr(topo, 'is_active', False):
        err = _set(manager, topo, 'is_active', True, 'TopologyDefinition')
        if err:
            return [err]
    return []


def _stopped(manager, receipt, problem):
    receipt['problems'].append(problem)
    receipt['ok'] = False
    after = plan(manager)
    receipt['retryPlanDigest'] = after.get('planDigest', '')
    receipt['words'] = ('STOPPED at the first failure: %s. Done so far: %d retired, %d moved (durable). Nothing else changed. '
                        'The backup %s stays. Retry the REMAINING work with planDigest %s (%s), or restore the backup.'
                        % (problem, len(receipt['retired']), len(receipt['rehomed']),
                           (receipt.get('backup') or {}).get('file', '-'), receipt['retryPlanDigest'], after.get('words', '')))
    return receipt


def apply(manager, plan_digest):
    from topology.topology_self import instance_name
    p = plan(manager)
    if not p['ok']:
        return dict(p, ok=False, retired=[], rehomed=[], backup=None, problems=[])
    if not p['retire'] and not p['rehome']:
        return {'ok': True, 'retired': [], 'rehomed': [], 'backup': None, 'problems': [], 'words': p['words'] + '; nothing changed'}
    if plan_digest != p['planDigest']:
        return {'ok': False, 'retired': [], 'rehomed': [], 'backup': None, 'problems': [], 'planDigest': p['planDigest'],
                'words': 'refused: the plan changed since it was reviewed (or no planDigest was given); review the current '
                         'plan and apply with its planDigest %s' % p['planDigest']}
    me = instance_name()
    active = next((getattr(t, 'name', '') for t in _rows(manager, 'TopologyDefinition') if getattr(t, 'is_active', False)), '')
    from topology.topology_constants import SCHEMA_VERSION
    doc = {'schema_version': SCHEMA_VERSION, 'kind': 'polari-topology-package'}
    retire_set = {(d['class'], d['name']) for d in p['retire']}
    for _, cls, section in SECTIONS:
        rows = [_row_dict(r, PACKAGE_FIELDS[cls]) for r in _rows(manager, cls) if (cls, getattr(r, 'name', '')) in retire_set]
        rows.sort(key=lambda d: d['name'])
        doc[section] = rows
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')      # + the digest below: two runs never collide
    record = {'kind': 'polari-topology-retire-backup', 'instance': me, 'takenAt': stamp, 'planDigest': p['planDigest'],
              'activeTopology': active, 'activatedTopology': me if p['rehome'] else '', 'rehome': p['rehome'], 'document': doc}
    folder = backup_dir()
    path = os.path.join(folder, '%s%s-%s.json' % (_PREFIX, stamp, p['planDigest'][:12]))
    try:
        os.makedirs(folder, exist_ok=True)
        data = json.dumps(record, indent=1, sort_keys=True).encode('utf-8')
        with open(path, 'xb') as fh:
            fh.write(data)
            fh.flush()
            os.fsync(fh.fileno())
        with open(path, 'rb') as fh:
            back = fh.read()
        if back != data or json.loads(back.decode('utf-8')) != record:
            raise IOError('the backup read back differs from what was written')
    except Exception as exc:  # noqa: BLE001 - no verified backup, no change
        return {'ok': False, 'retired': [], 'rehomed': [], 'backup': None, 'problems': [],
                'words': 'refused: backup to %s failed (%s: %s); nothing changed (knob %s)' % (path, type(exc).__name__, exc,
                                                                                          BACKUP_KNOB)}
    receipt = {'ok': True, 'retired': [], 'rehomed': [], 'problems': [], 'retryPlanDigest': '',
               'backup': {'file': os.path.basename(path), 'dir': folder, 'sha256': hashlib.sha256(data).hexdigest(),
                          'bytes': len(data)}}
    if p['rehome']:
        errs = _activate_own(manager, me)
        if errs:
            return _stopped(manager, receipt, errs[0])
        for d in p['rehome']:
            row = _find(manager, d['class'], d['name'])
            if row is None:
                continue
            err = _set(manager, row, 'topology_name', d['to'], d['class'])
            if err:
                return _stopped(manager, receipt, err)
            receipt['rehomed'].append(d)
    for _, cls, _ in reversed(SECTIONS):                 # referencing rows before referenced ones
        for d in [x for x in p['retire'] if x['class'] == cls]:
            row = _find(manager, cls, d['name'])
            if row is None:
                continue
            err = _delete(manager, cls, row)
            if err:
                return _stopped(manager, receipt, err)
            receipt['retired'].append(d)
    try:
        from polariApiServer.persist_debounce import schedule_persist
        schedule_persist(manager, reason='tpl-6 retire example rows')
    except Exception:  # noqa: BLE001 - a host-tool manager has no persistence loop
        pass
    receipt['words'] = ('%s: retired %d example row%s, moved %d onto %s; backup %s (sha256 %s); undo with restore %s'
                        % (me, len(receipt['retired']), '' if len(receipt['retired']) == 1 else 's', len(receipt['rehomed']),
                           me, path, receipt['backup']['sha256'][:12], receipt['backup']['file']))
    return receipt


def list_backups():
    folder = backup_dir()
    try:
        names = sorted(n for n in os.listdir(folder) if n.startswith(_PREFIX) and n.endswith('.json'))
    except OSError:
        names = []
    return {'ok': True, 'dir': folder, 'backups': names}


def restore(manager, backup_file):
    out = {'ok': False, 'created': [], 'kept': [], 'unrehomed': [], 'removed': [], 'problems': [], 'words': ''}
    name = os.path.basename(str(backup_file or ''))
    if not name.startswith(_PREFIX) or not name.endswith('.json') or name != backup_file:
        out['words'] = 'refused: name a backup file from the backup list (%s*.json), not a path' % _PREFIX
        return out
    path = os.path.join(backup_dir(), name)
    try:
        with open(path, 'rb') as fh:
            record = json.loads(fh.read().decode('utf-8'))
    except Exception as exc:  # noqa: BLE001
        out['words'] = 'refused: %s unreadable (%s: %s)' % (path, type(exc).__name__, exc)
        return out
    if record.get('kind') != 'polari-topology-retire-backup':
        out['words'] = 'refused: %s is not a retire backup' % path
        return out
    doc = record.get('document') or {}
    merged = merge_topology_doc(manager, dict(doc, topology=(doc.get('topology') or [])))
    if not merged.get('ok'):
        out['words'] = 'refused: ' + str(merged.get('error'))
        return out
    out['kept'] = [{'class': k['class'], 'name': k['name'], 'why': 'a row with this name exists here (restored by an earlier run, or written since); kept as it is'}
                   for k in merged['skips'] if k.get('name')]

    def stop(problem):
        out['problems'].append(problem)
        out['words'] = ('STOPPED at the first failure: %s. Restored so far: %d row%s, %d moved back (durable). Run restore %s '
                        'again to continue (rows already back are kept by name).'
                        % (problem, len(out['created']), '' if len(out['created']) == 1 else 's', len(out['unrehomed']), name))
        return out
    classes = _classes()
    for cls, row in merged['creates']:
        obj = classes[cls](**row, manager=manager)
        err = _save(manager, obj, cls)
        if err:
            _forget(manager, cls, obj)
            return stop(err)
        out['created'].append({'class': cls, 'name': row.get('name', '')})
    for d in record.get('rehome') or []:
        row = _find(manager, d['class'], d['name'])
        if row is None or getattr(row, 'topology_name', '') != d['to']:
            out['kept'].append({'class': d['class'], 'name': d['name'], 'why': 'no longer on topology %s; left where it is' % d['to']})
            continue
        err = _set(manager, row, 'topology_name', d['from'], d['class'])
        if err:
            return stop(err)
        out['unrehomed'].append(d)
    was, made = record.get('activeTopology') or '', record.get('activatedTopology') or ''
    now_active = next((getattr(t, 'name', '') for t in _rows(manager, 'TopologyDefinition') if getattr(t, 'is_active', False)), '')
    if was and _find(manager, 'TopologyDefinition', was) is not None and now_active != was:
        if made and now_active != made:
            out['kept'].append({'class': 'TopologyDefinition', 'name': now_active,
                                'why': 'someone activated %s since; the active topology is left as it is' % now_active})
        else:
            for t in _rows(manager, 'TopologyDefinition'):
                if getattr(t, 'is_active', False) and getattr(t, 'name', '') != was:
                    err = _set(manager, t, 'is_active', False, 'TopologyDefinition')
                    if err:
                        return stop(err)
            err = _set(manager, _find(manager, 'TopologyDefinition', was), 'is_active', True, 'TopologyDefinition')
            if err:
                return stop(err)
    # apply created the instance's own topology; once nothing refers to it and it is not active, restore removes it too
    own = _find(manager, 'TopologyDefinition', made) if made else None
    if own is not None and not getattr(own, 'is_active', False) and 'tpl-6' in (getattr(own, 'notes', '') or ''):
        users = [(c, getattr(r, 'name', '')) for c in TOPOLOGY_SCOPED for r in _rows(manager, c)
                 if getattr(r, 'topology_name', '') == made]
        if users:
            out['kept'].append({'class': 'TopologyDefinition', 'name': made,
                                'why': 'still used by %d row%s (e.g. %s:%s); kept' % (len(users), '' if len(users) == 1 else 's',
                                                                                     users[0][0], users[0][1])})
        else:
            err = _delete(manager, 'TopologyDefinition', own)
            if err:
                return stop(err)
            out['removed'] = [{'class': 'TopologyDefinition', 'name': made}]
    out['ok'] = True
    out['words'] = ('restored %d row%s from %s, moved %d back, kept %d as they are, active topology %s'
                    % (len(out['created']), '' if len(out['created']) == 1 else 's', name, len(out['unrehomed']),
                       len(out['kept']), was or '(unchanged)'))
    return out


LOOPBACK = ('127.0.0.1', '::1', '::ffff:127.0.0.1')
FORWARD_HEADERS = ('X-Forwarded-For', 'Forwarded', 'X-Real-IP')


def operator_gate(request):
    """-> (allowed, how, words). Fail closed: anything not positively the host operator or a Polari administrator is refused."""
    addr = str(getattr(request, 'remote_addr', '') or '')
    get = getattr(request, 'get_header', None)
    forwarded = [h for h in FORWARD_HEADERS if callable(get) and get(h)]
    if (addr in LOOPBACK or addr.startswith('127.')) and not forwarded:
        return True, 'host-operator', ('called from inside this backend (%s: docker exec by the host operator, which the isle '
                                       'reaches through sudo or pkexec)' % addr)
    user = getattr(getattr(request, 'context', None), 'user_info', None)
    if user:
        try:
            from security.custom.security_claims import is_admin
        except Exception:  # noqa: BLE001 - no security module here: no administrator identity to accept
            is_admin = None
        try:
            if is_admin is not None and is_admin(user):
                return True, 'admin', 'a Polari administrator identity'
        except Exception:  # noqa: BLE001 - a broken check refuses
            pass
    return False, '', ('refused: this door changes rows, and runs only for the host operator or a Polari administrator '
                       '(caller %s%s). Read the plan with GET /api/topology/example-rows (open), then run it ON the '
                       'backend\'s device: `pol topology example-rows retire --digest <d>` without --api (docker exec), '
                       'or `ssh <device> pol topology example-rows ...` (an Isle App bulk run of '
                       'planned actions is planned, not built yet). Nothing was written, backed up or deleted.'
                       % (addr or 'unknown', ', forwarded by a proxy' if forwarded else ''))
