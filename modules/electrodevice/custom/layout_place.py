"""
@module electrodevice.custom.layout_place

lay-1: THE PLACER — a DESIGN (components with named terminals, the nets, the header attachments; electrodevice.custom.layout_sources) in, DETERMINISTIC placements and wires out.
No randomness, no search: the same design on the same board gives the same holes (the build steps hash to the same sha). Rules (BREADBOARD_BUILD_PLAN section 3, bb-1):
  - rails first: GND (and +5 V, when a part needs it) from the header to the top rail;
  - parts in column order from row START_ROW down the board, one net = one strip (a-e left of the trench, f-j right); a part's leads land on the strips of the nets they belong to;
  - a 4-leg pushbutton STRADDLES the trench: legs two rows apart, the signal side left, the other side right; its two legs on one side are joined inside it;
  - a two-lead part spans rows (a resistor RESISTOR_SPAN_ROWS, an LED LED_SPAN_ROWS): LED anode row -> series resistor -> cathode row falls out of the nets;
  - a three-lead part (TMP36, transistor) takes three adjacent rows of one column, in the order the part is read when its flat face is toward the reader (TMP36: +Vs, Vout, GND; transistor E-B-C);
  - header wires run from the header pin to the first free hole of the net's strip; a net on several strips is bridged by a wire; a rail net is tapped from its strip to the rail.
Hole use: parts take columns from the trench outward (e, d, c.. on the left, f, g, h.. on the right), wires take them from the board's edge inward (a, b, c.. left; j, i, h.. right), so a part and a wire
never fight for a hole. Every number is a knob below, labelled, never a measurement.
"""
from electrodevice.custom import board_family as BF
from electrodevice.custom.layout_words import LayoutRefused

START_ROW = 3                    # first strip used: rows 1-2 stay free (a layout knob)
RESISTOR_SPAN_ROWS = 4           # a 1/4 W axial resistor bent to span 0.4 in = 4 hole pitches (common practice; a layout knob, not measured; the kit book gives no dimension)
LED_SPAN_ROWS = 1                # a 5 mm LED's leads are 2.54 mm = 1 hole pitch apart (common; the kit book gives no dimension)
BUTTON_LEG_ROWS = 2              # a 6 mm tactile switch's legs are 0.2 in = 2 hole pitches apart along the trench, and it straddles the 0.3 in trench (common; not measured)
RAIL_POS, RAIL_GND, RAIL_SUPPLY = 'top', '-', '+'
SPAN = {'resistor': RESISTOR_SPAN_ROWS, 'led': LED_SPAN_ROWS, 'diode': LED_SPAN_ROWS, 'capacitor': LED_SPAN_ROWS}
#: three-lead parts: kind -> terminal names in the order of the rows, flat face toward the reader (TMP36: kit book "left leg = power, centre = signal, right = ground"; the transistor: E-B-C per the brief,
#: the kit page prints no pinout)
THREE_LEAD = {'tmp36': ('vs', 'out', 'gnd'), 'transistor': ('emitter', 'base', 'collector')}
RANK = {'switch': 0, 'tmp36': 1, 'resistor': 2, 'transistor': 3, 'led': 4}


class _Board:
    """Hole bookkeeping of one breadboard."""

    def __init__(self, geo):
        self.geo, self.taken = geo, {}

    def free_part_col(self, rows, side):
        """The first column (from the trench outward) that is free in EVERY one of `rows`: a part's leads stay in one column, 2.54 mm apart."""
        rows = rows if isinstance(rows, (list, tuple)) else [rows]
        for c in (BF.LEFT_COLS[::-1] if side == 'L' else BF.RIGHT_COLS):
            if all((r, c) not in self.taken for r in rows):
                return c
        return None

    def free_wire_col(self, row, side):
        for c in (BF.LEFT_COLS if side == 'L' else BF.RIGHT_COLS[::-1]):
            if (row, c) not in self.taken:
                return c
        return None

    def take(self, row, col, who):
        if row > self.geo.rows:
            raise LayoutRefused("the layout needs row %d but board %s has %d rows (%s): a full breadboard has 63" % (row, self.geo.name, self.geo.rows, self.geo.size or self.geo.kind))
        if (row, col) in self.taken:
            raise LayoutRefused("hole row %d, %s is taken by %s" % (row, col, self.taken[(row, col)]))
        self.taken[(row, col)] = who
        return 'r%d%s' % (row, col)


def place(design, geo, header_board):
    """-> {'placements': [...], 'wires': [...], 'strips': {net: [hole,..]}, 'rows_used': n, 'board': name}."""
    if geo.kind != 'breadboard' or geo.reserved:
        raise LayoutRefused("board %s is a %s%s: layouts are placed on breadboards so far" % (geo.name, geo.kind, ' (reserved: no geometry yet)' if geo.reserved else ''))
    bd = _Board(geo)
    gnd, supply = design['ground_net'], set(design.get('supply_nets') or [])
    strips = {}      # signal net -> (row, side) the first strip of it
    extra = {}       # net -> [hole, ...] more strips of the net (bridged)
    wires, placements = [], []
    cls_of = _net_classes(design)

    def wire(name, kind, a, b, net, cls, note=''):
        wires.append({'name': name, 'kind': kind, 'from': {'board': a[0], 'tie': a[1]}, 'to': {'board': b[0], 'tie': b[1]}, 'net': net, 'class': cls, 'note': note})

    # 1. rails first
    rails = []
    for net, pol, label in ([(gnd, RAIL_GND, 'GND')] + [(n, RAIL_SUPPLY, '+5V') for n in sorted(supply)]):
        if net in design['nets']:
            rails.append((net, pol, label))
    for net, pol, label in rails:
        wire('w-%s-header' % ('gnd' if pol == RAIL_GND else '5v'), 'header', (header_board, label), (geo.name, 'rail:%s:%s:1' % (RAIL_POS, pol)), net, 'ground' if pol == RAIL_GND else 'power',
             'from the %s pin of the board to the %s rail' % (label, 'ground (-)' if pol == RAIL_GND else 'supply (+)'))
    rail_of = {net: pol for net, pol, _ in rails}

    def rail_tap(net, row, side, who):
        col = bd.free_wire_col(row, side)
        if col is None:
            raise LayoutRefused("row %d has no free hole left for the %s wire" % (row, net))
        hole = bd.take(row, col, 'wire %s' % who)
        pol = rail_of[net]
        wire('w-%s-r%d%s' % ('gnd' if pol == RAIL_GND else '5v', row, side.lower()), 'jumper', (geo.name, hole), (geo.name, 'rail:%s:%s:%d' % (RAIL_POS, pol, min(row, geo.rail_holes))), net,
             'ground' if pol == RAIL_GND else 'power', 'from this strip to the %s rail' % ('ground (-)' if pol == RAIL_GND else 'supply (+)'))

    def land(net, row, side, who):
        """A lead of net `net` sits on strip (row, side): a rail net is tapped to its rail, a signal net is registered or bridged to its first strip."""
        if net in rail_of:
            rail_tap(net, row, side, who)
        elif net not in strips:
            strips[net] = (row, side)
        elif strips[net] != (row, side):
            r0, s0 = strips[net]
            extra.setdefault(net, []).append('r%d%s' % (row, 'a' if side == 'L' else 'f'))
            col0, col1 = bd.free_wire_col(r0, s0), bd.free_wire_col(row, side)
            if col0 is None or col1 is None:
                raise LayoutRefused("no free hole to bridge net %s between rows %d and %d" % (net, r0, row))
            wire('w-%s-r%d' % (net.lower(), row), 'jumper', (geo.name, bd.take(r0, col0, 'bridge')), (geo.name, bd.take(row, col1, 'bridge')), net, cls_of.get(net, 'default'),
                 'joins the two strips of net %s' % net)

    def part_leg(ref, term, net, row, side, col=None):
        c = col or bd.free_part_col([row], side)
        if c is None:
            raise LayoutRefused("row %d (%s) has no free hole left for %s" % (row, 'left' if side == 'L' else 'right', term['id']))
        return {'terminal': term['id'], 'name': term['name'], 'net': net, 'hole': bd.take(row, c, term['id']), 'row': row, 'col': c, 'side': side}

    cursor = START_ROW
    for comp in sorted(design['components'], key=lambda c: (RANK.get(c['kind'], 9), c['ref'])):
        kind, terms = comp['kind'], comp['terminals']
        if kind == 'switch':
            sig = next((t for t in terms if t['net'] != gnd), terms[0])
            oth = next(t for t in terms if t is not sig)
            row_a, row_b = cursor, cursor + BUTTON_LEG_ROWS
            legs = [part_leg(comp['ref'], sig, sig['net'], row_a, 'L', 'e'), part_leg(comp['ref'], sig, sig['net'], row_b, 'L', 'e'),
                    part_leg(comp['ref'], oth, oth['net'], row_a, 'R', 'f'), part_leg(comp['ref'], oth, oth['net'], row_b, 'R', 'f')]
            land(sig['net'], row_a, 'L', comp['ref'])
            land(oth['net'], row_a, 'R', comp['ref'])
            # the second leg of each side is joined to the first inside the switch: that strip is the same net, no wire
            placements.append(_placement(comp, 'pushbutton', legs, rows=[row_a, row_b], straddles=True,
                                         internal=[[legs[0]['hole'], legs[1]['hole']], [legs[2]['hole'], legs[3]['hole']]]))
            cursor = row_b + 2
        elif kind in THREE_LEAD:
            order = THREE_LEAD[kind]
            by_name = {t['name']: t for t in terms}
            if set(by_name) != set(order):
                raise LayoutRefused("%s %s must have terminals %s, the design gives %s" % (kind, comp['ref'], '/'.join(order), '/'.join(sorted(by_name))))
            legs = []
            col = bd.free_part_col([cursor + i for i in range(len(order))], 'L')
            for i, n in enumerate(order):
                t = by_name[n]
                legs.append(part_leg(comp['ref'], t, t['net'], cursor + i, 'L', col))
                land(t['net'], cursor + i, 'L', comp['ref'])
            placements.append(_placement(comp, kind, legs, rows=[cursor, cursor + 2], order=order))
            cursor += 4
        elif kind in SPAN:
            span = SPAN[kind]
            t1, t2 = terms[0], terms[1]
            r1 = _known_row(strips, rail_of, t1['net'])
            r2 = _known_row(strips, rail_of, t2['net'])
            if r1 is None and r2 is None:
                r1 = cursor
                r2 = r1 + span
            elif r1 is None:
                r1 = r2 - span if r2 - span >= START_ROW else r2 + span
            elif r2 is None:
                r2 = r1 + span
            col = bd.free_part_col([r1, r2], 'L')
            legs = [part_leg(comp['ref'], t1, t1['net'], r1, 'L', col), part_leg(comp['ref'], t2, t2['net'], r2, 'L', col)]
            land(t1['net'], r1, 'L', comp['ref'])
            land(t2['net'], r2, 'L', comp['ref'])
            placements.append(_placement(comp, comp['kit_key'] or kind, legs, rows=sorted([r1, r2])))
            cursor = max(cursor, max(r1, r2) + 2)
        else:
            raise LayoutRefused("no placement rule for a %s (%s): rules exist for switch, resistor, led, diode, capacitor, tmp36 and transistor" % (kind, comp['ref']))
    # 2. header wires for the signal nets (after the parts, so each lands on the strip its net owns)
    for net, atts in sorted(design['attach'].items(), key=lambda kv: kv[0]):
        if net in rail_of:
            continue
        if net not in strips:
            raise LayoutRefused("net %s has a header pin (%s) but no part reaches it" % (net, ', '.join(a['pin'] for a in atts)))
        row, side = strips[net]
        for a in atts:
            col = bd.free_wire_col(row, side)
            if col is None:
                raise LayoutRefused("row %d has no free hole left for the %s wire" % (row, a['pin']))
            wire('w-%s' % a['pin'].lower(), 'header', (header_board, a['pin']), (geo.name, bd.take(row, col, 'wire ' + a['pin'])), net, 'pin:' + a['pin'],
                 'the %s pin %s to the strip of net %s' % (a['role'], a['pin'], net))
    # keep the order: rail header wires, signal header wires, then everything that taps or bridges
    rank = lambda w: (0 if w['name'].endswith('-header') else 1 if w['kind'] == 'header' else 2)   # noqa: E731
    wires.sort(key=lambda w: (rank(w), w['name']))
    rows_used = max([p['rows'][-1] for p in placements] or [0])
    return {'board': geo.name, 'header_board': header_board, 'placements': placements, 'wires': wires, 'rows_used': rows_used,
            'strips': {n: 'r%d%s' % (r, 'a' if s == 'L' else 'f') for n, (r, s) in strips.items() if not n.startswith('~')}}


def _known_row(strips, rail_of, net):
    return None if (net in rail_of or net not in strips) else strips[net][0]


def _net_classes(design):
    """net -> the colour class of its wires: 'ground', 'power', or 'pin:<label>' of its first header pin (resolved to a family by layout_colors)."""
    out = {}
    for net, atts in design['attach'].items():
        pins = [a['pin'] for a in atts if a['role'] != 'ground']
        if pins:
            out[net] = 'pin:' + pins[0]
    out[design['ground_net']] = 'ground'
    return out


def _placement(comp, part, legs, rows, internal=None, straddles=False, order=None):
    """`ties` are the holes of the part's terminals IN THE DESIGN'S TERMINAL ORDER (the first leg of each terminal; the other legs of a switch side are joined inside it)."""
    first = {}
    for leg in legs:
        first.setdefault(leg['terminal'], leg['hole'])
    return {'name': comp['ref'], 'part': part, 'kind': comp['kind'], 'row': comp['row'], 'kit_part': (comp.get('kit_part') or {}).get('name', ''), 'params': comp['params'],
            'legs': legs, 'ties': [first[t['id']] for t in comp['terminals']], 'internal': internal or [], 'rows': rows, 'straddles_trench': straddles,
            'terminal_order': order or [t['name'] for t in comp['terminals']], 'terminal_ids': [t['id'] for t in comp['terminals']], 'job': comp.get('job', '')}
