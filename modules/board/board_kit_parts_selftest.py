"""board_kit_parts_selftest — fs-2d (his ask: "the power pins have no definitions at all" + his follow-up: "these
are all the parts in our kit, we will be wanting to use these as reference for how we make our sample firmwares"):
the power/reference pin-detail vocabulary (board.custom.power_pins), the kit parts register (board.custom.kit_parts)
and the resolved target-compatibility pairs this session's reading of the kit book + the UNO docs settled.

    PYTHONPATH=.:modules python3 -m board.board_kit_parts_selftest
"""


def run_kit_parts(check):
    from board.custom import board_object as BO
    from board.custom import power_pins as PP
    from board.custom import kit_parts as KP
    from board.custom import target_compat as TC
    tables = BO.seed_tables()
    r = BO.rows_for('arduino-uno-r3', tables)

    # ---------------------------------------------------------------- deliverable 1: power/reference pin detail
    for label in ('+5V', '5V', 'AREF', 'GND', 'VIN', 'IOREF', 'RESET', '+3V3'):
        parts = KP.parts_for_pin(label, r)
        d = PP.detail_for(label, r, parts_that_connect_here=parts)
        check('power/reference pin %r resolves (no longer a 404)' % label, d is not None, d)
        check('power/reference pin %r has a non-empty, cited purpose' % label, bool(d and d['purpose'] and d['sources']), d)
        check('power/reference pin %r carries electrical + typical_uses' % label,
              bool(d and d['electrical'] and d['typical_uses']), d)
        check('power/reference pin %r is never assignable, with a reason' % label,
              d is not None and d['assignable'] is False and bool(d['assignable_reason']), d)
    check('an ordinary signal pin (D6) is NOT a power/reference label', not PP.is_power_reference_label('D6'))
    check('GND resolves to 4 physical locations on the UNO (POWER header x2 + DIGITAL_H x1 + ICSP x1)',
          len(PP.locations_for('GND', r)) == 4, PP.locations_for('GND', r))
    check('5V and 3.3V aliases resolve to the same canonical label board_uno.py uses',
          PP.label_for('5V') == '+5V' and PP.label_for('3.3V') == '+3V3')

    # ---------------------------------------------------------------- deliverable 3 (+ his follow-up): the kit parts register
    rows = KP.rows()
    check('the kit parts register has at least 20 rows', len(rows) >= 20, len(rows))
    check('every kit part cites a source', all(row['source'] for row in rows), [row['name'] for row in rows if not row['source']])
    check('every kit part names its kit (arduino-starter-kit)', all(row['kit'] == KP.KIT for row in rows))
    check('every kit part names what it is (one sentence)', all(row['what_it_is'] for row in rows))
    tmp36 = KP.by_name('arduino-starter-kit:tmp36')
    led = KP.by_name('arduino-starter-kit:led')
    check('the TMP36 kit part exists with an analog-in interface', tmp36 is not None and tmp36['interface_kind'] == 'analog-in', tmp36)
    check('the TMP36 kit part is linked to the temp-sensor-to-os sample capability',
          tmp36 is not None and 'temp-sensor-to-os' in tmp36['sample_capabilities'].split(','), tmp36)
    check('the LED kit part is linked to the blink-on-command sample capability',
          led is not None and 'blink-on-command' in led['sample_capabilities'].split(','), led)
    backlog = KP.parts_without_sample()
    check('most kit parts have no sample yet — the backlog (only the TMP36 and the LED do)',
          len(backlog) == len(rows) - 2, backlog)
    check('the TMP36 and LED are NOT in the backlog (they already have a sample)',
          'arduino-starter-kit:tmp36' not in backlog and 'arduino-starter-kit:led' not in backlog, backlog)
    check('the DC motor needs a driver (never wired straight to a pin)',
          KP.by_name('arduino-starter-kit:dc-motor')['driver_needed'] != '')

    names_5v = {p['name'] for p in KP.parts_for_pin('5V', r)}
    check('parts_that_connect_here for 5V includes the TMP36 and the potentiometer',
          {'arduino-starter-kit:tmp36', 'arduino-starter-kit:potentiometer'} <= names_5v, names_5v)
    names_gnd = {p['name'] for p in KP.parts_for_pin('GND', r)}
    check('parts_that_connect_here for GND includes the TMP36, the LED (its cathode) and the battery snap',
          {'arduino-starter-kit:tmp36', 'arduino-starter-kit:led', 'arduino-starter-kit:battery-snap'} <= names_gnd, names_gnd)

    # ---------------------------------------------------------------- deliverable 2: the resolved compatibility pairs
    def valid_pins(kind):
        return sorted(v['pin'] for v in TC.valid_targets(kind, r) if v['verdict'] == 'ok')

    check('interrupt-in task valid targets == exactly D2/D3 (INT0/INT1, ATmega328P) — a PCINT-only pin stays '
          'undetermined (named below), never silently "ok"', valid_pins('interrupt-in') == ['D2', 'D3'], valid_pins('interrupt-in'))
    check('i2c-sda resolves to exactly A4 (SDA), i2c-scl to exactly A5 (SCL) — UNO docs',
          valid_pins('i2c-sda') == ['A4'] and valid_pins('i2c-scl') == ['A5'])
    check('spi resolves to exactly the D10-D13 header pins (SS=D10, MOSI=D11, MISO=D12, SCK=D13)',
          valid_pins('spi-ss') == ['D10'] and valid_pins('spi-mosi') == ['D11']
          and valid_pins('spi-miso') == ['D12'] and valid_pins('spi-sck') == ['D13'])
    check('digital-in/out resolve on A0-A5 too (UNO docs: the analog pins also act as digital pins)',
          {'A0', 'A1', 'A2', 'A3', 'A4', 'A5'} <= set(valid_pins('digital-in'))
          and {'A0', 'A1', 'A2', 'A3', 'A4', 'A5'} <= set(valid_pins('digital-out')))
    check('analog-in resolves to exactly A0-A5 (never a digital-only pin)',
          valid_pins('analog-in') == ['A0', 'A1', 'A2', 'A3', 'A4', 'A5'])
    check('pwm-out resolves to exactly the six ~ pins D3 D5 D6 D9 D10 D11 (kit book + UNO docs)',
          valid_pins('pwm-out') == ['D10', 'D11', 'D3', 'D5', 'D6', 'D9'])

    # the one pair that REMAINS undetermined, named with the missing fact (derive-or-cite: never silently resolved)
    soc_by_pin = {s['pin']: s for s in r['soc_pins']}
    d4 = next(p for p in r['pins'] if p['canonical'] == 'D4')
    verdict, reason = TC.compatible('interrupt-in', d4, soc_by_pin.get(d4['soc_pin']))
    check('interrupt-in on a PCINT-only pin (D4) is undetermined, naming the missing fact (the datasheet\'s Pin '
          'Change Interrupt chapter/page was not reconfirmed this session) rather than guessed to "ok"',
          verdict == 'undetermined' and 'PCINT' in reason and 'reconfirmed' in TC.INT_DOC_NOTE, reason)

    # power/ground pins never valid for ANY task kind, re-confirmed with the kit-parts-aware universe
    universe = TC.board_target_universe(r)
    power_ground = [p['canonical'] for p in universe if p['function'] in ('power', 'ground')]
    for kind in TC.TASK_KINDS:
        if kind in TC.NEVER_ASSIGNABLE:
            continue
        verdicts = {v['pin']: v['verdict'] for v in TC.valid_targets(kind, r) if v['pin'] in power_ground}
        if not all(v == 'no' for v in verdicts.values()):
            check('power/ground pins are never a valid target (kind=%s, fs-2d re-confirmed)' % kind, False, verdicts)
            break
    else:
        check('power/ground pins are never a valid target, for every task kind (fs-2d re-confirmed)', True)
