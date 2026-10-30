"""
@module electrodevice.custom.layout_compile

lay-1: COMPILE A LAYOUT TO ITS NETS with `electrodevice.breadboard_netlist_seed` — the layout's placements become ComponentPlacement-shaped rows, its wires (and the pairs of legs a
pushbutton joins inside itself) become BoardJumper-shaped rows, and `layout_nets` walks them with the same tie grammar and union-find the SPICE render uses. The answer is a PARTITION OF
TERMINALS: every part terminal (`LED1.anode`) and every header pin a wire touches (`hdr:D6`) lands in the group of the strip/rail/pin net it is on. Two terminals in one group are
electrically one net in the layout; the netlist gate compares these groups with the design's.
"""
import json
import types

from electrodevice.custom.layout_words import LayoutRefused

SPICE_KINDS = {'switch', 'resistor', 'led', 'diode', 'capacitor'}


def _placement_rows(laid, board):
    rows = {}
    for p in laid['placements']:
        kind = p['kind'] if p['kind'] in SPICE_KINDS else 'part'
        params = dict(p['params']) if kind != 'switch' else {'state': 'open'}
        rows[p['name']] = types.SimpleNamespace(name=p['name'], board_name=board, kind=kind, params_json=json.dumps(params),
                                                tiepoints_json=json.dumps(p['ties']), device_name='', description='')
    return rows


def _jumper_rows(laid, board, header_board):
    rows, n = {}, 0
    for w in laid['wires']:
        rows[w['name']] = types.SimpleNamespace(name=w['name'], board_a=w['from']['board'], tie_a=w['from']['tie'], board_b=w['to']['board'], tie_b=w['to']['tie'],
                                                description=w.get('note', ''), kind=w['kind'], colour_override='')
    for p in laid['placements']:
        for pair in p['internal']:
            n += 1
            rows['%s-inside-%d' % (p['name'], n)] = types.SimpleNamespace(name='%s-inside-%d' % (p['name'], n), board_a=board, tie_a=pair[0], board_b=board, tie_b=pair[1],
                                                                          description='joined inside %s' % p['name'], kind='internal', colour_override='')
    return rows


def compile_nets(manager, design, laid, board, header_board):
    """-> {'groups': [[terminal ids]], 'net_of': {terminal id: compiled net name}, 'suggestions': [..]}. Raises LayoutRefused naming the row at fault (a hole off the board, a pin that is not a header pin)."""
    from electrodevice import breadboard_netlist_seed as bn
    from electrodevice.custom import board_models as BM
    tabs = getattr(manager, 'objectTables', None) or {}
    mgr = types.SimpleNamespace(objectTables={'BreadboardDefinition': dict(tabs.get('BreadboardDefinition') or {}), 'BenchBoard': dict(tabs.get('BenchBoard') or {}),
                                              **{c: dict(tabs.get(c) or {}) for c in BM.TABLES}, 'ComponentPlacement': _placement_rows(laid, board),
                                              'BoardJumper': _jumper_rows(laid, board, header_board)}, db=None)
    header_pins = sorted({w['from']['tie'] for w in laid['wires'] if w['from']['board'] == header_board}
                         | {w['to']['tie'] for w in laid['wires'] if w['to']['board'] == header_board}
                         | {t[len('hdr:'):] for net in design['nets'].values() for t in net if t.startswith('hdr:')})
    try:
        out = bn.layout_nets(mgr, [board, header_board], ties=[(header_board, h) for h in header_pins])
    except ValueError as exc:
        raise LayoutRefused('the layout cannot be compiled: %s' % exc)
    net_of = {}
    for comp in design['components']:
        placed = out['netByPlacement'].get(comp['ref'])
        if placed is None:
            continue                       # a part the layout does not place: its terminals are reported by the gate as missing
        for t, net in zip(comp['terminals'], placed):
            net_of[t['id']] = net
    for h in header_pins:
        net_of['hdr:%s' % h] = out['netByTie'][(header_board, h)]
    groups = {}
    for tid, net in net_of.items():
        groups.setdefault(net, []).append(tid)
    return {'groups': sorted(sorted(g) for g in groups.values()), 'net_of': net_of, 'suggestions': out['suggestions']}
