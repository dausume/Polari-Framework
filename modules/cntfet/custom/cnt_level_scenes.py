"""
@module cntfet.custom.cnt_level_scenes

The MULTISCALE microchip scenes (Dustin 2026-08-31: 2-D/3-D
visualization + simulation for all three levels — plug the FETs in
and show how they interconnect to form a cell; cells become
instancable objects plugged into blocks; choose per level between
REAL shapes and BLACK-BOX stand-ins that carry the lower level's
real characterized data. "The goal is to turn this gradually into a
multiscale simulation that works for microchips.")

Scale coupling, stated:
  FET scale    fet-3d-{device} scenes (fg-6) — math-shape pieces +
               FETFieldSample bands.
  CELL scale   cell-{dim}-{cell}-{device}: every transistor of the
               cell's flattened netlist placed CMOS-row style (Vdd
               rail / p-row / net tracks / n-row / GND rail).
               lod=real (3-D): each FET instances the SAME
               fet-part-{device}-* MathShapeDefinition rows the FET
               scenes use — one geometry source across scales.
               lod=blackbox (and every 2-D scene): a labelled box
               per FET whose userData carries the device's summary
               path — the scale-boundary contract.
  BLOCK scale  block-{dim}-{block}-{device}: one instancable box
               per CELL instance, userData carrying THAT
               CellFETConfiguration's characterized score/run (or
               its fill refusal verbatim) + the cell-scene name one
               scale down. lod=real re-expands cells into their
               transistors — guarded by an entry budget (the
               performance choice is a knob, never a silent cap).

Wiring honesty: the row layout + net tracks are the SCHEMATIC
convention (gate stub at the instance centre, drain/source stubs at
±0.35·pitch), not lithography — every scene says so.

Scenes are generated ON DEMAND (GET upserts the SimSpaceDefinition
row idempotently) so the grid never seeds thousands of rows at boot;
generated rows persist and appear under /sim-spaces.

@consumers
  - cnt_api (GET /api/fet/scene/cell/… , /api/fet/scene/block/…)
  - cell-detail-panel / block-detail-panel (embedded sim-space-viewer)
  - cntfet.level_scenes_selftest
"""

import json

from cntfet.cnt_cell_library_basis import CELL_LIBRARY
from cntfet.custom.cnt_derive import get_row
from cntfet.cnt_fields_basis import FIELD_KNOBS

#: entry budget for lod=real (his performance knob — refused, never
#: silently downgraded)
LEVEL_SCENE_KNOBS = {
    'real_entry_budget': 1600,
    'row_gap_factor': 1.1,     # rows sit this × FET height apart
    'pitch_factor': 1.2,       # instance pitch × FET width
    'track_gap_nm': 12.0,      # net-track spacing
    'wire_thickness_nm': 4.0,
}

_P_STYLE_3D, _N_STYLE_3D = 'fet-si-sd-p', 'fet-si-sd-n'
_RAIL_STYLE_3D, _TRACK_STYLE_3D = 'fet-gate-metal', 'fet-band-none'
_2D = {'p': 'danger', 'n': 'success', 'rail': 'warning',
       'track': 'muted', 'cellbox': 'default'}


def scene_name(level, dim, key, device):
    return f'{level}-{dim}-{key}-{device}'


def _flatten(cell_key, prefix=''):
    """(type, drain, gate, source) with compose stages expanded —
    local mirror of cnt_power.flatten_devices (kept dependency-free
    for the layout path)."""
    cell = CELL_LIBRARY[cell_key]
    if not cell.get('compose'):
        return [(t, d, g, s) for t, d, g, s in cell['devices']]
    out = []
    for idx, (sub, in_nets, out_net) in enumerate(cell['compose']):
        if isinstance(in_nets, str):
            in_nets = [in_nets]
        sub_cell = CELL_LIBRARY[sub]
        pmap = dict(zip(sub_cell['inputs'], in_nets))
        pmap[sub_cell['output']] = out_net
        pfx = f'{prefix}u{idx}_'
        for t, d, g, s in _flatten(sub, pfx):
            def m(net):
                if net in ('vddn', '0'):
                    return net
                return pmap.get(net, pfx + net)
            out.append((t, m(d), m(g), m(s)))
    return out


def _lookup_device(manager, device_name):
    """(row, tech) — tech decided by WHICH class matched, never by
    duck-typing."""
    row = get_row(manager, 'AlignedCNTFETDevice', device_name)
    if row is not None:
        return row, 'cnt'
    row = get_row(manager, 'SiliconMOSFET', device_name)
    return row, ('silicon' if row is not None else None)


def _fet_footprint(manager, device_name, tech):
    """(w_nm, h_nm, view_scale_triplet) for one device."""
    if tech == 'cnt':
        from cntfet.cnt_scene_seed import _geometry
        k = dict(FIELD_KNOBS)
        geo = _geometry(device_name, manager, k)
        rx = k['radial_exaggeration']
        r_max = max(r['r1'] for r in geo['radial']) * rx
        return (geo['length_nm'], 2.0 * r_max * 1.9, (1.0, rx, rx))
    from sifet.custom.si_scene import _si_pieces
    _sh, _sp, meta = _si_pieces(device_name, manager)
    _t, _r, view, _n = meta
    return (view['x1'] - view['x0'], view['y1'] - view['y0'],
            (1.0, 1.0, 1.0))


def _cell_layout(manager, cell, device_name, tech, knobs=None):
    """Rails, p-row/n-row instance slots, net tracks and pin stubs —
    all in nm. One source for 2-D and 3-D."""
    k = {**LEVEL_SCENE_KNOBS, **(knobs or {})}
    devs = _flatten(cell)
    w, h, view = _fet_footprint(manager, device_name, tech)
    pitch = w * k['pitch_factor']
    p_devs = [x for x in devs if x[0] == 'p']
    n_devs = [x for x in devs if x[0] == 'n']
    ncols = max(len(p_devs), len(n_devs), 1)
    width = ncols * pitch
    nets = sorted({net for _t, d, g, s in devs
                   for net in (d, g, s) if net not in ('vddn', '0')})
    tg = k['track_gap_nm']
    band = (len(nets) + 1) * tg
    row_gap = band / 2.0 + h * k['row_gap_factor'] / 2.0
    wire = k['wire_thickness_nm']
    inst, tracks, stubs = [], [], []
    for row, items, y in (('p', p_devs, row_gap),
                          ('n', n_devs, -row_gap)):
        for i, (t, d, g, s) in enumerate(items):
            x = (i - (len(items) - 1) / 2.0) * pitch
            inst.append({'type': t, 'x': x, 'y': y,
                         'drain': d, 'gate': g, 'source': s,
                         'w': w, 'h': h})
    track_y = {net: (i - (len(nets) - 1) / 2.0) * tg
               for i, net in enumerate(nets)}
    for net, ty in track_y.items():
        xs = ([e['x'] + off * pitch
               for e in inst
               for pin, off in (('gate', 0.0), ('drain', 0.35),
                                ('source', -0.35))
               if e[pin] == net])
        if not xs:
            continue
        x0, x1 = min(xs), max(xs)
        tracks.append({'net': net, 'y': ty, 'x0': x0 - wire,
                       'x1': x1 + wire})
    for e in inst:
        for pin, off in (('gate', 0.0), ('drain', 0.35),
                         ('source', -0.35)):
            net = e[pin]
            if net == 'vddn':
                ty = row_gap + h * 0.75
            elif net == '0':
                ty = -row_gap - h * 0.75
            else:
                ty = track_y[net]
            stubs.append({'net': net, 'pin': pin,
                          'x': e['x'] + off * pitch,
                          'y0': min(e['y'], ty), 'y1': max(e['y'], ty)})
    rails = [{'net': 'vddn', 'y': row_gap + h * 0.75},
             {'net': '0 (GND)', 'y': -row_gap - h * 0.75}]
    height = 2 * (row_gap + h * 1.3)
    return {'instances': inst, 'tracks': tracks, 'stubs': stubs,
            'rails': rails, 'width': width, 'height': height,
            'pitch': pitch, 'fet_w': w, 'fet_h': h, 'tech': tech,
            'view': view, 'nets': nets,
            'wire': wire,
            'note': ('CMOS-row SCHEMATIC layout (rails / p-row / '
                     'net tracks / n-row; gate stub at centre, '
                     'drain/source at ±0.35·pitch) — not '
                     'lithography, stated')}


def _box(eid, label, x, y, w, h, dim, style3d, style2d, depth,
         user, s):
    if dim == '3d':
        return {'id': eid, 'label': label,
                'position': [round(x * s, 4), round(y * s, 4), 0.0],
                'rotation': [0, 0, 0],
                'scale': [round(max(w * s, 0.03), 4),
                          round(max(h * s, 0.03), 4),
                          round(depth * s, 4)],
                'shapeRef': 'cube', 'styleRef': style3d,
                'userData': user}
    return {'id': eid, 'label': label,
            'position': [round(x * s, 4), round(y * s, 4)],
            'scale': _box2d_scale(w, h, s),
            'shapeRef': 'rectangle', 'styleRef': style2d,
            'userData': user}


def _box2d_scale(w, h, s):
    # 2-D styles draw a 40×40 base; non-uniform scale (fg-6b)
    return [round(max(w * s, 0.05) / 40.0, 4),
            round(max(h * s, 0.05) / 40.0, 4)]


def cell_scene(manager, cell, device_name, dim='3d', lod='real',
               knobs=None):
    """Build (not yet persist) the cell scene definition dict +
    stats. 2-D is always the box layout (math-shape refs are a 3-D
    pipeline); that is stated, not hidden."""
    if cell not in CELL_LIBRARY:
        return {'ok': False, 'error': f'no library cell "{cell}" — '
                'sequential cells (cdff) flatten through their own '
                'arc later; the combinational library is the v1 '
                'scope'}
    device, tech = _lookup_device(manager, device_name)
    if device is None:
        return {'ok': False, 'error': f'no device "{device_name}"'}
    if dim not in ('2d', '3d'):
        return {'ok': False, 'error': 'dim = 2d | 3d'}
    if lod not in ('real', 'blackbox'):
        return {'ok': False, 'error': 'lod = real | blackbox'}
    k = {**LEVEL_SCENE_KNOBS, **(knobs or {})}
    lay = _cell_layout(manager, cell, device_name, tech, knobs)
    s = FIELD_KNOBS['scene_scale']
    entries = []
    depth = lay['fet_h'] * 0.6
    # rails + tracks + stubs (wires)
    for r in lay['rails']:
        e = _box(f"rail-{_slug(r['net'])}", f"rail {r['net']}",
                 0.0, r['y'], lay['width'] * 1.05, lay['wire'] * 2,
                 dim, _RAIL_STYLE_3D, _2D['rail'], depth * 0.3,
                 {'net': r['net'], 'kind': 'rail'}, s)
        if dim == '2d':
            e['scale'] = _box2d_scale(lay['width'] * 1.05,
                                      lay['wire'] * 2, s)
        entries.append(e)
    for t in lay['tracks']:
        e = _box(f"track-{_slug(t['net'])}", f"net {t['net']}",
                 (t['x0'] + t['x1']) / 2.0, t['y'],
                 t['x1'] - t['x0'], lay['wire'], dim,
                 _TRACK_STYLE_3D, _2D['track'], depth * 0.25,
                 {'net': t['net'], 'kind': 'net-track'}, s)
        if dim == '2d':
            e['scale'] = _box2d_scale(t['x1'] - t['x0'],
                                      lay['wire'], s)
        entries.append(e)
    for i, st in enumerate(lay['stubs']):
        e = _box(f'stub-{i}-{_slug(st["net"])}',
                 f"{st['pin']} → {st['net']}",
                 st['x'], (st['y0'] + st['y1']) / 2.0,
                 lay['wire'], max(st['y1'] - st['y0'],
                                  lay['wire']), dim,
                 _TRACK_STYLE_3D, _2D['track'], depth * 0.25,
                 {'net': st['net'], 'pin': st['pin'],
                  'kind': 'pin-stub'}, s)
        if dim == '2d':
            e['scale'] = _box2d_scale(lay['wire'],
                                      max(st['y1'] - st['y0'],
                                          lay['wire']), s)
        entries.append(e)
    # the FET instances
    use_real = (lod == 'real' and dim == '3d')
    pieces = None
    if use_real:
        if lay['tech'] == 'cnt':
            from cntfet.cnt_scene_seed import _geometry, _pieces
            geo = _geometry(device_name, manager, dict(FIELD_KNOBS))
            _shapes, specs = _pieces(geo, device_name)
        else:
            from sifet.custom.si_scene import _si_pieces
            _shapes, specs, _meta = _si_pieces(device_name, manager)
        # CNT spec rows carry name/kind; Si rect rows carry id (and
        # no kind) — normalize once here
        pieces = [({'name': r.get('name') or r.get('id', ''),
                    'kind': r.get('kind', '')}, nm)
                  for r, nm in specs]
        projected = (len(entries)
                     + len(lay['instances']) * len(specs))
        if projected > k['real_entry_budget']:
            return {'ok': False,
                    'error': f'lod=real would need {projected} '
                             f'entries (budget '
                             f'{k["real_entry_budget"]}) — use '
                             'lod=blackbox (the stand-ins carry '
                             'the FET summary paths) or raise the '
                             'knob deliberately'}
    vx, vy, vz = lay['view']
    for idx, inst in enumerate(lay['instances']):
        user = {'kind': 'fet-instance', 'type': inst['type'],
                'device': device_name,
                'nets': {'drain': inst['drain'],
                         'gate': inst['gate'],
                         'source': inst['source']},
                'summaryPath': f'/api/fet/device/{device_name}'
                               '/summary',
                'fetScene': f'fet-{dim}-{device_name}'}
        if use_real:
            for r, shape_nm in pieces:
                entries.append({
                    'id': f'i{idx}-{_slug(r["name"])}',
                    'label': f"#{idx} {inst['type']}-FET "
                             f"{r['name']}",
                    'position': [round(inst['x'] * s, 4),
                                 round(inst['y'] * s, 4), 0.0],
                    'rotation': [0, 0, 0],
                    'scale': [round(s * vx, 4), round(s * vy, 4),
                              round(s * vz, 4)],
                    'shapeRef': f'mathshape:{shape_nm}',
                    'styleRef': (_P_STYLE_3D if inst['type'] == 'p'
                                 else _N_STYLE_3D)
                    if r['kind'] == 'channel' else
                    _style_for_kind(r['kind']),
                    'userData': {**user, 'piece': r['name']}})
        else:
            e = _box(f'i{idx}', f"#{idx} {inst['type']}-FET "
                     f"({device_name})",
                     inst['x'], inst['y'], inst['w'] * 0.9,
                     inst['h'] * 0.9, dim,
                     _P_STYLE_3D if inst['type'] == 'p'
                     else _N_STYLE_3D,
                     _2D[inst['type']], depth, user, s)
            if dim == '2d':
                e['scale'] = _box2d_scale(inst['w'] * 0.9,
                                          inst['h'] * 0.9, s)
            entries.append(e)
    name = scene_name('cell', dim, cell, device_name)
    half_w = lay['width'] * s * 0.65
    half_h = lay['height'] * s * 0.65
    fields = {
        'name': name,
        'description': (
            f'MULTISCALE cell scene ({lod}): {cell} built from '
            f'{len(lay["instances"])} × {device_name} FETs, CMOS-row '
            f'layout with labelled net tracks. '
            + ('Each FET instances the SAME fet-part math shapes '
               'the FET scenes use — one geometry source across '
               'scales. ' if use_real else
               'Black-box FET stand-ins carry the device summary '
               'path — the scale-boundary contract. ')
            + ('2-D scenes always use the box layout (math-shape '
               'meshes are a 3-D pipeline). ' if dim == '2d' else '')
            + lay['note']),
        'dimensionality': dim, 'coordinate_system': 'math',
        'unit_scale': 1.0,
        'viewport_json': json.dumps(
            {'center': [0, 0] if dim == '2d' else [0, 0, 0],
             'extent': ([round(half_w, 3), round(half_h, 3)]
                        if dim == '2d' else
                        [round(half_w, 3), round(half_h, 3),
                         round(depth * s * 3, 3)])}),
        'bound_classes_json': '[]',
        'definition': json.dumps({
            'freestandingOnly': True, 'level': 'cell', 'lod': lod,
            'cell': cell, 'device': device_name,
            'nets': lay['nets'], 'freestanding': entries}),
        'camera_json': (json.dumps({
            'mode': 'orbit', 'projection': 'orthographic',
            'position': [0.0, 0.0, max(half_w * 2, 2.0)],
            'target': [0.0, 0.0, 0.0], 'up': [0, 1, 0],
        }) if dim == '3d' else ''),
        'owning_module': 'cntfet',
    }
    return {'ok': True, 'fields': fields, 'entries': len(entries),
            'instances': len(lay['instances']),
            'nets': len(lay['nets']), 'lod': lod, 'dim': dim}


def block_scene(manager, block, device_name, dim='3d',
                lod='blackbox', knobs=None):
    """Cells as INSTANCABLE objects plugged into the block — one
    box per cell instance, userData carrying that
    CellFETConfiguration's characterized numbers (or the fill
    refusal). lod=real expands transistors, entry-budget guarded."""
    from cntfet.cnt_blocks_page import BLOCK_LIBRARY
    if block not in BLOCK_LIBRARY:
        return {'ok': False, 'error': f'no block "{block}"'}
    device, tech = _lookup_device(manager, device_name)
    if device is None:
        return {'ok': False, 'error': f'no device "{device_name}"'}
    if dim not in ('2d', '3d'):
        return {'ok': False, 'error': 'dim = 2d | 3d'}
    k = {**LEVEL_SCENE_KNOBS, **(knobs or {})}
    insts = BLOCK_LIBRARY[block]['instances']
    # real characterized data per CELL KIND — pulled once, the
    # scale-boundary contract every stand-in carries
    from cntfet.cnt_cell_scoring_seed import score_cells
    from cntfet.cnt_cell_page import config_name
    sc = score_cells(manager, device_name)
    scores = {}
    if sc.get('ok'):
        for c in sc['cells']:
            if c.get('ok'):
                key = (c.get('frame') or {}).get('cell')
                scores[key] = {'score': c['score'],
                               'libertyCell': c['cell'],
                               'run': sc.get('run')}
    data_note = ('' if sc.get('ok') else
                 f"no characterized run — {sc.get('error', '')[:120]}")
    if lod == 'real':
        total_fets = 0
        for i in insts:
            key = i['cell']
            total_fets += (24 if key not in CELL_LIBRARY
                           else len(_flatten(key)))
        projected = total_fets * 8
        if projected > k['real_entry_budget']:
            return {'ok': False,
                    'error': f'lod=real would need ~{projected} '
                             f'entries (budget '
                             f'{k["real_entry_budget"]}) — '
                             'lod=blackbox keeps one instancable '
                             'box per cell, carrying the real '
                             'characterized data; raise the knob '
                             'deliberately if you want the '
                             'geometry'}
        return {'ok': False,
                'error': 'lod=real at block scale is a follow-up '
                         '(v1 renders cells as instancable '
                         'black-boxes with real data; the cell '
                         'scenes hold the real geometry one scale '
                         'down)'}
    w0, h0, _view = _fet_footprint(manager, device_name, tech)
    s = FIELD_KNOBS['scene_scale']
    import math as _m
    ncols = max(1, int(_m.ceil(_m.sqrt(len(insts)))))
    pitch_x = w0 * 1.6
    pitch_y = h0 * 3.2
    entries = []
    for idx, i in enumerate(insts):
        key = i['cell']
        nfet = 24 if key not in CELL_LIBRARY else len(_flatten(key))
        col, row = idx % ncols, idx // ncols
        x = (col - (ncols - 1) / 2.0) * pitch_x
        y = -(row - (len(insts) / ncols) / 2.0) * pitch_y
        w = w0 * (0.7 + 0.08 * nfet)
        h = h0 * 2.2
        cfg = config_name(key, device_name)
        user = {'kind': 'cell-instance', 'inst': i.get('inst', ''),
                'cell': key, 'fets': nfet, 'ports': i.get('ports'),
                'cellConfig': cfg,
                'data': scores.get(key,
                                   {'refusal': data_note
                                    or 'cell not in the latest '
                                       'run'}),
                'cellScene': scene_name('cell', dim, key,
                                        device_name),
                'summaryPath': f'/api/fet/cellcfg/{key}/'
                               f'{device_name}/summary',
                'page': f'/display/cell-detail?object={key}'
                        f'&device={device_name}'}
        e = _box(f'c{idx}-{i.get("inst", key)}',
                 f"{i.get('inst', '')} {key} ({nfet} FETs)"
                 + (f" score {scores[key]['score']:.2f}"
                    if key in scores else ' — uncharacterized'),
                 x, y, w, h, dim, _P_STYLE_3D if key in scores
                 else _TRACK_STYLE_3D, _2D['cellbox'],
                 h0 * 0.6, user, s)
        if dim == '2d':
            e['scale'] = _box2d_scale(w, h, s)
        entries.append(e)
    name = scene_name('block', dim, block, device_name)
    width = ncols * pitch_x
    height = (len(insts) / ncols + 1) * pitch_y
    fields = {
        'name': name,
        'description': (
            f'MULTISCALE block scene (blackbox): {block} as '
            f'{len(insts)} instancable cell boxes on {device_name}; '
            'every box carries its CellFETConfiguration\'s REAL '
            'characterized data (or the fill refusal) + the cell '
            'scene one scale down — the scale-boundary contract. '
            + (data_note or '')),
        'dimensionality': dim, 'coordinate_system': 'math',
        'unit_scale': 1.0,
        'viewport_json': json.dumps(
            {'center': [0, 0] if dim == '2d' else [0, 0, 0],
             'extent': ([round(width * s * 0.6, 3),
                         round(height * s * 0.6, 3)]
                        if dim == '2d' else
                        [round(width * s * 0.6, 3),
                         round(height * s * 0.6, 3),
                         round(h0 * s * 2, 3)])}),
        'bound_classes_json': '[]',
        'definition': json.dumps({
            'freestandingOnly': True, 'level': 'block',
            'lod': 'blackbox', 'block': block,
            'device': device_name, 'freestanding': entries}),
        'camera_json': (json.dumps({
            'mode': 'orbit', 'projection': 'orthographic',
            'position': [0.0, 0.0, max(width * s, 2.0)],
            'target': [0.0, 0.0, 0.0], 'up': [0, 1, 0],
        }) if dim == '3d' else ''),
        'owning_module': 'cntfet',
    }
    return {'ok': True, 'fields': fields, 'entries': len(entries),
            'instances': len(insts), 'lod': 'blackbox', 'dim': dim,
            'characterized': bool(scores)}


def _style_for_kind(kind):
    return {'contact': 'fet-pd-contact', 'extension': 'fet-si-sd-n',
            'oxide': 'fet-sio2-oxide',
            'gate': 'fet-gate-metal'}.get(kind, 'fet-band-none')


def _slug(text):
    return str(text).replace(' ', '-').replace('/', '-')


def upsert_scene(manager, fields):
    """Idempotent-by-name SimSpaceDefinition upsert (rows persist,
    appear under /sim-spaces)."""
    tables = getattr(manager, 'objectTables', None)
    if tables is None:
        return {'ok': False, 'error': 'no manager'}
    table = tables.setdefault('SimSpaceDefinition', {})
    row = next((r for r in table.values()
                if getattr(r, 'name', '') == fields['name']), None)
    db = getattr(manager, 'db', None)
    if row is not None:
        for kk, v in fields.items():
            setattr(row, kk, v)
        action = 'updated'
    else:
        from simSpace.sim_space_definition import SimSpaceDefinition
        row = SimSpaceDefinition(manager=manager, **fields)
        table[id(row)] = row
        action = 'created'
    try:
        if db is not None:
            db.saveInstanceInDB(row)
    except Exception:
        pass
    return {'ok': True, 'scene': fields['name'], 'action': action}


def generate_scene(manager, level, key, device_name, dim='3d',
                   lod=None):
    """The GET handler's worker: build + upsert + stats."""
    if level == 'cell':
        rep = cell_scene(manager, key, device_name, dim=dim,
                         lod=lod or 'real')
    elif level == 'block':
        rep = block_scene(manager, key, device_name, dim=dim,
                          lod=lod or 'blackbox')
    else:
        return {'ok': False, 'error': 'level = cell | block'}
    if not rep.get('ok'):
        return rep
    up = upsert_scene(manager, rep['fields'])
    if not up.get('ok'):
        return up
    return {'ok': True, 'scene': up['scene'], 'action': up['action'],
            'level': level, 'dim': dim, 'lod': rep['lod'],
            'entries': rep['entries'],
            'instances': rep['instances'],
            'ladder': ('FET scene fet-3d-{device} one scale down; '
                       'block scenes one scale up — the multiscale '
                       'chain'),
            'note': rep['fields']['description'][:220]}
