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
    print('%s: %s%s' % ('PASS' if cond else 'FAIL', label, (' - %r' % (extra,)) if extra and not cond else ''))


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
        if saved is None:
            del IE.sync_from_registry
        else:
            IE.sync_from_registry = saved
    check('a registry outage never stops the boot (said in words, links still described)',
          nb['registry']['ok'] is False and 'core unreachable' in nb['registry']['words'] and nb['links'].get('ok'), nb.get('registry'))

    # -- PRODUCTION DEFAULTS (the 2026-11-06 lesson: a live core boot hit NameError in a path every test had injected around).
    # Nothing injected but the HTTP boundary itself: polariApiServer.outbound.http_request.
    import contextlib
    import io
    import json as _json
    from polariApiServer import outbound
    served, calls = {}, []

    @contextlib.contextmanager
    def fake_http(kind, name, method, url, **kw):
        calls.append(url)
        if url not in served:
            raise OSError('connection refused: %s' % url)
        yield io.BytesIO(_json.dumps(served[url]).encode())
    real_http = outbound.http_request
    outbound.http_request = fake_http
    try:
        served['https://electronics.isle/assets/runtime-config.json'] = {'backend': {'https': {'url': 'api.polari-pol.isle'}}}
        ok_ev = S.frontend_evidence('https://electronics.isle', 'polari-pol')
        check('production frontend_evidence (no fetch injected) reads through the outbound seam and verifies', ok_ev[0]
              and 'https://electronics.isle/assets/runtime-config.json' in calls, ok_ev)
        down = S.frontend_evidence('https://gone.isle', 'polari-pol')
        check('production frontend_evidence: an unreachable frontend is UNVERIFIED in words, never raised', not down[0]
              and 'unreadable' in down[1], down)
        pm = _manager()
        pm.polServer = types.SimpleNamespace(defClassList=[], endpointConstructed={'board', 'islemesh'}, bootRegistry=None)
        pm.objectTyping = [types.SimpleNamespace(className='EngineProviderBinding')]
        # the storage boundary, as managedDB answers: save -> None (False only on refusal), delete -> a row count
        pm.db = types.SimpleNamespace(saveInstanceInDB=lambda row: None, deleteRowsWhere=lambda *a: 1)
        os.environ.pop('ISLE_CORE_API', None)
        nb = S.after_boot(pm, 'selftest')
        check('production after_boot, ISLE_CORE_API unset: the REAL consumer says no registry, the boot goes on',
              nb['registry'].get('ok') and 'ISLE_CORE_API unset' in nb['registry'].get('words', '') and nb['links'].get('ok'),
              nb.get('registry'))
        os.environ['ISLE_CORE_API'] = 'https://api.polari.isle'
        served['https://api.polari.isle/api/islemesh/engines'] = {'ok': True, 'engines': [
            {'name': 'board-engines@board', 'app': 'board-engines', 'provides': 'board', 'url': 'https://board-engines.isle',
             'is_mock': False}]}
        nb = S.after_boot(pm, 'selftest')
        check('production after_boot, registry set: the REAL pull binds board and the same boot draws its edge',
              nb['registry'].get('ok') and any(e['kind'] == 'board' for e in nb['links'].get('engines', [])),
              (nb.get('registry'), nb.get('links', {}).get('words')))
        del served['https://api.polari.isle/api/islemesh/engines']
        nb = S.after_boot(pm, 'selftest')
        check('production after_boot, registry unreachable: said in words, nothing retired, the boot goes on',
              nb['registry'].get('ok') is False and 'unreachable' in nb['registry'].get('words', '')
              and any(e['kind'] == 'board' for e in nb['links'].get('engines', [])), nb.get('registry'))
    finally:
        outbound.http_request = real_http
        os.environ.pop('ISLE_CORE_API', None)

    # -- tpl-4: "Needs an isle" states from timestamped evidence (Codex's review: configuration is not readiness)
    from datetime import datetime, timedelta, timezone
    from topology.topology_isle_needs import isle_needs
    from islemesh.islemesh_basis import IsleDevice, IsleEngine
    now = datetime(2026, 11, 6, 18, 0, tzinfo=timezone.utc)
    isle_feats = lambda r: {f['key']: f for f in r['features'] if f['requiresIsle']}
    os.environ.pop('ISLE_CORE_API', None)
    nm = _manager()
    none = isle_needs(nm, now)
    check('no isle: said so in words', not none['isle']['configured'] and 'no isle' in none['isle']['words'])
    check('no isle: the 8 Polari-only features are "supported"', [f['state'] for f in none['features'] if not f['requiresIsle']] == ['supported'] * 8)
    check('no isle: every isle feature is not-configured, says "needs an isle" and names its fallback', all(
        f['state'] == 'not-configured' and f['words'].startswith('needs an isle') and f['fallback'] for f in isle_feats(none).values()))
    check('no response field claims availability (no "available" key at all)', all('available' not in f for f in none['features']))
    os.environ['ISLE_CORE_API'] = 'https://unreachable.invalid'
    cfg = isle_feats(isle_needs(nm, now))
    check('NEGATIVE configured-only (unreachable origin, no rows): every isle feature "configured", none last-reported, every fallback shown',
          all(f['state'] == 'configured' and f['fallback'] and not f['observedAt'] for f in cfg.values()), cfg)
    check('NEGATIVE configured-only: trusted HTTPS is explicitly not claimed', 'configured is not trusted' in cfg['trusted-names']['words'])
    check('NEGATIVE configured-only: placement names the shared operation and both authorizations, never "executable"',
          'isle polari' in cfg['run-placement']['words'] and 'sudo over SSH' in cfg['run-placement']['words']
          and 'pkexec' in cfg['run-placement']['words'] and 'not evaluated as executable' in cfg['run-placement']['words'])
    hm = _manager()
    IsleDevice(name='member-old', last_seen=(now - timedelta(days=30)).isoformat(), manager=hm)
    IsleDevice(name='member-nostamp', manager=hm)
    hist = isle_feats(isle_needs(hm, now))
    check('NEGATIVE historical device-only: a 30-day-old report is "stale" with its age, fallback still shown',
          hist['discovery']['state'] == 'stale' and hist['discovery']['ageSeconds'] == 30 * 86400 and hist['discovery']['fallback'], hist['discovery'])
    check('NEGATIVE devices without resource observations: device resources not reported', hist['device-resources']['state'] == 'configured'
          and 'no resources observed' in hist['device-resources']['words'], hist['device-resources'])
    check('NEGATIVE devices never imply trust or placement', hist['trusted-names']['state'] == 'configured' and hist['run-placement']['state'] == 'configured')
    fm = _manager()
    IsleDevice(name='member-b', last_seen=(now - timedelta(minutes=5)).isoformat(), manager=fm)
    EngineProviderBinding(name='board', url='https://board-engines.isle', bound_from='board-engines',
                          bound_at=(now - timedelta(minutes=2)).isoformat(), manager=fm)
    IsleEngine(name='board-engines@board', app_name='board-engines', provides='board', url='https://board-engines.isle', bound=True,
               notes='[isle registry] wired', manager=fm)
    fresh = isle_feats(isle_needs(fm, now))
    check('fresh reports: discovery + network view last-reported with observedAt and age, no fallback',
          all(fresh[k]['state'] == 'last-reported' and fresh[k]['ageSeconds'] == 300 and not fresh[k]['fallback'] for k in ('discovery', 'network-view')), fresh['discovery'])
    check('fresh registry binding: engine routing last-reported at its bound_at', fresh['engine-auto-routing']['state'] == 'last-reported'
          and fresh['engine-auto-routing']['ageSeconds'] == 120, fresh['engine-auto-routing'])
    check('even with fresh reports, trust and placement stay "configured" (no observation of them exists)',
          fresh['trusted-names']['state'] == 'configured' and fresh['run-placement']['state'] == 'configured')
    os.environ['POLARI_ISLE_EVIDENCE_MAX_AGE_S'] = '60'
    tight = isle_feats(isle_needs(fm, now))
    check('the max-age knob: a 5-minute report is stale under POLARI_ISLE_EVIDENCE_MAX_AGE_S=60', tight['discovery']['state'] == 'stale'
          and 'STALE' in tight['discovery']['words'])
    os.environ.pop('POLARI_ISLE_EVIDENCE_MAX_AGE_S')
    # Codex's edge: an impossible FUTURE report is never fresh; small skew is tolerated; the raw timestamp stays as evidence
    sm = _manager()
    IsleDevice(name='member-future', last_seen='2099-01-01T00:00:00Z', manager=sm)
    fut = isle_needs(sm, now)
    d = isle_feats(fut)['discovery']
    check('NEGATIVE future report (2099 evaluated 2026-11-06): state clock-skew, not last-reported; no age; fallback shown',
          d['state'] == 'clock-skew' and d['ageSeconds'] is None and not d['observedAt'] and d['fallback'], d)
    check('the future report keeps its raw timestamp as evidence, flagged, with its (negative) age',
          d['evidence'][0]['observedAt'] == '2099-01-01T00:00:00Z' and d['evidence'][0].get('clockSkew')
          and d['evidence'][0]['ageSeconds'] < 0 and 'CLOCK SKEW' in d['words'], d['evidence'])
    check('the isle summary never names a future report as the newest', fut['isle']['reported']['lastSeen'] == ''
          and 'dated in the future' in fut['isle']['words'], fut['isle'])
    km = _manager()
    IsleDevice(name='member-ahead', last_seen=(now + timedelta(seconds=90)).isoformat(), manager=km)
    ahead = isle_feats(isle_needs(km, now))['discovery']
    check('a report 90 s ahead (within the 300 s tolerance) is ordinary skew: last-reported, age 0, never negative',
          ahead['state'] == 'last-reported' and ahead['ageSeconds'] == 0, ahead)
    IsleDevice(name='member-future', last_seen='2099-01-01T00:00:00Z', manager=km)
    mixed = isle_feats(isle_needs(km, now))['discovery']
    check('mixed: the usable report decides; the future one is ignored and said', mixed['state'] == 'last-reported'
          and 'ignored 1 report dated in the future' in mixed['words'], mixed)
    os.environ['POLARI_ISLE_CLOCK_SKEW_S'] = '30'
    sk = _manager()
    IsleDevice(name='member-ahead', last_seen=(now + timedelta(seconds=90)).isoformat(), manager=sk)
    sk_d = isle_feats(isle_needs(sk, now))['discovery']
    os.environ.pop('POLARI_ISLE_CLOCK_SKEW_S')
    check('the tolerance knob: 90 s ahead is clock-skew under POLARI_ISLE_CLOCK_SKEW_S=30', sk_d['state'] == 'clock-skew', sk_d)
    check('every evidence item carries its own observedAt and ageSeconds', all('ageSeconds' in e and 'observedAt' in e
          for f in isle_needs(fm, now)['features'] for e in f['evidence']))

    os.environ.pop('ISLE_CORE_API', None)
    noorigin = isle_feats(isle_needs(fm, now))
    check('reports without a configured origin still count as reported (the isle posted here)', noorigin['discovery']['state'] == 'last-reported')

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
