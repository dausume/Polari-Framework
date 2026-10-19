"""
@module board.custom.light_variant_twin

fsc-6: THE LIGHT PURPOSES ON A CONFIG THAT SPEAKS ButtonClockState (the two LED-sense variants, uno-light-sense-poll and uno-light-sense-pcint). board.custom.light_twin judges the uno-light
build, which speaks LightState (led_on, toggles, source). The sense variants are the button-clock app: same button (D2, 30 ms debounce), same light (D6), same 10 Hz report, same bound
(100 ms) - but a DIFFERENT wire class, so the same two checks are restated on the fields it has. Nothing is loosened; each field the light check reads has a named stand-in:

  LightState                       ButtonClockState (what is read instead)
  toggles == presses               button_presses == presses (and ButtonClockEvent `press` x presses)
  source == button                 status stays `idle` (no command was sent) and no command moved the count
  source == command                status == `commanded`, and button_presses stays 0 (a command is not a press)
  SET_LED = led_on                 SET_LED = set_led (a presence-masked command field; the report still shows led_on)
  (the sense wire)                 run WITH the variant's own jumper (D6 -> its sense pin), as it is built to be used; the edges it counts are named in the words, not required

Both runs also go through NEGATIVE controls on the same judges, from real twin runs: the presses judge must reject a run with no press and a run whose presses land on a pin that is not the
button; the commands judge must reject a run with no command. `prove()` returns the {'ok', 'route', 'why', 'frames_compared', 'how', 'controls'} shape light_twin.prove returns.
scl-2: the from-Polari check starts from the struct (board.custom.light_struct). The boot Purpose needs no restatement: board.custom.light_boot_twin reads boot_session, which both classes carry (it takes the variant).
"""
import shutil
import tempfile

from board.custom import light_twin as LT

N_PRESSES = LT.N_PRESSES
CPS = 16000000


def _specs():
    from board.custom import gen
    from board.custom.compat import wire_spec
    fmap_s = gen.pinned_contract('ButtonClockState')[0]['field_map']
    fmap_e = gen.pinned_contract('ButtonClockEvent')[0]['field_map']
    return fmap_s, wire_spec(None, 'ButtonClockState', fmap_s), fmap_e, wire_spec(None, 'ButtonClockEvent', fmap_e)


def decode(uart):
    """-> (states, events, bad_crc) - the ButtonClockState (message 1) and ButtonClockEvent (message 2) frames, through the independent Python reference codec."""
    from board.custom import packet_ref
    fmap_s, spec_s, fmap_e, spec_e = _specs()
    p = packet_ref.StreamParser()
    states, events = [], []
    for mt, _dev, _seq, payload, ver in p.feed(bytes(uart)):
        if mt == 1:
            states.append(packet_ref.decode_any(fmap_s, payload, ver, spec_s))
        elif mt == 2:
            events.append(packet_ref.decode_any(fmap_e, payload, ver, spec_e))
    return states, events, p.bad_crc


def set_led_frame(seq, on):
    """A SET_LED command PRESENCE-MASKED to exactly set_led (the whole struct would be a ~170-byte frame the twin's --inject drops)."""
    from board.custom import packet_ref
    from grpcbridge.custom import wire_ref
    _fs, spec_s, _fe, _se = _specs()
    return packet_ref.frame(1, 0, seq, wire_ref.encode(spec_s, {'set_led': bool(on)}, present=['set_led']), version=spec_s['wire_version'])


def _argv(variant, seconds, extra, wired=True):
    from board.custom import variant_twin as VT
    wire = ['--wire', 'PD6:%s' % VT.sense_soc_pin(variant)] if wired else []
    return VT._argv(seconds, wire + extra)


def judge_presses(states, events, n=N_PRESSES):
    """(ok, why): the light flips with every press, the press count equals the presses, nobody commanded it."""
    last = states[-1] if states else {}
    seen = sorted({(f.get('button_presses'), bool(f.get('led_on'))) for f in states if f.get('button_presses')})
    flips = all(led == bool(c % 2) for c, led in seen)
    kinds = [e.get('kind') for e in events]
    ok = (bool(states) and last.get('button_presses') == n and bool(last.get('led_on')) == bool(n % 2) and flips
          and last.get('status') == 'idle' and kinds.count('press') == n)
    return ok, ('%d press(es): last frame button_presses=%s led_on=%s status=%s; every state seen had led_on == (presses odd): %s; %d `press` event(s); sense edges counted %s'
                % (n, last.get('button_presses'), last.get('led_on'), last.get('status'), flips, kinds.count('press'), (last.get('sense_rises') or 0) + (last.get('sense_falls') or 0)))


def judge_commands(states):
    """(ok, why): after SET_LED 1 the frames say led_on with status=commanded and no press counted; after SET_LED 0, off, still no press."""
    on = [f for f in states if f.get('led_on')]
    last = states[-1] if states else {}
    ok = (bool(on) and all(f.get('status') == 'commanded' and not f.get('button_presses') for f in on)
          and not last.get('led_on') and last.get('status') == 'commanded' and not last.get('button_presses'))
    return ok, ('SET_LED 1 -> %d frame(s) with led_on, status=%s, button_presses=%s; SET_LED 0 -> last frame led_on=%s status=%s button_presses=%s'
                % (len(on), on[-1].get('status') if on else None, on[-1].get('button_presses') if on else None, last.get('led_on'), last.get('status'), last.get('button_presses')))


def run_presses(variant, hex_bytes, n=N_PRESSES, pin='PD2'):
    from firmwarefaults.custom import harness
    pinat, end = LT.press_pinat(n)
    if pin != 'PD2':
        pinat = [a.replace('pin=PD2', 'pin=%s' % pin) for a in pinat]
    r = harness.run(_argv(variant, (end + LT.RUN_TAIL) / float(CPS), pinat), hex_bytes, timeout=120)
    return (r,) + decode(r['uart'])


def run_commands(variant, hex_bytes, send=True):
    from firmwarefaults.custom import harness
    files = {'on.bin': set_led_frame(1, True), 'off.bin': set_led_frame(2, False)}
    inj = ['--inject', 'on.bin@%d' % LT.CMD_ON_CYCLE, '--inject', 'off.bin@%d' % LT.CMD_OFF_CYCLE] if send else []
    r = harness.run_files(_argv(variant, (LT.CMD_OFF_CYCLE + 4 * LT.RUN_TAIL) / float(CPS), inj), hex_bytes, files, timeout=120)
    return (r,) + decode(r['uart'])


def prove(which, variant, mode='digital-twin'):
    if mode == 'hardware':
        return {'ok': False, 'route': 'refused', 'why': 'the light test --hardware is not wired yet (the UNO is not attached)'}
    ready, why = LT.engine_ready()
    if not ready:
        return {'ok': False, 'route': 'refused', 'why': 'no simavr twin here: %s' % why}
    work = tempfile.mkdtemp(prefix='fsc6-light-')
    try:
        return _prove_in(work, which, variant)
    finally:
        shutil.rmtree(work, ignore_errors=True)


def _prove_in(work, which, variant):
    from board.custom import gen, build as B
    gen.gen('uno', None, work, variant=variant)
    row = B.build('uno', work)
    if row.get('state') != 'built':
        return {'ok': False, 'route': 'digital-twin', 'why': '%s did not build: %s' % (variant, row.get('notes'))}
    hex_bytes = open(row['hex_path'], 'rb').read()
    ok, parts, seen, ctl = True, [], 0, []
    if which in ('both', 'button'):
        r, st, ev, bad = run_presses(variant, hex_bytes)
        o, w = judge_presses(st, ev)
        ok, seen = ok and o and r['ok'] and bad == 0, seen + len(st)
        parts.append('button: ' + w)
        r0, s0, e0, _b = run_presses(variant, hex_bytes, n=0)
        r1, s1, e1, _b = run_presses(variant, hex_bytes, pin='PD4')
        ctl += [('no press at all', judge_presses(s0, e0)[0] and r0['ok']), ('the same presses on a pin that is not the button (D4)', judge_presses(s1, e1)[0] and r1['ok'])]
    if which in ('both', 'polari'):
        # scl-2: the from-Polari proof STARTS FROM THE STRUCT (the same-shaped toggle on ButtonClockState.set_led -> a derived frame -> the twin); the hand-frame check runs inside it as the board half
        from board.custom import light_struct as LS
        o, w, n, sctl = LS.prove_polari(variant, 'button_clock', hex_bytes)
        ok, seen = ok and o, seen + n
        parts.append('polari: ' + w)
        ctl += sctl
    ctl_ok = all(not passed for _l, passed in ctl)
    return {'ok': ok and ctl_ok, 'route': 'digital-twin', 'frames_compared': seen,
            'why': '%s on %s; negative controls all rejected by the same judge: %s%s' % ('; '.join(parts), variant, ctl_ok, '' if ctl_ok else ' [' + '; '.join(l for l, p in ctl if p) + ' WRONGLY PASSED]'),
            'controls': [{'control': l, 'judged_ok': p} for l, p in ctl],
            'how': 'board.custom.light_variant_twin (firmwarefaults.custom.harness: --pin-at / --inject / --wire, the Python wire reference decoder; ButtonClockState stand-ins for LightState)'}
