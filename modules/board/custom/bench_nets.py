"""
@module board.custom.bench_nets

bob-2 (AI-Notes/plans/BENCH_BOARDS_PLAN.md): CONNECTIONS ACROSS BOARDS. His example (2026-10-30): "define our PCB in KiCAD then import it and integrate it
with a simulated Breadboard wired to a dev board". The Bench works on footholds only, so a bench's electrical picture is:

  each Board's own joins     footholds with one `node` are joined inside that board (a breadboard strip, a PCB net, a dev board's GND pins)
  + BenchConnection rows     a wire / jumper between two footholds on any two Boards, or MATING (a header pin pushed into a breadboard hole)
  = bench nets               union-find over (board id, node)

  mate_header(board_id, header_footholds, breadboard_id, column, first_row)  the connections of a 1 x N header pushed into breadboard holes
                                                                              (pin k -> r<first_row + k - 1><column>)
  nets(boards, connections)  → [{net, members: [{board, foothold, ...}], drive: [...], findings: [...]}]
  check(net)                 the electrical findings on one bench net, from the foothold drive / signal data only:
      supply-conflict   two supplies at different voltages joined (a short between rails)
      supply-to-ground  a supply joined to a ground
      over-voltage      a chip pin's logic level below a supply or a driving pin's level on the same net (5 V into a 3.3 V pin)
  and a NOTE when only inputs / passive holes share a net (nothing on the bench drives it - a board's own pull is not a foothold fact yet)
  Unknown numbers (-1) never make a finding; they make an 'undetermined' note naming the foothold.

`boards` = {board id: [foothold rows]}; a board id is the Board on the Bench's id (board.custom.bench_boards: boards_json#1, breadboards_json#1.2, a
BenchBoard name).
"""


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


DRIVING = ('out', 'supply')


def mate_header(board_id, header_footholds, breadboard_id, column, first_row):
    """A 1 x N header pushed into a breadboard: header pin k lands in hole r<first_row + k - 1><column>. → BenchConnection dicts (kind mated)."""
    out = []
    for k, f in enumerate(sorted(header_footholds, key=lambda f: int(str(f).rsplit(':', 1)[-1])), 1):
        out.append({'from_board': board_id, 'from_foothold': f, 'to_board': breadboard_id, 'to_foothold': 'r%d%s' % (first_row + k - 1, column), 'kind': 'mated'})
    return out


def check(members):
    findings, notes = [], []
    supplies = [m for m in members if m['direction'] == 'supply']
    volts = sorted({m['rail_volts'] for m in supplies if m['rail_volts'] >= 0})
    grounds = [m for m in supplies if m['rail_volts'] == 0.0]
    rails = [m for m in supplies if m['rail_volts'] > 0]
    if len([v for v in volts if v > 0]) > 1:
        findings.append({'kind': 'supply-conflict', 'words': 'supplies at %s V joined: %s' % (' and '.join('%g' % v for v in volts if v > 0),
                                                                                              ', '.join('%s %s' % (m['board'], m['foothold']) for m in rails))})
    if grounds and rails:
        findings.append({'kind': 'supply-to-ground', 'words': 'a %g V supply (%s %s) joined to ground (%s %s)' % (rails[0]['rail_volts'], rails[0]['board'], rails[0]['foothold'],
                                                                                                          grounds[0]['board'], grounds[0]['foothold'])})
    highest = max([m['rail_volts'] for m in rails] + [m['logic_volts'] for m in members if m['direction'] in ('out', 'inout') and m['logic_volts'] > 0] + [0.0])
    for m in members:
        if m['direction'] in ('inout', 'in') and 0 < m['logic_volts'] < highest:
            src = next((x for x in members if x is not m and (x['rail_volts'] == highest or x['logic_volts'] == highest)), None)
            findings.append({'kind': 'over-voltage', 'words': '%s %s works at %g V but the net can carry %g V (%s %s)' % (m['board'], m['foothold'], m['logic_volts'], highest,
                                                                                                                 src['board'] if src else '?', src['foothold'] if src else '?')})
        if m['direction'] in ('inout', 'in', 'out') and m['logic_volts'] < 0 and m['chip_pin']:
            notes.append('%s %s: logic level undetermined' % (m['board'], m['foothold']))
    if not any(m['direction'] in DRIVING + ('inout',) for m in members) and any(m['direction'] == 'in' for m in members):
        # a NOTE, not a finding: a board may pull the line inside (the DevKitM-1's CHIP_PU has R5) and footholds do not carry pulls yet
        notes.append('nothing on the bench drives this net (only inputs / passive holes); a pull inside a board is not modelled at the foothold level')
    return findings, notes


def nets(boards, connections):
    uf = _UF()
    index = {}
    for bid, rows in boards.items():
        for f in rows:
            key = (bid, f['node'])
            index[(bid, f['foothold'])] = (key, f)
            uf.find(key)
    problems = []
    for c in connections:
        a, b = index.get((c['from_board'], c['from_foothold'])), index.get((c['to_board'], c['to_foothold']))
        if a is None or b is None:
            problems.append('connection %s %s -> %s %s: %s has no such foothold' % (c['from_board'], c['from_foothold'], c['to_board'], c['to_foothold'],
                                                                                   c['from_board'] if a is None else c['to_board']))
            continue
        uf.union(a[0], b[0])
    groups = {}
    for (bid, fid), (key, f) in index.items():
        groups.setdefault(uf.find(key), []).append(dict(f, board=bid))
    out = []
    for root, members in groups.items():
        boards_on = sorted({m['board'] for m in members})
        if len(boards_on) < 2:   # a net inside one board only is the board's own business (its definition level)
            continue
        findings, notes = check(members)
        named = sorted({m['net'] for m in members if m.get('net')})
        out.append({'net': ' / '.join(named) or '%s:%s' % root, 'boards': boards_on, 'members': sorted(members, key=lambda m: (m['board'], m['foothold'])),
                    'findings': findings, 'undetermined': notes})
    return sorted(out, key=lambda n: n['net']), problems


# ---------------------------------------------------------------- the stored side (BenchConnection rows on a live server)
def _rows(manager, cls):
    return list(((getattr(manager, 'objectTables', None) or {}).get(cls) or {}).values()) if manager is not None else []


def _boards(bench_name, manager):
    """{board id: footholds} of the Boards on a Bench that have footholds, + {id: row} of all of them."""
    from board.custom import bench_boards as BB
    from board.custom import footholds as FH
    rows = BB.boards_on_bench(bench_name, manager)
    if rows is None:
        return None, None
    feet, cache = {}, {}
    for r in rows:
        key = (r['definition_kind'], r['definition'])
        if key not in cache:
            cache[key] = FH.for_definition(*key, manager=manager)[0]
        if cache[key]:
            feet[r['id']] = cache[key]
    return feet, {r['id']: r for r in rows}


def connections_of(bench_name, manager):
    return [{k: getattr(o, k, '') for k in ('name', 'from_board', 'from_foothold', 'to_board', 'to_foothold', 'kind', 'colour', 'label')}
            for o in sorted(_rows(manager, 'BenchConnection'), key=lambda o: getattr(o, 'name', '')) if getattr(o, 'bench', '') == bench_name]


def bench_nets(bench_name, manager):
    """(nets, problems) | (None, why) - the bench's nets across boards from the stored connections."""
    feet, by_id = _boards(bench_name, manager)
    if feet is None:
        return None, 'no bench named %r' % bench_name
    return nets(feet, connections_of(bench_name, manager))


def _check_end(feet, by_id, board, foothold):
    if board not in by_id:
        return 'no Board %r on this bench (ids: %s)' % (board, ', '.join(sorted(by_id)))
    if board not in feet:
        return 'Board %r has no footholds (%s)' % (board, by_id[board]['footholds_note'])
    if foothold not in {f['foothold'] for f in feet[board]}:
        return 'Board %r has no foothold %r' % (board, foothold)
    return ''


def add_connections(manager, bench_name, conns):
    """(status, body): store BenchConnection rows after checking BOTH ends exist; all or none."""
    from board.objects.board.BenchConnection import BenchConnection
    feet, by_id = _boards(bench_name, manager)
    if feet is None:
        return 404, {'ok': False, 'error': 'no bench named %r' % bench_name}
    why = [w for c in conns for w in (_check_end(feet, by_id, c.get('from_board', ''), c.get('from_foothold', '')),
                                       _check_end(feet, by_id, c.get('to_board', ''), c.get('to_foothold', ''))) if w]
    if why:
        return 422, {'ok': False, 'error': '; '.join(why)}
    if manager is None:
        return 503, {'ok': False, 'error': 'no object manager: a connection is a stored row'}
    made = []
    for c in conns:
        name = '%s:%s:%s->%s:%s' % (bench_name, c['from_board'], c['from_foothold'], c['to_board'], c['to_foothold'])
        BenchConnection(manager=manager, name=name, bench=bench_name, from_board=c['from_board'], from_foothold=c['from_foothold'], to_board=c['to_board'],
                        to_foothold=c['to_foothold'], kind=c.get('kind', 'wire'), colour=c.get('colour', ''), label=c.get('label', ''), notes=c.get('notes', ''))
        made.append(name)
    n, problems = bench_nets(bench_name, manager)
    return 201, {'ok': True, 'bench': bench_name, 'added': made, 'nets': n, 'problems': problems}


def mate(manager, bench_name, body):
    """{board, connector, breadboard, column, first_row}: push a dev board's 1 x N header into breadboard holes (one mated connection per pin)."""
    feet, by_id = _boards(bench_name, manager)
    if feet is None:
        return 404, {'ok': False, 'error': 'no bench named %r' % bench_name}
    board, conn = body.get('board', ''), body.get('connector', '')
    pins = [f['foothold'] for f in feet.get(board, []) if f['foothold'].startswith(conn + ':')]
    if not pins:
        return 422, {'ok': False, 'error': 'Board %r has no header %r' % (board, conn)}
    return add_connections(manager, bench_name, mate_header(board, pins, body.get('breadboard', ''), str(body.get('column', 'a')), int(body.get('first_row', 1))))
