"""ucd-0d PROBE — PIN-LEVEL forcing and pin-to-pin wiring on the simavr twin (UNO_CORE_DEMO_PLAN.md §5e Q7, §5f's
ucd-0d row, §5g): the SAME five cases as board.board_pinlevel_selftest.pin_parts, run standalone (no module selftest
harness needed) and printed verbatim so a run can be read without re-deriving it:

  (a) N presses on PD2 via --pin-at (falling-edge default build) -> g_presses == N
  (b) NEGATIVE: the same presses with EIMSK poked to 0 -> g_presses == 0 (the pin toggles; nothing is armed)
  (c) EICRA poked to any-edge -> g_presses == 2N
  (d) --wire PD6:PD3 on a firmware that toggles D6 -> PD3 follows it (PIND bit 3 == PIND bit 6; wire-edge lines)
  (e) the same wire against a firmware that ALSO drives PD3 -> {"t":"wire-conflict"} is printed

Skips HONESTLY (exit 0, one SKIP line) when neither the prf-board-engines image nor a local polari-avr-twin is here.

    PYTHONPATH=.:modules python3 tests/board_uno_pinlevel_probe.py     # from polari-framework/
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
    from board import board_pinlevel_selftest as P
    from board.custom import board_engines as be
    where = be.resolve('avr-twin')
    if where['how'] not in ('local-binary', be.LOCAL_IMAGE):
        print('SKIP: no simavr twin on this device (%s) — build the image: docker compose -f polari-rf-node/docker-compose.board-engines.yml build' % where['why'])
        return 0

    print('--- (a)/(b)/(c): uno-button-count, --pin-at presses, EIMSK / EICRA poked ---')
    print('--- (d)/(e): --wire PD6:PD3, a driven D6 and a conflicting D3 ---')
    P.pin_parts(check)
    print('\n%d/%d probe checks passed' % (sum(results), len(results)))
    return 0 if all(results) else 1


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
