"""
@module motors.composition_splice

arch-8: the WRAP, NOT PORT splice (PART_ARCHETYPES_PLAN arch-0 §2).
Motors keeps its MotorPartDefinition rows; this adapter presents a
motor design as a composition view — the same rows exposed as
component members of one CompositionNode-shaped report, with the
M0's real interfaces stated so the level DERIVES. Nothing is
duplicated into seeded composition rows: the adapter reads live
motor rows at call time, so the view cannot drift from the bill
(mag-11's rule: the picture and the bill come from the same rows).

The M0 interfaces are stated HERE because they are motor knowledge:
press fits from mag-15 (assembly governs at clock scale), the
pinion's field buffer, and the working air gap — which is a
DESIGNED NON-CONTACT relation, recorded as an interface with zero
DOF removed rather than omitted (the gap is the machine).

@consumers motors.motor_api, motors.selftest_motors
"""

import json

from composition.node_basis import derive_level
from motors.part_roles import PART_ROLE_ASSIGNMENTS
from magnetics.magnet_analysis import _rows

#: The M0's separable boundaries — every one designed, every one
#: with its DOF mate. All separable ⇒ the movement derives ASSEMBLY.
M0_INTERFACES = [
    {'name': 'ifm0-rotor-shaft', 'member_a': 'lavet-v2-rotor-magnet',
     'member_b': 'lavet-v2-pinion', 'designed_separable': True,
     'dof_removed': ['tx', 'ty', 'tz', 'rx', 'ry'],
     'retention_scheme': 'press',
     'failure_modes': ['fm-preload-loss'],
     'note': 'press fit — the handling load governs (mag-15)'},
    {'name': 'ifm0-coil-bobbin', 'member_a': 'lavet-v2-coil',
     'member_b': 'lavet-v2-bobbin-flanges',
     'designed_separable': True,
     'dof_removed': ['tx', 'ty', 'tz', 'rx', 'ry'],
     'retention_scheme': 'wound',
     'failure_modes': ['fm-turn-to-turn-abrasion', 'fm-fretting'],
     'note': 'the simple-stator construction (cv-stator-simple); '
             'binding it is the recorded promotion candidate'},
    {'name': 'ifm0-bobbin-stator', 'member_a': 'lavet-v2-bobbin-flanges',
     'member_b': 'lavet-v2-stator', 'designed_separable': True,
     'dof_removed': ['tx', 'ty', 'tz', 'rx', 'ry', 'rz'],
     'retention_scheme': 'press',
     'failure_modes': ['fm-preload-loss'], 'note': ''},
    {'name': 'ifm0-leads-coil', 'member_a': 'lavet-v2-leads',
     'member_b': 'lavet-v2-coil', 'designed_separable': True,
     'dof_removed': ['tx', 'ty', 'tz'],
     'retention_scheme': 'fastener',
     'failure_modes': ['fm-fretting'],
     'note': 'solder/wrap joint — separable by rework'},
    {'name': 'ifm0-working-gap', 'member_a': 'lavet-v2-stator',
     'member_b': 'lavet-v2-rotor-magnet',
     'designed_separable': True, 'dof_removed': [],
     'retention_scheme': 'none',
     'failure_modes': [],
     'note': 'the WORKING AIR GAP: a designed non-contact relation '
             '— zero DOF removed, never mortared (the mortar-model '
             'rule), and the reason the rotor can turn at all'},
]


#: M0's interfaces were exercised by the bench build; a spec that
#: does not say otherwise inherits that. M1 specs carry their own
#: (theoretical) levels — made-and-measured must never leak onto
#: an unbuilt machine.
_M0_REALIZATION = {
    'realization_level': 'made-and-measured',
    'qualifying_act': 'the M0 bench build assembled and '
                      'disassembled every one of these joints',
}


def interface_specs(design_name):
    """The stated joints per design — motor knowledge, dispatched
    here so every consumer (composition view, failure conditions,
    scene markers) reads the ONE list."""
    if design_name == 'clock-lavet-m0':
        return M0_INTERFACES
    if design_name == 'reluctance-6s4p-m1':
        from motors.m1_composition import M1_INTERFACES
        return M1_INTERFACES
    return []


def _declared_level(design_name):
    if design_name == 'reluctance-6s4p-m1':
        from motors.m1_composition import M1_DECLARED_LEVEL
        return M1_DECLARED_LEVEL
    return 'assembly'


def _promotion_answers(design_name):
    if design_name == 'clock-lavet-m0':
        return _M0_PROMOTION_ANSWERS
    if design_name == 'reluctance-6s4p-m1':
        from motors.m1_composition import M1_PROMOTION_ANSWERS
        return M1_PROMOTION_ANSWERS
    return {}


class _Row:
    def __init__(self, **kw):
        for k, v in kw.items():
            setattr(self, k, v)


def _movement_parts(manager, design_name):
    return [p for p in _rows(manager, 'MotorPartDefinition')
            if getattr(p, 'design_ref', '') == design_name]


def composition_view(manager, design_name='clock-lavet-m0'):
    """The motor design as composition structure: an overlay manager
    holding the SAME part rows as components, one movement node,
    and the stated interfaces — then the real derive_level() run
    over it. Read-only; nothing persists."""
    parts = _movement_parts(manager, design_name)
    if not parts:
        return {'ok': False,
                'refusal': f'no MotorPartDefinition rows for design '
                           f'"{design_name}"'}
    members = []
    components = {}
    for p in parts:
        name = getattr(p, 'name', '')
        members.append({'ref': name, 'kind': 'component',
                        'quantity': getattr(p, 'quantity', 1)})
        components[name] = _Row(
            name=name,
            display_name=getattr(p, 'display_name', ''),
            material_ref=getattr(p, 'material_ref', ''),
            material_condition='',
            shape_ref=getattr(p, 'shape_ref', ''),
            shape_units=getattr(p, 'shape_units', 'cm'),
            coating_ref='', coating_build_mm=0.0,
            roles=PART_ROLE_ASSIGNMENTS.get(name, []))
    node_name = f'{design_name}-movement'
    interfaces = {}
    stated = []
    part_names = set(components)
    for spec in interface_specs(design_name):
        if not {spec['member_a'], spec['member_b']} <= part_names:
            continue
        stated.append(spec['name'])
        interfaces[spec['name']] = _Row(
            name=spec['name'], node_ref=node_name,
            member_a=spec['member_a'], member_b=spec['member_b'],
            designed_separable=spec['designed_separable'],
            dof_removed_json=json.dumps(spec['dof_removed']),
            retention_scheme=spec['retention_scheme'],
            retention_material_requirements_json='{}',
            failure_mode_refs_json=json.dumps(spec['failure_modes']),
            equation_refs_json='[]',
            realization_level=spec.get(
                'realization_level',
                _M0_REALIZATION['realization_level']),
            qualifying_act=spec.get(
                'qualifying_act', _M0_REALIZATION['qualifying_act']),
            notes=spec['note'])
    overlay = _Row(objectTables={
        'CompositionNode': {node_name: _Row(
            name=node_name,
            declared_level=_declared_level(design_name),
            members_json=json.dumps(members),
            functional_ref='', genealogy_ref='',
            bulk_failure_mode_refs_json='[]')},
        'PartComponentDefinition': components,
        'InterfaceDefinition': interfaces,
    }, objectTypingDict={
        'CompositionNode': object(),
        'PartComponentDefinition': object(),
        'InterfaceDefinition': object()})
    level = derive_level(overlay, node_name)
    # Parity: the adapter is honest only if it exposes EVERY part
    # the bill sees, with the SAME material and shape refs.
    parity = {
        'partCount': len(parts),
        'memberCount': len(members),
        'allMaterialsMatch': all(
            components[getattr(p, 'name', '')].material_ref
            == getattr(p, 'material_ref', '') for p in parts),
        'allShapesMatch': all(
            components[getattr(p, 'name', '')].shape_ref
            == getattr(p, 'shape_ref', '') for p in parts),
    }
    roles_missing = [n for n, c in components.items()
                     if not c.roles]
    return {
        'ok': True, 'design': design_name, 'node': node_name,
        'level': level,
        'members': [{'ref': m['ref'],
                     'material': components[m['ref']].material_ref,
                     'shapeRef': components[m['ref']].shape_ref,
                     'shapeUnits': components[m['ref']].shape_units,
                     'roles': components[m['ref']].roles}
                    for m in members],
        'interfaces': stated,
        'parity': parity,
        'rolesMissingOn': roles_missing,
        'note': 'WRAP, NOT PORT: this view reads the live '
                'MotorPartDefinition rows at call time, so it '
                'cannot drift from the mag-11 bill — same rows, '
                'same shapes, same materials.',
    }


_M0_PROMOTION_ANSWERS = {
        'ifm0-coil-bobbin': {
            'moves_relative': False, 'separable_for_service': False,
            'why': 'the mag-26 bound stator: fusing deletes '
                   'fretting outright; service = rewind from new'},
        'ifm0-rotor-shaft': {
            'moves_relative': False, 'separable_for_service': True,
            'why': 'the pinion is the wear part — it must come off '
                   'to be replaced, or the rotor magnet dies with '
                   'it'},
        'ifm0-bobbin-stator': {
            'moves_relative': False, 'separable_for_service': True,
            'why': 'the stator is the chassis; potting the bobbin '
                   'in makes the whole movement one scrap unit'},
        'ifm0-leads-coil': {
            'moves_relative': False, 'separable_for_service': True,
            'why': 'rework joint by design'},
        'ifm0-working-gap': {
            'moves_relative': True, 'separable_for_service': True,
            'why': 'the rotor TURNS — this interface is the '
                   'machine. The gate refusing it is the model '
                   'working'},
}


def promotion_candidates(manager, design_name='clock-lavet-m0'):
    """Which of the movement's interfaces COULD be promoted, per
    the Boothroyd-Dewhurst questions — a suggestion surface, never
    an action. Interfaces already NON-SEPARABLE (M1's mold-fused
    castings) are not candidates: their promotion already happened,
    and they are listed as such rather than re-asked."""
    view = composition_view(manager, design_name)
    if not view.get('ok'):
        return view
    answers = _promotion_answers(design_name)
    specs = {s['name']: s for s in interface_specs(design_name)}
    out, already = [], []
    for name in view['interfaces']:
        spec = specs.get(name, {})
        if not spec.get('designed_separable', True):
            already.append({
                'interface': name,
                'note': f'already fused '
                        f'({spec.get("retention_scheme", "?")}): '
                        f'{spec.get("note", "")}'})
            continue
        a = answers.get(name, {})
        blocked = a.get('moves_relative') \
            or a.get('separable_for_service')
        out.append({'interface': name,
                    'promotable': not blocked,
                    'why': a.get('why', 'not assessed'),
                    'blockers': [b for b, hit in
                                 (('members must move relative',
                                   a.get('moves_relative')),
                                  ('must separate for service',
                                   a.get('separable_for_service')))
                                 if hit]})
    return {'ok': True, 'design': design_name, 'candidates': out,
            'promotable': [c['interface'] for c in out
                           if c['promotable']],
            'alreadyPromoted': already,
            'note': 'suggestions over evidence — promoting any of '
                    'these is a human decision recorded as an '
                    'arch-4 PROMOTE operation, never an automatic '
                    'act'}
