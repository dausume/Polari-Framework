"""
@module computelod.custom.computelod_walk

THE LADDER, READ (plan §F1), and WALKING it from any row (plan Core Design Principle): down through
ComputeMappings ("how is this implemented?"), up through CharacterizationMappings ("what does it produce?"),
and sideways to the concept node ("what do I need to learn?"). Every answer names the evidence status of the
edge it took; an absent edge is reported as unresolved, never invented.
"""


def _rows(manager, cls):
    return list((getattr(manager, 'objectTables', {}) or {}).get(cls, {}).values())


def ladder(manager):
    rungs = sorted(_rows(manager, 'ComputeLOD'), key=lambda r: int(getattr(r, 'rank', 0) or 0))
    kinds = _rows(manager, 'ComputeKind')
    out = []
    for r in rungs:
        out.append({'name': str(r.name), 'rank': int(getattr(r, 'rank', 0) or 0), 'group': str(getattr(r, 'group', '')),
                    'title': str(getattr(r, 'title', '')), 'design_level_ref': str(getattr(r, 'design_level_ref', '') or ''),
                    'owner_module': str(getattr(r, 'owner_module', '') or ''), 'status': str(getattr(r, 'status', '')),
                    'concept_node': str(getattr(r, 'concept_node', '') or ''),
                    # the short kind (the row name is <rung>/<kind>, unique across rungs)
                    'kinds': sorted(str(k.name).split('/', 1)[-1] for k in kinds if str(getattr(k, 'rung', '')) == str(r.name))})
    return out


def walk(manager, rung, ref, direction='down'):
    """One step: the edges leaving (down) or arriving at (up) <rung, ref>."""
    cls = 'ComputeMapping' if direction == 'down' else 'CharacterizationMapping'
    edges = []
    for m in _rows(manager, cls):
        src = (str(getattr(m, 'source_rung', '')), str(getattr(m, 'source_ref', '')))
        if src == (rung, ref):
            e = {'mapping': str(m.name), 'to_rung': str(getattr(m, 'target_rung', '')), 'to_ref': str(getattr(m, 'target_ref', '')),
                 'mapping_status': str(getattr(m, 'mapping_status', '')), 'evidence_level': str(getattr(m, 'evidence_level', '')),
                 'evidence_ref': str(getattr(m, 'evidence_ref', '') or '')}
            if cls == 'ComputeMapping':
                e['kind'] = str(getattr(m, 'kind', '')); e['loss_note'] = str(getattr(m, 'loss_note', '') or '')
            else:
                e['characteristic'] = str(getattr(m, 'characteristic', '')); e['result'] = getattr(m, 'result', 0.0)
                e['units'] = str(getattr(m, 'units', '')); e['method'] = str(getattr(m, 'method', ''))
            edges.append(e)
    return {'rung': rung, 'ref': ref, 'direction': direction, 'edges': edges,
            'unresolved': not edges, 'note': '' if edges else 'no %s mapping recorded from here — an honest gap, not an error' % direction}
