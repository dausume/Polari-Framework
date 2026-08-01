"""
@module mathshapes.gear_geometry

gr-3 (named a seam since the gears arc; demanded by Dustin
2026-08-01): "the math definition of the gear should be accurate,
showing the teeth of the gear and allowing the math definition of
those teeth to be tuned."

THE MATH OBJECT — a spur gear is fully determined by:

    m        module (mm per tooth of pitch diameter) — OR derived
             from a followed shape via the cascade (pitch radius =
             ref value x ratio, then m = 2 r_p / z)
    z        tooth count
    alpha    pressure angle (deg)
    x        profile-shift coefficient — THE low-tooth-count knob:
             clock pinions run 6-12 teeth, which UNDERCUT at x=0;
             shifting the profile outward restores a solid flank
    face     face width; bore radius; center; axis

Derived, never stated: pitch r_p = m z / 2, base r_b = r_p cos α,
tip r_a = r_p + m(1 + x), root r_f = r_p − m(1.25 − x), tooth
thickness at pitch. The flank is the true INVOLUTE of the base
circle: p(t) = r_b (cos t + t sin t, sin t − t cos t).

Coherence refusals name the knob: z < 3, non-positive module, a
bore swallowing the root circle, and UNDERCUT (z below the shifted
limit) — the refusal states the minimum profile shift that clears
it. Horological honesty: real clock trains historically use
CYCLOIDAL profiles for very low counts; that family stays a named
seam (gears.PROFILE_FAMILIES has it), and this involute-with-shift
object says so in its note rather than pretending to be it.

@consumers mathshapes.shape_analysis (family 'gear'),
motors.motor_shapes seeds, mathshapes.selftest_winding
"""

import math


def gear_coherence(params, resolve_ref=None):
    """Validate the tunables into the gear MATH OBJECT (or refuse,
    naming every incoherence and its knob)."""
    refusals = []
    z = params.get('teeth', 0)
    alpha_deg = float(params.get('pressure_angle_deg', 20.0))
    x = float(params.get('profile_shift', 0.0))
    face = float(params.get('face_width', 0) or 0)
    bore = float(params.get('bore_radius', 0) or 0)
    center = [float(c) for c in params.get('center', [0, 0, 0])]
    axis = params.get('axis', 'z')
    if not (isinstance(z, (int, float)) and z >= 3
            and float(z).is_integer()):
        refusals.append(f'teeth must be a whole number >= 3 '
                        f'(got {z!r})')
    m = params.get('module')
    ref = params.get('ref')
    if ref and resolve_ref is not None:
        # the cascade: pitch radius follows a named derived value.
        got = resolve_ref(ref, params.get('radius_from',
                                          'flangeRadius'))
        if got is None:
            refusals.append(f'ref "{ref}" resolves no '
                            f'"{params.get("radius_from")}" value')
        elif refusals == []:
            r_p = got * float(params.get('radius_ratio', 1.0))
            m = 2.0 * r_p / int(z)
    if m is None:
        refusals.append('needs module (or ref + radius_ratio to '
                        'derive it through the cascade)')
    elif float(m) <= 0:
        refusals.append(f'module must be > 0 (got {m})')
    if face <= 0:
        refusals.append(f'face_width must be > 0 (got {face})')
    if not (0 < alpha_deg < 45):
        refusals.append(f'pressure_angle_deg must be in (0, 45) '
                        f'(got {alpha_deg})')
    if refusals:
        return {'ok': False, 'refusals': refusals}
    z = int(z)
    m = float(m)
    alpha = math.radians(alpha_deg)
    ha = float(params.get('addendum_coeff', 1.0))
    hf = float(params.get('dedendum_coeff', 1.25))
    r_p = m * z / 2.0
    r_b = r_p * math.cos(alpha)
    r_a = r_p + m * (ha + x)
    r_f = max(r_p - m * (hf - x), 0.0)
    # undercut: the classic limit z_min = 2(1-x)/sin^2(alpha) —
    # below it the flank digs into the root. The refusal names the
    # shift that clears it.
    z_min = 2.0 * (1.0 - x) / (math.sin(alpha) ** 2)
    if z < z_min:
        x_needed = 1.0 - z * math.sin(alpha) ** 2 / 2.0
        return {'ok': False, 'refusals': [
            f'{z} teeth UNDERCUT at profile shift {x:g} (needs z '
            f'>= {z_min:.1f}) — raise profile_shift to '
            f'>= {x_needed:.2f}, or use the cycloidal profile '
            f'(the horological answer for low counts; a named '
            f'seam, not built here)']}
    if bore >= r_f:
        return {'ok': False, 'refusals': [
            f'bore_radius {bore} swallows the root circle '
            f'({r_f:.4g}) — no tooth would remain attached']}
    # tip-thickness coherence: a shifted tooth SHARPENS as the
    # addendum grows; a tip that crosses zero is self-intersecting
    # geometry, not a gear. The refusal names both knobs.
    inv_a = math.tan(alpha) - alpha
    half_pitch = (math.pi / (2 * z)
                  + 2 * x * math.tan(alpha) / z)
    t_tip = math.sqrt(max((r_a / r_b) ** 2 - 1.0, 0.0))
    phi_tip = math.atan2(math.sin(t_tip) - t_tip * math.cos(t_tip),
                         math.cos(t_tip) + t_tip * math.sin(t_tip))
    tip_half_angle = half_pitch + inv_a - phi_tip
    if tip_half_angle <= 0:
        return {'ok': False, 'refusals': [
            f'the tooth tip sharpens to NOTHING at this tuning '
            f'(profile shift {x:g}, addendum_coeff {ha:g}) — '
            f'shorten the addendum (addendum_coeff) or reduce '
            f'profile_shift']}
    tooth_thickness = m * (math.pi / 2 + 2 * x * math.tan(alpha))
    return {
        'ok': True,
        'object': {'m': m, 'z': z, 'alpha': alpha, 'x': x,
                   'face': face, 'bore': bore, 'center': center,
                   'axis': axis, 'r_p': r_p, 'r_b': r_b,
                   'r_a': r_a, 'r_f': r_f},
        'derived': {
            'pitchRadius': round(r_p, 6),
            'baseRadius': round(r_b, 6),
            'tipRadius': round(r_a, 6),
            'rootRadius': round(r_f, 6),
            'module': round(m, 6),
            'toothThicknessAtPitch': round(tooth_thickness, 6),
            'tipLand': round(2 * tip_half_angle * r_a, 6),
            'undercutLimitTeeth': round(z_min, 2),
        },
        'latex': (r'\text{flank: } p(t) = r_b\,(\cos t + t\sin t,'
                  r'\ \sin t - t\cos t),\quad r_p = \tfrac{mz}{2},'
                  r'\ r_b = r_p\cos\alpha'),
        'note': 'involute with profile shift; very low counts are '
                'historically CYCLOIDAL in clockwork — that '
                'profile family remains a named seam',
    }


def _involute_point(r_b, t):
    return (r_b * (math.cos(t) + t * math.sin(t)),
            r_b * (math.sin(t) - t * math.cos(t)))


def _involute_t_at(r_b, r):
    return math.sqrt(max(r * r / (r_b * r_b) - 1.0, 0.0))


def gear_profile(obj, flank_samples=8):
    """One revolution of the 2D tooth profile (list of [px, py] in
    the gear plane, counter-clockwise, closed implicitly)."""
    z, r_b, r_a, r_f = (obj['z'], obj['r_b'], obj['r_a'],
                        obj['r_f'])
    # angular half-thickness of the tooth at the pitch circle,
    # shifted; involute angle bookkeeping (inv α).
    alpha = obj['alpha']
    inv = math.tan(alpha) - alpha
    half_pitch = (math.pi / (2 * obj['z'])
                  + 2 * obj['x'] * math.tan(alpha) / obj['z'])
    t_tip = _involute_t_at(r_b, r_a)
    prof = []
    for k in range(z):
        base_ang = 2 * math.pi * k / z
        # tooth centered on base_ang: rising flank, tip arc,
        # falling flank, then root arc to the next tooth.
        rise, fall = [], []
        for i in range(flank_samples + 1):
            t = t_tip * i / flank_samples
            px, py = _involute_point(r_b, t)
            r = math.hypot(px, py)
            phi = math.atan2(py, px)          # involute rolls +phi
            rise.append((r, phi))
        # place flanks symmetric about the tooth center: the
        # involute at the pitch radius sits inv(alpha) past its
        # base-circle start; rotate so pitch-thickness lands right.
        offs = half_pitch + inv
        for r, phi in rise:
            a = base_ang - offs + phi
            fall.append((r, base_ang + offs - phi))
            prof.append([r * math.cos(a), r * math.sin(a)])
        for r, a in reversed(fall):
            prof.append([r * math.cos(a), r * math.sin(a)])
        # root arc between this tooth's falling flank and the next
        # tooth's rising flank.
        a0 = base_ang + offs
        a1 = base_ang + 2 * math.pi / z - offs
        for i in range(1, 4):
            a = a0 + (a1 - a0) * i / 4
            prof.append([r_f * math.cos(a), r_f * math.sin(a)])
    return prof


def gear_mesh(obj, flank_samples=8):
    """Extruded gear solid: profile walls + bore walls + top and
    bottom annuli, one vertex set (the tube_mesh idiom)."""
    prof = gear_profile(obj, flank_samples=flank_samples)
    n = len(prof)
    c, axis, face = obj['center'], obj['axis'], obj['face']
    ai = {'x': 0, 'y': 1, 'z': 2}[axis]
    p0, p1 = (ai + 1) % 3, (ai + 2) % 3

    def lift(p2, t):
        p = [0.0, 0.0, 0.0]
        p[ai] = c[ai] - face / 2 + t * face
        p[p0] = c[p0] + p2[0]
        p[p1] = c[p1] + p2[1]
        return p

    bore_r = obj['bore'] if obj['bore'] > 0 else obj['r_f'] * 0.25
    bore = [[bore_r * math.cos(2 * math.pi * i / n),
             bore_r * math.sin(2 * math.pi * i / n)]
            for i in range(n)]
    pts = ([lift(p, 0.0) for p in prof]
           + [lift(p, 1.0) for p in prof]
           + [lift(p, 0.0) for p in bore]
           + [lift(p, 1.0) for p in bore])
    ob, ot, ib, it_ = 0, n, 2 * n, 3 * n
    tris = []
    for j in range(n):
        jn = (j + 1) % n
        tris.append([ob + j, ob + jn, ot + j])       # outer wall
        tris.append([ob + jn, ot + jn, ot + j])
        tris.append([ib + j, it_ + j, ib + jn])      # bore wall
        tris.append([ib + jn, it_ + j, it_ + jn])
        tris.append([ob + j, ib + j, ob + jn])       # bottom
        tris.append([ob + jn, ib + j, ib + jn])
        tris.append([ot + j, ot + jn, it_ + j])      # top
        tris.append([ot + jn, it_ + jn, it_ + j])
    return pts, tris
