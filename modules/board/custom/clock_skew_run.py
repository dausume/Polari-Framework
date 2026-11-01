"""
@module board.custom.clock_skew_run

tmp-6 (AI-Notes/plans/TEMPERATURE_PLAN.md): THE TIMING BAND FORCED INTO A FIRMWARE RUN. The UNO's firmware runs on the simavr twin with its
clock off by the band tmp-4 gives at a temperature (board.custom.timing_drift.clock_band), and every byte between the ATmega328P and the
UNO R3's USB-serial chip (an ATmega16U2) crosses through a bit-level receiver (board.custom.uart_sampling) at each side's own rate.

Why this is a skewed run although simavr has one clock: the twin is cycle-exact, so the firmware's behaviour IN CYCLES does not depend on
the clock rate - the rate only maps cycles to true time. A clock off by e therefore lives entirely at the boundary: (1) the twin runs at
f = 16 MHz x (1 + e) (`--freq`), (2) everything the far side does is placed in true time (a byte the 16U2 sends at t arrives at cycle
t x f), (3) every byte is re-sampled by the receiving USART at its own rate - the 328P's divisor over f, the 16U2's over its own clock.
The twin's own UART (byte-level, no baud check) is bypassed on both sides.

  peer_divisor(baud) -> (ubrr, u2x)          arduino-usbserial on the 16U2: U2X1 = 1 and UBRR1 = SERIAL_2X_UBBRVAL(baud), except 57600
                                             (U2X1 = 0, SERIAL_UBBRVAL); the LUFA macros are ((F_CPU/8 + baud/2) / baud) - 1 (/16 without U2X)
  limits(u2x, ubrr, peer_pct=0) -> {lo_pct, hi_pct, ...}   the device-clock band in which both directions decode (uart_sampling.model_limits)
  chip_times(tx_log, f, bit) -> [(t, byte, bit)]   the board's bytes on the chip's timing (a burst back to back)
  run(variant, u2x, corners, peer_pct=0, phase=0.5) -> {ok, rows, limits, why}   one twin run per corner
  run_at(temp_c, clock='cstce16m0v53-r0', u2x=1, ppm=None, ...)   corners = the clock's band at temp_c (low, nominal, high), or `ppm` given

Each run: the uno-sim-rig firmware (SimRigState at TELEMETRY_HZ 10, commands on), built offline with USART_U2X 0 or 1; SET pwm_duty 50 sent
by the 16U2 at CMD_AT_S true seconds; RUN_S of true time. Observed: the command bytes the 328P latched, whether the board then reports
pwm_duty 50 (read from the twin's own UART output - what the board DID), the bytes and frames the 16U2 latched (what the host SEES), and
the firmware's uptime_ms against true time (its clock drift, measured: uptime grows (1+e) times as fast as true time, so a 1 s firmware
timeout lasts 1/(1+e) s). Bytes "intact" = the byte the sender meant; framing errors are counted apart (see (a)).

Limits said, not hidden: (a) a framing error is counted at the receiver but the byte is still delivered - the default build's RX ISR and
arduino-usbserial's both read UDR without checking FE (hal.c; Arduino-usbserial.c USART1_RX_vect), so that is what each firmware does with
it; a HAL_UART_ERRCOUNT build would count it, which the twin cannot be told (it injects bytes, not flags); (b') the board's own bytes are
re-timed to the chip's byte time within a burst (chip_times: the twin's UART is slower than the chip's); (b) the twin feeds injected bytes
no closer than its own byte time (10 bits at 115200 over f) - about 2 % slower than the 16U2's 117647 Bd, so the arrival times slip by up
to that; (c) the sampling phase is a knob (0.5 of a sample); (d) the 16U2's clock is a knob (peer_pct, default 0 = exact): the UNO R3
schematic names a 16 MHz crystal (Y1) without a tolerance.

Sources: Arduino-usbserial.c (github.com/arduino/ArduinoCore-avr, firmwares/atmegaxxu2/arduino-usbserial: "Special case 57600 baud for
compatibility with the ATmega328 bootloader", UBRR1 / UCSR1A), LUFA Serial_AVR8.h (SERIAL_UBBRVAL / SERIAL_2X_UBBRVAL); the firmware's own
divisor from the build (hal.c UBRR0_VALUE, board_config.h USART_U2X - board.custom.cycle_measure.uart_model reads them).
"""
import os

from board.custom import timing_drift as TD
from board.custom import uart_sampling as US

VARIANT = 'uno-sim-rig'
BAUD = 115200
F_NOM = 16000000
PEER_F = 16e6
CMD_AT_S = 0.2
RUN_S = 2.0
DUTY = 50
_BUILDS = {}
_LAST = {}


def peer_divisor(baud=BAUD, f=int(PEER_F)):
    if baud == 57600:
        return ((f // 16 + baud // 2) // baud) - 1, 0
    return ((f // 8 + baud // 2) // baud) - 1, 1


def _bit_s(f, ubrr, u2x):
    return (8.0 if u2x else 16.0) * (ubrr + 1) / f


def limits(u2x, ubrr, peer_pct=0.0, baud=BAUD):
    """The device clock error band (%) inside which BOTH directions decode at every phase: 16U2 -> 328P needs peer/device in the 328P's
    window, 328P -> 16U2 needs device/peer in the 16U2's. Closed form from uart_sampling.model_limits (the datasheet equations shown too)."""
    pu, pux = peer_divisor(baud)
    peer_rate = 1.0 / _bit_s(PEER_F * (1 + peer_pct / 100.0), pu, pux)
    dev_rate0 = 1.0 / _bit_s(F_NOM, ubrr, u2x)
    s_d, f_d = US.model_limits(u2x)
    s_p, f_p = US.model_limits(pux)
    lo = max(s_p * peer_rate / dev_rate0, peer_rate / (dev_rate0 * f_d))
    hi = min(f_p * peer_rate / dev_rate0, peer_rate / (dev_rate0 * s_d))
    ds_d, df_d = US.rate_limits(u2x)
    ds_p, df_p = US.rate_limits(pux)
    eq_lo = max(ds_p * peer_rate / dev_rate0, peer_rate / (dev_rate0 * df_d))
    eq_hi = min(df_p * peer_rate / dev_rate0, peer_rate / (dev_rate0 * ds_d))
    return {'lo_pct': (lo - 1) * 100.0, 'hi_pct': (hi - 1) * 100.0, 'eq_lo_pct': (eq_lo - 1) * 100.0, 'eq_hi_pct': (eq_hi - 1) * 100.0,
            'holds_anywhere': lo <= hi, 'device_baud': dev_rate0, 'peer_baud': peer_rate, 'peer_ubrr': pu, 'peer_u2x': pux,
            'words': ('the 328P sends at %.0f Bd (UBRR0 %d, U2X0 %d) and the 16U2 at %.0f Bd (UBRR1 %d, U2X1 %d, clock %+g %%)'
                      % (dev_rate0, ubrr, u2x, peer_rate, pu, pux, peer_pct))}


def _build(variant, u2x, home):
    key = (variant, u2x, home)
    if key not in _BUILDS:
        from board.custom import gen, build as B, cycle_measure as CM
        work = os.path.join(home, 'skew-%s-u2x%d' % (variant, u2x))
        gen.gen('uno', None, work, variant=variant, usart_u2x=u2x)
        row = B.build('uno', work)
        if row.get('state') != 'built':
            return row, None, None
        proj = row['project_dir']
        files = {fn: open(os.path.join(proj, fn), 'rb').read() for fn in os.listdir(proj) if fn.endswith(('.c', '.h'))}
        _BUILDS[key] = (row, open(row['hex_path'], 'rb').read(), CM.uart_model(b'', files))
    return _BUILDS[key]


def _spec():
    from board.custom import gen
    from board.custom.compat import wire_spec
    fmap = gen.pinned_contract('SimRigState')[0]['field_map']
    return fmap, wire_spec(None, 'SimRigState', fmap)


def _frames(stream):
    """[(t_s_or_None, frame dict)] + bad CRC count, through the reference parser; stream = [(t, byte)]."""
    from board.custom import packet_ref
    fmap, spec = _spec()
    p, out = packet_ref.StreamParser(), []
    for t, b in stream:
        for mt, dev, seq, payload, ver in p.feed(bytes([b])):
            if mt == 1:
                try:
                    out.append((t, packet_ref.decode_any(fmap, payload, ver, spec)))
                except ValueError:
                    pass
    return out, p.bad_crc


def _drift_ppm(frames):
    pts = [(t, f.get('uptime_ms')) for t, f in frames if t is not None and isinstance(f.get('uptime_ms'), int)]
    if len(pts) < 2 or pts[-1][0] <= pts[0][0]:
        return None
    return ((pts[-1][1] - pts[0][1]) / 1000.0 / (pts[-1][0] - pts[0][0]) - 1.0) * 1e6


def chip_times(log, f, bit):
    """The twin's --uart-tx-log (u64 cycle + u8 byte) -> [(t_s, byte, bit)] on the CHIP's timing. The twin spaces a burst's bytes by its own
    byte time (it times a byte as if U2X were off - cycle_measure.uart_model), the chip by 10 of its bits; the firmware writes the next byte
    as soon as UDRE says there is room, so a burst on the twin (bytes one twin byte-time apart) is a burst on the chip: back to back at the
    chip's byte time. A byte after a longer pause starts at its own time."""
    recs = [(int.from_bytes(log[i:i + 8], 'little'), log[i + 8]) for i in range(0, len(log) - 8, 9)]
    if not recs:
        return []
    gaps = [b[0] - a[0] for a, b in zip(recs, recs[1:])]
    burst = min(gaps) * 1.05 if gaps else 0
    out, t_prev, c_prev = [], None, None
    for cyc, b in recs:
        if t_prev is not None and cyc - c_prev <= burst:
            t = t_prev + 10 * bit
        else:
            t = max(cyc / float(f), (t_prev + 10 * bit) if t_prev is not None else 0.0)
        out.append((t, b, bit))
        t_prev, c_prev = t, cyc
    return out


def _one(hexb, model, label, e_pct, peer_pct, phase):
    from board.custom import packet_ref
    from grpcbridge.custom import wire_ref
    from firmwarefaults.custom import harness
    f = int(round(F_NOM * (1 + e_pct / 100.0)))
    ubrr, u2x = model['ubrr'], model['u2x']
    dev_bit = _bit_s(f, ubrr, u2x)
    pu, pux = peer_divisor()
    peer_bit = _bit_s(PEER_F * (1 + peer_pct / 100.0), pu, pux)
    _, spec = _spec()
    cmd = packet_ref.frame(1, 0, 1, wire_ref.encode(spec, {'pwm_duty': DUTY}, present=['pwm_duty']), version=spec['wire_version'])
    got = US.receive([(CMD_AT_S + k * 10 * peer_bit, b, peer_bit) for k, b in enumerate(cmd)], dev_bit, u2x, phase)
    files, argv = {}, ['--hex', 'firmware.hex', '--mcu', 'atmega328p', '--freq', str(f), '--free', '--seconds', '%g' % RUN_S, '--status-ms', '0',
                       '--uart-out', harness.UART, '--uart-tx-log', harness.TXLOG]
    for k, r in enumerate(got):
        files['rx%03d.bin' % k] = bytes([r['byte']])
        argv += ['--inject', 'rx%03d.bin@%d' % (k, int(round(r['t_done'] * f)))]
    res = harness.run_files(argv, hexb, files, timeout=300)
    if not res['ok']:
        return {'corner': label, 'device_clock_pct': e_pct, 'verdict': 'twin run failed', 'basis': (res.get('stderr') or '')[-300:]}
    sent = chip_times(res['tx'], f, dev_bit)
    seen = US.receive(sent, peer_bit, pux, phase)
    truth, _ = _frames([(t, b) for t, b, _ in sent])
    host, bad = _frames([(r['t_done'], r['byte']) for r in seen])
    cmd_data = sum(1 for r in got if r['byte'] == r['of'])
    cmd_fe = sum(1 for r in got if r['fe'])
    host_data = sum(1 for r in seen if r['byte'] == r['of'])
    host_fe = sum(1 for r in seen if r['fe'])
    did = any(fr.get('pwm_duty') == DUTY for _, fr in truth)
    saw = any(fr.get('pwm_duty') == DUTY for _, fr in host)
    drift = _drift_ppm(truth)
    data_ok = cmd_data == len(cmd) and host_data == len(sent) and len(got) == len(cmd) and len(seen) == len(sent)
    if data_ok and not (cmd_fe or host_fe):
        verdict = 'link holds: every byte decoded both ways'
    elif data_ok:
        verdict = ('data arrives, with %d framing error(s): both firmwares ignore FE, so it works here; a receiver that checks FE would drop '
                   'those bytes' % (cmd_fe + host_fe))
    else:
        verdict = ('link BROKEN: %d of %d command bytes and %d of %d board bytes arrive as sent'
                   % (cmd_data, len(cmd), host_data, len(sent)))
    return {'corner': label, 'device_clock_pct': e_pct, 'f_hz': f, 'peer_clock_pct': peer_pct, 'device_baud': round(1 / dev_bit, 1),
            'peer_baud': round(1 / peer_bit, 1), 'cmd_bytes': len(cmd), 'cmd_bytes_intact': cmd_data, 'cmd_framing_errors': cmd_fe,
            'board_did_command': 'yes' if did else 'no', 'board_bytes': len(sent), 'host_bytes_intact': host_data,
            'host_framing_errors': host_fe, 'host_bytes_lost': len(sent) - len(seen), 'board_frames': len(truth),
            'host_frames': len(host), 'host_bad_crc': bad, 'host_saw_echo': 'yes' if saw else 'no',
            'uptime_drift_ppm': round(drift, 1) if drift is not None else -1.0, 'expected_drift_ppm': round(e_pct * 1e4, 1),
            'timeout_1s_true_s': round(1.0 / (1 + e_pct / 100.0), 6), 'verdict': verdict,
            'basis': ('twin at %d Hz; the 16U2 sends at %.0f Bd, the 328P samples at %.0f Bd (U2X0 %d); uptime_ms against true time over %d frames '
                      '(1 ms resolution over %.1f s: about +-%d ppm)' % (f, 1 / peer_bit, 1 / dev_bit, u2x, len(truth), RUN_S, round(1e6 / (RUN_S * 1000)))),
            'firmware_sha256': '', 'argv': ' '.join(['polari-avr-twin'] + argv)}


def run(variant=VARIANT, u2x=1, corners=(('nominal', 0.0),), peer_pct=0.0, phase=0.5, home=None):
    from firmwarefaults.custom import fault_engines as fe
    if not fe.available():
        return {'ok': False, 'rows': [], 'why': 'no avr twin on this device (the board engines image or a worker) - nothing was run'}
    home = home or os.path.join(os.path.expanduser('~'), '.polari', 'clock-skew')
    row, hexb, model = _build(variant, int(u2x), home)
    if hexb is None:
        return {'ok': False, 'rows': [], 'why': 'the build failed: %s' % (row.get('error') or row.get('state'))}
    lim = limits(model['u2x'], model['ubrr'], peer_pct)
    rows = []
    for label, e in corners:
        r = _one(hexb, model, label, float(e), float(peer_pct), phase)
        r['firmware_sha256'] = row.get('artifact_sha256', '')
        rows.append(r)
    return {'ok': True, 'variant': variant, 'u2x': model['u2x'], 'ubrr': model['ubrr'], 'limits': lim, 'rows': rows, 'why': ''}


def run_at(temp_c, clock='cstce16m0v53-r0', u2x=1, ppm=None, peer_pct=0.0, phase=0.5, home=None, board=TD.UNO):
    """The clock's band at temp_c -> low / nominal / high corners (or one corner at `ppm`, a ClockSkewFault knob) -> run()."""
    if clock not in TD.CLOCKS:
        return {'ok': False, 'rows': [], 'why': 'no clock %r - %s' % (clock, ', '.join(TD.CLOCKS))}
    if TD.CLOCKS[clock]['f_hz'] != F_NOM:
        return {'ok': False, 'rows': [], 'why': '%s runs at %g MHz; the UNO firmware is built for F_CPU 16 MHz, so it would need its own build - not run'
                                              % (clock, TD.CLOCKS[clock]['f_hz'] / 1e6)}
    if ppm is not None:
        corners, words = [('given', float(ppm) / 1e4)], 'a given clock error of %g ppm (a knob)' % float(ppm)
    else:
        band = TD.clock_band(clock, float(temp_c))
        if not band['inside']:
            return {'ok': False, 'rows': [], 'why': 'at %g C the clock is %s - no corner to run' % (float(temp_c), band['words'])}
        corners = [('low', band['low_pct']), ('nominal', 0.0), ('high', band['high_pct'])]
        words = '%s at %g C: %s' % (clock, float(temp_c), band['words'])
    out = run(VARIANT, u2x, corners, peer_pct, phase, home)
    out.update(temp_c=float(temp_c), clock=clock, band_words=words, ppm=ppm)
    if out.get('ok'):
        _LAST[(board, out['u2x'])] = out
    return out


def last(board=TD.UNO, u2x=1):
    return _LAST.get((board, int(u2x)))


def _summary(res):
    rows = res['rows']
    holds = [r['corner'] for r in rows if str(r.get('verdict', '')).startswith('link holds')]
    if len(holds) == len(rows):
        return 'holds at every corner (%s)' % ', '.join(holds)
    return '; '.join('%s %+g %%: %s' % (r['corner'], r['device_clock_pct'], r['verdict']) for r in rows)


def rows(definition, which):
    """The Board Details parts: timing-run (one editable row per build - type a temperature) and timing-run-corners (the newest runs)."""
    if definition != TD.UNO:
        return [], 'the firmware run at temperature needs the UNO R3\'s template firmware and its cited clock - not %s' % definition
    if which == 'timing-run-corners':
        out = []
        for u2x in (1, 0):
            res = last(definition, u2x)
            for r in (res or {}).get('rows', []):
                out.append(dict(r, u2x=u2x, temp_c=res['temp_c']))
        return out, '' if out else 'no firmware run yet - type a temperature above'
    out = []
    for u2x in (1, 0):
        res = last(definition, u2x)
        ubrr = res['ubrr'] if res else TD.ubrr(F_NOM, BAUD, u2x)[0]
        lim = limits(u2x, ubrr)
        band = TD.clock_band(res['clock'] if res else 'cstce16m0v53-r0', res['temp_c'] if res else 25.0)
        out.append({'board': definition, 'u2x': u2x, 'ubrr': ubrr, 'signed': True, 'temp_c': res['temp_c'] if res else 25.0,
                    'clock_band_pct': ('%+.2f .. %+.2f' % (band['low_pct'], band['high_pct'])) if band['inside'] else 'unrated',
                    'link_band_pct': ('%+.2f .. %+.2f' % (lim['lo_pct'], lim['hi_pct'])) if lim['holds_anywhere'] else 'nowhere',
                    'datasheet_band_pct': '%+.2f .. %+.2f' % (lim['eq_lo_pct'], lim['eq_hi_pct']),
                    'verdict': _summary(res) if res else 'not run', 'basis': lim['words'] + ('; ' + res['band_words'] if res else '')})
    return out, ''
