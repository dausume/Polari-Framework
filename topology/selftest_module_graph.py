"""
Selftest for the module-level graph semantics (tt-1).

Run from polari-framework/:  python3 -m topology.selftest_module_graph

Stdlib-only, same idiom as selftest_topology: a fake manager built
from the real SEED_* lists with SimpleNamespace rows. Covers:
classification vocabulary (consumer/provider/hybrid/independent/
data-only), reverse-edge computation, deterministic + STABLE
transient/primary designation (kept primary survives recompute;
removing the primary promotes the next consumer), and the
boundary_graph reverse edges.
"""

import copy
import types

from topology.topology_module_graph import (
    classify, designate_transients, module_graph,
)
from topology.topology_seed import (
    SEED_MODULE_ASSIGNMENTS, SEED_MODULE_DEPENDENCY_EDGES,
)

_results = []


def check(label, cond, extra=''):
    _results.append((label, bool(cond)))
    print(f'{"PASS" if cond else "FAIL"}: {label}'
          + (f' — {extra}' if extra and not cond else ''))


def _rows(seed_list):
    return {s['name']: types.SimpleNamespace(**copy.deepcopy(s))
            for s in seed_list}


def _edge(name, module, consumer_instance, dep, provider='engines'):
    return types.SimpleNamespace(
        name=name, module_name=module,
        consumer_instance_name=consumer_instance,
        depends_on_module=dep, provider_instance_name=provider,
        status='resolved', evidence_json='[]',
        topology_name='staging-a', notes='')


def _mgr(extra_edges=(), polari_modules=()):
    edges = _rows(SEED_MODULE_DEPENDENCY_EDGES)
    for e in extra_edges:
        edges[e.name] = e
    return types.SimpleNamespace(objectTables={
        'ModuleAssignment': _rows(SEED_MODULE_ASSIGNMENTS),
        'ModuleDependencyEdge': edges,
        'PolariModule': {getattr(m, 'name', ''): m
                         for m in polari_modules},
    })


def _module(report, name):
    for m in report['modules']:
        if m['name'] == name:
            return m
    return None


if __name__ == '__main__':
    print('== suite: classification vocabulary ==')
    check('out+in => hybrid', classify(2, 1) == 'hybrid')
    check('out only => consumer', classify(1, 0) == 'consumer')
    check('in only => provider', classify(0, 3) == 'provider')
    check('neither => independent', classify(0, 0) == 'independent')
    check('data_only overrides degree',
          classify(2, 2, data_only=True) == 'data-only')

    print('== suite: module graph over the seed ==')
    mgr = _mgr()
    report = module_graph(mgr, 'staging-a')
    check('module graph ok', report.get('ok'))
    multiscale = _module(report, 'materialsScience.multiscale')
    check('multiscale is a consumer',
          multiscale and multiscale['classification'] == 'consumer')
    check('multiscale dependsOn fem+dft',
          multiscale and multiscale['dependsOn'] == [
              'materialsScience.dft', 'materialsScience.fem'])
    fem = _module(report, 'materialsScience.fem')
    check('fem is a provider (reverse edge computed)',
          fem and fem['classification'] == 'provider'
          and fem['dependents'] == ['materialsScience.multiscale'])
    check('fem placement carried',
          fem and fem['placements'] == [
              {'instance': 'engines', 'state': 'enabled'}])
    scoring = _module(report, 'scoring')
    check('scoring (no edges) is independent',
          scoring and scoring['classification'] == 'independent')
    check('graph names cover assignments + edge endpoints',
          {'scoring', 'aquaponics', 'materialsScience.fem'}
          <= {m['name'] for m in report['modules']})

    print('== suite: transient/primary designation ==')
    # Seed: fem has ONE consumer — primary, never transient.
    solo = [e for e in report['edges']
            if e['dependsOnModule'] == 'materialsScience.fem']
    check('single-consumer dep is primary, not transient',
          len(solo) == 1 and solo[0]['isPrimary']
          and not solo[0]['isTransient'])

    # Add a second + third consumer of fem: exactly one primary,
    # N-1 transient, alphabetically-first consumer wins.
    mgr = _mgr(extra_edges=(
        _edge('waxprint@prf-a->materialsScience.fem',
              'waxprint', 'prf-a', 'materialsScience.fem'),
        _edge('aquaponics@prf-a->materialsScience.fem',
              'aquaponics', 'prf-a', 'materialsScience.fem'),
    ))
    result = designate_transients(mgr, 'staging-a')
    fem_edges = sorted(
        (e for e in mgr.objectTables['ModuleDependencyEdge'].values()
         if e.depends_on_module == 'materialsScience.fem'),
        key=lambda e: e.name)
    primaries = [e for e in fem_edges if e.is_primary]
    transients = [e for e in fem_edges if e.is_transient]
    check('shared dep: exactly one primary',
          len(primaries) == 1)
    check('shared dep: N-1 transient copies',
          len(transients) == len(fem_edges) - 1)
    check('alphabetically-first consumer is primary',
          primaries and primaries[0].module_name == 'aquaponics')
    check('designation reports its changes with reasons',
          result['changed'] and all(
              'reason' in c for c in result['changed']))

    # Stability: a still-valid primary survives recompute even when
    # an alphabetically-earlier consumer would win a fresh pass.
    for e in fem_edges:
        e.is_primary = (e.module_name == 'waxprint')
        e.is_transient = not e.is_primary
    designate_transients(mgr, 'staging-a')
    kept = [e for e in fem_edges if e.is_primary]
    check('existing primary kept when still a consumer',
          len(kept) == 1 and kept[0].module_name == 'waxprint')

    # Promotion: removing the primary's edge promotes the
    # alphabetically-first remaining consumer.
    del mgr.objectTables['ModuleDependencyEdge'][
        'waxprint@prf-a->materialsScience.fem']
    designate_transients(mgr, 'staging-a')
    remaining = sorted(
        (e for e in mgr.objectTables['ModuleDependencyEdge'].values()
         if e.depends_on_module == 'materialsScience.fem'),
        key=lambda e: e.name)
    check('removed primary => next consumer promoted',
          [e.module_name for e in remaining if e.is_primary]
          == ['aquaponics'])
    check('designation is idempotent (second pass changes nothing)',
          designate_transients(mgr, 'staging-a')['changed'] == [])

    print('== suite: data-only self-declaration ==')
    flagged = types.SimpleNamespace(
        name='scoring', data_only=True, tech_node_ref='')
    dotted = types.SimpleNamespace(
        name='materialsScience', data_only=True, tech_node_ref='')
    report = module_graph(
        _mgr(polari_modules=(flagged, dotted)), 'staging-a')
    check('PolariModule.data_only => data-only classification',
          _module(report, 'scoring')['classification'] == 'data-only')
    check('top-level flag covers dotted capabilities',
          _module(report, 'materialsScience.fem')[
              'classification'] == 'data-only')
    check('unflagged modules unaffected',
          _module(report, 'aquaponics')[
              'classification'] != 'data-only')

    print('== suite: dynamic move planning (tt-13) ==')
    from topology.topology_analysis import plan_move
    from topology.topology_seed import (
        SEED_INSTANCE_DEFINITIONS, SEED_NODE_MACHINES,
    )
    mgr = _mgr()
    mgr.objectTables['InstanceDefinition'] = _rows(
        SEED_INSTANCE_DEFINITIONS)
    mgr.objectTables['PolariNodeMachine'] = _rows(SEED_NODE_MACHINES)
    move = plan_move(mgr, 'staging-a', 'aquaponics',
                     to_instance='prf-b')
    check('container target => module-reassignment with ghosts '
          'noted', move.get('ok')
          and move['moveKind'] == 'module-reassignment'
          and move['fromInstances'] == ['prf-a']
          and 'TRANSIENT' in move['note'])
    move = plan_move(mgr, 'staging-a', 'materialsScience.fem',
                     to_machine='isle-core')
    check('device target on an engine => engine-relocation with '
          'constraint + human commands',
          move.get('ok') and move['moveKind'] == 'engine-relocation'
          and move['instance'] == 'engines'
          and move['placementConstraint']
          == 'node.labels.polari.machine == isle-core'
          and any('pol allocate engines isle-core' in c
                  for c in move['suggestedCommands']))
    move = plan_move(mgr, 'staging-a', 'aquaponics',
                     to_machine='isle-core')
    check('device target on a NON-engine module refused honestly',
          not move.get('ok') and 'name a container' in move['error'])
    check('both targets refused', not plan_move(
        mgr, 'staging-a', 'x', to_instance='a',
        to_machine='b').get('ok'))
    check('neither target refused', not plan_move(
        mgr, 'staging-a', 'x').get('ok'))
    check('unknown instance refused honestly', not plan_move(
        mgr, 'staging-a', 'aquaponics',
        to_instance='nope').get('ok'))
    # Transient ghosts are inert: resolve ignores them.
    from topology.topology_analysis import resolve_edges
    mgr.objectTables['ModuleAssignment'][
        'materialsScience.fem@engines'].state = 'transient'
    resolve_edges(mgr, 'staging-a')
    fem_edge = [e for e in mgr.objectTables[
        'ModuleDependencyEdge'].values()
        if e.depends_on_module == 'materialsScience.fem'][0]
    check('transient ghost excluded from resolution '
          '(edge unresolves)', fem_edge.status == 'unresolved')

    print('== suite: placement coherence (tt-14) ==')
    from topology.topology_analysis import (
        instance_app_kind, instance_storage, is_real_machine,
        placement_check,
    )

    def _ns(**fields):
        return types.SimpleNamespace(**fields)
    prf = _ns(name='prf-a', kind='prf', db_backend='sqlite')
    worker = _ns(name='engines', kind='worker', db_backend='')
    psc = _ns(name='psc-a', kind='psc', db_backend='')
    infra = _ns(name='shared-infra', kind='infra', db_backend='')
    auth = _ns(name='kc', kind='auth', db_backend='')
    check('app kinds: polari / integrated-app / infrastructure / '
          'auth',
          instance_app_kind(prf) == 'polari'
          and instance_app_kind(worker) == 'polari'
          and instance_app_kind(psc) == 'integrated-app'
          and instance_app_kind(infra) == 'infrastructure'
          and instance_app_kind(auth) == 'auth')
    check('modules may land on prf AND worker (both are Polari)',
          placement_check('aquaponics', prf)[0]
          and placement_check('aquaponics', worker)[0])
    ok, why = placement_check('aquaponics', psc)
    check('psc refused — non-adaptive integrated app',
          not ok and 'not a Polari instance' in why)
    check('infra refused', not placement_check(
        'aquaponics', infra)[0])
    check('auth container refused',
          'auth container' in placement_check('scoring', auth)[1])
    ok, why = placement_check('materialsScience.fem', prf)
    check('engine capability refused on a plain prf instance',
          not ok and 'engine capability' in why)
    check('engine capability allowed on a worker/engine instance',
          placement_check('materialsScience.fem', worker)[0])
    check('named sqlite storage carries ownership',
          instance_storage(prf)['name'] == 'sqlite-prf-a'
          and not instance_storage(prf)['shared'])
    combo = _ns(name='prf-b', kind='prf', db_backend='combo')
    check('combo backend reads as the shared mariadb',
          instance_storage(combo)['shared'])
    check('non-polari instances hold no object storage',
          instance_storage(psc) is None)
    check('sim machine rows are not real deploy targets',
          not is_real_machine(_ns(name='sim-polarinodemachine',
                                  source='sim-599'))
          and is_real_machine(_ns(name='isle-core',
                                  source='nodes.yml')))
    check('move to psc refused end-to-end', not plan_move(
        _ns(objectTables={
            'InstanceDefinition': {'psc-a': psc},
            'ModuleAssignment': {},
            'PolariNodeMachine': {}}),
        'staging-a', 'scoring', to_instance='psc-a').get('ok'))

    print('== suite: boundary graph reverse edges ==')
    from moduleService.module_dependency_tracker import boundary_graph
    graph = boundary_graph()
    nodes = {n['name']: n for n in graph['boundaries']}
    check('every boundary carries boundaryDependents',
          all('boundaryDependents' in n
              for n in graph['boundaries']))
    inverted_ok = all(
        name in nodes[imported]['boundaryDependents']
        for name, node in nodes.items()
        for imported in node['boundaryImports'])
    check('dependents is the exact inversion of imports',
          inverted_ok)
    check('a known reverse edge exists '
          '(something imports polariDataTyping)',
          nodes.get('polariDataTyping', {}).get('boundaryDependents'))

    print('== suite: mod-env-1 rows-derived POLARI_MODULES ==')
    from topology.topology_analysis import modules_env_for_instance

    def _amgr(assignments):
        return types.SimpleNamespace(objectTables={
            'ModuleAssignment': {a.name: a for a in assignments},
            'TopologyDefinition': {'staging-a': types.SimpleNamespace(
                name='staging-a', is_active=True)},
        })

    def _assign(module, instance='prf-a', state='enabled'):
        return types.SimpleNamespace(
            name=f'{module}@{instance}', module_name=module,
            instance_name=instance, state=state,
            topology_name='staging-a')

    env = modules_env_for_instance(
        _amgr([_assign('scoring'), _assign('composition'),
               _assign('materialsScience.fem'),
               _assign('waxprint', state='disabled'),
               _assign('gears', instance='other')]), 'prf-a')
    check('rows -> env: enabled rows only, this instance only, '
          'dotted names collapse to their package',
          env.get('ok') and env['assigned']
          == ['composition', 'materialsScience', 'scoring'])
    check('requires closure added, each addition NAMING who '
          'pulled it in',
          'mathshapes' in env['env'].split(',')
          and 'composition' in env['addedByRequires'].get(
              'mathshapes', []),
          extra=str(env.get('addedByRequires')))
    check('env is the sorted comma list the deploy consumes',
          env['env'] == ','.join(sorted(env['env'].split(',')))
          and env['count'] == len(env['env'].split(',')))
    empty = modules_env_for_instance(_amgr([]), 'prf-a')
    check('ZERO rows REFUSES (empty env would boot monolithic), '
          'naming the assign knob',
          not empty.get('ok')
          and 'monolithic' in empty.get('refusal', '')
          and 'pol topology assign' in str(empty.get('suggestion')))

    failed = [label for label, ok in _results if not ok]
    print(f'\n{len(_results) - len(failed)}/{len(_results)} checks '
          f'passed' + (f'; FAILED: {failed}' if failed else ''))
    raise SystemExit(1 if failed else 0)
