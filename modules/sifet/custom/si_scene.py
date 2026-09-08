"""
@module sifet.custom.si_scene

fg-6: the SILICON device's 3-D sim-space scene — box-stack geometry
(substrate / S/D junctions / channel / oxide / gate / contacts, the
SAME rows-backed layout the 2-D parts view draws, cnt_parts_svg.
_si_layout) with the FETFieldSample binding: sample rows generated
by cnt_fields.sample_fields (which dispatches its profiles to
sifet.custom.si_fields and bands with SI_FIELD_BANDS) ride the cubes along
the channel surface, Vg as the scrubber's instant — the same
scrub-the-gate experience the CNT tube scenes give.

Scene name = cnt_scene.scene_name(device) = 'fet-3d-{device}' (fet,
not cntfet) so the generic detail page's viewer items resolve for
every technology. Depth (z) is a SKETCH knob — the device width
(w_nm, up to 1 µm) drawn to scale would dwarf the 90 nm channel.

@consumers
  - polariServer (SEED_SI_DEVICE_SCENES → SimSpaceDefinition seeds)
  - cnt_scene.scene_page_items via the generic fet-detail page
  - sifet.si_scene_selftest
"""

import json

from cntfet.cnt_fields_basis import FIELD_KNOBS, SCALAR_FIELDS, run_ref
from cntfet.custom.cnt_parts_svg import PARTS2D_KNOBS, _si_layout
from cntfet.cnt_scene_seed import scene_name
from sifet.custom.si_device import get_row

#: region kind → Material3DDefinition name (seeded in
#: cnt_fields.SEED_FET_FIELD_MATERIALS_3D; the body rect gets its own)
_STYLE = {
    'contact': 'fet-pd-contact',
    'extension': {'n': 'fet-si-sd-n', 'p': 'fet-si-sd-p'},
    'channel': 'fet-si-channel',
    'oxide': 'fet-sio2-oxide',
    'gate': 'fet-gate-metal',
}

SI_SCENE_KNOBS = {
    # drawn z depth (nm, SKETCH): w_nm to scale would dwarf Lg
    'si_scene_depth_nm': 40.0,
}


def _si_pieces(device_name, manager=None, knobs=None):
    """(shape_rows, entry_specs, layout_meta) from ONE source — the
    seeded MathShapeDefinition rows and the scene entries can never
    disagree. fg-6 (Dustin): the 3-D pieces are MATH SHAPES — every
    silicon piece an analytic box in TRUE nanometres (z depth = the
    stated sketch knob), exact math objects whose 4×4
    matrix-equation form shape_equation_rows() yields."""
    k = {**FIELD_KNOBS, **PARTS2D_KNOBS, **SI_SCENE_KNOBS,
         **(knobs or {})}
    dev = (get_row(manager, 'SiliconMOSFET', device_name)
           if manager is not None else None)
    parts = []
    if dev is not None:
        from cntfet.custom.cnt_parts import device_parts
        pr = device_parts(manager, dev)
        if pr.get('ok'):
            parts = pr['parts']
    kind = str(getattr(dev, 'shape', '') or 'planar (sketch)')
    template, rects, view, notes = _si_layout(dev, parts, k, kind)
    total = view['x1'] - view['x0']
    depth = k['si_scene_depth_nm']
    shapes, specs = [], []
    for r in rects:
        nm = f"fet-part-{device_name}-{r['id']}"
        shapes.append({
            'name': nm, 'display_name': nm,
            'family': 'primitive', 'primitive_kind': 'box',
            'parameters_json': json.dumps({
                'center': [round(r['x'] + r['w'] / 2.0 - total / 2.0,
                                 4),
                           round(r['y'] + r['h'] / 2.0, 4), 0.0],
                'size': [r['w'], r['h'], depth]}),
            'csg_json': '', 'quadric_matrix_json': '',
            'bounds_json': '',
            'notes': ('true nm from the rows; z depth is the '
                      f'{depth:g} nm SKETCH knob'
                      + ('; sketch dims — see the layout notes'
                         if r['sketch'] else '')),
            'provenance_id': 'fg-6'})
        specs.append((r, nm))
    return shapes, specs, (template, rects, view, notes)


def part_shape_seeds_si(device_name, manager=None, knobs=None):
    """The per-device MathShapeDefinition rows (fg-6) — seeded
    beside the motor/pot part shapes."""
    shapes, _specs, _meta = _si_pieces(device_name, manager, knobs)
    return shapes


def si_device_scene(device_name, manager=None, knobs=None):
    """The SimSpaceDefinition dict for one silicon device. With a
    manager the layout is rows-backed (thickness/junction depth);
    otherwise the sketch template, stated in the description."""
    k = {**FIELD_KNOBS, **PARTS2D_KNOBS, **SI_SCENE_KNOBS,
         **(knobs or {})}
    shapes, specs, meta = _si_pieces(device_name, manager, knobs)
    template, rects, view, notes = meta
    dev = (get_row(manager, 'SiliconMOSFET', device_name)
           if manager is not None else None)
    pol = (getattr(dev, 'polarity', '') or
           ('p' if '-pmos-' in device_name else 'n'))
    s = k['scene_scale']
    depth = k['si_scene_depth_nm'] * s
    total = view['x1'] - view['x0']
    entries = []
    for r, shape_nm in specs:
        st = _STYLE[r['kind']]
        if isinstance(st, dict):
            st = st.get(pol, st['n'])
        if r['id'] == 'body':
            st = 'fet-si-body'
        entries.append({
            'id': r['id'], 'label': r['label'],
            'position': [0.0, 0.0, 0.0],
            'rotation': [0, 0, 0],
            'scale': [s, s, s],
            'shapeRef': f'mathshape:{shape_nm}', 'styleRef': st,
            'userData': {'region': r['label'], 'kind': r['kind'],
                         'material': r['material'],
                         'sketch': r['sketch'],
                         'x_nm': [r['x'], r['x'] + r['w']],
                         'mathShape': shape_nm,
                         'viewScale': f'[{s:g}, {s:g}, {s:g}] — the '
                                      'shape row carries true nm',
                         'equations': 'the piece is a '
                                      'MathShapeDefinition — '
                                      'shape_equation_rows() gives '
                                      'its matrix-equation form',
                         'fidelity': 'geometry from the component '
                                     'rows; sketch lengths labelled'},
        })
    y_lo, y_hi = view['y0'] * s, view['y1'] * s
    half = total * s / 2.0
    extent = [half * 1.25, max(y_hi - y_lo, 0.5) * 1.4, depth * 3.0]
    return {
        'name': scene_name(device_name),
        'description': (
            f'fg-6 silicon device scene for {device_name} '
            f'({template}): every piece a MathShapeDefinition row '
            '(mathshape: refs — true-nm analytic boxes with a '
            'matrix-equation form) — the rows-backed stack (substrate, '
            'S/D junctions, channel, oxide, gate, contacts; z depth '
            f'is a {k["si_scene_depth_nm"]:g} nm SKETCH knob) with '
            'FETFieldSample cells along the channel surface banded '
            'by value (SI_FIELD_BANDS — areal cm^-2 / cm^-3 ranges); '
            'scrub Vg. Generate/refresh the samples: POST '
            '{"action": "sample-fields"} to /api/cntfet/devices/'
            + device_name + '. Select the field with the viewer run '
            'input = fet-fields:' + device_name + ':<field>. '
            + '; '.join(notes)),
        'dimensionality': '3d',
        'coordinate_system': 'math',
        'unit_scale': 1.0,
        'viewport_json': json.dumps({
            'center': [0.0, round((y_lo + y_hi) / 2.0, 4), 0.0],
            'extent': [round(v, 4) for v in extent]}),
        'bound_classes_json': json.dumps(
            [{'className': 'FETFieldSample'}]),
        'definition': json.dumps({
            'freestandingOnly': False,
            'device': device_name,
            'template': template,
            'runRefs': {f: run_ref(device_name, f)
                        for f in SCALAR_FIELDS},
            'freestanding': entries,
        }),
        'camera_json': json.dumps({
            # orbit start pose — free navigation ('fixed' disables
            # the controls entirely)
            'mode': 'orbit', 'projection': 'orthographic',
            'position': [0.0, 0.0, max(half * 2.0, 2.0)],
            'target': [0.0, round((y_lo + y_hi) / 2.0, 4), 0.0],
            'up': [0, 1, 0], 'fit': 'auto',
        }),
        'owning_module': 'sifet',
    }


def SEED_SI_DEVICE_SCENES(device_names, manager=None):
    return [si_device_scene(n, manager=manager) for n in device_names]
