"""
@module mathshapes.shape_anchor_seed

ms-anchor seeds: one anchor picked on the seeded demo-cylinder's top
cap (ray down the axis, reference 'away' so w runs INTO the part
along the axis), a second with reference 'toward' for a raised pad,
and three offsets on them — the §8.5 thread example as an M5
INTERNAL thread (ISO 68-1: P = 0.8 mm, D = 5 mm, D1 = D − 1.0825·P =
4.134 mm; in cm), the bore it sits in (a planar disk of the minor
radius over the full length), and a square pad.

The anchor numbers are HAND-COMPUTED (the selftest re-picks them and
must agree): demo-cylinder is r = 1, h = 4, axis z, centre 0 — the
ray (0, 0, 10) → −z meets the top cap z = 2 at (0, 0, 2), outward
normal +z; 'away' gives a = −z, so w = 2 − z (0 at the cap, 4 at the
base); with the ray along the normal there is no 'most toward'
tangent, so b is the arbitrary in-plane +x and c = a × b = −y.

Thread knob meaning (the formula as written in §8.5):
  |frac((w − (P/2π)·θ)/P) − ½| < h/P   with θ = atan2(v, u)
  → h is the ridge HALF-width in w (the ridge spans 2h per pitch);
    r is the inner radius of the band, depth its radial thickness.
Frame coordinates: q = M p = [u, v, w, 1] with w ALONG the reference
axis a and (u, v) along (b, c) — §8.5's usage (w − t = 0 is the
offset plane; the thread runs along w), kept over its one-line
(·a, ·b, ·c) listing; recorded as a deviation for Dustin.
Chaining: an offset composes with its anchor's shape only; the full
"bore then thread" part is the thread anchored on the bore's
`--result` row once result_shape_rows persisted it (the API does).

The engine reaches the surface the Polari way (Dustin 2026-11-03: no
custom APIs): SEED_SHAPE_ANCHOR_ANALYSES registers each entry point of
custom/shape_anchor_analyses.py as an AnalysisDefinition row
(callable_ref 'module:function', fn(manager, **params) -> dict) and
SEED_SHAPE_ANCHOR_SOLUTIONS wraps each in one DirectInvocation →
AnalysisCall → ReturnValue SolutionDefinition (the mech / vpn pattern),
so every analysis runs through the generic solution-execution routes
and composes as a step in any other no-code solution.

@consumers polariServer (seed_pairs — SHAPE_ANCHOR_SEED_PAIRS),
mathshapes.shape_anchor_selftest, SolutionExecutionEngine
"""

import json

from polariNoCode import graph_builder as gb

PROV = 'ms-anchor'

_TOP_PICK = {
    'ray_origin_json': json.dumps([0.0, 0.0, 10.0]),
    'ray_dir_json': json.dumps([0.0, 0.0, -1.0]),
    'hit_json': json.dumps([0.0, 0.0, 2.0]),
    'normal_json': json.dumps([0.0, 0.0, 1.0]),
    'normal_eq_ref': 'demo-cylinder--grad',
    'basis': 'exact',
}

SEED_SHAPE_ANCHORS = [
    dict(_TOP_PICK, **{
        'name': 'demo-cylinder-top-axis',
        'display_name': 'demo-cylinder top cap, looking down the axis, away',
        'shape_ref': 'demo-cylinder',
        'reference': 'away',
        'frame_json': json.dumps({
            'a': [0.0, 0.0, -1.0], 'b': [1.0, 0.0, 0.0],
            'c': [0.0, -1.0, 0.0], 'origin': [0.0, 0.0, 2.0],
            'matrix': [1, 0, 0, 0, 0, -1, 0, 0, 0, 0, -1, 2, 0, 0, 0, 1],
            'mode': 'away',
            'note': 'ray is along the normal: no "most toward" tangent '
                    'exists; b is an arbitrary in-plane direction'}),
        'provenance_id': PROV,
        'notes': 'w runs down the cylinder axis into the part — the '
                 'thread axis of the M5 example.',
    }),
    dict(_TOP_PICK, **{
        'name': 'demo-cylinder-top-toward',
        'display_name': 'demo-cylinder top cap, looking down the axis, toward',
        'shape_ref': 'demo-cylinder',
        'reference': 'toward',
        'frame_json': json.dumps({
            'a': [0.0, 0.0, 1.0], 'b': [1.0, 0.0, 0.0],
            'c': [0.0, 1.0, 0.0], 'origin': [0.0, 0.0, 2.0],
            'matrix': [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, -2, 0, 0, 0, 1],
            'mode': 'toward',
            'note': 'ray is along the normal: no "most toward" tangent '
                    'exists; b is an arbitrary in-plane direction'}),
        'provenance_id': PROV,
        'notes': 'w grows OUT of the cap — for pads that rise off it.',
    }),
]

#: the §8.5 thread, every number a knob (parameters_json).
THREAD_EXPR = ('lmax(abs(frac((w - (P/(2*pi))*atan2(v, u))/P) - 0.5) '
               '- h/P, sqrt(u*u + v*v) - (r + depth), '
               'r - sqrt(u*u + v*v))')

SEED_ANCHORED_OFFSETS = [
    {'name': 'demo-m5-bore',
     'display_name': 'M5 minor-diameter bore down demo-cylinder',
     'anchor_ref': 'demo-cylinder-top-axis', 'mode': 'planar_disk',
     't': 4.0, 'offset_eq': '',
     'extent_json': json.dumps({'radius': 0.2067}),
     'surface_eq_ref': '', 'surface_eq_json': '',
     'parameters_json': '{}', 'op': 'subtract', 'result_shape_ref': '',
     'approx_reason': '', 'provenance_id': PROV,
     'notes': 'ISO 68-1 M5: D1 = 5 − 1.0825·0.8 = 4.134 mm → r = 0.2067 '
              'cm; the disk patch over the full length IS the bore.'},
    {'name': 'demo-m5-internal-thread',
     'display_name': 'M5 internal thread groove (§8.5 thread equation)',
     'anchor_ref': 'demo-cylinder-top-axis', 'mode': 'custom',
     't': 0.0, 'offset_eq': '',
     'extent_json': json.dumps({'w': [0.0, 4.0]}),
     'surface_eq_ref': '',
     'surface_eq_json': json.dumps({'expr': THREAD_EXPR, 'operands': {}}),
     'parameters_json': json.dumps(
         {'P': 0.08, 'h': 0.02, 'r': 0.2067, 'depth': 0.0433}),
     'op': 'subtract', 'result_shape_ref': '',
     'approx_reason': '', 'provenance_id': PROV,
     'notes': 'helical band r..r+depth = minor..major radius, ridge '
              'half-width h = P/4 (a 50 % duty); subtracted = the '
              'groove an external M5 ridge occupies. 50 turns over 4 cm.'},
    {'name': 'demo-cylinder-top-pad',
     'display_name': 'square pad 1×1×0.5 raised off the top cap',
     'anchor_ref': 'demo-cylinder-top-toward', 'mode': 'planar_square',
     't': 0.5, 'offset_eq': '',
     'extent_json': json.dumps({'side': 1.0}),
     'surface_eq_ref': '', 'surface_eq_json': '',
     'parameters_json': '{}', 'op': 'add', 'result_shape_ref': '',
     'approx_reason': '', 'provenance_id': PROV,
     'notes': 'exact: four side planes + two slab planes; result volume '
              '= π·1²·4 + 0.5.'},
]


# ------------------------------------------------------------------
# the engine as rows: AnalysisDefinition + one solution each
# ------------------------------------------------------------------
_MOD = 'mathshapes.custom.shape_anchor_analyses'


def _analysis(name, fn, description, params):
    return {'name': name, 'domain': 'mathshapes',
            'callable_ref': f'{_MOD}:{fn}', 'description': description,
            'params_json': json.dumps(params), 'enabled': True,
            'is_prior': True, 'provenance_id': PROV, 'notes': ''}


#: name → (callable, description, {param: meaning})
_ANALYSES = [
    ('ms-anchor-pick', 'pick_anchor',
     'Ray-pick a ShapeAnchor on a MathShapeDefinition: march the implicit '
     'field along o + s·d to its first zero (bisection to 1e-12), normal = '
     '∇F/|∇F| (2Qp of the active surface), the tangent basis and the frame '
     'for the chosen reference; persist = true upserts the row by name (§8.5 step 1 + 2).',
     {'shape': 'MathShapeDefinition name', 'ray_origin': '[x, y, z]',
      'ray_dir': '[dx, dy, dz] (normalised on use)',
      'reference': 'toward | away | tangent_toward | tangent_away',
      'name': "anchor row name ('' = <shape>-anchor)",
      'persist': 'true to land the ShapeAnchor row',
      'max_dist': "march length ('' = from the shape's bounds)",
      'step': "march step ('' = bounding diagonal / 256)"}),
    ('ms-anchor-frame', 'anchor_frame',
     'The frame (a, b, c, origin, world→local 4x4) of a ShapeAnchor for any '
     "of the four references ('' = the anchor's own) — the four-way toggle.",
     {'anchor': 'ShapeAnchor name',
      'mode': "toward | away | tangent_toward | tangent_away ('' = the row's)"}),
    ('ms-offset-evaluate', 'evaluate_offset',
     'G / F / the composed result of an AnchoredOffset at world points, each '
     'with its (u, v, w) in the anchor frame; approxReason says when the '
     'field is first-order only.',
     {'offset': 'AnchoredOffset name',
      'points': '[x, y, z] or [[x, y, z], ...]'}),
    ('ms-offset-sample', 'sample_offset',
     'Grid-sampled volumes of parent / offset solid / result over the '
     "offset's bounds (inside cells × cell volume — a discretisation).",
     {'offset': 'AnchoredOffset name', 'grid': 'cells per axis (4..80), default 24'}),
    ('ms-offset-equations', 'offset_equations',
     'The no-code rows of an offset: <offset>--frame (M), --local (q = M p), '
     '--G (in q, knobs as scalar operands), --field (composed with the '
     "parent's --field) + the parent's rows and its ∇F row; conform refuses by name.",
     {'offset': 'AnchoredOffset name'}),
    ('ms-offset-result', 'offset_result',
     'The result as ordinary MathShapeDefinition rows (planar modes, constant t): '
     'world-frame quadrics + --solid + --result csg over the parent; persist = '
     'true lands them and sets result_shape_ref. Other modes refuse by name.',
     {'offset': 'AnchoredOffset name', 'persist': 'true to land the rows'}),
]

SEED_SHAPE_ANCHOR_ANALYSES = [_analysis(n, fn, d, p) for n, fn, d, p in _ANALYSES]


def _solution(analysis_name, params, description):
    """DirectInvocation → AnalysisCall → ReturnValue: the analysis as a
    runnable, composable no-code solution. Input params flow in by name."""
    name = analysis_name.replace('ms-', 'ms-run-', 1)
    graph = gb.solution(
        name,
        gb.node('Start', 'DirectInvocation', {}, outs=[['Call']]),
        gb.node('Call', 'AnalysisCall',
                {'analysis': analysis_name,
                 'params': {p: gb.var_src(p) for p in params},
                 'resultVariable': 'result'},
                outs=[['Return']]),
        gb.ret('Return', 'result'),
    )
    return {'name': name, 'function_name': name.replace('-', '_'),
            'target_runtime': 'python_backend', 'definition': json.dumps(graph),
            'contract_json': json.dumps({
                'description': description,
                'inputs': [{'name': p, 'required': False, 'description': meaning}
                           for p, meaning in params.items()],
                'returns': [{'name': 'result',
                             'description': 'the analysis dict (ok, …, _analysis provenance)'}],
                'executionRights': 'invoker'}),
            'category': ''}


SEED_SHAPE_ANCHOR_SOLUTIONS = [_solution(n, p, d) for n, fn, d, p in _ANALYSES]


def shape_anchor_seed_pairs():
    """[(class_name, cls, rows)] for the server's seed pass — the rows
    first, then the analyses + solutions that read them."""
    from mathshapes.shape_basis import AnchoredOffset, ShapeAnchor
    from polariApiServer.solutionDefinition import SolutionDefinition
    from polariNoCode.analysis_calls import AnalysisDefinition
    return [('ShapeAnchor', ShapeAnchor, SEED_SHAPE_ANCHORS),
            ('AnchoredOffset', AnchoredOffset, SEED_ANCHORED_OFFSETS),
            ('AnalysisDefinition', AnalysisDefinition, SEED_SHAPE_ANCHOR_ANALYSES),
            ('SolutionDefinition', SolutionDefinition, SEED_SHAPE_ANCHOR_SOLUTIONS)]


class _LazySeedPairs(list):
    """Materialised on first use so this seed module stays import-light
    (shape_basis imports the row classes; the manifest's `seedPairs`
    resolves this name and iterates it — see manifest_admission._resolve)."""

    def _fill(self):
        if not list.__len__(self):
            self.extend(shape_anchor_seed_pairs())

    def __iter__(self):
        self._fill(); return list.__iter__(self)

    def __len__(self):
        self._fill(); return list.__len__(self)


#: polari-app.json `seedPairs` target (ms-anchor).
SHAPE_ANCHOR_SEED_PAIRS = _LazySeedPairs()

#: the name `pol modules conform` derives for the manifest's `seedPairs`
#: (<PKG>_SEED_PAIRS at top level of a *_seed.py) — the same lazy list.
MATHSHAPES_SEED_PAIRS = SHAPE_ANCHOR_SEED_PAIRS
