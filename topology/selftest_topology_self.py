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


_cfg = {'backend': 'api.polari-pol.isle'}


def _cfg_fetch(url):
    return {'backend': {'https': {'protocol': 'https', 'url': _cfg['backend'], 'port': '443'}}}


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
    check('fresh: no July rows (only its own instance, only its own device)', _names(m, 'InstanceDefinition') == ['polari-pol']
          and _names(m, 'PolariNodeMachine') == ['member-a'], (_names(m, 'InstanceDefinition'), _names(m, 'PolariNodeMachine')))
    second = S.describe_self(m, live, 'selftest')
    check('second boot: idempotent (nothing created, no duplicates)', second['created'] == []
          and len(m.objectTables['ModuleAssignment']) == 3 and len(m.objectTables['TopologyDefinition']) == 1
          and len(m.objectTables['PolariNodeMachine']) == 1, second)
    S.describe_self(m, live | {'pcb'}, 'selftest')
    check('a module admitted later lands as its own row', 'pcb@polari-pol' in _names(m, 'ModuleAssignment'))

    # -- tpl-1: engine bindings + frontend origins as rows
    from topology.topology_modules import EngineProviderBinding
    from topology.topology_analysis import resolve_edges, validate_topology
    EngineProviderBinding(name='board', url='https://board-engines.isle', bound_from='board-engines', manager=m)
    EngineProviderBinding(name='pcb', url='https://pcb-engines.isle', bound_from='pcb-engines', manager=m)
    links = S.describe_links(m, live, 'selftest', fetch=_cfg_fetch)
    ins = {r.name: r for r in m.objectTables['InstanceDefinition'].values()}
    check('a binding names its worker (kind worker, the bound url)', 'board-engines' in ins and ins['board-engines'].kind == 'worker'
          and ins['board-engines'].api_base_url == 'https://board-engines.isle', links)
    check('the capability sits on the worker', 'board.engines@board-engines' in _names(m, 'ModuleAssignment'))
    edges = {r.name: r for r in m.objectTables.get('ModuleDependencyEdge', {}).values()}
    e = edges.get('board@polari-pol->board.engines')
    check('the live consumer depends on it, resolved to the worker with the binding as evidence', e is not None
          and e.provider_instance_name == 'board-engines' and e.status == 'resolved' and 'EngineProviderBinding:board' in e.evidence_json, edges)
    check('a kind with no verified consumer gets worker + capability rows but no edge, said in words',
          'pcb.engines@pcb-engines' in _names(m, 'ModuleAssignment') and not any('pcb.engines' in n for n in edges)
          and 'no edge for pcb' in links['words'], links['words'])
    check('the other .isle origin is a frontend with its runtime-config connection to this backend',
          ins.get('electronics') is not None and ins['electronics'].public_base_url == 'https://electronics.isle'
          and 'prf-frontend->prf-backend:prf-runtime-config@electronics->polari-pol' in _names(m, 'ServiceConnection'))
    fes = {f['name']: f for f in links['frontends']}
    check("the backend's own origin is not a separate frontend", 'polari-pol' not in fes)
    check('a frontend whose runtime config names this backend is VERIFIED', fes['electronics']['verified']
          and 'VERIFIED' in ins['electronics'].notes, fes)
    _cfg['backend'] = 'api.someone-else.isle'
    other = S.describe_links(m, live, 'selftest', fetch=_cfg_fetch)['frontends'][0]
    check('one naming another backend stays configured/UNVERIFIED, with the host it names', not other['verified']
          and 'api.someone-else.isle' in other['words'], other)
    def _down(url):
        raise OSError('connection refused')
    absent = S.describe_links(m, live, 'selftest', fetch=_down)['frontends'][0]
    check('an absent frontend is UNVERIFIED in words (CORS only authorizes)', not absent['verified']
          and 'unreadable' in absent['words'], absent)
    _cfg['backend'] = 'api.polari-pol.isle'
    os.environ['POLARI_TOPOLOGY_VERIFY'] = 'off'
    off = S.describe_links(m, live, 'selftest', fetch=_cfg_fetch)['frontends'][0]
    os.environ.pop('POLARI_TOPOLOGY_VERIFY')
    check('POLARI_TOPOLOGY_VERIFY=off: not checked, said so', not off['verified'] and 'not checked' in off['words'], off)
    S.describe_links(m, live, 'selftest', fetch=_cfg_fetch)
    topo_name = 'polari-pol'
    resolve_edges(m, topo_name)
    check('resolve_edges keeps the worker as the provider', edges['board@polari-pol->board.engines'].provider_instance_name == 'board-engines')
    report = validate_topology(m, topo_name)
    bad = [f for f in report.get('findings', []) if f.get('severity') == 'error']
    check('the described topology validates with no errors', report.get('valid') and not bad, bad or report)
    again = S.describe_links(m, live, 'selftest', fetch=_cfg_fetch)
    check('second pass: idempotent', again['created'] == [] and again['retired'] == [], again)
    ins['electronics'].notes = 'a person renamed this'
    ins['electronics'].public_base_url = 'https://kept.isle'
    S.describe_links(m, live, 'selftest', fetch=_cfg_fetch)
    check('a row a person edited is left as it is', ins['electronics'].public_base_url == 'https://kept.isle')
    del m.objectTables['EngineProviderBinding'][next(k for k, r in m.objectTables['EngineProviderBinding'].items() if r.name == 'board')]
    gone = S.describe_links(m, live, 'selftest', fetch=_cfg_fetch)
    check('binding removed: the capability disabled, the edge unresolved, both said', 'ModuleAssignment:board.engines@board-engines' in gone['retired']
          and edges['board@polari-pol->board.engines'].status == 'unresolved', gone)

    m.polServer = types.SimpleNamespace(defClassList=[], endpointConstructed=set(live), bootRegistry=None)
    hook = S.on_binding_changed(m, 'selftest')
    check('on_binding_changed refreshes the links from the live modules', hook.get('ok') and any(f['name'] == 'electronics' for f in hook['frontends']), hook)
    check('on_binding_changed never raises (a manager with no server)', S.on_binding_changed(_manager()).get('ok') is False)

    # -- fix 11 hook point: after_boot pulls the registry (when a consumer exists) BEFORE describing the links
    import islemesh.custom.islemesh_engines as IE
    had = hasattr(IE, 'sync_from_registry')
    nb = S.after_boot(m, 'selftest')
    check('no registry consumer yet: after_boot says so and still describes the links', had or ('no engine registry consumer'
          in nb['registry']['words'] and nb['links'].get('ok')), nb.get('registry'))
    order = []
    def fake_sync(manager, source):
        order.append('registry')
        EngineProviderBinding(name='board', url='https://board-engines.isle', bound_from='board-engines', manager=manager)
        return {'ok': True, 'words': 'bound board'}
    saved = getattr(IE, 'sync_from_registry', None)
    IE.sync_from_registry = fake_sync
    try:
        nb = S.after_boot(m, 'selftest')
    finally:
        if saved is None:
            del IE.sync_from_registry
        else:
            IE.sync_from_registry = saved
    check('with a consumer: the registry is pulled first, so its engine is in the same boot\'s links',
          order == ['registry'] and any(e['kind'] == 'board' for e in nb['links']['engines']), nb.get('links'))
    def broken_sync(manager, source):
        raise RuntimeError('core unreachable')
    IE.sync_from_registry = broken_sync
    try:
        nb = S.after_boot(m, 'selftest')
    finally:
        del IE.sync_from_registry
    check('a registry outage never stops the boot (said in words, links still described)',
          nb['registry']['ok'] is False and 'core unreachable' in nb['registry']['words'] and nb['links'].get('ok'), nb.get('registry'))

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
