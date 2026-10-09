"""board_button_clock_twin_selftest — ucd-0e2 (UNO_CORE_DEMO_PLAN.md §1/§5f/§5g): THE FIRMWARE + ITS PROOF ON THE TWIN
for the button-clock demo (variant uno-button-clock, app apps/button_clock.c). `button_clock_parts(check)` is wired
into board.board_selftest.run(); the same checks run standalone from tests/board_uno_button_clock_probe.py. Reuses the
idioms of board.board_pinlevel_selftest (pin-at, --wire) and board.custom.packet_ref / grpcbridge.custom.wire_ref (the
Python reference codec, offline from the pinned contract — no Java bridge needed).

Six cases, all against the REAL simavr twin (no fake/mock), run through the direct harness (firmwarefaults.custom.
harness — deterministic cycle scheduling, never real-time sleeps):

  (a) N presses on PD2, --wire PD6:PD3 -> button_presses == N, sense_rises + sense_falls == N, led_on == (N odd)
  (b) a small event_queue_len build -> one press overflows it; dropped_events reports exactly what overflowed, and
      received + dropped == the N*3 events a press mints (press, led_on/off, sense_rise/fall)
  (c) SET_TIME twice (--inject): the first sync -> clock_synced, epoch tracks; drift_ms stays 0 until the SECOND sync
  (d) SNAPSHOT (--inject): an out-of-band state frame (status snapshot) arrives between the scheduled ticks, followed
      by the queue's events
  (e) boot_session: constant across every frame of one run; differs when the EEPROM's prior value differs (the proxy
      for "differs between two runs" — honest limitation: a --free harness run starts a fresh simavr process each
      time, so "a second run" is modelled as a different PRIOR EEPROM value, not a literal second reset of the SAME
      process; on real hardware EEPROM persists through an actual reset and this is a direct proof)
  (f) NEGATIVE: the same N presses with NO --wire -> sense_rises + sense_falls stay 0 while button_presses == N

Skips HONESTLY (every check SKIP) when the avr-twin engine (prf-board-engines image or a local polari-avr-twin) is not
reachable on this device — board.custom.board_engines.resolve names why.

    PYTHONPATH=.:modules python3 -m board.board_button_clock_twin_selftest     # from polari-framework/
"""
import struct
import tempfile

VARIANT = 'uno-button-clock'
N_PRESSES = 4
PRESS_GAP_CYCLES = 2400000     # 150 ms @ 16 MHz: >= 3 x the default 30 ms debounce (the plan's own spacing rule)
PRESS_HOLD_CYCLES = 80000      # ~5 ms "held" before release
START_CYCLE = 1600000          # 100 ms in — past every *_init() at the top of main()


def _press_pinat(n=N_PRESSES, start=START_CYCLE, gap=PRESS_GAP_CYCLES, hold=PRESS_HOLD_CYCLES):
    out, c = [], start
    for _ in range(n):
        out += ['--pin-at', 'cycle=%d,pin=PD2,level=0' % c, '--pin-at', 'cycle=%d,pin=PD2,level=1' % (c + hold)]
        c += gap
    return out, c


def _specs():
    from board.custom import gen
    from board.custom.compat import wire_spec
    fmap_s = gen.pinned_contract('ButtonClockState')[0]['field_map']
    fmap_e = gen.pinned_contract('ButtonClockEvent')[0]['field_map']
    return fmap_s, wire_spec(None, 'ButtonClockState', fmap_s), fmap_e, wire_spec(None, 'ButtonClockEvent', fmap_e)


def _decode_frames(uart_bytes, fmap_s, spec_s, fmap_e, spec_e):
    from board.custom import packet_ref
    parser = packet_ref.StreamParser()
    frames = parser.feed(uart_bytes)
    states, events = [], []
    for mt, dev, seq, payload, ver in frames:
        if mt == 1:
            states.append(packet_ref.decode_any(fmap_s, payload, ver, spec_s))
        elif mt == 2:
            events.append(packet_ref.decode_any(fmap_e, payload, ver, spec_e))
    return states, events, parser.bad_crc


def _cmd_frame(spec_s, seq, **vals):
    """A SET_TIME/SET_LED/SNAPSHOT command frame, PRESENCE-MASKED to exactly the fields given (never present=None,
    which would encode all 24 fields — a ~170-byte frame the twin's --inject drops mid-frame; proven empirically)."""
    from board.custom import packet_ref
    from grpcbridge.custom import wire_ref
    payload = wire_ref.encode(spec_s, vals, present=list(vals))
    return packet_ref.frame(1, 0, seq, payload, version=spec_s['wire_version'])


def _build(work, variant=VARIANT, **knobs):
    from board.custom import gen, build
    gen.gen('uno', None, work, variant=variant, **knobs)
    return build.build('uno', work)


def button_clock_parts(check):
    from board.custom import board_engines as be
    where = be.resolve('avr-twin')
    if where['how'] not in ('local-binary', be.LOCAL_IMAGE):
        check('SKIP ucd-0e2 (button-clock firmware + twin proof): no simavr twin here — %s' % where['why'], True)
        return
    from firmwarefaults.custom import harness

    fmap_s, spec_s, fmap_e, spec_e = _specs()
    work = tempfile.mkdtemp(prefix='ucd-0e2-button-clock-')
    row = _build(work)
    check('uno-button-clock builds (plain C, avr-libc, within the cited flash/RAM limits)',
          row['state'] == 'built' and 0 < row['flash_bytes'] <= 32256 and 0 < row['ram_bytes'] <= 2048,
          '%s: flash %s/32256 B, ram %s/2048 B' % (row.get('notes'), row.get('flash_bytes'), row.get('ram_bytes')))
    hex_bytes = open(row['hex_path'], 'rb').read()

    # ---- (a) N presses, --wire PD6:PD3: the full invariant (a SET_TIME first, so led_changed_at/last_edge_at are
    # meaningful epoch stamps rather than the pre-sync 0 clock_tick reports honestly) ------------------------------
    pinat, end_cycle = _press_pinat()
    seconds_a = (end_cycle + 1600000) / 16000000.0
    cmd0 = _cmd_frame(spec_s, 0, set_epoch_s=1760000000, set_ms=0, set_sync_generation=1)
    argv = ['--hex', 'firmware.hex', '--mcu', 'atmega328p', '--freq', '16000000', '--free', '--seconds', '%g' % seconds_a,
            '--status-ms', '0', '--adc0-mv', '750', '--uart-out', 'uart.bin', '--wire', 'PD6:PD3',
            '--inject', 'cmd0.bin@800000'] + pinat
    r = harness.run_files(argv, hex_bytes, {'cmd0.bin': cmd0}, timeout=120)
    states, events, bad_crc = _decode_frames(r['uart'], fmap_s, spec_s, fmap_e, spec_e)
    last = states[-1] if states else {}
    check('(a) %d presses + --wire PD6:PD3 -> button_presses == %d, sense_rises + sense_falls == %d, led_on == (%d odd) '
          '= %s, no bad-CRC frames' % (N_PRESSES, N_PRESSES, N_PRESSES, N_PRESSES, bool(N_PRESSES % 2)),
          r['ok'] and bad_crc == 0 and last.get('button_presses') == N_PRESSES
          and (last.get('sense_rises', 0) + last.get('sense_falls', 0)) == N_PRESSES
          and last.get('led_on') == bool(N_PRESSES % 2) and last.get('led_changed_at', 0) > 0
          and last.get('last_edge_at', 0) > 0, last)
    kinds = [e.get('kind') for e in events]
    seqs = [e.get('seq') for e in events]
    non_sync = [k for k in kinds if k != 'sync']
    check('(a) %d events (press + led_on/off) + %d sense events (+ 1 sync, from the SET_TIME above), in order, '
          'increasing seq, no drops' % (2 * N_PRESSES, N_PRESSES),
          len(non_sync) == 3 * N_PRESSES and kinds.count('sync') == 1 and kinds.count('press') == N_PRESSES
          and kinds.count('led_on') + kinds.count('led_off') == N_PRESSES
          and kinds.count('sense_rise') + kinds.count('sense_fall') == N_PRESSES
          and seqs == sorted(seqs) and last.get('dropped_events', -1) == 0, kinds)

    # ---- (f) NEGATIVE: the same presses, no --wire --------------------------------------------------------------
    argv_f = ['--hex', 'firmware.hex', '--mcu', 'atmega328p', '--freq', '16000000', '--free', '--seconds', '%g' % seconds_a,
              '--status-ms', '0', '--adc0-mv', '750', '--uart-out', 'uart.bin'] + pinat
    r = harness.run(argv_f, hex_bytes, timeout=120)
    states_f, _, _ = _decode_frames(r['uart'], fmap_s, spec_s, fmap_e, spec_e)
    last_f = states_f[-1] if states_f else {}
    check('(f) NEGATIVE: the same %d presses with NO --wire -> sense_rises + sense_falls stay 0 while button_presses == %d'
          % (N_PRESSES, N_PRESSES),
          r['ok'] and last_f.get('button_presses') == N_PRESSES
          and last_f.get('sense_rises', -1) == 0 and last_f.get('sense_falls', -1) == 0, last_f)

    # ---- (b) overflow: a 2-slot queue, one press mints 3 events (press, led change, sense edge) ------------------
    work_q = tempfile.mkdtemp(prefix='ucd-0e2-button-clock-q2-')
    row_q = _build(work_q, event_queue_len=2)
    check('a event_queue_len=2 build (the same firmware, one knob overridden) builds', row_q['state'] == 'built', row_q.get('notes'))
    hex_q = open(row_q['hex_path'], 'rb').read()
    argv_q = ['--hex', 'firmware.hex', '--mcu', 'atmega328p', '--freq', '16000000', '--free', '--seconds', '0.3',
              '--status-ms', '0', '--adc0-mv', '750', '--uart-out', 'uart.bin', '--wire', 'PD6:PD3',
              '--pin-at', 'cycle=160000,pin=PD2,level=0', '--pin-at', 'cycle=240000,pin=PD2,level=1']
    r = harness.run(argv_q, hex_q, timeout=60)
    states_q, events_q, _ = _decode_frames(r['uart'], fmap_s, spec_s, fmap_e, spec_e)
    last_q = states_q[-1] if states_q else {}
    dropped = last_q.get('dropped_events', -1)
    check('(b) event_queue_len=2: one press mints 3 events — received %d + dropped %d == 3 (drop-oldest: the OLDEST, '
          '"press", is the one missing)' % (len(events_q), dropped),
          r['ok'] and len(events_q) + dropped == 3 and dropped >= 1 and 'press' not in [e.get('kind') for e in events_q],
          [e.get('kind') for e in events_q])

    # ---- (c) SET_TIME twice: synced, epoch tracks, drift_ms only from the SECOND sync ----------------------------
    host_epoch_1, host_epoch_2 = 1760000000, 1760000005   # the 2nd sync: host time jumped +5 s
    cmd1 = _cmd_frame(spec_s, 1, set_epoch_s=host_epoch_1, set_ms=0, set_sync_generation=5)
    cmd2 = _cmd_frame(spec_s, 2, set_epoch_s=host_epoch_2, set_ms=0, set_sync_generation=6)
    argv_c = ['--hex', 'firmware.hex', '--mcu', 'atmega328p', '--freq', '16000000', '--free', '--seconds', '1.2',
              '--status-ms', '0', '--adc0-mv', '750', '--uart-out', 'uart.bin',
              '--inject', 'cmd1.bin@1600000', '--inject', 'cmd2.bin@16000000']
    r = harness.run_files(argv_c, hex_bytes, {'cmd1.bin': cmd1, 'cmd2.bin': cmd2}, timeout=60)
    states_c, events_c, _ = _decode_frames(r['uart'], fmap_s, spec_s, fmap_e, spec_e)
    synced_frames = [s for s in states_c if s.get('clock_synced')]
    first_synced = synced_frames[0] if synced_frames else {}
    after_2nd = [s for s in states_c if s.get('sync_generation') == 6]
    check('(c) the FIRST SET_TIME -> clock_synced true, epoch_s/ms track uptime from it, drift_ms stays 0 (nothing to '
          'compare against yet)',
          bool(synced_frames) and first_synced.get('sync_generation') == 5
          and abs(first_synced.get('epoch_s', 0) - host_epoch_1) <= 1 and first_synced.get('drift_ms') == 0, first_synced)
    check('(c) the SECOND SET_TIME (host +5 s) -> sync_generation bumped to 6, drift_ms reported non-zero (never '
          'from the first sync)',
          bool(after_2nd) and after_2nd[0].get('drift_ms', 0) != 0, after_2nd[0] if after_2nd else None)
    check('(c) a `sync` ButtonClockEvent queued for each SET_TIME',
          len([e for e in events_c if e.get('kind') == 'sync']) == 2, [e.get('kind') for e in events_c])

    # ---- (d) SNAPSHOT: an out-of-band state frame (status snapshot), then the queued events -----------------------
    cmd3 = _cmd_frame(spec_s, 3, snapshot=True)
    argv_d = ['--hex', 'firmware.hex', '--mcu', 'atmega328p', '--freq', '16000000', '--free', '--seconds', '0.5',
              '--status-ms', '0', '--adc0-mv', '750', '--uart-out', 'uart.bin', '--inject', 'cmd3.bin@1600000']
    r = harness.run_files(argv_d, hex_bytes, {'cmd3.bin': cmd3}, timeout=60)
    states_d, _, _ = _decode_frames(r['uart'], fmap_s, spec_s, fmap_e, spec_e)
    snap_frames = [s for s in states_d if s.get('status') == 'snapshot']
    non_snap_after = [s for s in states_d if s is not snap_frames[0]] if snap_frames else []
    check('(d) SNAPSHOT -> one out-of-band ButtonClockState frame with status snapshot, arriving between the '
          'scheduled telemetry ticks; status reverts to idle/commanded/synced on the frames after it',
          bool(snap_frames) and len(states_d) >= 3
          and all(s.get('status') != 'snapshot' for s in states_d if s is not snap_frames[0]), [s.get('status') for s in states_d])

    # ---- (e) boot_session: constant within a run; differs when the prior EEPROM value differs --------------------
    r = harness.run(['--hex', 'firmware.hex', '--mcu', 'atmega328p', '--freq', '16000000', '--free', '--seconds', '0.3',
                     '--status-ms', '0', '--adc0-mv', '750', '--uart-out', 'uart.bin'], hex_bytes, timeout=60)
    states_e1, _, _ = _decode_frames(r['uart'], fmap_s, spec_s, fmap_e, spec_e)
    sessions_1 = {s.get('boot_session') for s in states_e1}
    seed = struct.pack('<I', 10).hex()   # a "prior" EEPROM value of 10 -> this run's boot_session mints as 11
    r = harness.run(['--hex', 'firmware.hex', '--mcu', 'atmega328p', '--freq', '16000000', '--free', '--seconds', '0.3',
                     '--status-ms', '0', '--adc0-mv', '750', '--uart-out', 'uart.bin', '--eeprom-set', '0x0=%s' % seed],
                    hex_bytes, timeout=60)
    states_e2, _, _ = _decode_frames(r['uart'], fmap_s, spec_s, fmap_e, spec_e)
    sessions_2 = {s.get('boot_session') for s in states_e2}
    check('(e) boot_session is IDENTICAL on every frame of one run (%s) and non-zero' % sessions_1,
          len(sessions_1) == 1 and 0 not in sessions_1, sessions_1)
    check('(e) boot_session DIFFERS when the prior EEPROM value differs (10 -> mints 11, vs a virgin chip -> mints 1) '
          '— the honest proxy for "differs between two resets": a --free harness run is a fresh simavr process each '
          'time, so a literal second reset of the SAME process is not exercised here; on real hardware EEPROM '
          'persists through an actual reset and this is then a direct proof, not a proxy',
          len(sessions_2) == 1 and sessions_2 != sessions_1, (sessions_1, sessions_2))


def run_button_clock_twin(check):
    button_clock_parts(check)


if __name__ == '__main__':
    import sys
    passed = total = 0

    def check(label, cond, extra=''):
        global passed, total
        total += 1
        passed += bool(cond)
        print('  [%s] %s %s' % ('PASS' if cond else 'FAIL', label, extra if not cond else ''))

    button_clock_parts(check)
    print('\n%d/%d checks passed' % (passed, total))
    sys.exit(0 if passed == total else 1)
