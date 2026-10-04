"""
@module pcb.custom.kicad_read

READ a KiCad project (`.kicad_sch` + `.kicad_pcb` + `.kicad_pro` + the project's lib tables) into ROW DICTS — the pcb rows of
plan §2 — without KiCad (pcb.custom.sexpr). Pure: files in ({relative path: text}), dicts out; pcb.custom.ingest adds the
engine's checks and the exports. Every row carries where it came from (the file sha256), nothing is typed by hand.

  read_project(files, board=None) → {'board', 'files': {path: sha256}, 'Schematic', 'SchematicSheet', 'Symbol', 'Part', 'Footprint',
                                     'LandPattern', 'PcbBoard', 'Placement', 'BoardNet', 'Route', 'problems'}

Rules (each stated where it is applied):
  * a reference starting with '#' (#PWR01, #FLG05) is a power symbol / flag — a schematic object, never a Part;
  * a multi-unit part (U1 units A/B/C) is ONE reference;
  * a Part = one (symbol, value, footprint as placed) group — the BOM line;
  * a library nickname the project's sym-lib-table / fp-lib-table maps to ${KIPRJMOD} is `project`, anything else is
    `kicad-official` (the global tables of a stock KiCad install name only the official libraries);
  * a net's class: GND* = ground, a leading '+' or VCC/VDD/VBAT/HT = power, else signal — the net NAME is the only source here;
  * routes are SUMMARISED per net (plan §2: "summarised rather than every segment").
"""
import hashlib
import json
import math
import os
import re

from pcb.custom import sexpr as S

POWER_RE = re.compile(r'^(\+|VCC|VDD|VBAT|VIN|HT\b)', re.I)


def sha(text):
    return hashlib.sha256(text.encode() if isinstance(text, str) else text).hexdigest()


def _lib_table(text):
    """nickname → uri from a sym-lib-table / fp-lib-table."""
    if not text:
        return {}
    t = S.parse(text)
    return {S.value(lib, 'name'): S.value(lib, 'uri') for lib in S.find(t, 'lib')}


def _source(nick, table):
    uri = table.get(nick, '')
    return 'project' if '${KIPRJMOD}' in uri else 'kicad-official'


def _net_class(name):
    if name.upper().startswith('GND'):
        return 'ground'
    return 'power' if POWER_RE.match(name) else 'signal'


def _pick(files, ext, board):
    cands = sorted(n for n in files if n.endswith(ext) and '/' not in n)
    if board and '%s%s' % (board, ext) in cands:
        return '%s%s' % (board, ext)
    return cands[0] if cands else None


# ------------------------------------------------------------------ the schematic
def _lib_symbol_pins(lsym):
    pins = []
    for p in S.find_all(lsym, 'pin'):
        if len(p) > 1 and not isinstance(p[1], list) and str(p[1]) not in ('',) and S.find(p, 'number'):
            pins.append({'number': S.value(p, 'number'), 'name': S.value(p, 'name'), 'type': str(p[1])})
    return sorted({(x['number'], x['name'], x['type']) for x in pins}, key=lambda t: (len(t[0]), t[0]))


def read_schematic(files, top, board):
    tree = S.parse(files[top])
    problems = ['%s: %s' % (top, w) for w in S.check_kicad(tree, 'kicad_sch')]
    sheets = [(top, '/', '1')]
    queue = [(top, tree, '/')]
    placed, power = [], []
    counts = {'wires': 0, 'labels': 0, 'junctions': 0, 'no_connects': 0}
    lib_syms = {}
    seen = set()
    while queue:
        fname, t, path = queue.pop(0)
        if fname in seen:
            continue
        seen.add(fname)
        for ls in (S.find(S.find(t, 'lib_symbols')[0], 'symbol') if S.find(t, 'lib_symbols') else []):
            lib_syms.setdefault(str(ls[1]), ls)
        counts['wires'] += len(S.find(t, 'wire'))
        counts['labels'] += sum(len(S.find(t, k)) for k in ('label', 'global_label', 'hierarchical_label'))
        counts['junctions'] += len(S.find(t, 'junction'))
        counts['no_connects'] += len(S.find(t, 'no_connect'))
        for s in S.find(t, 'symbol'):
            ref = S.prop(s, 'Reference')
            rec = {'lib_id': S.value(s, 'lib_id'), 'ref': ref, 'value': S.prop(s, 'Value'), 'footprint': S.prop(s, 'Footprint'),
                   'in_bom': S.value(s, 'in_bom', 'yes'), 'on_board': S.value(s, 'on_board', 'yes'), 'unit': S.value(s, 'unit', '1'),
                   'sheet': path, 'datasheet': S.prop(s, 'Datasheet')}
            (power if ref.startswith('#') else placed).append(rec)
        for sh in S.find(t, 'sheet'):   # a hierarchical sheet: its file joins the walk
            sub = S.prop(sh, 'Sheetfile') or S.prop(sh, 'Sheet file')
            name = S.prop(sh, 'Sheetname') or S.prop(sh, 'Sheet name') or sub
            if sub in files:
                sheets.append((sub, path + name + '/', str(len(sheets) + 1)))
                queue.append((sub, S.parse(files[sub]), path + name + '/'))
            else:
                problems.append('sheet %s names %s, which is not among the files' % (name, sub))
    tb = S.find(tree, 'title_block')
    sch = {'name': board, 'board': board, 'file': top, 'sha256': sha(files[top]), 'format_version': S.value(tree, 'version'),
           'generator': S.value(tree, 'generator'), 'title': S.value(tb[0], 'title') if tb else '', 'sheets': len(sheets),
           'symbols': len(placed) + len(power), 'power_symbols': len(power), 'origin': 'ingested', 'licence_notes': '', 'notes': ''}
    sch.update(counts)
    per_sheet = {}
    for p in placed + power:
        per_sheet[p['sheet']] = per_sheet.get(p['sheet'], 0) + 1
    sheet_rows = [{'name': '%s:%s' % (board, path), 'schematic': board, 'path': path, 'page': page, 'file': f, 'symbols': per_sheet.get(path, 0), 'notes': ''}
                  for f, path, page in sheets]
    return sch, sheet_rows, placed, power, lib_syms, problems


# ------------------------------------------------------------------ the board
def _arc_len(st, mid, en):
    (x1, y1), (x2, y2), (x3, y3) = st, mid, en
    d = 2 * (x1 * (y2 - y3) + x2 * (y3 - y1) + x3 * (y1 - y2))
    if abs(d) < 1e-12:
        return math.dist(st, en)
    ux = ((x1 ** 2 + y1 ** 2) * (y2 - y3) + (x2 ** 2 + y2 ** 2) * (y3 - y1) + (x3 ** 2 + y3 ** 2) * (y1 - y2)) / d
    uy = ((x1 ** 2 + y1 ** 2) * (x3 - x2) + (x2 ** 2 + y2 ** 2) * (x1 - x3) + (x3 ** 2 + y3 ** 2) * (x2 - x1)) / d
    r = math.dist((ux, uy), st)
    a1, a2, a3 = (math.atan2(y - uy, x - ux) for x, y in (st, mid, en))
    sweep = (a3 - a1) % (2 * math.pi)
    if not ((a2 - a1) % (2 * math.pi) < sweep):
        sweep = 2 * math.pi - sweep
    return r * sweep


def _pt(e, head):
    x, y, _ = S.xy(e, head)
    return (x, y)


def _edge_bbox(tree):
    xs, ys, items = [], [], 0
    for head in ('gr_line', 'gr_arc', 'gr_rect', 'gr_circle', 'gr_poly'):
        for g in S.find(tree, head):
            if S.value(g, 'layer') != 'Edge.Cuts':
                continue
            items += 1
            for k in ('start', 'end', 'mid', 'center'):
                if S.find(g, k):
                    x, y = _pt(g, k)
                    xs.append(x)
                    ys.append(y)
            for p in S.find_all(g, 'xy'):
                xs.append(S.num(p[1]))
                ys.append(S.num(p[2]))
    if not xs:
        return None, 0
    return (min(xs), min(ys), max(xs), max(ys)), items


def _footprint_dims(fp):
    pads = [p for p in S.find(fp, 'pad')]
    centers = [_pt(p, 'at') for p in pads]
    pitch = min((math.dist(a, b) for i, a in enumerate(centers) for b in centers[i + 1:] if math.dist(a, b) > 1e-6), default=0.0)
    first = pads[0] if pads else None
    size = S.find(first, 'size')[0] if first is not None and S.find(first, 'size') else ['size', 0, 0]
    drill = S.find(first, 'drill')[0] if first is not None and S.find(first, 'drill') else None
    dval = 0.0
    if drill is not None:
        nums = [x for x in drill[1:] if not isinstance(x, list) and x != 'oval']
        dval = S.num(nums[0]) if nums else 0.0
    cx, cy = [], []
    for head in ('fp_line', 'fp_rect', 'fp_poly', 'fp_circle'):
        for g in S.find(fp, head):
            if S.value(g, 'layer') in ('F.CrtYd', 'B.CrtYd'):
                if head == 'fp_circle':   # (center x y) (end x y): the bounding square of the circle
                    (ccx, ccy), rr = _pt(g, 'center'), math.dist(_pt(g, 'center'), _pt(g, 'end'))
                    cx += [ccx - rr, ccx + rr]
                    cy += [ccy - rr, ccy + rr]
                    continue
                for k in ('start', 'end'):
                    if S.find(g, k):
                        x, y = _pt(g, k)
                        cx.append(x)
                        cy.append(y)
                for p in S.find_all(g, 'xy'):
                    cx.append(S.num(p[1]))
                    cy.append(S.num(p[2]))
    return {'pads': len(pads), 'pitch_mm': round(pitch, 4), 'pad_w_mm': S.num(size[1]), 'pad_h_mm': S.num(size[2] if len(size) > 2 else size[1]),
            'drill_mm': dval, 'pad_shape': str(first[3]) if first is not None and len(first) > 3 and not isinstance(first[3], list) else '',
            'courtyard_w_mm': round(max(cx) - min(cx), 4) if cx else 0.0, 'courtyard_h_mm': round(max(cy) - min(cy), 4) if cy else 0.0}


def read_pcb(files, top, board, fp_table, pro):
    tree = S.parse(files[top])
    problems = ['%s: %s' % (top, w) for w in S.check_kicad(tree, 'kicad_pcb')]
    layers = []
    for lay in S.find(tree, 'layers')[0][1:] if S.find(tree, 'layers') else []:
        if isinstance(lay, list) and len(lay) >= 3:
            layers.append({'id': str(lay[0]), 'name': str(lay[1]), 'type': str(lay[2]), 'user_name': str(lay[3]) if len(lay) > 3 else ''})
    copper = [x for x in layers if x['name'].endswith('.Cu')]
    stack = []
    for lay in S.find_all(S.find(tree, 'setup')[0], 'layer') if S.find(tree, 'setup') else []:
        stack.append({'layer': str(lay[1]), 'type': S.value(lay, 'type'), 'thickness': S.num(S.value(lay, 'thickness'), 0.0), 'material': S.value(lay, 'material')})
    bbox, edge_items = _edge_bbox(tree)
    nets = {str(n[1]): str(n[2]) for n in S.find(tree, 'net') if len(n) > 2}
    placements, footprints, landpatterns, pad_nets = [], {}, {}, {}
    for fp in S.find(tree, 'footprint'):
        lib_id = str(fp[1])
        nick, _, fname = lib_id.partition(':')
        ref = S.prop(fp, 'Reference')
        x, y, rot = S.xy(fp)
        attr = S.find(fp, 'attr')
        attr_v = str(attr[0][1]) if attr and len(attr[0]) > 1 else ''
        dims = _footprint_dims(fp)
        for p in S.find(fp, 'pad'):
            n = S.find(p, 'net')
            if n and len(n[0]) > 2:
                pad_nets[str(n[0][2])] = pad_nets.get(str(n[0][2]), 0) + 1
        placements.append({'name': '%s:%s' % (board, ref), 'board': board, 'ref': ref, 'value': S.prop(fp, 'Value'), 'footprint': lib_id, 'part': '',
                           'x_mm': x, 'y_mm': y, 'rotation': rot, 'side': 'back' if S.value(fp, 'layer') == 'B.Cu' else 'front', 'attr': attr_v,
                           'pads': dims['pads'], 'notes': ''})
        if lib_id not in footprints:
            src = _source(nick, fp_table)
            mod = 'footprints.pretty/%s.kicad_mod' % fname if src == 'project' else ''
            footprints[lib_id] = {'name': lib_id, 'lib': nick, 'footprint': fname, 'source': src,
                                  'lib_version': ('the project\'s %s' % fp_table.get(nick, '').replace('${KIPRJMOD}/', '')) if src == 'project' else '',
                                  'lib_sha256': sha(files[mod]) if mod in files else '', 'licence': '', 'pad_count': dims['pads'],
                                  'mount': 'smd' if attr_v == 'smd' else ('tht' if attr_v == 'through_hole' else attr_v), 'description': S.value(fp, 'descr'),
                                  'notes': '' if mod in files or src != 'project' else 'the project library file is not among the files — sha from the board only'}
            landpatterns[lib_id] = dict({'name': lib_id, 'footprint': lib_id, 'package': fname, 'density': 'as-drawn', 'facts_json': '{}',
                                         'derivation': 'as drawn in the footprint (pad 1 size + drill, the smallest pad-to-pad distance, the courtyard '
                                                       'bounding box) — NOT derived from a datasheet', 'compared_to': '', 'difference': '',
                                         'undetermined': 'no DatasheetFact rows for this package: the IPC-7351-style derivation and the comparison come at pcb-3',
                                         'notes': ''}, **{k: v for k, v in dims.items()})
    routes = {}
    for seg in S.find(tree, 'segment') + S.find(tree, 'arc'):
        code = S.value(seg, 'net')
        r = routes.setdefault(code, {'segments': 0, 'vias': 0, 'length_mm': 0.0, 'widths': set(), 'layers': set()})
        r['segments'] += 1
        st, en = _pt(seg, 'start'), _pt(seg, 'end')
        r['length_mm'] += _arc_len(st, _pt(seg, 'mid'), en) if seg[0] == 'arc' else math.dist(st, en)
        r['widths'].add(S.num(S.value(seg, 'width')))
        r['layers'].add(S.value(seg, 'layer'))
    for via in S.find(tree, 'via'):
        r = routes.setdefault(S.value(via, 'net'), {'segments': 0, 'vias': 0, 'length_mm': 0.0, 'widths': set(), 'layers': set()})
        r['vias'] += 1
    zones = S.find(tree, 'zone')
    zone_nets = {S.value(z, 'net_name') for z in zones}
    route_rows, net_rows = [], []
    for code, name in sorted(nets.items(), key=lambda kv: int(kv[0]) if kv[0].isdigit() else 0):
        if not name:
            continue
        r = routes.get(code, {'segments': 0, 'vias': 0, 'length_mm': 0.0, 'widths': set(), 'layers': set()})
        route_rows.append({'name': '%s:%s' % (board, name), 'board': board, 'net': name, 'segments': r['segments'], 'vias': r['vias'],
                           'length_mm': round(r['length_mm'], 3), 'min_width_mm': min(r['widths']) if r['widths'] else 0.0,
                           'widths_json': json.dumps(sorted(r['widths'])), 'layers_json': json.dumps(sorted(r['layers'])), 'pads': pad_nets.get(name, 0),
                           'notes': 'also a copper zone (pour)' if name in zone_nets else ''})
        net_rows.append({'name': '%s:%s' % (board, name), 'board': board, 'net': name, 'net_class': _net_class(name), 'volts': 0.0,
                         'circuit_net': '', 'fact': '', 'notes': 'ingested from %s (KiCad net code %s); class from the name only' % (top, code)})
    rules = {}
    try:
        p = json.loads(pro) if pro else {}
        dr = (p.get('board') or {}).get('design_settings') or {}
        rules = {k: v for k, v in (dr.get('rules') or {}).items() if k.startswith('min_')}
        cls = ((p.get('net_settings') or {}).get('classes') or [{}])[0]
        rules.update({'netclass_%s' % k: cls[k] for k in ('clearance', 'track_width', 'via_diameter', 'via_drill') if k in cls})
    except ValueError:
        problems.append('the .kicad_pro is not JSON — its design rules are not read')
    gen = S.find(tree, 'general')
    board_row = {'name': board, 'board_definition': '', 'title': '', 'file': top, 'sha256': sha(files[top]), 'format_version': S.value(tree, 'version'),
                 'generator': S.value(tree, 'generator'), 'copper_layers': len(copper), 'layers_json': json.dumps(layers), 'stackup_json': json.dumps(stack),
                 'thickness_mm': S.num(S.value(gen[0], 'thickness')) if gen else 0.0,
                 'width_mm': round(bbox[2] - bbox[0], 4) if bbox else 0.0, 'height_mm': round(bbox[3] - bbox[1], 4) if bbox else 0.0,
                 'outline_json': json.dumps({'bbox_mm': [round(v, 4) for v in bbox] if bbox else [], 'edge_items': edge_items, 'layer': 'Edge.Cuts'}),
                 'design_rules_json': json.dumps(rules, sort_keys=True), 'fab_rule_set': '', 'footprints': len(placements),
                 'nets': len(net_rows), 'segments': len(S.find(tree, 'segment')) + len(S.find(tree, 'arc')), 'vias': len(S.find(tree, 'via')),
                 'zones': len(zones), 'licence': '', 'licence_source': '', 'provenance': 'ingested:%s sha256 %s' % (top, sha(files[top])), 'notes': ''}
    if not bbox:
        problems.append('no Edge.Cuts outline — the board size is unknown')
    return board_row, placements, list(footprints.values()), list(landpatterns.values()), net_rows, route_rows, problems


# ------------------------------------------------------------------ the whole project
def read_project(files, board=None):
    sch_name = _pick(files, '.kicad_sch', board)
    pcb_name = _pick(files, '.kicad_pcb', board)
    if not sch_name and not pcb_name:
        raise ValueError('no .kicad_sch or .kicad_pcb among %s' % sorted(files)[:8])
    board = board or os.path.splitext(sch_name or pcb_name)[0]
    sym_table, fp_table = _lib_table(files.get('sym-lib-table', '')), _lib_table(files.get('fp-lib-table', ''))
    out = {'board': board, 'files': {n: sha(t) for n, t in sorted(files.items())}, 'problems': []}
    placed, lib_syms = [], {}
    if sch_name:
        sch, sheets, placed, power, lib_syms, probs = read_schematic(files, sch_name, board)
        out.update(Schematic=[sch], SchematicSheet=sheets)
        out['problems'] += probs
    pl_rows = []
    if pcb_name:
        b, pl_rows, fps, lps, nets, routes, probs = read_pcb(files, pcb_name, board, fp_table, files.get('%s.kicad_pro' % board) or files.get(_pick(files, '.kicad_pro', board) or '', ''))
        out.update(PcbBoard=[b], Placement=pl_rows, Footprint=fps, LandPattern=lps, BoardNet=nets, Route=routes)
        out['problems'] += probs
    symbols = []
    for lib_id, ls in sorted(lib_syms.items()):
        nick, _, name = lib_id.partition(':')
        src = _source(nick, sym_table)
        lib_file = sym_table.get(nick, '').replace('${KIPRJMOD}/', '')
        pins = _lib_symbol_pins(ls)
        symbols.append({'name': lib_id, 'lib': nick, 'symbol': name, 'source': src,
                        'lib_version': ("the project's %s" % lib_file) if src == 'project' else '',
                        'lib_sha256': sha(files[lib_file]) if src == 'project' and lib_file in files else '', 'licence': '',
                        'pin_count': len(pins), 'pins_json': json.dumps([{'number': n, 'name': nm, 'type': t} for n, nm, t in pins]),
                        'description': S.prop(ls, 'Description'), 'notes': 'embedded in %s (lib_symbols)' % sch_name})
    out['Symbol'] = symbols
    fp_of_ref = {p['ref']: p['footprint'] for p in pl_rows}
    attr_of_ref = {p['ref']: p['attr'] for p in pl_rows}
    groups = {}
    for s in placed:
        fp = fp_of_ref.get(s['ref'], s['footprint'])
        key = (s['lib_id'], s['value'], fp)
        g = groups.setdefault(key, {'refs': set(), 'sch_fp': set(), 'in_bom': set()})
        g['refs'].add(s['ref'])
        g['sch_fp'].add(s['footprint'])
        g['in_bom'].add(s['in_bom'])
    parts = []
    for (lib_id, val, fp), g in sorted(groups.items(), key=lambda kv: sorted(kv[1]['refs'])[0]):
        refs = sorted(g['refs'], key=lambda r: (re.sub(r'\d+', '', r), int(re.sub(r'\D', '', r) or 0)))
        notes = []
        if g['sch_fp'] - {fp}:
            notes.append('the schematic names footprint %s; the board places %s' % (', '.join(sorted(g['sch_fp'])), fp))
        if g['in_bom'] == {'no'}:
            notes.append('excluded from the BOM (in_bom no)')
        attr = attr_of_ref.get(refs[0], '')
        name = '%s:%s' % (board, refs[0] if len(refs) == 1 else '%s..%s' % (refs[0], refs[-1]))
        parts.append({'name': name, 'board': board, 'value': val, 'manufacturer': '', 'mpn': '', 'package': fp.partition(':')[2],
                      'mount': 'smd' if attr == 'smd' else ('tht' if attr == 'through_hole' else ''), 'symbol': lib_id, 'footprint': fp,
                      'refs_json': json.dumps(refs), 'qty': len(refs), 'device_definition': '', 'lifecycle': '', 'lifecycle_source': '', 'datasheet': '',
                      'provenance': 'ingested:%s' % (sch_name or pcb_name), 'licence_notes': '',
                      'undetermined': 'manufacturer, MPN and lifecycle: the KiCad project names none', 'notes': '; '.join(notes)})
    out['Part'] = parts
    part_of = {r: p['name'] for p in parts for r in json.loads(p['refs_json'])}
    for p in pl_rows:
        p['part'] = part_of.get(p['ref'], '')
        if not p['part']:
            p['notes'] = 'on the board but not in the schematic'
    return out


def read_dir(path):
    """{relative path: text} of a KiCad project directory (design files, lib tables, the project's .pretty footprints)."""
    out = {}
    for root, dirs, fns in os.walk(path):
        dirs[:] = sorted(d for d in dirs if d.endswith('.pretty') or root == path and not d.startswith('.') and d not in ('3d_shapes', '3dmodels'))
        for fn in sorted(fns):
            if fn.endswith(('.kicad_sch', '.kicad_pcb', '.kicad_pro', '.kicad_sym', '.kicad_mod', '.kicad_dru')) or fn in ('sym-lib-table', 'fp-lib-table'):
                fp = os.path.join(root, fn)
                out[os.path.relpath(fp, path)] = open(fp, encoding='utf-8').read()
    return out
