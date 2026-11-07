"""
Selftest for tpl-6 (AI-Notes/plans/TOPOLOGY_LAYERS_PLAN.md; Codex gate 8): retire the 2026-07-09 example rows as one
generalized operation — dry-run plan, review-bound apply, verified backup, idempotent, restore — on a manager shaped like
the live core: the REAL topology_seed rows, active, with the backend's own tpl-0 rows attached to them.

Run from polari-framework/:  PYTHONPATH=.:modules python3 -m topology.selftest_example_retire

In-memory manager (the selftest_topology_self shape) with a recording stand-in DB; the backup goes to a temp dir.
"""
import json
import hashlib
import os
import shutil
import tempfile
import types

_results = []


def check(label, cond, extra=''):
    _results.append(bool(cond))
    print('%s: %s%s' % ('PASS' if cond else 'FAIL', label, (' - %r' % (extra,)) if extra and not cond else ''))


class _DB:
    def __init__(self):
        self.saved, self.deleted = [], []

    def saveInstanceInDB(self, row):
        self.saved.append((type(row).__name__, getattr(row, 'name', '')))

    def deleteRowsWhere(self, table, column, value):
        self.deleted.append((table, column, value))
        return 1


def _manager():
    m = types.SimpleNamespace(objectTables={}, idList=[], db=_DB(), noteTreeMutation=lambda *a, **k: None)
    m.tree_deletes = []

    def deleteTreeNode(className, nodePolariId, instancesDeleted=None, migratedInstances=None, **_):
        # the CRUDE call shape: the operation must pass FRESH lists (objectTreeManagerDecorators' defaults are shared)
        m.tree_deletes.append((className, nodePolariId, instancesDeleted == [] and instancesDeleted is not None))
        m.objectTables[className].pop(nodePolariId)
        return [nodePolariId], []
    m.deleteTreeNode = deleteTreeNode
    return m


def _env(**kw):
    for k in ('POLARI_INSTANCE_NAME', 'POLARI_INSTANCE_ID', 'CORS_ORIGINS', 'POLARI_MACHINE_NAME', 'ISLE_HOSTNAME',
              'POLARI_TOPOLOGY_SEED', 'DEPLOY_ENV', 'POLARI_TOPOLOGY_BACKUP_DIR', 'POLARI_TOPOLOGY_VERIFY'):
        os.environ.pop(k, None)
    os.environ.update(kw)


def _names(m, cls):
    return sorted(getattr(r, 'name', '') for r in m.objectTables.get(cls, {}).values())


def _find(m, cls, name):
    return next((r for r in m.objectTables.get(cls, {}).values() if getattr(r, 'name', '') == name), None)


def _seed(m):
    """The REAL 2026-07-09 snapshot, as the example seed writes it."""
    from topology import topology_seed as S
    from topology.topology_basis import InstanceDefinition, OrchestrationTarget, PolariNodeMachine
    from topology.topology_links import ServiceConnection
    from topology.topology_modules import ModuleAssignment, ModuleDependencyEdge
    from topology.topology_state import TopologyDefinition
    for var, cls in (('SEED_NODE_MACHINES', PolariNodeMachine), ('SEED_ORCHESTRATION_TARGETS', OrchestrationTarget),
                     ('SEED_TOPOLOGY_DEFINITIONS', TopologyDefinition), ('SEED_INSTANCE_DEFINITIONS', InstanceDefinition),
                     ('SEED_MODULE_ASSIGNMENTS', ModuleAssignment), ('SEED_MODULE_DEPENDENCY_EDGES', ModuleDependencyEdge),
                     ('SEED_SERVICE_CONNECTIONS', ServiceConnection)):
        for entry in getattr(S, var):
            cls(**entry, manager=m)
    _find(m, 'TopologyDefinition', 'staging-a').is_active = True


def _counts(m):
    return {cls: len(rows) for cls, rows in m.objectTables.items()}


def main():
    from topology import topology_example_retire as R
    from topology import topology_self as S
    from topology import topology_seed as SEED
    tmp = tempfile.mkdtemp(prefix='tpl6-')
    try:
        # -- the live core's shape: July rows active, then the backend describes itself at boot (tpl-0)
        _env(CORS_ORIGINS='https://polari.isle', ISLE_HOSTNAME='isle-core', POLARI_TOPOLOGY_BACKUP_DIR=tmp)
        m = _manager()
        _seed(m)
        S.describe_self(m, {'cmod', 'islemesh'}, 'selftest')
        check('setup: tpl-0 attached the self rows to the active July topology (what core shows today)',
              _find(m, 'InstanceDefinition', 'polari').topology_name == 'staging-a'
              and _find(m, 'ModuleAssignment', 'cmod@polari') is not None)
        check('setup: core runs on isle-core, a machine the snapshot also names (no second machine row created)',
              _names(m, 'PolariNodeMachine') == sorted(e['name'] for e in SEED.SEED_NODE_MACHINES))
        psc = _find(m, 'InstanceDefinition', 'psc-a')
        psc.notes = 'kept by a person: the scorecard moves here later'          # a person's edit
        edge = next(iter(m.objectTables['ModuleDependencyEdge'].values()))
        edge.status, edge.provider_instance_name = 'unresolved', ''              # `resolve` recomputed it: not an edit
        before = _counts(m)

        # -- provenance labels every row
        prov = R.provenance(m)
        check('provenance: an untouched snapshot row is example', prov['InstanceDefinition']['prf-a']['kind'] == 'example')
        check('provenance: the backend\'s own rows are self', prov['InstanceDefinition']['polari']['kind'] == 'self'
              and prov['ModuleAssignment']['cmod@polari']['kind'] == 'self')
        check('provenance: a person-edited snapshot row is example-edited, naming the field',
              prov['InstanceDefinition']['psc-a']['kind'] == 'example-edited' and 'notes' in prov['InstanceDefinition']['psc-a']['words'])
        check('provenance: a recomputed edge status is not an edit', prov['ModuleDependencyEdge'][edge.name]['kind'] == 'example')

        # -- the plan: a dry run
        p = R.plan(m)
        retire = {(d['class'], d['name']) for d in p['retire']}
        keep = {(d['class'], d['name']): d['why'] for d in p['keep']}
        check('plan: ok, and changes nothing', p['ok'] and _counts(m) == before, p.get('words'))
        check('plan: retires the untouched July instances (prf-a, engines, odoo ...)',
              {('InstanceDefinition', n) for n in ('prf-a', 'engines', 'odoo', 'livekit')} <= retire)
        check('plan: retires the July topology itself', ('TopologyDefinition', 'staging-a') in retire)
        check('plan: never retires a self row', not any(n == 'polari' or n.endswith('@polari') for _, n in retire))
        check('plan: keeps the person-edited instance, saying why', ('InstanceDefinition', 'psc-a') in keep
              and 'notes' in keep[('InstanceDefinition', 'psc-a')])
        check('plan: keeps isle-core because the kept self instance runs there', ('PolariNodeMachine', 'isle-core') in keep
              and 'InstanceDefinition:polari' in keep[('PolariNodeMachine', 'isle-core')], keep.get(('PolariNodeMachine', 'isle-core')))
        check('plan: keeps the machine the kept psc-a still names', ('PolariNodeMachine', psc.machine_name) in keep)
        check('plan: retires the recomputed edge (status is derived)', ('ModuleDependencyEdge', edge.name) in retire)
        check('plan: never touches the orchestration vocabulary', not any(c == 'OrchestrationTarget' for c, _ in retire))
        rehome = {(d['class'], d['name']): d['to'] for d in p['rehome']}
        check('plan: moves the kept rows on staging-a onto a topology named after the instance',
              rehome.get(('InstanceDefinition', 'polari')) == 'polari' and rehome.get(('InstanceDefinition', 'psc-a')) == 'polari'
              and rehome.get(('ModuleAssignment', 'cmod@polari')) == 'polari')
        check('plan: a digest binds the review', len(p['planDigest']) == 64 and R.plan(m)['planDigest'] == p['planDigest'])

        # -- apply refuses an unreviewed or stale plan
        r = R.apply(m, '')
        check('apply with no digest: refused, nothing changed, no backup', not r['ok'] and _counts(m) == before
              and not os.listdir(tmp) and p['planDigest'] in r['words'])
        r = R.apply(m, 'f' * 64)
        check('apply with a stale digest: refused', not r['ok'] and _counts(m) == before)

        # -- apply
        r = R.apply(m, p['planDigest'])
        check('apply: ok', r['ok'], r.get('words'))
        b = r['backup'] or {}
        path = os.path.join(tmp, b.get('file', '-'))
        raw = open(path, 'rb').read() if os.path.isfile(path) else b''
        check('apply: a backup file in the backup dir, sha256 and size as reported',
              raw and hashlib.sha256(raw).hexdigest() == b['sha256'] and len(raw) == b['bytes'])
        rec = json.loads(raw.decode('utf-8')) if raw else {}
        check('apply: the backup holds every retired row as a topology package, the rehome list and the active topology',
              rec.get('document', {}).get('kind') == 'polari-topology-package'
              and sum(len(rec['document'][s]) for s in ('machines', 'topology', 'instances', 'assignments', 'edges', 'connections'))
              == len(p['retire']) and rec.get('rehome') == p['rehome'] and rec.get('activeTopology') == 'staging-a')
        check('apply: the retired rows are gone', all(_find(m, c, n) is None for c, n in retire))
        check('apply: deleted through deleteTreeNode with fresh lists and from the DB by id',
              len(m.tree_deletes) == len(retire) and all(fresh for _, _, fresh in m.tree_deletes)
              and len(m.db.deleted) == len(retire) and all(col == 'id' for _, col, _ in m.db.deleted))
        check('apply: the kept rows remain', all(_find(m, c, n) is not None for c, n in keep))
        check('apply: the self rows now sit on topology polari, which is the active one',
              _find(m, 'InstanceDefinition', 'polari').topology_name == 'polari'
              and _find(m, 'TopologyDefinition', 'polari') is not None and _find(m, 'TopologyDefinition', 'polari').is_active)
        check('apply: OrchestrationTarget rows untouched', len(m.objectTables['OrchestrationTarget']) == before['OrchestrationTarget'])

        # -- idempotent
        p2 = R.plan(m)
        check('second plan: nothing to retire', p2['ok'] and not p2['retire'] and not p2['rehome'], p2.get('words'))
        r2 = R.apply(m, '')
        check('second apply: ok, nothing changed, no second backup', r2['ok'] and r2['backup'] is None and len(os.listdir(tmp)) == 1)
        check('a later boot does not bring them back (tpl-0 on an isle backend: seed none)', S.seed_mode() == 'none')

        # -- backups list + restore
        lb = R.list_backups()
        check('backups: listed by name', lb['backups'] == [b['file']])
        bad = R.restore(m, '../' + b['file'])
        check('restore: a path is refused (names from the list only)', not bad['ok'])
        rs = R.restore(m, b['file'])
        check('restore: ok', rs['ok'], rs.get('words'))
        check('restore: every retired row is back', all(_find(m, c, n) is not None for c, n in retire))
        check('restore: the self rows are back on staging-a, which is active again',
              _find(m, 'InstanceDefinition', 'polari').topology_name == 'staging-a' and _find(m, 'TopologyDefinition', 'staging-a').is_active
              and not _find(m, 'TopologyDefinition', 'polari').is_active)
        check('restore: the restored rows hold the snapshot values', R.provenance(m)['InstanceDefinition']['prf-a']['kind'] == 'example')
        check('restore: a second restore creates nothing (idempotent by name)', R.restore(m, b['file'])['created'] == [])

        # -- a backup that cannot be written stops everything
        _env(CORS_ORIGINS='https://polari.isle', ISLE_HOSTNAME='isle-core', POLARI_TOPOLOGY_BACKUP_DIR=os.path.join(tmp, b['file']))
        mid = _counts(m)
        r3 = R.apply(m, R.plan(m)['planDigest'])
        check('apply with an unwritable backup dir: refused, nothing changed', not r3['ok'] and _counts(m) == mid
              and 'backup' in r3['words'], r3.get('words'))

        # -- where the snapshot is the reality
        _env(POLARI_INSTANCE_NAME='prf-a', POLARI_TOPOLOGY_BACKUP_DIR=tmp)
        pr = R.plan(m)
        check('prf-a (the instance the snapshot describes): plan refused, nothing listed', not pr['ok'] and not pr['retire']
              and 'POLARI_TOPOLOGY_SEED=none' in pr['words'])
        check('prf-a: apply refused too', not R.apply(m, '')['ok'])

        # -- a fresh tpl-0 backend has nothing to retire
        _env(CORS_ORIGINS='https://polari-pol.isle', ISLE_HOSTNAME='pol-core', POLARI_TOPOLOGY_BACKUP_DIR=tmp)
        f = _manager()
        S.describe_self(f, {'board'}, 'selftest')
        pf = R.plan(f)
        check('fresh backend: nothing to retire, nothing kept as example', pf['ok'] and not pf['retire'] and not pf['rehome'])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
        _env()
    passed = sum(_results)
    print('\n%d/%d passed' % (passed, len(_results)))
    return 0 if passed == len(_results) else 1


if __name__ == '__main__':
    raise SystemExit(main())
