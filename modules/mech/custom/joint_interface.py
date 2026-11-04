"""
@module mech.custom.joint_interface

mxc-2 / D-mxc-8: the ONE WRITER between MechJoint and
composition.InterfaceDefinition. A joint is a thin row: kind,
feature pair, limits, ratio, preload. The boundary it realises —
members, separability, DOF removed, retention scheme — is a
composition interface row the joint points at through
`interface_ref`. The two must agree:

    joint free axes  ==  complement(interface.dof_removed_json)

and nothing else may write either side's DOF. This module derives
the interface from the joint (`interface_spec` — pure, no manager;
`interface_for_joint` — upserts the live row through the arch-1
seed_upsert path, the way composition's own seeds land), maps an
interface back to a joint (`joint_from_interface`, for FreeCAD
ingest and for the round-trip test), and says when the two drifted
(`consistency_check`).

Retention mapping (joint -> InterfaceDefinition.retention_scheme):
    fixed, fastener_refs non-empty            -> 'fastener'
    fixed, instance_a == instance_b           -> 'monolithic'
    fixed, shaft/bore feature pair            -> 'press'
    fixed, otherwise                          -> 'none'  (stated)
    grid, a magnet feature on either side     -> 'magnetic'
    grid, otherwise                           -> 'none'
    every motion kind (revolute, slider ...)  -> 'none'
'monolithic' and 'magnetic' were added to composition's
RETENTION_SCHEMES in this slice.

@consumers mech.custom.dof_solver, mech.mech_assembly_seed,
mech.mech_assembly_selftest, (mxc-3) the FreeCAD ingest
"""

import json

from composition.custom.data_refs import named, rows
from mech.objects.assembly._shared import (
    DOF_AXES, JOINT_DOF, JOINT_KINDS, complement, joint_free_axes, loads,
)

#: Marker written into the interface's notes so the joint KIND (which
#: the DOF set alone cannot always name: screw vs cylindrical, grid
#: held by magnets vs fixed) survives the round trip.
_TAG = '[mech joint'


def _get(obj, key, default=''):
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def interface_name_for(joint):
    """Deterministic interface name: the joint's interface_ref when
    set, else 'if-<joint name>'."""
    return _get(joint, 'interface_ref') or f'if-{_get(joint, "name")}'


def _feature_kind(feature):
    return _get(feature, 'kind') if feature is not None else ''


def retention_for(joint, feature_a=None, feature_b=None):
    """The InterfaceDefinition.retention_scheme a joint implies.
    Returns (scheme, why)."""
    kind = _get(joint, 'kind')
    fasteners = loads(_get(joint, 'fastener_refs_json', '[]'), [])
    kinds = {_feature_kind(feature_a), _feature_kind(feature_b)}
    if kind == 'fixed':
        if fasteners:
            return 'fastener', f'fixed joint realised by {fasteners}'
        if _get(joint, 'instance_a') and (_get(joint, 'instance_a')
                                           == _get(joint, 'instance_b')):
            return 'monolithic', ('both features on one body — a '
                                  'single-body boundary')
        if kinds >= {'shaft', 'bore'}:
            return 'press', 'shaft-in-bore fixed joint'
        return 'none', ('fixed joint with no fastener, no press pair '
                        'and two distinct bodies — retention UNSTATED')
    if kind == 'grid':
        if 'magnet' in kinds:
            return 'magnetic', 'grid seat with a magnet socket'
        return 'none', 'grid seat held by weight only'
    return 'none', f'{kind} joint: retained by its own geometry'


def interface_spec(joint, assembly=None, instances=None,
                   features=None):
    """The InterfaceDefinition seed dict for one joint — PURE (no
    manager), so seeds can precompute it and the live path can
    upsert it. `instances`: {name: MechPartInstance-like} to map
    instance -> component_ref; `features`: {name: MechFeature-like}
    for the retention decision."""
    instances = instances or {}
    features = features or {}
    kind = _get(joint, 'kind')
    free = joint_free_axes(joint)
    inst_a = instances.get(_get(joint, 'instance_a'))
    inst_b = instances.get(_get(joint, 'instance_b'))
    member_a = (_get(inst_a, 'component_ref') if inst_a else '') \
        or _get(joint, 'instance_a')
    member_b = (_get(inst_b, 'component_ref') if inst_b else '') \
        or _get(joint, 'instance_b')
    scheme, why = retention_for(
        joint, features.get(_get(joint, 'feature_a')),
        features.get(_get(joint, 'feature_b')))
    node_ref = _get(assembly, 'node_ref') if assembly is not None else ''
    notes = _get(joint, 'notes') or ''
    tag = (f'{_TAG} {_get(joint, "name")} kind={kind} '
           f'a={_get(joint, "instance_a")} b={_get(joint, "instance_b")} '
           f'retention-why: {why}]')
    return {
        'name': interface_name_for(joint),
        'display_name': f'{_get(joint, "name")} ({kind})',
        'node_ref': node_ref or '',
        'member_a': member_a, 'member_b': member_b,
        'designed_separable': scheme != 'monolithic',
        'dof_removed_json': json.dumps(list(complement(free))),
        'retention_scheme': scheme,
        'retention_material_requirements_json': '{}',
        'failure_mode_refs_json': '[]',
        'equation_refs_json': '[]',
        'realization_level': 'theoretical',
        'qualifying_act': ('assemble the fixture and exercise this '
                           'joint through its limits'),
        'is_prior': True,
        'provenance_id': 'mxc-2',
        'notes': (tag + (' ' + notes if notes else '')),
    }


def interface_for_joint(joint, manager, assembly=None):
    """Create or update the live InterfaceDefinition for `joint` on
    `manager` (the arch-1 upsert path: a changed field reaches the
    row, a human's is_prior=False row is left alone) and return its
    name. The joint's interface_ref is set to that name."""
    instances = {_get(i, 'name'): i
                 for i in rows(manager, 'MechPartInstance')}
    features = {_get(f, 'name'): f for f in rows(manager, 'MechFeature')}
    if assembly is None:
        assembly = named(manager, 'MechAssembly',
                         _get(joint, 'assembly_ref'))
    spec = interface_spec(joint, assembly, instances, features)
    from moduleService.seed_upsert import upsert_seed_rows
    try:
        from composition.interface_basis import InterfaceDefinition
    except Exception:
        InterfaceDefinition = None
    if InterfaceDefinition is None:
        import types
        existing = named(manager, 'InterfaceDefinition', spec['name'])
        if existing is None:
            manager.objectTables.setdefault('InterfaceDefinition', {})[
                spec['name']] = types.SimpleNamespace(**spec)
        else:
            for k, v in spec.items():
                setattr(existing, k, v)
    else:
        upsert_seed_rows(manager, 'InterfaceDefinition',
                         InterfaceDefinition, [spec], tag='MechJoint')
    if isinstance(joint, dict):
        joint['interface_ref'] = spec['name']
    else:
        joint.interface_ref = spec['name']
    return spec['name']


def _parse_tag(notes):
    """-> {'name', 'kind', 'a', 'b'} from the mech tag (empty strings
    when the interface was not written by mech)."""
    out = {'name': '', 'kind': '', 'a': '', 'b': ''}
    notes = notes or ''
    if _TAG not in notes:
        return out
    head = notes[notes.index(_TAG) + len(_TAG):].split(']', 1)[0]
    parts = head.strip().split()
    out['name'] = parts[0] if parts else ''
    for p in parts:
        for key in ('kind', 'a', 'b'):
            if p.startswith(key + '='):
                out[key] = p[len(key) + 1:]
    return out


def kind_from_free_axes(free):
    """The joint kinds whose DEFAULT free set equals `free` — in
    JOINT_KINDS order, so the first is the canonical guess and the
    rest are the ambiguity, stated."""
    free = tuple(a for a in DOF_AXES if a in set(free))
    return [k for k in JOINT_KINDS if JOINT_DOF[k] == free]


def joint_from_interface(iface, manager=None):
    """The reverse map: an InterfaceDefinition -> a MechJoint-shaped
    dict (kind, dof_json, instance_a/b, interface_ref, fastener
    presence). Members resolve to instances through component_ref
    when a manager is given (first instance carrying that component
    in the interface's node's assembly). Fields the interface does
    not carry (feature pair, limits, ratio, preload, the fastener
    NAMES) are NOT invented: they come back empty with `missing`
    naming them — the caller merges onto the existing MechJoint."""
    removed = loads(_get(iface, 'dof_removed_json', '[]'), [])
    free = complement(removed)
    tag = _parse_tag(_get(iface, 'notes'))
    name, kind = tag['name'], tag['kind']
    candidates = kind_from_free_axes(free)
    ambiguous = []
    scheme = _get(iface, 'retention_scheme', 'none')
    if not kind:
        if scheme == 'magnetic':
            kind = 'grid'
        elif candidates:
            kind = candidates[0]
            ambiguous = candidates[1:]
        else:
            kind = 'fixed' if not free else 'ball'
            ambiguous = ['no kind has exactly this free set — '
                         'dof_json carries it explicitly']
    inst_a, inst_b = _get(iface, 'member_a'), _get(iface, 'member_b')
    if tag['a'] and tag['b']:
        # the tag names the INSTANCES; members are components, and two
        # instances may share one component (two identical brackets)
        inst_a, inst_b = tag['a'], tag['b']
    elif manager is not None:
        by_component = {}
        for inst in rows(manager, 'MechPartInstance'):
            by_component.setdefault(_get(inst, 'component_ref'),
                                    _get(inst, 'name'))
        inst_a = by_component.get(inst_a, inst_a)
        inst_b = by_component.get(inst_b, inst_b)
    return {
        'name': name or _get(iface, 'name').replace('if-', '', 1),
        'kind': kind,
        'dof_json': json.dumps(list(free)),
        'instance_a': inst_a, 'instance_b': inst_b,
        'interface_ref': _get(iface, 'name'),
        'has_fastener': scheme == 'fastener',
        'retention_scheme': scheme,
        'ambiguous_kinds': ambiguous,
        'missing': ['feature_a', 'feature_b', 'limits_json', 'ratio',
                    'preload_json', 'fastener_refs_json'],
    }


def consistency_check(joint, iface, instances=None):
    """Do the joint and its interface still agree? Returns
    {'ok', 'mismatches': [{'field', 'joint', 'interface'}]} — the
    check the API runs before trusting either side."""
    instances = instances or {}
    mismatches = []
    free = set(joint_free_axes(joint))
    removed = set(loads(_get(iface, 'dof_removed_json', '[]'), []))
    if free & removed or (free | removed) != set(DOF_AXES):
        mismatches.append({'field': 'dof',
                           'joint': sorted(free),
                           'interface': sorted(removed),
                           'rule': 'free must be the exact complement '
                                   'of dof_removed'})
    expected_scheme, _ = retention_for(joint)
    if _get(joint, 'kind') == 'grid':
        expected_scheme = _get(iface, 'retention_scheme')  # needs features
    if _get(iface, 'retention_scheme') != expected_scheme:
        mismatches.append({'field': 'retention_scheme',
                           'joint': expected_scheme,
                           'interface': _get(iface, 'retention_scheme')})
    for side in ('a', 'b'):
        inst = instances.get(_get(joint, f'instance_{side}'))
        want = (_get(inst, 'component_ref') if inst else '') \
            or _get(joint, f'instance_{side}')
        have = _get(iface, f'member_{side}')
        if want != have:
            mismatches.append({'field': f'member_{side}',
                               'joint': want, 'interface': have})
    if _get(joint, 'interface_ref') and \
            _get(joint, 'interface_ref') != _get(iface, 'name'):
        mismatches.append({'field': 'interface_ref',
                           'joint': _get(joint, 'interface_ref'),
                           'interface': _get(iface, 'name')})
    return {'ok': not mismatches, 'joint': _get(joint, 'name'),
            'interface': _get(iface, 'name'), 'mismatches': mismatches}
