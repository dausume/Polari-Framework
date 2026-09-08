"""@module composition.objects.node._shared — what the node row classes share (constants, seeds, helpers); split from node_basis.py (sap-2c)."""
import json
from composition.custom.data_refs import resolve_named, rows

DECLARED_LEVELS = ('', 'component', 'part', 'subassembly',
                   'assembly', 'part-with-separable-sub-parts')
MEMBER_KINDS = ('component', 'node')
def _loads(text, default):
    try:
        return json.loads(text or '')
    except (TypeError, ValueError):
        return default
def owned_interfaces(manager, node_name):
    return [i for i in rows(manager, 'InterfaceDefinition')
            if getattr(i, 'node_ref', '') == node_name]
def _is_nested(manager, node_name):
    for other in rows(manager, 'CompositionNode'):
        for m in _loads(getattr(other, 'members_json', ''), []):
            if m.get('kind') == 'node' and m.get('ref') == node_name:
                return True
    return False
def derive_level(manager, node_name):
    """Derive the node's level from its structure, check it against
    the declaration, and say WHY — or refuse and say what would
    tell us."""
    node, refusal = resolve_named(manager, 'CompositionNode',
                                  node_name)
    if refusal:
        return {'ok': False, **refusal}
    members = _loads(getattr(node, 'members_json', ''), [])
    if not members:
        return {'ok': False, 'node': node_name,
                'refusal': 'node has no members — an empty node has '
                           'no level to derive',
                'suggestion': {'knob': 'members_json',
                               'action': 'list the components/nodes '
                                         'this is made of'}}
    unresolved = []
    for m in members:
        kind = m.get('kind')
        cls = ('PartComponentDefinition' if kind == 'component'
               else 'CompositionNode' if kind == 'node' else None)
        if cls is None:
            unresolved.append({'ref': m.get('ref', '?'),
                               'why': f'unknown member kind '
                                      f'"{kind}"'})
            continue
        _, ref_refusal = resolve_named(manager, cls, m.get('ref', ''))
        if ref_refusal:
            unresolved.append({'ref': m.get('ref', '?'),
                               'why': ref_refusal['refusal']})
    if unresolved:
        return {'ok': False, 'node': node_name,
                'refusal': 'member references do not resolve — a '
                           'level derived over missing members '
                           'would be a guess',
                'unresolved': unresolved}
    interfaces = owned_interfaces(manager, node_name)
    if (len(members) == 1 and members[0].get('kind') == 'component'
            and not interfaces):
        derived = 'component'
        deciding = []
    elif not interfaces:
        pairs = [f'{a.get("ref")} <-> {b.get("ref")}'
                 for i, a in enumerate(members)
                 for b in members[i + 1:]]
        return {'ok': False, 'node': node_name,
                'refusal': 'two or more members but NO interface '
                           'rows — separability is the level test '
                           'and it is unstated. This is "I do not '
                           'know", not a default',
                'suggestion': {'knob': 'InterfaceDefinition',
                               'action': 'add rows (designed_'
                                         'separable) for the member '
                                         'boundaries',
                               'pairs': pairs}}
    else:
        separable = [i for i in interfaces
                     if getattr(i, 'designed_separable', True)]
        bound = [i for i in interfaces
                 if not getattr(i, 'designed_separable', True)]
        if not separable:
            derived = 'part'
        elif not bound:
            derived = 'assembly'
        else:
            derived = 'part-with-separable-sub-parts'
        deciding = [{'interface': getattr(i, 'name', ''),
                     'separable': bool(getattr(i,
                                               'designed_separable',
                                               True))}
                    for i in interfaces]
    declared = getattr(node, 'declared_level', '') or ''
    matches = (declared == '' or declared == derived
               or (declared == 'subassembly' and derived == 'assembly'
                   and _is_nested(manager, node_name)))
    result = {
        'ok': True, 'node': node_name, 'derived': derived,
        'declared': declared, 'decidingInterfaces': deciding,
        'separableSet': [d['interface'] for d in deciding
                         if d['separable']],
        'boundSet': [d['interface'] for d in deciding
                     if not d['separable']],
        'note': ('one object, two separability regimes — promotion '
                 'attaches to the bound interface set, and the '
                 'separable set is what still comes apart'
                 if derived == 'part-with-separable-sub-parts'
                 else 'separability decides the level, not size or '
                      'complexity'),
    }
    if not matches:
        result['ok'] = False
        result['refusal'] = (
            f'declared level "{declared}" but structure derives '
            f'"{derived}" — the interface rows above decide it. '
            f'Either the declaration is stale or an interface row '
            f'is wrong; a label may not overrule the structure')
    return result
def composition_report(manager):
    """Every node with its derived level — the table view."""
    out = []
    for node in rows(manager, 'CompositionNode'):
        name = getattr(node, 'name', '')
        out.append(derive_level(manager, name))
    return {'ok': True, 'nodes': out, 'count': len(out),
            'refusals': [n for n in out if not n.get('ok')]}
