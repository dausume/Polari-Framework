"""
@module cntfet.cnt_scene_seed

fv-4: the device's 3-D sim-space scene — CONFIG, not a component.
One SimSpaceDefinition per device (`cnt-device-3d-{device}`) whose
freestanding blob is the static REGION geometry (cylinders along
x for tube / oxide / gate shell, cubes for contacts) and whose
bound class is FETFieldSample (cnt_fields): banded cubes along the
tube axis, one per cell, Vg as the scrubber's instant.

Row filtering (what compile_3d supports, read 2026-08-27):
  compile_3d has NO binding-level or scene-level filter expression
  (the 'filter expression' the SimSpaceBindingDefinition docstring
  mentions is not implemented in the compiler). The ONLY row
  selection it honours is `run_filter` (`?run=<name>` on the
  snapshot endpoint, the viewer's `run` input) via
  simulations.run_scope.row_in_run_scope: a row passes when it
  carries no `simulation_run_ref` attribute or its
  `simulation_run_ref` is in scope (the run name itself plus any
  coupled runs of a SimulationRun row of that name; a name with no
  SimulationRun row is still a valid scope of one). So:
    - every FETFieldSample carries simulation_run_ref =
      'fet-fields:{device}:{field}' (cnt_fields.run_ref), and
    - the DisplayDefinition viewer item passes inputs.run = that
      string, selecting device × field with ONE scene per device
      and ONE binding for the class.
  The binding is defaultVisible: False and each device scene lists
  the class in bound_classes_json — compile_3d includes a binding
  when the scene overrides it OR it is defaultVisible, so the
  sample rows never pour into unrelated 3-D scenes.

Cylinder axis: three-geometry-builders builds THREE.CylinderGeometry
(axis = local Y); three-renderer applies `rotation` as Euler
radians (node.rotation.set(x, y, z)). A rotation of [0, 0, pi/2]
turns local Y onto world X, so the shells are cylinders with
scale [2r, length, 2r] rotated by z = pi/2 — no cube fallback
needed.

@consumers polariServer (SEED_CNT_DEVICE_SCENES /
  SEED_FET_FIELD_BINDINGS seed pass), cnt_pages_seed / fv-5
  (scene_page_items), selftest_fields
"""

import json
import math

from cntfet.cnt_fields_basis import (
    FIDELITY, FIELD_KNOBS, SCALAR_FIELDS, SEEDED_STYLE_NAMES,
    device_regions, run_ref,
)
from cntfet.custom.cnt_derive import get_row

SCENE_PREFIX = 'fet-3d-'   # fet, not cntfet (was 'cnt-device-3d-';
#                            the old rows are the backfill script's
#                            legacy list — Si devices get fet-3d-*
#                            scenes too, sifet.custom.si_scene)
BINDING_NAME = 'FETFieldSample-3d'

_REGION_STYLE = {
    'contact': 'fet-pd-contact',
    'channel': 'fet-cnt-channel',
    'extension': {'n': 'fet-cnt-extension-n', 'p': 'fet-cnt-extension-p'},
    'oxide': 'fet-hfo2-oxide',
    'gate': 'fet-gate-metal',
}


def scene_name(device_name):
    return f'{SCENE_PREFIX}{device_name}'


def _style(region, polarity):
    s = _REGION_STYLE[region['kind']]
    return s[polarity] if isinstance(s, dict) else s


def _sketch_geometry(device_name):
    """Regions when no manager/derived device is at hand (seed pass
    before derive): the S1 sketch lengths, stated in userData."""
    k = FIELD_KNOBS
    lc, lext, lg = k['l_c_default_nm'], k['l_ext_sketch_nm'], 15.0
    d, tox, tg = 1.2526, 3.0, k['gate_thickness_nm']
    x, regions = 0.0, []
    for name, kind, length in (('source contact', 'contact', lc),
                               ('source extension', 'extension', lext),
                               ('channel', 'channel', lg),
                               ('drain extension', 'extension', lext),
                               ('drain contact', 'contact', lc)):
        regions.append({'name': name, 'kind': kind, 'x0': x, 'x1': x + length,
                        'r0': 0.0, 'r1': d / 2, 'material': 'sketch',
                        'componentRow': None})
        x += length
    radial = [
        {'name': 'tube', 'kind': 'channel', 'x0': lc, 'x1': x - lc,
         'r0': 0.0, 'r1': d / 2, 'material': 'sketch', 'componentRow': None},
        {'name': 'oxide shell', 'kind': 'oxide', 'x0': lc, 'x1': x - lc,
         'r0': d / 2, 'r1': d / 2 + tox, 'material': 'sketch',
         'componentRow': None},
        {'name': 'gate metal shell', 'kind': 'gate', 'x0': lc + lext,
         'x1': lc + lext + lg, 'r0': d / 2 + tox, 'r1': d / 2 + tox + tg,
         'material': 'sketch', 'componentRow': None},
    ]
    return {'ok': True, 'device': device_name, 'regions': regions,
            'radial': radial, 'length_nm': x, 'polarity': 'n',
            'notes': ['sketch geometry (device not derived / no manager '
                      'at seed time) — S1 default lengths'],
            'diameter_nm': d, 't_ox_nm': tox}


def _slug(text):
    return str(text).replace(' ', '-')


def _pieces(geo, device_name):
    """(shape_rows, entry_specs) for every FET piece from ONE source
    — the seeded MathShapeDefinition rows and the scene entries that
    reference them can never disagree. fg-6 (Dustin): the 3-D pieces
    are MATH SHAPES — true-nanometre geometry, device centred at
    x = 0: contacts as analytic boxes, tube segments as x-axis
    cylinders, the oxide/gate shells as CSG differences of coaxial
    cylinders. Every row is an exact math object: mathshapes.
    shape_equations.shape_equation_rows() yields its 4×4
    matrix-equation form (the [[matrix-equation-operation-node]]
    round-trip)."""
    length = geo['length_nm']
    shapes, specs = [], []

    def shape(name, family, kind='', params=None, csg=None,
              bounds=None, notes=''):
        shapes.append({
            'name': name, 'display_name': name, 'family': family,
            'primitive_kind': kind,
            'parameters_json': json.dumps(params or {}),
            'csg_json': json.dumps(csg) if csg else '',
            'quadric_matrix_json': '',
            'bounds_json': json.dumps(bounds) if bounds else '',
            'notes': notes, 'provenance_id': 'fg-6'})

    for r in geo['regions']:
        cx = 0.5 * (r['x0'] + r['x1']) - length / 2.0
        ln = r['x1'] - r['x0']
        nm = f"fet-part-{device_name}-{_slug(r['name'])}"
        if r['kind'] == 'contact':
            side = 2.0 * r['r1'] * 1.5
            shape(nm, 'primitive', 'box',
                  {'center': [cx, 0.0, 0.0], 'size': [ln, side, side]},
                  notes='contact pad — length row-backed; the 1.5x-'
                        'tube cross-section is a SKETCH (no row '
                        'carries the pad geometry)')
        else:
            shape(nm, 'primitive', 'cylinder',
                  {'radius': r['r1'], 'height': ln, 'axis': 'x',
                   'center': [cx, 0.0, 0.0]},
                  notes='tube segment — true nm from the component '
                        'rows')
        specs.append((r, nm))
    for r in geo['radial']:
        if r['kind'] == 'channel':
            continue   # the tube is already drawn per region
        cx = 0.5 * (r['x0'] + r['x1']) - length / 2.0
        ln = r['x1'] - r['x0']
        base = f"fet-part-{device_name}-{_slug(r['name'])}"
        # ONE annular_sector primitive (mq-2 — the radial-machine
        # primitive with exact closed forms, an exact triangulated
        # mesh and a quadric emission): half_angle 180° = the full
        # ring. The CSG outer−inner form meshed as a POINT CLOUD in
        # the 3-D renderer — invisible pieces (Dustin's find).
        shape(base, 'primitive', 'annular_sector',
              {'r_inner': r['r0'], 'r_outer': r['r1'],
               'half_angle_deg': 180.0, 'azimuth_deg': 0.0,
               'height': ln, 'axis': 'x',
               'center': [cx, 0.0, 0.0]},
              notes='shell as an annular ring (r_in..r_out about '
                    'the tube axis); true nm')
        specs.append((r, base))
    return shapes, specs


def part_shape_seeds(device_name, manager=None, knobs=None):
    """The per-device MathShapeDefinition rows (fg-6) — seeded
    beside the motor/pot part shapes and referenced by the scene's
    `mathshape:` entries."""
    k = {**FIELD_KNOBS, **(knobs or {})}
    shapes, _specs = _pieces(_geometry(device_name, manager, k),
                             device_name)
    return shapes


def _geometry(device_name, manager, k):
    geo = None
    if manager is not None:
        dev = get_row(manager, 'AlignedCNTFETDevice', device_name)
        if dev is not None and getattr(dev, 'derived_at', ''):
            rep = device_regions(manager, dev, knobs=k)
            if rep.get('ok'):
                geo = rep
    return geo if geo is not None else _sketch_geometry(device_name)


def region_freestanding(geo, knobs=None, device_name=''):
    """Scene entries referencing the per-piece math shapes. The
    shapes carry TRUE nanometre geometry; the stated radial
    exaggeration is applied here as a VIEW transform only
    (scale [s, s·rx, s·rx]) — it never touches the math."""
    k = {**FIELD_KNOBS, **(knobs or {})}
    s, rx = k['scene_scale'], k['radial_exaggeration']
    polarity = geo.get('polarity', 'n')
    _shapes, specs = _pieces(geo, device_name)
    entries = []
    for r, shape_name in specs:
        entries.append({
            'id': f"piece-{_slug(r['name'])}",
            'label': f"{r['name']} ({r['material']})",
            'position': [0.0, 0.0, 0.0], 'rotation': [0, 0, 0],
            'scale': [s, s * rx, s * rx],
            'shapeRef': f'mathshape:{shape_name}',
            'styleRef': _style(r, polarity),
            'userData': {
                'region': r['name'], 'kind': r['kind'],
                'material': r['material'],
                'componentRow': r.get('componentRow'),
                'x0_nm': r['x0'], 'x1_nm': r['x1'],
                'r0_nm': r.get('r0'), 'r1_nm': r.get('r1'),
                'mathShape': shape_name,
                'viewScale': (f'[{s:g}, {s * rx:g}, {s * rx:g}] — '
                              f'radial ×{rx:g} VIEW exaggeration; '
                              'the shape row carries true nm'),
                'equations': ('the piece is a MathShapeDefinition — '
                              'shape_equation_rows() gives its 4×4 '
                              'matrix-equation form'),
                'fidelity': 'geometry from the component rows; '
                            'sketch lengths labelled in the shape '
                            'row notes'},
        })
    return entries


def device_scene_seeds(device_name, manager=None, knobs=None):
    """The SimSpaceDefinition dict for one device. With a manager and
    a derived device the regions are row-backed; otherwise the S1
    sketch geometry (stated in the description)."""
    k = {**FIELD_KNOBS, **(knobs or {})}
    geo = _geometry(device_name, manager, k)
    s, rx = k['scene_scale'], k['radial_exaggeration']
    half = geo['length_nm'] * s / 2
    r_max = max(r['r1'] for r in geo['radial']) * rx * s
    extent = [half * 1.15, max(r_max * 3, 0.3), max(r_max * 3, 0.3)]
    return {
        'name': scene_name(device_name),
        'description': (
            f'fv-4 device scene for {device_name}: region geometry '
            f'(contacts, doped extensions, channel, oxide + gate shells; '
            f'radii x{rx:g} for visibility) with FETFieldSample cells '
            f'along the tube axis banded by value; scrub Vg. Select the '
            f'field with the viewer run input = fet-fields:{device_name}:'
            f'<field>. {FIDELITY}. '
            + '; '.join(geo.get('notes') or [])),
        'dimensionality': '3d',
        'coordinate_system': 'math',
        'unit_scale': 1.0,
        'viewport_json': json.dumps({'center': [0, 0, 0],
                                     'extent': extent}),
        'bound_classes_json': json.dumps([{'className': 'FETFieldSample'}]),
        'definition': json.dumps({
            'freestandingOnly': False,
            'device': device_name,
            'runRefs': {f: run_ref(device_name, f) for f in SCALAR_FIELDS},
            'freestanding': region_freestanding(
                geo, knobs=k, device_name=device_name),
        }),
        'camera_json': json.dumps({
            # orbit: the authored pose is the START; navigation stays
            # free (mode 'fixed' DISABLES the controls — Dustin
            # could not move the scene at all)
            'mode': 'orbit', 'projection': 'orthographic',
            'position': [0.0, 0.0, max(half * 2, 2.0)],
            'target': [0.0, 0.0, 0.0], 'up': [0, 1, 0], 'fit': 'auto',
        }),
        'owning_module': 'cntfet',
    }


def SEED_CNT_DEVICE_SCENES(device_names, manager=None):
    return [device_scene_seeds(n, manager=manager) for n in device_names]


SEED_FET_FIELD_BINDINGS = [{
    'name': BINDING_NAME, 'class_name': 'FETFieldSample',
    'dimensionality': '3d', 'enabled': True,
    'binding_json': json.dumps({
        'enabled': True, 'dimensionality': '3d', 'kind': 'object',
        'position': {'kind': 'fields',
                     'fields': {'x': 'pos_x', 'y': 'pos_y', 'z': 'pos_z'}},
        'visual': {
            'shapeRef': 'cube',
            # band_style holds the Material3DDefinition name directly;
            # the identity map keeps the mapping explicit (and lets a
            # scene remap one band without touching rows).
            'styleRef': {'fromField': 'band_style',
                         'map': {n: n for n in SEEDED_STYLE_NAMES},
                         'default': 'fet-band-none'},
        },
        'scale': {'kind': 'uniform', 'field': 'cell_scene', 'factor': 1.0},
        'temporal': {'kind': 'time', 'field': 'vg_v', 'unit': 'V',
                     'cumulative': False},
        'clickAction': 'navigate-to-instance',
        # NOT defaultVisible: only scenes that list FETFieldSample in
        # bound_classes_json (the device scenes) render these rows.
        'defaultVisible': False,
        'rowFilter': {'mechanism': 'run_filter',
                      'field': 'simulation_run_ref',
                      'pattern': 'fet-fields:{device}:{field}'},
    }),
}]


def _viewer_item(item_id, index, title, device, field, segments):
    return {'id': item_id, 'index': index, 'type': 'component',
            'rowSegmentsUsed': segments, 'gridColumnStart': None,
            'title': title, 'visible': True, 'collapsed': False,
            'cssClass': '',
            'componentProps': {'componentName': 'sim-space-viewer',
                               'inputs': {'simSpaceName': scene_name(device),
                                          'run': run_ref(device, field),
                                          'hideRunPanel': True,
                                          'clickNavigates': False}},
            'item': None, 'nestedRows': []}


def scene_page_items(device, fields=SCALAR_FIELDS):
    """DisplayDefinition component items (one sim-space-viewer per
    scalar field, the run input selecting the field's rows) for a
    detail-page row."""
    segs = max(12 // max(len(fields), 1), 4)
    return [
        _viewer_item(f'cnt-scene-{device}-{field}', i,
                     f'{device}: {field} along the tube (F1 SKETCH; '
                     f'scrub Vg)', device, field, segs)
        for i, field in enumerate(fields)
    ]
