"""
@module board.custom.board_details

bob-3 (AI-Notes/plans/BENCH_BOARDS_PLAN.md): THE BOARD DETAILS - the definition level of one Board, the page one dives into from the Bench (his ruling
2026-10-30: the Bench works on footholds; how a board is defined is its own level, with its own page; for a PCB that page becomes the single-Board
design simulation view). One door shape for every definition kind, one row set per part:

  part(kind, definition, which, manager)  → (rows, why)   which = summary | footholds | nets | parts | layers | coverage
      summary    what defines this board, from what documents / files, and what each tab holds for it
      footholds  the bench contract (board.custom.footholds)
      nets       datasheet: the BoardNet rows; geometry: the joined nodes (strips, rails); layers: our own SchematicNet rows (kxc-2)
      parts      datasheet: the BoardHardware components; layers: the placed symbols (SchematicSymbol, kxc-1) with their simulation fields
      layers     datasheet: the enclosure levels (die -> package -> board); layers: the PCB's copper / mask / silk layers + stackup (PcbBoard)
      coverage   layers: what the KiCad ingest understood of each file (KiCadCoverage); other kinds: nothing (said)
      pads       layers: every pad (PcbPad, kxc-4) - the footprints part of the single-Board design view
      copper     layers: each net's copper (NetGeometry): segments, vias, length, narrowest track, and its DC resistance from the copper itself -
                 rho L / (w t) per segment with t = the layer's copper thickness from the board's stackup and rho by definition (IEC 60028); the
                 net's sum is an UPPER BOUND on any one path (a branching net is not one series track) - the 'circuits in the layers'
      zones      layers: copper pours / keep-outs / teardrops with their filled copper area (PcbZone) - the copper a thermal view spreads heat in
      drawings   layers: the drawing on every layer (PcbLayerGraphics) - silkscreen, fab, courtyard, edge, user
      rules      layers: net classes (PcbNetClass) + custom rules (PcbDesignRule)
      runs       layers: the simulation runs kept for the PCB's schematic (SpiceRun, kxc-3b: pcb.custom.spice_runs), newest first; the chart reads one
"""
import json

from board.custom import footholds as FH

PARTS = ('summary', 'footholds', 'nets', 'parts', 'layers', 'coverage', 'pads', 'copper', 'zones', 'drawings', 'rules', 'runs')
#: bob-3b: annealed copper's resistivity at 20 °C BY DEFINITION - the International Annealed Copper Standard (IEC 60028: 1/58 ohm mm2/m)
COPPER_OHM_M = 1.0 / 58 * 1e-6
COPPER_CITE = 'IEC 60028 International Annealed Copper Standard: 1/58 ohm mm2/m = 1.7241e-8 ohm m at 20 C'


def _table(manager, cls):
    return list(((getattr(manager, 'objectTables', None) or {}).get(cls) or {}).values()) if manager is not None else []


def _attrs(o, keys):
    return {k: (o.get(k, '') if isinstance(o, dict) else getattr(o, k, '')) for k in keys}


def _tables(manager):
    from board.custom import hardware_system as HS
    return HS.default_tables(manager)


def _datasheet(definition, which, manager):
    t = _tables(manager)
    if which == 'nets':
        return [{'net': n['net'], 'class': n['net_class'], 'volts': n['volts'] if n['volts'] or n['net_class'] == 'ground' else -1.0, 'fact': n.get('fact', ''),
                 'notes': n.get('notes', '')} for n in t.get('BoardNet', []) if n['board'] == definition]
    if which == 'parts':
        hw = next((h for h in t.get('BoardHardware', []) if h['board'] == definition), {})
        return [{'ref': c.get('ref', ''), 'value': c.get('value', ''), 'role': c.get('role', ''), 'kicad_part': ('%s:%s' % (c['lib'], c['part'])) if c.get('part') else '',
                 'footprint': c.get('footprint', ''), 'undetermined': c.get('undetermined', '')} for c in json.loads(hw.get('components_json') or '[]')]
    if which == 'layers':
        return [{'level': e.get('level', ''), 'enclosure': e['name'], 'kind': e.get('kind', ''), 'parent': e.get('parent', ''), 'notes': e.get('notes', '')}
                for e in t.get('HardwareEnclosure', []) if e.get('board') == definition]
    return None


def _geometry(definition, which, manager):
    if which == 'nets':
        rows, _ = FH.for_definition('geometry', definition, manager=manager)
        nodes = {}
        for r in rows:
            nodes.setdefault(r['node'], []).append(r['foothold'])
        return [{'node': n, 'footholds': len(fs), 'first': fs[0], 'last': fs[-1]} for n, fs in sorted(nodes.items())]
    return None


def _layers(definition, which, manager):
    if which == 'nets':
        return [_attrs(o, ('net', 'scope', 'endpoints', 'pintypes_json', 'kicad_check', 'aliases_json')) for o in _table(manager, 'SchematicNet')
                if getattr(o, 'board', '') == definition]
    if which == 'parts':
        return [_attrs(o, ('ref', 'unit', 'lib_id', 'value', 'footprint', 'sheet', 'sim_device', 'sim_type', 'sim_params', 'sim_library', 'dnp'))
                for o in _table(manager, 'SchematicSymbol') if getattr(o, 'board', '') == definition and getattr(o, 'power', '') != 'yes']
    if which == 'layers':
        pcb = next((o for o in _table(manager, 'PcbBoard') if getattr(o, 'name', '') == definition), None)
        if pcb is None:
            return []
        stack = {s['layer']: s for s in json.loads(getattr(pcb, 'stackup_json', '[]') or '[]')}
        return [{'layer': lay['name'], 'id': lay['id'], 'type': lay['type'], 'user_name': lay.get('user_name', ''),
                 'stackup_type': stack.get(lay['name'], {}).get('type', ''), 'thickness_mm': stack.get(lay['name'], {}).get('thickness', ''),
                 'material': stack.get(lay['name'], {}).get('material', '')} for lay in json.loads(getattr(pcb, 'layers_json', '[]') or '[]')]
    if which == 'coverage':
        return [_attrs(o, ('file', 'element', 'count', 'handling', 'polari_class', 'next_slice', 'notes')) for o in _table(manager, 'KiCadCoverage')
                if getattr(o, 'board', '') == definition]
    mine = lambda cls: [o for o in _table(manager, cls) if getattr(o, 'board', '') == definition]   # noqa: E731
    if which == 'pads':
        return [_attrs(o, ('ref', 'number', 'pad_type', 'shape', 'x_mm', 'y_mm', 'angle', 'side', 'size_w_mm', 'size_h_mm', 'drill_mm', 'layers_json', 'net', 'pintype',
                           'pinfunction')) for o in mine('PcbPad')]
    if which == 'copper':
        return copper_rows(mine('NetGeometry'), _stackup(manager, definition))
    if which == 'zones':
        return [_attrs(o, ('net', 'kind', 'zone_name', 'layers_json', 'priority', 'outline_area_mm2', 'filled_area_mm2', 'min_thickness_mm', 'thermal_gap_mm',
                           'thermal_bridge_mm')) for o in mine('PcbZone')]
    if which == 'drawings':
        return [_attrs(o, ('layer', 'item', 'count', 'bbox_json')) for o in mine('PcbLayerGraphics')]
    if which == 'runs':
        from pcb.custom import spice_runs as SR
        return [_attrs(r, ('name', 'ran_at', 'analysis', 'plot', 'points', 'vectors', 'status', 'source', 'host', 'engine', 'deck_sha256'))
                for r in SR.runs(manager, definition)]
    if which == 'rules':
        return [dict({'what': 'net class'}, **_attrs(o, ('netclass', 'clearance', 'track_width', 'via_diameter', 'via_drill', 'diff_pair_width', 'diff_pair_gap', 'net_count',
                                                         'nets_json'))) for o in mine('PcbNetClass')] + \
               [dict({'what': 'custom rule'}, **_attrs(o, ('rule', 'condition', 'layer', 'constraints_json'))) for o in mine('PcbDesignRule')]
    return None


def _stackup(manager, definition):
    pcb = next((o for o in _table(manager, 'PcbBoard') if getattr(o, 'name', '') == definition), None)
    return {s['layer']: s for s in json.loads(getattr(pcb, 'stackup_json', '[]') or '[]')} if pcb is not None else {}


def copper_rows(geoms, stack):
    """One row per net: its copper and the DC resistance the copper itself gives (cited rho, the stackup's thickness; unknown thickness -> -1, said)."""
    out = []
    for g in geoms:
        segs = json.loads(getattr(g, 'segments_json', '[]') or '[]')
        ohm, unknown, widths = 0.0, set(), []
        for x1, y1, x2, y2, w, layer in segs:
            t_mm = float((stack.get(layer) or {}).get('thickness') or 0)
            widths.append(w)
            if t_mm <= 0 or w <= 0:
                unknown.add(layer)
                continue
            ohm += COPPER_OHM_M * (((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5 / 1000) / ((w / 1000) * (t_mm / 1000))
        out.append({'net': getattr(g, 'net', ''), 'segments': getattr(g, 'segments', 0), 'arcs': getattr(g, 'arcs', 0), 'vias': getattr(g, 'vias', 0),
                    'length_mm': getattr(g, 'length_mm', 0.0), 'narrowest_mm': min(widths) if widths else -1.0, 'layers_json': getattr(g, 'layers_json', '[]'),
                    'dc_ohm_upper_bound': round(ohm, 6) if segs and not unknown else -1.0,
                    'basis': ('rho %s; copper thickness per layer from the stackup (%s); arcs not counted' % (COPPER_CITE, ', '.join(
                        '%s %s mm' % (k, (stack.get(k) or {}).get('thickness')) for k in sorted(json.loads(getattr(g, 'layers_json', '[]') or '[]')))))
                             if segs and not unknown else ('no copper thickness for %s in the stackup' % ', '.join(sorted(unknown)) if unknown else 'no tracks')})
    return sorted(out, key=lambda r: r['net'])


SUMMARY = {'datasheet': 'a dev board known from its vendor documents: the pinout and header tables (ConnectorPin, BoardPin), the chip\'s datasheet '
                        '(SocPin, PinFunction, ElectricalCharacteristic) and the board\'s own parts (BoardHardware); every number cited (DatasheetFact)',
           'geometry': 'a breadboard known from its counts: numbered strips of 5 + 5 holes split by the centre trench, power rails, the 2.54 mm pitch - '
                       'the holes and which are joined are DERIVED, nothing is drawn by hand',
           'layers': 'a PCB known from its design files (a KiCad import): every file kept, every element accounted for (Coverage), the schematic\'s own '
                     'nets (Polari\'s, checked against KiCad), the placed parts with their simulation fields, the copper / mask / silk layers'}


def part(kind, definition, which, manager=None):
    if kind not in FH.KINDS:
        return [], 'no definition kind %r - %s' % (kind, ' | '.join(FH.KINDS))
    if which not in PARTS:
        return [], 'no part %r - %s' % (which, ' | '.join(PARTS))
    if which == 'footholds':
        return FH.for_definition(kind, definition, manager=manager)
    if which == 'summary':
        rows, why = FH.for_definition(kind, definition, manager=manager)
        tabs = {p: len(part(kind, definition, p, manager)[0]) for p in ('nets', 'parts', 'layers', 'coverage', 'pads', 'zones')}
        return [{'board': '%s/%s' % (kind, definition), 'defined_by': SUMMARY[kind], 'footholds': len(rows) if rows else -1,
                 'nodes': len({r['node'] for r in rows}) if rows else -1, 'footholds_note': why,
                 'nets': tabs['nets'], 'parts': tabs['parts'], 'layers': tabs['layers'], 'coverage_rows': tabs['coverage'], 'pads': tabs['pads'], 'zones': tabs['zones']}], ''
    rows = {'datasheet': _datasheet, 'geometry': _geometry, 'layers': _layers}[kind](definition, which, manager)
    if rows is None:
        return [], 'a %s board has no %s at its definition level' % (kind, which)
    return rows, '' if rows else 'nothing stored for %s/%s %s' % (kind, definition, which)
