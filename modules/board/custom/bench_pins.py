"""
@module board.custom.bench_pins

bob-2b (AI-Notes/plans/BENCH_BOARDS_PLAN.md, his correction 2026-10-30): THE BENCH IS PINS, NOT A NETLIST. "The Bench level is focused around pins from board and
chips and their connections to firmware and the pin driving requirements being met from inherent properties of pins and defined connections." The wiring
(wires, mated headers, a breadboard's strips) is BOARD-level; this module CONVERTS it into what the Bench shows:

  pin_rows(boards, wiring, firmware)  one row per PIN on the bench (a header pin of a dev board or a PCB connector pin - never a passive breadboard hole):
      firmware      which firmware variable uses the pin and how (LED_PIN gpio.out in uno-light) - the pin's REQUIREMENT from code
      connections   the other PINS it reaches, and through what (via the half breadboard) - pin <-> pin, never the holes in between
      checks        the pin's INHERENT properties (logic level, source / sink limit, direction) against what its connections and firmware need:
                    over-voltage   a driver on its connections works above this pin's logic level (5 V into a 3.3 V pin)
                    contention     this pin is driven as an output by its firmware and something else on its connections drives too
                    short          two supplies at different voltages, or a supply and ground, are connected
                    floating       its firmware reads it but nothing on its connections drives it (a board's own pull is not a foothold fact yet: a NOTE)
                    load           the current its connections draw vs its limit - only when a board-level circuit defines that load; a plain wire draws
                                   none, and that is said
      status        ok | finding | note
  firmware_uses(boards)  {(board id, chip pin): [use]} from the CatomVariable rows of every firmware variant that targets the board's definition

  circuits     bob-2c: a BOARD-LEVEL circuit built on the bench (a BenchConnection of kind circuit naming an electrodevice CircuitDefinition bound to the
                board's pins by BoardPinNet) gives its pins a DEFINED connection with real drive behaviour: board.custom.electrical_check works it out (LED
                current against the pin's cited limit, one output per net, ground, level, pull, VOH under load ...) and each finding that names a pin lands
                on that pin's row - refuse = a finding, warn / undetermined = a note, ok = said in `defined`

The full bench netlist (board.custom.bench_nets) is its own view - a popup, not the main bench (his follow-up 2026-10-30).
"""
import re
from board.custom import bench_nets as BN

PIN_KINDS = ('header-pin', 'connector-pin', 'test-pad', 'pad')
DRIVES = ('uart.tx', 'gpio.out', 'pwm.out')
READS = ('uart.rx', 'gpio.in', 'int.ext', 'adc.in')


def is_pin(f):
    return f['kind'] in PIN_KINDS


def firmware_uses(boards, variables=None, running=None):
    """boards = {id: {'definition', ...}} → {(board id, chip pin): [{'variant', 'variable', 'role', 'used_by', 'running'}]}. `running` = {board id: the
    firmware it runs} (bob-2d): such a board shows only that firmware's variables; a board with none shows every variant for its definition, each
    marked 'if flashed'."""
    running = running or {}
    from cmod.custom import catom_variables as CV
    variables = variables if variables is not None else CV.SEED_VARIABLES
    out = {}
    for bid, b in boards.items():
        for v in variables:
            if v.get('board') != b.get('definition') or v.get('role') not in DRIVES + READS:
                continue
            if bid in running and v['variant'] != running[bid]:
                continue
            value = CV.effective(v)[0]
            chip = CV.resolve_pin(v.get('soc', ''), value) if value else ''
            if chip:
                out.setdefault((bid, chip), []).append({'variant': v['variant'], 'variable': v['variable'], 'role': v['role'], 'used_by': v.get('used_by', ''),
                                                        'running': bid in running})
    return out


def use_words(u):
    """One firmware use in words: 'uno-light BUTTON_PIN int.ext', or 'uno-light (if flashed) ...' when the board is not recorded as running it."""
    return '%s%s %s %s' % (u['variant'], '' if u.get('running') else ' (if flashed)', u['variable'], u['role'])


def _drives(m, fw):
    """Does this member DRIVE its connection? A supply does; a pin its firmware drives does; an 'out' foothold (a PCB pad behind which a part drives) does."""
    if m['direction'] == 'supply' and m['rail_volts'] > 0:
        return m['rail_volts']
    if m['direction'] == 'out' or any(u['role'] in DRIVES for u in fw.get((m['board'], m['chip_pin']), [])):
        return m['logic_volts'] if m['logic_volts'] > 0 else -1.0
    return None


def pin_rows(boards, wiring, firmware=None, tables=None):
    feet = {bid: b['footholds'] for bid, b in boards.items()}
    running = {c['from_board']: c.get('label', '') for c in wiring if c.get('kind') == 'firmware' and c.get('label')}
    fw = firmware if firmware is not None else firmware_uses(boards, running=running)
    nets, problems = BN.nets(feet, wiring)
    rows = []
    labels = {bid: b.get('label', bid) for bid, b in boards.items()}
    for n in nets:
        pins = [m for m in n['members'] if is_pin(m)]
        vias = sorted({labels[m['board']] for m in n['members'] if not is_pin(m)})
        # pins one board joins inside (a dev board's four GND pins) are ONE row on the bench: the minimum a person has to read
        groups = {}
        for m in pins:
            groups.setdefault((m['board'], m['node']), []).append(m)
        name = lambda g: '%s %s' % (labels[g[0]['board']], g[0]['label'] or g[0]['foothold']) + (' (%d pins)' % len(g) if len(g) > 1 else '')   # noqa: E731
        for key, group in groups.items():
            p = group[0]
            others = [m for k, g in groups.items() if k != key for m in g]
            if not others:
                continue
            uses = [u for m in group for u in fw.get((m['board'], m['chip_pin']), [])]
            checks, notes = [], []
            mine = _drives(p, fw)
            drivers = [(m, _drives(m, fw)) for m in others if _drives(m, fw) is not None]
            for m, v in drivers:
                if v and v > 0 and 0 < p['logic_volts'] < v and p['direction'] in ('in', 'inout'):
                    checks.append('over-voltage: %s %s drives %g V; this pin works at %g V' % (labels[m['board']], m['label'] or m['foothold'], v, p['logic_volts']))
                if mine is not None and p['direction'] != 'supply' and m['direction'] != 'supply':
                    checks.append('contention: this pin is driven by its firmware and %s %s drives too' % (labels[m['board']], m['label'] or m['foothold']))
                if p['direction'] == 'supply' and m['direction'] == 'supply' and p['rail_volts'] >= 0 and v is not None and v != p['rail_volts']:
                    checks.append('short: this %g V supply is connected to %s %s at %g V' % (p['rail_volts'], labels[m['board']], m['label'] or m['foothold'], v))
            if p['direction'] == 'supply' and p['rail_volts'] > 0 and any(m['direction'] == 'supply' and m['rail_volts'] == 0.0 for m in others):
                checks.append('short: this %g V supply is connected to ground' % p['rail_volts'])
            if any(u['role'] in READS for u in uses) and not drivers:
                notes.append('floating: its firmware reads it but nothing connected drives it (a pull inside a board is not a foothold fact yet)')
            if any(u['role'] in DRIVES for u in uses):
                notes.append('load: no board-level circuit defines what this pin drives - a plain wire draws no current; the %s mA limit is checked once one does'
                             % ('%g' % p['source_ma'] if p['source_ma'] > 0 else 'uncited'))
            other_groups = [g for k, g in groups.items() if k != key]
            rows.append({'board': p['board'], 'board_label': labels[p['board']], 'pin': name(group), 'footholds': ', '.join(m['foothold'] for m in group),
                         'chip_pin': p['chip_pin'], 'firmware': '; '.join(dict.fromkeys(use_words(u) for u in uses)),
                         'connections': '; '.join(name(g) for g in other_groups), 'via': ', '.join(vias), 'logic_volts': p['logic_volts'], 'source_ma': p['source_ma'],
                         'rail_volts': p['rail_volts'], 'checks': '; '.join(dict.fromkeys(checks)), 'notes': '; '.join(notes), 'defined': '',
                         'status': 'finding' if checks else 'ok'})
    _circuits(rows, boards, [c for c in wiring if c.get('kind') == 'circuit'], fw, tables, running)
    return sorted(rows, key=lambda r: (r['status'] != 'finding', r['board'], r['pin'])), problems


def _mentions(text, pin):
    return re.search(r'(^|[^A-Za-z0-9])%s([^A-Za-z0-9]|$)' % re.escape(pin), text or '') is not None


def _circuits(rows, boards, circuits, fw, tables, running=None):
    """Fold each board-level circuit's electrical findings into the pin rows of the pins it binds (adding a row for a pin nothing else connects)."""
    if not circuits:
        return
    from board.custom import electrical_check as EC
    tables = tables if tables is not None else EC.tables_for(None)
    soc_of = {(p['board'], p['canonical']): p['soc_pin'] for p in tables.get('BoardPin', [])}
    for c in circuits:
        bid, circuit = c['from_board'], c.get('label', '')
        b = boards.get(bid)
        if b is None:
            continue
        defn = b.get('definition', '')
        # bob-2d: with the firmware the board RUNS, the board-level rules read its real pin claims (uno-light's D2 pull-up set in hal_button_init)
        sol = (running or {}).get(bid, '')
        findings = EC.check(circuit, '%s@%s' % (sol, defn) if sol else defn, tables)
        bound = [r for r in tables.get('BoardPinNet', []) if r.get('circuit') == circuit and str(r.get('board_pin', '')).startswith(defn + ':')]
        for bp in bound:
            canon = bp['board_pin'].split(':', 1)[1]
            chip = soc_of.get((defn, canon), '')
            group = [f for f in b['footholds'] if f.get('chip_pin') == chip and chip]
            if not group:
                continue
            label = '%s %s' % (b.get('label', bid), group[0]['label'] or group[0]['foothold'])
            row = next((r for r in rows if r['board'] == bid and (r['pin'] == label or r['pin'].startswith(label + ' ('))), None)
            if row is None:
                uses = fw.get((bid, chip), [])
                row = {'board': bid, 'board_label': b.get('label', bid), 'pin': label, 'footholds': ', '.join(f['foothold'] for f in group), 'chip_pin': chip,
                       'firmware': '; '.join(dict.fromkeys(use_words(u) for u in uses)), 'connections': '', 'via': '',
                       'logic_volts': group[0]['logic_volts'], 'source_ma': group[0]['source_ma'], 'rail_volts': group[0]['rail_volts'], 'checks': '', 'notes': '',
                       'status': 'ok'}
                rows.append(row)
            mine = [f for f in findings if _mentions(f['subject'], canon) or _mentions(f['detail'], canon)]
            refuse = ['%s: %s' % (f['rule'], f['detail']) for f in mine if f['status'] == 'refuse']
            uses = fw.get((bid, chip), [])
            role = bp.get('role', '')
            for u in uses:   # the firmware's use against the circuit's role for the pin: code and wiring must agree on who drives
                if (role == 'output' and u['role'] in READS) or (role == 'input' and u['role'] in DRIVES):
                    refuse.append('role mismatch: %s %s uses it as %s but circuit %s wires it as an %s' % (u['variant'], u['variable'], u['role'], circuit, role))
            soft = ['%s (%s): %s' % (f['rule'], f['status'], f['detail']) for f in mine if f['status'] in ('warn', 'undetermined')]
            fine = sorted({f['rule'] for f in mine if f['status'] == 'ok'})
            row['defined'] = 'circuit %s (%s on net %s)%s' % (circuit, bp.get('role', ''), bp.get('circuit_net', ''), ('; ok: %s' % ', '.join(fine)) if fine else '')
            row['connections'] = '; '.join(x for x in (row['connections'], 'circuit %s' % circuit) if x)
            row['checks'] = '; '.join(x for x in [row['checks']] + refuse if x)
            # the generic 'no board-level circuit defines a load' note gives way to the circuit's own numbers
            notes = [n for n in row['notes'].split('; ') if n and not n.startswith('load: no board-level circuit')]
            row['notes'] = '; '.join(notes + soft)
            row['status'] = 'finding' if row['checks'] else 'ok'


def bench_pin_rows(bench_name, manager):
    """(rows, problems) | (None, why) - the pins of a stored bench (its Boards on the Bench + the stored wiring)."""
    feet, by_id = BN._boards(bench_name, manager)
    if feet is None:
        return None, 'no bench named %r' % bench_name
    boards = {bid: {'label': by_id[bid]['label'], 'footholds': f, 'definition': by_id[bid]['definition']} for bid, f in feet.items()}
    return pin_rows(boards, BN.connections_of(bench_name, manager))
