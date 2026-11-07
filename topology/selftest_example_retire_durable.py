"""
Selftest for Codex's two required tpl-6 corrections (2026-11-07):

1. DURABLE FIRST. A stand-in database that KEEPS state (so a "restart" rebuilds memory from what is durable) and refuses,
   returns -1 / False / None, or raises at any chosen save or delete. After every failure: memory == the database, the
   receipt says ok False with the words, retryPlanDigest is the plan of the remaining work, a rebuilt manager plans the
   same, and the retry converges to the clean result. Restore likewise, and it never overwrites what a person wrote since.
   Includes Codex's exact control (isle-core ~/collab/tpl6-review/isle-persistence-review.py): every save refused.
2. FAIL CLOSED. operator_gate and the HTTP handlers themselves (a direct call, bypassing the CLI and UI): a non-loopback
   caller, a forwarded loopback, and a non-admin identity get 403 and NOTHING is written, backed up or deleted.

Run from polari-framework/:  PYTHONPATH=.:modules python3 -m topology.selftest_example_retire_durable
"""
import io
import json
import os
import shutil
import sys
import tempfile
import types

from topology import selftest_example_retire as T

_results = []


def check(label, cond, extra=''):
    _results.append(bool(cond))
    print('%s: %s%s' % ('PASS' if cond else 'FAIL', label, (' - %r' % (extra,)) if extra and not cond else ''))


_SIMPLE = (str, int, float, bool)


class Store:
    """A database double that keeps rows by (class, name), with scripted failures."""

    def __init__(self):
        self.rows, self.ids, self.rules = {}, {}, []

    def fail(self, op, cls=None, name=None, mode='false'):
        self.rules.append((op, cls, name, mode))

    def _rule(self, op, cls, name):
        for r_op, r_cls, r_name, mode in self.rules:
            if r_op == op and r_cls in (None, cls) and r_name in (None, name):
                return mode
        return None

    @staticmethod
    def _answer(mode, ok):
        if mode == 'raise':
            raise RuntimeError('scripted database failure')
        return {'false': False, '-1': -1, 'none': None}.get(mode, ok)

    def saveInstanceInDB(self, row):
        cls, name = type(row).__name__, getattr(row, 'name', '')
        mode = self._rule('save', cls, name)
        if mode:
            return self._answer(mode, True)
        self.rows[(cls, name)] = {k: v for k, v in vars(row).items()
                                  if not k.startswith('_') and k not in ('manager', 'id') and isinstance(v, _SIMPLE)}
        self.ids[getattr(row, 'id', None)] = (cls, name)
        return True

    def deleteRowsWhere(self, cls, column, value):
        key = self.ids.get(value)
        mode = self._rule('delete', cls, key[1] if key else None)
        if mode:
            return self._answer(mode, 1)
        if key and key in self.rows:
            self.rows.pop(key)
            return 1
        return 0


def _classes():
    from topology.topology_basis import InstanceDefinition, OrchestrationTarget, PolariNodeMachine
    from topology.topology_links import ServiceConnection
    from topology.topology_modules import ModuleAssignment, ModuleDependencyEdge
    from topology.topology_state import TopologyDefinition, TopologyObservation
    return {c.__name__: c for c in (InstanceDefinition, OrchestrationTarget, PolariNodeMachine, ServiceConnection,
                                     ModuleAssignment, ModuleDependencyEdge, TopologyDefinition, TopologyObservation)}


def _core(store):
    """The live core's shape (T's setup), every row durable in `store`."""
    from topology import topology_self as S
    m = T._manager()
    m.db = store
    T._seed(m)
    for table in list(m.objectTables.values()):
        for row in list(table.values()):
            store.saveInstanceInDB(row)
    S.describe_self(m, {'cmod', 'islemesh'}, 'selftest')
    return m


def _rebuild(store):
    """A restart: a fresh manager holding exactly what the database kept."""
    m = T._manager()
    m.db = store
    classes = _classes()
    for (cls, name), fields in sorted(store.rows.items()):
        row = classes[cls](name=name, manager=m)
        for k, v in fields.items():
            setattr(row, k, v)
        store.ids[getattr(row, 'id', None)] = (cls, name)
    return m


def _state(m):
    return {(cls, getattr(r, 'name', '')): (getattr(r, 'topology_name', None), bool(getattr(r, 'is_active', False)))
            for cls, table in m.objectTables.items() for r in table.values()}


def _store_state(store):
    return {key: (f.get('topology_name'), bool(f.get('is_active', False))) for key, f in store.rows.items()}


def _coherent(m, store):
    return _state(m) == _store_state(store)


def _env(tmp):
    T._env(CORS_ORIGINS='https://polari.isle', ISLE_HOSTNAME='isle-core', POLARI_TOPOLOGY_BACKUP_DIR=tmp)


def _clean_result(tmp):
    """The end state of an apply with no failures (the target every retry must reach)."""
    from topology import topology_example_retire as R
    store = Store()
    m = _core(store)
    r = R.apply(m, R.plan(m)['planDigest'])
    assert r['ok'], r
    return _state(m)


def durable(R, tmp):
    target = _clean_result(os.path.join(tmp, 'clean'))

    # -- Codex's exact control: every save refused
    store = Store(); m = _core(store); p = R.plan(m)
    before = _state(m)
    store.fail('save', mode='false')
    a = R.apply(m, p['planDigest'])
    check('control (every save refused): apply says ok False, with the failure in words', not a['ok'] and a['problems'], a)
    check('control: claims nothing moved and nothing retired', a['rehomed'] == [] and a['retired'] == [])
    check('control: memory == database, and unchanged', _coherent(m, store) and _state(m) == before)
    check('control: the retry digest is the plan of what remains (all of it)', a['retryPlanDigest'] == R.plan(m)['planDigest']
          == p['planDigest'])
    b = R.restore(m, a['backup']['file'])
    check('control: restore with every save refused claims nothing either', b['created'] == [] and _coherent(m, store))

    check('control: that restore has nothing to do (apply changed nothing), so it truthfully creates nothing',
          b['created'] == [] and b['removed'] == [])
    store = Store(); m = _core(store); a = R.apply(m, R.plan(m)['planDigest'])
    store.fail('save', mode='false')
    b = R.restore(m, a['backup']['file'])
    check('restore after a REAL apply with every save refused: ok False, nothing claimed, memory == database',
          not b['ok'] and b['created'] == [] and b['problems'] and _coherent(m, store), b.get('words'))

    # -- a rehome save that raises midway
    store = Store(); m = _core(store); p = R.plan(m)
    store.fail('save', 'InstanceDefinition', 'polari', 'raise')
    a = R.apply(m, p['planDigest'])
    check('rehome raises midway: ok False, stopped, words name the row', not a['ok'] and 'InstanceDefinition:polari' in a['problems'][0], a.get('problems'))
    check('rehome raises: memory == database (the failed field reverted)', _coherent(m, store))
    check('rehome raises: the self instance polari still on staging-a in memory and on disk',
          T._find(m, 'InstanceDefinition', 'polari').topology_name == 'staging-a'
          and store.rows[('InstanceDefinition', 'polari')]['topology_name'] == 'staging-a')
    check('rehome raises: nothing was deleted', not a['retired'] and all(T._find(m, d['class'], d['name']) for d in p['retire']))
    re = _rebuild(store)
    check('rehome raises: a restart plans exactly the retry digest', R.plan(re)['planDigest'] == a['retryPlanDigest'])
    check('rehome raises: the retry is NOT "nothing to do"', R.plan(m)['retire'] and R.plan(m)['rehome'])
    store.rules.clear()
    r2 = R.apply(m, a['retryPlanDigest'])
    check('rehome raises: the retry with retryPlanDigest completes', r2['ok'], r2.get('words'))
    check('rehome raises: and converges to the clean result, memory == database', _state(m) == target and _coherent(m, store))

    # -- deletes: -1, False, None, raise; each stops with the row kept
    for mode in ('-1', 'false', 'none', 'raise'):
        store = Store(); m = _core(store); p = R.plan(m)
        store.fail('delete', 'ModuleAssignment', 'scoring@prf-a', mode)
        a = R.apply(m, p['planDigest'])
        check('delete %s: ok False, the row still in memory and on disk' % mode, not a['ok']
              and T._find(m, 'ModuleAssignment', 'scoring@prf-a') is not None and ('ModuleAssignment', 'scoring@prf-a') in store.rows)
        check('delete %s: stopped before the referenced rows (prf-a kept), memory == database' % mode,
              T._find(m, 'InstanceDefinition', 'prf-a') is not None and _coherent(m, store))
        check('delete %s: a restart plans the retry digest' % mode, R.plan(_rebuild(store))['planDigest'] == a['retryPlanDigest'])
        store.rules.clear()
        r2 = R.apply(m, a['retryPlanDigest'])
        check('delete %s: the retry converges to the clean result' % mode, r2['ok'] and _state(m) == target and _coherent(m, store))

    # -- the instance's own topology cannot be saved: nothing else happens
    store = Store(); m = _core(store); p = R.plan(m)
    store.fail('save', 'TopologyDefinition', 'polari', 'false')
    a = R.apply(m, p['planDigest'])
    check('own topology refused: ok False, no TopologyDefinition polari in memory, nothing moved or deleted',
          not a['ok'] and T._find(m, 'TopologyDefinition', 'polari') is None and not a['rehomed'] and not a['retired']
          and _coherent(m, store))
    check('own topology refused: staging-a stays active', T._find(m, 'TopologyDefinition', 'staging-a').is_active)

    # -- restore: a create refused midway, then the retry
    store = Store(); m = _core(store); p = R.plan(m)
    a = R.apply(m, p['planDigest'])
    after_apply = _state(m)
    store.fail('save', 'InstanceDefinition', 'odoo', 'raise')
    b = R.restore(m, a['backup']['file'])
    check('restore create raises midway: ok False, stopped, memory == database', not b['ok'] and b['problems'] and _coherent(m, store))
    check('restore create raises: the failed row is not left in memory', T._find(m, 'InstanceDefinition', 'odoo') is None)
    store.rules.clear()
    b2 = R.restore(m, a['backup']['file'])
    check('restore retry: ok, creates only what is still missing', b2['ok'] and b2['created']
          and not ({(c['class'], c['name']) for c in b2['created']} & {(c['class'], c['name']) for c in b['created']}))
    check('restore retry: EXACTLY the state before apply (rows, topology, active flags; the own topology apply made is '
          'removed), memory == database', _state(m) == before_apply_keys(R, tmp) and _coherent(m, store),
          sorted(set(_state(m)) ^ set(before_apply_keys(R, tmp))))
    plain = Store(); pm = _core(plain); pa_ = R.apply(pm, R.plan(pm)['planDigest']); pr_ = R.restore(pm, pa_['backup']['file'])
    check('restore: an uninterrupted apply + restore is an exact inverse', pr_['ok'] and pr_['removed']
          and _state(pm) == before_apply_keys(R, tmp) and _coherent(pm, plain))

    # -- restore keeps what a person wrote since
    store = Store(); m = _core(store); p = R.plan(m)
    a = R.apply(m, p['planDigest'])
    from topology.topology_basis import InstanceDefinition
    from topology.topology_state import TopologyDefinition
    mine = InstanceDefinition(name='prf-a', kind='prf', notes='mine, written after the cleanup', topology_name='polari', manager=m)
    store.saveInstanceInDB(mine)
    lab = TopologyDefinition(name='lab', status='applied', is_active=False, manager=m)
    store.saveInstanceInDB(lab)
    R._set(m, T._find(m, 'TopologyDefinition', 'polari'), 'is_active', False)
    R._set(m, lab, 'is_active', True)
    b = R.restore(m, a['backup']['file'])
    check('restore after a person wrote prf-a: ok, prf-a KEPT with their notes', b['ok']
          and T._find(m, 'InstanceDefinition', 'prf-a').notes == 'mine, written after the cleanup'
          and any(k['name'] == 'prf-a' for k in b['kept']))
    check('restore after a person activated lab: lab stays active, said in kept', T._find(m, 'TopologyDefinition', 'lab').is_active
          and not T._find(m, 'TopologyDefinition', 'staging-a').is_active and any(k['name'] == 'lab' for k in b['kept']))
    check('restore with person edits: memory == database', _coherent(m, store))
    check('restore with person edits: the own topology is kept while prf-a (theirs) still uses it',
          T._find(m, 'TopologyDefinition', 'polari') is not None and any(k['name'] == 'polari' for k in b['kept']))


_before_keys = {}


def before_apply_keys(R, tmp):
    if not _before_keys:
        store = Store(); m = _core(store)
        _before_keys.update(_state(m))
    return _before_keys


class _Req:
    def __init__(self, addr, headers=None, user=None, body=None):
        self.remote_addr, self._h = addr, {k.lower(): v for k, v in (headers or {}).items()}
        self.context = types.SimpleNamespace(user_info=user)
        self.bounded_stream = io.BytesIO(json.dumps(body or {}).encode('utf-8'))

    def get_header(self, name):
        return self._h.get(name.lower())


def gate(R, tmp):
    ok = lambda req: R.operator_gate(req)[0]
    check('gate: loopback 127.0.0.1 (docker exec) is the host operator', ok(_Req('127.0.0.1')))
    check('gate: loopback ::1 too', ok(_Req('::1')))
    check('gate: a container-network caller is refused', not ok(_Req('172.18.0.5')))
    check('gate: no address is refused', not ok(_Req('')))
    check('gate: loopback carrying X-Forwarded-For (a proxy) is refused', not ok(_Req('127.0.0.1', {'X-Forwarded-For': '10.0.0.9'})))
    check('gate: loopback carrying Forwarded is refused', not ok(_Req('127.0.0.1', {'Forwarded': 'for=10.0.0.9'})))
    check('gate: a signed-in non-admin from the network is refused', not ok(_Req('172.18.0.5', user={'sub': 'x', 'roles': ['viewer']})))
    real = sys.modules.get('security.custom.security_claims')
    fake = types.ModuleType('security.custom.security_claims')
    fake.is_admin = lambda u: 'polari-admin' in (u.get('roles') or [])
    sys.modules['security.custom.security_claims'] = fake
    try:
        check('gate: a Polari administrator identity (security_claims.is_admin) is accepted',
              ok(_Req('172.18.0.5', user={'sub': 'a', 'roles': ['polari-admin']})))
        fake.is_admin = lambda u: (_ for _ in ()).throw(RuntimeError('broken'))
        check('gate: a broken admin check refuses', not ok(_Req('172.18.0.5', user={'sub': 'a'})))
    finally:
        if real is not None:
            sys.modules['security.custom.security_claims'] = real
        else:
            sys.modules.pop('security.custom.security_claims', None)
    words = R.operator_gate(_Req('172.18.0.5'))[2]
    check('gate: the refusal names the standard paths and never presents the Isle App run as existing',
          'pol topology example-rows retire --digest' in words and 'without --api' in words and 'Nothing was written' in words
          and 'planned, not built yet' in words)

    # the HTTP handlers themselves, called directly (no CLI, no UI)
    from topology.topology_api import TopologyAPI
    store = Store(); m = _core(store); p = R.plan(m)
    fake_self = types.SimpleNamespace(manager=m)
    fake_self._payload = lambda req: TopologyAPI._payload(fake_self, req)
    fake_self._refuse = lambda resp, err, status='400 Bad Request': TopologyAPI._refuse(fake_self, resp, err, status)
    fake_self._operator_only = lambda req, resp: TopologyAPI._operator_only(fake_self, req, resp)
    snap, files = dict(store.rows), set(os.listdir(tmp))
    resp = types.SimpleNamespace(status='200 OK', media=None)
    TopologyAPI.on_post_example_rows_retire(fake_self, _Req('172.18.0.5', body={'planDigest': p['planDigest']}), resp)
    check('HTTP retire from the network with the RIGHT digest: 403, denied', resp.status.startswith('403') and resp.media['denied'])
    check('HTTP retire denied: no write, no backup, no delete', store.rows == snap and set(os.listdir(tmp)) == files
          and _coherent(m, store) and R.plan(m)['planDigest'] == p['planDigest'])
    resp = types.SimpleNamespace(status='200 OK', media=None)
    TopologyAPI.on_post_example_rows_restore(fake_self, _Req('10.1.2.3', body={'backup': 'retire-example-x.json'}), resp)
    check('HTTP restore from the network: 403, nothing written', resp.status.startswith('403') and store.rows == snap)
    resp = types.SimpleNamespace(status='200 OK', media=None)
    TopologyAPI.on_post_example_rows_retire(fake_self, _Req('127.0.0.1', {'X-Forwarded-For': '1.2.3.4'},
                                                            body={'planDigest': p['planDigest']}), resp)
    check('HTTP retire via a forwarding proxy on loopback: 403, nothing written', resp.status.startswith('403') and store.rows == snap)
    resp = types.SimpleNamespace(status='200 OK', media=None)
    TopologyAPI.on_post_example_rows_retire(fake_self, _Req('127.0.0.1', body={'planDigest': p['planDigest']}), resp)
    check('HTTP retire as the host operator: runs (ok, backup written)', resp.media.get('ok') and resp.media.get('backup')
          and _coherent(m, store), resp.media)
    pa = R.plan(_core(Store()))['plannedAction']
    check('plan carries the planned action the Isle App collects (summary, execute door, operator command, undo)',
          pa and pa['kind'] == 'polari.topology.retire-example' and 'retire 48' in pa['summary']
          and pa['execute']['path'] == '/api/topology/example-rows/retire' and pa['operatorCommand'].endswith(pa['digest']))
    check('planned action: stable identity = kind + backend + device + digest', pa['id'] ==
          'polari.topology.retire-example:polari@isle-core:' + pa['digest'] and pa['device'] == 'isle-core')
    check('planned action: status planned, and says the Isle App run is not built yet', pa['status'] == 'planned'
          and 'not built yet' in pa['appRun'])


def main():
    from topology import topology_example_retire as R
    tmp = tempfile.mkdtemp(prefix='tpl6d-')
    try:
        _env(tmp)
        durable(R, tmp)
        gate(R, tmp)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
        T._env()
    passed = sum(_results)
    print('\n%d/%d passed' % (passed, len(_results)))
    return 0 if passed == len(_results) else 1


if __name__ == '__main__':
    raise SystemExit(main())
