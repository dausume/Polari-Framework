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
              'other'            anything else (imported, typed by a person, the isle): KEPT
    plan(manager) -> {ok, instance, retire: [{class, name}], keep: [{class, name, why}], rehome: [{class, name, from, to}],
                      planDigest, words}
        A snapshot row stays when a kept row still refers to it (an instance's machine, an assignment's instance, an
        edge's or connection's instances), to a fixpoint. Kept rows on the snapshot's topology move to a topology named
        after this instance (what a fresh boot creates, tpl-0); TopologyObservation rows move with them.
    apply(manager, plan_digest) -> receipt {ok, retired, rehomed, backup: {file, sha256, bytes}, words}
        Refuses unless plan_digest equals the digest of the plan computed NOW (so only the reviewed preview runs; a second
        apply after success finds nothing to do). Writes the backup first (a polari-topology-package document of every
        retired row + the rehome list + which topology was active), re-reads and compares it, and only then changes rows.
        The digest is a review-binding check, not an authorization boundary.
    restore(manager, backup_file) -> {ok, created, unrehomed, words}
        Re-creates the backed-up rows through the import planner (idempotent-by-name) and moves rehomed rows back.

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
            if '(tpl-0)' in notes or getattr(row, 'source', '') == 'self-described':
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
    return {'ok': True, 'instance': me, 'retire': retire_l, 'keep': keep_l, 'rehome': rehome,
            'planDigest': _digest(retire_l, rehome), 'words': words}


def backup_dir():
    knob = (os.environ.get(BACKUP_KNOB) or '').strip()
    if knob:
        return knob
    return '/data/topology-backups' if os.path.isdir('/data') else os.path.abspath('topology-backups')


def _save(manager, row):
    db = getattr(manager, 'db', None)
    if db is not None:
        db.saveInstanceInDB(row)


def _find(manager, cls, name):
    return next((r for r in _rows(manager, cls) if getattr(r, 'name', '') == name), None)


def _ensure_topology(manager, me):
    topo = _find(manager, 'TopologyDefinition', me)
    if topo is None:
        from topology.topology_state import TopologyDefinition
        topo = TopologyDefinition(name=me, description='This backend as it describes itself (tpl-0): its own instance and the '
                                  'modules live on it. Peers and the isle add their rows beside it.',
                                  status='applied', is_active=True, notes='created when the example rows were retired (tpl-6)',
                                  manager=manager)
    for t in _rows(manager, 'TopologyDefinition'):
        if t is not topo and getattr(t, 'is_active', False):
            t.is_active = False
            _save(manager, t)
    topo.is_active = True
    _save(manager, topo)
    return topo


def _delete(manager, cls, row):
    rid = getattr(row, 'id', None)
    if rid is not None and hasattr(manager, 'deleteTreeNode') and rid in (manager.objectTables.get(cls) or {}):
        manager.deleteTreeNode(className=cls, nodePolariId=rid, instancesDeleted=[], migratedInstances=[])
    else:
        table = manager.objectTables.get(cls) or {}
        for k, v in list(table.items()):
            if v is row:
                table.pop(k)
    db = getattr(manager, 'db', None)
    if db is not None and rid is not None and hasattr(db, 'deleteRowsWhere'):
        if db.deleteRowsWhere(cls, 'id', rid) == -1:
            return 'the database refused the delete of %s:%s (the row is gone from memory; see the backend log)' % (cls, row.name)
    return ''


def apply(manager, plan_digest):
    from topology.topology_self import instance_name
    p = plan(manager)
    if not p['ok']:
        return dict(p, ok=False)
    if not p['retire'] and not p['rehome']:
        return {'ok': True, 'retired': [], 'rehomed': [], 'backup': None, 'words': p['words'] + '; nothing changed'}
    if plan_digest != p['planDigest']:
        return {'ok': False, 'retired': [], 'rehomed': [], 'backup': None, 'planDigest': p['planDigest'],
                'words': 'refused: the plan changed since it was reviewed (or no planDigest was given); review the current '
                         'plan and apply with its planDigest %s' % p['planDigest']}
    me = instance_name()
    active = next((getattr(t, 'name', '') for t in _rows(manager, 'TopologyDefinition') if getattr(t, 'is_active', False)), '')
    doc = {'schema_version': None, 'kind': 'polari-topology-package'}
    from topology.topology_constants import SCHEMA_VERSION
    doc['schema_version'] = SCHEMA_VERSION
    retire_set = {(d['class'], d['name']) for d in p['retire']}
    for _, cls, section in SECTIONS:
        rows = [_row_dict(r, PACKAGE_FIELDS[cls]) for r in _rows(manager, cls) if (cls, getattr(r, 'name', '')) in retire_set]
        rows.sort(key=lambda d: d['name'])
        doc[section] = rows
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    record = {'kind': 'polari-topology-retire-backup', 'instance': me, 'takenAt': stamp, 'planDigest': p['planDigest'],
              'activeTopology': active, 'rehome': p['rehome'], 'document': doc}
    folder = backup_dir()
    path = os.path.join(folder, '%s%s.json' % (_PREFIX, stamp))
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
        return {'ok': False, 'retired': [], 'rehomed': [], 'backup': None,
                'words': 'refused: backup to %s failed (%s: %s); nothing changed (knob %s)' % (path, type(exc).__name__, exc,
                                                                                          BACKUP_KNOB)}
    backup = {'file': os.path.basename(path), 'dir': folder, 'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data)}
    problems = []
    if p['rehome']:
        _ensure_topology(manager, me)
        for d in p['rehome']:
            row = _find(manager, d['class'], d['name'])
            if row is not None:
                row.topology_name = d['to']
                _save(manager, row)
    for _, cls, _ in reversed(SECTIONS):                 # referencing rows before referenced ones
        for d in [x for x in p['retire'] if x['class'] == cls]:
            row = _find(manager, cls, d['name'])
            if row is not None:
                err = _delete(manager, cls, row)
                if err:
                    problems.append(err)
    try:
        from polariApiServer.persist_debounce import schedule_persist
        schedule_persist(manager, reason='tpl-6 retire example rows')
    except Exception:  # noqa: BLE001 - a host-tool manager has no persistence loop
        pass
    return {'ok': not problems, 'retired': p['retire'], 'rehomed': p['rehome'], 'backup': backup, 'problems': problems,
            'words': '%s: retired %d example row%s, moved %d onto %s; backup %s (sha256 %s); undo with restore %s%s'
                     % (me, len(p['retire']), '' if len(p['retire']) == 1 else 's', len(p['rehome']), me, path,
                        backup['sha256'][:12], backup['file'], '; PROBLEMS: ' + '; '.join(problems) if problems else '')}


def list_backups():
    folder = backup_dir()
    try:
        names = sorted(n for n in os.listdir(folder) if n.startswith(_PREFIX) and n.endswith('.json'))
    except OSError:
        names = []
    return {'ok': True, 'dir': folder, 'backups': names}


def restore(manager, backup_file):
    name = os.path.basename(str(backup_file or ''))
    if not name.startswith(_PREFIX) or not name.endswith('.json') or name != backup_file:
        return {'ok': False, 'created': [], 'unrehomed': [],
                'words': 'refused: name a backup file from the backup list (%s*.json), not a path' % _PREFIX}
    path = os.path.join(backup_dir(), name)
    try:
        with open(path, 'rb') as fh:
            record = json.loads(fh.read().decode('utf-8'))
    except Exception as exc:  # noqa: BLE001
        return {'ok': False, 'created': [], 'unrehomed': [], 'words': 'refused: %s unreadable (%s: %s)' % (path, type(exc).__name__, exc)}
    if record.get('kind') != 'polari-topology-retire-backup':
        return {'ok': False, 'created': [], 'unrehomed': [], 'words': 'refused: %s is not a retire backup' % path}
    doc = record.get('document') or {}
    merged = merge_topology_doc(manager, dict(doc, topology=(doc.get('topology') or [])))
    if not merged.get('ok'):
        return {'ok': False, 'created': [], 'unrehomed': [], 'words': 'refused: ' + str(merged.get('error'))}
    created = []
    for cls, row in merged['creates']:
        _save(manager, _classes()[cls](**row, manager=manager))
        created.append({'class': cls, 'name': row.get('name', '')})
    unrehomed = []
    for d in record.get('rehome') or []:
        row = _find(manager, d['class'], d['name'])
        if row is not None and getattr(row, 'topology_name', '') == d['to']:
            row.topology_name = d['from']
            _save(manager, row)
            unrehomed.append(d)
    was = record.get('activeTopology') or ''
    if was and _find(manager, 'TopologyDefinition', was) is not None:
        for t in _rows(manager, 'TopologyDefinition'):
            on = getattr(t, 'name', '') == was
            if bool(getattr(t, 'is_active', False)) != on:
                t.is_active = on
                _save(manager, t)
    return {'ok': True, 'created': created, 'unrehomed': unrehomed,
            'words': 'restored %d row%s from %s, moved %d back, active topology %s'
                     % (len(created), '' if len(created) == 1 else 's', name, len(unrehomed), was or '(unchanged)')}
