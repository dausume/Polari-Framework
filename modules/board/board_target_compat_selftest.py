"""board_target_compat_selftest — fs-2a (his ruling 2026-10-06): the compatibility table between a firmware task's
target kind and a board's pin roles/capabilities (board.custom.target_compat), checked against the UNO's real pins:
ADC valid targets are exactly A0-A5, PWM exactly the six timer pins, UART rx/tx exactly D0/D1, power/ground pins are
NEVER valid for any kind, and at least one named undetermined case (a PCINT-only pin asked for interrupt-in).

    PYTHONPATH=.:modules python3 -m board.board_target_compat_selftest
"""


def run_target_compat(check):
    from board.custom import board_object as BO
    from board.custom import target_compat as TC
    tables = BO.seed_tables()
    r = BO.rows_for('arduino-uno-r3', tables)

    rows = TC.rows()
    check('TargetCompatibilityRule rows: one per TASK_KINDS entry', len(rows) == len(TC.TASK_KINDS), len(rows))
    check('every compatibility row cites a source (source_url) except where the kind draws on more than one role '
          '(none do today — every row has one)', all(row['source_url'].startswith('http') for row in rows),
          [row['kind'] for row in rows if not row['source_url'].startswith('http')])
    check('the power/ground rows are described as never-assignable', all(
          '(never' in row['matches'] for row in rows if row['kind'] in ('power', 'ground')), rows)

    def valid_pins(kind):
        vt = TC.valid_targets(kind, r)
        return sorted(v['pin'] for v in vt if v['verdict'] == 'ok')

    check('ADC task valid targets == A0-A5 exactly', valid_pins('analog-in') == ['A0', 'A1', 'A2', 'A3', 'A4', 'A5'], valid_pins('analog-in'))
    check('PWM task valid targets == the six timer pins D3 D5 D6 D9 D10 D11 exactly',
          valid_pins('pwm-out') == ['D10', 'D11', 'D3', 'D5', 'D6', 'D9'], valid_pins('pwm-out'))
    check('UART rx valid targets == D0 exactly', valid_pins('uart-rx') == ['D0'], valid_pins('uart-rx'))
    check('UART tx valid targets == D1 exactly', valid_pins('uart-tx') == ['D1'], valid_pins('uart-tx'))
    check('I2C SDA valid targets == A4 exactly', valid_pins('i2c-sda') == ['A4'], valid_pins('i2c-sda'))
    check('I2C SCL valid targets == A5 exactly', valid_pins('i2c-scl') == ['A5'], valid_pins('i2c-scl'))

    universe = TC.board_target_universe(r)
    power_ground = [p['canonical'] for p in universe if p['function'] in ('power', 'ground')]
    check('the board target universe includes the power/ground connector-only pins (NC/IOREF/+3V3/+5V/GND/VIN/AREF — '
          'RESET is a control signal, not classified power/ground by pin_roles/pinmap_svg)',
          {'GND', 'VIN', '+5V', '+3V3', 'IOREF', 'AREF'} <= set(power_ground), power_ground)
    for kind in TC.TASK_KINDS:
        if kind in TC.NEVER_ASSIGNABLE:
            continue
        verdicts = {v['pin']: v['verdict'] for v in TC.valid_targets(kind, r) if v['pin'] in power_ground}
        if not all(v == 'no' for v in verdicts.values()):
            check('power/ground pins are NEVER a valid target (kind=%s)' % kind, False, verdicts)
            break
    else:
        check('power/ground pins are NEVER a valid target, for every task kind', True)

    # a NAMED undetermined case: D4 (PD4) has PCINT20 but no INT0/INT1 — a pin-change-only pin
    d4 = next(p for p in r['pins'] if p['canonical'] == 'D4')
    soc_by_pin = {s['pin']: s for s in r['soc_pins']}
    verdict, reason = TC.compatible('interrupt-in', d4, soc_by_pin.get(d4['soc_pin']))
    check('an undetermined case, named: interrupt-in on D4 (PCINT20, no dedicated INT0/INT1) is undetermined, not refused',
          verdict == 'undetermined' and 'PCINT' in reason, reason)
    d2 = next(p for p in r['pins'] if p['canonical'] == 'D2')
    verdict2, reason2 = TC.compatible('interrupt-in', d2, soc_by_pin.get(d2['soc_pin']))
    check('interrupt-in on D2 (INT0) is a clean ok (the dedicated external interrupt, not just PCINT)',
          verdict2 == 'ok' and 'INT0' in reason2, reason2)

    # a true invalid case (his example): PWM onto D13 (SCK, no Output Compare function)
    d13 = next(p for p in r['pins'] if p['canonical'] == 'D13')
    verdict3, reason3 = TC.compatible('pwm-out', d13, soc_by_pin.get(d13['soc_pin']))
    check('PWM onto D13 is refused (no Output Compare function) — the true invalid case his ruling asked for',
          verdict3 == 'no', reason3)
    # and digital-out onto an analog pin IS valid (confirms A0 is the wrong invalid-case pick, D13/PWM is the right one)
    a0 = next(p for p in r['pins'] if p['canonical'] == 'A0')
    verdict4, reason4 = TC.compatible('digital-out', a0, soc_by_pin.get(a0['soc_pin']))
    check('digital-out onto A0 (an analog pin) IS valid (every I/O pin is GPIO-capable)', verdict4 == 'ok', reason4)

    # every cited reason names a DatasheetFact (derive-or-cite) when the pin has a soc register fact
    for kind, pin_name in (('analog-in', 'A0'), ('pwm-out', 'D6'), ('uart-rx', 'D0'), ('uart-tx', 'D1')):
        p = next(x for x in r['pins'] if x['canonical'] == pin_name)
        v, why = TC.compatible(kind, p, soc_by_pin.get(p['soc_pin']))
        check('compatible(%s, %s) cites a datasheet fact' % (kind, pin_name), v == 'ok' and 'datasheet fact' in why, why)
