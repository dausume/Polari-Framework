"""
@module cmod.custom.isotope_step_rules

bss-1 (AI-Notes/plans/BENCH_SOLUTION_SIM_PLAN.md section 3): THE STEP EACH ISOTOPE ASKS FOR, derived or cited, never typed - one IsotopeStepRule per
IsotopeVariant. The route half of the variant's name ('read-button:gpio-poll' -> gpio-poll) says the kind; the number comes from:

  cycle           1 / clock_hz, the clock from the committed cycle record (the build's own -DF_CPU); worst = the route's ISR's longest run when measured
  loop-period     the main loop's poll pass, measured on the twin (cycle_records.loop_of: the gap whose measure names the poll point); worst = the worst gap
  bit-time        the UART's actual bit on the wire: UBRR0 16 with U2X0 1 at clock_hz -> clock_hz / (8 (16 + 1)) = 117 647 Bd (board.custom.timing_drift
                  TABLE_16MHZ, the shipped config; tmp-6: the 16U2 runs the same); worst = one byte (10 bits)
  adc-conversion  13 ADC clocks (ATmega328P datasheet, ADC "Prescaling and Conversion Timing": a normal conversion takes 13 ADC clock cycles) at a
                  prescaler that is a KNOB (128 here) until hal.c's ADPS bits are read -> cited + knob, said
  pwm-period / bus-transaction   knobs: not measured or configured here; step -1 and the words

  rule(variant, record='uno-light')     -> the rule dict (no rows touched)
  derive(manager, variants, record)     -> upsert the rows (a row with basis 'person' is kept as typed); -> the rows
  rule_for(manager, variant, record)    -> the stored row, derived on the spot when there is none
"""
from cmod.custom import config_rows as R

ROUTE_KIND = {'gpio-poll': 'loop-period', 'analog-read': 'loop-period',
              'pin-change-interrupt': 'cycle', 'ext-interrupt': 'cycle', 'analog-comparator': 'cycle', 'gpio-out': 'cycle', 'transistor-switch': 'cycle',
              'uart-rx-interrupt': 'bit-time', 'uart-tx': 'bit-time',
              'analog-threshold': 'adc-conversion', 'analog-sensor': 'adc-conversion',
              'pwm': 'pwm-period',
              'i2c-expander': 'bus-transaction', 'i2c-sensor': 'bus-transaction', 'spi-shift-register': 'bus-transaction', 'spi-sensor': 'bus-transaction',
              'one-wire': 'bus-transaction'}
ISR_OF_ROUTE = {'ext-interrupt': 'hal.INT0_vect', 'uart-rx-interrupt': 'hal.USART_RX_vect'}
UBRR0, U2X0 = 16, 1          # the shipped UART config (timing_drift.TABLE_16MHZ[(115200, 1)] = (16, +2.1 %))
ADC_CLOCKS = 13               # cited: ATmega328P datasheet, ADC, "Prescaling and Conversion Timing"
ADC_PRESCALER = 128           # KNOB until hal.c's ADPS bits are read
DEFAULT_RECORD = 'uno-light'


def _record(record):
    from board.custom import cycle_records as CR
    rec = CR.load(record) or {}
    return rec, CR


def rule(variant, record=DEFAULT_RECORD):
    route = variant.split(':')[-1]
    kind = ROUTE_KIND.get(route, 'knob')
    rec, CR = _record(record)
    hz = float(rec.get('clock_hz') or 0)
    out = {'name': variant, 'variant': variant, 'kind': kind, 'step_s': -1.0, 'worst_s': -1.0, 'basis': 'knob', 'source': '', 'notes': ''}
    if not hz and kind in ('cycle', 'loop-period', 'bit-time', 'adc-conversion'):
        out['notes'] = 'no committed cycle record %r: the clock is not known here' % record
        return out
    ref = CR.ref(rec) if rec else ''
    if kind == 'cycle':
        out.update(step_s=1.0 / hz, basis='cited', source='clock_hz %d from %s (the build\'s -DF_CPU)' % (hz, ref))
        isr = CR.isr_of(ISR_OF_ROUTE.get(route, ''), record) if route in ISR_OF_ROUTE else None
        if isr:
            out.update(worst_s=isr['max'] / hz, notes='%s runs at most %d cycles (%s)' % (ISR_OF_ROUTE[route], isr['max'], ref))
    elif kind == 'loop-period':
        lp = CR.loop_of(record)
        if lp:
            gap = next((g for g in lp.get('gaps', []) if 'poll' in str(g.get('measure', ''))), (lp.get('gaps') or [{}])[0])
            out.update(step_s=float(gap.get('max_cycles', 0)) / hz, worst_s=float(lp.get('worst_gap_cycles', 0)) / hz, basis='derived',
                       source='%s: poll pass %s..%s cycles over %s passes; worst gap %s cycles' % (ref, gap.get('min_cycles'), gap.get('max_cycles'), gap.get('n'),
                                                                                                lp.get('worst_gap_cycles')))
        else:
            out['notes'] = 'the cycle record has no main-loop measurement'
    elif kind == 'bit-time':
        baud = hz / (8.0 * (UBRR0 + 1)) if U2X0 else hz / (16.0 * (UBRR0 + 1))
        out.update(step_s=1.0 / baud, worst_s=10.0 / baud, basis='derived',
                   source='UBRR0 %d, U2X0 %d at %d Hz -> %.0f Bd (board.custom.timing_drift TABLE_16MHZ, the shipped config); a byte is 10 bits' % (UBRR0, U2X0, hz, baud))
    elif kind == 'adc-conversion':
        out.update(step_s=ADC_CLOCKS * ADC_PRESCALER / hz, basis='cited', source='ATmega328P datasheet, ADC "Prescaling and Conversion Timing": %d ADC clocks; '
                   'prescaler %d is a KNOB until hal.c\'s ADPS bits are read' % (ADC_CLOCKS, ADC_PRESCALER))
    elif kind == 'pwm-period':
        out['notes'] = 'the PWM period is not measured or configured here: a knob'
    elif kind == 'bus-transaction':
        out['notes'] = 'the bus clock is not configured here: a knob'
    else:
        out['notes'] = 'route %r has no step rule yet: a knob' % route
    return out


def derive(manager, variants, record=DEFAULT_RECORD):
    rows = []
    for v in variants:
        have = R.get(manager, 'IsotopeStepRule', v)
        if have and have.get('basis') == 'person':
            rows.append(have)
            continue
        r = rule(v, record)
        rows.append(R.upsert(manager, 'IsotopeStepRule', v, **{k: x for k, x in r.items() if k != 'name'}))
    return rows


def rule_for(manager, variant, record=DEFAULT_RECORD):
    have = R.get(manager, 'IsotopeStepRule', variant)
    if have:
        return have
    return derive(manager, [variant], record)[0] if getattr(manager, 'objectTables', None) is not None else rule(variant, record)
