"""
Selftest for tpl-0 (AI-Notes/plans/TOPOLOGY_LAYERS_PLAN.md): a backend describes itself; the July snapshot is seeded only
where it is true; a fresh backend's benches get their shipped topology specs (manual fix 13).

Run from polari-framework/:  PYTHONPATH=modules python3 -m topology.selftest_topology_self

In-memory manager (the cmod selftest shape): no DB, no falcon.
"""
import os
import types

_results = []


def check(label, cond, extra=''):
    _results.append(bool(cond))
    print('%s: %s%s' % ('PASS' if cond else 'FAIL', label, (' - %s' % extra) if extra and not cond else ''))


def _manager():
    return types.SimpleNamespace(objectTables={}, idList=[], db=None, noteTreeMutation=lambda *a, **k: None)


def _env(**kw):
    keys = ('POLARI_INSTANCE_NAME', 'POLARI_INSTANCE_ID', 'CORS_ORIGINS', 'POLARI_MACHINE_NAME', 'ISLE_HOSTNAME',
            'POLARI_TOPOLOGY_SEED', 'DEPLOY_ENV')
    for k in keys:
        os.environ.pop(k, None)
    for k, v in kw.items():
        os.environ[k] = v


def _names(m, cls):
    return sorted(getattr(r, 'name', '') for r in m.objectTables.get(cls, {}).values())


def main():
    from topology import topology_self as S

    # -- who am I
    _env(POLARI_INSTANCE_NAME='bench-a', CORS_ORIGINS='https://polari-pol.isle')
    check('the POLARI_INSTANCE_NAME knob wins', S.instance_name() == 'bench-a', S.instance_name())
    _env(CORS_ORIGINS='https://polari-pol.isle,https://electronics.isle')
    check('absent the knob, the first https://<name>.isle origin names the instance (the isle generator writes it first)',
          S.instance_name() == 'polari-pol', S.instance_name())
    _env(CORS_ORIGINS='https://prf.example.nip.io')
    check('no knob and no isle origin -> local', S.instance_name() == 'local', S.instance_name())
    _env(ISLE_HOSTNAME='member-a')
    check('the machine comes from ISLE_HOSTNAME when POLARI_MACHINE_NAME is absent', S.machine_name() == 'member-a')
    _env()
    check('no machine knob -> unknown (never a container id)', S.machine_name() == '')

    # -- the July snapshot only where it is true
    _env(POLARI_INSTANCE_NAME='prf-a')
    check('the compose suite instance the snapshot describes (prf-a) keeps the example seed', S.seed_mode() == 'example')
    _env(CORS_ORIGINS='https://polari-pol.isle')
    check('an isle backend gets no example seed', S.seed_mode() == 'none')
    _env(CORS_ORIGINS='https://polari-pol.isle', POLARI_TOPOLOGY_SEED='example')
    check('POLARI_TOPOLOGY_SEED=example forces it anywhere', S.seed_mode() == 'example')
    _env(POLARI_INSTANCE_NAME='prf-a', POLARI_TOPOLOGY_SEED='none')
    check('POLARI_TOPOLOGY_SEED=none turns it off even on prf-a', S.seed_mode() == 'none')

    # -- a fresh isle backend describes itself
    _env(CORS_ORIGINS='https://polari-pol.isle,https://electronics.isle', ISLE_HOSTNAME='member-a', DEPLOY_ENV='development')
    m = _manager()
    live = {'board', 'cmod', 'islemesh'}
    first = S.describe_self(m, live, 'selftest')
    check('fresh: one topology named after the instance, active', _names(m, 'TopologyDefinition') == ['polari-pol']
          and next(iter(m.objectTables['TopologyDefinition'].values())).is_active, first)
    inst = next(iter(m.objectTables.get('InstanceDefinition', {}).values()), None)
    check('fresh: its own InstanceDefinition (kind prf, tier dev, on its device)', inst is not None and inst.name == 'polari-pol'
          and inst.kind == 'prf' and inst.env_tier == 'dev' and inst.machine_name == 'member-a', vars(inst) if inst else None)
    check('fresh: one enabled ModuleAssignment per live module, nothing else',
          _names(m, 'ModuleAssignment') == ['board@polari-pol', 'cmod@polari-pol', 'islemesh@polari-pol'], _names(m, 'ModuleAssignment'))
    check('fresh: no July rows (no machines, no other instances)', _names(m, 'InstanceDefinition') == ['polari-pol']
          and not m.objectTables.get('PolariNodeMachine'))
    second = S.describe_self(m, live, 'selftest')
    check('second boot: idempotent (nothing created, no duplicates)', second['created'] == []
          and len(m.objectTables['ModuleAssignment']) == 3 and len(m.objectTables['TopologyDefinition']) == 1, second)
    S.describe_self(m, live | {'pcb'}, 'selftest')
    check('a module admitted later lands as its own row', 'pcb@polari-pol' in _names(m, 'ModuleAssignment'))

    # -- on the compose suite the example topology stays the one it joins
    _env(POLARI_INSTANCE_NAME='prf-a')
    from topology.selftest_topology import _mgr
    ex = _mgr()
    ex.idList, ex.db, ex.noteTreeMutation = [], None, (lambda *a, **k: None)
    before = vars(ex.objectTables['InstanceDefinition']['prf-a']).copy()
    out = S.describe_self(ex, {'scoring'}, 'selftest')
    check('example: joins the active example topology, creates no topology or instance', out['topology'] == 'staging-a'
          and out['created'] == [], out)
    check('example: the prf-a row its owner wrote is left as it is', vars(ex.objectTables['InstanceDefinition']['prf-a']) == before)

    # -- fix 13: the benches' shipped specs at boot
    try:
        from cmod.cmod_light_topology_selftest import _seed
        from cmod.custom import bench_topology_spec as SP
    except ImportError as exc:
        check('cmod importable for the bench half', False, exc)
    else:
        bm = _manager()
        _seed(bm)
        shipped = {s['name'] for s in SP.specs()}
        benches = [r for r in bm.objectTables.get('BenchSolution', {}).values() if getattr(r, 'system', '') in shipped]
        a = SP.apply_shipped(bm)
        check('fresh: every Bench Solution whose System ships a spec gets it (%d)' % len(benches),
              benches and sum(1 for x in a if x['applied']) == len(benches), a)
        b = SP.apply_shipped(bm)
        check('second boot: nothing re-applied; each says it already holds its spec',
              b and not any(x['applied'] for x in b) and all('already holds' in x['words'] for x in b), b)

    _env()
    print('\n%d/%d passed' % (sum(_results), len(_results)))
    return 0 if all(_results) else 1


if __name__ == '__main__':
    raise SystemExit(main())
