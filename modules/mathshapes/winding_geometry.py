"""
@module mathshapes.winding_geometry

ws-1 (Dustin 2026-07-31): "define the actual wire winding via a
matrix equation ... based on the radius, the center of the stator
and its orientation and the orientation of the exiting wires, and
the fineness of the wire; its turns should be tunable. We must
ensure the parameters being tuned are coherent and can form a math
object. The actual winding should be able to be observed."

THE MATH OBJECT — a wound coil is fully determined by:

    C        center of the winding (3-vector)
    axis     bobbin axis (3-vector, normalized)
    exit     the exiting-wire direction; orthogonalized against the
             axis it fixes the winding PHASE (theta = 0 points at
             the exit) so the leads leave where the drawing says
    r0       bore radius (where the first layer sits)
    d        wound wire diameter — the FINENESS (bare + enamel)
    N        turns
    L        axial window length available

Everything else DERIVES: turns per layer tpl = floor(L/d), layers,
outer radius, per-turn radius r_k = r0 + d(k + 1/2), wire length.
`winding_coherence` refuses incoherent tunings (zero axis, exit
parallel to axis, wire too fat for the window...) naming the knob —
a refusal here is what "cannot form a math object" means.

THE MATRIX EQUATION (world points from the parameter t in turns):

    p(t) = [x_local(t), y_local(t), z_local(t)] · Mᵀ + C
    x_local = r(t) cos(2πt + φ)      r(t) = r0 + d(⌊t/tpl⌋ + ½)
    y_local = r(t) sin(2πt + φ)
    z_local = ±(L/2 − d/2 − d·u)     u = t mod tpl (zigzag/layer)

with M = [u v w] the orthonormal frame from (axis, exit). It is
emitted as a MatrixEquationDefinition spec (numpy expr + bindings)
and `winding_points` implements the SAME formula — the parity
selftest proves the drawn object IS the equation.

@consumers mathshapes.shape_analysis (family 'winding'),
motors.motor_shapes (the M0 v2 coil), selftest_shapes
"""

import math

MAX_MESH_POINTS = 42000


def _vec(v, name, refusals):
    try:
        x = [float(c) for c in v]
        if len(x) != 3:
            raise ValueError
        return x
    except Exception:
        refusals.append(f'{name} must be a 3-vector, got {v!r}')
        return None


def _norm(v):
    return math.sqrt(sum(c * c for c in v))


def _unit(v):
    n = _norm(v)
    return [c / n for c in v] if n else v


def _cross(a, b):
    return [a[1] * b[2] - a[2] * b[1],
            a[2] * b[0] - a[0] * b[2],
            a[0] * b[1] - a[1] * b[0]]


def winding_coherence(params):
    """Validate a winding's tunable parameters into the MATH OBJECT
    (or refuse, naming every incoherence — nothing silently
    clamped). Returns {'ok': True, 'object': {...}, 'derived': ...}
    or {'ok': False, 'refusals': [...]}.
    """
    refusals = []
    center = _vec(params.get('center', [0, 0, 0]), 'center',
                  refusals)
    axis = _vec(params.get('axis', [0, 0, 1]), 'axis', refusals)
    exit_dir = _vec(params.get('exit_dir', [0, -1, 0]), 'exit_dir',
                    refusals)
    r0 = float(params.get('bore_radius', 0) or 0)
    d = float(params.get('wire_diameter', 0) or 0)
    turns = params.get('turns', 0)
    length = float(params.get('window_length', 0) or 0)
    phase = float(params.get('phase', 0.0) or 0.0)
    if axis is not None and _norm(axis) < 1e-12:
        refusals.append('axis is the zero vector — a winding needs '
                        'an orientation')
        axis = None
    if r0 <= 0:
        refusals.append(f'bore_radius must be > 0 (got {r0})')
    if d <= 0:
        refusals.append(f'wire_diameter (the fineness) must be > 0 '
                        f'(got {d})')
    if not (isinstance(turns, (int, float)) and turns >= 1
            and float(turns).is_integer()):
        refusals.append(f'turns must be a whole number >= 1 '
                        f'(got {turns!r})')
    if length <= 0:
        refusals.append(f'window_length must be > 0 (got {length})')
    if d > 0 and length > 0 and d > length:
        refusals.append(f'wire_diameter {d} exceeds the window '
                        f'{length} — not one turn fits; coarsen the '
                        f'window or refine the wire')
    if axis is not None and exit_dir is not None:
        w = _unit(axis)
        # Gram-Schmidt: the exit direction fixes theta=0 in the
        # winding plane; parallel to the axis it fixes nothing.
        proj = sum(a * b for a, b in zip(exit_dir, w))
        u = [e - proj * c for e, c in zip(exit_dir, w)]
        if _norm(u) < 1e-9:
            refusals.append('exit_dir is (anti)parallel to the '
                            'axis — the exiting wires must leave '
                            'sideways to define the phase')
        else:
            u = _unit(u)
    if refusals:
        return {'ok': False, 'refusals': refusals,
                'note': 'these tunings cannot form a math object'}
    turns = int(turns)
    v = _cross(w, u)
    tpl = int(length // d)
    layers = math.ceil(turns / tpl)
    outer = r0 + layers * d
    # wire length: sum of per-turn circumferences, exact per layer
    full, rem = divmod(turns, tpl)
    wire_len = sum(
        2 * math.pi * (r0 + d * (k + 0.5)) * tpl
        for k in range(full))
    if rem:
        wire_len += 2 * math.pi * (r0 + d * (full + 0.5)) * rem
    return {
        'ok': True,
        'object': {'C': center, 'M': [u, v, w], 'r0': r0, 'd': d,
                   'N': turns, 'L': length, 'tpl': tpl,
                   'phase': phase},
        'derived': {
            'turnsPerLayer': tpl, 'layers': layers,
            'outerRadius': round(outer, 6),
            'wireLength': round(wire_len, 4),
            'meanTurnLength': round(wire_len / turns, 6),
            'wireVolume': round(
                wire_len * math.pi * (d / 2) ** 2, 6),
        },
        'latex': (r'p(t) = \begin{pmatrix}'
                  r' r(t)\cos(2\pi t + \varphi) &'
                  r' r(t)\sin(2\pi t + \varphi) &'
                  r' z(t) \end{pmatrix} M + C,\quad'
                  r' r(t) = r_0 + d(\lfloor t/n_{pl}\rfloor + '
                  r'\tfrac12)'),
    }


def _local_point(obj, t):
    r = obj['r0'] + obj['d'] * (math.floor(t / obj['tpl']) + 0.5)
    theta = 2 * math.pi * t + obj['phase']
    k = math.floor(t / obj['tpl'])
    u = t - k * obj['tpl']
    half = obj['L'] / 2 - obj['d'] / 2
    z = (-half + obj['d'] * u) if k % 2 == 0 else (
        half - obj['d'] * u)
    return [r * math.cos(theta), r * math.sin(theta), z]


def _world(obj, local):
    m = obj['M']  # rows u, v, w — local x rides u, y rides v, z w
    return [obj['C'][i]
            + local[0] * m[0][i] + local[1] * m[1][i]
            + local[2] * m[2][i]
            for i in range(3)]


def winding_segments(obj, samples_per_turn=16, turn_stride=1):
    """The observable curve as SEGMENTS of world points. stride 1 =
    one continuous polyline (the true wire); stride n > 1 renders
    every nth turn as its OWN segment — decimation must never draw
    a phantom wire jumping across the skipped turns. The equation
    itself is never decimated, only the display."""
    n, spt = obj['N'], max(4, int(samples_per_turn))
    stride = max(1, int(turn_stride))
    segments = []
    turn = 0
    while turn < n:
        seg = []
        span_end = min(turn + 1, n) if stride > 1 else n
        t = float(turn)
        while t <= span_end + 1e-9:
            seg.append(_world(obj, _local_point(obj, min(t, n))))
            t += 1.0 / spt
        segments.append(seg)
        if stride == 1:
            break
        turn += stride
    return segments


def winding_points(obj, samples_per_turn=16, turn_stride=1):
    """Flat list of the segment points (analysis convenience)."""
    return [p for seg in winding_segments(
        obj, samples_per_turn, turn_stride) for p in seg]


def winding_tube_mesh(obj, samples_per_turn=16, turn_stride=None,
                      n_ring=6, wire_scale=1.0):
    """Swept tube (radius d/2) along the winding — the mesh a
    Mesh3DDefinition renders. Auto-decimates to stay under
    MAX_MESH_POINTS, reporting exactly what was dropped.
    wire_scale is a DISPLAY-ONLY exaggeration knob: hair-fine
    magnet wire is sub-pixel at scene scale, so it may be drawn
    fatter — the method string always states the true diameter."""
    spt = max(4, int(samples_per_turn))
    ring = max(3, int(n_ring))
    wire_scale = max(1.0, float(wire_scale or 1.0))
    if turn_stride is None:
        per_turn = spt * ring
        turn_stride = max(1, math.ceil(
            obj['N'] * per_turn / MAX_MESH_POINTS))
    segments = winding_segments(obj, samples_per_turn=spt,
                                turn_stride=turn_stride)
    rr = obj['d'] / 2 * wire_scale
    pts, tris = [], []
    for centers in segments:
        prev_ring = None
        for idx, c in enumerate(centers):
            nxt = centers[idx + 1] if idx + 1 < len(centers) else c
            prv = centers[idx - 1] if idx else c
            tang = _unit([a - b for a, b in zip(nxt, prv)]) \
                if _norm([a - b for a, b in zip(nxt, prv)]) > 1e-12 \
                else [0, 0, 1]
            ref = [0, 0, 1] if abs(tang[2]) < 0.9 else [1, 0, 0]
            e1 = _unit(_cross(tang, ref))
            e2 = _cross(tang, e1)
            base = len(pts)
            for j in range(ring):
                ang = 2 * math.pi * j / ring
                pts.append([
                    c[i] + rr * (math.cos(ang) * e1[i]
                                 + math.sin(ang) * e2[i])
                    for i in range(3)])
            if prev_ring is not None:
                for j in range(ring):
                    a = prev_ring + j
                    b = prev_ring + (j + 1) % ring
                    cidx = base + j
                    dd = base + (j + 1) % ring
                    tris.append([a, b, cidx])
                    tris.append([b, dd, cidx])
            prev_ring = base
    rendered = math.ceil(obj['N'] / turn_stride)
    scale_note = ('' if wire_scale == 1.0 else
                  f'; wire drawn at {wire_scale:g}x diameter for '
                  f'visibility (true d = {obj["d"]:g}, knob '
                  f'render_wire_scale)')
    return {
        'points': [[round(v, 4) for v in p] for p in pts],
        'triangles': tris,
        'method': (f'swept wire tube — {rendered} of {obj["N"]} '
                   f'turns rendered (stride {turn_stride}, knob '
                   f'render_turn_stride); the equation is never '
                   f'decimated, only the display{scale_note}'),
        'turnStride': turn_stride,
    }


def winding_matrix_equation(obj, name='winding-curve'):
    """The winding as a MatrixEquationDefinition spec: a numpy expr
    over bindings {t (vector of turn-parameters), M, C, r0, d, tpl,
    L, phase}. winding_points implements the SAME formula — parity
    is a pinned selftest, so the drawn object IS the equation."""
    expr = (
        "np.stack(["
        "(r0 + d*(np.floor(t/tpl) + 0.5))*np.cos(2*np.pi*t + phase),"
        "(r0 + d*(np.floor(t/tpl) + 0.5))*np.sin(2*np.pi*t + phase),"
        "np.where(np.floor(t/tpl) % 2 == 0,"
        " -(L/2 - d/2) + d*(t - np.floor(t/tpl)*tpl),"
        "  (L/2 - d/2) - d*(t - np.floor(t/tpl)*tpl))"
        "], -1) @ M + np.asarray(C)")
    return {
        'name': name,
        'description': 'The wire winding as a matrix equation: '
                       'world points from the turn parameter t. '
                       'Tunables: r0 (bore), d (fineness), tpl '
                       '(window/fineness), phase (exit-wire '
                       'orientation), M+C (stator frame).',
        'latex': (r'P = \begin{pmatrix} r(t)\cos\theta &'
                  r' r(t)\sin\theta & z(t)\end{pmatrix} M + C'),
        'operation_json_obj': {'kind': 'expr', 'expr': expr},
        'operands': ['t', 'M', 'C', 'r0', 'd', 'tpl', 'L', 'phase'],
        'bindings_from_object': {
            'M': obj['M'], 'C': obj['C'], 'r0': obj['r0'],
            'd': obj['d'], 'tpl': obj['tpl'], 'L': obj['L'],
            'phase': obj['phase']},
    }
