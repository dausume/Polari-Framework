"""
@module hwnocode.custom.schematic_kicad

cb-6 (AI-Notes/plans/COMPONENT_BINDING_PLAN.md §8c): ONE SCHEMATIC FOR A WHOLE HARDWARE SOLUTION, as a real KiCad sheet. The solved
schematic components of a HardwareSolution (custom/solved/<solution>.json) become a pcb DESIGN - the same shape pcb.custom.uno_shield
builds - and pcb.custom.schematic_writer writes the `.kicad_sch` from it (D-pcb-1: written directly, relayed through the KiCad engine
for the electrical-rule check and the drawing). Nothing is typed twice:
  - the board's headers are its own Connector rows (board.custom.board_object.rows_for), each header pin wired when its board net is one a
    component uses, named with the CIRCUIT's net (LED_CONTROL, BUTTON_INPUT); GND by the power symbol; every other pin left unconnected
    (KiCad's check lists them, never hidden behind no-connect flags - the uno_shield posture)
  - the parts are the components' physical parts (core, series, an external pull), each pin on the circuit net its CircuitComponentDefinition
    row names; a pull inside the chip (the firmware's PinClaim) is not a part on the sheet - it is listed in the report, in words
  - library ids and footprints per part kind: KIND_LIB (KiCad 9's official libraries, the kit parts' through-hole packages)

  design(record, tables=None)   -> the design {'board', 'host', 'components', 'nets', 'unconnected', 'inside_chip', 'signals'}
  libs_needed(design)           -> the library symbol ids the writer needs (the components' + the power symbols + PWR_FLAG)
  write(record, libs)           -> (kicad_sch text, report)   (libs = {lib_id: library text}, pcb.custom.pcb_engines.library supplies them)
"""
import json

from pcb.custom import schematic_writer as W

#: part kind -> (lib id, footprint, how the circuit row's pins (in pins_json order) map onto the symbol's pins)
KIND_LIB = {
    'led': ('Device:LED', 'LED_THT:LED_D5.0mm', ('A', 'K')),                 # pins_json: [anode net, cathode net]
    'resistor': ('Device:R', 'Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P7.62mm_Horizontal', ('1', '2')),
    'pushbutton': ('Switch:SW_Push', 'Button_Switch_THT:SW_PUSH_6mm', ('1', '2')),
}


class DesignRefused(ValueError):
    pass


def _header_lib(n):
    return 'Connector_Generic:Conn_01x%02d' % n, 'Connector_PinHeader_2.54mm:PinHeader_1x%02d_P2.54mm_Vertical' % n


def _circuit_parts(tables, circuit):
    return {c['name']: c for c in tables.get('CircuitComponentDefinition', []) if c.get('circuit_name') == circuit}


def _value(part):
    v = (part.get('value') or '').replace(' ohm', '')
    return v or part.get('part_kind', '')


def design(record, tables=None):
    from board.custom import board_object as bo
    from board.custom import electrical_check as EC
    t = record['target']
    board, circuit = t['board'], t['circuit']
    tables = tables if tables is not None else EC.tables_for(None)
    circ_parts = _circuit_parts(tables, circuit)
    comps, nets, unconnected, inside = [], {}, [], []
    # 1. which board pins carry which circuit net (from the components' signal ports)
    port_net = {}
    for p in record['SchematicComponentPort']:
        if p['kind'] == 'signal' and p.get('pin') and p.get('net'):
            port_net[p['pin']] = p['net']
    r = bo.rows_for(board, tables)
    board_net_of = {p['canonical']: p['net'] for p in r.get('pins', [])}
    wire = {board_net_of[c]: n for c, n in port_net.items() if c in board_net_of}   # the board's own net -> the circuit's net
    # 2. the headers: every pin carrying a net the components use, by the circuit's name
    by_conn = {}
    for cp in r.get('connector_pins', []):
        by_conn.setdefault(cp['connector'], []).append(cp)
    jn = 0
    for c in sorted(r.get('connectors', []), key=lambda c: c['ref']):
        if c['kind'] != 'header':
            continue
        jn += 1
        lib_id, fp = _header_lib(int(c['pin_count']))
        ref = 'J%d' % jn
        conn = {}
        for cp in sorted(by_conn.get(c['connector'], []), key=lambda x: int(x['number'])):
            net = wire.get(cp['net']) or ('GND' if cp['net'] == 'GND' else '')
            if net:
                conn[str(cp['number'])] = net
            else:
                unconnected.append((ref, str(cp['number']), '%s:%s %s' % (c['connector'], cp['number'], cp['label'])))
        comps.append({'ref': ref, 'lib_id': lib_id, 'value': c['connector'], 'footprint': fp, 'role': 'header', 'manufacturer': '', 'mpn': '',
                      'package': '1x%02d 2.54 mm' % int(c['pin_count']), 'pins': conn, 'uno_connector': c['name'], 'component': ''})
    # 3. the parts of every component, on the circuit's nets
    refs = set()
    for part in sorted(record['SchematicComponentPart'], key=lambda p: (p['component'], p['order'])):
        src = (part.get('notes') or '')
        if not src.startswith('CircuitComponentDefinition:'):
            inside.append('%s %s on %s: %s' % (part['ref'], part['part_kind'], part.get('port') or '-', part.get('rule', '')))
            continue
        row = circ_parts.get(src.split(':', 1)[1])
        lib = KIND_LIB.get(part['part_kind'])
        if row is None or lib is None:
            raise DesignRefused('no %s for %s (%s): add its circuit row or its KiCad library entry (KIND_LIB)' % (
                'circuit row' if row is None else 'library entry', part['name'], part['part_kind']))
        lib_id, fp, order = lib
        labels = EC._pins(row)
        if len(labels) != len(order):
            raise DesignRefused('%s has %d pins on the circuit, its symbol %s takes %d' % (part['name'], len(labels), lib_id, len(order)))
        ref = part['ref']
        while ref in refs:
            ref += "'"
        refs.add(ref)
        comps.append({'ref': ref, 'lib_id': lib_id, 'value': _value(part), 'footprint': fp, 'role': part['role'], 'manufacturer': '', 'mpn': '',
                      'package': '', 'pins': dict(zip(order, labels)), 'component': part['component']})
    for c in comps:
        for pin, net in c['pins'].items():
            nets.setdefault(net, []).append((c['ref'], pin))
    return {'board': record['target']['hardware_solution'] or '%s@%s' % (circuit, board), 'host': board, 'components': comps, 'nets': nets,
            'unconnected': unconnected, 'inside_chip': inside, 'signals': port_net}


def libs_needed(d):
    return sorted({c['lib_id'] for c in d['components']} | {W.POWER_LIB[n] for n in d['nets'] if n in W.POWER_LIB} | {'power:PWR_FLAG'})


def write(record, libs, tables=None):
    d = design(record, tables)
    t = record['target']
    text, report = W.write(d, libs, title='%s - schematic of the solved components' % d['board'],
                           comment='derived from %s (circuit %s on %s); solver %s' % (t['hardware_solution'], t['circuit'], t['board'],
                                                                                    record.get('inputs_sha256', '')[:12]))
    report['inside_chip'] = d['inside_chip']
    report['design'] = d
    return text, report


def libs_from(fetch, d):
    """{lib_id: text} for every symbol the design needs; `fetch(lib, name)` returns one library entry's text."""
    return {lib_id: fetch(*lib_id.split(':', 1)) for lib_id in libs_needed(d)}



def netlist_nets(netlist_text):
    """{net name: sorted ['REF.PIN', ...]} from KiCad's `sch export netlist --format kicadsexpr` (KiCad prefixes a local label's net with '/';
    unconnected-pin nets are left out)."""
    import re
    out = {}
    for m in re.finditer(r'\(net \(code "\d+"\) \(name "([^"]*)"\)(.*?)\)\s*(?=\(net |\)\s*\)\s*$)', netlist_text, re.S):
        name = m.group(1).lstrip('/')
        if name.startswith('unconnected-'):
            continue
        out[name] = sorted('%s.%s' % n for n in re.findall(r'\(node \(ref "([^"]+)"\) \(pin "([^"]+)"\)', m.group(2)))
    return out


def _pin_number(lib_text, name_or_number):
    """A symbol pin's NUMBER from its name or number (the design keys LED pins by name, A / K)."""
    from pcb.custom import sexpr as S
    tree = S.parse(lib_text)
    for p in S.find_all(tree, 'pin'):
        num, nm = S.value(p, 'number'), S.value(p, 'name')
        if num is not None and name_or_number in (str(num), str(nm)):
            return str(num)
    return name_or_number


def parity(d, libs, netlist_text):
    """KiCad's own netlist against the design: every net the design wires must come back from KiCad with exactly those pins.
    -> (same: bool, [difference in words])"""
    want = {}
    for c in d['components']:
        for pin, net in c['pins'].items():
            want.setdefault(net, []).append('%s.%s' % (c['ref'], _pin_number(libs[c['lib_id']], pin)))
    got = netlist_nets(netlist_text)
    diff = []
    for net in sorted(set(want) | set(got)):
        a, b = sorted(want.get(net, [])), got.get(net, [])
        if a != b:
            diff.append('%s: the rows wire %s, KiCad reads %s' % (net, ', '.join(a) or 'nothing', ', '.join(b) or 'nothing'))
    return not diff, diff


def render(record, tables=None):
    """Through the pcb engine (pcb.custom.pcb_engines: a local kicad-cli, the image, or a pcb.engines worker): the library symbols, the
    sheet, KiCad's electrical-rule check, its netlist (compared with the rows: `parity`) and the SVG drawing.
    -> {'name', 'kicad_sch', 'sha256', 'erc': {errors, warnings, by_type}, 'parity': (same, diff), 'svg', 'report'}; EngineRefused when no
    engine is reachable (said, never faked)."""
    import hashlib
    from collections import Counter
    from pcb.custom import pcb_engines as E
    d = design(record, tables)
    libs = {lib_id: E.library('symbol', *lib_id.split(':', 1))['text'] for lib_id in libs_needed(d)}
    text, report = write(record, libs, tables)
    fn = '%s.kicad_sch' % d['board'].replace('@', '-').replace(':', '-')
    run = lambda args: E.run(args + [fn], {fn: text}, source_date=E.SOURCE_DATE)   # noqa: E731
    erc_res = run(['sch', 'erc', '--format', 'json', '--severity-all', '-o', 'erc.json'])
    erc = json.loads(erc_res['files'].get('erc.json', b'{}') or b'{}')
    v = [x for s in erc.get('sheets', []) for x in s.get('violations', [])]
    net = run(['sch', 'export', 'netlist', '--format', 'kicadsexpr', '-o', 'net.net'])['files'].get('net.net', b'').decode()
    svg_files = run(['sch', 'export', 'svg', '-o', 'svg/'])['files']
    svg = next((b.decode() for k, b in svg_files.items() if k.endswith('.svg')), '')
    return {'name': fn, 'kicad_sch': text, 'sha256': hashlib.sha256(text.encode()).hexdigest(),
            'erc': {'errors': sum(1 for x in v if x.get('severity') == 'error'), 'warnings': sum(1 for x in v if x.get('severity') == 'warning'),
                    'by_type': dict(Counter('%s %s' % (x.get('severity'), x.get('type')) for x in v))},
            'parity': parity(d, libs, net), 'svg': svg, 'report': report}
