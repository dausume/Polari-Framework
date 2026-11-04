"""@module mech.objects.assembly._shared — what the assembly row classes share (constants, helpers); mxc-2."""
import json

#: Joint frame convention (every entry below): the joint's z axis is
#: THE joint axis (revolute pin, slider rail, screw/cylinder axis,
#: grid normal); x and y span the mating plane. Axis labels are the
#: composition DOF_AXES ('tx','ty','tz','rx','ry','rz') so a joint's
#: free set and an InterfaceDefinition.dof_removed_json are exact
#: complements of one another.
DOF_AXES = ('tx', 'ty', 'tz', 'rx', 'ry', 'rz')

#: FreeCAD 1.x Assembly JointTypes (so export is 1:1) plus 'grid' —
#: Gridfinity cell seating, which FreeCAD has no name for (exported as
#: fixed when magnets hold it, slider-on-z when not).
JOINT_KINDS = ('fixed', 'revolute', 'cylindrical', 'slider', 'ball',
               'distance', 'parallel', 'perpendicular', 'angle',
               'rack_pinion', 'screw', 'gears', 'belt', 'grid')

#: kind -> the DOF the joint leaves FREE between its two bodies, in
#: the joint frame. 'distance' removes the separation along z;
#: 'parallel' removes the two tilts (rx, ry); 'perpendicular' and
#: 'angle' pin ONE angle — taken as rx (the tilt about the common
#: normal) by convention. The four COUPLED kinds (rack_pinion, screw,
#: gears, belt) list the axes they tie together; the coupling itself
#: is one more equation, counted in JOINT_COUPLING, not an axis.
JOINT_DOF = {
    'fixed':         (),
    'revolute':      ('rz',),
    'cylindrical':   ('tz', 'rz'),
    'slider':        ('tz',),
    'ball':          ('rx', 'ry', 'rz'),
    'distance':      ('tx', 'ty', 'rx', 'ry', 'rz'),
    'parallel':      ('tx', 'ty', 'tz', 'rz'),
    'perpendicular': ('tx', 'ty', 'tz', 'ry', 'rz'),
    'angle':         ('tx', 'ty', 'tz', 'ry', 'rz'),
    # secondary joints: each gear/rack/pulley is already held by its
    # own revolute or slider; this joint adds ONLY the ratio equation
    'rack_pinion':   DOF_AXES,
    'screw':         ('tz', 'rz'),
    'gears':         DOF_AXES,
    'belt':          DOF_AXES,
    # Gridfinity: the cell profile fixes tx, ty, rz and (seated) the
    # tilts; tz (lift-off) stays free until magnets or weight hold it.
    'grid':          ('tz',),
}

#: kind -> number of ratio equations tying the free axes together
#: (a screw's tz and rz are ONE DOF, not two).
JOINT_COUPLING = {'rack_pinion': 1, 'screw': 1, 'gears': 1, 'belt': 1}

#: Kinds whose free axes are DESIGNED motion (a slider is meant to
#: slide); every other free axis on a body is unintended play.
MOTION_KINDS = ('revolute', 'cylindrical', 'slider', 'ball',
                'distance', 'parallel', 'perpendicular', 'angle',
                'rack_pinion', 'screw', 'gears', 'belt')

ASSEMBLY_KINDS = ('desk', 'drawer_cassette', 'frame', 'clock_movement',
                  'printer', 'generic')
CONTACT_KINDS = ('sliding', 'rolling', 'static')
CONFLICT_KINDS = ('interference', 'thread_engagement_short',
                  'clearance_hole_small', 'slide_overload',
                  'cantilever_tip', 'grid_mismatch', 'under_constrained',
                  'over_constrained', 'wrong_pairing')
CONFLICT_SEVERITIES = ('error', 'warning', 'info')
#: MechPartInstance.quantity_role: 'body' = a rigid body in the DOF
#: graph; 'fastener' = hardware OF a joint (screw, T-nut, magnet) —
#: listed on the joint's fastener_refs_json, never a body of its own.
INSTANCE_ROLES = ('body', 'fastener')

#: Feature roles that may pair across a joint (plan §3.2: a joint is
#: valid when the KEY matches and the ROLES pair).
ROLE_PAIRS = (('male', 'female'), ('channel', 'rider'), ('cell', 'cell'),
              ('plane', 'plane'), ('socket', 'socket'))


def loads(text, default):
    """Lenient JSON: '' / None / garbage -> default (never raises)."""
    if isinstance(text, (dict, list)):
        return text
    try:
        return json.loads(text or '')
    except (TypeError, ValueError):
        return default


def joint_free_axes(joint):
    """The joint's free axes: its explicit dof_json when set ('[]' is
    an explicit EMPTY set — a grid joint held by magnets), else the
    kind's default. Always a tuple ordered as DOF_AXES."""
    get = joint.get if isinstance(joint, dict) else \
        (lambda k, d='': getattr(joint, k, d))
    kind = get('kind', '')
    raw = get('dof_json', '') or ''
    if isinstance(raw, (list, tuple)):
        free = set(raw)
    elif isinstance(raw, str) and raw.strip() in ('', 'null'):
        free = set(JOINT_DOF.get(kind, ()))
    else:
        parsed = loads(raw, None)
        free = (set(parsed) if isinstance(parsed, list)
                else set(JOINT_DOF.get(kind, ())))
    return tuple(a for a in DOF_AXES if a in free)


def complement(axes):
    """DOF_AXES minus `axes`, in DOF_AXES order."""
    axes = set(axes or ())
    return tuple(a for a in DOF_AXES if a not in axes)


def roles_pair(role_a, role_b):
    return (role_a, role_b) in ROLE_PAIRS or (role_b, role_a) in ROLE_PAIRS
