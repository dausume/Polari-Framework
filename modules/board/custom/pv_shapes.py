"""
@module board.custom.pv_shapes

pv-0 (PIN_VIEW_PLAN.md 2.1 + 2.6): MATH-DEFINED SHAPES for the pin view. A shape is one `MathShapeDefinition` row (mathshapes; family primitive, kind polygon: the body outline, millimetres,
y down) whose `parameters_json` also carries the GENERATOR and its inputs; the PIN POSITIONS are COMPUTED from them here, never hand-placed:

  two-row    DIP / SPDIP / SOIC     body w x h, pin count, pitch, row spacing        pins 1..N/2 down the left row, the rest up the right row
  quad       TQFP / QFP / QFN       body, pin count, pitch, ring side (+ exposed pad) pins 1.. down the left side, along the bottom, up the right, along the top (counter-clockwise)
  die        the silicon            an inner square; N pads spread over its perimeter (ordered by the leg each bonds to)
  part-box   a board part           a small box; named pins alternate left / right
  board      a board outline        outline polygon + holes + header rows at pitch + placed footprints (the chips, the parts)

Every number is CITED (document + page/table) in the row's `cited` map or is a DRAWING KNOB (listed in `knobs`: the view needs proportions, not mechanical truth). The die pad positions are
a knob — no die map is cited (die pads are `undetermined` in the exposure rows). Nothing here is typed twice: pin counts, pitches and names come from PackageDefinition / PackageContact /
ConnectorPin / EnclosureContact rows; only the drawing dimensions live here.

    python3 -m board.custom.pv_shapes [--json]       the shape rows and the pin counts they compute
"""
import json
import math
import sys

from board.custom import exposure_view as V

PREFIX = 'pv-'
MM = 'mm'
D328 = 'Microchip ATmega48A/PA/88A/PA/168A/PA/328/P datasheet DS40002061B'
D16U2 = 'Atmel ATmega8U2/16U2/32U2 datasheet doc7799D'
UNO_DS = 'Arduino UNO R3 product datasheet A000066 (cached A000066-datasheet.pdf)'
EPS = 1e-9


def _c(value, doc, page):
    return {'value': value, 'document': doc, 'page_table': page}


# ---------------------------------------------------------------- generators (pure: parameters in, pin positions out)
def two_row(p):
    """-> {'ring': {w, h}, 'pins': [{number, x, y, side, index}], 'pad': None}; origin = the body centre. Pin 1 top of the left row (the pin-1 notch end)."""
    n, pitch, rs = int(p['pins']), float(p['pitch']), float(p['row_spacing'])
    half = n // 2
    span = (half - 1) * pitch
    pins = []
    for i in range(n):
        if i < half:
            pins.append({'number': i + 1, 'x': -rs / 2, 'y': -span / 2 + i * pitch, 'side': 'left', 'index': i})
        else:
            j = i - half
            pins.append({'number': i + 1, 'x': rs / 2, 'y': span / 2 - j * pitch, 'side': 'right', 'index': j})
    return {'ring': {'w': rs, 'h': span}, 'pins': pins, 'pad': None}


def quad(p):
    """-> as two_row; `ring` = the square the pin centres lie on (side `ring_side`), `pad` = the exposed pad {x, y, w, h} when the package has one. Pin 1 at the top end of the left side."""
    n, pitch, ring = int(p['pins']), float(p['pitch']), float(p['ring_side'])
    per = n // 4
    half = ring / 2
    pins = []
    for i in range(n):
        side_i, j = divmod(i, per)
        off = -(per - 1) * pitch / 2 + j * pitch
        if side_i == 0:
            x, y, side = -half, off, 'left'
        elif side_i == 1:
            x, y, side = off, half, 'bottom'
        elif side_i == 2:
            x, y, side = half, -off, 'right'
        else:
            x, y, side = -off, -half, 'top'
        pins.append({'number': i + 1, 'x': x, 'y': y, 'side': side, 'index': j})
    pad = None
    if p.get('pad'):
        pad = {'x': 0.0, 'y': 0.0, 'w': float(p['pad'][0]), 'h': float(p['pad'][1]), 'number': n + 1}
    return {'ring': {'w': ring, 'h': ring}, 'pins': pins, 'pad': pad}


def perimeter_points(n, w, h):
    """n points spread evenly over the perimeter of a w x h rectangle centred on the origin, starting at the top-left going clockwise (y down). Pure geometry — the die pad ring."""
    per = 2 * (w + h)
    out = []
    for i in range(n):
        d = (i + 0.5) * per / n
        if d < w:
            x, y, side = -w / 2 + d, -h / 2, 'top'
        elif d < w + h:
            x, y, side = w / 2, -h / 2 + (d - w), 'right'
        elif d < 2 * w + h:
            x, y, side = w / 2 - (d - w - h), h / 2, 'bottom'
        else:
            x, y, side = -w / 2, h / 2 - (d - 2 * w - h), 'left'
        out.append({'x': x, 'y': y, 'side': side, 'index': i})
    return out


def die(p, n):
    s = float(p['size'][0]), float(p['size'][1])
    pts = perimeter_points(n, s[0], s[1])
    return {'ring': {'w': s[0], 'h': s[1]}, 'pins': pts, 'pad': None}


def part_box(p):
    names = list(p['pin_names'])
    w, h = float(p['box'][0]), float(p['box'][1])
    pitch = float(p.get('pitch', 1.27))
    rows = max(1, math.ceil(len(names) / 2)) if len(names) > 1 else 1
    pins = []
    for i, name in enumerate(names):
        if len(names) == 1:
            pins.append({'name': name, 'x': 0.0, 'y': 0.0, 'side': 'center', 'index': 0})
            continue
        col, row = i % 2, i // 2
        pins.append({'name': name, 'x': (w / 2) if col else -w / 2, 'y': -(rows - 1) * pitch / 2 + row * pitch, 'side': 'right' if col else 'left', 'index': row})
    return {'ring': {'w': w, 'h': max(h, (rows - 1) * pitch)}, 'pins': pins, 'pad': None}


def header(p):
    """A header row (1 x N, or 2 x N/2 for an ICSP): {number: (x, y)} in the board frame; `pitch` is the cited 2.54 mm."""
    n, pitch, rows = int(p['pins']), float(p['pitch']), int(p.get('rows', 1))
    step = pitch * (-1 if p.get('dir', 1) < 0 else 1)   # dir -1: pin numbers run right-to-left (the UNO's top headers: D0 at the right edge)
    out = []
    for i in range(n):
        if rows == 1:
            out.append({'number': i + 1, 'x': p['x'] + i * step, 'y': p['y']})
        else:
            col, row = i % rows, i // rows   # odd pins in one column, even in the other (the ICSP numbering)
            out.append({'number': i + 1, 'x': p['x'] + col * pitch, 'y': p['y'] + row * pitch})
    return out


GENERATORS = {'two-row': two_row, 'quad': quad}


def layout(row):
    """The computed pins of one shape row (a dict or a MathShapeDefinition-like object): {'ring', 'pins', 'pad'}. die / part-box rows need their own call (die(p, n))."""
    p = params(row)
    gen = p.get('generator')
    if gen in GENERATORS:
        return GENERATORS[gen](p)
    if gen == 'part-box':
        return part_box(p)
    raise KeyError('shape %s has no pin generator for %r (die shapes take a pad count)' % (_name(row), gen))


def params(row):
    raw = row.get('parameters_json') if isinstance(row, dict) else getattr(row, 'parameters_json', '{}')
    return json.loads(raw or '{}')


def _name(row):
    return row.get('name') if isinstance(row, dict) else getattr(row, 'name', '')


def on_perimeter(pin, ring, tol=1e-6):
    """True when a computed pin lies on the perimeter of its ring rectangle (centred on the origin)."""
    return abs(abs(pin['x']) - ring['w'] / 2) < tol or abs(abs(pin['y']) - ring['h'] / 2) < tol


# ---------------------------------------------------------------- the rows
def _rect(w, h):
    return [[-w / 2, -h / 2], [w / 2, -h / 2], [w / 2, h / 2], [-w / 2, h / 2]]


def _row(name, title, gen_params, vertices, notes):
    p = dict(gen_params, units=MM, plane='xy', z=0.0, thickness=0.0, vertices=vertices)
    return {'name': name, 'display_name': title, 'family': 'primitive', 'primitive_kind': 'polygon', 'quadric_matrix_json': '', 'csg_json': '', 'parameters_json': json.dumps(p, sort_keys=True),
            'bounds_json': '', 'notes': notes, 'provenance_id': 'pv-0'}


def shape_name(kind, key):
    return '%s%s-%s' % (PREFIX, kind, key)


def package_row(pkg, contacts):
    """The MathShapeDefinition row of one PackageDefinition (SPDIP / TQFP / QFN). Pin count from the PackageDefinition + its PackageContact rows (never typed)."""
    n_legs = sum(1 for c in contacts if c['package'] == pkg['name'] and c.get('kind') != 'thermal-pad')
    has_pad = any(c['package'] == pkg['name'] and c.get('kind') == 'thermal-pad' for c in contacts)
    t = pkg['package_type'].upper()
    name = shape_name('pkg', pkg['name'])
    if t in ('SPDIP', 'DIP'):
        body = (0.285 * 25.4, 1.365 * 25.4)
        g = {'generator': 'two-row', 'package_type': t, 'pins': n_legs, 'pitch': 0.100 * 25.4, 'row_spacing': 0.300 * 25.4, 'body': list(body),
             'cited': {'pitch': _c(2.54, D328, '28P3 package drawing, p.644: pitch .100 in BSC'), 'body_w': _c(round(body[0], 3), D328, '28P3, p.644: molded package width E1 .285 in nominal'),
                       'body_h': _c(round(body[1], 3), D328, '28P3, p.644: overall length D 1.365 in nominal'),
                       'row_spacing': _c(7.62, D328, '28P3, p.644 title "300 mil body" = 0.300 in; the PackageDefinition footprint %s' % (pkg.get('footprint') or 'DIP-28_W7.62mm'))},
             'knobs': ['the pin-1 end (top of the left row) is a drawing convention']}
        return _row(name, 'ATmega328P 28-pin SPDIP (28P3) outline', g, _rect(*body), 'pv-0: two-row generator; every dimension cited from the 28P3 drawing (DS40002061B p.644); pins computed')
    if t in ('TQFP', 'QFP'):
        ring = 9.00 - 0.60
        g = {'generator': 'quad', 'package_type': t, 'pins': n_legs, 'pitch': 0.80, 'ring_side': ring, 'body': [7.00, 7.00], 'overall': [9.00, 9.00], 'pad': None,
             'cited': {'pitch': _c(0.80, D328, '32A package drawing, p.636: lead pitch e 0.80 BSC'), 'body': _c([7.00, 7.00], D328, '32A, p.636: molded package D1 x E1 7.00 BSC'),
                       'overall': _c([9.00, 9.00], D328, '32A, p.636: overall D x E 9.00 BSC'), 'foot_length': _c(0.60, D328, '32A, p.636: foot length L 0.60 nominal'),
                       'ring_side': _c(round(ring, 3), D328, 'derived: overall 9.00 minus one foot length 0.60 (the pin centres sit half a foot inside the tip, both ends)')},
             'knobs': ['the pin-1 corner (top of the left side) is a drawing convention']}
        return _row(name, 'ATmega328P 32-pin TQFP (32A) outline', g, _rect(7.00, 7.00), 'pv-0: quad generator; dimensions cited from the 32A drawing (DS40002061B p.636); not on the UNO (the variant the bench board may carry)')
    if t in ('QFN', 'VQFN'):
        ring = 5.00 - 0.40
        g = {'generator': 'quad', 'package_type': 'QFN', 'pins': n_legs, 'pitch': 0.50, 'ring_side': ring, 'body': [5.00, 5.00], 'pad': [3.10, 3.10] if has_pad else None,
             'cited': {'pitch': _c(0.50, D16U2, 'ordering information package type 32M1, p.295: 32-pad, 5 x 5 x 1 mm body, pad pitch 0.50 mm; same value in %s 32M1-A p.642' % D328),
                       'body': _c([5.00, 5.00], D16U2, 'p.295 (5 x 5 x 1 mm body); %s 32M1-A p.641-642: D x E 5.00 BSC' % D328),
                       'exposed_pad': _c([3.10, 3.10], D328, '32M1-A drawing p.642: exposed pad D2 x E2 3.10 nominal (the 16U2 packaging section itself is a figure with no text; same package code)'),
                       'terminal_length': _c(0.40, D328, '32M1-A p.642: terminal length L 0.40 nominal'),
                       'ring_side': _c(round(ring, 3), D328, 'derived: body 5.00 minus one terminal length 0.40 (terminal centres)')},
             'knobs': ['the pin-1 corner (top of the left side) is a drawing convention']}
        return _row(name, 'ATmega16U2 32-pad QFN (32M1-A) outline', g, _rect(5.00, 5.00), 'pv-0: quad generator + the exposed pad; pitch + body from doc7799 p.295, pad + terminal from the 32M1-A drawing (partial: sibling document)')
    raise KeyError('no shape generator for package type %s' % t)


def die_row(soc):
    size = (5.0, 5.0) if soc == 'atmega16u2' else (3.0, 3.0)
    g = {'generator': 'die', 'size': list(size), 'pads': 'one per SocPin + one per supply / signal pad the package crossings name', 'cited': {},
         'knobs': ['die size', 'pad positions: no die map is cited (E0 die pads are `undetermined` in the exposure rows); pads are spread over the perimeter in the order of the leg each bonds to']}
    return _row(shape_name('die', soc), '%s die (drawing knob)' % soc, g, _rect(*size), 'pv-0: DRAWING KNOB die square inside the package; no die dimensions are cited')


# ---- the UNO board
BOARD_BBOX = (66.04, 50.80)
HOLE_D = 3.20
#: header rows on the UNO: connector -> (x, y of pin 1, rows, dir). Positions are DRAWING KNOBS (the cited drawing dimensions the outline, holes and the 100 mil
#: pitch only). With the USB connector on the left, the top headers number right-to-left: D0 sits at the right edge, D7 then a wider gap then D8 … D13, GND,
#: AREF, SDA, SCL towards the left (the UNO's printed header order); the bottom headers read left-to-right (NC, IOREF, RESET, 3V3, 5V, GND, GND, VIN; A0–A5).
HEADERS = {'DIGITAL_L': (63.5, 2.54, 1, -1), 'DIGITAL_H': (41.6, 2.54, 1, -1), 'POWER': (24.0, 48.26, 1, 1), 'ANALOG': (46.0, 48.26, 1, 1), 'ICSP': (61.5, 22.0, 2, 1)}
#: placed footprints: ref -> (x, y, rotation degrees) in the board frame, centre of the footprint. KNOBS.
PLACE = {'U1': (38.0, 25.4, 90), 'U2': (13.0, 26.0, 0), 'X2': (5.0, 14.0, 0)}


def part_names(tables, board):
    """{part ref: [pin names]} for every board part a crossing ends on: SchematicPart outer refs (the schematic's own pin) + via parts of internal-only lines (derived from the EnclosureContact rows)."""
    parts = {}
    labels = leg_labels(tables)
    for c in V.board_rows(tables, board):
        o = c['outer_ref']
        if o.startswith('SchematicPart:'):
            ref, _, pin = o[len('SchematicPart:'):].rpartition(':')
            parts.setdefault(ref, [])
            if pin not in parts[ref]:
                parts[ref].append(pin)
        elif c['via'] == 'internal-only' and c['via_part']:
            parts.setdefault(c['via_part'], [])
            lab = part_pin_name(c, labels)
            if lab not in parts[c['via_part']]:
                parts[c['via_part']].append(lab)
    return {k: sorted(v, key=_natural) for k, v in sorted(parts.items())}


def leg_labels(tables):
    return {'PackageContact:%s' % c['name']: c['label'] for c in tables.get('PackageContact', [])}


def part_pin_name(c, labels):
    """The name of the pin on a via part of an internal-only line: the chip-side leg label the line comes from (the schematic pin NUMBER of a passive is not in the rows -> undetermined)."""
    return '%s line' % labels.get(c['inner_ref'], c['inner_ref'].rpartition(':')[2])


def _natural(s):
    import re
    return [int(t) if t.isdigit() else t for t in re.split(r'(\d+)', str(s))]


def bench_components(tables, board):
    """[(circuit, component dict, net label)] — every bench component pin that sits on a net a BoardPinNet of this board names (derived from BoardPinNet + the circuit rows; never typed)."""
    nets = {n['name']: n for n in tables.get('CircuitNetDefinition', [])}
    comps = tables.get('CircuitComponentDefinition', [])
    out, seen = [], set()
    for bpn in tables.get('BoardPinNet', []):
        nr = nets.get(bpn['circuit_net'])
        if bpn['board'] != board or nr is None:
            continue
        for c in comps:
            if c['circuit_name'] == bpn['circuit'] and nr['net'] in json.loads(c.get('pins_json') or '[]') and (bpn['circuit'], c['name'], nr['net']) not in seen:
                seen.add((bpn['circuit'], c['name'], nr['net']))
                out.append((bpn['circuit'], c, nr['net']))
    return out


def part_row(board, ref, pin_names):
    n = len(pin_names)
    box = (max(3.0, 1.5 * math.ceil(n / 2)), 3.0) if n > 1 else (1.5, 1.5)
    g = {'generator': 'part-box', 'part': ref, 'pin_names': pin_names, 'box': list(box), 'pitch': 1.27, 'cited': {},
         'knobs': ['the box size and the pin pitch (%d pin(s) named by the rows that end on this part)' % n, 'the part\'s real footprint is not modelled; its pin NUMBERS beyond the schematic pin named in the row are `undetermined`']}
    return _row(shape_name('part', ref.replace(' ', '_')), '%s (board part, drawing knob)' % ref, g, _rect(*box), 'pv-0: part-box generator; pins = the lines the exposure rows end on this part')


def board_row(board, tables):
    cps = [c for c in tables.get('ConnectorPin', []) if c['board'] == board]
    conns = [c for c in tables.get('Connector', []) if c['board'] == board]
    heads = []
    for c in conns:
        x, y, rows, dirn = HEADERS.get(c['connector'], (5.0, 5.0, 1, 1))
        heads.append({'connector': c['connector'], 'ref': c.get('ref', ''), 'pins': c['pin_count'], 'pitch': 2.54, 'rows': rows, 'dir': dirn, 'x': x, 'y': y, 'name': c['name']})
    w, h = BOARD_BBOX
    outline = [[0, 0], [w, 0], [w, 12.7], [w + 2.54, 15.24], [w + 2.54, 48.26], [w, h], [0, h]]
    holes = [{'x': 15.24, 'y': 2.54, 'd': HOLE_D, 'cited': True}, {'x': 66.04, 'y': 17.78, 'd': HOLE_D, 'cited': True}, {'x': 66.04, 'y': 45.72, 'd': HOLE_D, 'cited': True},
             {'x': 14.0, 'y': 48.0, 'd': HOLE_D, 'cited': False}]
    placements = [{'ref': r, 'x': x, 'y': y, 'rot': rot} for r, (x, y, rot) in sorted(PLACE.items())]
    g = {'generator': 'board', 'board': board, 'headers': heads, 'holes': holes, 'placements': placements, 'bbox': [w, h], 'origin': 'top-left of the outline, y down',
         'cited': {'bbox': _c([w, h], UNO_DS, '5.4 Board Outline & Mounting Holes, p.12: 2600 mil x 2000 mil = 66.04 x 50.80 mm'),
                   'hole_diameter': _c(HOLE_D, UNO_DS, 'p.12: 4 x 3.20 mm (126 mil)'),
                   'holes': _c([[15.24, 2.54], [66.04, 17.78], [66.04, 45.72]], UNO_DS, 'p.12: 15.24 mm and 2.54 mm for the upper-left hole; 17.78 mm and 45.72 mm down the right edge'),
                   'header_pitch': _c(2.54, UNO_DS, 'p.12 grid (100 mil = 2.54 mm); the Connector rows\' footprints are P2.54mm sockets (rows: Connector.footprint)')},
         'knobs': ['the stepped right edge (the drawing shows a step, its size is not dimensioned): 2.54 mm step, 15.24 mm and 48.26 mm', 'the lower-left hole (14.0, 48.0): not dimensioned',
                   'every header row position (the connectors sit on the top and bottom edges; their x offsets are not dimensioned in the cached text)',
                   'every footprint placement and rotation (U1, U2, USB connector, the part boxes)']}
    return _row(shape_name('board', board), '%s board outline (cited bbox, knob details)' % board, g, [list(map(float, v)) for v in outline],
                'pv-0: board generator; bbox + holes + pitch cited from the UNO product datasheet p.12; every placement a drawing knob')


def part_cells(refs, start=(4.0, 34.0), cell=7.0, per_row=4):
    """Auto-layout KNOB: board parts in a grid in the free lower-left area (clear of U1 at x 34.4-41.6 and the bottom headers); deterministic by ref order."""
    out = {}
    for i, ref in enumerate(sorted(refs)):
        out[ref] = (start[0] + (i % per_row) * cell, start[1] + (i // per_row) * 4.5)
    return out


def shape_rows(tables, board='arduino-uno-r3'):
    """Every MathShapeDefinition row of the pin view for the UNO: 3 package outlines (SPDIP, TQFP, QFN), 2 dies, the board outline and one box per board part."""
    rows = []
    contacts = tables.get('PackageContact', [])
    for pkg in tables.get('PackageDefinition', []):
        if pkg['name'] in ('atmega328p-28-spdip', 'atmega328p-32-tqfp', 'atmega16u2-32-qfn'):
            rows.append(package_row(pkg, contacts))
    comps = [c for c in tables.get('BoardComponent', []) if c['board'] == board and c.get('package')]
    for soc in sorted({c['soc'] for c in comps}):
        rows.append(die_row(soc))
    parts = part_names(tables, board)
    for ref, names in parts.items():
        rows.append(part_row(board, ref, names))
    by_comp = {}
    for circuit, c, label in bench_components(tables, board):
        by_comp.setdefault((circuit, c['name']), []).append(label)
    for (circuit, name), labels in sorted(by_comp.items()):
        rows.append(part_row(board, 'bench-%s' % name, sorted(labels)))
    b = board_row(board, tables)
    p = json.loads(b['parameters_json'])
    cells = part_cells([r for r in parts if r not in PLACE])   # bench parts sit outside the board: the model places them in a column to its right
    p['placements'] += [{'ref': r, 'x': x, 'y': y, 'rot': 0} for r, (x, y) in sorted(cells.items())]
    b['parameters_json'] = json.dumps(p, sort_keys=True)
    rows.append(b)
    return rows


def seed_rows():
    """The code-owned seed rows (derived from the board tables + the bench circuit rows on every seed)."""
    from board.custom import hardware_system as HS
    return shape_rows(HS.default_tables())


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    rows = seed_rows()
    out = []
    for r in rows:
        p = json.loads(r['parameters_json'])
        n = len(layout(r)['pins']) if p.get('generator') in GENERATORS or p.get('generator') == 'part-box' else None
        out.append({'name': r['name'], 'generator': p.get('generator'), 'pins': n, 'knobs': len(p.get('knobs', [])), 'cited': sorted(p.get('cited', {}))})
    if '--json' in argv:
        print(json.dumps({'ok': True, 'rows': out, 'count': len(out)}, indent=2))
    else:
        for o in out:
            print('%-52s %-9s pins=%-4s cited=%s' % (o['name'], o['generator'], o['pins'], ','.join(o['cited']) or '-'))
    return 0


if __name__ == '__main__':
    sys.exit(main())
