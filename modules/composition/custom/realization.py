"""
@module composition.custom.realization

arch-6: REALIZATION ROLLS UP, DERIVED — the answer to handover §5.5
(do assemblies get realization levels?): yes, as the MINIMUM over
their member materials and their interfaces, because a design of
made-and-measured parts is still an unbuilt assembly and the
interfaces are exactly what has not been demonstrated (practice:
integration readiness, IRL).

The ladder is the same one magnetics earns per material —
theoretical → literature-demonstrated → recipe-seeded →
made-and-measured — and the selftest asserts the two modules AGREE
(the mag-25 lesson: two modules stating the same fact must be
tested against each other). Levels are never advanced here:
advancing is a qualifying act somebody performs (mag-12,
suggestion-over-evidence); this module only reports what is earned
and WHAT ACT WOULD ADVANCE IT.

@consumers composition.composition_api,
composition.composition_selftest
"""

import json

from composition.custom.data_refs import named, resolve_named
from composition.node_basis import owned_interfaces

REALIZATION_LEVELS = ('theoretical', 'literature-demonstrated',
                      'recipe-seeded', 'made-and-measured')


def _rank(level):
    try:
        return REALIZATION_LEVELS.index(level)
    except ValueError:
        return -1


def material_realization(manager, material_ref):
    """(level, note) for a material row, honestly unassessed when
    the row or its module is absent."""
    opt = named(manager, 'MagneticMaterialOption', material_ref)
    if opt is None:
        return None, (f'material "{material_ref}" not resolvable '
                      f'(row absent or owning module not booted)')
    level = getattr(opt, 'realization_level', '')
    if level not in REALIZATION_LEVELS:
        return None, (f'material "{material_ref}" states no '
                      f'realization level')
    return level, ''


def node_realization(manager, node_name):
    """min(member materials, owned interfaces) — with the LIMITING
    elements named and the acts that would advance them."""
    node, refusal = resolve_named(manager, 'CompositionNode',
                                  node_name)
    if refusal:
        return {'ok': False, **refusal}
    try:
        members = json.loads(getattr(node, 'members_json', '')
                             or '[]')
    except ValueError:
        members = []
    contributions = []
    unassessed = []
    for m in members:
        if m.get('kind') == 'node':
            sub = node_realization(manager, m.get('ref', ''))
            if sub.get('ok'):
                contributions.append(
                    {'element': m.get('ref'), 'kind': 'sub-node',
                     'level': sub['level'],
                     'act': sub.get('nextAct', '')})
            else:
                unassessed.append({'element': m.get('ref'),
                                   'why': sub.get('refusal', '')})
            continue
        comp = named(manager, 'PartComponentDefinition',
                     m.get('ref', ''))
        if comp is None:
            unassessed.append({'element': m.get('ref'),
                               'why': 'component row not '
                                      'resolvable'})
            continue
        level, why = material_realization(
            manager, getattr(comp, 'material_ref', ''))
        if level is None:
            unassessed.append({'element': m.get('ref'), 'why': why})
        else:
            contributions.append(
                {'element': m.get('ref'), 'kind': 'material',
                 'material': getattr(comp, 'material_ref', ''),
                 'level': level, 'act': ''})
    for iface in owned_interfaces(manager, node_name):
        level = getattr(iface, 'realization_level', '')
        if level not in REALIZATION_LEVELS:
            unassessed.append(
                {'element': getattr(iface, 'name', ''),
                 'why': 'interface states no realization level'})
            continue
        contributions.append(
            {'element': getattr(iface, 'name', ''),
             'kind': 'interface', 'level': level,
             'act': getattr(iface, 'qualifying_act', '')})
    if not contributions and not unassessed:
        return {'ok': False, 'node': node_name,
                'refusal': 'nothing to derive realization from — '
                           'no resolvable members or interfaces'}
    if unassessed:
        # A gap is a gap, never silently the floor OR ignored.
        return {'ok': True, 'node': node_name, 'level': 'unassessed',
                'unassessed': unassessed,
                'contributions': contributions,
                'note': 'realization cannot be derived past an '
                        'unassessed element — a property nobody '
                        'measured cannot clear a requirement, and '
                        'a member nobody can resolve cannot either'}
    floor = min(contributions, key=lambda c: _rank(c['level']))
    limiting = [c for c in contributions
                if c['level'] == floor['level']]
    return {
        'ok': True, 'node': node_name, 'level': floor['level'],
        'limitedBy': limiting,
        'contributions': contributions,
        'nextAct': next((c['act'] for c in limiting if c.get('act')),
                        ''),
        'note': 'derived as the MINIMUM over materials and '
                'interfaces (IRL): a design of made-and-measured '
                'parts is still an unbuilt assembly, and the '
                'interface is what has not been demonstrated. '
                'Advancing a level is a qualifying act somebody '
                'performs — never a relabelling here.',
    }
