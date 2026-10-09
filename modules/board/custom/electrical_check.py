"""
@module board.custom.electrical_check

ucd-0c (UNO_CORE_DEMO_PLAN.md §1, §5f item 3, §5g's adopted list): PHASE-1 ELECTRICAL CHECKS over the demo circuit
as rows — `BoardPinNet` (board.custom.board_pin_nets) ties a `BoardPin` to one of electrodevice's
`CircuitNetDefinition` nets; this module walks those rows plus `CircuitComponentDefinition` (the parts) and
answers a short, named list of FINDINGS: {rule, status, subject, detail, cite}. `status` is one of:
  ok            the rule checked out, the number/why said plainly
  warn          the rule did not refuse but names something to define/fix (e.g. an undefined pull)
  refuse        the rule failed outright (a real electrical problem — two drivers, no shared ground, over current)
  undetermined  the rule could not be evaluated because a number is not cited — NEVER a guess; `detail` names what
                is missing

Phase-1 rules (§1's bench, uno-button-clock): (a) LED current against the DRIVING PIN's own cited max_ma and the
board's own cited logic level; (b) a net with a driver-role BoardPinNet has exactly one driver; (c) every component
reaches the circuit's own ground net, which itself ties to the board's GND; (d) an input-role pin on a net driven
by this SAME board is level-compatible (one board, one logic level); (e) the button's pull is DEFINED — either an
external pull resistor on its net, or a PinClaim with `pull='up'` for its board pin — else a WARN naming the gap.

Nothing here is a guess: a number not cited (a board's own logic level, a part's own rating) makes that finding
`undetermined`, naming exactly what is missing — never a made-up value.
"""
import json


# -------------------------------------------------------------------- cited facts this module itself needs
#: the board's own logic level (V_pin) — cited: board.custom.board_uno's own BoardHardware.power_rails_json entry
#: {'net': '+5V', 'volts': 5.0}, itself from the Arduino UNO R3 Full Pinout p.1 power header (board_uno.DOC/REV/URL
#: — the SAME document board_uno.py cites for pinout.max_current_io below). No board here means no cited number —
#: 'undetermined', never guessed.
BOARD_LOGIC_LEVEL_V = {'arduino-uno-r3': 5.0}


def _board_logic_level(board):
    v = BOARD_LOGIC_LEVEL_V.get(board)
    if v is None:
        return None, "the board's own logic level is not cited for %r" % board
    from board.custom.board_uno import DOC
    return v, "BoardHardware.power_rails_json net '+5V' = %s V (board_uno.py, %s p.1 power header)" % (v, DOC)


def _pin_max_ma(board_pin_row):
    """(max_ma, cite) | (None, why) — the BoardPin's own cited per-pin current limit (board_uno.py's
    electrical_json: {'max_ma': 20, 'fact': '<board>:pinout.max_current_io'})."""
    if board_pin_row is None:
        return None, 'no BoardPin row to read a current limit from'
    try:
        electrical = json.loads(board_pin_row.get('electrical_json') or '{}')
    except (TypeError, ValueError):
        electrical = {}
    max_ma = electrical.get('max_ma')
    fact = electrical.get('fact', '')
    if max_ma is None:
        return None, '%s: electrical_json carries no cited max_ma' % board_pin_row.get('name', '?')
    return max_ma, 'BoardPin.electrical_json max_ma=%s (fact %s)' % (max_ma, fact or 'uncited')


# -------------------------------------------------------------------- row lookups (pure over an already-built `tables`)
def _rows(tables, cls):
    return tables.get(cls) or []


def _by_name(rows, name):
    return next((r for r in rows if r.get('name') == name), None)


def circuit_rows(tables, circuit_name):
    """(circuit dict|None, [net dict,...], [component dict,...], [BoardPinNet dict,...]) for one circuit."""
    circuit = _by_name(_rows(tables, 'CircuitDefinition'), circuit_name)
    nets = [n for n in _rows(tables, 'CircuitNetDefinition') if n.get('circuit_name') == circuit_name]
    comps = [c for c in _rows(tables, 'CircuitComponentDefinition') if c.get('circuit_name') == circuit_name]
    pin_nets = [p for p in _rows(tables, 'BoardPinNet') if p.get('circuit') == circuit_name]
    return circuit, nets, comps, pin_nets


def _net_row_by_label(nets, label):
    return next((n for n in nets if n.get('net') == label), None)


def _pin_nets_on(pin_nets, net_row_name):
    return [p for p in pin_nets if p.get('circuit_net') == net_row_name]


def _params(component):
    try:
        return json.loads(component.get('params_json') or '{}')
    except (TypeError, ValueError):
        return {}


def _pins(component):
    try:
        return json.loads(component.get('pins_json') or '[]')
    except (TypeError, ValueError):
        return []


# -------------------------------------------------------------------- the net-reachability graph (rule c)
class _UnionFind:
    def __init__(self, items):
        self._p = {x: x for x in items}

    def find(self, x):
        self._p.setdefault(x, x)
        root = x
        while self._p[root] != root:
            root = self._p[root]
        while self._p[x] != root:
            self._p[x], x = root, self._p[x]
        return root

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self._p[ra] = rb


def _net_graph(nets, comps):
    uf = _UnionFind(n['net'] for n in nets)
    for c in comps:
        pins = _pins(c)
        for p in pins[1:]:
            uf.union(pins[0], p)
    return uf


# -------------------------------------------------------------------- the five Phase-1 rules
def _finding(rule, status, subject, detail, cite):
    return {'rule': rule, 'status': status, 'subject': subject, 'detail': detail, 'cite': cite}


def _check_led_current(board, nets, comps, pin_nets, board_pins_by_name):
    """(a) LED current = (V_pin - v_forward) / ohms, checked against the DRIVING PIN's own cited max_ma."""
    leds = [c for c in comps if c.get('kind') == 'led']
    out = []
    for led in leds:
        pins = _pins(led)
        if len(pins) != 2:
            out.append(_finding('led_current', 'undetermined', led.get('name', '?'),
                                'expected 2 pins (anode, cathode), got %r' % (pins,), ''))
            continue
        anode_label, cathode_label = pins[0], pins[1]
        # the resistor between the anode and some OTHER (upstream) net — the series current limiter
        resistor = next((c for c in comps if c.get('kind') == 'resistor' and anode_label in _pins(c)), None)
        if resistor is None:
            out.append(_finding('led_current', 'undetermined', led.get('name', '?'),
                                'no series resistor found on %s — cannot derive the limited current' % anode_label, ''))
            continue
        r_pins = _pins(resistor)
        upstream_label = next((p for p in r_pins if p != anode_label), None)
        ohms = _params(resistor).get('ohms')
        v_forward = _params(led).get('v_forward')
        upstream_row = _net_row_by_label(nets, upstream_label) if upstream_label else None
        drivers = [p for p in _pin_nets_on(pin_nets, upstream_row['name'])] if upstream_row else []
        drivers = [p for p in drivers if p.get('role') == 'driver']
        v_pin, v_cite = (None, '') if not drivers else _board_logic_level(board)
        pin_row = board_pins_by_name.get(drivers[0].get('board_pin', '')) if drivers else None
        max_ma, max_ma_cite = _pin_max_ma(pin_row) if pin_row is not None else (None, 'no driving BoardPinNet found on %s' % upstream_label)
        missing = [name for name, val in (('ohms', ohms), ('v_forward', v_forward), ('V_pin', v_pin), ('pin max_ma', max_ma)) if val is None]
        if missing:
            out.append(_finding('led_current', 'undetermined', led.get('name', '?'),
                                'cannot compute: missing %s' % ', '.join(missing),
                                led.get('description', '')))
            continue
        current_ma = (v_pin - v_forward) / ohms * 1000.0
        status = 'ok' if current_ma <= max_ma else 'refuse'
        detail = ('I = (%.2f V - %.2f V) / %s ohm = %.3f mA <= pin %s max_ma=%s'
                 % (v_pin, v_forward, ohms, current_ma, pin_row.get('canonical', '?'), max_ma)) if status == 'ok' else \
                 ('I = (%.2f V - %.2f V) / %s ohm = %.3f mA EXCEEDS pin %s max_ma=%s'
                 % (v_pin, v_forward, ohms, current_ma, pin_row.get('canonical', '?'), max_ma))
        cite = '%s; %s; LED v_forward: %s' % (v_cite, max_ma_cite, led.get('description', '(no citation on the row)'))
        out.append(_finding('led_current', status, led.get('name', '?'), detail, cite))
    return out


def _check_single_driver(nets, pin_nets):
    """(b) a net with at least one driver-role BoardPinNet has EXACTLY one — never two."""
    out = []
    by_net = {}
    for p in pin_nets:
        if p.get('role') == 'driver':
            by_net.setdefault(p['circuit_net'], []).append(p)
    for net_row_name, drivers in sorted(by_net.items()):
        net = next((n for n in nets if n['name'] == net_row_name), {'net': net_row_name})
        names = sorted(d.get('board_pin', '') for d in drivers)
        if len(drivers) > 1:
            out.append(_finding('single_driver', 'refuse', net['net'],
                                'TWO OR MORE drivers on one net: %s — a net may have at most one' % ', '.join(names), ''))
        else:
            out.append(_finding('single_driver', 'ok', net['net'],
                                'exactly one driver: %s' % names[0], ''))
    return out


def _check_shared_ground(nets, comps, pin_nets):
    """(c) every component on the circuit reaches the circuit's own ground net, which itself ties to the board's
    GND (a BoardPinNet row with role='ground')."""
    ground_net = next((n for n in nets if n.get('is_ground')), None)
    if ground_net is None:
        return [_finding('shared_ground', 'undetermined', '(circuit)', 'no net is flagged is_ground on this circuit', '')]
    board_ties_ground = any(p.get('role') == 'ground' for p in _pin_nets_on(pin_nets, ground_net['name']))
    uf = _net_graph(nets, comps)
    ground_root = uf.find(ground_net['net'])
    touched = {p for c in comps for p in _pins(c)}
    unreachable = sorted(n for n in touched if uf.find(n) != ground_root)
    if unreachable:
        return [_finding('shared_ground', 'refuse', '(circuit)',
                         'net(s) %s never reach the ground net %r through any component' % (unreachable, ground_net['net']), '')]
    if not board_ties_ground:
        return [_finding('shared_ground', 'warn', '(circuit)',
                         "every component reaches %r, but no BoardPinNet ties that net to the board's own GND"
                         % ground_net['net'], '')]
    return [_finding('shared_ground', 'ok', '(circuit)',
                     'every component reaches the ground net %r, which ties to the board\'s own GND' % ground_net['net'],
                     'BoardPinNet role=ground on %s' % ground_net['name'])]


def _check_level_compatible(nets, pin_nets):
    """(d) an input-role pin on a net driven by a board output is level-compatible — same board, one cited logic
    level, so 'ok', said so; a cross-board net (not modelled this phase) would be 'undetermined', never guessed."""
    out = []
    by_net = {}
    for p in pin_nets:
        by_net.setdefault(p['circuit_net'], []).append(p)
    for net_row_name, rows in sorted(by_net.items()):
        net = next((n for n in nets if n['name'] == net_row_name), {'net': net_row_name})
        drivers = [r for r in rows if r.get('role') == 'driver']
        inputs = [r for r in rows if r.get('role') == 'input']
        if not drivers or not inputs:
            continue
        boards = {d.get('board') for d in drivers} | {i.get('board') for i in inputs}
        if len(boards) == 1:
            board = next(iter(boards))
            v, cite = _board_logic_level(board)
            if v is None:
                out.append(_finding('level_compatible', 'undetermined', net['net'], cite, ''))
            else:
                out.append(_finding('level_compatible', 'ok', net['net'],
                                    'driver and input share one board (%s) at one cited logic level (%s V) — compatible'
                                    % (board, v), cite))
        else:
            out.append(_finding('level_compatible', 'undetermined', net['net'],
                                'cross-board net (%s) — level compatibility across boards is not modelled this phase'
                                % ', '.join(sorted(boards)), ''))
    return out


def _check_pull_defined(nets, comps, pin_nets, pin_claims):
    """(e) the button pin's pull is DEFINED: an external pull resistor on its net, OR a PinClaim pull='up' for its
    board pin — else a WARN naming the gap (never a refusal — a novice still gets a working, if incomplete, bench)."""
    button_pins = [p for p in pin_nets if p.get('role') == 'input' and p.get('board_pin')
                  and not any(d.get('role') == 'driver' and d.get('circuit_net') == p.get('circuit_net') for d in pin_nets)]
    out = []
    for bp in button_pins:
        net = next((n for n in nets if n['name'] == bp['circuit_net']), {'net': bp['circuit_net']})
        has_pull_resistor = any(c.get('kind') == 'resistor' and net['net'] in _pins(c) for c in comps)
        canonical = bp.get('board_pin', '').rpartition(':')[2]
        claim = next((c for c in (pin_claims or []) if c.get('board_pin', '').endswith(':%s' % canonical)), None)
        claim_pull = (claim or {}).get('pull', '')
        if has_pull_resistor:
            out.append(_finding('pull_defined', 'ok', bp['board_pin'],
                                'an external pull resistor is on %s' % net['net'], ''))
        elif claim_pull == 'up':
            out.append(_finding('pull_defined', 'ok', bp['board_pin'],
                                "PinClaim %s: pull='up' (internal pull-up)" % claim.get('name', '?'), ''))
        else:
            out.append(_finding('pull_defined', 'warn', bp['board_pin'],
                                '%s has no pull: define it (internal pull-up or a resistor)' % canonical, ''))
    return out


# -------------------------------------------------------------------- the public door
def check(circuit_name, binding_or_board, tables, pin_claims=None):
    """[finding, ...] for one circuit over one board (or a '<solution>@<board>'/'<solution>' binding — see
    `_resolve` below). `tables` = {'CircuitDefinition'|'CircuitNetDefinition'|'CircuitComponentDefinition'|
    'BoardPinNet'|'BoardPin': [dict, ...]} (`tables_for` below builds this from a live manager or the seeds).
    `pin_claims` overrides the derived PinClaim list for rule (e) — a test seam (`cmod.custom.claims.pin_claims`'s
    own `overrides` only edits an EXISTING assignment-derived claim; a bare board/circuit test has no task claiming
    D2 at all, so a caller that wants to PROVE the 'turns ok' half of rule (e) hands a synthetic claim list here)."""
    board, derived_claims = _resolve(binding_or_board, tables)
    circuit, nets, comps, pin_nets = circuit_rows(tables, circuit_name)
    if circuit is None:
        return [_finding('circuit_exists', 'undetermined', circuit_name,
                         'no CircuitDefinition named %r (GET /api/electrodevice/circuits lists them)' % circuit_name, '')]
    board_pins_by_name = {p['name']: p for p in _rows(tables, 'BoardPin')}
    claims = pin_claims if pin_claims is not None else derived_claims
    out = []
    out += _check_led_current(board, nets, comps, pin_nets, board_pins_by_name)
    out += _check_single_driver(nets, pin_nets)
    out += _check_shared_ground(nets, comps, pin_nets)
    out += _check_level_compatible(nets, pin_nets)
    out += _check_pull_defined(nets, comps, pin_nets, claims)
    return out


def _resolve(binding_or_board, tables):
    """(board_name, [PinClaim dict, ...]) — `binding_or_board` is a bare board name (the CLI/door's `--board`,
    `?board=`: no FirmwareSolution/HardwareBinding involved, PinClaims empty, rule (e) can only warn) or a
    '<solution>' / '<solution>@<board>' naming a real FirmwareSolution: its DEFAULT binding's own PinClaims are
    derived (`cmod.custom.claims.pin_claims`) so rule (e) can read a REAL pull claim when one exists. Never raises
    — any resolution failure just means no claims (honest warn, never a guess)."""
    from board.custom import board_object as BO
    try:
        from cmod.custom import binding as BND
        from cmod.custom import claims as C
    except Exception:  # pragma: no cover — cmod absent on this node: board-only checks still run
        return BO.board_name(binding_or_board), []
    manager = tables.get('_manager')
    try:
        b = BND.resolve(binding_or_board, manager=manager)
    except Exception:
        b = None
    if b is None:
        return BO.board_name(binding_or_board), []
    board = b.get('board', '') or BO.board_name(binding_or_board)
    try:
        sol = BND._solution_dict(b.get('solution', ''), manager=manager) or {}
        graph = sol.get('graph', '')
        claims = C.pin_claims(b, graph, manager=manager) if graph else []
    except Exception:
        claims = []
    return board, claims


def tables_for(manager=None):
    """{class: [dict, ...]} merging the board layers (BoardPin) with the electrodevice circuit rows and this
    board's own BoardPinNet rows. Pure/live duality PER CLASS (same posture as `cmod.custom.claims._chain_tables`/
    `_live_assignments`): the seed is the base, a live manager's own rows overlay it class by class WHERE IT
    actually has any — so a manager that has not yet materialized one of these classes (a bare test manager, or a
    server mid-boot) still reads a complete, correct picture instead of an empty one. `_manager` (private key)
    rides along so `_resolve` above can derive PinClaims through a live manager without a second parameter
    threaded through every caller."""
    from board.custom import board_object as BO
    out = BO.seed_tables()
    from electrodevice.objects.circuit._shared import SEED_CIRCUITS, SEED_CIRCUIT_NETS, SEED_CIRCUIT_COMPONENTS
    from board.custom.board_pin_nets import SEED_BOARD_PIN_NETS
    out['CircuitDefinition'] = list(SEED_CIRCUITS)
    out['CircuitNetDefinition'] = list(SEED_CIRCUIT_NETS)
    out['CircuitComponentDefinition'] = list(SEED_CIRCUIT_COMPONENTS)
    out['BoardPinNet'] = list(SEED_BOARD_PIN_NETS)
    out['_manager'] = manager
    if manager is not None:
        for cls, rows in BO.tables_from_manager(manager).items():
            if rows:
                out[cls] = rows
        for cls in ('CircuitDefinition', 'CircuitNetDefinition', 'CircuitComponentDefinition', 'BoardPinNet'):
            tbl = (manager.objectTables or {}).get(cls, {}) or {}
            rows = [{k: v for k, v in vars(r).items() if not k.startswith('_') and k != 'manager'} for r in tbl.values()]
            if rows:
                out[cls] = rows
    return out


def _main(argv):
    """`python3 -m board.custom.electrical_check <circuit> [--board <board>|--binding <solution>[@<board>]]` — the
    CLI's own backend (`pol board circuit-check`, polari-cli scripts/board.sh)."""
    import sys
    circuit = argv[0] if argv else 'uno-button-clock'
    board_or_binding = 'arduino-uno-r3'
    i = 1
    while i < len(argv):
        if argv[i] in ('--board', '--binding') and i + 1 < len(argv):
            board_or_binding = argv[i + 1]
            i += 2
        else:
            i += 1
    tables = tables_for(manager=None)
    findings = check(circuit, board_or_binding, tables)
    ok = all(f['status'] != 'refuse' for f in findings)
    print('%s on %s: %s' % (circuit, board_or_binding, 'ok' if ok else 'REFUSED'))
    for f in findings:
        print('  [%s] %-18s %-14s %s' % (f['status'].upper(), f['rule'], f['subject'], f['detail']))
        if f.get('cite'):
            print('        cite: %s' % f['cite'])
    return 0 if ok else 1


if __name__ == '__main__':
    import sys
    sys.exit(_main(sys.argv[1:]))
