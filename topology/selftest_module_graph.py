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

    failed = [label for label, ok in _results if not ok]
    print(f'\n{len(_results) - len(failed)}/{len(_results)} checks '
          f'passed' + (f'; FAILED: {failed}' if failed else ''))
    raise SystemExit(1 if failed else 0)
