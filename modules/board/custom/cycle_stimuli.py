"""
@module board.custom.cycle_stimuli

cyc-0: THE STIMULUS each measured variant is driven with - recorded with the measurement, so a cycle count is always "this hex, driven THIS way".
A stimulus is {name, argv (the twin flags after the hex), files {name: bytes}, seconds, describe, drives}; every field is deterministic (cycle-scheduled,
--free, never wall-clock), so two runs of the same hex + stimulus are the same run.

What each stimulus is meant to reach (the worst path the data allows, said in `drives`):
  presses    5 debounced presses on the variant's button pin, each 157 ms apart so the phase against the 100 ms report changes (a press can land while a
             frame is being sent), plus the contact held ~5 ms
  commands   SET_LED on, off, on, on-again (the one that changes nothing: the short path), and two frames sent back to back in ONE burst (the
             command-apply path twice in a single pass of the loop)
  analog     the A0 triangle ramp the fgm-5a proof uses (200..4800 mV over 1 s) for the analog route, long enough for three presses
  wire       D6 -> D3 for the button-clock demo's sense line (so the second interrupt runs)
Data-dependent parts the stimulus cannot make worse are named in the record (the report frame length is whatever the encoder wrote: the observed largest
is stored and compared with the generated header's maximum).
"""
CPS = 16000000
START = 1600000                 # 100 ms: past the init at the top of main()
GAP = 2400000 + 112000          # 157 ms between presses: >= 3 x the 30 ms debounce, phase-shifting against the 100 ms report
HOLD = 80000                    # ~5 ms closed
N_PRESS = 5
CMD_BURST_AT = 14400000         # 900 ms: two frames in one burst


def _press_args(pin, n=N_PRESS):
    out, c = [], START
    for _ in range(n):
        out += ['--pin-at', 'cycle=%d,pin=%s,level=0' % (c, pin), '--pin-at', 'cycle=%d,pin=%s,level=1' % (c + HOLD, pin)]
        c += GAP
    return out, c


def _base(seconds, adc='--adc0-mv 750'):
    return ['--hex', 'firmware.hex', '--mcu', 'atmega328p', '--freq', str(CPS), '--free', '--seconds', '%g' % seconds, '--status-ms', '0',
            '--uart-out', 'uart.bin', '--seed', '1'] + adc.split()


def _light_commands(cls_spec_fn, frame_fn):
    """The four single commands + one burst of two, as (argv, files, count)."""
    fmap, spec = cls_spec_fn()
    cmds = [(4800000, True), (8000000, False), (11200000, True), (12800000, True)]   # the last asks for what already is: nothing changes
    files, argv = {}, []
    seq = 1
    for i, (at, on) in enumerate(cmds):
        files['c%d.bin' % i] = frame_fn(spec, seq, on)
        argv += ['--inject', 'c%d.bin@%d' % (i, at)]
        seq += 1
    files['burst.bin'] = frame_fn(spec, seq, False) + frame_fn(spec, seq + 1, True)
    argv += ['--inject', 'burst.bin@%d' % CMD_BURST_AT]
    return argv, files, len(cmds) + 2


def _v1_frame(spec, seq, on):
    from board.custom import light_twin as LT
    return LT.cmd_frame(spec, seq, led_on=on)


def stimulus(variant):
    """-> {name, argv, files, seconds, describe, drives, pin}; raises KeyError for a variant with no stimulus defined."""
    from board.custom import light_twin as LT
    files, extra, cmds = {}, [], 0
    if variant in ('uno-light', 'uno-light-unsensed', 'uno-light-pcint', 'uno-light-analog'):
        extra, files, cmds = _light_commands(LT._spec, _v1_frame)
    if variant == 'uno-light':
        # smp-2: S1 - the unsensed stimulus + the sense JUMPER D6 -> D3 (the polled sense route runs every pass; the report carries the sensed level)
        pin = 'PD2'
        pa, end = _press_args(pin)
        pa += ['--wire', 'PD6:PD3']
        adc = '--adc0-mv 750'
        seconds = 1.3
    elif variant == 'uno-light-unsensed':
        pin = 'PD2'
        pa, end = _press_args(pin)
        adc = '--adc0-mv 750'
        seconds = 1.3
    elif variant == 'uno-light-pcint':
        pin = 'PD4'
        pa, end = _press_args(pin)
        adc = '--adc0-mv 750'
        seconds = 1.3
    elif variant == 'uno-light-analog':
        pin, pa, adc, seconds = 'A0', [], '--adc0-ramp 200,4800,1000', 3.6
    elif variant == 'uno-button-clock':
        pin = 'PD2'
        pa, end = _press_args(pin)
        pa += ['--wire', 'PD6:PD3']
        adc, seconds = '--adc0-mv 750', 1.3
    elif variant == 'uno-sim-rig':
        from board.custom import packet_ref
        from board.custom.compat import wire_spec
        from grpcbridge.custom import wire_ref
        from board.custom import gen
        fmap = gen.pinned_contract('SimRigState')[0]['field_map']
        spec = wire_spec(None, 'SimRigState', fmap)
        pin, pa, adc, seconds = 'A0', [], '--adc0-mv 750', 1.3
        steps = [({'pwm_duty': 25}, 3200000), ({'pwm_duty': 50}, 6400000), ({'pwm_duty': 100}, 9600000), ({'led_on': True}, 12800000)]
        for i, (vals, at) in enumerate(steps):
            files['c%d.bin' % i] = packet_ref.frame(1, 0, i + 1, wire_ref.encode(spec, vals, present=list(vals)), version=spec['wire_version'])
            extra += ['--inject', 'c%d.bin@%d' % (i, at)]
        cmds = len(steps)
    elif variant == 'uno-light-v2':
        from board.custom import light_v2_twin as L2
        pin = 'PD2'
        pa, end = _press_args(pin)
        adc, seconds = '--adc0-mv 750', 1.3
        fmap, spec = L2._spec()
        n, at = 1, [4800000, 8000000, 11200000, 12800000]
        for i, on in enumerate((True, False, True, True)):
            files['c%d.bin' % i] = L2.cmd_frame(spec, n, command_id=n, led_on=on)
            extra += ['--inject', 'c%d.bin@%d' % (i, at[i])]
            n += 1
        files['burst.bin'] = L2.cmd_frame(spec, n, command_id=n, led_on=False) + L2.cmd_frame(spec, n + 1, command_id=n + 1, led_on=True)
        extra += ['--inject', 'burst.bin@%d' % CMD_BURST_AT]
        cmds = 6
    else:
        raise KeyError('no stimulus defined for %s' % variant)
    drives = []
    if pa:
        drives.append('%d presses on %s (%d ms apart, closed ~5 ms)' % (N_PRESS, pin, GAP // 16000) if variant != 'uno-light-analog' else '')
    if variant == 'uno-light-analog':
        drives.append('the A0 ramp 200..4800 mV, 1 s period, for %g s (three presses by the fgm-5a model)' % seconds)
    if cmds and variant == 'uno-sim-rig':
        drives.append('%d commands: pwm_duty 25, 50, 100 and led_on, with the TMP36 held at 750 mV (the ADC is read for every report)' % cmds)
    elif cmds:
        drives.append('%d SET_LED commands (4 single - the last changes nothing - and 2 in one burst)' % cmds)
    if variant == 'uno-button-clock':
        drives.append('D6 wired to D3 so the sense interrupt runs; no commands (the clock-set path is not exercised)')
    if variant == 'uno-light':
        drives.append('D6 wired to D3 (the sense jumper): the polled sense route runs every pass and the report carries the sensed level')
    return {'name': variant + '/cyc0-v1', 'argv': _base(seconds, adc) + pa + extra, 'files': files, 'seconds': seconds, 'pin': pin,
            'drives': [d for d in drives if d], 'commands': cmds,
            'describe': 'deterministic, cycle-scheduled, --free; ' + '; '.join(d for d in drives if d)}
