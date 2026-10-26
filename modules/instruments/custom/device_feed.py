"""
@module instruments.custom.device_feed

osc-4 (OSCILLOSCOPE_PLAN.md §3e): the emulated scope's channels fed FROM THE DEVICE SIDE — "emulate 4-channel oscilloscope behavior in respect
to devices" — so a capture shows what a probe on the board would, derived from what the simulated board was actually driven with or did:

  sources_from_stimulus(variant, logic_v=5.0)
      the twin STIMULUS a variant is measured with (board.custom.cycle_stimuli.stimulus: `--pin-at cycle=N,pin=PD2,level=0`, `--adc0-mv MV`,
      `--adc0-ramp LO,HI,PERIOD_MS`, `--wire A:B`) -> one source per driven line: a button pin is a `pulses` trace (pulled up at logic_v, low
      while pressed, every edge at cycle / CPS seconds), ADC0 is `dc` (mV / 1000) or the twin's `triangle` ramp; the window is the stimulus's
      `seconds`. Everything is derived from the stimulus record — the same inputs the cycle record names (reproducibility).
  sources_from_events(events, cps, logic_v=5.0)
      the twin's OWN pin events (`{"t": "pin", "pin": "PD6", "level": 1, "cycle": N}` as board.board_twins_api streams them) -> a `pulses`
      trace per pin: what the firmware did (the LED line, the sense line), not what it was fed.
  feed(emu, channels, seconds, scale_v_div=2.0, depth=None)
      puts the traces on the emulator: channel n <- spec; the timebase is set so the window is [0, seconds] (10 divisions of seconds/10 with the
      trigger offset moving the -5 div pre-trigger origin to 0), every fed channel is switched on at `scale_v_div` (2 V/div so a 5 V logic
      line sits inside the ±4 div dynamic range — at the default 1 V/div it would clip at +4 V, as a real scope does), the others left as they
      are; the next capture acquires afresh.
No twin needs to run for the stimulus path (it is a pure record); the events path takes the events it is given (posted, or read from a session
by a later slice).
"""
import re

from instruments.custom import sources as SRC

_PIN_AT = re.compile(r'cycle=(\d+),pin=([A-Za-z0-9]+),level=([01])')


def _cps(argv):
    for i, a in enumerate(argv):
        if a == '--freq' and i + 1 < len(argv):
            return float(argv[i + 1])
    from board.custom.cycle_stimuli import CPS
    return float(CPS)


def sources_from_stimulus(variant, logic_v=5.0):
    from board.custom import cycle_stimuli as CS
    st = CS.stimulus(variant)
    argv, cps = list(st['argv']), _cps(st['argv'])
    pins, adc, wires = {}, None, []
    for i, a in enumerate(argv):
        if a == '--pin-at' and i + 1 < len(argv):
            m = _PIN_AT.fullmatch(argv[i + 1])
            if not m:
                raise ValueError('unreadable --pin-at %r' % argv[i + 1])
            cycle, pin, level = int(m.group(1)), m.group(2), int(m.group(3))
            pins.setdefault(pin, []).append([cycle / cps, logic_v if level else 0.0])
        elif a == '--adc0-mv' and i + 1 < len(argv):
            adc = {'kind': 'dc', 'offset_v': float(argv[i + 1]) / 1000.0}
        elif a == '--adc0-ramp' and i + 1 < len(argv):
            lo, hi, ms = (float(x) for x in argv[i + 1].split(','))
            adc = {'kind': 'triangle', 'lo_v': lo / 1000.0, 'hi_v': hi / 1000.0, 'period_s': ms / 1000.0}
        elif a == '--wire' and i + 1 < len(argv):
            wires.append(argv[i + 1])
    sources = {pin: {'kind': 'pulses', 'initial_v': logic_v, 'edges': sorted(edges)} for pin, edges in pins.items()}   # a button line idles HIGH (pull-up)
    if adc is not None:
        sources['adc0'] = adc
    return {'variant': variant, 'seconds': float(st['seconds']), 'cps': cps, 'sources': sources, 'wires': wires,
            'describe': 'stimulus %s: %s' % (variant, st.get('describe', ''))}


def sources_from_events(events, cps, logic_v=5.0):
    pins = {}
    for ev in events:
        if not isinstance(ev, dict) or ev.get('t') != 'pin':
            continue
        pins.setdefault(str(ev['pin']), []).append([int(ev['cycle']) / float(cps), logic_v if int(ev.get('level', 0)) else 0.0])
    out = {}
    for pin, edges in pins.items():
        edges.sort()
        first_level = edges[0][1]
        out[pin] = {'kind': 'pulses', 'initial_v': logic_v - first_level if first_level in (0.0, logic_v) else 0.0, 'edges': edges}   # the level BEFORE the first edge is its opposite
    return out


def feed(emu, channels, seconds, scale_v_div=2.0, depth=None):
    """channels: {channel number: source spec}. Returns {channel: description}."""
    s = emu.state
    seconds = float(seconds)
    if seconds <= 0:
        raise ValueError('seconds must be positive')
    with emu.lock:
        s.tb_scale = min(max(seconds / s.p['divisions_h'], s.p['tb_min']), s.p['tb_max'])
        s.tb_offset = -s.p['pretrigger_div'] * s.tb_scale          # the window starts at t = 0 (the stimulus's own clock)
        if depth:
            s.mdepth = int(min(int(depth), s.depth_cap()))
        out = {}
        for ch, spec in channels.items():
            n = int(ch)
            if n not in s.channels:
                raise ValueError('no channel %d on %s' % (n, s.p['model']))
            s.sources[n] = SRC.validate(spec)
            s.channels[n]['display'] = True
            s.channels[n]['scale'] = min(max(float(scale_v_div), s.p['scale_min']), s.p['scale_max'])
            out[n] = SRC.describe(spec)
        s.wav['start'], s.wav['stop'] = 1, int(s.mdepth)
        s.invalidate()
    return out
