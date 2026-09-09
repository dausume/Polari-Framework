"""
@module suiteapps.suiteapps_api

GET /api/suiteapps                     suites with parts/contracts counts and the placement summary
GET /api/suiteapps/{name}              one suite: parts, contracts, placement per part
POST /api/suiteapps/{name}/place       recompute + write SuitePlacement rows
"""
import json
import time

import falcon

from objectTreeDecorators import treeObject, treeObjectInit


class SuiteAppsAPI(treeObject):
    @treeObjectInit
    def __init__(self, polServer=None, manager=None):
        self.polServer = polServer
        self.manager = manager
        if polServer is not None and getattr(polServer, 'falconServer', None) is not None:
            add = polServer.falconServer.add_route
            add('/api/suiteapps', self, suffix='list')
            add('/api/suiteapps/{name}', self, suffix='one')
            add('/api/suiteapps/{name}/place', self, suffix='place')

    def _rows(self, class_name):
        return list(((self.manager.objectTables or {}).get(class_name, {}) or {}).values())

    def _devices(self):
        snaps = {s.device_name: s for s in self._rows('HardwareMapSnapshot')}
        cands = {}
        for c in self._rows('PassthroughCandidate'):
            if c.mappable:
                for app in json.loads(c.satisfies_json or '[]'):
                    cands.setdefault(c.device_name, set()).add(app)
        isles = {d.machine_name or d.name: d for d in self._rows('IsleDevice')}
        machines = {m.name: m for m in self._rows('PolariNodeMachine')}
        names = set(snaps) | set(isles) | set(machines)
        out = []
        for n in sorted(names):
            m = machines.get(n); i = isles.get(n); s = snaps.get(n)
            out.append({'name': n, 'is_core': bool(i and getattr(i, 'agent_mode', '') == 'core') or bool(m and getattr(m, 'swarm_role', '') == 'manager'),
                        'hardware_tier_ready': bool(s and s.hardware_tier_ready), 'ports_satisfy': sorted(cands.get(n, [])),
                        'logical_cpus': getattr(m, 'logical_cpus', 0) if m else 0, 'total_ram_mb': getattr(m, 'total_ram_mb', 0) if m else 0, 'load': 0})
        return out

    def _suite(self, name):
        s = next((x for x in self._rows('SuiteAppDefinition') if x.name == name), None)
        if s is None:
            return None
        parts = sorted([p for p in self._rows('SuitePart') if p.suite == name], key=lambda p: p.order)
        contracts = [c for c in self._rows('SuiteContract') if c.suite == name]
        return s, parts, contracts

    def _compute(self, name):
        from suiteapps.custom.placement import place
        found = self._suite(name)
        if not found:
            return None
        s, parts, contracts = found
        pd = [{'name': p.name, 'app': p.app, 'kind': p.kind, 'placement': p.placement, 'same_as': p.same_as, 'node': p.node, 'required': p.required, 'order': p.order} for p in parts]
        plan = place(pd, self._devices())
        return s, parts, contracts, plan

    def on_get_list(self, request, response):
        out = []
        for s in self._rows('SuiteAppDefinition'):
            _, parts, contracts, plan = self._compute(s.name)
            out.append({'suite': s.name, 'title': s.title, 'purpose': s.purpose, 'parts': len(parts), 'contracts': len(contracts), 'placement': plan['summary']})
        response.media = {'ok': True, 'suites': out}

    def on_get_one(self, request, response, name):
        c = self._compute(name)
        if not c:
            response.status = falcon.HTTP_404
            response.media = {'ok': False, 'error': 'no suite %r' % name}
            return
        s, parts, contracts, plan = c
        pl = {p['part']: p for p in plan['placements']}
        response.media = {'ok': True, 'suite': s.name, 'title': s.title, 'purpose': s.purpose, 'frontPage': s.front_page,
                          'parts': [{'part': p.name, 'app': p.app, 'kind': p.kind, 'role': p.role, 'placement': p.placement, 'required': p.required,
                                     'device': pl[p.name]['device'], 'verdict': pl[p.name]['verdict'], 'reason': pl[p.name]['reason']} for p in parts],
                          'contracts': [{'object': k.object_class, 'owner': k.owner_module, 'from': k.producer, 'to': k.consumer, 'description': k.description} for k in contracts],
                          'summary': plan['summary']}

    def on_post_place(self, request, response, name):
        from suiteapps.suiteapps_basis import SuitePlacement
        c = self._compute(name)
        if not c:
            response.status = falcon.HTTP_404
            response.media = {'ok': False, 'error': 'no suite %r' % name}
            return
        s, parts, contracts, plan = c
        existing = {r.name: r for r in self._rows('SuitePlacement') if r.suite == name}
        n = 0
        for p in plan['placements']:
            row = existing.get('%s:%s' % (name, p['part'])) or SuitePlacement(manager=self.manager, name='%s:%s' % (name, p['part']), suite=name)
            for k in ('part', 'device', 'verdict', 'reason', 'computed_at'):
                setattr(row, k, p[k])
            try:
                self.manager.db.saveInstanceInDB(row); n += 1
            except Exception:  # noqa: BLE001
                pass
        response.media = {'ok': True, 'rowsWritten': n, 'summary': plan['summary']}
