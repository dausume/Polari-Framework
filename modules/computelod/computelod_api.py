"""
@module computelod.computelod_api

  GET /api/computelod                         the ladder: eleven rungs with kinds, owner, design_level_ref, status
  GET /api/computelod/rungs/{name}            one rung + its kinds + its concept node's prerequisites
  GET /api/computelod/walk/{rung}/{ref}?direction=down|up   one step through the mappings from a row
"""
import json

from objectTreeDecorators import treeObject, treeObjectInit

from computelod.custom.computelod_walk import ladder, walk


class ComputeLodAPI(treeObject):
    @treeObjectInit
    def __init__(self, polServer):
        self.polServer = polServer
        self.apiName = '/api/computelod'
        if polServer is not None:
            add = polServer.falconServer.add_route
            add('/api/computelod', self)
            add('/api/computelod/rungs/{name}', self, suffix='rung')
            add('/api/computelod/walk/{rung}/{ref}', self, suffix='walk')

    def _rows(self, cls):
        return list((getattr(self.manager, 'objectTables', {}) or {}).get(cls, {}).values())

    def on_get(self, request, response):
        response.media = {'ok': True, 'ladder': ladder(self.manager),
                          'rule': 'ONE conceptual ladder; a KIND specializes within a rung and never creates one; die/package hang off microarchitecture through the microchip ladder (design_level_ref)'}

    def on_get_rung(self, request, response, name):
        r = next((x for x in ladder(self.manager) if x['name'] == name), None)
        if r is None:
            response.status = '404 Not Found'; response.media = {'ok': False, 'error': 'no rung %r' % name}; return
        node = next((n for n in self._rows('TechNode') if str(n.name) == r['concept_node']), None)
        prereq = json.loads(getattr(node, 'depends_on_json', '[]') or '[]') if node is not None else []
        response.media = {'ok': True, 'rung': r, 'learn': {'concept_node': r['concept_node'], 'recommended_prerequisites': prereq,
                                                            'note': 'learning order ≠ implementation order (plan §7): these are tech-tree edges, the ladder is the other'}}

    def on_get_walk(self, request, response, rung, ref):
        d = (request.params.get('direction') or 'down').strip()
        response.media = {'ok': True, 'walk': walk(self.manager, rung, ref, 'up' if d == 'up' else 'down')}
