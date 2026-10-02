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
