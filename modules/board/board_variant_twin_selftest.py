"""board_variant_twin_selftest - fgm-5a: the isotope variants PROVEN ON THE SIMAVR TWIN (SKIPPING honestly without a twin). uno-light-pcint: presses on D4 flip the
light and are reported, the light pin follows, D2 presses change nothing, a bouncing contact counts once. uno-light-analog: A0 driven by the twin's ramp, the
presses match a pure model of the ramp, a pin held high / a switch closed from boot count nothing. uno-sim-rig PWM: SET pwm_duty 25 / 50 / 100 -> OCR0A 63 /
127 / 255. A proof that cannot fail is not a proof, so each check is also run against firmware that must FAIL it. Then the acceptance runner turns each into a
passed ScenarioRun, and the iso-0 catalogue READS those runs and climbs the route to proven-on-twin.

    PYTHONPATH=.:modules python3 -m board.board_variant_twin_selftest      # from polari-framework/ (standalone)
    (called by board.board_selftest.main as run_variant_twin(check))
"""
import shutil
import tempfile
from types import SimpleNamespace

ROUTES = (('uno-light-pcint', 'light-pcint-button-acceptance', 'read-button:pin-change-interrupt'),
          ('uno-light-analog', 'light-analog-button-acceptance', 'read-button:analog-threshold'),
          ('uno-sim-rig', 'sim-rig-pwm-duty-acceptance', 'drive-led:pwm'))


def _hex(variant):
    from board.custom import variant_twin as VT
    work = tempfile.mkdtemp(prefix='fgm5a-st-')
    try:
        row = VT.build(variant, work)
        return row, (open(row['hex_path'], 'rb').read() if row.get('state') == 'built' else b'')
    finally:
        shutil.rmtree(work, ignore_errors=True)


def run_variant_twin(check):
    from board.custom import variant_twin as VT
    check('fgm-5a: the pure ramp model counts the falling crossings (200..4800 mV, 1 s period, 3.6 s, press < 1500, release > 3500 -> 3; a ramp that never '
          'gets low -> 0)',
          VT.expected_presses(200, 4800, 1000, 3.6, 1500, 3500) == 3 and VT.expected_presses(3000, 4800, 1000, 3.6, 1500, 3500) == 0)
    ready, why = VT.engine_ready()
    if not ready:
        check('SKIP fgm-5a (the isotope variants on the twin): no simavr twin here - %s' % why, True)
        return
    proofs = {}
    for variant, scenario, row in ROUTES:
        r = VT.prove(variant)
        proofs[variant] = r
        b = r.get('build') or {}
        check('fgm-5a %s on the twin: every check passed (%s) - flash %s B, static RAM %s B measured by avr-size'
              % (variant, ', '.join(VT.CHECKS[variant]), b.get('flash_bytes'), b.get('ram_bytes')),
              r['ok'] and r['route'] == 'digital-twin' and r.get('frames_compared', 0) > 0 and 0 < b.get('flash_bytes', 0) <= 32256, r['why'])
        for name in VT.CHECKS[variant]:
            check('fgm-5a %s: check %r reported its outcome in words' % (variant, name), ('%s: ' % name) in r['why'] and '[FAILED]' not in r['why'], r['why'][:300])
    # the checks must be able to FAIL: the same stimulus against firmware that does not have the behaviour
    _, int0_hex = _hex('uno-light')
    ok, words, _n = VT.check_presses(int0_hex)
    check('fgm-5a: the D4 press check FAILS on uno-light (the INT0 button on D2 ignores D4): %s' % words[:140], not ok)
    _, pc_hex = _hex('uno-light-pcint')
    ok, words, _n = VT.check_ramp(pc_hex)
    check('fgm-5a: the A0 ramp check FAILS on uno-light-pcint (no analog button): %s' % words[:140], not ok)
    ok, words, _n = VT.check_pwm(int0_hex)
    check('fgm-5a: the PWM duty check FAILS on firmware with no PWM (uno-light): %s' % words[:140], not ok)

    from cmod.custom import isotope_variants as IV
    from firmwarefaults.custom import acceptance as ACC
    from firmwarefaults.custom import sink as S
    sk = S.LocalSink()
    mgr = SimpleNamespace(objectTables={'ScenarioRun': {}}, idList=[], db=None)
    vs = {v['name']: v for v in IV.variants()}
    before = {row: IV.status(vs[row], mgr)['status'] for _, _, row in ROUTES}
    check('fgm-5a: before any run the three routes read compiles', set(before.values()) == {'compiles'}, before)
    for variant, scenario, row in ROUTES:
        run = ACC.run(scenario, 'digital-twin', sink=sk)
        check('fgm-5a: acceptance Scenario %s -> a ScenarioRun outcome passed, measured on the simavr twin (%d frames)' % (scenario, run['frames_seen']),
              run['outcome'] == 'passed' and run['frames_seen'] > 0 and run['variant'] == variant, (run['outcome'], run['verdict_words'][:200]))
        r = sk.tables['ScenarioRun'][run['name']]
        mgr.objectTables['ScenarioRun'][len(mgr.objectTables['ScenarioRun']) + 1] = SimpleNamespace(
            name=r['name'], scenario=r['scenario'], outcome=r['outcome'], ran_at=r['ran_at'], kind='measured', repro_json=r['repro_json'], verdict_words=r['verdict_words'])
    after = {row: IV.status(vs[row], mgr) for _, _, row in ROUTES}
    check('fgm-5a: the iso-0 catalogue READS those ScenarioRuns - all three routes climb compiles -> proven-on-twin, each naming its run',
          all(s['status'] == 'proven-on-twin' and 'ScenarioRun' in s['proof'] for s in after.values()), {k: v['status'] for k, v in after.items()})
    check('fgm-5a: the shipped INT0 route and the GPIO LED are not lifted by them (their Purposes have no passing run here)',
          IV.status(vs['read-button:ext-interrupt'], mgr)['status'] == 'compiles' and IV.status(vs['drive-led:gpio-out'], mgr)['status'] == 'compiles')


if __name__ == '__main__':
    n = [0, 0]

    def _check(label, cond, extra=''):
        n[0] += 1
        n[1] += bool(cond)
        print('  [%s] %s %s' % ('PASS' if cond else 'FAIL', label, '' if cond else extra))
    run_variant_twin(_check)
    print('%d/%d checks passed' % (n[1], n[0]))
    raise SystemExit(0 if n[0] == n[1] else 1)
