"""
@module tensortree.tensortree_api

  GET  /api/tensortree                      the trees, with each one's validation summary
  GET  /api/tensortree/trees/{name}         one tree: nodes, unresolved spaces, the validation report
  GET  /api/tensortree/trees/{name}/graph   the graph VIEW (structure + every crossing mapping) — plan §16
  GET  /api/tensortree/trees/{name}/validate
  POST /api/tensortree/discover             {"selection": "<TensorSelection.name>", "context_node": ""} → ranked candidates
Rows are edited through CRUDE (they are treeObjects); this surface only READS and DISCOVERS.
"""
from objectTreeDecorators import treeObject, treeObjectInit

from tensortree.custom.tensortree_validate import validate_tree
from tensortree.custom.tensortree_graph import tree_graph
from tensortree.custom.tensortree_discover import discover


class TensorTreeAPI(treeObject):
    @treeObjectInit
    def __init__(self, polServer):
        self.polServer = polServer
        self.apiName = '/api/tensortree'
        if polServer is not None:
            add = polServer.falconServer.add_route
            add('/api/tensortree', self)
            add('/api/tensortree/trees/{name}', self, suffix='tree')
            add('/api/tensortree/trees/{name}/graph', self, suffix='graph')
            add('/api/tensortree/trees/{name}/validate', self, suffix='validate')
            add('/api/tensortree/discover', self, suffix='discover')

    def _rows(self, cls):
        return list((getattr(self.manager, 'objectTables', {}) or {}).get(cls, {}).values())

    def on_get(self, request, response):
        trees = []
        for t in self._rows('TensorTreeDefinition'):
            rep = validate_tree(self.manager, str(t.name))
            trees.append({'name': str(t.name), 'tensor': str(getattr(t, 'tensor', '')), 'view_kind': str(getattr(t, 'view_kind', '')),
                          'ok': rep['ok'], 'resolved_nodes': rep['resolved_nodes'], 'nodes': len(rep['nodes']), 'unresolved': len(rep['unresolved'])})
        response.media = {'ok': True, 'count': len(trees), 'trees': trees,
                          'rules': 'one root · one structural parent · acyclic · mappings may cross · many trees per tensor · a tree may be incomplete'}

    def on_get_tree(self, request, response, name):
        rep = validate_tree(self.manager, name)
        response.media = {'ok': True, 'tree': name, 'validation': rep}

    def on_get_graph(self, request, response, name):
        response.media = {'ok': True, 'graph': tree_graph(self.manager, name)}

    def on_get_validate(self, request, response, name):
        response.media = {'ok': True, 'validation': validate_tree(self.manager, name)}

    def on_post_discover(self, request, response):
        body = request.media if isinstance(request.media, dict) else {}
        sel = next((s for s in self._rows('TensorSelection') if str(s.name) == str(body.get('selection', ''))), None)
        if sel is None:
            response.status = '404 Not Found'; response.media = {'ok': False, 'error': 'no TensorSelection %r' % body.get('selection')}; return
        response.media = {'ok': True, 'discovery': discover(self.manager, sel, str(body.get('context_node', '') or ''))}
