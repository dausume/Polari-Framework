"""
@module tensortree.custom.tensortree_graph

THE GRAPH VIEW (plan §16): a TensorTree's structural edges + every TensorMapping between its nodes. A view,
never rows — TensorTree stays the canonical rooted organization; the graph is the expanded relational reading.
"""


def _rows(manager, cls):
    return list((getattr(manager, 'objectTables', {}) or {}).get(cls, {}).values())


def tree_graph(manager, tree_name):
    nodes, edges = [], []
    for n in _rows(manager, 'TensorNode'):
        if str(getattr(n, 'tree', '')) != tree_name:
            continue
        nodes.append({'id': str(n.name), 'kind': 'node', 'title': str(getattr(n, 'title', '') or n.name), 'status': str(getattr(n, 'status', ''))})
        if str(getattr(n, 'parent', '') or ''):
            edges.append({'from': str(n.parent), 'to': str(n.name), 'kind': 'structural'})
    for u in _rows(manager, 'UnresolvedTensorSpace'):
        if str(getattr(u, 'tree', '')) != tree_name:
            continue
        nodes.append({'id': str(u.name), 'kind': 'unresolved', 'title': str(getattr(u, 'title', '') or u.name),
                      'unresolved_kind': str(getattr(u, 'unresolved_kind', ''))})
        if str(getattr(u, 'parent', '') or ''):
            edges.append({'from': str(u.parent), 'to': str(u.name), 'kind': 'structural'})
    ids = {n['id'] for n in nodes}
    for m in _rows(manager, 'TensorMapping'):
        s, t = str(getattr(m, 'source_node', '') or ''), str(getattr(m, 'target_node', '') or '')
        if s in ids or t in ids:
            edges.append({'from': s, 'to': t, 'kind': 'mapping', 'mapping': str(m.name), 'mapping_kind': str(getattr(m, 'kind', '')),
                          'evidence_level': str(getattr(m, 'evidence_level', '')), 'crosses': s in ids and t in ids})
    return {'tree': tree_name, 'nodes': nodes, 'edges': edges,
            'structural': sum(1 for e in edges if e['kind'] == 'structural'), 'mappings': sum(1 for e in edges if e['kind'] == 'mapping')}
