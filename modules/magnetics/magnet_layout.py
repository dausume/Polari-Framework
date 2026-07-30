"""
@module magnetics.magnet_layout

mag-4: the LAYOUT COMPILER — slot-matrix rows in, a solved
reluctance network + a priced bill-of-parts out. Flux paths are
DESIGNED by placing magnetic blocks + magnetic joints and WALLED by
plain ones; the network derives from the matrix, never hand-copied.

Lumped model (stated, not hidden): each block is a NODE; each joint
becomes three series branch elements — half of each adjacent block
(its material, length = half its dimension along the adjacency
axis, area = the contact face) + the mortar layer (its material,
the joint thickness). Corners lump each block as half-lengths per
joint — a standard segmented-core approximation; the validity
sentence rides every solve.

Coils: a wound placement must sit on a LIMB (exactly two joints) —
winding a junction block is ambiguous and refuses honestly. The MMF
inserts in series into the block's first joint branch.

Honesty:
- missing JointMortarAssignment for an actual adjacency = a
  SUGGESTION on the dry-fit report (the un-mortared joint IS the
  drift), never silent;
- an assignment between non-adjacent slots = a suggestion too;
- costing rides Section-A gates: theoretical block/mortar materials
  refuse pricing by name; density/dimension gaps refuse rather than
  guess; thickness priors carry their est flags.
"""

import json

from magnetics.magnet_analysis import gates_for, _named, _rows
from magnetics.magnetic_netlist import MU0


def _loads(row, attr, default):
    try:
        return json.loads(getattr(row, attr, '') or '')
    except ValueError:
        return default


def layout_rows(manager, layout_name):
    layout = _named(manager, 'BlockLayoutDefinition', layout_name)
    if layout is None:
        raise ValueError(f'no BlockLayoutDefinition named '
                         f'"{layout_name}"')
    placements = sorted(
        (p for p in _rows(manager, 'BlockPlacement')
         if getattr(p, 'layout_name', '') == layout_name),
        key=lambda p: getattr(p, 'name', ''))
    if not placements:
        raise ValueError(f'layout "{layout_name}" has no '
                         f'BlockPlacement rows')
    joints = [j for j in _rows(manager, 'JointMortarAssignment')
              if getattr(j, 'layout_name', '') == layout_name]
    return layout, placements, joints


def _slot(placement):
    s = _loads(placement, 'slot_json', {})
    return (int(s.get('x', 0)), int(s.get('y', 0)),
            int(s.get('z', 0)))


def _adjacency_axis(slot_a, slot_b):
    """0/1/2 for x/y/z unit adjacency, None otherwise."""
    deltas = [abs(a - b) for a, b in zip(slot_a, slot_b)]
    if sorted(deltas) == [0, 0, 1]:
        return deltas.index(1)
    return None


def _brick_dims(manager, placement):
    variant = _named(manager, 'BlockSizeVariant',
                     getattr(placement, 'variant_ref', ''))
    if variant is None:
        raise ValueError(
            f'placement "{getattr(placement, "name", "?")}" '
            f'references unknown variant '
            f'"{getattr(placement, "variant_ref", "")}"')
    dims = _loads(variant, 'dims_json', {})
    return variant, dims


def _block_volume(variant, dims):
    """v1 volume math per shape kind — refuses unknown shapes."""
    kind = getattr(variant, 'shape_kind', '')
    if kind in ('brick', 'half-brick', 'tooth', 'bearing-seat'):
        return dims['x_m'] * dims['y_m'] * dims['z_m']
    if kind == 'wedge':
        return 0.5 * dims['x_m'] * dims['y_m'] * dims['z_m']
    if kind in ('arc-segment', 'disk-sector'):
        import math
        r_in = dims.get('r_in_m', 0.0)
        frac = dims['angle_deg'] / 360.0
        return (math.pi * (dims['r_out_m'] ** 2 - r_in ** 2)
                * frac * dims['thick_m'])
    raise ValueError(f'no v1 volume math for shape kind "{kind}" '
                     f'(variant "{getattr(variant, "name", "?")}") '
                     f'— add it or pick a supported shape')


_AXIS_FACE = {0: ('y_m', 'z_m'), 1: ('x_m', 'z_m'),
              2: ('x_m', 'y_m')}
_AXIS_LEN = {0: 'x_m', 1: 'y_m', 2: 'z_m'}


def dry_fit_report(manager, layout_name):
    """Adjacency map + the drift suggestions: un-mortared
    adjacencies, assignments between non-adjacent placements."""
    _, placements, joints = layout_rows(manager, layout_name)
    by_name = {getattr(p, 'name', ''): p for p in placements}
    adjacencies = []
    for i, a in enumerate(placements):
        for b in placements[i + 1:]:
            axis = _adjacency_axis(_slot(a), _slot(b))
            if axis is not None:
                adjacencies.append(
                    (getattr(a, 'name', ''), getattr(b, 'name', ''),
                     axis))
    assigned = {}
    suggestions = []
    for j in joints:
        pair = frozenset((getattr(j, 'from_placement', ''),
                          getattr(j, 'to_placement', '')))
        match = next((adj for adj in adjacencies
                      if frozenset(adj[:2]) == pair), None)
        if match is None:
            suggestions.append({
                'knob': 'JointMortarAssignment',
                'action': f'joint "{getattr(j, "name", "?")}" pairs '
                          f'non-adjacent placements '
                          f'{sorted(pair)} — fix the slots or the '
                          f'joint'})
        else:
            assigned[pair] = j
    unmortared = [adj for adj in adjacencies
                  if frozenset(adj[:2]) not in assigned]
    for adj in unmortared:
        suggestions.append({
            'knob': 'JointMortarAssignment',
            'action': f'adjacency {adj[0]} <-> {adj[1]} has NO '
                      f'mortar assignment — assign a grade '
                      f'(magnetic or plain); an un-mortared joint '
                      f'is a dry-fit gap'})
    interlocks = {getattr(p, 'name', ''):
                  _loads(_brick_dims(manager, p)[0],
                         'interlock_json', [])
                  for p in placements}
    return {'ok': True, 'layout': layout_name,
            'placements': sorted(by_name),
            'adjacencies': [{'a': a, 'b': b, 'axis': 'xyz'[ax]}
                            for a, b, ax in adjacencies],
            'mortaredJoints': len(assigned),
            'interlocks': interlocks,
            'suggestions': suggestions}


def generate_network(manager, layout_name):
    """Layout rows -> mag-3-shaped element dicts + a solve, without
    persisting rows: blocks are nodes, joints expand to
    half-block/mortar/half-block series elements, wound limbs gain
    an mmf-coil in series."""
    _, placements, joints = layout_rows(manager, layout_name)
    by_name = {getattr(p, 'name', ''): p for p in placements}
    report = dry_fit_report(manager, layout_name)

    joint_count = {}
    valid_joints = []
    for j in joints:
        a = by_name.get(getattr(j, 'from_placement', ''))
        b = by_name.get(getattr(j, 'to_placement', ''))
        if a is None or b is None:
            continue
        axis = _adjacency_axis(_slot(a), _slot(b))
        if axis is None:
            continue
        valid_joints.append((j, a, b, axis))
        for p in (a, b):
            key = getattr(p, 'name', '')
            joint_count[key] = joint_count.get(key, 0) + 1

    elements = []
    nodes = set()

    def node_of(placement):
        n = f'blk-{getattr(placement, "name", "?")}'
        nodes.add(n)
        return n

    coil_joint = {}
    for p in placements:
        coil = _loads(p, 'coil_json', {})
        if not coil.get('turns'):
            continue
        pname = getattr(p, 'name', '')
        if joint_count.get(pname, 0) != 2:
            raise ValueError(
                f'wound placement "{pname}" has '
                f'{joint_count.get(pname, 0)} joints — v1 winds '
                f'LIMBS (exactly two joints); winding a junction '
                f'block is ambiguous')
        first = next(jt for jt in valid_joints
                     if pname in (getattr(jt[0], 'from_placement',
                                          ''),
                                  getattr(jt[0], 'to_placement',
                                          '')))
        coil_joint[getattr(first[0], 'name', '')] = (pname, coil)

    for j, a, b, axis in valid_joints:
        jname = getattr(j, 'name', '?')
        _, dims_a = _brick_dims(manager, a)
        _, dims_b = _brick_dims(manager, b)
        area = getattr(j, 'contact_area_m2', 0.0) or 0.0
        if not area:
            fa, fb = _AXIS_FACE[axis]
            area = min(dims_a[fa] * dims_a[fb],
                       dims_b[fa] * dims_b[fb])
        node_a, node_b = node_of(a), node_of(b)
        mid1, mid2 = f'{jname}-m1', f'{jname}-m2'
        nodes.update((mid1, mid2))
        chain = [
            {'name': f'{jname}-half-{getattr(a, "name", "?")}',
             'kind': 'core-segment',
             'params_json': json.dumps({
                 'length_m': dims_a[_AXIS_LEN[axis]] / 2.0,
                 'area_m2': area,
                 'material_ref': getattr(a, 'material_ref', '')}),
             'nodes_json': json.dumps([node_a, mid1])},
            {'name': f'{jname}-mortar',
             'kind': 'core-segment',
             'params_json': json.dumps({
                 'length_m': getattr(j, 'thickness_m', 0.001),
                 'area_m2': area,
                 'material_ref': getattr(j, 'mortar_ref', '')}),
             'nodes_json': json.dumps([mid1, mid2])},
            {'name': f'{jname}-half-{getattr(b, "name", "?")}',
             'kind': 'core-segment',
             'params_json': json.dumps({
                 'length_m': dims_b[_AXIS_LEN[axis]] / 2.0,
                 'area_m2': area,
                 'material_ref': getattr(b, 'material_ref', '')}),
             'nodes_json': json.dumps([mid2, node_b])},
        ]
        if jname in coil_joint:
            # series insert: node_a -[half A]- coil_node -[coil]-
            # mid1 -[mortar]- mid2 -[half B]- node_b.
            pname, coil = coil_joint[jname]
            coil_node = f'{jname}-coil'
            nodes.add(coil_node)
            chain[0]['nodes_json'] = json.dumps([node_a, coil_node])
            chain.insert(1, {
                'name': f'coil-{pname}', 'kind': 'mmf-coil',
                'params_json': json.dumps({
                    'turns': coil['turns'],
                    'amps': coil.get('amps', 0.0)}),
                'nodes_json': json.dumps([coil_node, mid1])})
        elements.extend(chain)
    return {'elements': elements, 'nodes': sorted(nodes),
            'dryFit': report}


def solve_layout(manager, layout_name):
    """Generate + solve through the mag-3 solver on a VIRTUAL
    overlay manager (generated rows never persist)."""
    import types

    from magnetics.magnetic_netlist import solve_network
    try:
        generated = generate_network(manager, layout_name)
    except ValueError as exc:
        return {'ok': False, 'refusal': str(exc)}
    nodes = generated['nodes']
    reference = nodes[0] if nodes else '0'
    virtual_name = f'__layout__{layout_name}'
    circuit = types.SimpleNamespace(
        name=virtual_name, description='generated from layout',
        analyses_json='[{"type": "op"}]', notes='')
    element_rows = {}
    for spec in generated['elements']:
        wired = json.loads(spec['nodes_json'])
        wired = [('0' if n == reference else n) for n in wired]
        element_rows[spec['name']] = types.SimpleNamespace(
            name=spec['name'], circuit_name=virtual_name,
            kind=spec['kind'], params_json=spec['params_json'],
            nodes_json=json.dumps(wired), description='')
    node_rows = {
        f'{virtual_name}-{n}': types.SimpleNamespace(
            name=f'{virtual_name}-{n}', circuit_name=virtual_name,
            node=('0' if n == reference else n),
            is_reference=(n == reference), description='')
        for n in nodes}
    overlay = types.SimpleNamespace()
    overlay.objectTables = {
        **getattr(manager, 'objectTables', {}),
        'MagneticCircuitDefinition': {virtual_name: circuit},
        'MagneticElementDefinition': element_rows,
        'FluxNodeDefinition': node_rows,
    }
    try:
        solved = solve_network(overlay, virtual_name)
    except ValueError as exc:
        return {'ok': False, 'refusal': str(exc),
                'dryFit': generated['dryFit']}
    solved['layout'] = layout_name
    solved['referenceNode'] = f'blk node "{reference}" grounded '
    solved['generatedFrom'] = {
        'placements': len(generated['dryFit']['placements']),
        'elements': len(generated['elements'])}
    solved['dryFit'] = generated['dryFit']
    solved['validity'] += ('; lumped segmented-core model — blocks '
                           'as nodes, half-lengths per joint, '
                           'corners approximate')
    return solved


def layout_cost(manager, layout_name, policy_name=''):
    """Per-block + per-joint bill of parts: volume x density x
    effective $/kg through the supplychain cascade — gates honored
    (theoretical materials refuse by name), estimates flagged."""
    try:
        _, placements, joints = layout_rows(manager, layout_name)
    except ValueError as exc:
        return {'ok': False, 'refusal': str(exc)}
    try:
        from supplychain.formula_analysis import effective_unit_price
    except ImportError:
        return {'ok': False,
                'refusal': 'supplychain module not enabled — '
                           'layout costing rides its cascade'}

    def priced(material_ref, kg, label):
        opt = _named(manager, 'MagneticMaterialOption', material_ref)
        if opt is None:
            return None, {'part': label,
                          'refusal': f'unknown material '
                                     f'"{material_ref}"'}
        gates = gates_for(manager, opt)
        if not gates['costing']['allowed']:
            return None, {'part': label,
                          'refusal': gates['costing']['refusal'],
                          'suggestion': gates['costing'].get(
                              'suggestion')}
        item = getattr(opt, 'item_ref', '')
        eff = effective_unit_price(manager, item,
                                   policy_name=policy_name)
        if eff is None:
            return None, {'part': label,
                          'refusal': f'no cited-or-makeable price '
                                     f'for "{item}"'}
        return {'part': label, 'material': material_ref,
                'kg': round(kg, 6),
                'usdPerKg': eff['normalized'], 'via': eff['via'],
                'usd': round(kg * eff['normalized'], 4),
                'isEstimate': bool(eff.get('isEstimate'))}, None

    rows, refusals = [], []
    total, any_est = 0.0, False
    for p in placements:
        variant, dims = _brick_dims(manager, p)
        try:
            volume = _block_volume(variant, dims)
        except (ValueError, KeyError) as exc:
            refusals.append({'part': getattr(p, 'name', '?'),
                             'refusal': str(exc)})
            continue
        opt = _named(manager, 'MagneticMaterialOption',
                     getattr(p, 'material_ref', ''))
        props = _loads(opt, 'properties_json', {}) if opt else {}
        density = (props.get('density_kg_m3') or {}).get('value')
        if density is None:
            refusals.append({
                'part': getattr(p, 'name', '?'),
                'refusal': f'material '
                           f'"{getattr(p, "material_ref", "")}" '
                           f'has no density — kg would be a guess'})
            continue
        row, refusal = priced(getattr(p, 'material_ref', ''),
                              volume * density,
                              getattr(p, 'name', '?'))
        if refusal:
            refusals.append(refusal)
        else:
            rows.append({**row, 'kind': 'block',
                         'volumeM3': round(volume, 9)})
            total += row['usd']
            any_est = any_est or row['isEstimate']
    by_name = {getattr(p, 'name', ''): p for p in placements}
    for j in joints:
        a = by_name.get(getattr(j, 'from_placement', ''))
        b = by_name.get(getattr(j, 'to_placement', ''))
        if a is None or b is None:
            continue
        axis = _adjacency_axis(_slot(a), _slot(b))
        if axis is None:
            continue
        area = getattr(j, 'contact_area_m2', 0.0) or 0.0
        if not area:
            _, dims_a = _brick_dims(manager, a)
            _, dims_b = _brick_dims(manager, b)
            fa, fb = _AXIS_FACE[axis]
            area = min(dims_a[fa] * dims_a[fb],
                       dims_b[fa] * dims_b[fb])
        volume = area * getattr(j, 'thickness_m', 0.001)
        opt = _named(manager, 'MagneticMaterialOption',
                     getattr(j, 'mortar_ref', ''))
        props = _loads(opt, 'properties_json', {}) if opt else {}
        density = (props.get('density_kg_m3') or {}).get('value')
        if density is None:
            refusals.append({
                'part': getattr(j, 'name', '?'),
                'refusal': f'mortar '
                           f'"{getattr(j, "mortar_ref", "")}" has '
                           f'no density'})
            continue
        row, refusal = priced(getattr(j, 'mortar_ref', ''),
                              volume * density,
                              getattr(j, 'name', '?'))
        if refusal:
            refusals.append(refusal)
        else:
            est = bool(getattr(j, 'thickness_is_estimate', True))
            rows.append({**row, 'kind': 'joint',
                         'volumeM3': round(volume, 12),
                         'thicknessIsEstimate': est})
            total += row['usd']
            any_est = any_est or est or row['isEstimate']
    return {'ok': True, 'layout': layout_name, 'parts': rows,
            'refusals': refusals,
            'totalUsd': round(total, 4), 'anyEstimate': any_est,
            'excluded': 'mold amortization + labor hours ride the '
                        'biz-1 planner (workflow rows), not this '
                        'bill; kiln/cure energy excluded-loud as '
                        'always'}
