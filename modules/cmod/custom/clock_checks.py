"""
@module cmod.custom.clock_checks

cfg-1 (AI-Notes/plans/CATOM_CONFIG_PLAN.md "The clock group in detail", part 1): THE CLOCK GROUP'S CHECKS, registered on the cfg-0 registry
(config_checks) at import - closed forms only (layer 1), every number from a cited row or the chip's own equations:

  serial-link   a values option that sets `usart_u2x` (and `baud`, default 115200): the chip's divisor and error (timing_drift.ubrr, Table 20-1), the far
                end's divisor and clock (the Bench Solution's board's ClockPeer: arduino-usbserial's SERIAL_2X_UBBRVAL, or exact), the band of chip clock
                error inside which BOTH directions decode at every sampling phase (board.custom.clock_skew_run.limits, from uart_sampling's model), and the
                chip's own clock band at the Bench Solution's ambient range (ClockSource bounds, timing_drift.clock_band). invalid: the nominal clock (0 %)
                or the clock band falls outside the decode band; compromise: inside, but the divisor error is beyond the receiver's recommended share
                (Tables 20-2 / 20-3) or the margin left is under the share; ideal: inside with the recommended share to spare. margin = the smaller margin
                (%) between the clock band and the decode band.
  tick          the 1 ms tick as hal.c sets it (Timer2 CTC, clk/128, OCR2A 124: 16 MHz / 128 / 125 = 1000 Hz exactly) at the option's F_CPU (16 MHz on
                every UNO variant): ideal when the divisor is exact and the clock band is inside +-1 % (the tick then drifts only as the clock does),
                compromise when the divisor itself is off, invalid when the tick cannot be made at all (a knob set the prescaler out of range).

  context(manager, bench_solution)  -> the clock context the checks read: {board, clock (ClockSource name), peer (ClockPeer dict), ambient (lo, hi)};
                                       what is missing is said in `words` and the check then says 'unrated' as compromise, never a guess
"""
from cmod.custom import config_checks as CC
from cmod.custom import config_rows as R

F_CPU_HZ = 16000000.0      # every UNO variant's F_CPU (board_config.h); an option may set `f_cpu_hz`
TICK = {'prescaler': 128, 'ocr': 124, 'source': 'hal.c hal_tick_init: TCCR2B = CS22 | CS20 (clk/128), OCR2A = 124 (CTC): f / 128 / 125'}
DEFAULT_BAUD = 115200
DS = 'Microchip DS40002061B'


def _board_of(manager, firmware_solution):
    fs = R.get(manager, 'FirmwareSolution', firmware_solution) if getattr(manager, 'objectTables', None) is not None else None
    if fs and fs.get('board_definition'):
        return fs['board_definition']
    try:   # a variant name standing in for a Firmware Solution row (bss-8): the variants file is the UNO's
        from board.custom import variants as V
        V.find(firmware_solution)
        return 'arduino-uno-r3'
    except Exception:  # noqa: BLE001
        return ''


def _rows(manager, cls):
    return R.rows(manager, cls) if getattr(manager, 'objectTables', None) is not None else []


def context(manager, bench_solution):
    from board.custom import timing_drift as TD
    bs = R.get(manager, 'BenchSolution', bench_solution) or {}
    cond = R.get(manager, 'BenchConditions', bs.get('conditions', '')) or {}
    board = _board_of(manager, bs.get('firmware_solution', ''))
    words = []
    clock = next((r['name'] for r in _rows(manager, 'ClockSource') if board and board in [b.strip() for b in r.get('boards', '').split(',')]), '')
    if not clock:
        clock = next((n for n, c in TD.CLOCKS.items() if n == 'cstce16m0v53-r0' and board == 'arduino-uno-r3'), '')
        if clock:
            words.append('the clock source comes from timing_drift.CLOCKS (no ClockSource row on this server yet)')
    if not clock:
        words.append('no ClockSource names the board %r: the clock band is unknown' % board)
    peer = next((r for r in _rows(manager, 'ClockPeer') if board and board in [b.strip() for b in r.get('boards', '').split(',')]), None)
    if peer is None:
        if board == 'arduino-uno-r3':
            peer = {'name': 'uno-16u2-usbserial', 'kind': 'usb-serial-chip', 'divisor_rule': 'arduino-usbserial', 'error_pct': 0.0, 'f_hz': 16e6, 'undetermined': ''}
            words.append('the peer comes from clock_skew_run (no ClockPeer row on this server yet)')
        else:
            words.append('no ClockPeer names the board %r: the far end is unknown' % board)
    amb = (float(cond.get('ambient_min_c', 25.0)), float(cond.get('ambient_max_c', 25.0))) if cond else (25.0, 25.0)
    if not cond:
        words.append('no BenchConditions: 25 C assumed, said')
    return {'board': board, 'clock': clock, 'peer': peer, 'ambient': amb, 'words': words}


def _band(clock, ambient, manager):
    """The clock's worst band over the ambient range: the wider of the two ends (a bound is flat inside its range), or None + why when unrated."""
    from board.custom import timing_drift as TD
    bands = [TD.clock_band(clock, t, manager) for t in ambient]
    if any(not b['inside'] for b in bands):
        return None, '; '.join(b['words'] for b in bands if not b['inside'])
    lo, hi = min(b['low_pct'] for b in bands), max(b['high_pct'] for b in bands)
    return (lo, hi), bands[0]['words']


def serial_link(option, ctx):
    vals = option.get('values') or {}
    if 'usart_u2x' not in vals:
        return None
    from board.custom import clock_skew_run as CS
    from board.custom import timing_drift as TD
    manager = ctx.get('manager')
    cc = ctx.get('clock_context') or context(manager, ctx['bench_solution'])
    u2x, baud = int(vals['usart_u2x']), int(vals.get('baud', DEFAULT_BAUD))
    f = float(vals.get('f_cpu_hz', F_CPU_HZ))
    ubrr, err = TD.ubrr(f, baud, u2x)
    lo_w, hi_w, rec, rwords = TD.RECEIVER[u2x]
    if not cc['clock'] or cc['peer'] is None:
        return {'outcome': 'compromise', 'margin': 0.0, 'why': 'unrated: %s' % '; '.join(cc['words']), 'evidence': 'UBRR %d, divisor %+.2f %% (%s Table 20-1)' % (ubrr, err, DS)}
    peer = cc['peer']
    if peer.get('divisor_rule') == 'exact':
        lim = {'lo_pct': lo_w - err, 'hi_pct': hi_w - err, 'words': 'an exact peer at %d Bd: the chip\'s divisor error %+.2f %% against its own receiver window %+g .. %+g %%' % (baud, err, lo_w, hi_w)}
    else:
        lim = CS.limits(u2x, ubrr, float(peer.get('error_pct') or 0.0), baud)
    band, bwords = _band(cc['clock'], cc['ambient'], manager)
    evidence = '%s; the decode band %+.2f .. %+.2f %% of chip clock error (uart_sampling model: both directions, every phase); the clock %s at %g .. %g C: %s' % (
        lim['words'], lim['lo_pct'], lim['hi_pct'], cc['clock'], cc['ambient'][0], cc['ambient'][1], bwords)
    if band is None:
        return {'outcome': 'compromise', 'margin': 0.0, 'why': 'the clock is unrated at these conditions: %s' % bwords, 'evidence': evidence}
    if not (lim['lo_pct'] <= 0.0 <= lim['hi_pct']):
        rel = (lim['peer_baud'] / lim['device_baud'] - 1) * 100.0 if 'peer_baud' in lim else err
        return {'outcome': 'invalid', 'margin': min(0.0 - lim['lo_pct'], lim['hi_pct'] - 0.0),
                'why': 'at the nominal clock the link does not decode both ways: the far end runs %+.1f %% against this divisor (UBRR %d, U2X %d: %+.2f %%)' % (rel, ubrr, u2x, err),
                'gives_up': 'the link', 'evidence': evidence}
    margin = min(band[0] - lim['lo_pct'], lim['hi_pct'] - band[1])
    if margin < 0:
        return {'outcome': 'invalid', 'margin': margin, 'why': 'the clock band %+.2f .. %+.2f %% leaves the decode band %+.2f .. %+.2f %%: framing errors at the edge of the conditions'
                % (band[0], band[1], lim['lo_pct'], lim['hi_pct']), 'gives_up': 'the link at the edge of the ambient range', 'evidence': evidence}
    if abs(err) > rec:
        return {'outcome': 'compromise', 'margin': margin, 'why': 'decodes both ways with %+.2f .. %+.2f %% to spare, but the divisor error %+.2f %% is beyond the receiver\'s recommended '
                '+-%g %% share (%s Tables 20-2 / 20-3): it works only with a peer on the same divisor' % (band[0] - lim['lo_pct'], lim['hi_pct'] - band[1], err, rec, DS), 'evidence': evidence}
    if margin < rec:
        return {'outcome': 'compromise', 'margin': margin, 'why': 'decodes both ways, but only %.2f %% is left beyond the clock band (under the receiver\'s recommended +-%g %% share)' % (margin, rec),
                'evidence': evidence}
    return {'outcome': 'ideal', 'margin': margin, 'why': 'decodes both ways with %.2f %% to spare beyond the clock band; divisor %+.2f %% inside the recommended +-%g %%' % (margin, err, rec),
            'evidence': evidence}


def tick(option, ctx):
    vals = option.get('values') or {}
    if 'usart_u2x' not in vals and 'f_cpu_hz' not in vals and 'tick_prescaler' not in vals:
        return None
    f = float(vals.get('f_cpu_hz', F_CPU_HZ))
    pre, ocr = int(vals.get('tick_prescaler', TICK['prescaler'])), int(vals.get('tick_ocr', TICK['ocr']))
    if pre <= 0 or not 0 <= ocr <= 255:
        return {'outcome': 'invalid', 'margin': 0.0, 'why': 'the tick cannot be made: prescaler %d, OCR2A %d (8-bit)' % (pre, ocr), 'gives_up': 'the 1 ms tick', 'evidence': TICK['source']}
    hz = f / pre / (ocr + 1)
    err = (hz / 1000.0 - 1) * 100.0
    manager = ctx.get('manager')
    cc = ctx.get('clock_context') or context(manager, ctx['bench_solution'])
    band, bwords = _band(cc['clock'], cc['ambient'], manager) if cc['clock'] else (None, 'no clock source')
    evidence = '%s at F_CPU %g: %.4f Hz (%+.3f %%); the clock %s' % (TICK['source'], f, hz, err, bwords)
    if abs(err) > 0.1:
        return {'outcome': 'compromise', 'margin': -abs(err), 'why': 'the tick divisor is %+.3f %% off 1 kHz at this F_CPU' % err, 'evidence': evidence}
    if band is None:
        return {'outcome': 'compromise', 'margin': 0.0, 'why': 'the divisor is exact but the clock is unrated here: %s' % bwords, 'evidence': evidence}
    width = max(abs(band[0]), abs(band[1]))
    return {'outcome': 'ideal' if width <= 1.0 else 'compromise', 'margin': 1.0 - width,
            'why': 'the tick is exactly 1 kHz at nominal and drifts only as the clock does (+-%g %%)' % width, 'evidence': evidence}


CC.register('clock', 1, 'serial-link', serial_link)
CC.register('clock', 1, 'tick', tick)
