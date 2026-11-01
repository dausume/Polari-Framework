"""
@module board.custom.timing_drift

tmp-4 (AI-Notes/plans/TEMPERATURE_PLAN.md): TIMING AT A TEMPERATURE - how far a board's clocks and its logic's delays can move from nominal, as
their datasheets bound them, and what that does to a UART link. Every number is cited below; where a datasheet gives a BOUND over a range (a
resonator's +-0.3 % over -20 .. +80 C) the bound is used as a bound - its worst case anywhere in the range, and 'unrated' outside it - never
drawn as a curve the document does not give.

  clock_band(clock, temp_c) -> {inside, low_pct, high_pct, words}       the clock's worst-case error at temp_c (initial + temperature + aging)
  ubrr(f_osc, baud, u2x) -> (ubrr, error_pct)                          the ATmega328P's own equations (Table 20-1): UBRR = f / (16 baud) - 1
                                                                       (U2X: 8), rounded; error = the rate it gives / the rate asked - 1
  uart_rows(temps, bauds, clock, far_end_pct)                          each baud x U2X x temperature: divisor error + the clock's band against
                                                                       the receiver's window (its Max Total Error) and its recommended share
  delay_rows(part, temps)                                              a logic part's maximum propagation delay at each temperature: the
                                                                       narrowest datasheet column containing it
  timing(kind, definition, which, params) -> (rows, why)               the Board Details parts (timing-clocks, timing-uart, logic-delays;
                                                                       timing-run, timing-run-corners from tmp-6)

tmp-6 forces these bands into a firmware run (board.custom.clock_skew_run: the twin at the skewed rate, every UART byte re-sampled bit by
bit at each side's rate); the parts timing-run / timing-run-corners are that run's rows.

Sources (read 2026-11-01):
  ATmega328P   Microchip DS40002061B (2020): Table 20-1 (baud equations), §20.8.3 Tables 20-2 / 20-3 p. 194 (receiver error, D = data + parity
               bits: 8N1 is D = 8), Table 20-7 p. 199 (16 MHz examples: 9600 UBRR 103 / 207 0.2 %; 115.2k UBRR 8 -3.5 %, UBRR 16 +2.1 %), Table
               29-9 p. 313 (calibrated RC: factory 8.0 MHz +-10 % at 3 V, 25 C; user calibration +-1 % over 1.8 - 5.5 V, -40 .. 85 C)
  CSTCE16M0V53-R0  Murata product page (pim.murata.com, part CSTCE16M0V53-R0) and its Product Search Data Sheet (02/15/2024, p. 2): initial
               +-0.5 % max, +-0.3 % max over -20 .. +80 C, aging +-0.2 % max - the UNO R3's ATmega328P clock (board.custom.uno_schematic_paths:
               ZU4 pins 9 / 10 -> CSTCE16M0V53-R0)
  SN74LVC245A  TI SCAS218X (Jan 2015) §7.6 p. 6, VCC 3.3 V +-0.3 V, CL 50 pF / RL 500 ohm: t_pd A<->B max 6.1 ns at 25 C, 6.3 ns over -40 .. 85 C,
               7.3 ns over -40 .. 125 C (min 1.5 ns throughout)
  SN74AHCT125  TI SCLS264R (Feb 2024) §5.5 p. 6, VCC 5 V +-0.5 V: t_pd A->Y max 5.5 ns at 25 C and 6.5 ns over -40 .. 85 C at CL 15 pF; 7.5 / 8.5 ns
               at CL 50 pF (min 1 ns over the range); no -40 .. 125 C column for the SN74
"""
DS328 = 'Microchip ATmega48A/PA/88A/PA/168A/PA/328/P datasheet DS40002061B (2020)'
CLOCKS = {
    'cstce16m0v53-r0': {'f_hz': 16e6, 'initial_pct': 0.5, 'temp_pct': 0.3, 't_min_c': -20.0, 't_max_c': 80.0, 'aging_pct': 0.2,
                        'what': 'Murata CSTCE16M0V53-R0 16 MHz ceramic resonator (the UNO R3\'s ATmega328P clock)',
                        'source': 'Murata product page + Product Search Data Sheet (02/15/2024) p. 2: +-0.5 % initial, +-0.3 % over -20 .. +80 C, '
                                  '+-0.2 % aging (all max)'},
    'atmega328p-rc-user': {'f_hz': 8e6, 'initial_pct': 0.0, 'temp_pct': 1.0, 't_min_c': -40.0, 't_max_c': 85.0, 'aging_pct': 0.0,
                           'what': 'the ATmega328P\'s calibrated RC oscillator after a user calibration (8 MHz)',
                           'source': '%s Table 29-9 p. 313: user calibration +-1 %% over 1.8 - 5.5 V, -40 .. 85 C' % DS328},
    'atmega328p-rc-factory': {'f_hz': 8e6, 'initial_pct': 10.0, 'temp_pct': 0.0, 't_min_c': 25.0, 't_max_c': 25.0, 'aging_pct': 0.0,
                              'what': 'the ATmega328P\'s RC oscillator as the factory calibrated it (8 MHz)',
                              'source': '%s Table 29-9 p. 313: factory calibration +-10 %% at 3 V, 25 C only' % DS328},
}
#: DS40002061B Tables 20-2 (U2X 0) / 20-3 (U2X 1), D = 8 (8N1): the Max Total Error column (low %, high %) and the recommended maximum receiver
#: error +-%. The window is the Max Total Error column, not 100 - Rslow: in the U2X 0, D = 8 row the two disagree (Rslow 95.36 % implies -4.64 %,
#: the row prints -4.54 %; every other row agrees with its Rslow) - the tighter -4.54 % is used, and said
RECEIVER = {0: (-4.54, 4.58, 2.0, 'Rslow 95.36 % / Rfast 104.58 % (Rslow implies -4.64 %: the tighter -4.54 % of the row\'s Max Total Error is used)'),
            1: (-4.00, 3.90, 1.5, 'Rslow 96.00 % / Rfast 103.90 %')}
#: DS40002061B Table 20-7, f_osc 16 MHz: (baud, u2x) -> (UBRR, error %) - the check on ubrr()
TABLE_16MHZ = {(9600, 0): (103, 0.2), (9600, 1): (207, 0.2), (115200, 0): (8, -3.5), (115200, 1): (16, 2.1)}
DELAYS = {
    'sn74lvc245a-n': {'what': 'SN74LVC245A t_pd A<->B, VCC 3.3 V +-0.3 V, CL 50 pF, RL 500 ohm', 'min_ns': 1.5,
                      'columns': [(25.0, 25.0, 6.1), (-40.0, 85.0, 6.3), (-40.0, 125.0, 7.3)], 'source': 'TI SCAS218X (Jan 2015) section 7.6, p. 6'},
    'sn74ahct125-n': {'what': 'SN74AHCT125 t_pd A->Y, VCC 5 V +-0.5 V, CL 15 pF', 'min_ns': 1.0,
                      'columns': [(25.0, 25.0, 5.5), (-40.0, 85.0, 6.5)], 'source': 'TI SCLS264R (Feb 2024) section 5.5, p. 6 (CL 50 pF: 7.5 / 8.5 ns)'},
}
TEMPS = (-40.0, -20.0, 25.0, 80.0, 85.0, 125.0)
BAUDS = (9600, 115200)
UNO = 'arduino-uno-r3'
PARTS = ('timing-clocks', 'timing-uart', 'logic-delays', 'timing-run', 'timing-run-corners')


def clock_band(clock, temp_c):
    c = CLOCKS[clock]
    if not c['t_min_c'] <= temp_c <= c['t_max_c']:
        return {'inside': False, 'low_pct': 0.0, 'high_pct': 0.0,
                'words': 'unrated: the datasheet bounds it only over %g .. %g C' % (c['t_min_c'], c['t_max_c'])}
    b = c['initial_pct'] + c['temp_pct'] + c['aging_pct']
    return {'inside': True, 'low_pct': -b, 'high_pct': b,
            'words': 'worst case +-%g %% = initial %g + temperature %g + aging %g (bounds, added: none is a curve)' % (b, c['initial_pct'], c['temp_pct'],
                                                                                                               c['aging_pct'])}


def ubrr(f_osc, baud, u2x):
    div = 8.0 if u2x else 16.0
    n = max(0, int(round(f_osc / (div * baud) - 1)))
    return n, (f_osc / (div * (n + 1)) / baud - 1.0) * 100.0


def uart_rows(temps=TEMPS, bauds=BAUDS, clock='cstce16m0v53-r0', far_end_pct=0.0):
    c = CLOCKS[clock]
    out = []
    for baud in bauds:
        for u2x in (0, 1):
            n, err = ubrr(c['f_hz'], baud, u2x)
            lo_w, hi_w, rec, rwords = RECEIVER[u2x]
            for t in temps:
                band = clock_band(clock, t)
                row = {'clock': clock, 'baud': baud, 'u2x': u2x, 'ubrr': n, 'divisor_error_pct': err, 'temp_c': t, 'clock_low_pct': band['low_pct'],
                       'clock_high_pct': band['high_pct'], 'far_end_pct': far_end_pct, 'worst_low_pct': -1.0, 'worst_high_pct': -1.0,
                       'window_pct': '%+.2f .. %+.2f' % (lo_w, hi_w), 'recommended_pct': rec, 'verdict': '', 'basis': ''}
                if not band['inside']:
                    row.update(verdict='unrated', basis='the clock is %s' % band['words'])
                else:
                    lo, hi = err + band['low_pct'] - far_end_pct, err + band['high_pct'] - far_end_pct
                    row.update(worst_low_pct=lo, worst_high_pct=hi)
                    if lo_w <= lo and hi <= hi_w:
                        row['verdict'] = 'fits the recommended share' if max(abs(lo), abs(hi)) <= rec else \
                            'inside the receiver\'s window but beyond its recommended +-%g %% share' % rec
                    else:
                        row['verdict'] = 'OUTSIDE the receiver\'s window: framing errors'
                    row['basis'] = ('divisor %+.2f %% (UBRR %d, Table 20-1\'s equations) + the clock %s - the far end %+g %% (a knob: 0 = an exact '
                                    'clock); against the receiver\'s Max Total Error %+g .. %+g %% (D = 8, U2X %d, Tables 20-2 / 20-3: %s)'
                                    % (err, n, band['words'], far_end_pct, lo_w, hi_w, u2x, rwords))
                out.append(row)
    return out


def delay_rows(part, temps=TEMPS):
    d = DELAYS[part]
    out = []
    for t in temps:
        col = next(((lo, hi, mx) for lo, hi, mx in d['columns'] if lo <= t <= hi), None)
        out.append({'part': part, 'temp_c': t, 'min_ns': d['min_ns'] if col else -1.0, 'max_ns': col[2] if col else -1.0,
                    'column': ('%g C' % col[0]) if col and col[0] == col[1] else ('%g .. %g C' % (col[0], col[1])) if col else 'none',
                    'what': d['what'], 'basis': ('the narrowest datasheet column containing %g C' % t) if col else
                    'unrated: no datasheet column reaches %g C' % t, 'source': d['source']})
    return out


def _temps(params):
    raw = (params or {}).get('temps')
    if not raw:
        return list(TEMPS), ''
    try:
        temps = [float(x) for x in str(raw).split(',') if x.strip()]
    except ValueError:
        return [], 'temps must be numbers of C separated by commas, got %r' % raw
    if not temps or len(temps) > 12 or any(not -200 <= t <= 400 for t in temps):
        return [], 'give 1 .. 12 temperatures within -200 .. 400 C'
    return temps, ''


def timing(kind, definition, which, params=None):
    if which in ('timing-run', 'timing-run-corners'):   # tmp-6: the band forced into a firmware run
        from board.custom import clock_skew_run as CSR
        return CSR.rows(definition, which)
    temps, why = _temps(params)
    if why:
        return [], why
    if which == 'logic-delays':
        return (delay_rows(definition, temps), '') if definition in DELAYS else \
            ([], 'no cited propagation delay for %s yet (%s have one)' % (definition, ', '.join(DELAYS)))
    if definition != UNO:
        return [], 'no cited clock for %s yet - the UNO R3 (its ATmega328P and resonator) has one' % definition
    if which == 'timing-clocks':
        rows = []
        for clock, c in CLOCKS.items():
            for t in temps:
                b = clock_band(clock, t)
                rows.append({'clock': clock, 'what': c['what'], 'f_mhz': c['f_hz'] / 1e6, 'temp_c': t, 'low_pct': b['low_pct'],
                             'high_pct': b['high_pct'], 'inside': 'yes' if b['inside'] else 'no', 'basis': b['words'], 'source': c['source']})
        return rows, ''
    try:
        far = float((params or {}).get('far_end_pct') or 0.0)
    except ValueError:
        return [], 'far_end_pct needs a number'
    clock = (params or {}).get('clock') or 'cstce16m0v53-r0'
    if clock not in CLOCKS:
        return [], 'no clock %r - %s' % (clock, ', '.join(CLOCKS))
    return uart_rows(temps, BAUDS, clock, far), ''
