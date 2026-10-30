"""
@module pcb.custom.bench_export

kxc-5 (AI-Notes/plans/KICAD_INTERCHANGE_PLAN.md): EXPORT WHAT WE CAN - A BENCH AS A KiCad SCHEMATIC. His rulings 2026-10-30: Polari is the source of truth
and "we should make what exports we can from polari to kiCad possible happen"; dev boards, breadboards and PCBs are equally Boards on the Bench. So the
export reads the Bench level only (footholds + connections, board.custom.bench_nets) and writes it with the existing writer (pcb.custom.schematic_writer):

  every connector-like group of footholds on a dev board or a PCB -> ONE generic KiCad header symbol (Connector_Generic:Conn_01xNN, or Conn_02xNN_Odd_Even
      for a two-row header), pinned exactly as the footholds are numbered - the header IS the foothold set, no pin mapping to guess
  a breadboard -> no symbol: its strips and rails are only nets (KiCad has no breadboard part)
  the nets -> each board's own joins + the bench connections (union-find), named by the most specific net name on them (a power name first)

  design(boards, connections, title) -> (writer design, mapping {(board id, foothold): (ref, pin)}, report)
  compare(mapping, nets, kicad_netlist_rows)  the re-exported KiCad netlist groups the same pins as our bench nets?

The design is the writer's input; the library texts come from the KiCad worker (pcb_engines.library) - a host with no KiCad refuses in words.

kxc-5b (his addition 2026-10-30: "if there are not direct conversions between KiCAD and polari data, we can attempt to encode that data into standard
label and description data in KiCAD, for things where it is critical"): each written part carries hidden `Polari.*` properties (as KiCad itself keeps
`Sim.*`) - Polari.Board (the Board-on-the-Bench id), Polari.Definition (kind/definition), Polari.Connector, Polari.Drive (per pin: direction, logic or
rail volts, source / sink mA - the bench's drive data) and Polari.Firmware (per pin: variant:variable:role, + ':if-flashed' when the board is not recorded as running that firmware). The ingest reads them back
(SchematicSymbol.polari_json).
"""
import re

POWER_NAMES = ('GND', '+5V', '+3V3')
#: our rail names -> the writer's power-symbol names (KiCad's power library spells them +5V / +3V3 / GND)
POWER_ALIASES = {'5V': '+5V', '3V3': '+3V3', '+5V': '+5V', '+3V3': '+3V3', 'GND': 'GND'}


class _UF:
    def __init__(self):
        self.p = {}

    def find(self, a):
        self.p.setdefault(a, a)
        while self.p[a] != a:
            self.p[a] = self.p[self.p[a]]
            a = self.p[a]
        return a

    def union(self, a, b):
        self.p[self.find(a)] = self.find(b)


def _groups(footholds):
    """{connector: [footholds]} - J1:9 -> J1, DIGITAL_L:7 -> DIGITAL_L; footholds without a 'name:n' shape are skipped (a breadboard's holes)."""
    out = {}
    for f in footholds:
        m = re.match(r'^(.+):(\d+)$', f['foothold'])
        if m and f['kind'] in ('header-pin', 'connector-pin', 'test-pad', 'pad'):
            out.setdefault(m.group(1), []).append((int(m.group(2)), f))
    return out


def _net_name(members):
    names = [m.get('net') or '' for m in members if m.get('net')]
    for n in names:
        if POWER_ALIASES.get(n) in POWER_NAMES:
            return POWER_ALIASES[n]
    return re.sub(r'[^A-Za-z0-9_+\-./]', '_', sorted(names, key=lambda n: (n.startswith('Net-') or n.startswith('unconnected'), len(n), n))[0]) if names else ''


def whole_parts():
    """{definition: (lib_id, footprint, pin_of(connector, number) -> symbol pin, source)} - a dev board KiCad has as ONE part, with a CITED pin map."""
    from board.custom import board_c3 as C3
    return {'esp32-c3': ('%s:%s' % (C3.KICAD_DEVKIT[0], C3.KICAD_DEVKIT[1]), C3.KICAD_DEVKIT[2], lambda conn, n: C3.kicad_devkit_pin(conn, n),
                         'board_c3.kicad_devkit_pin (fact esp32-c3:kicad.symbols)')}


def design(boards, connections, title='bench', two_rows=None, use_whole_parts=True, firmware=None):
    """boards = {board id: {'label', 'footholds': [...], 'definition'?}}; two_rows = {(board id, connector)} drawn as 2 x N headers; a board whose
    definition KiCad has as one whole part (whole_parts: the ESP32-C3-DevKitM-1) is written as that part when use_whole_parts."""
    two_rows = two_rows or set()
    uf, index = _UF(), {}
    for bid, b in boards.items():
        for f in b['footholds']:
            index[(bid, f['foothold'])] = f
            uf.find((bid, f['node']))
    for c in connections:
        a, b = index.get((c['from_board'], c['from_foothold'])), index.get((c['to_board'], c['to_foothold']))
        if a is not None and b is not None:
            uf.union((c['from_board'], a['node']), (c['to_board'], b['node']))
    members = {}
    for (bid, fid), f in index.items():
        members.setdefault(uf.find((bid, f['node'])), []).append(dict(f, board=bid))
    names, used = {}, set()
    for root, ms in sorted(members.items(), key=lambda kv: str(kv[0])):
        base = _net_name(ms) or 'N_%s_%s' % (re.sub(r'\W', '_', root[0]), re.sub(r'\W', '_', root[1]))
        name, k = base, 1
        # a power name is GLOBAL in KiCad: only ONE bench net may carry it, or two rails nothing joins would merge (the UNO's +3V3 and the
        # C3's 3V3); a second, separate group gets a numbered plain label instead
        while name in used:
            k += 1
            name = '%s_%d' % (base, k)
        used.add(name)
        names[root] = name
    comps, mapping, report = [], {}, {'boards': [], 'skipped': []}
    fw = firmware or {}
    jn = 0
    for bid in sorted(boards):
        b = boards[bid]
        groups = _groups(b['footholds'])
        whole = whole_parts().get(b.get('definition', '')) if use_whole_parts else None
        if whole and groups:
            lib_id, fp, pin_of, src = whole
            jn += 1
            ref = 'J%d' % jn
            wired = {}
            for conn in sorted(groups):
                for p, f in groups[conn]:
                    root = uf.find((bid, f['node']))
                    sp = str(pin_of(conn, p))
                    mapping[(bid, f['foothold'])] = (ref, sp)
                    if len(members[root]) > 1:
                        wired[sp] = names[root]
            pairs = [(str(pin_of(conn, p)), f) for conn in sorted(groups) for p, f in groups[conn]]
            comps.append({'ref': ref, 'lib_id': lib_id, 'value': b.get('label', bid), 'footprint': fp, 'role': 'module', 'pins': wired,
                          'polari_board': bid, 'polari_connector': ', '.join(sorted(groups)),
                          'polari_fields': polari_fields(bid, b, ', '.join(sorted(groups)), pairs, fw)})
            report['boards'].append({'board': bid, 'connector': ', '.join(sorted(groups)), 'ref': ref, 'symbol': lib_id, 'pins': sum(len(v) for v in groups.values()),
                                     'pin_map': src})
            continue
        if not groups:
            report['skipped'].append('%s (%s): no header-like footholds - its nodes are nets only' % (bid, b.get('label', '')))
            continue
        for conn in sorted(groups):
            pins = sorted(groups[conn], key=lambda t: t[0])
            n = max(p for p, _ in pins)
            jn += 1
            ref = 'J%d' % jn
            xs, ys = {round(f['x_mm'], 2) for _, f in pins}, {round(f['y_mm'], 2) for _, f in pins}
            # two rows when asked, or when the footholds' own positions are a 2 x N grid (the UNO's ICSP) - never guessed without positions
            two = (bid, conn) in two_rows or (n >= 4 and n % 2 == 0 and -1.0 not in xs | ys and ((len(xs) == 2 and len(ys) == n // 2) or (len(ys) == 2 and len(xs) == n // 2)))
            lib = 'Connector_Generic:Conn_02x%02d_Odd_Even' % ((n + 1) // 2) if two else 'Connector_Generic:Conn_01x%02d' % n
            wired = {}
            for p, f in pins:
                net = names[uf.find((bid, f['node']))]
                mapping[(bid, f['foothold'])] = (ref, str(p))
                if len(members[uf.find((bid, f['node']))]) > 1:   # a lone foothold stays unconnected (the writer lists it)
                    wired[str(p)] = net
            comps.append({'ref': ref, 'lib_id': lib, 'value': '%s %s' % (b.get('label', bid), conn), 'footprint': b.get('footprints', {}).get(conn, ''),
                          'role': 'header', 'pins': wired, 'polari_board': bid, 'polari_connector': conn,
                          'polari_fields': polari_fields(bid, b, conn, [(str(p), f) for p, f in pins], fw)})
            report['boards'].append({'board': bid, 'connector': conn, 'ref': ref, 'symbol': lib, 'pins': n})
    nets = {}
    for c in comps:
        for pin, net in c['pins'].items():
            nets.setdefault(net, []).append((c['ref'], pin))
    return {'board': re.sub(r'\W', '-', title), 'components': comps, 'nets': nets, 'unconnected': []}, mapping, report


def _drive(f):
    v = f['rail_volts'] if f['direction'] == 'supply' else f['logic_volts']
    bits = [f['direction']] + (['%gV' % v] if v >= 0 else []) + (['src %gmA' % f['source_ma']] if f['source_ma'] > 0 else []) + \
        (['snk %gmA' % f['sink_ma']] if f['sink_ma'] > 0 else [])
    return ' '.join(bits)


def polari_fields(bid, board, connector, pairs, firmware):
    """The hidden Polari.* properties of one written part (kxc-5b): identity + per-pin drive + per-pin firmware use - the critical data KiCad has no field for."""
    drive = '; '.join('%s=%s' % (sp, _drive(f)) for sp, f in pairs if f['direction'] != 'undetermined')
    uses = '; '.join('%s=%s' % (sp, ','.join('%s:%s:%s%s' % (u['variant'], u['variable'], u['role'], '' if u.get('running', True) else ':if-flashed')
                                             for u in firmware.get((bid, f['chip_pin']), [])))
                     for sp, f in pairs if f.get('chip_pin') and firmware.get((bid, f['chip_pin'])))
    out = [('Polari.Board', bid), ('Polari.Definition', board.get('definition', '')), ('Polari.Connector', connector), ('Polari.Drive', drive)]
    return out + ([('Polari.Firmware', uses)] if uses else [])


def compare(design_, kicad_rows):
    """Our design's nets vs KiCad's re-exported netlist: {'same', 'ours_only', 'kicad_only'} as pin-set groups (single-pin KiCad nets are unconnected pins)."""
    ours = {frozenset(v) for v in design_['nets'].values() if len(v) > 1}
    theirs = {}
    for name, ref, pin, _ in kicad_rows:
        theirs.setdefault(name, set()).add((ref, pin))
    theirs = {frozenset(v) for v in theirs.values() if len(v) > 1}
    return {'same': len(ours & theirs), 'ours_only': sorted(sorted(g) for g in ours - theirs), 'kicad_only': sorted(sorted(g) for g in theirs - ours)}


def libraries_needed(design_):
    from pcb.custom.schematic_writer import POWER_LIB
    return sorted({c['lib_id'] for c in design_['components']} | {POWER_LIB[n] for n in design_['nets'] if n in POWER_LIB} | {'power:PWR_FLAG'})


def fetch_libraries(design_):
    """{lib_id: symbol text} from the KiCad worker / local install (pcb_engines.library); EngineRefused when there is none."""
    from pcb.custom import pcb_engines as E
    out = {}
    for lib_id in libraries_needed(design_):
        lib, _, name = lib_id.partition(':')
        out[lib_id] = E.library('symbol', lib, name)['text']
    return out

