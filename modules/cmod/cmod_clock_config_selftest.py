"""cmod_clock_config_selftest - cfg-1 (AI-Notes/plans/CATOM_CONFIG_PLAN.md "The clock group in detail", part 1): the clock group's first checks on the cfg-0
registry, judged in a Bench Solution: the UNO light's serial link at 115200 against its own clock (the CSTCE16M0V53-R0 resonator, a ClockSource row) and its
far end (the 16U2 running arduino-usbserial, a ClockPeer row). The shipped matched divisor (U2X 1, UBRR 16, +2.1 %) decodes both ways with -2.50 .. +2.56 %
of clock error to spare against the +-1.0 % band, but its divisor error is beyond the receiver's recommended +-1.5 % share: COMPROMISE, chosen
automatically; normal mode (U2X 0, UBRR 8, -3.5 %) needs the chip 1.9 .. 8.6 % fast to decode both ways, so at nominal it is INVALID (the 16U2's bytes come
5.9 % fast for it, as tmp-6 measured). The tick is exactly 1 kHz. A person's ClockSource row is read over the seed; an unrated temperature is said; the
rows are seeded; the manifests.

    PYTHONPATH=.:modules python3 -m cmod.cmod_clock_config_selftest      # from polari-framework/
"""
import json
import sys
import types

passed = total = 0
BS = 'uno-light-on-desk'
CATOM = 'report-state'


def check(label, cond, extra=''):
    global passed, total
    total += 1
    passed += bool(cond)
    print('  [%s] %s %s' % ('\033[0;32mPASS\033[0m' if cond else '\033[0;31mFAIL\033[0m', label, extra if not cond else ''))


def _manager():
    return types.SimpleNamespace(objectTables={}, idList=[], db=None, noteTreeMutation=lambda *a, **k: None)


def _seed(m):
    from board.board_seed import SEED_BENCH_CONDITIONS, SEED_BENCH_SOLUTIONS, SEED_CLOCK_PEERS, SEED_CLOCK_SOURCES
    from cmod.cmod_seed import SEED_CLOCK_OPTIONS
    from cmod.custom import config_rows as R
    for cls, rows in (('BenchConditions', SEED_BENCH_CONDITIONS), ('BenchSolution', SEED_BENCH_SOLUTIONS), ('ClockSource', SEED_CLOCK_SOURCES), ('ClockPeer', SEED_CLOCK_PEERS),
                      ('ConfigOption', SEED_CLOCK_OPTIONS)):
        for r in rows:
            R.upsert(m, cls, r['name'], **{k: v for k, v in r.items() if k != 'name'})


def main():
    from cmod.custom import catom_config as CF
    from cmod.custom import clock_checks as CK
    from cmod.custom import config_checks as CC
    from cmod.custom import config_rows as R
    m = _manager()
    _seed(m)
    check('THE ROWS: three ClockSource rows seeded from timing_drift.CLOCKS (the resonator names the UNO board), two ClockPeer rows (the 16U2 running arduino-usbserial '
          'names the UNO; an exact peer as a knob), two ConfigOption rows on report-state\'s clock group',
          sorted(r['name'] for r in R.rows(m, 'ClockSource')) == ['atmega328p-rc-factory', 'atmega328p-rc-user', 'cstce16m0v53-r0']
          and R.get(m, 'ClockSource', 'cstce16m0v53-r0')['boards'] == 'arduino-uno-r3' and R.get(m, 'ClockPeer', 'uno-16u2-usbserial')['divisor_rule'] == 'arduino-usbserial'
          and len(R.rows(m, 'ConfigOption', catom=CATOM, group='clock')) == 2)
    check('THE CHECKS registered on the cfg-0 registry for the clock group: serial-link and tick, both closed form (layer 1)',
          [(c['layer'], c['check']) for c in CC.checks('clock')] == [(1, 'serial-link'), (1, 'tick')], CC.checks('clock'))
    cc = CK.context(m, BS)
    check('THE CLOCK CONTEXT of the Bench Solution: the board (the variant uno-light stands in for the Firmware Solution: arduino-uno-r3), its clock row, its peer row, '
          'the ambient range from its conditions (18 .. 30 C)', cc['board'] == 'arduino-uno-r3' and cc['clock'] == 'cstce16m0v53-r0' and cc['peer']['name'] == 'uno-16u2-usbserial'
          and cc['ambient'] == (18.0, 30.0) and cc['words'] == [], cc)
    v = CF.evaluate(m, BS, CATOM)
    g = next(x for x in v['groups'] if x['group'] == 'clock')
    by = {o['option'].split(':')[-1]: o for o in g['options']}
    u1, u0 = by['u2x1-ubrr16'], by['u2x0-ubrr8']
    s1 = next(c for c in u1['checks'] if c['check'] == 'serial-link')
    check('PROOF: the shipped matched divisor is a COMPROMISE - decodes both ways with -2.50 .. +2.56 % of chip clock error (the decode band) against the resonator\'s '
          '+-1.0 % band at 18 .. 30 C, but its +2.12 % divisor error is beyond the receiver\'s recommended +-1.5 % share; the margin is the 1.5 % left',
          u1['verdict'] == 'compromise' and s1['outcome'] == 'compromise' and 'beyond the receiver\'s recommended +-1.5 % share' in s1['why'] and abs(s1['margin'] - 1.5) < 0.02
          and '-2.50 .. +2.56 %' in s1['evidence'] and 'UBRR0 16, U2X0 1' in s1['evidence'] and '117647 Bd' in s1['evidence'], (u1['verdict'], s1))
    s0 = next(c for c in u0['checks'] if c['check'] == 'serial-link')
    check('PROOF: normal mode is INVALID against the 16U2 - the decode band +1.91 .. +8.60 % does not contain the nominal clock: the far end runs +5.9 % against '
          'UBRR 8 (-3.55 %); the link is what it gives up', u0['verdict'] == 'invalid' and s0['outcome'] == 'invalid' and '+5.9 %' in s0['why'] and s0['gives_up'] == 'the link'
          and '+1.91 .. +8.60 %' in s0['evidence'], (u0['verdict'], s0))
    t1 = next(c for c in u1['checks'] if c['check'] == 'tick')
    check('THE TICK is ideal on the shipped option: exactly 1 kHz at nominal (16 MHz / 128 / 125, hal.c), drifting only as the clock does (+-1 %); on the invalid option it is '
          'recorded as skipped (the cheaper check settled it)', t1['outcome'] == 'ideal' and '1000.0000 Hz' in t1['evidence'] and '+-1 %' in t1['why']
          and next(c for c in u0['checks'] if c['check'] == 'tick')['outcome'] == 'skipped', (t1, u0['checks']))
    check('CHOSEN AUTOMATICALLY: the compromise (the only option that works) is the configuration\'s choice, with the score and the reason in words',
          g['chosen'].endswith(':u2x1-ubrr16') and g['chosen_by'] == 'auto' and 'compromise' in g['why'], (g.get('chosen'), g.get('chosen_by'), g.get('why')))
    R.upsert(m, 'ClockSource', 'cstce16m0v53-r0', initial_pct=1.5, notes='a person tightened nothing: a worse part for the test')
    v2 = CF.evaluate(m, BS, CATOM)
    s1b = next(c for o in next(x for x in v2['groups'] if x['group'] == 'clock')['options'] if o['option'].endswith('u2x1-ubrr16') for c in o['checks'] if c['check'] == 'serial-link')
    check('A PERSON\'S ClockSource row is what timing_drift reads: widen the resonator\'s initial tolerance to 1.5 % (band +-2.0 %) and the margin shrinks to 0.5 %, '
          'still a compromise', s1b['outcome'] == 'compromise' and abs(s1b['margin'] - 0.5) < 0.02 and 'initial 1.5' in s1b['evidence'], s1b)
    R.upsert(m, 'ClockSource', 'cstce16m0v53-r0', initial_pct=3.0)
    v3 = CF.evaluate(m, BS, CATOM)
    s1c = next(c for o in next(x for x in v3['groups'] if x['group'] == 'clock')['options'] if o['option'].endswith('u2x1-ubrr16') for c in o['checks'] if c['check'] == 'serial-link')
    check('A band wider than the decode band (+-3.5 %) is INVALID at the edge of the conditions: framing errors, said', s1c['outcome'] == 'invalid' and 'framing errors' in s1c['why'], s1c)
    R.upsert(m, 'ClockSource', 'cstce16m0v53-r0', initial_pct=0.5)
    R.upsert(m, 'BenchConditions', 'room', ambient_min_c=-30.0)
    v4 = CF.evaluate(m, BS, CATOM)
    s1d = next(c for o in next(x for x in v4['groups'] if x['group'] == 'clock')['options'] if o['option'].endswith('u2x1-ubrr16') for c in o['checks'] if c['check'] == 'serial-link')
    check('AN UNRATED TEMPERATURE (-30 C, below the resonator\'s -20 .. +80 C bound) is a compromise that SAYS unrated, never a guessed band',
          s1d['outcome'] == 'compromise' and 'unrated' in s1d['why'] and '-20 .. 80 C' in s1d['why'], s1d)
    R.upsert(m, 'BenchConditions', 'room', ambient_min_c=18.0)
    R.upsert(m, 'ClockPeer', 'uno-16u2-usbserial', divisor_rule='exact')
    v5 = CF.evaluate(m, BS, CATOM)
    s0e = next(c for o in next(x for x in v5['groups'] if x['group'] == 'clock')['options'] if o['option'].endswith('u2x0-ubrr8') for c in o['checks'] if c['check'] == 'serial-link')
    check('AGAINST AN EXACT PEER (the knob) normal mode is STILL invalid, by a hair: the chip\'s own -3.55 % divisor plus the resonator\'s -1 % band reaches -4.55 %, '
          '0.01 % past the U2X 0 receiver window\'s -4.54 % (Table 20-2) - framing errors at the cold edge of the conditions, said; the window is the chip\'s own',
          s0e['outcome'] == 'invalid' and 'edge of the conditions' in s0e['why'] and -0.02 < s0e['margin'] < 0 and 'exact peer' in s0e['evidence'], s0e)
    from cmod.cmod_catom_config_api import CatomConfigAPI
    api = CatomConfigAPI(polServer=None, manager=m)
    resp = types.SimpleNamespace(status='200 OK', media=None)
    req = types.SimpleNamespace(get_param=lambda k: None, bounded_stream=types.SimpleNamespace(read=lambda: b'{}'))
    try:
        api.on_post_evaluate(req, resp, BS, CATOM)
        ok = resp.media and resp.media.get('ok') and any(x['group'] == 'clock' for x in resp.media['groups'])
    except AttributeError:
        api.on_get(req, resp, BS, CATOM)
        ok = resp.media and resp.media.get('ok')
    check('THE DOOR: the cfg-0 catom-config door answers the clock group for the UNO light bench', bool(ok), resp.media)
    from moduleService.manifests import conform
    rr, rb = conform('cmod'), conform('board')
    check('MANIFESTS: cmod and board conform with the new rows, the checks file and this selftest listed', rr['ok'] and rb['ok'], (rr.get('findings'), rb.get('findings')))
    print('\n%d/%d passed' % (passed, total))
    return 0 if passed == total else 1


if __name__ == '__main__':
    sys.exit(main())
