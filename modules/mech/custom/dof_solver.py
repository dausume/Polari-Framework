"""
@module mech.custom.dof_solver

mxc-2: free degrees of freedom per instance, from its joints.

WHAT THIS IS — a Grübler/Kutzbach COUNT over rigid groups. Every
joint on one body pair collapses to one relative constraint (axis
labels taken AS LABELLED in the joint frame); pairs that remove all
six merge into one rigid group; from the ground group a breadth-
first walk accumulates each group's free axes down its chain
(a drawer on a slider keeps tz even though a baseplate is fixed
INTO it — the fix is relative, not to ground). Assembly mobility =
the sum over tree edges of (free axes − ratio couplings): the number
of independent joint coordinates (screw, gears, belt, rack_pinion
count their tied axes as one).

WHAT THIS IS NOT — a rank test. It cannot see:
- parallel or coincident axes (two revolutes on one line are a
  hinge, the count says 'ball-ish');
- geometric singularities, or whether a slider's tz on one joint is
  the same world direction as another's;
- a single-slide drawer's droop: the count says 'free: tz', the
  drawer also tips about the slide (a stiffness question, mxc-4);
- whether a closed LOOP is consistent: a second path to a group
  already reached is listed under `loops` and not counted (the
  first, shortest path wins). Loops of full fixes (a bracket fixed
  to two beams) merge into one rigid group and are silent — that is
  how frames are built; a MOTION joint whose bodies are already one
  rigid group through other fixes IS flagged over_constrained.

What it DOES flag, honestly:
- under_constrained: a non-ground body with free axes beyond what
  its MOTION joints are designed to leave free (a floating body; a
  bracket on ONE screw — the rotation about the screw axis is held by
  friction only, a single fastener is a pivot); a body not connected
  to ground through valid joints;
- over_constrained: two or more joints on the SAME body pair where
  one alone already removes all six (fixed + fixed, fixed + press,
  fixed + revolute) — 'parallel fixed joints', reported rather than
  silently unioned; redundant NON-full pairs (two coaxial revolutes =
  two bearings on a shaft) go to `redundant_pairs` as information,
  not a conflict.

Fasteners: instances with quantity_role 'fastener' are not bodies.
A joint lists the hardware that realises it in fastener_refs_json;
ONE fastener at one point fixes five DOF (rz about its axis is
friction-held); two or more such point joints between the same pair
at distinct positions fix all six. 'grid' joints are point joints
too (four magnet seats on one bin are one seating, not four fixes).

@consumers mech.custom.fit_checks, mech.mech_assembly_selftest,
mech.mech_api (mxc-6)
"""

import json

from composition.custom.data_refs import named, rows
from mech.objects.assembly._shared import (
    DOF_AXES, JOINT_COUPLING, JOINT_KINDS, MOTION_KINDS, complement,
    joint_free_axes, loads,
)

#: Joint kinds aggregated PER BODY PAIR as point fixes (see module
#: docstring) rather than standing alone.
POINT_KINDS = ('grid',)

NOTE = ('a Grübler/Kutzbach COUNT over rigid groups with axes taken as '
        'labelled in each joint frame — NOT a rank test: parallel axes, '
        'singularities, single-slide droop and the consistency of closed '
        'loops are invisible to it (loops are listed, not solved); '
        'parallel full fixes on one body pair are reported as '
        'over_constrained, not hidden')


def _g(obj, key, default=''):
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _assembly_rows(manager, assembly_name):
    insts = [i for i in rows(manager, 'MechPartInstance')
             if _g(i, 'assembly_ref') == assembly_name]
    joints = [j for j in rows(manager, 'MechJoint')
              if _g(j, 'assembly_ref') == assembly_name]
    return insts, joints


def validate_joint(joint, instances):
    """(ok, reason): both instances exist, kind known, fasteners
    resolve to fastener instances. Feature key/role pairing is
    fit_checks' job (it needs the catalogue)."""
    kind = _g(joint, 'kind')
    if kind not in JOINT_KINDS:
        return False, f'unknown joint kind "{kind}"'
    for side in ('a', 'b'):
        inst = _g(joint, f'instance_{side}')
        if inst not in instances:
            return False, f'instance_{side} "{inst}" is not in the assembly'
    for f in loads(_g(joint, 'fastener_refs_json', '[]'), []):
        if f not in instances:
            return False, f'fastener "{f}" is not in the assembly'
        if _g(instances[f], 'quantity_role', 'body') != 'fastener':
            return False, (f'fastener "{f}" has quantity_role '
                           f'"{_g(instances[f], "quantity_role")}", '
                           f'not fastener')
    if _g(joint, 'valid', True) is False and _g(joint, 'invalid_reason'):
        return False, _g(joint, 'invalid_reason')
    return True, ''


def _positions(joint):
    """How many fastening POSITIONS a joint stands for: 1 (a joint is
    one location; its fastener list is the hardware AT that location
    — screw + T-nut), unless limits_json says 'positions': n (a
    flange modelled as one joint with its bolt circle)."""
    lim = loads(_g(joint, 'limits_json', '{}'), {})
    try:
        return max(int(lim.get('positions', 1)), 1)
    except (TypeError, ValueError, AttributeError):
        return 1


def _is_point(joint):
    """A point fix: a grid seat, or a fixed joint realised by
    fasteners at ONE position (a pivot until a second position
    fixes rz). A fixed joint with no fasteners (press, adhesive,
    monolithic) or with 2+ positions is a full fix on its own."""
    kind = _g(joint, 'kind')
    fasteners = loads(_g(joint, 'fastener_refs_json', '[]'), [])
    return kind in POINT_KINDS or (kind == 'fixed' and bool(fasteners)
                                   and _positions(joint) == 1)


def _origin_key(joint):
    """Where the point joint sits, so two fasteners at the SAME spot
    do not count as two positions. Uses the joint's limits_json
    'origin' when present, else the feature pair."""
    lim = loads(_g(joint, 'limits_json', '{}'), {})
    if isinstance(lim, dict) and lim.get('origin') is not None:
        return json.dumps(lim['origin'])
    return f'{_g(joint, "feature_a")}|{_g(joint, "feature_b")}'


def _pair_aggregate(js):
    """Collapse every joint on one body pair into ONE relative
    constraint: removed axes, designed-free axes, ratio couplings,
    friction-held axes, and the over-constraint verdict."""
    point_js = [j for j in js if _is_point(j)]
    full_js = [j for j in js if not _is_point(j)]
    removed, designed, friction = set(), set(), set()
    coupling = 0
    detail = []
    if point_js:
        union = set()
        for j in point_js:
            free = set(joint_free_axes(j))
            rm = set(DOF_AXES) - free
            if _g(j, 'kind') == 'fixed':
                rm.discard('rz')          # one fastener = a pivot
            else:                         # grid: lift-off is DESIGNED
                designed |= free
            union |= rm
        fastener_points = [j for j in point_js if _g(j, 'kind') == 'fixed']
        positions = {_origin_key(j) for j in fastener_points}
        if fastener_points and len(positions) >= 2:
            union.add('rz')
        elif fastener_points and 'rz' not in union and not full_js:
            friction.add('rz')
        removed |= union
        detail.append({'joints': [_g(j, 'name') for j in point_js],
                       'removed': sorted(union, key=DOF_AXES.index),
                       'positions': len(positions),
                       'aggregate': 'point fixes on one pair'})
    full_six = []
    for j in full_js:
        free = set(joint_free_axes(j))
        rm = set(DOF_AXES) - free
        if not free:
            full_six.append(j)
        removed |= rm
        if _g(j, 'kind') in MOTION_KINDS:
            designed |= free
            coupling += JOINT_COUPLING.get(_g(j, 'kind'), 0)
        detail.append({'joint': _g(j, 'name'), 'kind': _g(j, 'kind'),
                       'removed': sorted(rm, key=DOF_AXES.index)})
    over = None
    redundant = None
    if full_six and len(js) > 1:
        over = (f'{_g(full_six[0], "name")} alone removes all six DOF '
                f'between these bodies; the other {len(js) - 1} joint(s) '
                f'on the same pair are redundant constraints (parallel '
                f'fixes)')
    elif len(full_js) > 1:
        each = [len(set(DOF_AXES) - set(joint_free_axes(j))) for j in full_js]
        if len(removed) < sum(each):
            redundant = ('redundant but not a full fix (two bearings on '
                         'one shaft) — information, not a conflict')
    free = tuple(a for a in DOF_AXES if a not in removed)
    return {'joints': [_g(j, 'name') for j in js], 'removed': removed,
            'free': free, 'designed': designed & set(free),
            'friction_held': friction & set(free), 'coupling': coupling,
            'count': max(len(free) - coupling, 0), 'detail': detail,
            'over': over, 'redundant': redundant}


def solve_dof(assembly, manager):
    """-> {instances: {name: {free, free_count, designed_free,
    unintended, group, path}}, groups, assembly_mobility,
    under_constrained, over_constrained, redundant_pairs, loops,
    invalid_joints, note}.

    The walk: (1) every joint on one body pair collapses to one
    relative constraint; (2) pairs that remove all six merge their
    bodies into one RIGID GROUP (a bracket on two screws and its
    beam are one body for the count); (3) from the ground group,
    breadth-first over the remaining constraints, a group's free
    axes = its parent's free axes + the constraint's free axes
    (relative freedom ACCUMULATES down a chain); (4) assembly
    mobility = the sum over tree edges of (free axes − couplings) =
    the number of independent joint coordinates. A second path to a
    group already reached is a closed LOOP: the count keeps the
    first (shortest) path and lists the loop — a count cannot say
    whether a loop is consistent."""
    a_name = _g(assembly, 'name')
    ground = _g(assembly, 'ground_instance')
    insts, joints = _assembly_rows(manager, a_name)
    by_name = {_g(i, 'name'): i for i in insts}
    bodies = [n for n, i in by_name.items()
              if _g(i, 'quantity_role', 'body') != 'fastener']
    if not bodies:
        return {'ok': False, 'assembly': a_name,
                'refusal': 'no body instances in the assembly'}
    if ground and ground not in by_name:
        return {'ok': False, 'assembly': a_name,
                'refusal': f'ground_instance "{ground}" is not an '
                           f'instance of the assembly'}
    if not ground:
        return {'ok': False, 'assembly': a_name,
                'refusal': 'no ground_instance — every freedom is '
                           'relative to something; name the fixed body'}

    invalid = []
    pairs = {}
    for j in joints:
        ok, why = validate_joint(j, by_name)
        if not ok:
            invalid.append({'joint': _g(j, 'name'), 'why': why})
            continue
        a, b = _g(j, 'instance_a'), _g(j, 'instance_b')
        if a not in bodies or b not in bodies:
            invalid.append({'joint': _g(j, 'name'),
                            'why': 'joint touches a fastener instance '
                                   'as a body'})
            continue
        if a == b:
            invalid.append({'joint': _g(j, 'name'),
                            'why': 'both ends on one instance (a '
                                   'single-body boundary is not a '
                                   'kinematic joint)'})
            continue
        pairs.setdefault(frozenset((a, b)), []).append(j)

    agg = {pair: _pair_aggregate(js) for pair, js in pairs.items()}
    over = [{'instances': sorted(pair), 'joints': ag['joints'],
             'why': ag['over']} for pair, ag in agg.items() if ag['over']]
    redundant = [{'instances': sorted(pair), 'joints': ag['joints'],
                  'note': ag['redundant']}
                 for pair, ag in agg.items() if ag['redundant']]

    # (2) rigid groups: union-find over full fixes
    parent = {b: b for b in bodies}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for pair, ag in agg.items():
        if not ag['free']:
            a, b = tuple(pair)
            parent[find(a)] = find(b)
    group_of = {b: find(b) for b in bodies}
    members = {}
    for b, g in group_of.items():
        members.setdefault(g, []).append(b)
    # a NON-full constraint whose two bodies are already one rigid
    # group (through other joints) contradicts that rigidity
    edges = {}
    for pair, ag in agg.items():
        if not ag['free']:
            continue
        a, b = tuple(pair)
        ga, gb = group_of[a], group_of[b]
        if ga == gb:
            over.append({'instances': sorted(pair), 'joints': ag['joints'],
                         'why': f'{ag["joints"]} leaves {list(ag["free"])} '
                                f'free, but its bodies are already one '
                                f'rigid group through other full fixes '
                                f'{sorted(members[ga])} — a loop over-'
                                f'constraint'})
            continue
        key = frozenset((ga, gb))
        if key in edges:          # two parallel constraints between groups
            edges[key]['parallel'].append(ag)
        else:
            edges[key] = {'agg': ag, 'parallel': []}

    # (3) breadth-first from ground
    g0 = group_of[ground]
    state = {g0: {'free': (), 'count': 0, 'unintended': (),
                  'friction': (), 'path': []}}
    order = [g0]
    loops = []
    mobility = 0
    i = 0
    while i < len(order):
        g = order[i]
        i += 1
        for key, e in edges.items():
            if g not in key:
                continue
            other = next(x for x in key if x != g)
            ag = e['agg']
            if other in state:
                if state[g]['path'] and \
                        state[g]['path'][-1] == ag['joints']:
                    continue          # the edge THIS group came in on
                loops.append({'groups': [sorted(members[g]),
                                         sorted(members[other])],
                              'joints': ag['joints'],
                              'note': 'closed loop: the count keeps the '
                                      'first path; consistency of the '
                                      'loop is beyond a count'})
                continue
            par = state[g]
            free = tuple(a for a in DOF_AXES
                         if a in set(par['free']) | set(ag['free']))
            unint = tuple(a for a in DOF_AXES
                          if a in set(par['unintended'])
                          | (set(ag['free']) - ag['designed']))
            fric = tuple(a for a in DOF_AXES
                         if a in set(par['friction']) | ag['friction_held'])
            state[other] = {'free': free,
                            'count': par['count'] + ag['count'],
                            'unintended': unint, 'friction': fric,
                            'path': par['path'] + [ag['joints']]}
            mobility += ag['count']
            order.append(other)
            for p in e['parallel']:
                loops.append({'groups': [sorted(members[g]),
                                         sorted(members[other])],
                              'joints': p['joints'],
                              'note': 'a second constraint between the '
                                      'same two rigid groups — a loop; '
                                      'not counted'})

    result_inst = {}
    under = []
    touched = {b for pair in pairs for b in pair}
    for b in bodies:
        g = group_of[b]
        st = state.get(g)
        if b == ground or (st is not None and g == g0):
            result_inst[b] = {'free': [], 'free_count': 0,
                              'ground': True, 'designed_free': [],
                              'unintended': [], 'group': sorted(members[g]),
                              'path': []}
            continue
        if st is None:
            free = list(DOF_AXES)
            result_inst[b] = {'free': free, 'free_count': 6,
                              'ground': False, 'designed_free': [],
                              'unintended': free,
                              'group': sorted(members[g]), 'path': []}
            why = ('floating: no valid joint touches this body'
                   if b not in touched else
                   'not connected to the ground instance through any '
                   'valid joint')
            under.append({'instance': b, 'free': free,
                          'unintended': free, 'why': why})
            continue
        free = list(st['free'])
        unint = list(st['unintended'])
        result_inst[b] = {'free': free, 'free_count': st['count'],
                          'ground': False,
                          'designed_free': [a for a in free
                                            if a not in unint],
                          'unintended': unint,
                          'group': sorted(members[g]),
                          'path': st['path']}
        if unint:
            why = (f'free {unint} not designed by any motion joint'
                   + ('; rz about a SINGLE fastener is friction-held '
                      '— add a second fastener or an anti-rotation '
                      'feature' if st['friction'] else ''))
            under.append({'instance': b, 'free': free,
                          'unintended': unint, 'why': why})
    return {
        'ok': True, 'assembly': a_name, 'ground': ground,
        'instances': result_inst,
        'groups': [sorted(m) for m in members.values()],
        'assembly_mobility': mobility,
        'under_constrained': under, 'over_constrained': over,
        'redundant_pairs': redundant, 'loops': loops,
        'invalid_joints': invalid,
        'joint_count': len(joints),
        'valid_joint_count': len(joints) - len(invalid),
        'note': NOTE,
    }


def dof_conflicts(result):
    """MechConflict dicts for the solver's findings (under/over
    constrained + invalid joints as wrong_pairing)."""
    out = []
    a = result.get('assembly', '')
    if not result.get('ok'):
        return out
    for u in result['under_constrained']:
        out.append({'name': f'{a}:under:{u["instance"]}',
                    'assembly_ref': a, 'kind': 'under_constrained',
                    'severity': 'error',
                    'detail_json': json.dumps(u),
                    'notes': result['note']})
    for o in result['over_constrained']:
        out.append({'name': f'{a}:over:{"+".join(o["instances"])}',
                    'assembly_ref': a, 'kind': 'over_constrained',
                    'severity': 'warning',
                    'detail_json': json.dumps(o),
                    'notes': result['note']})
    for i in result['invalid_joints']:
        out.append({'name': f'{a}:invalid:{i["joint"]}',
                    'assembly_ref': a, 'kind': 'wrong_pairing',
                    'severity': 'error',
                    'detail_json': json.dumps(i),
                    'notes': 'joint excluded from the DOF count'})
    return out


def solve_dof_by_name(manager, assembly_name):
    asm = named(manager, 'MechAssembly', assembly_name)
    if asm is None:
        return {'ok': False, 'refusal': f'no MechAssembly "{assembly_name}"'}
    return solve_dof(asm, manager)
