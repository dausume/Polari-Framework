"""
@module cntfet.cnt_parts_svg

fg-3 (FET_GENERIC_PAGES_PLAN; fv-7 BUILD): the 2-D parts view as
DATA. The device's parts list (cnt_parts — the binding contract) laid
out as rectangles in DEVICE coordinates (nm): the template is chosen
by the device's own rows (cnt-gaa side section / si-planar /
si-finfet vertical section), every region carries its part payload
(material, doping, purpose, the ROW it comes from) and an optional
field overlay sampled from cnt_fields at the device's OWN Vdd
(device-relative rule). Silicon overlays REFUSE until a sifet field
basis exists (plan decision 3 — stated, not faked; fg-4 builds it).
Sketch dimensions (lengths no row carries) are labelled as such.

Each device's 2-D view is also a SimSpaceDefinition row
(`fet-2d-{device}`, freestandingOnly) so it appears under /sim-spaces
beside the 3-D scenes: SEED_FET_2D_SCENES.

@consumers
  - cnt_api (GET /api/fet/device/{name}/parts2d)
  - polariServer (SEED_FET_2D_SCENES → SimSpaceDefinition seeds)
  - polari-platform-angular fet-parts-2d (the d3 diagram)
  - cntfet.selftest_parts2d
"""

import json

from cntfet.cnt_derive import get_row

SCHEMA2D = 'fet-parts2d/1'

#: sketch knobs for lengths no row carries — echoed on every payload
PARTS2D_KNOBS = {
    'si_sd_length_nm': 40.0,       # lateral S/D length (sketch)
    'si_contact_length_nm': 20.0,  # contact plug length (sketch)
    'si_body_depth_nm': 60.0,      # drawn body depth (sketch)
    'si_gate_thickness_nm': 30.0,  # drawn gate height (sketch)
    'si_channel_depth_nm': 4.0,    # drawn inversion band (sketch)
    'radial_exaggeration': 3.0,    # CNT radial sizes ×3 (stated)
}

#: region kind → seeded SimSpace2D style name (and the frontend's
#: colour grouping key)
KIND_STYLE = {'contact': 'muted', 'extension': 'success',
              'channel': 'default', 'oxide': 'warning',
              'gate': 'danger'}


def _rect(rid, kind, label, x, y, w, h, material='', part=None,
          sketch=False):
    """One region rectangle in device coordinates (nm; y up,
    template-specific origin named in view.axis)."""
    return {'id': rid, 'kind': kind, 'label': label,
            'x': round(x, 3), 'y': round(y, 3),
            'w': round(w, 3), 'h': round(h, 3),
            'material': material, 'part': part, 'sketch': bool(sketch)}


def _part_for(parts, kind, label):
    """The cnt_parts entry this region maps to (regionKind join; a
    'source'/'drain' token in both names wins)."""
    cands = [p for p in parts if p.get('regionKind') == kind]
    if not cands:
        return None
    low = label.lower()
    for side in ('source', 'drain'):
        if side in low:
            for p in cands:
                if side in str(p.get('part', '')).lower():
                    return p
    return cands[0]


def _cnt_layout(manager, device, parts, knobs):
    """Side section of the GAA tube device: axial regions along x,
    oxide/gate shells mirrored above and below the tube band."""
    from cntfet.cnt_fields import device_regions
    from cntfet.cnt_scene import _sketch_geometry
    name = device if isinstance(device, str) else device.name
    notes = []
    geo = None
    if manager is not None and not isinstance(device, str):
        rep = device_regions(manager, device)
        if rep.get('ok'):
            geo = rep
        else:
            notes.append(f"row-backed geometry refused "
                         f"({rep.get('error')}) — S1 sketch lengths "
                         'drawn instead')
    if geo is None:
        geo = _sketch_geometry(name)
    rx = knobs['radial_exaggeration']
    sketch = geo['regions'][0].get('material') == 'sketch'
    rects = []
    r_tube = max(r['r1'] for r in geo['regions']) * rx
    for r in geo['regions']:
        grow = 1.5 if r['kind'] == 'contact' else 1.0
        h = 2 * r_tube * grow
        rects.append(_rect(f"ax-{r['name'].replace(' ', '-')}",
                           r['kind'], f"{r['name']} ({r['material']})",
                           r['x0'], -h / 2, r['x1'] - r['x0'], h,
                           material=r['material'],
                           part=_part_for(parts, r['kind'], r['name']),
                           sketch=sketch))
    for r in geo['radial']:
        if r['kind'] == 'channel':
            continue   # the tube band is already drawn per region
        r0, r1 = r['r0'] * rx, r['r1'] * rx
        for sign, tag in ((1, 'top'), (-1, 'bottom')):
            y = r0 if sign > 0 else -r1
            rects.append(_rect(
                f"sh-{tag}-{r['name'].replace(' ', '-')}", r['kind'],
                f"{r['name']} ({r['material']})",
                r['x0'], y, r['x1'] - r['x0'], r1 - r0,
                material=r['material'],
                part=_part_for(parts, r['kind'], r['name']),
                sketch=sketch))
    r_max = max(r['r1'] for r in geo['radial']) * rx
    view = {'x0': 0.0, 'x1': geo['length_nm'],
            'y0': -r_max * 1.9, 'y1': r_max * 1.9,
            'axis': ('x = along the tube (nm); y = radial (nm, '
                     f'×{rx:g} for visibility — stated, not to '
                     'scale)')}
    notes.extend(geo.get('notes') or [])
    return 'cnt-gaa', rects, view, notes


def _si_layout(device, parts, knobs, kind):
    """Vertical section of the silicon device: body below the
    surface (y = 0), S/D junctions to their junction depth, the
    gated channel band, oxide and gate stacked above."""
    k = knobs
    lg = float(getattr(device, 'lg_nm', 0.0) or 90.0)
    ox_part = _part_for(parts, 'oxide', 'gate dielectric')
    tox = float(((ox_part or {}).get('dimensions') or {})
                .get('thickness_nm') or 3.0)
    sd_part = _part_for(parts, 'extension', 'source / drain')
    xj = float(((sd_part or {}).get('dimensions') or {})
               .get('junction_depth_nm') or 20.0)
    lsd, lc = k['si_sd_length_nm'], k['si_contact_length_nm']
    body, tg = k['si_body_depth_nm'], k['si_gate_thickness_nm']
    chd = k['si_channel_depth_nm']
    total = lg + 2 * lsd
    ch_part = _part_for(parts, 'channel', 'channel')
    rects = [
        _rect('body', 'channel', f'body / substrate ({kind})',
              0, -body, total, body - chd, material='silicon',
              part=ch_part, sketch=True),
        _rect('src-junction', 'extension', 'source junction (S/D '
              'doping to its junction depth)', 0, -xj, lsd, xj,
              material='silicon n+/p+', part=sd_part),
        _rect('drn-junction', 'extension', 'drain junction',
              total - lsd, -xj, lsd, xj, material='silicon n+/p+',
              part=sd_part),
        _rect('channel', 'channel', 'channel (inversion forms in the '
              'top few nm — drawn band is a sketch)', lsd, -chd, lg,
              chd, material='silicon', part=ch_part, sketch=True),
        _rect('oxide', 'oxide', 'gate dielectric',
              lsd, 0, lg, tox,
              material=(ox_part or {}).get('material', ''),
              part=ox_part),
        _rect('gate', 'gate', 'gate electrode', lsd, tox, lg, tg,
              material=(_part_for(parts, 'gate', 'gate') or {})
              .get('material', ''),
              part=_part_for(parts, 'gate', 'gate'), sketch=True),
        _rect('src-contact', 'contact', 'source contact', 0, 0, lc,
              tg * 0.8, material='silicide / metal',
              part=_part_for(parts, 'contact', 'source contact'),
              sketch=True),
        _rect('drn-contact', 'contact', 'drain contact',
              total - lc, 0, lc, tg * 0.8,
              material='silicide / metal',
              part=_part_for(parts, 'contact', 'drain contact'),
              sketch=True),
    ]
    view = {'x0': 0.0, 'x1': total, 'y0': -body * 1.05,
            'y1': (tox + tg) * 1.15,
            'axis': ('x = along the channel (nm); y = depth into '
                     'the wafer (nm, surface at 0). Lateral S/D, '
                     'contact and gate heights are SKETCH lengths '
                     '(knobs) — no row carries them')}
    notes = ['S/D length, contact length, body depth, gate height '
             'and the inversion band are sketch knobs (labelled '
             'per region); junction depth and oxide thickness are '
             'row-backed']
    template = 'si-finfet' if 'fin' in str(kind).lower() else 'si-planar'
    if template == 'si-finfet':
        notes.append('finfet drawn as a planar section across the '
                     'fin — fin_width / fin_height / n_fins are in '
                     'the channel part card')
    return template, rects, view, notes


def _overlay(manager, device, field, vg, vd):
    """The 1-D field profile along x (CNT: cnt_fields at the
    device's own Vdd; Si: an honest refusal until fg-4)."""
    if not hasattr(device, 'material'):
        return {'ok': False, 'refusal': (
            'silicon field overlays refuse until a sifet transport/'
            'field basis exists (fg-4) — the region geometry above '
            'is still row-backed')}
    from cntfet.cnt_device_viz import device_vdd
    from cntfet.cnt_fields import FIELDS, field_profile
    vdd = device_vdd(device)
    rep = field_profile(manager, device, field,
                        vdd if vg is None else vg,
                        vdd if vd is None else vd)
    if not rep.get('ok'):
        return {'ok': False,
                'refusal': rep.get('error', 'field refused'),
                'fields': list(FIELDS)}
    keep = ('field', 'vg', 'vd', 'x_nm', 'value', 'unit', 'fidelity',
            'note', 'formula', 'material')
    return {'ok': True, **{kk: rep[kk] for kk in keep if kk in rep}}


def parts2d_report(manager, name, field='potential', vg=None, vd=None,
                   knobs=None):
    """{ok, schema, device, template, vdd_v, view, regions[],
    styleByKind, field, knobs, notes} — the fet-parts-2d feed."""
    k = {**PARTS2D_KNOBS, **(knobs or {})}
    device = (get_row(manager, 'AlignedCNTFETDevice', name)
              or get_row(manager, 'SiliconMOSFET', name))
    if device is None:
        return {'ok': False, 'schema': SCHEMA2D,
                'error': f'no device named "{name}"'}
    from cntfet.cnt_device_viz import device_vdd
    from cntfet.cnt_parts import device_parts
    pr = device_parts(manager, device)
    parts = pr.get('parts', []) if pr.get('ok') else []
    notes = ([] if pr.get('ok')
             else [f"parts list refused: {pr.get('error')}"])
    if hasattr(device, 'material'):
        template, rects, view, lnotes = _cnt_layout(
            manager, device, parts, k)
    else:
        kind = ''
        if pr.get('ok'):
            kind = str(pr.get('technology', '')).split('(')[-1] \
                .rstrip(')')
        kind = kind or str(getattr(device, 'shape', '') or 'planar '
                                                           '(sketch)')
        template, rects, view, lnotes = _si_layout(
            device, parts, k, kind)
    return {
        'ok': True, 'schema': SCHEMA2D, 'device': device.name,
        'template': template, 'vdd_v': device_vdd(device),
        'view': view, 'regions': rects, 'styleByKind': KIND_STYLE,
        'field': _overlay(manager, device, field, vg, vd),
        'knobs': k, 'notes': notes + lnotes,
        'note': ('regions are drawn from the same rows the parts '
                 'list names — the 2-D view is data, not an '
                 'illustration; sketch dimensions say so'),
    }


# ---- SimSpaceDefinition registration (fet-2d-{device}) --------------

def scene2d_name(device_name):
    return f'fet-2d-{device_name}'


def fet2d_scene(device_name, manager=None, knobs=None):
    """The 2-D SimSpaceDefinition row for one device — the same
    region rectangles as freestanding shapes (freestandingOnly), so
    the parts view appears under /sim-spaces beside the 3-D scenes.
    Without a manager (seed pass before boot data) the sketch
    geometry is drawn, stated in the description."""
    k = {**PARTS2D_KNOBS, **(knobs or {})}
    dev = None
    if manager is not None:
        dev = (get_row(manager, 'AlignedCNTFETDevice', device_name)
               or get_row(manager, 'SiliconMOSFET', device_name))
    parts = []
    if dev is not None:
        from cntfet.cnt_parts import device_parts
        pr = device_parts(manager, dev)
        if pr.get('ok'):
            parts = pr['parts']
    if device_name.startswith('si-') or (
            dev is not None and not hasattr(dev, 'material')):
        kind = str(getattr(dev, 'shape', '') or 'planar (sketch)')
        template, rects, view, notes = _si_layout(dev, parts, k, kind)
    else:
        template, rects, view, notes = _cnt_layout(
            manager, dev if dev is not None else device_name, parts, k)
    cx = (view['x0'] + view['x1']) / 2
    cy = (view['y0'] + view['y1']) / 2
    entries = []
    for r in rects:
        entries.append({
            'id': r['id'], 'label': r['label'],
            'position': [r['x'] + r['w'] / 2 - cx,
                         r['y'] + r['h'] / 2 - cy],
            'scale': [r['w'], r['h']],
            'shapeRef': 'rectangle',
            'styleRef': KIND_STYLE.get(r['kind'], 'default'),
            'userData': {'kind': r['kind'], 'material': r['material'],
                         'part': ((r['part'] or {}).get('part', '')
                                  if r['part'] else ''),
                         'x_nm': [r['x'], r['x'] + r['w']],
                         'sketch': r['sketch']},
        })
    return {
        'name': scene2d_name(device_name),
        'description': (
            f'fg-3 2-D parts view for {device_name} ({template}): '
            'region rectangles in device coordinates (nm) from the '
            'same rows the parts list names. The interactive view '
            '(part cards, field overlay, Vg/Vd) is the fet-parts-2d '
            'panel on /display/fet-detail?object=' + device_name
            + '. ' + '; '.join(notes)),
        'dimensionality': '2d',
        'coordinate_system': 'math',
        'unit_scale': 1.0,
        'viewport_json': json.dumps({
            'center': [0, 0],
            'extent': [(view['x1'] - view['x0']) * 0.6,
                       (view['y1'] - view['y0']) * 0.75]}),
        'bound_classes_json': '[]',
        'definition': json.dumps({'freestandingOnly': True,
                                  'template': template,
                                  'device': device_name,
                                  'freestanding': entries}),
        'owning_module': 'cntfet',
    }


def SEED_FET_2D_SCENES(device_names, manager=None):
    return [fet2d_scene(n, manager=manager) for n in device_names]
