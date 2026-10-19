"""
fsc-6 selftest part (called by board.board_light_selftest.run_light): the four Purposes of uno-light-mission on the two LED-sense variants' OWN builds, on the simavr twin.

  - the pure judges (board.custom.light_variant_twin) accept the right frames and reject wrong ones
  - on the twin, each Purpose's own acceptance scenario run for uno-light-sense-poll and uno-light-sense-pcint (ACC.run(..., variant=)) -> outcome passed, stored with variant = that config,
    every negative control rejected, and no temp directory left behind
SKIPS honestly with no twin.
"""
import glob
import os
import tempfile

SENSE = ('uno-light-sense-poll', 'uno-light-sense-pcint')
SCENARIOS = ('initialization-acceptance', 'light-from-button-acceptance', 'light-from-polari-acceptance', 'ensure-polari-observes-hardware-state-acceptance')


def run_variants(check):
    from board.custom import light_twin as LT
    from board.custom import light_variant_twin as LVT
    good = [{'button_presses': k, 'led_on': bool(k % 2), 'status': 'idle'} for k in (0, 0, 1, 1, 2, 3, 3)]
    ev = [{'kind': 'press'}] * 3
    check('fsc-6 JUDGE (button): the right ButtonClockState frames pass; a light stuck off, a count of 2, a status of `commanded` and a missing `press` event are each rejected',
          LVT.judge_presses(good, ev)[0] and not LVT.judge_presses([dict(f, led_on=False) for f in good], ev)[0] and not LVT.judge_presses(good[:-2], ev)[0]
          and not LVT.judge_presses([dict(f, status='commanded') for f in good], ev)[0] and not LVT.judge_presses(good, ev[:2])[0])
    cmd = [{'button_presses': 0, 'led_on': False, 'status': 'idle'}, {'button_presses': 0, 'led_on': True, 'status': 'commanded'}, {'button_presses': 0, 'led_on': False, 'status': 'commanded'}]
    check('fsc-6 JUDGE (command): SET_LED 1 then 0 reported as commanded with no press counted passes; a command that never lit the light, one that counted a press, and a light left on are rejected',
          LVT.judge_commands(cmd)[0] and not LVT.judge_commands(cmd[:1])[0] and not LVT.judge_commands([cmd[0], dict(cmd[1], button_presses=1), cmd[2]])[0] and not LVT.judge_commands(cmd[:2])[0])
    ready, why = LT.engine_ready()
    if not ready:
        check('SKIP fsc-6 (the sense variants on the twin): no simavr twin here - %s' % why, True)
        return
    from firmwarefaults.custom import acceptance as ACC
    from firmwarefaults.custom import sink as S
    before = set(glob.glob(os.path.join(tempfile.gettempdir(), 'fsc6-*'))) | set(glob.glob(os.path.join(tempfile.gettempdir(), 'fsc0b-*')))
    for cfg in SENSE:
        runs = {n: ACC.run(n, 'digital-twin', sink=S.LocalSink(), variant=cfg) for n in SCENARIOS}
        check('fsc-6 TWIN: all four Purposes\' own scenarios pass on %s\'s own build, each stored with variant = %s: %s' % (cfg, cfg, {n.split('-acceptance')[0]: r['outcome'] for n, r in runs.items()}),
              all(r['outcome'] == 'passed' and r['variant'] == cfg and r['scenario'] == n and r['frames_seen'] > 0 for n, r in runs.items()), {n: r['verdict_words'][:160] for n, r in runs.items() if r['outcome'] != 'passed'})
        obs = {n: __import__('json').loads(r['observed_json']).get('controls', []) for n, r in runs.items()}
        check('fsc-6 TWIN: …every negative control through the same judges was rejected (boot 4, button 2, command 1, observe 2)',
              {n: len(c) for n, c in obs.items()} == {SCENARIOS[0]: 4, SCENARIOS[1]: 2, SCENARIOS[2]: 1, SCENARIOS[3]: 2} and not any(x['judged_ok'] for c in obs.values() for x in c), obs)
    after = set(glob.glob(os.path.join(tempfile.gettempdir(), 'fsc6-*'))) | set(glob.glob(os.path.join(tempfile.gettempdir(), 'fsc0b-*')))
    check('fsc-6 TWIN: the twin runners leave no temp directory behind', after <= before, sorted(after - before))
