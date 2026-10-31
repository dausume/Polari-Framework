"""
@module board.custom.pcb_scene

bob-3f (BENCH_BOARDS_PLAN bob-3): ONE PCB DRAWN with WHERE ITS HEAT SITS - the pin view's own payload, so the one sanctioned drawing component
(hardware-pin-view) draws it with no new component: GET /api/board/pcb:<board>/pin-view (/display/pin-view?board=pcb:ecc83), mounted on the Board
Details Thermal tab. A surface is the board in its own Edge.Cuts shape (bob-3e), a mark is a pad (PcbPad), and `thermal` is the temperature-rise field
of pcb.custom.thermal_spread (the plate FEM) on the same frame - the component shades it under the pads. Each pad's notes carry the rise where it sits.
No field (no run, no layout, nothing placed) -> `thermal.why` says so in words and the board is drawn without it.

Frame: the board's top-left (Edge.Cuts bounding box) is (0, 0), y down - KiCad's own frame shifted, never turned.
"""
import json
import re


def _rail(net):
    n = (net or '').upper().lstrip('+')
    if n.startswith('GND') or n in ('VSS', '0V'):
        return 'GND'
    return {'5V': '5V', '3V3': '3V3', '3.3V': '3V3', 'VBUS': 'VBUS'}.get(n, 'undetermined')


def _rise_at(field, x, y):
    """The field's value at board point (x, y) mm - the nearest map point (None off the board)."""
    if not field:
        return None
    xs, ys = field['xs_mm'], field['ys_mm']
    i = min(range(len(xs)), key=lambda k: abs(xs[k] - x))
    j = min(range(len(ys)), key=lambda k: abs(ys[k] - y))
    return field['rise_c'][j][i]


def _pin(sid, board, p, ox, oy, rise):
    x, y = p['x_mm'] - ox, p['y_mm'] - oy
    rail = _rail(p.get('net'))
    heat = ('rise +%.2f K here (the plate FEM, Thermal tab)' % rise) if rise is not None else 'no temperature field (see the Thermal tab)'
    return {'id': 'pad:%s:%s:%s' % (board, p['ref'], p['number']), 'level': 'board', 'surface': sid, 'label': '%s.%s' % (p['ref'], p['number']),
            'number': None, 'x': round(x, 4), 'y': round(y, 4), 'side': '', 'kind': 'pad:%s' % (p.get('pad_type') or ''), 'bonded': True,
            'soc': '', 'soc_pin': '', 'canonical': '', 'functions': [], 'default_function': '', 'drive_class': '',
            'drive_role': 'returns' if rail == 'GND' else 'undetermined', 'ref': p['name'], 'stage': 'unassigned',
            'stage_why': 'a pad of %s on net %s' % (p['ref'], p.get('net') or '(none)'), 'consumers': [], 'lit': None, 'dim': False, 'short_label': '',
            'signals': [], 'families': [], 'drive_relevant': False, 'drive_status': 'returns' if rail == 'GND' else 'undetermined',
            'drive_why': 'net %s' % (p.get('net') or '(none)'), 'rail': rail, 'pull': 'none', 'limit_class': 'unchecked', 'limit_basis': 'a pad carries no cited limit',
            'group_budget': [], 'signal_relevant': False, 'activated': None, 'capable': [], 'lifecycle': [], 'phase_basis': [],
            'notes': '%s pad %s, %.2f x %.2f mm; net %s; %s' % (p.get('shape') or '', p['number'], p.get('size_w_mm') or 0, p.get('size_h_mm') or 0,
                                                              p.get('net') or '(none)', heat),
            'rise_c': rise}


def build(board, manager=None, rows=None, powers=None):
    """-> (status, the pin-view payload of one PCB with its temperature field)."""
    from board.custom import pin_view_modes as MD
    from board.custom import pv_families as F
    from board.custom import pv_shapes as S
    from pcb.custom import thermal_spread as TS
    from pcb.custom.thermal import _rows_of
    rows = rows if rows is not None else _rows_of(manager, board, TS.CLASSES)
    pcb = next(iter(rows.get('PcbBoard') or []), None)
    if pcb is None:
        return 404, {'ok': False, 'error': 'no PCB named %r (a KiCad board file ingested)' % board}
    shape_row = json.loads(pcb.get('outline_json') or '{}')
    bbox = shape_row.get('bbox_mm') or [0.0, 0.0, pcb.get('width_mm') or 0.0, pcb.get('height_mm') or 0.0]
    ox, oy, w, h = bbox[0], bbox[1], float(pcb.get('width_mm') or 0), float(pcb.get('height_mm') or 0)
    outline = [[round(x - ox, 4), round(y - oy, 4)] for x, y in shape_row.get('polygon_mm') or []] or [[0, 0], [w, 0], [w, h], [0, h]]

    summary, _hot, field, why = TS.spread(manager, board, rows=rows, powers=powers)
    if not why and (field is None or (summary or {}).get('max_rise_c', -1.0) < 0):
        why = (summary or {}).get('basis', '') or 'no temperature field'
    sid, shape = 'pcb:%s' % board, 'pv-pcb-scene-%s' % re.sub(r'[^A-Za-z0-9_.-]', '_', board)
    pins = [_pin(sid, board, p, ox, oy, _rise_at(field, p['x_mm'] - ox, p['y_mm'] - oy) if not why else None) for p in rows.get('PcbPad') or []]
    surface = {'id': sid, 'kind': 'board', 'level': 'board', 'title': pcb.get('title') or board, 'parent': '', 'shape': shape, 'x': 0.0, 'y': 0.0, 'rot': 0,
               'w': round(w, 4), 'h': round(h, 4), 'ref': board, 'component': '', 'soc': '', 'package': '', 'pin_ids': [p['id'] for p in pins],
               'notes': '%s: %d pads; the outline is %s' % (board, len(pins), 'its Edge.Cuts shape' if shape_row.get('polygon_mm') else 'its Edge.Cuts box'),
               'pin_count': len(pins)}
    shapes = {shape: {'name': shape, 'display_name': '%s outline (Edge.Cuts)' % board,
                      'parameters': {'vertices': outline,
                                     'cutouts': [[[round(x - ox, 4), round(y - oy, 4)] for x, y in hl] for hl in shape_row.get('holes_mm') or []]}}}
    thermal = {'surface': sid, 'why': why, 'unit': 'K above ambient'}
    if not why:
        thermal.update(xs=field['xs_mm'], ys=field['ys_mm'], rise=field['rise_c'], max=summary['max_rise_c'], mean=summary['mean_rise_c'],
                       title='Temperature rise: peak +%.1f K, mean +%.1f K (%s, h = %g W/m2K)' % (summary['max_rise_c'], summary['mean_rise_c'],
                                                                                                summary['source'], summary['h_w_m2k']),
                       basis=summary['basis'])
    notes = ['PCB %s: %d pads; %s' % (board, len(pins), thermal.get('title') or ('no temperature field: %s' % why))]
    return 200, {'ok': True, 'board': 'pcb:%s' % board, 'source': 'pcb (board.custom.pcb_scene)', 'system': '', 'binding': '', 'phase': 'runtime', 'blank': 'board',
                 'phase_info': None, 'candidate': None, 'protocol': None, 'mission': {'name': '', 'status': 'none', 'why': ''},
                 'stage': {'stage': 'base', 'binding': '', 'claims': 0, 'committed_claims': 0, 'undetermined': [], 'notes': notes, 'requested': 'base'},
                 'vocabulary': dict(F.vocabulary(), drive=MD.vocabulary()), 'bench': None,
                 'layout': dict(S.LABEL, note='drawing knobs (mm): part titles and pin labels are drawn in model units at this font size'),
                 'surfaces': [surface], 'pins': pins, 'connections': [], 'unresolved': [], 'shapes': shapes, 'thermal': thermal,
                 'counts': {'surfaces': 1, 'pins': len(pins), 'connections': 0, 'unresolved': 0, 'by_level': {'board': len(pins)}, 'by_kind': {}, 'findings': 0},
                 'echo': {}}
