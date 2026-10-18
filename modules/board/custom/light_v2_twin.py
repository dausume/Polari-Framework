"""
@module board.custom.light_v2_twin

fgm-6a: THE v2 LIGHT'S COMMAND CONFIRMATION ON THE SIMAVR TWIN. Builds the variant uno-light-v2 through the shipped pipeline (gen + build, the
board engines seam), drives it deterministically through firmwarefaults.custom.harness (cycle-scheduled, never real-time sleeps), decodes every
frame with the independent Python reference codec (board.custom.packet_ref / grpcbridge.custom.wire_ref), and judges the board's answers with the
backend's own confirmation rules (board.custom.light_confirm.observe_report) on a fake clock = cycle / 16 MHz. Four proofs (his ruling 7.8.3):

  rapid       20 SET_LED commands 20 ms apart (ids 1..20, alternating on/off) -> 20 confirmations, each resolved by a report naming its OWN id with
              the light value it asked for; the light follows every one (toggles 20); a control with the ids scrambled in the tracker confirms nothing
  reboot      the board is RESET (avr_reset: it restarts, boot_session +1, EEPROM kept) (b1) while it is still sending its answer to a command it has
              applied, (b2) while the command is still arriving -> the command is `unknown-resend`, never confirmed; (b3) the same command with no
              reset is confirmed (so the check can fail)
  malformed   no led_on / no command_id / command_id 0 / a truncated payload -> rejected-invalid on the wire (the first with its id echoed, the others
              leaving last_command_id alone), the light unchanged; the next good command is applied
  button      a button press changes the light and leaves last_command_id / last_command_result as they were; a command that never reached the board
              stays unconfirmed through the press's reports (then `unconfirmed` at its timeout), while a command sent after the press is confirmed

`prove(which)` returns the {'ok', 'route', 'why', 'frames_compared', 'build'} shape the acceptance runner turns into a ScenarioRun. Refuses honestly
(route 'refused') with no twin.
"""
import shutil
import tempfile
from types import SimpleNamespace

VARIANT = 'uno-light-v2'
CLASS = 'LightStateV2'
CPS = 16000000.0
N_RAPID = 20
RAPID_GAP = 320000            # 20 ms: the answer (a ~70 B report, ~6 ms) is out before the next command arrives
START = 1600000               # 100 ms in, past the first report
CMD_END = 3200000             # a single command's slot, ECHO_CUT after it the reset lands mid-answer
CMD_BYTES_CYCLES = 36000      # a partial-mask command is ~26 B: ~2.3 ms of UART byte times (~36 k cycles)
ECHO_CUT = 60000              # 3.75 ms after the command started: the command is in, applied, and the answer is half sent
EARLY_CUT = 12000             # 0.75 ms in: the command is still arriving
RUN_TAIL = 3200000
PRESS_HOLD = 80000
CHECKS = ('rapid', 'reboot', 'malformed', 'button')


def _spec():
    from board.custom import gen
    from board.custom.compat import wire_spec
    fmap = gen.pinned_contract(CLASS)[0]['field_map']
    return fmap, wire_spec(None, CLASS, fmap)


def cmd_frame(spec, seq, **vals):
    """A command frame PRESENCE-MASKED to exactly the fields given (SET_LED = command_id + led_on)."""
    from board.custom import packet_ref
    from grpcbridge.custom import wire_ref
    return packet_ref.frame(1, 0, seq, wire_ref.encode(spec, vals, present=list(vals)), version=spec['wire_version'])


def truncated_frame(spec, seq):
    """A frame whose CRC is good but whose payload says command_id is present and then ends: the board's decode fails."""
    from board.custom import packet_ref
    full = cmd_frame(spec, seq, command_id=9)   # prelude + 8 bytes of command_id ...
    payload = bytes(full[10:-4])[:5]            # ... cut to the prelude + 3 bytes
    return packet_ref.frame(1, 0, seq, payload, version=spec['wire_version'])


def decode(uart):
    from board.custom import packet_ref
    fmap, spec = _spec()
    p = packet_ref.StreamParser()
    out = []
    for mt, dev, seq, payload, ver in p.feed(bytes(uart)):
        if mt == 1:
            try:
                out.append(packet_ref.decode_any(fmap, payload, ver, spec))
            except ValueError:
                pass
    return out, p.bad_crc


def _argv(seconds, extra):
    return ['--hex', 'firmware.hex', '--mcu', 'atmega328p', '--freq', '16000000', '--free', '--seconds', '%g' % seconds,
            '--status-ms', '0', '--uart-out', 'uart.bin'] + extra


def build(work):
    from board.custom import gen, build as B
    gen.gen('uno', None, work, variant=VARIANT)
    return B.build('uno', work)


def run(hex_bytes, commands, press=(), reset_at=None, tail=RUN_TAIL):
    """commands: [(cycle, filename-bytes)] injected at their cycle; press: cycles of D2 presses; reset_at: a cycle (or None).
    -> (harness result, decoded frames, bad_crc)."""
    from firmwarefaults.custom import harness
    files, extra, end = {}, [], 0
    for i, (cycle, data) in enumerate(commands):
        files['c%02d.bin' % i] = data
        extra += ['--inject', 'c%02d.bin@%d' % (i, cycle)]
        end = max(end, cycle)
    for c in press:
        extra += ['--pin-at', 'cycle=%d,pin=PD2,level=0' % c, '--pin-at', 'cycle=%d,pin=PD2,level=1' % (c + PRESS_HOLD)]
        end = max(end, c + PRESS_HOLD)
    if reset_at is not None:
        extra += ['--reset-at', 'cycle=%d' % reset_at]
        end = max(end, reset_at)
    r = harness.run_files(_argv((end + tail) / CPS, extra), hex_bytes, files, timeout=180)
    frames, bad = decode(r['uart'])
    return r, frames, bad


def _tracker(cmds, session):
    """The backend's ledger rows for commands [(id, led_on, sent_cycle)] sent into board session `session` (LightCommand-shaped)."""
    return [SimpleNamespace(command_id=i, led_on_requested=on, sent_at=c / CPS, device_session_at_send=session, backend_session=1, status='pending',
                            result='', resolved_at=0.0, timeout_s=2.0, detail='') for i, on, c in cmds]


def _replay(tracker, frames, t0, step=1.0 / 10):
    """Feed the decoded reports to the tracker in stream order; returns {command_id: (status, index of the resolving report)}."""
    res = {}
    for k, f in enumerate(frames):
        for c in __import__('board.custom.light_confirm', fromlist=['x']).observe_report(
                tracker, {'boot_session': f.get('boot_session'), 'last_command_id': f.get('last_command_id'), 'last_command_result': f.get('last_command_result')},
                t0 + k * step):
            res[c.command_id] = (c.status, k)
    return res


def _session(frames):
    return int(frames[0]['boot_session']) if frames else 0


def _last(frames):
    return frames[-1] if frames else {}


# ------------------------------------------------------------------ (a) rapid
def check_rapid(hex_bytes):
    _, spec = _spec()
    cmds = [(START + k * RAPID_GAP, cmd_frame(spec, k + 1, command_id=k + 1, led_on=bool((k + 1) % 2))) for k in range(N_RAPID)]
    end = cmds[-1][0]
    r, fr, bad = run(hex_bytes, cmds)
    sess = _session(fr)
    tr = _tracker([(k + 1, bool((k + 1) % 2), cmds[k][0]) for k in range(N_RAPID)], sess)
    res = _replay(tr, fr, 0.0)
    by_id = {}
    for f in fr:
        by_id.setdefault(int(f.get('last_command_id') or 0), f)
    all_confirmed = len(res) == N_RAPID and all(s == 'confirmed' for s, _ in res.values())
    own = all(res[i][0] == 'confirmed' and fr[res[i][1]].get('last_command_id') == i and bool(fr[res[i][1]].get('led_on')) == bool(i % 2)
              and fr[res[i][1]].get('last_command_result') == 'applied' for i in res)
    order = [res[i][1] for i in range(1, N_RAPID + 1) if i in res]
    last = _last(fr)
    # control: the same reports against a ledger whose ids are shifted by one (a command that was never sent) -> the shifted ids that were
    # never answered (21) stay pending; and a ledger sent into ANOTHER boot session confirms nothing
    ctl_ids = _replay(_tracker([(i + 1, True, 0) for i in range(N_RAPID)], sess), fr, 0.0)
    ctl_sess = _replay(_tracker([(i + 1, True, 0) for i in range(N_RAPID)], sess + 7), fr, 0.0)
    ok = (r['ok'] and bad == 0 and bool(fr) and all_confirmed and own and order == sorted(order) and last.get('toggles') == N_RAPID
          and last.get('last_command_id') == N_RAPID and last.get('source') == 'command' and len(ctl_ids) == N_RAPID
          and all(s == 'unknown-resend' for s, _ in ctl_sess.values()))
    return ok, ('%d SET_LED commands 20 ms apart (ids 1..%d, alternating on/off): %d confirmed, each by a report naming its own id with the light value '
                'it asked for and result applied (in order: %s); last report toggles=%s last_command_id=%s source=%s; control: the same reports against '
                'a ledger from another boot session confirm 0 (%d unknown-resend)'
                % (N_RAPID, N_RAPID, sum(1 for s, _ in res.values() if s == 'confirmed'), order == sorted(order), last.get('toggles'),
                   last.get('last_command_id'), last.get('source'), sum(1 for s, _ in ctl_sess.values() if s == 'unknown-resend'))), len(fr)


# ------------------------------------------------------------------ (b) reboot
def check_reboot(hex_bytes):
    _, spec = _spec()
    c1 = CMD_END
    cmd = [(c1, cmd_frame(spec, 1, command_id=1, led_on=True))]
    out, ok, parts, seen = {}, True, [], 0
    for label, reset in (('b1 reset while the answer is half sent', c1 + ECHO_CUT), ('b2 reset while the command is arriving', c1 + EARLY_CUT),
                         ('b3 control: no reset', None)):
        r, fr, bad = run(hex_bytes, cmd, reset_at=reset)
        sess = _session(fr)
        tr = _tracker([(1, True, c1)], sess)
        res = _replay(tr, fr, 0.0)
        sessions = sorted({int(f['boot_session']) for f in fr})
        seen += len(fr)
        status = res.get(1, ('pending', -1))[0]
        want = 'confirmed' if reset is None else 'unknown-resend'
        good = r['ok'] and status == want and (reset is None and len(sessions) == 1 or reset is not None and len(sessions) == 2 and sessions[1] == sessions[0] + 1)
        if reset is not None:   # no report in the new boot ever names command 1
            good = good and not any(f.get('last_command_id') == 1 for f in fr)   # the answer was cut: no report, in either boot, names command 1
        ok = ok and good
        parts.append('%s: boot sessions %s, command 1 -> %s%s' % (label, sessions, status, '' if good else ' [MISMATCH, wanted %s]' % want))
        out[label[:2]] = status
    return ok, '; '.join(parts), seen


# ------------------------------------------------------------------ (c) malformed
def check_malformed(hex_bytes):
    _, spec = _spec()
    t = [START + k * RAPID_GAP * 3 for k in range(6)]
    cmds = [(t[0], cmd_frame(spec, 1, command_id=5)),                       # no led_on: rejected-invalid WITH its id
            (t[1], cmd_frame(spec, 2, led_on=True)),                        # no command_id (a v1-style SET_LED): rejected-invalid, id left alone
            (t[2], cmd_frame(spec, 3, command_id=0, led_on=True)),          # id 0 is "none"
            (t[3], truncated_frame(spec, 4)),                               # cannot be decoded
            (t[4], cmd_frame(spec, 5, command_id=6, led_on=True))]          # a good one: applied
    r, fr, bad = run(hex_bytes, cmds)
    sess = _session(fr)
    tr = _tracker([(5, True, t[0]), (6, True, t[4])], sess)
    res = _replay(tr, fr, 0.0)

    def seen(pred):
        return [f for f in fr if pred(f)]
    first = seen(lambda f: f.get('last_command_id') == 5 and f.get('last_command_result') == 'rejected-invalid')
    toggles_before_good = max([f.get('toggles') or 0 for f in fr if f.get('last_command_id') != 6] or [0])
    rejected_unnamed = seen(lambda f: f.get('last_command_id') == 5 and f.get('last_command_result') == 'rejected-invalid' and f.get('toggles') == 0)
    ok = (r['ok'] and bad == 0 and bool(first) and res.get(5, ('', 0))[0] == 'rejected-invalid' and res.get(6, ('', 0))[0] == 'confirmed'
          and toggles_before_good == 0 and _last(fr).get('toggles') == 1 and _last(fr).get('last_command_id') == 6 and bool(_last(fr).get('led_on'))
          and len(rejected_unnamed) >= 4)
    return ok, ('four malformed commands (no led_on / no command_id / id 0 / truncated payload): the first answered rejected-invalid with its id 5 '
                '(ledger: %s), the other three leave last_command_id at 5 with result rejected-invalid, the light stays off (toggles %d before the good '
                'one); the good command id 6 is then %s and the light is on (toggles %s)'
                % (res.get(5, ('unseen',))[0], toggles_before_good, res.get(6, ('unseen',))[0], _last(fr).get('toggles'))), len(fr)


# ------------------------------------------------------------------ (d) a button press does not confirm
def check_button(hex_bytes):
    from board.custom import light_confirm as LC
    _, spec = _spec()
    c1, press, c3 = START, START + 2400000, START + 7200000
    # command 1 reaches the board; command 2 is "sent" by the backend but never reaches it (lost); the button is pressed; command 3 is sent after
    cmds = [(c1, cmd_frame(spec, 1, command_id=1, led_on=True)), (c3, cmd_frame(spec, 2, command_id=3, led_on=True))]
    r, fr, bad = run(hex_bytes, cmds, press=[press])
    sess = _session(fr)
    tr = _tracker([(1, True, c1), (2, True, press - 1000), (3, True, c3)], sess)
    between = [f for f in fr if f.get('last_command_id') != 3]       # every report up to the moment command 3 is answered
    after = [f for f in between if f.get('source') == 'button']      # the reports the press caused
    _replay(tr, between, 0.0)
    cmd = {c.command_id: c for c in tr}
    st2_after_press = cmd[2].status
    LC.expire(tr, press / CPS + 5.0)
    st2 = cmd[2]
    unchanged = bool(after) and all(f.get('last_command_id') == 1 and f.get('last_command_result') == 'applied' for f in after)
    _replay(tr, fr, 0.0)
    ok = (r['ok'] and bad == 0 and unchanged and after[0].get('toggles') == 2 and st2_after_press == 'pending' and st2.status == 'unconfirmed'
          and 'no report named command 2' in st2.detail and cmd[3].status == 'confirmed' and cmd[1].status == 'confirmed'
          and _last(fr).get('last_command_id') == 3 and _last(fr).get('toggles') == 3)
    return ok, ('command 1 confirmed; the button press (toggles %s, source button, %d reports) left last_command_id %s result %s unchanged; the lost command 2 '
                'stayed %s through those reports and became %s at its timeout ("%s"); command 3, sent after the press, is %s'
                % (after[0].get('toggles') if after else None, len(after), after[0].get('last_command_id') if after else None,
                   after[0].get('last_command_result') if after else None, st2_after_press, st2.status, st2.detail[:50], cmd[3].status)), len(fr)


FNS = {'rapid': check_rapid, 'reboot': check_reboot, 'malformed': check_malformed, 'button': check_button}


def engine_ready():
    from board.custom import light_twin as LT
    return LT.engine_ready()


def prove(which='all', mode='digital-twin'):
    """-> {'ok', 'route', 'why', 'frames_compared', 'how', 'build': {...}} - ONE build, the named check(s) ('all' = every proof)."""
    if mode == 'hardware':
        return {'ok': False, 'route': 'refused', 'why': 'the v2 light --hardware proof is not wired yet (the UNO is not attached)'}
    ready, why = engine_ready()
    if not ready:
        return {'ok': False, 'route': 'refused', 'why': 'no simavr twin here: %s' % why}
    names = CHECKS if which == 'all' else (which,)
    work = tempfile.mkdtemp(prefix='fgm6a-')
    try:
        row = build(work)
        if row.get('state') != 'built':
            return {'ok': False, 'route': 'digital-twin', 'why': '%s did not build: %s' % (VARIANT, row.get('notes'))}
        hex_bytes = open(row['hex_path'], 'rb').read()
        ok, parts, seen = True, [], 0
        for n in names:
            good, words, k = FNS[n](hex_bytes)
            ok, seen = ok and good, seen + k
            parts.append('%s: %s%s' % (n, words, '' if good else ' [FAILED]'))
        return {'ok': ok, 'route': 'digital-twin', 'why': '; '.join(parts), 'frames_compared': seen,
                'build': {'flash_bytes': row['flash_bytes'], 'ram_bytes': row['ram_bytes'], 'size_text': row['size_text'], 'size_data': row['size_data'],
                          'size_bss': row['size_bss'], 'hex_sha256': row['artifact_sha256']},
                'how': 'board.custom.light_v2_twin (firmwarefaults.custom.harness: --inject / --reset-at / --pin-at, the Python wire reference decoder, '
                       'board.custom.light_confirm.observe_report on a cycle clock)'}
    finally:
        shutil.rmtree(work, ignore_errors=True)
