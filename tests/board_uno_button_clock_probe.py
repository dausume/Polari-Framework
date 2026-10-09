"""ucd-0e2 PROBE — the button-clock firmware's six tasks, proven on the simavr twin (UNO_CORE_DEMO_PLAN.md §1/§5f/§5g):
the SAME six cases as board.board_button_clock_twin_selftest.button_clock_parts, run standalone (no module selftest
harness needed) and printed verbatim so a run can be read without re-deriving it:

  (a) N presses on PD2 + --wire PD6:PD3 -> button_presses == N, sense_rises + sense_falls == N, led_on == (N odd),
      N x 2 events (press + led_on/off) + N sense events, in order
  (b) a small event_queue_len build -> one press overflows it; dropped_events reports exactly what overflowed
  (c) SET_TIME twice -> clock_synced, epoch tracks the host, drift_ms only from the SECOND sync
  (d) SNAPSHOT -> an out-of-band state frame + the queued events, right away
  (e) boot_session: constant within a run, differs when the EEPROM's prior value differs
  (f) NEGATIVE: the same presses with NO --wire -> sense_rises + sense_falls stay 0

Skips HONESTLY (exit 0, one SKIP line) when neither the prf-board-engines image nor a local polari-avr-twin is here.

    PYTHONPATH=.:modules python3 tests/board_uno_button_clock_probe.py     # from polari-framework/
"""
import os
import sys

FRAMEWORK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, FRAMEWORK); sys.path.insert(0, os.path.join(FRAMEWORK, 'modules'))
os.chdir(FRAMEWORK)

results = []


def check(label, cond, extra=''):
    results.append(bool(cond))
    print(('PASS' if cond else 'FAIL') + ': ' + label + (('  [%s]' % (extra,)) if extra else ''))


def main(argv):
    from board import board_button_clock_twin_selftest as T
    from board.custom import board_engines as be
    where = be.resolve('avr-twin')
    if where['how'] not in ('local-binary', be.LOCAL_IMAGE):
        print('SKIP: no simavr twin on this device (%s) — build the image: docker compose -f polari-rf-node/docker-compose.board-engines.yml build' % where['why'])
        return 0

    print('--- (a)/(f): uno-button-clock, N presses via --pin-at, --wire PD6:PD3 / no wire ---')
    print('--- (b): a 2-slot event queue, drop-oldest ---')
    print('--- (c)/(d): SET_TIME x2 (drift from the 2nd), SNAPSHOT ---')
    print('--- (e): boot_session via the EEPROM counter ---')
    T.button_clock_parts(check)
    print('\n%d/%d probe checks passed' % (sum(results), len(results)))
    return 0 if all(results) else 1


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
