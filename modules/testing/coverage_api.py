"""
@module testing.coverage_api

/api/testing/coverage           the plan (live: manifests in the image + rows)
/api/testing/coverage/apps      the hierarchy, largest first
/api/testing/coverage/modules   per-module verdicts
/api/testing/coverage/nodes     the nodes a distributed test could use
POST /api/testing/coverage/benchmark   ingest an AppBenchmark JSON (from
                                       `pol modules testplan benchmark`) → row
POST /api/testing/coverage/recompute   write AppHierarchyNode / ModuleCoverage /
                                       TestCoveragePlan rows (object coherence)
"""
import json
import time

import falcon

from objectTreeDecorators import treeObject, treeObjectInit


class CoverageAPI(treeObject):
    @treeObjectInit
    def __init__(self, polServer=None, manager=None):
        self.polServer = polServer
        self.manager = manager
        if polServer is not None and getattr(polServer, 'falconServer', None) is not None:
            add = polServer.falconServer.add_route
            add('/api/testing/coverage', self, suffix='plan')
            add('/api/testing/coverage/apps', self, suffix='apps')
            add('/api/testing/coverage/modules', self, suffix='modules')
            add('/api/testing/coverage/nodes', self, suffix='nodes')
            add('/api/testing/coverage/benchmark', self, suffix='benchmark')
            add('/api/testing/coverage/recompute', self, suffix='recompute')

    def _rows(self, class_name):
        return list(((self.manager.objectTables or {}).get(class_name, {}) or {}).values())

    def _budget(self):
        for r in self._rows('StandardComputerBudget'):
            if getattr(r, 'name', '') == 'standard':
                return {'name': r.name, 'cores': r.cores, 'vcpus': r.vcpus, 'ram_mb': r.ram_mb,
                        'disk_mb': r.disk_mb, 'boot_timeout_s': r.boot_timeout_s}
        from testing.custom.app_hierarchy import DEFAULT_BUDGET
        return dict(DEFAULT_BUDGET)

    def _nodes(self):
        out = []
        for m in self._rows('PolariNodeMachine'):
            out.append({'name': getattr(m, 'name', ''), 'kind': 'topology', 'logical_cpus': getattr(m, 'logical_cpus', 0),
                        'total_ram_mb': getattr(m, 'total_ram_mb', 0), 'free_disk_mb': getattr(m, 'free_disk_mb', 0),
                        'swarm_role': getattr(m, 'swarm_role', 'none')})
        return out

    def _compute(self):
        from moduleService import manifests as M
        from testing.custom import app_hierarchy as H
        graph = H.module_graph(M.all_manifests())
        seeds = [{'name': getattr(a, 'name', ''), 'modules': json.loads(getattr(a, 'modules_json', '[]') or '[]')}
                 for a in self._rows('PolariAppDefinition')]
        instances = {}
        for r in self._rows('ModuleAssignment'):
            instances.setdefault(getattr(r, 'instance', '') or getattr(r, 'instance_name', ''), set()).add(getattr(r, 'module', '') or getattr(r, 'module_name', ''))
        instances = {k: v for k, v in instances.items() if k}
        benchmarks = {getattr(b, 'app', ''): {'ok': b.ok, 'peak_rss_mb': b.peak_rss_mb, 'boot_seconds': b.boot_seconds,
                      'image_mb': b.image_mb, 'code_mb': b.code_mb, 'classes': b.classes, 'oom_killed': b.oom_killed}
                      for b in self._rows('AppBenchmark')}
        profiles = {getattr(p, 'subject_name', ''): {'min_ram_mb': p.min_ram_mb, 'min_disk_mb': p.min_disk_mb, 'min_threads': p.min_threads}
                    for p in self._rows('ModuleResourceProfile')}
        apps = H.app_catalog(seeds, graph, instances)
        nodes = self._nodes()
        host = next((n for n in nodes if n.get('swarm_role') == 'manager'), None)
        return H.plan(apps, graph, self._budget(), benchmarks, profiles, nodes, host)

    def on_get_plan(self, request, response):
        p = self._compute()
        response.media = {'ok': True, 'summary': {'budget': p['budget'], 'chosenApps': p['chosen'], 'counts': p['counts'],
                          'totalModules': p['total_modules'], 'uncovered': p['uncovered'], 'largest': p['largest'][:6]}}

    def on_get_apps(self, request, response):
        p = self._compute()
        response.media = {'ok': True, 'apps': [{'name': a['name'], 'kind': a['kind'], 'direct': len(a['modules']), 'closure': len(a['closure']),
                          'ramMb': a['estimate']['ram_mb'], 'bootS': a['estimate']['boot_s'], 'fidelity': a['estimate']['fidelity'],
                          'fits': a['fits'], 'chosen': a['chosen'], 'unknown': a['unknown']}
                          for a in sorted(p['apps'], key=lambda a: -len(a['closure'])) if a['kind'] != 'module' or a['chosen']]}

    def on_get_modules(self, request, response):
        p = self._compute()
        response.media = {'ok': True, 'modules': [{'module': m, 'verdict': r['verdict'], 'bestApp': r['best_app'], 'reason': r['reason'],
                          'apps': r['apps'], 'nodes': r['nodes']} for m, r in p['modules'].items()]}

    def on_get_nodes(self, request, response):
        response.media = {'ok': True, 'nodes': self._nodes(), 'budget': self._budget()}

    def on_post_benchmark(self, request, response):
        from testing.coverage_basis import AppBenchmark
        try:
            body = json.loads(request.bounded_stream.read() or b'{}')
        except Exception as e:  # noqa: BLE001
            response.status = falcon.HTTP_400
            response.media = {'ok': False, 'error': 'bad JSON: %s' % e}
            return
        if not body.get('app'):
            response.status = falcon.HTTP_400
            response.media = {'ok': False, 'error': 'app required'}
            return
        row = None
        for r in self._rows('AppBenchmark'):
            if getattr(r, 'app', '') == body['app']:
                row = r
                break
        fields = {'app': body['app'], 'modules_json': json.dumps(body.get('modules', [])), 'host': body.get('host', ''),
                  'budget': body.get('budget', 'standard'), 'cpu_limit': float(body.get('cpu_limit') or 0), 'mem_limit_mb': float(body.get('mem_limit_mb') or 0),
                  'boot_seconds': float(body.get('boot_seconds') or 0), 'peak_rss_mb': float(body.get('peak_rss_mb') or 0),
                  'classes': int(body.get('classes') or 0), 'image_mb': float(body.get('image_mb') or 0), 'code_mb': float(body.get('code_mb') or 0),
                  'ok': bool(body.get('ok')), 'oom_killed': bool(body.get('oom_killed')), 'health_http': int(body.get('health_http') or 0),
                  'measured_at': body.get('measured_at', ''), 'notes': body.get('notes', '')}
        if row is None:
            row = AppBenchmark(manager=self.manager, name='benchmark:' + body['app'], **fields)
        else:
            for k, v in fields.items():
                setattr(row, k, v)
        try:
            self.manager.db.saveInstanceInDB(row)
        except Exception:  # noqa: BLE001
            pass
        response.status = falcon.HTTP_201
        response.media = {'ok': True, 'benchmark': body['app'], 'fits': None}

    def on_post_recompute(self, request, response):
        from testing.coverage_basis import AppHierarchyNode, ModuleCoverage, TestCoveragePlan
        p = self._compute()
        stamp = time.strftime('%Y-%m-%dT%H:%M:%S')
        written = 0
        existing = {getattr(r, 'name', ''): r for r in self._rows('AppHierarchyNode')}
        for a in p['apps']:
            if a['kind'] == 'module' and not a['chosen']:
                continue
            e = a['estimate']
            fields = {'kind': a['kind'], 'modules_json': json.dumps(a['modules']), 'closure_json': json.dumps(a['closure']),
                      'module_count': len(a['modules']), 'closure_count': len(a['closure']), 'unknown_modules_json': json.dumps(a['unknown']),
                      'est_classes': e['classes'], 'est_ram_mb': e['ram_mb'], 'est_disk_mb': e['disk_mb'], 'est_boot_s': e['boot_s'],
                      'est_threads': e['threads'], 'engines_json': json.dumps(e['engines']), 'fidelity': e['fidelity'],
                      'fits_standard': a['fits'], 'fit_reasons_json': json.dumps(a['fit_reasons']), 'chosen': a['chosen'], 'computed_at': stamp}
            row = existing.get(a['name']) or AppHierarchyNode(manager=self.manager, name=a['name'])
            for k, v in fields.items():
                setattr(row, k, v)
            try:
                self.manager.db.saveInstanceInDB(row); written += 1
            except Exception:  # noqa: BLE001
                pass
        existing = {getattr(r, 'name', ''): r for r in self._rows('ModuleCoverage')}
        for m, r in p['modules'].items():
            row = existing.get('coverage:' + m) or ModuleCoverage(manager=self.manager, name='coverage:' + m)
            for k, v in {'module': m, 'apps_json': json.dumps(r['apps']), 'upstream_apps_json': json.dumps(r['upstream']),
                         'best_app': r['best_app'], 'verdict': r['verdict'], 'reason': r['reason'], 'nodes_json': json.dumps(r['nodes']),
                         'computed_at': stamp}.items():
                setattr(row, k, v)
            try:
                self.manager.db.saveInstanceInDB(row); written += 1
            except Exception:  # noqa: BLE001
                pass
        plan_row = next((r for r in self._rows('TestCoveragePlan') if getattr(r, 'name', '') == 'current'), None) \
            or TestCoveragePlan(manager=self.manager, name='current')
        for k, v in {'budget': p['budget']['name'], 'chosen_apps_json': json.dumps(p['chosen']), 'total_modules': p['total_modules'],
                     'covered_standard': p['counts']['covered-standard'], 'covered_distributed': p['counts']['covered-distributed'],
                     'covered_large_host': p['counts']['covered-large-host'], 'uncovered': p['counts']['uncovered'],
                     'uncovered_json': json.dumps(p['uncovered']), 'nodes_json': json.dumps([n['name'] for n in p['nodes']]),
                     'host_json': json.dumps(p['host'] or {}), 'computed_at': stamp}.items():
            setattr(plan_row, k, v)
        try:
            self.manager.db.saveInstanceInDB(plan_row); written += 1
        except Exception:  # noqa: BLE001
            pass
        response.media = {'ok': True, 'rowsWritten': written, 'counts': p['counts'], 'chosen': p['chosen']}
