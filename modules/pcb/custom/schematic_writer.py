"""
@module pcb.custom.schematic_writer

WRITE a `.kicad_sch` DIRECTLY from rows (D-pcb-1, his ruling: "write directly so we can track them through polari … while
relaying them through kicad engines"; no SKiDL). Input: a design (pcb.custom.uno_shield.design — components with KiCad lib ids,
values, footprints and {pin: net}) + the library SYMBOL texts (pcb.custom.pcb_engines.library — one official entry each, with its
library file's sha256). Output: one KiCad 9 schematic sheet (format 20250114, the version KiCad 9.0.2 writes).

How it connects (no wires to route): every connected pin gets, at its exact connection point, either a POWER symbol (power:+5V /
power:GND — one instance per pin, all pins of a net meeting through the global power net) or a local net LABEL with the net name
(a label at a pin's end joins it). One PWR_FLAG sits on each power net (fed through a connector, which ERC cannot see). Pins
with no net are left alone — ERC reports them; they are listed, never hidden.

Geometry: symbols on a 2.54 mm grid (KiCad's ERC checks off-grid pins at 1.27 mm), headers in a column on the left, parts to the
right; a pin's connection point = symbol origin + (pin x, -pin y) (library y points up, the sheet's down; rotation 0, no mirror).
Deterministic: uuids are uuid5 of 'polari:pcb/<board>/<what>', no dates — the same rows give the same bytes (sha on the row).
"""
import uuid

from pcb.custom import sexpr as S
from pcb.custom.sexpr import Q

FORMAT_VERSION = '20250114'
GRID = 2.54
POWER_LIB = {'+5V': 'power:+5V', 'GND': 'power:GND', '+3V3': 'power:+3V3'}


class WriterRefused(ValueError):
    pass


def _u(board, *what):
    return str(uuid.uuid5(uuid.NAMESPACE_URL, 'polari:pcb/%s/%s' % (board, '/'.join(str(w) for w in what))))


def _font(size=1.27, hide=False, justify=None):
    e = ['effects', ['font', ['size', size, size]]]
    if justify:
        e.append(['justify'] + justify)
    if hide:
        e.append(['hide', 'yes'])
    return e


def _fmt(v):
    s = ('%.4f' % v).rstrip('0').rstrip('.')
    return '0' if s in ('-0', '') else s


def lib_pins(tree):
    """{number: (x, y, name)} of a parsed library symbol (every unit)."""
    out = {}
    for p in S.find_all(tree, 'pin'):
        if len(p) > 2 and S.find(p, 'number') and S.find(p, 'at'):
            x, y, _ = S.xy(p)
            out[S.value(p, 'number')] = (x, y, S.value(p, 'name'))
    return out


def embed(lib_id, text):
    """A library entry as lib_symbols carries it: the top symbol renamed to the full lib id (sub-symbols keep their names)."""
    t = S.parse(text)
    if not (isinstance(t, list) and t and t[0] == 'symbol'):
        raise WriterRefused('%s: the library text is not a (symbol …)' % lib_id)
    if S.find(t, 'extends'):
        raise WriterRefused('%s is a derived symbol (extends) — not flattened by this writer' % lib_id)
    t[1] = Q(lib_id)
    return t


def _symbol(board, sheet_uuid, project, lib_id, ref, value, footprint, at, pins, extra_props=(), in_bom='yes', on_board='yes'):
    x, y = at
    sym = ['symbol', ['lib_id', Q(lib_id)], ['at', _fmt(x), _fmt(y), 0], ['unit', 1], ['exclude_from_sim', 'no'], ['in_bom', in_bom],
           ['on_board', on_board], ['dnp', 'no'], ['uuid', Q(_u(board, 'sym', ref))]]
    hidden = ref.startswith('#')
    sym.append(['property', Q('Reference'), Q(ref), ['at', _fmt(x + 2.54), _fmt(y - 2.54), 0], _font(hide=hidden)])
    sym.append(['property', Q('Value'), Q(value), ['at', _fmt(x + 2.54), _fmt(y + 2.54), 0], _font()])
    sym.append(['property', Q('Footprint'), Q(footprint), ['at', _fmt(x), _fmt(y), 0], _font(hide=True)])
    sym.append(['property', Q('Datasheet'), Q(''), ['at', _fmt(x), _fmt(y), 0], _font(hide=True)])
    for k, v in extra_props:
        sym.append(['property', Q(k), Q(v), ['at', _fmt(x), _fmt(y), 0], _font(hide=True)])
    for n in sorted(pins, key=lambda s: (len(s), s)):
        sym.append(['pin', Q(n), ['uuid', Q(_u(board, 'pin', ref, n))]])
    sym.append(['instances', ['project', Q(project), ['path', Q('/' + sheet_uuid), ['reference', Q(ref)], ['unit', 1]]]])
    return sym


def write(d, libs, title=None, comment=''):
    """d = a design; libs = {lib_id: library text} (every component's + the power symbols used). → (text, report) where report
    lists every connection made and every pin left unconnected."""
    board = d['board']
    sheet_uuid = _u(board, 'sheet', '/')
    need = {c['lib_id'] for c in d['components']} | {POWER_LIB[n] for n in d['nets'] if n in POWER_LIB} | {'power:PWR_FLAG'}
    missing = sorted(need - set(libs))
    if missing:
        raise WriterRefused('library symbols not supplied: %s' % ', '.join(missing))
    trees = {k: embed(k, libs[k]) for k in sorted(need)}
    items, conns, pwr_n, flagged = [], [], [0], set()
    report = {'connections': [], 'unconnected_pins': [], 'power_symbols': 0, 'labels': 0}

    def power(net, x, y):
        pwr_n[0] += 1
        ref = '#PWR%02d' % pwr_n[0]
        items.append(_symbol(board, sheet_uuid, board, POWER_LIB[net], ref, net, '', (x, y), ['1']))
        report['power_symbols'] += 1
        if net not in flagged:   # one PWR_FLAG per power net, on the first of its pins
            flagged.add(net)
            fref = '#FLG%02d' % len(flagged)
            items.append(_symbol(board, sheet_uuid, board, 'power:PWR_FLAG', fref, 'PWR_FLAG', '', (x, y), ['1']))

    headers = [c for c in d['components'] if c['role'] == 'header']
    parts = [c for c in d['components'] if c['role'] != 'header']
    placed = []
    y = 38.1
    for c in headers:   # a column on the left, each header below the previous
        pins = lib_pins(trees[c['lib_id']])
        top = max(p[1] for p in pins.values())
        bot = min(p[1] for p in pins.values())
        oy = y + top
        placed.append((c, (50.8, round(oy / GRID) * GRID), pins))
        y = oy - bot + 4 * GRID
    py = 38.1
    for c in parts:
        pins = lib_pins(trees[c['lib_id']])
        top = max(p[1] for p in pins.values())
        bot = min(p[1] for p in pins.values())
        oy = py + top
        placed.append((c, (127.0, round(oy / GRID) * GRID), pins))
        py = oy - bot + 8 * GRID
    for c, (ox, oy), pins in placed:
        by_name = {v[2]: k for k, v in pins.items()}
        wired = {}
        for pin, net in c['pins'].items():
            num = pin if pin in pins else by_name.get(pin)
            if num is None:
                raise WriterRefused('%s (%s) has no pin %r — pins %s' % (c['ref'], c['lib_id'], pin, sorted(pins)))
            wired[num] = net
        extra = [('polari_role', c['role'])] + ([('polari_uno_connector', c['uno_connector'])] if c.get('uno_connector') else [])
        items.append(_symbol(board, sheet_uuid, board, c['lib_id'], c['ref'], c['value'], c['footprint'], (ox, oy), list(pins), extra))
        for num, (px, py_, pname) in sorted(pins.items(), key=lambda kv: (len(kv[0]), kv[0])):
            cx, cy = ox + px, oy - py_
            net = wired.get(num)
            if net is None:
                report['unconnected_pins'].append({'ref': c['ref'], 'pin': num, 'name': pname, 'at': [_fmt(cx), _fmt(cy)],
                                                   'host_pin': (c.get('labels') or {}).get(num, '')})
                continue
            if net in POWER_LIB:
                power(net, cx, cy)
            else:
                items.append(['label', Q(net), ['at', _fmt(cx), _fmt(cy), 0], ['fields_autoplaced', 'yes'],
                              _font(justify=['left', 'bottom']), ['uuid', Q(_u(board, 'label', c['ref'], num))]])
                report['labels'] += 1
            report['connections'].append({'ref': c['ref'], 'pin': num, 'name': pname, 'net': net})
    tb = ['title_block', ['title', Q(title or board)], ['rev', Q('pcb-0')], ['company', Q('Polari')],
          ['comment', 1, Q(comment or 'written by pcb.custom.schematic_writer from rows (D-pcb-1) — generated: edit the rows, not this file')]]
    tree = ['kicad_sch', ['version', FORMAT_VERSION], ['generator', Q('polari_pcb')], ['generator_version', Q('pcb-0')],
            ['uuid', Q(sheet_uuid)], ['paper', Q('A4')], tb, ['lib_symbols'] + [trees[k] for k in sorted(trees)]] + items + \
           [['sheet_instances', ['path', Q('/'), ['page', Q('1')]]], ['embedded_fonts', 'no']]
    text = S.write(tree) + '\n'
    why = S.check_kicad(S.parse(text), 'kicad_sch')
    if why:
        raise WriterRefused('the written schematic fails its own check: %s' % '; '.join(why))
    return text, report
