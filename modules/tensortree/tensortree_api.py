"""
@module tensortree.tensortree_api

  GET  /api/tensortree                      the trees, with each one's validation summary
  GET  /api/tensortree/trees/{name}         one tree: nodes, unresolved spaces, the validation report
  GET  /api/tensortree/trees/{name}/graph   the graph VIEW (structure + every crossing mapping) — plan §16
  GET  /api/tensortree/trees/{name}/view      tt-5: ONE reading for the frontend panel — the graph + the validation +
                                            every node's localized dims with their channels + the selections + the policy
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
from tensortree.custom.tensortree_couple import propose as propose_coupling, couple as create_coupling, prove as prove_coupling
from tensortree.custom.tensortree_logic import of_mapping as _logic_of


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
            add('/api/tensortree/trees/{name}/view', self, suffix='view')
            add('/api/tensortree/discover', self, suffix='discover')
            add('/api/tensortree/select', self, suffix='select')
            add('/api/tensortree/scale/{material}', self, suffix='scale')
            add('/api/tensortree/scale/{material}/materialise', self, suffix='materialise')
            add('/api/tensortree/mappings/{name}/couple', self, suffix='couple')
            add('/api/tensortree/mappings/{name}/prove', self, suffix='prove')

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

    def on_get_view(self, request, response, name):
        import json as _json
        tree = next((t for t in self._rows('TensorTreeDefinition') if str(t.name) == name), None)
        if tree is None:
            response.status = '404 Not Found'; response.media = {'ok': False, 'error': 'no TensorTreeDefinition %r' % name}; return
        rep = validate_tree(self.manager, name); g = tree_graph(self.manager, name)
        dims = {}
        for d in self._rows('LocalizedDimension'):
            dims.setdefault(str(getattr(d, 'node', '')), []).append({'name': str(d.name), 'dimension': str(getattr(d, 'dimension', '')), 'channel': str(getattr(d, 'channel', '')),
                                                                       'range': _json.loads(getattr(d, 'range_json', '[]') or '[]'), 'scale': _json.loads(getattr(d, 'scale_json', '{}') or '{}')})
        nodes = []
        for n in g['nodes']:
            row = next((r for r in self._rows('TensorNode' if n['kind'] == 'node' else 'UnresolvedTensorSpace') if str(r.name) == n['id']), None)
            item = dict(n)
            if n['kind'] == 'node':
                v = rep['nodes'].get(n['id'], {})
                try:
                    gp = _json.loads(getattr(row, 'global_params_json', '{}') or '{}')
                except Exception:
                    gp = {}
                item.update({'status': v.get('status', 'unresolved'), 'why': v.get('why', ''), 'tensor': str(getattr(row, 'tensor', '') or ''), 'binding_ref': str(getattr(row, 'binding_ref', '') or ''),
                             'dims': dims.get(n['id'], []), 'incoherent': v.get('incoherent', {}), 'notes': str(getattr(row, 'notes', '') or ''),
                             # bp-2a: the sim space this node's binding renders in — the page scopes its ONE viewer to the tree's space
                             'sim_space': str((gp or {}).get('sim_space', '') or '')})
            else:
                item.update({'why': 'unresolved (%s)' % n.get('unresolved_kind', ''), 'known_dims': _json.loads(getattr(row, 'known_dims_json', '[]') or '[]'),
                             'open_questions': _json.loads(getattr(row, 'open_questions_json', '[]') or '[]'), 'candidates': _json.loads(getattr(row, 'candidate_bindings_json', '[]') or '[]') + _json.loads(getattr(row, 'candidate_mappings_json', '[]') or '[]'),
                             'hypotheses': _json.loads(getattr(row, 'hypotheses_json', '[]') or '[]')})
            nodes.append(item)
        maps = []
        for m in self._rows('TensorMapping'):
            if str(getattr(m, 'source_node', '')) in {n['id'] for n in nodes} or str(getattr(m, 'target_node', '')) in {n['id'] for n in nodes}:
                maps.append({'name': str(m.name), 'kind': str(getattr(m, 'kind', '')), 'source_node': str(getattr(m, 'source_node', '')), 'target_node': str(getattr(m, 'target_node', '')),
                             'source_dims': _json.loads(getattr(m, 'source_dims_json', '[]') or '[]'), 'target_dims': _json.loads(getattr(m, 'target_dims_json', '[]') or '[]'),
                             'mapping_status': str(getattr(m, 'mapping_status', '')), 'evidence_level': str(getattr(m, 'evidence_level', '')), 'evidence_ref': str(getattr(m, 'evidence_ref', '') or ''),
                             'loss_note': str(getattr(m, 'loss_note', '') or ''), 'validity': _json.loads(getattr(m, 'validity_json', '{}') or '{}'),
                             # pf-0 / D-pf-8: the proof state shown ON the mapping (a badge + the obligations), never folded into its status
                             'logic': _logic_of(self.manager, str(m.name))})
        sels = [{'name': str(s.name), 'node': str(getattr(s, 'node', '')), 'ranges': _json.loads(getattr(s, 'ranges_json', '{}') or '{}'), 'created_from': str(getattr(s, 'created_from', ''))}
                for s in self._rows('TensorSelection') if str(getattr(s, 'node', '')) in {n['id'] for n in nodes}]
        response.media = {'ok': True, 'tree': {'name': name, 'tensor': str(getattr(tree, 'tensor', '') or ''), 'view_kind': str(getattr(tree, 'view_kind', '')), 'root': str(getattr(tree, 'root_node', '')),
                                               'description': str(getattr(tree, 'description', '') or '')},
                          'nodes': nodes, 'edges': [e for e in g['edges'] if e['kind'] == 'structural'], 'mappings': maps, 'selections': sels,
                          'validation': {'ok': rep['ok'], 'errors': rep['errors'], 'resolved_nodes': rep['resolved_nodes']},
                          'channels': ['position.x', 'position.y', 'position.z', 'color', 'opacity', 'size', 'shape', 'orientation', 'vector', 'label', 'time'],
                          'evidence_levels': ['none', 'analytical', 'simulated', 'measured']}

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
        response.media = {'ok': True, 'selection': name, 'discovery': discover(self.manager, sel, str(body.get('context_node', '') or ''), str(body.get('via', '') or ''))}

    # ---- tt-7: a SimulationCouplingDefinition created FROM a kind=coupling mapping ------------------------------
    def on_get_couple(self, request, response, name):
        """Dry run: the coupling row that WOULD be created from mapping {name}, what it was derived from, what is missing."""
        p = propose_coupling(self.manager, name, {k: v for k, v in (request.params or {}).items()})
        response.status = {404: '404 Not Found', 422: '422 Unprocessable Entity'}.get(p.get('status'), '200 OK')
        response.media = p

    def on_post_couple(self, request, response, name):
        """Create it (a person's action). Body: sampler_equation_ref | config | name | description | enabled | force."""
        body = request.media if isinstance(request.media, dict) else {}
        p = create_coupling(self.manager, name, body)
        response.status = {404: '404 Not Found', 422: '422 Unprocessable Entity', 409: '409 Conflict', 201: '201 Created'}.get(p.get('status'), '200 OK')
        response.media = p

    def on_post_prove(self, request, response, name):
        """Execute the mapping's coupling once through the runner's own pre-pass (one coupling, one run) and write the simulated evidence."""
        body = request.media if isinstance(request.media, dict) else {}
        p = prove_coupling(self.manager, name, body)
        response.status = {404: '404 Not Found', 422: '422 Unprocessable Entity'}.get(p.get('status'), '200 OK')
        response.media = p

    def on_post_discover(self, request, response):
        body = request.media if isinstance(request.media, dict) else {}
        sel = next((s for s in self._rows('TensorSelection') if str(s.name) == str(body.get('selection', ''))), None)
        if sel is None:
            response.status = '404 Not Found'; response.media = {'ok': False, 'error': 'no TensorSelection %r' % body.get('selection')}; return
        response.media = {'ok': True, 'discovery': discover(self.manager, sel, str(body.get('context_node', '') or ''), str(body.get('via', '') or ''))}
