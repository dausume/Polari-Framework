"""
@module pcb.custom.kicad_footholds

bob-0, the LAYERS adapter of the bench contract (board.custom.footholds; AI-Notes/plans/BENCH_BOARDS_PLAN.md section 3): a PCB defined by its copper
(a KiCad import here) is a Board on the Bench like a dev board or a breadboard; what the Bench sees of it is its FOOTHOLDS - the pads of its
connectors and test points, where a wire or a mating header can land. The parse lives with the reader (pure, no KiCad):

  pad_positions(fp)            [(number, x_mm, y_mm, net)] of one (footprint ...) in board coordinates - KiCad's own rule: the pad's (at) is in the
                               footprint frame, rotated by the footprint's angle (y down, angle counter-clockwise on screen); checked against
                               pcbnew's GetPosition() for every pad of two boards (pcb_kicad_cover_selftest)
  is_foothold(ref, lib_id)     a connector (ref J / P / CN / X, or a Connector* library) or a test point (TP, TestPoint*)
  rows(tree, board)            BoardFoothold rows, definition_kind `layers`: node = the pad's net (pads on one net are joined in the copper)

Drive and signal are UNDETERMINED here and say why: which part drives a net and its ERC pin types come from the schematic connectivity (kxc-2) and
the circuit simulation (kxc-3); the rail voltage is unknown (a KiCad net carries none). The net CLASS by name (GND / +5V) is the only signal hint.
"""
import json
import math
import re

from pcb.custom import sexpr as S

CONNECTOR_REF = re.compile(r'^(J|P|CN|X|TP)\d+$')


def _f(x):
    return S.num(x, 0.0)


def pad_positions(fp):
    fx, fy, frot = S.xy(fp)
    a = math.radians(frot)
    out = []
    for p in S.find(fp, 'pad'):
        px, py, _ = S.xy(p)
        x = fx + px * math.cos(a) + py * math.sin(a)
        y = fy - px * math.sin(a) + py * math.cos(a)
        n = S.find(p, 'net')
        out.append((str(p[1]) if len(p) > 1 else '', round(x, 4), round(y, 4), str(n[0][2]) if n and len(n[0]) > 2 else ''))
    return out


def is_foothold(ref, lib_id):
    nick = (lib_id or '').partition(':')[0]
    return bool(CONNECTOR_REF.match(ref or '')) or nick.startswith(('Connector', 'TestPoint'))


def _family(net):
    """ground | power | '' - from the net NAME only (GND* / VSS ground; a leading + or -V, VCC / VDD / VBAT / VIN power)."""
    if re.match(r'^(GND|VSS)', net, re.I):
        return 'ground'
    return 'power' if re.match(r'^(\+|-V|VCC|VDD|VBAT|VIN)', net, re.I) else ''


def rows(tree, board):
    out = []
    for fp in S.find(tree, 'footprint'):
        ref, lib_id = S.prop(fp, 'Reference'), str(fp[1]) if len(fp) > 1 else ''
        if not is_foothold(ref, lib_id):
            continue
        side = 'bottom' if S.value(fp, 'layer') == 'B.Cu' else 'top'
        kind = 'test-pad' if ref.startswith('TP') or lib_id.startswith('TestPoint') else 'connector-pin'
        for num, x, y, net in pad_positions(fp):
            if not num:   # an unnumbered pad (a mounting tab) is copper, not a landing point
                continue
            fid = '%s:%s' % (ref, num)
            fam = _family(net) if net else ''
            out.append({'name': 'layers:%s:%s' % (board, fid), 'definition_kind': 'layers', 'definition': board, 'foothold': fid, 'kind': kind, 'label': '',
                        'x_mm': x, 'y_mm': y, 'position_basis': 'derived: the board file (footprint %s at + pad at, rotated by the footprint angle)' % lib_id,
                        'side': side, 'node': 'net:%s' % net if net else 'pin:%s' % fid, 'net': net, 'rail_volts': 0.0 if fam == 'ground' else -1.0,
                        'logic_volts': -1.0, 'source_ma': -1.0, 'sink_ma': -1.0,
                        'drive_basis': 'ground by net name (%s)' % net if fam == 'ground' else '',
                        'families_json': json.dumps([fam] if fam else []), 'chip_pin': '', 'direction': 'supply' if fam else 'undetermined',
                        'signal_basis': ('net class from the name %s only' % net) if fam else ('net %s' % net if net else 'no net: the pad is unconnected in the copper'),
                        'undetermined': 'drive and signal of net %s: the driving part and its ERC pin types come from the schematic connectivity (kxc-2) and '
                                        'the simulation (kxc-3); a KiCad net carries no voltage' % (net or '(none)'), 'notes': ''})
    return out


DRIVING = ('output', 'power_out', 'bidirectional', 'tri_state', 'open_collector', 'open_emitter')


def enrich(footholds, endpoints):
    """kxc-2 on top of bob-0: each PCB foothold learns what is behind its pad from the schematic's own nets (NetEndpoint rows, matched by the pad's
    net NAME - KiCad gives the board and the schematic the same names): the other pins on the net with their ERC types, and which of them DRIVE it.
    Voltages stay unknown (kxc-3, the simulation)."""
    by = {}
    for e in endpoints:
        by.setdefault(e['net'], []).append(e)
    for f in footholds:
        ref = f['foothold'].split(':')[0]
        others = [e for e in by.get(f['net'], []) if e['ref'] != ref]
        if not f['net'] or not by.get(f['net']):
            continue
        drivers = ['%s:%s (%s)' % (e['ref'], e['pin'], e['pintype']) for e in others if e['pintype'] in DRIVING]
        f['signal_basis'] = 'schematic net %s joins %s' % (f['net'], ', '.join('%s:%s (%s)' % (e['ref'], e['pin'], e['pintype']) for e in others[:8]) or 'no other pin') \
            + (' and %d more' % (len(others) - 8) if len(others) > 8 else '')
        if drivers:
            f['notes'] = 'driven by %s' % ', '.join(drivers[:6])
            if f['direction'] == 'undetermined':
                f['direction'] = 'out'   # something on the board drives this pad outward
        elif any(e['pintype'] in ('input', 'power_in') for e in others) and f['direction'] == 'undetermined':
            f['direction'] = 'in'   # only inputs behind it: the pad must be driven from outside
        f['undetermined'] = 'rail and logic voltages of net %s: from the simulation (kxc-3); a KiCad net carries no voltage' % f['net']
    return footholds
