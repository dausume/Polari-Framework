"""
@module tensortree.custom.tensortree_validate

THE STRUCTURAL RULES OF A TENSORTREE (plan §11) AND LOCAL NODE VALIDITY (§12, §F6.1), as one read-only report.

  1 exactly one root · 2 every non-root has one structural parent that exists · 3 the hierarchy is acyclic ·
  4 mappings may cross branches (nothing to check) · 5 many trees per tensor (nothing to check) ·
  6 a tree may be arbitrarily incomplete (an UnresolvedTensorSpace is never an error).

A TensorNode is `resolved` when EVERY LocalizedDimension it names has a channel from the vocabulary and a
coherent config; an unresolved child never changes that (validity is local). `UnresolvedTensorSpace.
unresolved_kind` must be one of the five research tasks. The report sets nothing on disk: the caller decides.
"""
import json

CHANNELS = ('position.x', 'position.y', 'position.z', 'color', 'opacity', 'size', 'shape', 'orientation',
            'vector', 'label', 'time')
UNRESOLVED_KINDS = ('semantic', 'structural', 'visualization', 'mapping', 'validation')
VIEW_KINDS = ('spatial', 'scale', 'modal', 'decomposition', 'operator', 'other')


def _rows(manager, cls):
    return list((getattr(manager, 'objectTables', {}) or {}).get(cls, {}).values())


def _j(s, default):
    try:
        v = json.loads(s or '')
        return v if v is not None else default
    except Exception:
        return default


def dimension_coherent(dim):
    """A LocalizedDimension is coherent when its channel is in the vocabulary and its scale (if any) is well
    formed: continuous scales need a 2-element numeric domain; a channel needs a dimension name."""
    ch = str(getattr(dim, 'channel', '') or '')
    if ch not in CHANNELS or not str(getattr(dim, 'dimension', '') or ''):
        return False, 'channel %r is not one of %s or the dimension is unnamed' % (ch, ', '.join(CHANNELS))
    sc = _j(getattr(dim, 'scale_json', '{}'), {})
    if sc.get('kind') == 'continuous':
        d = sc.get('domain')
        if not (isinstance(d, list) and len(d) == 2 and all(isinstance(x, (int, float)) for x in d) and d[0] < d[1]):
            return False, 'a continuous scale needs "domain": [lo, hi]'
    return True, ''


def validate_tree(manager, tree_name):
    nodes = [n for n in _rows(manager, 'TensorNode') if str(getattr(n, 'tree', '')) == tree_name]
    unres = [u for u in _rows(manager, 'UnresolvedTensorSpace') if str(getattr(u, 'tree', '')) == tree_name]
    dims = {str(getattr(d, 'name', '')): d for d in _rows(manager, 'LocalizedDimension')}
    names = {str(getattr(x, 'name', '')): x for x in nodes + unres}
    errors, report = [], {'tree': tree_name, 'nodes': {}, 'unresolved': {}}
    roots = [n for n in names if not str(getattr(names[n], 'parent', '') or '')]
    if len(roots) != 1:
        errors.append('rule 1: exactly one root — found %d (%s)' % (len(roots), ', '.join(roots) or 'none'))
    for n, row in names.items():
        p = str(getattr(row, 'parent', '') or '')
        if p and p not in names:
            errors.append('rule 2: %s names parent %r which is not in this tree' % (n, p))
    # rule 3: walk every node to the root; a revisit is a cycle
    for n in names:
        seen, cur = set(), n
        while cur:
            if cur in seen:
                errors.append('rule 3: cycle through %s' % cur); break
            seen.add(cur)
            cur = str(getattr(names.get(cur), 'parent', '') or '') if names.get(cur) is not None else ''
    for node in nodes:
        n = str(getattr(node, 'name', ''))
        want = [str(x) for x in _j(getattr(node, 'dims_json', '[]'), [])]
        good, bad = [], {}
        for dn in want:
            d = dims.get(dn)
            if d is None:
                bad[dn] = 'no LocalizedDimension row'; continue
            ok, why = dimension_coherent(d)
            (good.append(dn) if ok else bad.__setitem__(dn, why))
        resolved = bool(want) and not bad and bool(str(getattr(node, 'binding_ref', '') or ''))
        report['nodes'][n] = {'status': 'resolved' if resolved else 'unresolved', 'coherent': good, 'incoherent': bad,
                              'binding_ref': str(getattr(node, 'binding_ref', '') or ''),
                              'why': '' if resolved else ('no localized dimensions' if not want else
                                                         ('no binding_ref' if not bad else 'incoherent: ' + ', '.join(bad)))}
    for u in unres:
        n = str(getattr(u, 'name', '')); k = str(getattr(u, 'unresolved_kind', '') or '')
        if k not in UNRESOLVED_KINDS:
            errors.append('%s: unresolved_kind %r is not one of %s' % (n, k, ', '.join(UNRESOLVED_KINDS)))
        report['unresolved'][n] = {'kind': k, 'open_questions': _j(getattr(u, 'open_questions_json', '[]'), [])}
    report['errors'] = errors
    report['ok'] = not errors
    report['resolved_nodes'] = sum(1 for v in report['nodes'].values() if v['status'] == 'resolved')
    report['note'] = ('validity is LOCAL: a node is resolved by its own dimensions and binding; an unresolved space '
                      'below it is not an error (a tree is useful before it is finished)')
    return report
