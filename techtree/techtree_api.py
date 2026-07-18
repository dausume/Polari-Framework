"""
@cross-cutting
@module techtree.techtree_api

TechTreeAPI (tt-3): the /api/techtree/* surface, mirroring
TopologyAPI — reads serve the tech-tree render mode (tt-4) and the
CLI; writes are row-level upserts only. Completion is always
DERIVED at read time (tree_completion/tree_payload); nothing here
stores a completion number, and gaps come back as evidence-bearing
suggestions, never auto-applied (knobs-and-suggestions).

@consumers
  - polariServer (instantiated next to TopologyAPI)
  - polari-platform-angular /tech-tree page (tt-4)
"""

import json

from objectTreeDecorators import treeObject, treeObjectInit

from techtree.techtree_analysis import (
    active_tree_name, sync_edges, tree_completion, tree_payload,
    validate_tree,
)
from techtree.techtree_basis import (
    TechDependencyEdge, TechNode, TechSegment, TechSegmentAssignment,
    TechTreeDefinition,
)

CLASS_MAP = {
    'TechTreeDefinition': TechTreeDefinition,
    'TechNode': TechNode,
    'TechSegment': TechSegment,
    'TechSegmentAssignment': TechSegmentAssignment,
    'TechDependencyEdge': TechDependencyEdge,
}


class TechTreeAPI(treeObject):
    """Tech-tree endpoints."""

    @treeObjectInit
    def __init__(self, polServer):
        self.polServer = polServer
        self.apiName = '/api/techtree'
        if polServer is not None:
            add = polServer.falconServer.add_route
            add('/api/techtree/summary', self, suffix='summary')
            add('/api/techtree/tree', self, suffix='tree')
            add('/api/techtree/completion', self, suffix='completion')
            add('/api/techtree/validate', self, suffix='validate')
            add('/api/techtree/node', self, suffix='node')
            add('/api/techtree/segment', self, suffix='segment')
            add('/api/techtree/assignment', self, suffix='assignment')
            add('/api/techtree/definition', self, suffix='definition')

    # ---- helpers ----------------------------------------------------

    def _payload(self, request):
        try:
            return json.load(request.bounded_stream), None
        except Exception as e:
            return None, f'bad JSON payload: {e}'

    def _tree_name(self, request, payload=None):
        name = ''
        if payload:
            name = payload.get('tree', '') or payload.get('name', '')
        if not name:
            name = request.params.get('name', '')
        return name or active_tree_name(self.manager)

    def _table(self, class_name):
        return (self.manager.objectTables or {}).get(class_name, {})

    def _find(self, class_name, name):
        for row in self._table(class_name).values():
            if getattr(row, 'name', '') == name:
                return row
        return None

    def _save(self, row):
        try:
            self.manager.db.saveInstanceInDB(row)
        except Exception:
            pass  # in-memory row stays authoritative until next save

    def _refuse(self, response, error, status='400 Bad Request'):
        response.status = status
        response.media = {'ok': False, 'error': error}

    def _sync_and_save_edges(self, tree_name):
        result = sync_edges(
            self.manager, tree_name,
            edge_factory=lambda **fields: TechDependencyEdge(
                **fields, manager=self.manager))
        for edge in self._table('TechDependencyEdge').values():
            if getattr(edge, 'tree_name', '') == tree_name:
                self._save(edge)
        return result

    # ---- reads ------------------------------------------------------

    def on_get_summary(self, request, response):
        response.media = {
            'ok': True,
            'activeTree': active_tree_name(self.manager),
            'counts': {class_name: len(self._table(class_name))
                       for class_name in CLASS_MAP},
            'trees': [
                {'name': getattr(t, 'name', ''),
                 'owner': getattr(t, 'owner', ''),
                 'isActive': getattr(t, 'is_active', False),
                 'isBaseline': getattr(t, 'is_baseline', False),
                 'description': getattr(t, 'description', '')}
                for t in self._table('TechTreeDefinition').values()]}

    def on_get_tree(self, request, response):
        name = self._tree_name(request)
        if not name:
            return self._refuse(
                response, 'no active tree and no ?name= given',
                '404 Not Found')
        report = tree_payload(self.manager, name)
        if not report.get('ok'):
            response.status = '404 Not Found'
        response.media = report

    def on_get_completion(self, request, response):
        name = self._tree_name(request)
        if not name:
            return self._refuse(
                response, 'no active tree and no ?name= given',
                '404 Not Found')
        report = tree_completion(self.manager, name)
        if not report.get('ok'):
            response.status = '404 Not Found'
        response.media = report

    # ---- writes (row-level only) ------------------------------------

    def on_post_validate(self, request, response):
        payload, err = self._payload(request)
        if err:
            payload = {}
        name = self._tree_name(request, payload or {})
        if not name:
            return self._refuse(
                response, 'no active tree and no name given',
                '404 Not Found')
        report = validate_tree(self.manager, name)
        if not report.get('ok'):
            return self._refuse(response, report.get('error'),
                                '404 Not Found')
        response.media = report

    _DEFINITION_FIELDS = ('owner', 'description', 'is_active',
                          'is_baseline', 'notes')
    _NODE_FIELDS = ('tree_name', 'title', 'description',
                    'depends_on_json', 'layout_hints_json', 'notes')
    _SEGMENT_FIELDS = ('tech_node', 'tree_name', 'kind', 'weight',
                       'notes')
    _ASSIGNMENT_FIELDS = ('tech_node', 'tree_name', 'segment_kind',
                          'ref_name', 'notes')

    def _upsert(self, request, response, class_name, fields):
        payload, err = self._payload(request)
        if err:
            return self._refuse(response, err)
        name = (payload or {}).get('name', '')
        if not name:
            return self._refuse(response, 'payload needs {name}')
        row = self._find(class_name, name)
        created = row is None
        updates = {k: payload[k] for k in fields if k in payload}
        if created:
            row = CLASS_MAP[class_name](
                name=name, **updates, manager=self.manager)
        else:
            for k, v in updates.items():
                setattr(row, k, v)
        self._save(row)
        # Node writes can change depends_on_json — re-derive +
        # re-designate the edge rows so the graph stays coherent.
        tree = getattr(row, 'tree_name', '') or self._tree_name(
            request, payload)
        sync = (self._sync_and_save_edges(tree)
                if class_name == 'TechNode' and tree else None)
        response.media = {'ok': True, 'name': name,
                          'created': created,
                          'updated': sorted(updates),
                          **({'edgeSync': sync} if sync else {})}

    def on_post_definition(self, request, response):
        self._upsert(request, response, 'TechTreeDefinition',
                     self._DEFINITION_FIELDS)

    def on_post_node(self, request, response):
        self._upsert(request, response, 'TechNode', self._NODE_FIELDS)

    def on_post_segment(self, request, response):
        self._upsert(request, response, 'TechSegment',
                     self._SEGMENT_FIELDS)

    def on_post_assignment(self, request, response):
        self._upsert(request, response, 'TechSegmentAssignment',
                     self._ASSIGNMENT_FIELDS)
