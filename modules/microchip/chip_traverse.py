"""
@module microchip.chip_traverse

The traversal engine over the design ladder: level report (which
rungs have LIVE artifacts on this instance, which refuse), node
traversal (up the parent chain, down to children), and artifact
resolution — every {module, class, name} reference resolved
against the live object tables, every {anchor} reference resolved
against cntfet's citation-anchor rows. A reference that does not
resolve is reported 'absent' with the module that would provide
it — honest degradation, never an import error (this module
imports NO device code).

@consumers
  - microchip.chip_api
  - microchip.selftest_microchip
"""

import json


def _rows(manager, class_name):
    tables = getattr(manager, 'objectTables', None) or {}
    return (tables.get(class_name) or {}).values()


def _get(manager, class_name, name):
    for row in _rows(manager, class_name):
        if getattr(row, 'name', '') == name:
            return row
    return None


def _loads(row, key, fallback):
    try:
        return json.loads(getattr(row, key, '') or fallback)
    except Exception:
        return json.loads(fallback)


def resolve_artifact(manager, ref):
    """One artifact reference -> honest resolution record."""
    if 'anchor' in ref:
        row = _get(manager, 'CNTCalibrationAnchor', ref['anchor'])
        if row is None:
            return {'ref': ref, 'kind': 'citation-anchor',
                    'resolved': False,
                    'why': 'cntfet module absent or anchor rows '
                           'not seeded on this instance'}
        return {'ref': ref, 'kind': 'citation-anchor',
                'resolved': True,
                'value': getattr(row, 'value', None),
                'unit': getattr(row, 'unit', ''),
                'doi': getattr(row, 'doi', ''),
                'figure': getattr(row, 'figure', ''),
                'status': getattr(row, 'status', '')}
    row = _get(manager, ref.get('class', ''), ref.get('name', ''))
    if row is None:
        return {'ref': ref, 'kind': 'object-row', 'resolved': False,
                'why': f"module '{ref.get('module', '?')}' absent "
                       f"on this instance, or row "
                       f"'{ref.get('name', '?')}' not seeded"}
    return {'ref': ref, 'kind': 'object-row', 'resolved': True,
            'derivedAt': getattr(row, 'derived_at', ''),
            'status': 'derived' if getattr(row, 'derived_at', '')
            else 'seeded-underived'}


def levels_report(manager):
    """The ladder with per-level LIVE artifact counts on THIS
    instance (levels whose classes are absent refuse honestly)."""
    levels = sorted(_rows(manager, 'DesignLevelDefinition'),
                    key=lambda r: getattr(r, 'rank', 0))
    out = []
    tables = getattr(manager, 'objectTables', None) or {}
    for level in levels:
        classes = _loads(level, 'artifact_classes_json', '[]')
        artifacts = []
        for entry in classes:
            table = tables.get(entry.get('class', ''))
            if table is None:
                artifacts.append({**entry, 'present': False,
                                  'why': f"module "
                                  f"'{entry.get('module')}' not "
                                  f"loaded on this instance"})
            else:
                artifacts.append({**entry, 'present': True,
                                  'rowCount': len(table)})
        out.append({
            'name': level.name, 'rank': level.rank,
            'description': level.description,
            'status': level.status,
            'planPointer': level.plan_pointer,
            'scaleAxes': _loads(level, 'scale_axes_json', '[]'),
            'artifactClasses': artifacts,
            'refusal': None if level.status == 'live' else
            f'no artifacts exist at this level yet — '
            f'{level.plan_pointer}'})
    return out


def node_children(manager, node_name):
    return sorted(
        (r for r in _rows(manager, 'MicrochipDesignNode')
         if getattr(r, 'parent', '') == node_name),
        key=lambda r: getattr(r, 'name', ''))


def _node_summary(manager, node, with_artifacts=True):
    out = {
        'name': node.name, 'design': node.design,
        'level': node.level, 'parent': node.parent,
        'title': node.title, 'status': node.status,
        'citation': node.citation,
        'metrics': _loads(node, 'metrics_json', '{}'),
        'notes': node.notes,
    }
    if with_artifacts:
        out['artifacts'] = [
            resolve_artifact(manager, ref)
            for ref in _loads(node, 'artifact_refs_json', '[]')]
    return out


def traverse(manager, node_name):
    """The traversal interface: the node, its full parent chain
    (up to the chip root), its children (down toward devices),
    and every artifact reference resolved."""
    node = _get(manager, 'MicrochipDesignNode', node_name)
    if node is None:
        return {'ok': False, 'error': f'no design node '
                                      f'"{node_name}"'}
    up = []
    cursor, hops = node, 0
    while getattr(cursor, 'parent', '') and hops < 12:
        cursor = _get(manager, 'MicrochipDesignNode',
                      cursor.parent)
        if cursor is None:
            up.append({'broken': 'parent link points at a '
                                 'missing node'})
            break
        up.append(_node_summary(manager, cursor,
                                with_artifacts=False))
        hops += 1
    down = [_node_summary(manager, child)
            for child in node_children(manager, node_name)]
    return {'ok': True,
            'node': _node_summary(manager, node),
            'up': up, 'down': down}


def design_tree(manager, design):
    """The whole design as a nested tree from its root(s)."""
    nodes = [r for r in _rows(manager, 'MicrochipDesignNode')
             if getattr(r, 'design', '') == design]
    if not nodes:
        return {'ok': False, 'error': f'no design "{design}"'}

    def subtree(node, depth):
        entry = _node_summary(manager, node)
        if depth < 12:
            entry['children'] = [
                subtree(child, depth + 1)
                for child in node_children(manager, node.name)
                if getattr(child, 'design', '') == design]
        return entry
    roots = [n for n in nodes if not getattr(n, 'parent', '')]
    return {'ok': True, 'design': design,
            'tree': [subtree(root, 0) for root in roots],
            'nodeCount': len(nodes)}
