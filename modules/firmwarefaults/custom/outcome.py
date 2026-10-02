"""
@module firmwarefaults.custom.outcome

THE DECISION, as pure functions (the selftest feeds them fixture frame sequences): a run's frames + the harness's
forced-event record → outcome failed | passed | inapplicable | undetermined, and the claim status it maps to in his
vocabulary (FIRMWARE_SCENARIO_PLAN.md §1):

    failed       → refuted       (a counterexample: the cycle, the PC, the landed PC, the values)
    passed       → witnessed     (ONE interleaving held — evidence, never a proof)
    inapplicable → inapplicable  (the scenario's PC / ISR / build does not exist here — not defined on this state space)
    undetermined → undetermined  (the forcing condition never held in the window — nothing was tested)

Scenario 1's observable (`uptime-monotone`): uptime_ms going BACKWARDS between consecutive CRC-valid frames = the
torn read surfaced (refuted); monotone with the forced interrupt taken = witnessed.
"""

CLAIM_STATUS = {'failed': 'refuted', 'passed': 'witnessed', 'inapplicable': 'inapplicable', 'undetermined': 'undetermined'}


def backwards(uptimes):
    """[(index, previous, value)] for every frame whose uptime_ms is below the previous frame's."""
    return [(i, uptimes[i - 1], uptimes[i]) for i in range(1, len(uptimes)) if uptimes[i] < uptimes[i - 1]]


def decide_uptime(uptimes, bad_crc=0, forced=None):
    """forced: the harness event dict ({'fired', 'landed', …}) or None for a natural run.
    → {'outcome', 'claim_status', 'words', 'backwards', 'torn_value'}"""
    back = backwards(list(uptimes))
    torn = back[0][1] if back else -1   # the frame BEFORE the drop carries the torn (too large) value
    if forced is not None and not forced.get('fired'):
        return {'outcome': 'undetermined', 'claim_status': 'undetermined', 'backwards': back, 'torn_value': -1,
                'words': 'the forcing condition never held in the window — nothing was tested (not a pass)'}
    if len(uptimes) < 2:
        return {'outcome': 'undetermined', 'claim_status': 'undetermined', 'backwards': back, 'torn_value': -1,
                'words': 'fewer than two frames decoded — no sequence to judge'}
    if back:
        crc = 'every CRC passed (the wire is fine, the VALUE is wrong)' if not bad_crc else '%d frame(s) also failed their CRC' % bad_crc
        return {'outcome': 'failed', 'claim_status': 'refuted', 'backwards': back, 'torn_value': torn,
                'words': 'uptime_ms went backwards %d time(s): %s; %s' % (len(back), ', '.join('%d → %d' % (a, b) for _, a, b in back[:4]), crc)}
    return {'outcome': 'passed', 'claim_status': 'witnessed', 'backwards': back, 'torn_value': -1,
            'words': 'uptime_ms monotone over %d frames%s — one interleaving held (a witness, not a proof)'
                     % (len(uptimes), ' with the forced interrupt taken' if forced and forced.get('landed') else '')}


def align_words(ev, period=16000):
    """sc-2 align-at-pc: what happened to the genuine raise the forced one stood in for."""
    sw = ev.get('swallow', '')
    if sw == 'swallowed':
        return ('no extra tick: the genuine raise %d cycles later (%.2f ms) was swallowed — the tick was ADVANCED by that much, not added'
                % (ev.get('advanced_by_cycles', 0), ev.get('advanced_by_cycles', 0) / 16000.0))
    if sw == 'merged':
        return 'no extra tick: the genuine raise fell inside the forced pending (merged), so nothing was swallowed'
    return 'the genuine raise never came after the forced one (the window ended) — one extra tick is possible here'


def decide_build_refused(build_state, notes=''):
    """Scenario 1b (`build-refused`): the vulnerable firmware must not build."""
    if build_state == 'refused':
        return {'outcome': 'inapplicable', 'claim_status': 'inapplicable', 'backwards': [], 'torn_value': -1,
                'words': 'the build was REFUSED (%s) — the vulnerable firmware cannot exist, so the fault is not defined here'
                         % ((notes.split('error:')[-1].strip().splitlines() or [''])[0][:200] if 'error:' in notes else notes[:160])}
    return {'outcome': 'undetermined', 'claim_status': 'undetermined', 'backwards': [], 'torn_value': -1,
            'words': 'the build went through — the 16-bit head read would have to be forced (sc-1); nothing tested yet'}


def natural_rate(uptimes, final_ms, calls=0, cycles=0, window_cycles=2):
    """Scenario 1 without forcing: torn reads per byte-0 carry. Every tear at the byte-0 carry surfaces as a frame (the torn
    value is 256 ms ahead, past next_ms), so the tears = the backwards drops; carries = floor(final_ms / 256).

    Beside the observed count, the EXPOSURE: the chance a tick at a uniformly random phase lands in the window — only the
    gap between load 1 and load 2 tears at a byte-0 carry (a tick between loads 2/3 or 3/4 leaves byte 0 and byte 1
    consistent there), and the tick is taken before load 2 when its flag rises during load 1's 2 cycles. So exposure =
    window_cycles x calls / cycles (calls = hal_millis entries counted by --fn-cycles)."""
    tears = len(backwards(list(uptimes)))
    carries = int(final_ms) // 256
    exposure = (window_cycles * calls / cycles) if cycles else 0.0
    return {'tears': tears, 'carries': carries, 'rate': (tears / carries) if carries else 0.0, 'exposure_per_carry': round(exposure, 5),
            'calls': calls, 'cycles': cycles, 'window_cycles': window_cycles}


# ---------------------------------------------------------------- sc-1 observables (FIRMWARE_SCENARIO_PLAN.md §3a, §4)
def _r(outcome, words, value=''):
    return {'outcome': outcome, 'claim_status': CLAIM_STATUS[outcome], 'words': words, 'value': value}


def frames_from_tx_log(log, freq=16000000):
    """The twin's --uart-tx-log (u64 cycle + u8 byte per record) → [(ms_at_last_byte, msg_type, seq)] via the reference
    StreamParser fed byte by byte (a frame is dated by its last byte)."""
    from board.custom import packet_ref
    p, out = packet_ref.StreamParser(), []
    for i in range(0, len(log) - 8, 9):
        cyc = int.from_bytes(log[i:i + 8], 'little')
        for mt, dev, seq, payload, ver in p.feed(log[i + 8:i + 9]):
            out.append((cyc * 1000.0 / freq, mt, seq))
    return out


def gaps(times_ms, end_ms):
    """[(from_ms, to_ms, gap_ms)] between consecutive times and from the last to the end of the run."""
    pts = list(times_ms) + [end_ms]
    return [(a, b, b - a) for a, b in zip(pts, pts[1:])]


def decide_telemetry(frames, end_ms, gap_limit_ms, dropped, ack_state=None, request_type=0x7F, lost='the ack'):
    """Scenario 2: frames = [(ms, msg_type, seq)]. dropped = the harness dropped the ack (else nothing was tested)."""
    tel = [t for t, mt, _ in frames if mt == 1]
    req = [t for t, mt, _ in frames if mt == request_type]
    if not dropped:
        return _r('undetermined', '%s was never dropped (no request matched, or the drop index was never reached) — nothing was tested' % lost)
    if not tel:
        return _r('undetermined', 'no telemetry frame decoded — nothing to judge')
    worst = max(gaps(tel, end_ms), key=lambda g: g[2])
    reqs = ', '.join('%.1f' % t for t in req[:4]) or 'none'
    if worst[2] > gap_limit_ms:
        return _r('failed', 'telemetry STOPPED: last frame at %.1f ms, request(s) at %s ms, then nothing for %.1f ms (> %d ms) to the end '
                            'of the run — the firmware never left WAIT (ack state %s)' % (worst[0], reqs, worst[2], gap_limit_ms, ack_state),
                  'last telemetry %.1f ms; silent %.1f ms' % (worst[0], worst[2]))
    if len(req) < 2:
        return _r('undetermined', 'telemetry continued but no retry was seen (requests at %s ms) — the drop did not bite' % reqs)
    st = {2: 'acked', 3: 'gave up (status fault)'}.get(ack_state, 'state %s' % ack_state)
    return _r('passed', '%s was lost and the request went again at %.1f ms (%.1f ms after the first); telemetry never paused '
                        '(worst gap %.1f ms ≤ %d ms); %s — one interleaving held (a witness, not a proof)'
              % (lost, req[1], req[1] - req[0], worst[2], gap_limit_ms, st), 'retry +%.1f ms; worst gap %.1f ms' % (req[1] - req[0], worst[2]))


def decide_presses(presses, expected):
    """Scenario 3: the press counter vs the presses that really happened."""
    if presses is None:
        return _r('inapplicable', 'no press counter in this build (HAL_INT0 off)')
    if presses > expected:
        return _r('failed', 'g_presses = %d for %d press(es): the ringing edge was counted as a press (%d extra)' % (presses, expected, presses - expected),
                  '%d counted / %d pressed' % (presses, expected))
    if presses < expected:
        return _r('failed', 'g_presses = %d for %d press(es): a REAL press was swallowed (the debounce window is too long)' % (presses, expected),
                  '%d counted / %d pressed' % (presses, expected))
    return _r('passed', 'g_presses = %d for %d press(es): the bounce edge was ignored and the real presses counted — a witness, not a proof'
              % (presses, expected), '%d counted / %d pressed' % (presses, expected))


def decide_commands(applied, ideal, sent):
    """Scenario 4: commands the firmware applied vs what an ideal receiver finds in the delivered bytes (the line's floor)."""
    if applied is None:
        return _r('inapplicable', 'no applied-command counter in this build')
    if ideal == 0:
        return _r('undetermined', 'no intact command reached the board — nothing to judge')
    if applied < ideal:
        return _r('failed', '%d of %d command(s) applied while an ideal parser finds %d intact in the same delivered bytes: the parser '
                            'LOST %d the line delivered whole (the rejected span held more than one frame)' % (applied, sent, ideal, ideal - applied),
                  '%d applied / %d intact / %d sent' % (applied, ideal, sent))
    return _r('passed', '%d of %d command(s) applied = every intact one (ideal parser: %d) — no residual loss; a witness, not a proof'
              % (applied, sent, ideal), '%d applied / %d intact / %d sent' % (applied, ideal, sent))


def decide_record(boot, valid, old, new, reset_done):
    """Scenario 5: the record read at boot after a reset mid-write."""
    if not reset_done:
        return _r('undetermined', 'the reset never fired (the write never reached its 3rd byte) — nothing was tested')
    if boot is None:
        return _r('inapplicable', 'no boot record in this build')
    if not valid:
        return _r('failed', 'no valid record at boot: the old one was destroyed and the new one never committed', 'no record')
    if boot not in (old, new):
        return _r('failed', 'the record read at boot is 0x%08X — neither the old 0x%08X nor the new 0x%08X: half-updated (the write did not '
                            'complete and nothing could tell)' % (boot, old, new), '0x%08X (old 0x%08X, new 0x%08X)' % (boot, old, new))
    return _r('passed', 'the record read at boot is 0x%08X = the %s value — the cut write left a consistent record (a witness, not a proof)'
              % (boot, 'old' if boot == old else 'new'), '0x%08X (%s)' % (boot, 'old' if boot == old else 'new'))


def decide_recovery(tel_ms, hang_ms, end_ms, resets):
    """Plan §4 watchdog: after the forced runaway at hang_ms, do frames come back?"""
    if hang_ms is None:
        return _r('undetermined', 'the runaway was never forced — nothing was tested')
    after = [t for t in tel_ms if t > hang_ms]
    wd = [r for r in resets if r.get('wdrf') and not r.get('forced')]
    if not after:
        last = max([t for t in tel_ms if t <= hang_ms] or [0.0])
        return _r('failed', 'HUNG: the runaway at %.1f ms was never left — no frame for %.1f ms to the end of the run (last frame %.1f ms), %d '
                            'reset(s)' % (hang_ms, end_ms - last, last, len(resets)), 'silent %.1f ms' % (end_ms - last))
    return _r('passed', 'the runaway at %.1f ms ended in %d watchdog reset(s) (WDRF set) at %s ms; telemetry resumed at %.1f ms (%.1f ms after the '
                        'hang) — a witness, not a proof' % (hang_ms, len(wd), ', '.join('%.1f' % (r['cycle'] / 16000.0) for r in wd) or '-',
                                                              after[0], after[0] - hang_ms),
              '%d reset(s); back after %.1f ms' % (len(wd), after[0] - hang_ms))


def wilson(k, n, z=1.96):
    """The Wilson score interval for k events in n trials (95 % at z = 1.96) → (p, lo, hi)."""
    import math
    if n <= 0:
        return 0.0, 0.0, 1.0
    k = max(0, min(int(k), int(n)))
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return p, max(0.0, (c - h) / d), min(1.0, (c + h) / d)
