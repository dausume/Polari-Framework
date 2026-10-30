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

The full bench netlist (board.custom.bench_nets) is its own view - a popup, not the main bench (his follow-up 2026-10-30).
"""
from board.custom import bench_nets as BN

PIN_KINDS = ('header-pin', 'connector-pin', 'test-pad', 'pad')
DRIVES = ('uart.tx', 'gpio.out', 'pwm.out')
READS = ('uart.rx', 'gpio.in', 'int.ext', 'adc.in')


def is_pin(f):
    return f['kind'] in PIN_KINDS


def firmware_uses(boards, variables=None):
    """boards = {id: {'definition', ...}} → {(board id, chip pin): [{'variant', 'variable', 'role', 'used_by'}]}."""
    from cmod.custom import catom_variables as CV
    variables = variables if variables is not None else CV.SEED_VARIABLES
    out = {}
    for bid, b in boards.items():
        for v in variables:
            if v.get('board') != b.get('definition') or v.get('role') not in DRIVES + READS:
                continue
            value = CV.effective(v)[0]
            chip = CV.resolve_pin(v.get('soc', ''), value) if value else ''
            if chip:
                out.setdefault((bid, chip), []).append({'variant': v['variant'], 'variable': v['variable'], 'role': v['role'], 'used_by': v.get('used_by', '')})
    return out


def _drives(m, fw):
    """Does this member DRIVE its connection? A supply does; a pin its firmware drives does; an 'out' foothold (a PCB pad behind which a part drives) does."""
    if m['direction'] == 'supply' and m['rail_volts'] > 0:
        return m['rail_volts']
    if m['direction'] == 'out' or any(u['role'] in DRIVES for u in fw.get((m['board'], m['chip_pin']), [])):
        return m['logic_volts'] if m['logic_volts'] > 0 else -1.0
    return None


def pin_rows(boards, wiring, firmware=None):
    feet = {bid: b['footholds'] for bid, b in boards.items()}
    fw = firmware if firmware is not None else firmware_uses(boards)
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
                         'chip_pin': p['chip_pin'], 'firmware': '; '.join(dict.fromkeys('%s %s %s' % (u['variant'], u['variable'], u['role']) for u in uses)),
                         'connections': '; '.join(name(g) for g in other_groups), 'via': ', '.join(vias), 'logic_volts': p['logic_volts'], 'source_ma': p['source_ma'],
                         'rail_volts': p['rail_volts'], 'checks': '; '.join(dict.fromkeys(checks)), 'notes': '; '.join(notes), 'status': 'finding' if checks else 'ok'})
    return sorted(rows, key=lambda r: (r['status'] != 'finding', r['board'], r['pin'])), problems


def bench_pin_rows(bench_name, manager):
    """(rows, problems) | (None, why) - the pins of a stored bench (its Boards on the Bench + the stored wiring)."""
    feet, by_id = BN._boards(bench_name, manager)
    if feet is None:
        return None, 'no bench named %r' % bench_name
    boards = {bid: {'label': by_id[bid]['label'], 'footholds': f, 'definition': by_id[bid]['definition']} for bid, f in feet.items()}
    return pin_rows(boards, BN.connections_of(bench_name, manager))
