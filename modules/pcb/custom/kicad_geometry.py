"""
@module pcb.custom.kicad_geometry

kxc-4 (AI-Notes/plans/KICAD_INTERCHANGE_PLAN.md): THE PCB COMPLETE - the board file's copper and drawing as rows, so the single-Board design view
(BENCH_BOARDS_PLAN bob-3: layers, circuits in the layers, thermal, silkscreen, footprints) has its data. Pure (no KiCad):

  pads(tree, board)          PcbPad: every pad of every footprint - number, type (thru_hole / smd / np_thru_hole / connect), shape, size, drill, layers,
                             net, ERC pin type + function, board position and angle (footprint frame rotated, as pcbnew places it)
  net_geometry(tree, board)  NetGeometry: ONE row per net (D-kxc-2, recommended): its track segments, arcs and vias as lists, total length, layers
  zones(tree, board)         PcbZone: copper pours, keep-outs and teardrops - net, layers, outline, filled area (shoelace over the filled polygons)
  net_classes(pro, nets, board)  PcbNetClass: the .kicad_pro classes (clearance, track width, vias, diff pairs) and which nets each holds
  design_rules(dru, board)   PcbDesignRule: each (rule ...) of a .kicad_dru - its condition and constraints
  layer_graphics(tree, board)  PcbLayerGraphics: per (layer, item kind) - silkscreen, fab, courtyard, edge, user drawings - count + bounding box,
                             board-level and inside footprints together

D-kxc-2 is his to confirm; the per-net shape keeps a routed board (10^4 segments) at one row per net.
"""
import json
import math
import re

from pcb.custom import sexpr as S


def _pt(e, head):
    x, y, _ = S.xy(e, head)
    return x, y


def _place(fx, fy, frot, px, py):
    a = math.radians(frot)
    return round(fx + px * math.cos(a) + py * math.sin(a), 4), round(fy - px * math.sin(a) + py * math.cos(a), 4)


def _strs(e, head):
    f = S.find(e, head)
    return [str(x) for x in f[0][1:]] if f else []


def pads(tree, board):
    out = []
    for fp in S.find(tree, 'footprint'):
        ref = S.prop(fp, 'Reference')
        fx, fy, frot = S.xy(fp)
        side = 'bottom' if S.value(fp, 'layer') == 'B.Cu' else 'top'
        for i, p in enumerate(S.find(fp, 'pad')):
            num = str(p[1]) if len(p) > 1 else ''
            ptype = str(p[2]) if len(p) > 2 else ''
            shape = str(p[3]) if len(p) > 3 and not isinstance(p[3], list) else ''
            px, py, prot = S.xy(p)
            x, y = _place(fx, fy, frot, px, py)
            size = S.find(p, 'size')
            drill = S.find(p, 'drill')
            dnums = [S.num(v) for v in (drill[0][1:] if drill else []) if not isinstance(v, list) and v != 'oval']
            net = S.find(p, 'net')
            out.append({'name': '%s:%s:%s#%d' % (board, ref, num, i), 'board': board, 'ref': ref, 'number': num, 'pad_type': ptype, 'shape': shape,
                        'x_mm': x, 'y_mm': y, 'angle': round((prot if prot else frot) % 360, 4), 'side': side,
                        'size_w_mm': S.num(size[0][1]) if size else 0.0, 'size_h_mm': S.num(size[0][2]) if size and len(size[0]) > 2 else 0.0,
                        'drill_mm': dnums[0] if dnums else 0.0, 'drill_oval': bool(drill) and 'oval' in [str(v) for v in drill[0][1:]],
                        'layers_json': json.dumps(_strs(p, 'layers')), 'net': str(net[0][2]) if net and len(net[0]) > 2 else '',
                        'pintype': S.value(p, 'pintype'), 'pinfunction': S.value(p, 'pinfunction'), 'notes': ''})
    return out


def _arc_len(st, mid, en):
    from pcb.custom.kicad_read import _arc_len as A
    return A(st, mid, en)


def net_geometry(tree, board):
    names = {str(n[1]): str(n[2]) for n in S.find(tree, 'net') if len(n) > 2}
    nets = {}

    def row(code):
        return nets.setdefault(code, {'segments': [], 'arcs': [], 'vias': [], 'length': 0.0, 'layers': set()})
    for s in S.find(tree, 'segment'):
        r = row(S.value(s, 'net'))
        (x1, y1), (x2, y2) = _pt(s, 'start'), _pt(s, 'end')
        r['segments'].append([x1, y1, x2, y2, S.num(S.value(s, 'width')), S.value(s, 'layer')])
        r['length'] += math.dist((x1, y1), (x2, y2))
        r['layers'].add(S.value(s, 'layer'))
    for a in S.find(tree, 'arc'):
        r = row(S.value(a, 'net'))
        st, mid, en = _pt(a, 'start'), _pt(a, 'mid'), _pt(a, 'end')
        r['arcs'].append([*st, *mid, *en, S.num(S.value(a, 'width')), S.value(a, 'layer')])
        r['length'] += _arc_len(st, mid, en)
        r['layers'].add(S.value(a, 'layer'))
    for v in S.find(tree, 'via'):
        r = row(S.value(v, 'net'))
        x, y = _pt(v, 'at')
        r['vias'].append([x, y, S.num(S.value(v, 'size')), S.num(S.value(v, 'drill')), _strs(v, 'layers')])
    out = []
    for code, r in sorted(nets.items(), key=lambda kv: int(kv[0]) if str(kv[0]).isdigit() else 0):
        net = names.get(str(code), '')
        out.append({'name': '%s:%s' % (board, net or 'net-code-%s' % code), 'board': board, 'net': net, 'segments_json': json.dumps(r['segments']),
                    'arcs_json': json.dumps(r['arcs']), 'vias_json': json.dumps(r['vias']), 'segments': len(r['segments']), 'arcs': len(r['arcs']),
                    'vias': len(r['vias']), 'length_mm': round(r['length'], 4), 'layers_json': json.dumps(sorted(r['layers'])),
                    'notes': '' if net else 'tracks with no net (KiCad net code %s)' % code})
    return out


def _area(pts):
    return abs(sum(x1 * y2 - x2 * y1 for (x1, y1), (x2, y2) in zip(pts, pts[1:] + pts[:1]))) / 2.0


def _poly(e):
    return [(S.num(xy[1]), S.num(xy[2])) for xy in S.find_all(e, 'xy')]


def zones(tree, board):
    out = []
    for i, z in enumerate(S.find(tree, 'zone')):
        layers = _strs(z, 'layers') or ([S.value(z, 'layer')] if S.value(z, 'layer') else [])
        outline = _poly(S.find(z, 'polygon')[0]) if S.find(z, 'polygon') else []
        filled = sum(_area(_poly(fp)) for fp in S.find(z, 'filled_polygon'))
        attr = S.find(z, 'attr')
        kind = 'keepout' if S.find(z, 'keepout') else ('teardrop' if attr and S.find(attr[0], 'teardrop') else 'copper')
        fill = S.find(z, 'fill')
        out.append({'name': '%s:zone#%d' % (board, i), 'board': board, 'net': S.value(z, 'net_name'), 'kind': kind, 'zone_name': S.value(z, 'name'),
                    'layers_json': json.dumps(layers), 'priority': int(S.num(S.value(z, 'priority'), 0)), 'outline_json': json.dumps(outline),
                    'outline_area_mm2': round(_area(outline), 4) if outline else 0.0, 'filled_area_mm2': round(filled, 4),
                    'min_thickness_mm': S.num(S.value(z, 'min_thickness'), 0.0),
                    'thermal_gap_mm': S.num(S.value(fill[0], 'thermal_gap'), 0.0) if fill else 0.0,
                    'thermal_bridge_mm': S.num(S.value(fill[0], 'thermal_bridge_width'), 0.0) if fill else 0.0, 'notes': ''})
    return out


def net_classes(pro_text, nets, board):
    """The .kicad_pro's net classes; `nets` = the board's net names (each assigned by an explicit assignment, a pattern, else Default)."""
    try:
        ns = (json.loads(pro_text) if pro_text else {}).get('net_settings') or {}
    except ValueError:
        return []
    assign = dict(ns.get('netclass_assignments') or {})
    patterns = [(p.get('pattern', ''), p.get('netclass', '')) for p in (ns.get('netclass_patterns') or [])]

    def cls_of(net):
        if net in assign:
            v = assign[net]
            return v[0] if isinstance(v, list) and v else v
        for pat, c in patterns:
            rx = '^' + re.escape(pat).replace(r'\*', '.*').replace(r'\?', '.') + '$'
            if re.match(rx, net):
                return c
        return 'Default'
    members = {}
    for n in nets:
        members.setdefault(cls_of(n), []).append(n)
    keys = ('clearance', 'track_width', 'via_diameter', 'via_drill', 'microvia_diameter', 'microvia_drill', 'diff_pair_width', 'diff_pair_gap', 'priority')
    return [dict({'name': '%s:%s' % (board, c['name']), 'board': board, 'netclass': c['name'], 'nets_json': json.dumps(sorted(members.get(c['name'], []))),
                  'net_count': len(members.get(c['name'], [])), 'notes': ''}, **{k: float(c[k]) if k in c else -1.0 for k in keys}) for c in ns.get('classes') or []]


def design_rules(dru_text, board):
    out = []
    if not dru_text:
        return out
    for r in S.find(S.parse('(dru %s)' % dru_text), 'rule'):
        cons = [{'kind': str(c[1]), 'args': ' '.join(str(x) if not isinstance(x, list) else S.write(x) for x in c[2:])} for c in S.find(r, 'constraint')]
        out.append({'name': '%s:%s' % (board, str(r[1])), 'board': board, 'rule': str(r[1]), 'condition': S.value(r, 'condition'), 'layer': S.value(r, 'layer'),
                    'constraints_json': json.dumps(cons), 'notes': ''})
    return out


GRAPHICS = ('gr_line', 'gr_arc', 'gr_circle', 'gr_rect', 'gr_poly', 'gr_text', 'gr_text_box', 'fp_line', 'fp_arc', 'fp_circle', 'fp_rect', 'fp_poly', 'fp_text', 'property')


def layer_graphics(tree, board):
    acc = {}

    def take(e, head, ox=0.0, oy=0.0, orot=0.0):
        layer = S.value(e, 'layer')
        if not layer or (head == 'property' and S.find(e, 'hide')):
            return
        pts = []
        for k in ('start', 'end', 'mid', 'center', 'at'):
            if S.find(e, k):
                pts.append(_pt(e, k))
        pts += _poly(e)
        pts = [_place(ox, oy, orot, x, y) for x, y in pts] if (ox or oy or orot) else pts
        r = acc.setdefault((layer, head.replace('fp_', 'gr_') if head != 'property' else 'gr_text'), {'count': 0, 'xs': [], 'ys': []})
        r['count'] += 1
        r['xs'] += [p[0] for p in pts]
        r['ys'] += [p[1] for p in pts]
    for el in tree[1:]:
        if isinstance(el, list) and el and el[0] in GRAPHICS:
            take(el, el[0])
    for fp in S.find(tree, 'footprint'):
        fx, fy, frot = S.xy(fp)
        for el in fp[1:]:
            if isinstance(el, list) and el and el[0] in GRAPHICS:
                take(el, el[0], fx, fy, frot)
    return [{'name': '%s:%s:%s' % (board, layer, kind), 'board': board, 'layer': layer, 'item': kind, 'count': r['count'],
             'bbox_json': json.dumps([round(min(r['xs']), 3), round(min(r['ys']), 3), round(max(r['xs']), 3), round(max(r['ys']), 3)] if r['xs'] else []),
             'notes': ''} for (layer, kind), r in sorted(acc.items())]
