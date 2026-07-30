"""
@module magnetics.field_views

mag-fv analysis: analytic field primitives (EXACT closed forms —
dipole everywhere, infinite straight wire everywhere, both stated),
deterministic volume sampling, threshold-band classification, the
two display payloads (threshold-gated vector dispersions;
user-drawn shapes with PRECISION/RECALL fit metrics against the
sampled band), flux tubes from reluctance solves, and group
payloads for view alternation.

Stdlib + the module's own solver; shape containment is inline math
(sphere/box/cylinder) — emitting REAL mathshapes rows is the named
follow-up seam (that module drags a heavy dependency chain).
"""

import json
import math
import random

from magnetics.magnet_analysis import _named, _rows

MU0_OVER_4PI = 1.0e-7


def _loads(row, attr, default):
    try:
        return json.loads(getattr(row, attr, '') or '')
    except ValueError:
        return default


# ---------------------------------------------------------------- #
# Analytic primitives (exact; validity stated per primitive)
# ---------------------------------------------------------------- #

def _norm(v):
    return math.sqrt(sum(c * c for c in v))


def _unit(v):
    n = _norm(v)
    if n == 0:
        raise ValueError('zero-length axis/direction vector')
    return [c / n for c in v]


def dipole_field(point, params):
    """Exact point-dipole B (T): B = mu0/4pi * (3(m.r^)r^ - m)/r^3.
    Valid EVERYWHERE except r=0 (excluded by the sampler)."""
    center = params.get('center', [0, 0, 0])
    axis = _unit(params.get('axis', [0, 0, 1]))
    m = float(params.get('moment_a_m2', 1.0))
    r_vec = [p - c for p, c in zip(point, center)]
    r = _norm(r_vec)
    if r == 0:
        return None
    r_hat = [c / r for c in r_vec]
    m_dot_r = m * sum(a * b for a, b in zip(axis, r_hat))
    return [MU0_OVER_4PI * (3 * m_dot_r * rh - m * ax) / r ** 3
            for rh, ax in zip(r_hat, axis)]


def wire_field(point, params):
    """Exact INFINITE straight-wire B: |B| = mu0 I / (2 pi d),
    direction = I_dir x d_hat. The infinite-wire idealization is
    the stated validity limit."""
    amps = float(params.get('amps', 1.0))
    origin = params.get('point', [0, 0, 0])
    direction = _unit(params.get('direction', [0, 0, 1]))
    r_vec = [p - o for p, o in zip(point, origin)]
    along = sum(a * b for a, b in zip(r_vec, direction))
    perp = [rv - along * d for rv, d in zip(r_vec, direction)]
    d = _norm(perp)
    if d == 0:
        return None
    d_hat = [c / d for c in perp]
    tangent = [direction[1] * d_hat[2] - direction[2] * d_hat[1],
               direction[2] * d_hat[0] - direction[0] * d_hat[2],
               direction[0] * d_hat[1] - direction[1] * d_hat[0]]
    mag = 2.0 * MU0_OVER_4PI * amps / d
    return [mag * t for t in tangent]


PRIMITIVES = {'dipole': dipole_field, 'straight-wire': wire_field}


# ---------------------------------------------------------------- #
# Bands + shapes
# ---------------------------------------------------------------- #

def view_bands(manager, view_name):
    bands = [b for b in _rows(manager, 'FieldThresholdBand')
             if getattr(b, 'view_ref', '') == view_name]
    return sorted(bands, key=lambda b: -float(
        getattr(b, 'min_value', 0.0)))


def classify(magnitude, bands):
    for band in bands:
        if (float(getattr(band, 'min_value', 0.0)) <= magnitude
                < float(getattr(band, 'max_value', 0.0))):
            return band
    return None


def shape_contains(shape, point):
    kind = shape.get('kind', '')
    if kind == 'sphere':
        return _norm([p - c for p, c in
                      zip(point, shape['center'])]) \
            <= shape['r_m']
    if kind == 'box':
        return all(lo <= p <= hi for p, lo, hi in
                   zip(point, shape['min'], shape['max']))
    if kind == 'cylinder':
        axis = _unit(shape.get('axis', [0, 0, 1]))
        r_vec = [p - c for p, c in zip(point, shape['center'])]
        along = sum(a * b for a, b in zip(r_vec, axis))
        perp = _norm([rv - along * a for rv, a in zip(r_vec, axis)])
        return (abs(along) <= shape['half_len_m']
                and perp <= shape['r_m'])
    raise ValueError(f'unknown shape kind "{kind}" — sphere/box/'
                     'cylinder are the v1 vocabulary')


# ---------------------------------------------------------------- #
# Sampling
# ---------------------------------------------------------------- #

def sample_points(view):
    """Deterministic jittered grid over the view's region — the
    same jitter_seed always disperses identically."""
    spec = _loads(view, 'sample_json', {})
    region = spec.get('region')
    if not region:
        raise ValueError(
            f'view "{getattr(view, "name", "?")}" has no '
            f'sample_json.region — a volume sample needs bounds')
    per_axis = int(spec.get('per_axis', 6))
    rng = random.Random(int(spec.get('jitter_seed', 0)))
    lo, hi = region['min'], region['max']
    steps = [(h - l) / per_axis for l, h in zip(lo, hi)]
    points = []
    for i in range(per_axis):
        for j in range(per_axis):
            for k in range(per_axis):
                cell = (i, j, k)
                points.append([
                    l + (idx + 0.5 + (rng.random() - 0.5) * 0.6)
                    * step
                    for l, step, idx in zip(lo, steps, cell)])
    return points


def _analytic_field(view):
    params = _loads(view, 'source_params_json', {})
    primitive = params.get('primitive', '')
    fn = PRIMITIVES.get(primitive)
    if fn is None:
        raise ValueError(
            f'unknown analytic primitive "{primitive}" — v1 '
            f'vocabulary: {sorted(PRIMITIVES)}')
    return fn, params, primitive


def _watermark(view, extra=''):
    source = getattr(view, 'source_kind', '')
    marks = {
        'analytic': 'EXACT closed form (idealized primitive — '
                    'dipole point source / infinite wire)',
        'reluctance-solve': 'per-element flux from the lumped '
                            'reluctance solve — 1D per path, NO '
                            'off-path field claimed',
        'fem-2d': 'fem-2d field maps',
    }
    return (f'source={source}: {marks.get(source, "?")}'
            + (f'; {extra}' if extra else ''))


def dispersion_payload(manager, view_name):
    """Vector-dispersion mode: sampled vectors kept ONLY where
    |field| falls inside a band — absence means below threshold,
    not zero field (said in the payload)."""
    view = _named(manager, 'FieldViewDefinition', view_name)
    if view is None:
        return {'ok': False,
                'refusal': f'no FieldViewDefinition named '
                           f'"{view_name}"'}
    if getattr(view, 'source_kind', '') == 'fem-2d':
        return {'ok': False,
                'refusal': 'fem-2d field maps are not exported by '
                           'the fem engine yet — the named '
                           'follow-up; use analytic or '
                           'reluctance-solve sources today'}
    if getattr(view, 'source_kind', '') == 'reluctance-solve':
        return flux_tube_payload(manager, view_name)
    bands = view_bands(manager, view_name)
    if not bands:
        return {'ok': False,
                'refusal': f'view "{view_name}" has no '
                           f'FieldThresholdBand rows — thresholds '
                           f'are the gate, define them'}
    try:
        fn, params, primitive = _analytic_field(view)
        points = sample_points(view)
    except ValueError as exc:
        return {'ok': False, 'refusal': str(exc)}
    kept, below = [], 0
    for p in points:
        vec = fn(p, params)
        if vec is None:
            continue
        mag = _norm(vec)
        band = classify(mag, bands)
        if band is None:
            below += 1
            continue
        kept.append({'point': [round(c, 6) for c in p],
                     'vector': vec, 'magnitude': mag,
                     'band': getattr(band, 'name', ''),
                     'color': getattr(band, 'color', ''),
                     'alpha': getattr(band, 'alpha', 0.5)})
    return {'ok': True, 'view': view_name,
            'displayMode': 'vector-dispersion',
            'fieldKind': getattr(view, 'field_kind', ''),
            'primitive': primitive,
            'vectors': kept, 'sampled': len(points),
            'outsideBands': below,
            'note': 'vectors appear only inside bands — absence '
                    'means below/between thresholds, not zero '
                    'field',
            'watermark': _watermark(view),
            'bands': [{'name': getattr(b, 'name', ''),
                       'min': getattr(b, 'min_value', 0.0),
                       'max': getattr(b, 'max_value', 0.0),
                       'unit': getattr(b, 'unit', ''),
                       'color': getattr(b, 'color', ''),
                       'alpha': getattr(b, 'alpha', 0.5),
                       'label': getattr(b, 'label', '')}
                      for b in bands]}


def shapes_payload(manager, view_name):
    """Threshold-shapes mode: the user-drawn shape per band with
    color+alpha, PLUS honest fit metrics — precision (in-shape
    samples actually in-band) and recall (in-band samples the
    shape captures)."""
    view = _named(manager, 'FieldViewDefinition', view_name)
    if view is None:
        return {'ok': False,
                'refusal': f'no FieldViewDefinition named '
                           f'"{view_name}"'}
    if getattr(view, 'source_kind', '') != 'analytic':
        return {'ok': False,
                'refusal': 'threshold-shape fit metrics need a '
                           'point-evaluable source — analytic only '
                           'in v1'}
    bands = view_bands(manager, view_name)
    if not bands:
        return {'ok': False,
                'refusal': f'view "{view_name}" has no bands'}
    try:
        fn, params, primitive = _analytic_field(view)
        points = sample_points(view)
    except ValueError as exc:
        return {'ok': False, 'refusal': str(exc)}
    samples = []
    for p in points:
        vec = fn(p, params)
        if vec is None:
            continue
        samples.append((p, _norm(vec)))
    shapes = []
    for band in bands:
        shape = _loads(band, 'shape_json', {})
        entry = {'band': getattr(band, 'name', ''),
                 'label': getattr(band, 'label', ''),
                 'color': getattr(band, 'color', ''),
                 'alpha': getattr(band, 'alpha', 0.5),
                 'unit': getattr(band, 'unit', ''),
                 'min': getattr(band, 'min_value', 0.0),
                 'max': getattr(band, 'max_value', 0.0),
                 'shape': shape or None}
        if not shape:
            entry['fit'] = {'refusal': 'no shape drawn for this '
                                       'band yet — draw one to '
                                       'get fit metrics'}
            shapes.append(entry)
            continue
        in_band = [(p, m) for p, m in samples
                   if classify(m, [band]) is band]
        try:
            in_shape = [(p, m) for p, m in samples
                        if shape_contains(shape, p)]
        except (ValueError, KeyError) as exc:
            entry['fit'] = {'refusal': str(exc)}
            shapes.append(entry)
            continue
        true_pos = sum(1 for p, m in in_shape
                       if classify(m, [band]) is band)
        entry['fit'] = {
            'precision': (round(true_pos / len(in_shape), 4)
                          if in_shape else None),
            'recall': (round(true_pos / len(in_band), 4)
                       if in_band else None),
            'inBandSamples': len(in_band),
            'inShapeSamples': len(in_shape),
            'note': 'the shape is YOUR drawing of the band, not '
                    'the field — these numbers say how honest it '
                    'is'}
        shapes.append(entry)
    return {'ok': True, 'view': view_name,
            'displayMode': 'threshold-shapes',
            'fieldKind': getattr(view, 'field_kind', ''),
            'primitive': primitive, 'shapes': shapes,
            'sampled': len(samples),
            'watermark': _watermark(view),
            'mathshapesSeam': 'shape specs are mathshapes-'
                              'compatible; emitting real Shape '
                              'rows is the named follow-up '
                              '(module gated)'}


def flux_tube_payload(manager, view_name):
    """Reluctance-solve source: per-element tubes (flux, B, band
    color where B classifies) along the device's solved network."""
    view = _named(manager, 'FieldViewDefinition', view_name)
    if view is None:
        return {'ok': False,
                'refusal': f'no FieldViewDefinition named '
                           f'"{view_name}"'}
    device_kind = getattr(view, 'device_kind', '')
    device_ref = getattr(view, 'device_ref', '')
    if device_kind == 'block-layout':
        from magnetics.magnet_layout import solve_layout
        solved = solve_layout(manager, device_ref)
    elif device_kind == 'magnetic-circuit':
        from magnetics.magnetic_netlist import solve_network
        try:
            solved = solve_network(manager, device_ref)
        except ValueError as exc:
            solved = {'ok': False, 'refusal': str(exc)}
    else:
        return {'ok': False,
                'refusal': f'device_kind "{device_kind}" has no '
                           f'flux-tube source (block-layout | '
                           f'magnetic-circuit)'}
    if not solved.get('ok'):
        return {'ok': False, 'refusal': solved.get('refusal', ''),
                'via': 'device solve'}
    bands = view_bands(manager, view_name)
    tubes = []
    for e in solved['elements']:
        B = e.get('fluxDensityT')
        band = classify(abs(B), bands) if B is not None else None
        tubes.append({
            'element': e['element'], 'kind': e['kind'],
            'nodes': e['nodes'], 'fluxWb': e['fluxWb'],
            'fluxDensityT': B,
            'band': getattr(band, 'name', None) if band else None,
            'color': getattr(band, 'color', '#666666')
            if band else '#666666',
            'alpha': getattr(band, 'alpha', 0.25)
            if band else 0.25})
    return {'ok': True, 'view': view_name,
            'displayMode': 'flux-tubes',
            'device': {'kind': device_kind, 'ref': device_ref},
            'tubes': tubes,
            'saturationFlags': solved.get('saturationFlags', []),
            'watermark': _watermark(
                view, solved.get('validity', ''))}


def view_payload(manager, view_name):
    """Dispatch on the view's display mode."""
    view = _named(manager, 'FieldViewDefinition', view_name)
    if view is None:
        return {'ok': False,
                'refusal': f'no FieldViewDefinition named '
                           f'"{view_name}"'}
    if getattr(view, 'display_mode', '') == 'threshold-shapes':
        return shapes_payload(manager, view_name)
    return dispersion_payload(manager, view_name)


def group_payload(manager, group_name):
    """The alternation payload: every view of the group, in order,
    each rendered by its own mode — the UI cycles the index."""
    group = _named(manager, 'FieldViewGroup', group_name)
    if group is None:
        return {'ok': False,
                'refusal': f'no FieldViewGroup named '
                           f'"{group_name}"'}
    refs = _loads(group, 'view_refs_json', [])
    views = [{'view': ref, 'payload': view_payload(manager, ref)}
             for ref in refs]
    return {'ok': True, 'group': group_name,
            'displayName': getattr(group, 'display_name', ''),
            'order': refs, 'views': views,
            'note': 'alternate by index — one field flow shown at '
                    'a time, the group is what a SimSpace scene '
                    'binds'}
