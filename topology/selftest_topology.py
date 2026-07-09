"""
Selftest for the topology module (top-1).

Run from polari-framework/:  python3 -m topology.selftest_topology

Stdlib-only: builds a fake manager from the real SEED_* lists with
SimpleNamespace rows — no DB, no falcon, no treeObject machinery.
Covers: seed coherence, validation findings (evidence + knob +
action on every failure), deterministic edge resolution, drift
reporting, and the portable-package round trip
export(merge(export(X))) == export(X).
"""

import copy
import json
import types

from topology.topology_analysis import (
    active_topology_name, drift_report, graph_payload, resolve_edges,
    validate_topology,
)
from topology.topology_io import (
    export_topology, merge_topology_doc, package_equal,
)
from topology.topology_seed import (
    SEED_INSTANCE_DEFINITIONS, SEED_MODULE_ASSIGNMENTS,
    SEED_MODULE_DEPENDENCY_EDGES, SEED_NODE_MACHINES,
    SEED_ORCHESTRATION_TARGETS, SEED_SERVICE_CONNECTIONS,
    SEED_TOPOLOGY_DEFINITIONS,
)

_results = []


def check(label, cond, extra=''):
    _results.append((label, bool(cond)))
    print(f'{"PASS" if cond else "FAIL"}: {label}'
          + (f' — {extra}' if extra and not cond else ''))


def _rows(seed_list):
    return {s['name']: types.SimpleNamespace(**copy.deepcopy(s))
            for s in seed_list}


def _mgr():
    return types.SimpleNamespace(objectTables={
        'PolariNodeMachine': _rows(SEED_NODE_MACHINES),
        'OrchestrationTarget': _rows(SEED_ORCHESTRATION_TARGETS),
        'TopologyDefinition': _rows(SEED_TOPOLOGY_DEFINITIONS),
        'InstanceDefinition': _rows(SEED_INSTANCE_DEFINITIONS),
        'ModuleAssignment': _rows(SEED_MODULE_ASSIGNMENTS),
        'ModuleDependencyEdge': _rows(SEED_MODULE_DEPENDENCY_EDGES),
        'ServiceConnection': _rows(SEED_SERVICE_CONNECTIONS),
        'TopologyObservation': {},
    })


def _observation(node, services, stamp='2026-07-09T00:00:00+00:00'):
    return types.SimpleNamespace(
        name=f'{node}@{stamp}', topology_name='staging-a',
        node_name=node, observed_at=stamp, stacks_json='[]',
        services_json=json.dumps(services), modules_json='[]',
        source='selftest')


#: What the staging-a host ACTUALLY runs (real container names +
#: compose/swarm service labels from `docker ps` 2026-07-09) — the
#: aliased names (backend-b, dask-worker-a, msci-engines) exercise
#: the SERVICE_LABEL_ALIASES matching; plain-string entries exercise
#: the substring fallback.
FULL_STAGING_SERVICES = [
    {'name': 'pol-mariadb', 'service': 'pol-mariadb'},
    {'name': 'pol-keycloak', 'service': 'pol-keycloak'},
    {'name': 'pol-file-store', 'service': 'pol-file-store'},
    {'name': 'pol-proxy', 'service': 'pol-proxy'},
    {'name': 'psc-redis', 'service': 'psc-redis'},
    {'name': 'psc-backend', 'service': 'psc-backend'},
    {'name': 'psc-frontend', 'service': 'psc-frontend'},
    'prf-backend', 'prf-frontend',
    {'name': 'prf-b-backend', 'service': 'backend-b'},
    {'name': 'prf-b-frontend', 'service': 'frontend-b'},
    {'name': 'prf-b-keydb', 'service': 'keydb-b'},
    {'name': 'prf-dask-scheduler', 'service': 'dask-scheduler'},
    {'name': 'prf-a-dask-worker', 'service': 'dask-worker-a'},
    {'name': 'polari-engines_msci-engines.1.2mfrjud',
     'service': 'msci-engines'},
]


if __name__ == '__main__':
    print('== suite: seed coherence ==')
    mgr = _mgr()
    check('active topology is staging-a',
          active_topology_name(mgr) == 'staging-a')
    report = validate_topology(mgr, 'staging-a')
    check('seed topology validates ok', report.get('ok'))
    check('seed topology has zero error findings',
          report.get('errorCount') == 0,
          json.dumps(report.get('findings')))
    check('seed topology has zero warn findings',
          report.get('warnCount') == 0,
          json.dumps(report.get('findings')))
    check('unknown topology refused honestly',
          not validate_topology(mgr, 'nope').get('ok'))

    print('== suite: graph payload ==')
    graph = graph_payload(mgr, 'staging-a')
    check('graph ok', graph.get('ok'))
    check('graph carries 6 instances',
          len(graph.get('instances', [])) == 6)
    check('graph carries 3 machines',
          len(graph.get('machines', [])) == 3)
    check('graph carries 8 assignments',
          len(graph.get('assignments', [])) == 8)
    check('graph edges resolved to engines',
          all(e['providerInstanceName'] == 'engines'
              and e['status'] == 'resolved'
              for e in graph.get('edges', [])))
    check('graph carries 12 typed connections',
          len(graph.get('connections', [])) == 12)
    check('graph decodes service kinds',
          'prf-backend' in graph['instances'][0]['serviceKinds']
          or any('prf-backend' in i['serviceKinds']
                 for i in graph['instances']))

    print('== suite: validation findings (evidence + knob) ==')
    bad = _mgr()
    bad.objectTables['InstanceDefinition']['ghost-pin'] = (
        types.SimpleNamespace(
            name='ghost-pin', kind='prf',
            service_kinds_json='["prf-backend"]', replicas=1,
            env_tier='staging', machine_name='ghost',
            placement_constraint='', db_backend='sqlite',
            image_tag='staging', orchestration_target='compose',
            topology_name='staging-a', notes=''))
    report = validate_topology(bad, 'staging-a')
    ghost = [f for f in report['findings']
             if f['check'] == 'unknown-machine']
    check('unknown machine caught', len(ghost) == 1)
    check('finding carries evidence + knob + action',
          ghost and ghost[0]['evidence'] and ghost[0]['knob']
          and ghost[0]['action'])

    bad = _mgr()
    inst = bad.objectTables['InstanceDefinition']['engines']
    inst.machine_name = 'lightweight'  # not in the swarm yet
    report = validate_topology(bad, 'staging-a')
    swarm = [f for f in report['findings']
             if f['check'] == 'machine-not-in-swarm']
    check('swarm placement onto unjoined machine caught',
          len(swarm) == 1)
    check('swarm finding names pol swarm join',
          swarm and 'pol swarm join' in swarm[0]['action'])

    bad = _mgr()
    inst = bad.objectTables['InstanceDefinition']['engines']
    inst.orchestration_target = 'isle'
    report = validate_topology(bad, 'staging-a')
    check('unavailable target (isle) refused with finding',
          any(f['check'] == 'target-unavailable'
              for f in report['findings']))

    bad = _mgr()
    conn = bad.objectTables['ServiceConnection'][
        'prf-backend->prf-mariadb:db-credentials']
    conn.interconnect_key = 'magic-wire'
    report = validate_topology(bad, 'staging-a')
    check('unknown interconnect key caught',
          any(f['check'] == 'unknown-interconnect'
              for f in report['findings']))

    bad = _mgr()
    inst = bad.objectTables['InstanceDefinition']['prf-a']
    inst.db_backend = 'oracle'
    report = validate_topology(bad, 'staging-a')
    check('unknown db backend caught',
          any(f['check'] == 'unknown-db-backend'
              for f in report['findings']))

    print('== suite: edge resolution ==')
    mgr = _mgr()
    fem = mgr.objectTables['ModuleAssignment'][
        'materialsScience.fem@engines']
    fem.state = 'disabled'
    result = resolve_edges(mgr, 'staging-a')
    fem_edge = mgr.objectTables['ModuleDependencyEdge'][
        'materialsScience.multiscale@prf-a->materialsScience.fem']
    check('disabling the only fem assignment unresolves the edge',
          fem_edge.status == 'unresolved'
          and fem_edge.provider_instance_name == '')
    evidence = json.loads(fem_edge.evidence_json)
    check('unresolved evidence names the pol allocate knob',
          evidence and 'pol allocate' in evidence[0].get('action', ''))
    report = validate_topology(mgr, 'staging-a')
    check('validator surfaces the providerless edge',
          any(f['check'] == 'edge-without-provider'
              for f in report['findings']))
    # Re-provide fem elsewhere — resolution finds the new provider.
    mgr.objectTables['ModuleAssignment'][
        'materialsScience.fem@prf-dask'] = types.SimpleNamespace(
        name='materialsScience.fem@prf-dask',
        module_name='materialsScience.fem',
        instance_name='prf-dask', state='enabled',
        topology_name='staging-a', notes='')
    resolve_edges(mgr, 'staging-a')
    check('edge re-resolves to the new provider',
          fem_edge.status == 'resolved'
          and fem_edge.provider_instance_name == 'prf-dask')
    # Determinism: two candidates -> keeps current, else alphabetical.
    fem.state = 'enabled'
    resolve_edges(mgr, 'staging-a')
    check('existing provider kept when still valid',
          fem_edge.provider_instance_name == 'prf-dask')
    fem_edge.provider_instance_name = ''
    resolve_edges(mgr, 'staging-a')
    check('alphabetical pick among candidates',
          fem_edge.provider_instance_name == 'engines')
    dft_edge = mgr.objectTables['ModuleDependencyEdge'][
        'materialsScience.multiscale@prf-a->materialsScience.dft']
    check('untouched dft edge stays resolved',
          dft_edge.status == 'resolved'
          and dft_edge.provider_instance_name == 'engines')

    print('== suite: drift (desired vs observed) ==')
    mgr = _mgr()
    report = drift_report(mgr, 'staging-a')
    check('no observations => every instance unobserved',
          report['inDrift'] and all(
              r['kind'] == 'unobserved' for r in report['rows'])
          and len(report['rows']) == 6)
    check('unobserved rows suggest pol topology report',
          all(r['suggestedCommand'] == 'pol topology report'
              for r in report['rows']))
    mgr.objectTables['TopologyObservation']['full'] = _observation(
        'staging-a', FULL_STAGING_SERVICES)
    report = drift_report(mgr, 'staging-a')
    check('full observation => no drift',
          not report['inDrift'], json.dumps(report['rows']))
    partial = [s for s in FULL_STAGING_SERVICES
               if 'msci-engines' not in json.dumps(s)]
    partial.append('rogue-miner-1')
    mgr.objectTables['TopologyObservation']['later'] = _observation(
        'staging-a', partial, stamp='2026-07-09T01:00:00+00:00')
    report = drift_report(mgr, 'staging-a')
    missing = [r for r in report['rows']
               if r['kind'] == 'missing-service']
    unexpected = [r for r in report['rows']
                  if r['kind'] == 'unexpected-service']
    check('latest observation wins (missing engines caught)',
          len(missing) == 1
          and missing[0]['serviceKind'] == 'prf-msci-engines')
    check('missing-service row suggests apply --plan',
          missing and 'apply --plan' in missing[0]['suggestedCommand'])
    check('unexpected service surfaced, decision left to human',
          len(unexpected) == 1
          and unexpected[0]['subject'] == 'rogue-miner-1')

    print('== suite: reallocation suggestions (top-8) ==')
    mgr = _mgr()
    fem_edge = mgr.objectTables['ModuleDependencyEdge'][
        'materialsScience.multiscale@prf-a->materialsScience.fem']
    fem_edge.status = 'degraded'
    fem_edge.evidence_json = json.dumps(
        [{'routing': 'all candidates failed',
          'tried': [{'instance': 'engines',
                     'why': 'http://x:9500 unreachable'}]}])
    mgr.objectTables['TopologyObservation']['full'] = _observation(
        'staging-a', FULL_STAGING_SERVICES)
    report = drift_report(mgr, 'staging-a')
    realloc = [r for r in report['rows']
               if r['kind'] == 'reallocation-suggested']
    check('degraded edge yields exactly one suggestion',
          len(realloc) == 1)
    check('no alternative => suggests apply --plan + names allocate',
          realloc and 'apply --plan' in realloc[0]['suggestedCommand']
          and 'pol allocate' in realloc[0]['evidence'])
    mgr.objectTables['ModuleAssignment'][
        'materialsScience.fem@prf-dask'] = types.SimpleNamespace(
        name='materialsScience.fem@prf-dask',
        module_name='materialsScience.fem',
        instance_name='prf-dask', state='enabled',
        topology_name='staging-a', notes='')
    report = drift_report(mgr, 'staging-a')
    realloc = [r for r in report['rows']
               if r['kind'] == 'reallocation-suggested']
    check('live alternative => one-click pol allocate suggestion',
          realloc and realloc[0]['suggestedCommand']
          == 'pol allocate materialsScience.fem prf-dask')
    check('suggestion carries the routing evidence',
          realloc and 'unreachable' in realloc[0]['evidence'])
    fem_edge.status = 'resolved'
    report = drift_report(mgr, 'staging-a')
    check('resolved edges suggest nothing',
          not [r for r in report['rows']
               if r['kind'] == 'reallocation-suggested'])

    print('== suite: portable package round trip ==')
    mgr = _mgr()
    exported = export_topology(mgr, 'staging-a')
    check('export ok', exported.get('ok'))
    doc = exported['document']
    check('package is credential-free (no secret-shaped keys)',
          'pass' not in json.dumps(doc).lower()
          .replace('mariadb.env', '').replace('_pass', '')
          and 'secret' not in json.dumps(doc).lower()
          .replace('keycloak-client-secrets', '')
          .replace('client-secrets', ''))
    check('package only carries machines the topology uses',
          [m['name'] for m in doc['machines']] == ['staging-a'])
    empty = types.SimpleNamespace(objectTables={
        k: {} for k in mgr.objectTables})
    plan = merge_topology_doc(empty, doc)
    check('merge into empty manager creates everything',
          plan.get('ok') and len(plan['creates']) == (
              1 + 1 + 6 + 8 + 2 + 12) and not plan['skips'])
    for class_name, row in plan['creates']:
        empty.objectTables[class_name][row['name']] = (
            types.SimpleNamespace(**row))
    re_exported = export_topology(empty, 'staging-a')
    check('round trip: export(merge(export(X))) == export(X)',
          re_exported.get('ok') and package_equal(
              doc, re_exported['document']))
    plan = merge_topology_doc(mgr, doc)
    check('merge into seeded manager skips everything (idempotent)',
          plan.get('ok') and not plan['creates']
          and len(plan['skips']) == 30)
    check('non-package document refused honestly',
          not merge_topology_doc(mgr, {'kind': 'nope'}).get('ok'))
    check('wrong schema_version refused honestly',
          not merge_topology_doc(mgr, {
              'kind': 'polari-topology-package',
              'schema_version': '99'}).get('ok'))

    print('== suite: provider routing (top-7) ==')
    from topology import provider_registry as preg
    import os as _os
    _os.environ['LOCAL_IP'] = '192.168.0.210'
    mgr = _mgr()
    preg.set_manager(mgr)
    alive = lambda url: True
    dead = lambda url: False
    resolved = preg.resolve_provider('materialsScience.fem',
                                     probe=alive)
    check('routing resolves fem to the engines instance',
          resolved.get('ok')
          and resolved['instance'] == 'engines'
          and resolved['url'] == 'http://192.168.0.210:9500')
    fem_edge = mgr.objectTables['ModuleDependencyEdge'][
        'materialsScience.multiscale@prf-a->materialsScience.fem']
    check('live pick stamps routing evidence on the edge',
          fem_edge.status == 'resolved'
          and 'live' in fem_edge.evidence_json)
    preg._PROBE_CACHE.clear()
    refused = preg.resolve_provider('materialsScience.fem',
                                    probe=dead)
    check('all-dead providers refuse with knob + action',
          not refused.get('ok')
          and 'pol ' in refused['suggestion']['action']
          and refused['suggestion']['knob'])
    check('dead providers mark the edge degraded',
          fem_edge.status == 'degraded'
          and 'failed' in fem_edge.evidence_json)
    check('unassigned module refuses naming pol allocate',
          'pol allocate' in preg.resolve_provider(
              'materialsScience.md', probe=alive
          )['suggestion']['action'])
    preg.set_manager(None)
    check('uninitialized registry refuses honestly',
          not preg.resolve_provider('materialsScience.fem',
                                    probe=alive).get('ok'))
    # the engines_url_for ladder: env knob wins over topology
    preg.set_manager(mgr)
    preg._PROBE_CACHE.clear()
    from materialsScience.engines.remote import engines_url_for
    _os.environ['MSCI_ENGINES_URL'] = 'http://knob:9999'
    check('explicit env knob beats topology routing',
          engines_url_for('/dft/x') == 'http://knob:9999')
    del _os.environ['MSCI_ENGINES_URL']

    failed = sum(1 for _, ok in _results if not ok)
    print(f'\n{len(_results) - failed}/{len(_results)} checks passed')
    raise SystemExit(1 if failed else 0)
