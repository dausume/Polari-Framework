"""
@module tensortree.tensortree_api

  GET  /api/tensortree                      the trees, with each one's validation summary
  GET  /api/tensortree/trees/{name}         one tree: nodes, unresolved spaces, the validation report
  GET  /api/tensortree/trees/{name}/graph   the graph VIEW (structure + every crossing mapping) — plan §16
  GET  /api/tensortree/trees/{name}/validate
  POST /api/tensortree/discover             {"selection": "<TensorSelection.name>", "context_node": ""} → ranked candidates
  POST /api/tensortree/select               {"node": "<TensorNode.name>", "ranges": {dim: [lo, hi]}, "created_from": "…"}
                                            → CREATES the TensorSelection row (the click is a mathematical object,
                                            plan §15) and returns its discovery: VISUALIZE → SELECT → DISCOVER
  GET  /api/tensortree/scale/{material}     tt-4: the material's SCALE tree as a reading of the materials model (levels,
                                            gaps, pspp scale transfers by reference, fidelity ladder) — no rows written
  POST /api/tensortree/scale/{material}/materialise   persist that view as tree rows (a person's action, idempotent)
Rows are edited through CRUDE (they are treeObjects); this surface reads, discovers, and makes rows only on a
person's explicit action (select, materialise).
"""
from objectTreeDecorators import treeObject, treeObjectInit

from tensortree.custom.tensortree_validate import validate_tree
from tensortree.custom.tensortree_graph import tree_graph
from tensortree.custom.tensortree_discover import discover
from tensortree.custom.tensortree_scale import scale_tree, materialise


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
            add('/api/tensortree/select', self, suffix='select')
            add('/api/tensortree/scale/{material}', self, suffix='scale')
            add('/api/tensortree/scale/{material}/materialise', self, suffix='materialise')

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

    def on_get_scale(self, request, response, material):
        v = scale_tree(self.manager, material)
        if not v.get('ok'):
            response.status = '404 Not Found'
        response.media = v

    def on_post_materialise(self, request, response, material):
        r = materialise(self.manager, material)
        if not r.get('ok'):
            response.status = '404 Not Found'; response.media = r; return
        response.status = '201 Created'; response.media = {'ok': True, 'written': r['written'], 'tree': r['view']['tree']}

    def on_post_select(self, request, response):
        import datetime, json as _json
        from tensortree.tensortree_basis import TensorSelection
        body = request.media if isinstance(request.media, dict) else {}
        node = str(body.get('node', '') or ''); ranges = body.get('ranges') or {}
        if not node or not isinstance(ranges, dict) or not ranges:
            response.status = '400 Bad Request'; response.media = {'ok': False, 'error': 'a selection names a node and at least one {dim: [lo, hi]} range'}; return
        if not any(str(n.name) == node for n in self._rows('TensorNode')):
            response.status = '404 Not Found'; response.media = {'ok': False, 'error': 'no TensorNode %r' % node}; return
        bad = [d for d, r in ranges.items() if not (isinstance(r, list) and len(r) == 2 and all(isinstance(x, (int, float)) for x in r) and r[0] <= r[1])]
        if bad:
            response.status = '400 Bad Request'; response.media = {'ok': False, 'error': 'ranges must be [lo, hi] numbers: ' + ', '.join(bad)}; return
        name = str(body.get('name') or ('%s@%s' % (node, datetime.datetime.now().strftime('%Y%m%d-%H%M%S'))))
        sel = TensorSelection(name=name, node=node, ranges_json=_json.dumps(ranges), created_from=str(body.get('created_from', 'api') or 'api'),
                              created_at=datetime.datetime.now().isoformat(timespec='seconds'), manager=self.manager)
        db = getattr(self.manager, 'db', None)   # the object-tree standard: persist what a request created
        if db is not None and hasattr(db, 'saveInstanceInDB'):
            db.saveInstanceInDB(sel)
        response.status = '201 Created'
        response.media = {'ok': True, 'selection': name, 'discovery': discover(self.manager, sel, str(body.get('context_node', '') or ''))}

    def on_post_discover(self, request, response):
        body = request.media if isinstance(request.media, dict) else {}
        sel = next((s for s in self._rows('TensorSelection') if str(s.name) == str(body.get('selection', ''))), None)
        if sel is None:
            response.status = '404 Not Found'; response.media = {'ok': False, 'error': 'no TensorSelection %r' % body.get('selection')}; return
        response.media = {'ok': True, 'discovery': discover(self.manager, sel, str(body.get('context_node', '') or ''))}
