"""
@module board.custom.bench_scene

bob-4 (BENCH_BOARDS_PLAN.md): THE BENCH DRAWN - every Board on the Bench with its footholds, and the wires between them, as the pin view's own payload, so
the one sanctioned drawing component (hardware-pin-view) draws a bench with no new component: GET /api/board/bench:<bench>/pin-view
(/display/pin-view?board=bench:home-bench). His rulings: the Bench is pins and their connections, kept to the minimum a person has to read - so a surface
is a whole board, a mark is a foothold, a line is a bench connection, and a pin's drive words are its foothold's (cited) drive data plus the bench checks
(over-voltage, contention, short) from board.custom.bench_pins. No netlist here (that is the popup).

Placement: boards left to right in bench order, GAP_MM apart (a drawing knob). Inside a board every foothold sits where its definition puts it (the board
file's pads, the datasheet drawing, the breadboard geometry); footholds with no cited position are set out in rows per connector under the board at the
2.54 mm pitch (a breadboard's holes by strip and column, from their names) and say so in the pin's notes. A frame with y up (an Eagle board file) is turned to the pin view's y-down frame.
"""
import json
import re

GAP_MM = 12.0      # drawing knob: the space between two boards
PITCH = 2.54
MARGIN = 3.0       # drawing knob: the board outline beyond its outermost foothold
UNKNOWN = -1.0
HOLE = re.compile(r'^r(\d+)([a-j])$')
RAIL = re.compile(r'^rail:(top|bottom):([+-]):(\d+)$')


def _rail_word(f):
    if f['direction'] != 'supply':
        return 'logic-io' if f['direction'] in ('in', 'out', 'inout') else 'undetermined'
    if f['rail_volts'] == 0.0:
        return 'GND'
    return {5.0: '5V', 3.3: '3V3'}.get(round(f['rail_volts'], 1), f['net'] or 'undetermined')


def _local(feet):
    """{foothold: (x, y, cited)} in a y-down frame from the board's top-left, + the board's (w, h)."""
    placed = [f for f in feet if f['x_mm'] != UNKNOWN and f['y_mm'] != UNKNOWN]
    y_up = any('y UP' in (f.get('position_basis') or '') for f in placed)
    out = {}
    if placed:
        x0, x1 = min(f['x_mm'] for f in placed), max(f['x_mm'] for f in placed)
        y0, y1 = min(f['y_mm'] for f in placed), max(f['y_mm'] for f in placed)
        for f in placed:
            y = (y1 - f['y_mm']) if y_up else (f['y_mm'] - y0)
            out[f['foothold']] = (f['x_mm'] - x0 + MARGIN, y + MARGIN, True)
        w, h = x1 - x0 + 2 * MARGIN, y1 - y0 + 2 * MARGIN
    else:
        w, h = 0.0, 0.0
    rest = [f for f in feet if f['foothold'] not in out]
    holes = [f for f in rest if HOLE.match(f['foothold']) or RAIL.match(f['foothold'])]
    if holes and len(holes) == len(rest):   # a breadboard with no drawable geometry: its hole NAMES still say strip and column - set out as that grid
        base = h + (PITCH if h else MARGIN)
        rails = sorted({RAIL.match(f['foothold']).group(1, 2) for f in holes if RAIL.match(f['foothold'])})
        top = [r for r in rails if r[0] == 'top']
        for f in holes:
            m, r = HOLE.match(f['foothold']), RAIL.match(f['foothold'])
            if m:
                col = 'abcdefghij'.index(m.group(2))
                out[f['foothold']] = (MARGIN + (int(m.group(1)) - 1) * PITCH, base + (len(top) + col + (1 if col >= 5 else 0)) * PITCH, False)
            else:
                k = rails.index(r.group(1, 2))
                row = k if r.group(1) == 'top' else len(top) + 11 + (k - len(top))
                out[f['foothold']] = (MARGIN + (int(r.group(3)) - 1) * PITCH, base + row * PITCH, False)
        xs, ys = [v[0] for v in out.values()], [v[1] for v in out.values()]
        return out, max(xs) + MARGIN, max(ys) + MARGIN
    groups = {}
    for f in rest:
        m = re.match(r'^(.+):(\d+)$', f['foothold'])
        groups.setdefault(m.group(1) if m else '', []).append((int(m.group(2)) if m else 0, f))
    y = h + (PITCH if h else MARGIN)
    for conn in sorted(groups):
        for i, (_n, f) in enumerate(sorted(groups[conn], key=lambda t: (t[0], t[1]['foothold']))):
            out[f['foothold']] = (MARGIN + i * PITCH, y, False)
        w = max(w, MARGIN * 2 + (len(groups[conn]) - 1) * PITCH)
        y += PITCH * 2
    return out, max(w, 10.0), max(y if rest else h, 10.0)


def _pin(bid, label, f, x, y, cited, checks):
    fams = json.loads(f.get('families_json') or '[]')
    finding = checks.get((bid, f['foothold']), {})
    drive = {'supply': 'returns' if f['rail_volts'] == 0.0 else 'supplies', 'in': 'high-impedance', 'out': 'sources-or-sinks',
             'inout': 'not-driven', 'passive': 'not-driven'}.get(f['direction'], 'undetermined')
    limit = 'over' if finding.get('checks') else ('within-recommended' if f['source_ma'] > 0 and finding else 'unchecked' if f['source_ma'] <= 0 else 'undetermined')
    return {'id': 'foothold:%s:%s' % (bid, f['foothold']), 'level': 'board', 'surface': 'bench-board:%s' % bid, 'label': f['label'] or f['foothold'],
            'number': None, 'x': round(x, 4), 'y': round(y, 4), 'side': f.get('side', ''), 'kind': 'foothold:%s' % f['kind'], 'bonded': True,
            'soc': '', 'soc_pin': f.get('chip_pin', ''), 'canonical': f.get('chip_pin', ''), 'functions': [], 'default_function': '', 'drive_class': '',
            'drive_role': drive, 'ref': f['name'], 'stage': 'available' if f['direction'] in ('in', 'out', 'inout') else 'unassigned',
            'stage_why': 'a foothold of %s (%s)' % (label, f['definition_kind']), 'consumers': [], 'lit': None, 'dim': False, 'short_label': '',
            'signals': [], 'families': fams, 'drive_relevant': f['direction'] in ('supply', 'in', 'out', 'inout'), 'drive_status': drive,
            'drive_why': '; '.join(x for x in (f.get('drive_basis', ''), f.get('undetermined', ''), finding.get('checks', ''), finding.get('notes', '')) if x),
            'rail': _rail_word(f), 'pull': 'none', 'limit_class': limit,
            'limit_basis': ('source %s mA / sink %s mA' % (f['source_ma'], f['sink_ma'])) if f['source_ma'] > 0 else (f.get('undetermined') or 'no current limit cited'),
            'group_budget': [], 'signal_relevant': f['direction'] in ('in', 'out', 'inout'), 'activated': None, 'capable': [], 'lifecycle': [], 'phase_basis': [],
            'notes': 'node %s; position %s' % (f['node'], (f.get('position_basis') or 'cited') if cited else
                                               'not cited: set out under the board by its name - strip / column for a hole, connector order for a pin (a drawing knob)'),
            'bench_status': 'finding' if finding.get('checks') else 'ok'}


def build(bench, manager=None):
    """-> (status, the pin-view payload of a bench)."""
    from board.custom import bench_nets as BN
    from board.custom import bench_pins as BP
    from board.custom import pin_view_modes as MD
    from board.custom import pv_families as F
    from board.custom import pv_shapes as S
    feet, by_id = BN._boards(bench, manager)
    if feet is None:
        return 404, {'ok': False, 'error': 'no bench named %r' % bench}
    wiring = BN.connections_of(bench, manager)
    boards = {bid: {'label': by_id[bid]['label'], 'footholds': f, 'definition': by_id[bid]['definition']} for bid, f in feet.items()}
    rows, problems = BP.pin_rows(boards, wiring)
    checks = {}
    for r in rows:
        for fid in r['footholds'].split(', '):
            checks[(r['board'], fid)] = r
    surfaces, pins, shapes, x = [], {}, {}, 0.0
    for bid in feet:
        local, w, h = _local(feet[bid])
        sid, shape = 'bench-board:%s' % bid, 'pv-bench-scene-%s' % re.sub(r'[^A-Za-z0-9_.-]', '_', bid)
        mine = []
        for f in feet[bid]:
            lx, ly, cited = local[f['foothold']]
            p = _pin(bid, by_id[bid]['label'], f, lx, ly, cited, checks)
            pins[p['id']] = p
            mine.append(p['id'])
        surfaces.append({'id': sid, 'kind': 'board', 'level': 'board', 'title': by_id[bid]['label'], 'parent': '', 'shape': shape, 'x': round(x, 4), 'y': 0.0, 'rot': 0,
                         'w': round(w, 4), 'h': round(h, 4), 'ref': bid, 'component': '', 'soc': '', 'package': '', 'pin_ids': mine,
                         'notes': '%s (%s %s): %d footholds' % (by_id[bid]['label'], by_id[bid].get('definition_kind', ''), by_id[bid]['definition'], len(mine)),
                         'pin_count': len(mine)})
        shapes[shape] = {'name': shape, 'display_name': '%s outline (the footholds\' extent + a %g mm margin: a drawing knob)' % (by_id[bid]['label'], MARGIN),
                         'parameters': {'vertices': [[0, 0], [round(w, 4), 0], [round(w, 4), round(h, 4)], [0, round(h, 4)]]}}
        x += w + GAP_MM
    conns = []
    for c in wiring:
        a, b = 'foothold:%s:%s' % (c.get('from_board'), c.get('from_foothold')), 'foothold:%s:%s' % (c.get('to_board'), c.get('to_foothold'))
        if a not in pins or b not in pins:
            continue
        pa, pb = pins[a], pins[b]
        conns.append({'id': '%s--%s' % (a, b), 'a': a, 'b': b, 'kind': c.get('kind', 'wire'), 'via': c.get('kind', 'wire'), 'via_part': '', 'note': c.get('label', ''),
                      'signal': {'a': pa['drive_status'], 'b': pb['drive_status'], 'family': (pa['families'] or pb['families'] or ['gpio'])[0], 'protocol_signal': '',
                                 'function_a': '', 'function_b': '', 'capable': [], 'note': 'a bench connection (%s)' % c.get('kind', 'wire')},
                      'drive': {'a': pa['drive_status'], 'b': pb['drive_status'], 'rail': pa['rail'] if pa['rail'] != 'logic-io' else pb['rail'], 'domain': '',
                                'pull': 'none', 'via': c.get('kind', 'wire'), 'via_part': '', 'limit_verdict': 'over' if 'over' in (pa['limit_class'], pb['limit_class']) else 'unchecked',
                                'limit_basis': pa['drive_why'] if pa['bench_status'] == 'finding' else pb['drive_why'] if pb['bench_status'] == 'finding' else ''},
                      'use': {'tasks': [], 'purposes': [], 'stage': 'available'}, 'stage': 'available', 'drive_relevant': True, 'signal_relevant': True})
    findings = sum(1 for r in rows if r['status'] == 'finding')
    notes = ['bench %s: %d boards, %d footholds, %d connections; %d pin %s with a finding' % (bench, len(surfaces), len(pins), len(conns), findings, 'group' if findings == 1 else 'groups')]
    return 200, {'ok': True, 'board': 'bench:%s' % bench, 'source': 'bench (board.custom.bench_scene)', 'system': '', 'binding': '', 'phase': 'runtime', 'blank': 'board',
                 'phase_info': None, 'candidate': None, 'protocol': None, 'mission': {'name': '', 'status': 'none', 'why': ''},
                 'stage': {'stage': 'base', 'binding': '', 'claims': 0, 'committed_claims': 0, 'undetermined': [p for p in problems][:20], 'notes': notes, 'requested': 'base'},
                 'vocabulary': dict(F.vocabulary(), drive=MD.vocabulary()), 'bench': None,
                 'layout': dict(S.LABEL, note='drawing knobs (mm): part titles and pin labels are drawn in model units at this font size'),
                 'surfaces': surfaces, 'pins': list(pins.values()), 'connections': conns, 'unresolved': [], 'shapes': shapes,
                 'counts': {'surfaces': len(surfaces), 'pins': len(pins), 'connections': len(conns), 'unresolved': 0, 'by_level': {'board': len(pins)},
                            'by_kind': {k: sum(1 for c in conns if c['kind'] == k) for k in sorted({c['kind'] for c in conns})}, 'findings': findings},
                 'echo': {}}
