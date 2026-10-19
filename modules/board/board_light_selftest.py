"""board_light_selftest — ucd-light (UNO_CORE_DEMO_PLAN.md §5i): THE LIGHT TEST's wire struct and firmware. LightState exists and is
registered like the other wire classes, its pinned contract renders the C header with the generator every class goes through, the
variant uno-light resolves to just what the test needs (LED, commands, button — no sense pin, no event queue is used), and — on the
simavr twin, SKIPPING honestly without one — a press flips the light and reports source=button, SET_LED switches it and reports
source=command, and the acceptance runner turns both into passed ScenarioRuns.

    PYTHONPATH=.:modules python3 -m board.board_light_selftest      # from polari-framework/ (standalone)
    (called by board.board_selftest.main as run_light(check))
"""
import re
import tempfile


def run_light(check):
    from board.board_basis import BOARD_CLASSES, LightState
    from board.board_seed import BOARD_SEED_PAIRS
    from board.custom import gen, compat, variants as V
    s = LightState(name='uno-light', seq=3, boot_session=2, led_on=True, toggles=1, source='button', status='active')
    check('ucd-light: LightState constructs with the 7 fields of the struct (name, seq, boot_session, led_on, toggles, source, status)',
          (s.name, s.seq, s.boot_session, s.led_on, s.toggles, s.source, s.status) == ('uno-light', 3, 2, True, 1, 'button', 'active'))
    # 2026-10-11: ONE placeholder row ('uno-light') so the screen's indicator exists before the board's first report;
    # only `name` is code-owned (_converge) — the board's values are never overwritten by a later boot.
    light_seeds = [rows for n, _, rows in BOARD_SEED_PAIRS if n == 'LightState']
    check('ucd-light: LightState is registered in BOARD_CLASSES with ONE placeholder row (uno-light) whose fields the board owns '
          '(nothing but the name converges)',
          LightState in BOARD_CLASSES and len(light_seeds) == 1 and [r['name'] for r in light_seeds[0]] == ['uno-light']
          and light_seeds[0][0].get('_converge') == [] and light_seeds[0][0]['led_on'] is False)
    c, _ = gen.pinned_contract('LightState')
    check('ucd-light: pinned contract v1 — 7 fields, tags alphabetical (the framework rule), led_on a bool that doubles as the command',
          c['contract_version'] == 1 and len(c['field_map']['fields']) == 7 and compat.tag_order(c['field_map']) == sorted(c['field_map']['fields'])
          and c['field_map']['fields']['led_on']['proto_type'] == 'bool' and c['msg_type'] == 1)
    text, prov = gen.header('LightState', msg_type=1)
    check('ucd-light: the C header is GENERATED from the pinned contract (target avr, msg_type 1) with the source and status enums',
          prov['source'] == 'pinned' and 'target avr' in text and 'LIGHTSTATE_MSG_TYPE 1u' in text and 'LIGHTSTATE_SOURCE_BUTTON = 2' in text
          and 'LIGHTSTATE_SOURCE_COMMAND = 1' in text and 'LIGHTSTATE_STATUS_ACTIVE = 2' in text and 'LIGHTSTATE_F_LED_ON' in text)
    v = V.find('uno-light')
    r = V.resolve(v)
    check('ucd-light: variant uno-light resolves — app light, one class (LightState), LED + commands + button, no sense pin, no PWM, no ADC',
          r['app'] == 'light' and r['classes'] == ['LightState'] and r['features']['button'] and r['features']['led'] and r['features']['commands']
          and not (r['features']['sense'] or r['features']['pwm'] or r['features']['adc']), r['features'])
    try:
        V.resolve(dict(v, features_json='{"led": true, "commands": true, "button": true, "sense": true}'))
        refused = False
    except V.VariantRefused:
        refused = True
    check('ucd-light: the light app refuses a sense pin (no INT1 in the light test) — named, not ignored', refused)
    work = tempfile.mkdtemp(prefix='ucd-light-gen-')
    row = gen.gen('uno', work=work, variant='uno-light', variant_rows=[v])
    cfg = open(row['project_dir'] + '/board_config.h').read()
    check('ucd-light: board_config.h for uno-light turns on INT0 (the button on D2, debounced) and not INT1',
          '#define HAL_INT0     1' in cfg and 'HAL_INT1' not in cfg and '#define BUTTON_PIN   2' in cfg and '#define LED_PIN      6' in cfg)

    from board.custom import light_twin as LT
    ready, why = LT.engine_ready()
    if not ready:
        check('SKIP ucd-light (the light on the twin): no simavr twin here — %s' % why, True)
        return
    work = tempfile.mkdtemp(prefix='ucd-light-twin-')
    brow = LT.build(work)
    check('ucd-light: uno-light builds (plain C, avr-libc, within the cited flash/RAM limits)',
          brow['state'] == 'built' and 0 < brow['flash_bytes'] <= 32256 and 0 < brow['ram_bytes'] <= 2048, '%s: %s/%s' % (brow.get('notes'), brow.get('flash_bytes'), brow.get('ram_bytes')))
    hexb = open(brow['hex_path'], 'rb').read()
    res, frames, bad = LT.run_presses(hexb)
    ok, why = LT.judge_presses(frames)
    check('ucd-light (button up): %d presses on D2 -> every press flips led_on, toggles == presses, source == button; no bad-CRC frames' % LT.N_PRESSES,
          res['ok'] and bad == 0 and ok, why)
    pre = [f for f in frames if f.get('toggles') == 0]
    check('…before the first press the frames say led_on false, source unknown/empty, status idle (nothing has changed yet)',
          bool(pre) and all(not f['led_on'] and f['status'] == 'idle' for f in pre), pre[:1])
    check('…boot_session is constant across one run and seq climbs by one per frame',
          len({f['boot_session'] for f in frames}) == 1 and [f['seq'] for f in frames] == list(range(frames[0]['seq'], frames[0]['seq'] + len(frames))))
    res, frames, bad = LT.run_commands(hexb)
    ok, why = LT.judge_commands(frames)
    check('ucd-light (command down): SET_LED 1 then SET_LED 0 -> led_on follows, toggles counts both, source == command; no bad-CRC frames',
          res['ok'] and bad == 0 and ok, why)
    from firmwarefaults.custom import acceptance as ACC
    from firmwarefaults.custom import sink as S
    for name in ('light-from-button-acceptance', 'light-from-polari-acceptance'):
        run = ACC.run(name, 'digital-twin', sink=S.LocalSink())
        check('ucd-light: acceptance Scenario %s -> a ScenarioRun outcome passed (measured on the simavr twin)' % name,
              run['outcome'] == 'passed' and run['frames_seen'] > 0, (run['outcome'], run['verdict_words']))
    from board.custom.selftest_light_variants import run_scl, run_variants      # fsc-6 / scl: the struct-driven proof, then the same Purposes on the two LED-sense variants' own builds
    run_scl(check)
    run_variants(check)


if __name__ == '__main__':
    n = [0, 0]

    def _check(label, cond, extra=''):
        n[0] += 1
        n[1] += bool(cond)
        print('  [%s] %s %s' % ('PASS' if cond else 'FAIL', label, '' if cond else extra))
    run_light(_check)
    print('%d/%d checks passed' % (n[1], n[0]))
    raise SystemExit(0 if n[0] == n[1] else 1)
