"""
@module composition.node_basis

arch-2: the COMPOSITION TREE, with LEVEL DERIVED — never stamped.

The handover's distinguishing question at every boundary is
SEPARABILITY, and it is testable from structure alone:

  no members, one material            -> component
  interfaces all non-separable       -> part
  interfaces all separable           -> assembly
  mixed                              -> part-with-separable-sub-parts
                                        (mag-26 layered stator: one
                                        object, two regimes)

Ownership does the nesting work: a promoted part's internal
interfaces belong to IT, so a movement one level up sees only its
own separable boundaries and derives 'assembly' — no special case.

A node may DECLARE an intended level; declared != derived is a
REFUSAL naming the interface rows that decide it (same discipline as
viability: derived, and disagreement is information). Two or more
members with NO interface rows is 'I do not know' — stated, with the
member pairs that need rows.

@consumers polariServer seed passes, composition.composition_seed,
composition.composition_selftest
"""

import json

from objectTreeDecorators import treeObject, treeObjectInit

from composition.custom.data_refs import resolve_named, rows

#: Levels a node can DECLARE ('' = no declaration). 'subassembly'
#: is positional: an assembly that is itself a member of another
#: node — the derivation accepts it wherever 'assembly' derives and
#: the node is in fact nested.
DECLARED_LEVELS = ('', 'component', 'part', 'subassembly',
                   'assembly', 'part-with-separable-sub-parts')

MEMBER_KINDS = ('component', 'node')


class CompositionNode(treeObject):
    """One node of the composition tree: members + (via back-ref)
    the interfaces it owns. Level is DERIVED by derive_level()."""

    @treeObjectInit
    def __init__(self, name='', display_name='', declared_level='',
                 members_json='[]', functional_ref='',
                 genealogy_ref='', bulk_failure_mode_refs_json='[]',
                 is_prior=True, provenance_id='', notes='',
                 manager=None):
        self.name = name
        self.display_name = display_name
        self.declared_level = (declared_level
                               if declared_level in DECLARED_LEVELS
                               else '')
        #: [{'ref': name, 'kind': 'component'|'node',
        #:   'quantity': n}] — components are
        #: PartComponentDefinition rows, nodes nest.
        self.members_json = members_json
        #: FunctionalPartDefinition this node realizes (arch-3).
        self.functional_ref = functional_ref
        #: The node this identity was PROMOTED from (arch-4) — a
        #: promoted part is a NEW identity with its history named.
        self.genealogy_ref = genealogy_ref
        #: BULK-locus FailureModeDefinition names carried by this
        #: body (what a promotion bought it with).
        self.bulk_failure_mode_refs_json = bulk_failure_mode_refs_json
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes


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
