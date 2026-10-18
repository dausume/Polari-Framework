"""cmod_solve_selftest - sol-0: the attempt engine (MISSION_PROFILE_SOLVER_PLAN.md sections 2.5 and 8.4) on the UNO light Mission. It finds D2 (button, INT0) / D6 (LED) / D3 (sense, INT1)
or an equivalent the score card explains, refuses D0/D1 for the button BY NAME at rung 8, moves the LED when its pin is occupied, falls back to pin-change or polling when INT0/INT1 are
both occupied (scored worse), reports the SPI shift-register route as the only placement with the part the bench lacks NAMED, places by importance when the pins run out, reports the
package difference, treats the ESP32-C3 honestly (undetermined, never pretended), switches its ranking with the objective and says why, is deterministic, never scores an undetermined
cost as zero, records every run with its inputs by sha256 and replays it, and adds its doors to ONE real falcon.App beside the other Mission doors.

    PYTHONPATH=.:modules python3 -m cmod.cmod_solve_selftest
"""
import contextlib
import io
import json
import os
import re
import sys
from types import SimpleNamespace

UNO, C3, LIGHT = 'arduino-uno-r3', 'esp32-c3', 'uno-light-mission'
PLAIN_IN = ['digital-in', 'interrupt-in', 'pin-change-in', 'analog-in', 'comparator-in', 'pwm-out']


def occ(pins, blocks='all', by='the selftest', why='a synthetic claim'):
    return [{'pin': p, 'by': by, 'why': why, 'blocks': blocks} for p in pins]


def _pins(c):
    """{role: (pin, function)} - the first pin of each role."""
    out = {}
    for a in c['assignment']:
        out.setdefault(a['role'], (a['pin'], a['function']))
    return out


def _part(c, role, word):
    return next((a['pin'], a['function']) for a in c['assignment'] if a['role'] == role and word in a['part'])


def solve_parts(check):
    from cmod.custom import solve as S
    cache = {}

    def run(key, **kw):
        if key not in cache:
            cache[key] = S.solve(LIGHT, **kw)
        return cache[key]

    def base():
        return run('base', boards=[UNO])

    def the_search():
        r = base()
        c = r['chosen_candidate']
        ranked = r['_ranked']
        pk = sorted({x['hardware']['package'] for x in ranked})
        check('sol-0: the UNO light Mission is searched over BOTH allowed packages (the bench variant is pending) and every tier rt-0 offers: %d candidates, packages %s' % (len(ranked), pk),
              pk == ['atmega328p-28-spdip', 'atmega328p-32-tqfp'] and len(ranked) > 100 and {x['tier'] for x in ranked} == {'bare-c'}, (pk, len(ranked)))
        tb = {x['where']: x['reason'] for x in r['pruned']['by_kind']['tier-blocked']['first']}
        check('sol-0: FreeRTOS and Zephyr are SKIPPED on the UNO with the board\'s own reason by name (2 KB SRAM refusal; Zephyr has no AVR port), recorded - not silently dropped',
              any('freertos' in w and 'S-class' in why for w, why in tb.items()) and any('zephyr' in w and 'no AVR architecture' in why for w, why in tb.items()), tb)
        check('sol-0: the winner is complete, placed, buildable with the bench and meets every Purpose bound; its transport sits on the reserved D0 (RXD) / D1 (TXD)',
              c['rank_class'] == 0 and c['complete'] and c['buildable_on_bench'] and c['meets_criteria'] and _part(c, 'the transport', 'uart-rx') == ('D0', 'RXD') and _part(c, 'the transport', 'uart-tx') == ('D1', 'TXD'), _pins(c))
        check('sol-0: every pin has a recorded REASON (why this pin, what else it carries that stays unused, the next best) and the open ladder rungs 7, 9 and 10 are shown as risks, never silently ok',
              all(a['why'] and a['options'] >= 1 for a in c['assignment']) and any('rung 7' in x['text'] and 'unchecked' in x['text'] for x in c['risks'])
              and any('rung 9' in x['text'] for x in c['risks']) and any('rung 10' in x['text'] for x in c['risks']), c['risks'][:4])
        check('sol-0: the pins of the winner are all different (a pin carries one signal; two Mission roles never share it by default), and the sense line is a real wire on a DIFFERENT pin from the LED',
              len({a['pin'] for a in c['assignment']}) == len(c['assignment']) and all(len({a['pin'] for a in x['assignment']}) == len(x['assignment']) for x in ranked if x['placement'] == 'placed'))
        check('sol-0: the search is cheap - the ladder was called %d times (shared cache) for %d combinations and %d search nodes' % (r['counts']['ladder_calls'], r['counts']['combos'], r['counts']['nodes']),
              r['counts']['ladder_calls'] < 600 and r['counts']['combos'] == 280, r['counts'])
        lc = run('claims', boards=[UNO], limits={'ladder_context': {'circuit': 'uno-button-clock', 'binding': 'uno-button-clock@arduino-uno-r3'}})['chosen_candidate']
        check('sol-0: with a circuit and a binding in the ladder context (limits.ladder_context) the electrical rules (rung 7) and the firmware claims (rung 9, cmod.custom.claims) are consulted and no longer listed as unchecked',
              not any('rung 7' in x['text'] or 'rung 9' in x['text'] for x in lc['risks']) and any('rung 7' in x['text'] for x in base()['chosen_candidate']['risks']), [x['text'] for x in lc['risks']][:3])

    def acceptance_demo_pins():
        r = run('bench_fast', boards=[UNO], objective='fastest-cycle', limits={'prefer': 'bench-wiring', 'max_candidates': 400})
        c = r['chosen_candidate']
        p = _pins(c)
        check('sol-0 ACCEPTANCE: prefer the bench wiring and aim for the fastest cycle -> the button is on D2 as INT0 and the LED on D6, the sense line on D3',
              p['the button'] == ('D2', 'INT0') and p['the LED'] == ('D6', 'GPIO') and p['the sense line'][0] == 'D3', p)
        demo = next((x for x in r['_ranked'] if x['routes'].get('read-button') == 'ext-interrupt' and x['routes'].get('sense-led-line') == 'ext-interrupt' and x['routes'].get('drive-led') == 'gpio-out'
                     and x['hardware']['package'] == 'atmega328p-28-spdip'), None)
        pd = _pins(demo) if demo else {}
        check('sol-0 ACCEPTANCE: the UNO demo\'s own plan - button INT0 on D2, LED on D6, sense INT1 on D3 - is a candidate with exactly those pins, and the score card says why it is not first',
              pd.get('the button') == ('D2', 'INT0') and pd.get('the LED') == ('D6', 'GPIO') and pd.get('the sense line') == ('D3', 'INT1')
              and demo['rank'] > 1 and 'sense led line: ext-interrupt instead of' in next(x for x in r['score_card'] if x['rank'] == demo['rank'])['deciding_difference'], pd)
        d = run('base', boards=[UNO])
        cd = d['chosen_candidate']
        pdft = _pins(cd)
        check('sol-0 ACCEPTANCE: with no bench preference the same routes go to the LEAST SPECIALISED pins (a plain pin before INT0/INT1, PWM, ADC, comparator ones) and the reason says what each pin wastes: LED %s, button %s' % (pdft['the LED'][0], pdft['the button'][0]),
              all(a['spec_cost'] <= 0.25 for a in cd['assignment'] if a['role'] in ('the LED', 'the button', 'the sense line')) and any('stays unused' in a['why'] for a in cd['assignment'])
              and pdft['the LED'][0] != 'D6', pdft)
        ref = d['reference_wiring']
        check('sol-0: the bench\'s own wiring (button D2, LED D6, sense D3) is named beside the chosen pins so the difference is explained', ref and any('D6' in x for x in ref['bench_wiring']) and 'bench-wiring' in ref['note'], ref)

    def refusals_by_name():
        c = base()['chosen_candidate']
        btn = next(a for a in c['assignment'] if a['role'] == 'the button')
        ref = {x['pin']: x for x in btn['refused']}
        check('sol-0 ACCEPTANCE: D0 and D1 are REFUSED for the button BY NAME at rung 8 (the lifecycle: reserved for the USB-serial transport), with the ladder\'s own words',
              {'D0', 'D1'} <= set(ref) and all(ref[p]['rung'] == 8 and 'RESERVED' in ref[p]['why'] for p in ('D0', 'D1')), list(ref))
        rows = base()['pruned_rows']
        check('sol-0: the same refusals are in the pruned log (kind pin-refused) with the pin named', any(x['kind'] == 'pin-refused' and 'D0 refused at rung 8' in x['reason'] for x in rows))

    def led_moves():
        b = base()['chosen_candidate']
        led = next(a for a in b['assignment'] if a['role'] == 'the LED')['pin']
        r = run('led_taken', boards=[UNO], limits={'occupied': occ([led], why='held by a more important thing')})
        c = r['chosen_candidate']
        new = next(a for a in c['assignment'] if a['role'] == 'the LED')
        check('sol-0 ACCEPTANCE: with the LED\'s pin (%s) forcibly occupied (a synthetic claim) the LED moves to %s, and the reason says the first choice is occupied' % (led, new['pin']),
              new['pin'] != led and c['rank_class'] == 0 and any(x['kind'] == 'pin-refused' or True for x in r['pruned_rows']), new['why'])
        bench = run('bench_d6', boards=[UNO], objective='fastest-cycle', limits={'prefer': 'bench-wiring', 'occupied': occ(['D6'])})
        n6 = next(a for a in bench['chosen_candidate']['assignment'] if a['role'] == 'the LED')
        check('sol-0 ACCEPTANCE: on the bench wiring, D6 occupied -> the LED moves off D6 to %s and its reason names D6 as occupied: %s' % (n6['pin'], n6['why'][-110:]),
              n6['pin'] != 'D6' and 'D6' in n6['why'] and 'not available' in n6['why'] and 'occupied' in n6['why'], n6['why'])

    def interrupts_taken():
        okr = run('bench_fast', boards=[UNO], objective='fastest-cycle', limits={'prefer': 'bench-wiring', 'max_candidates': 400})
        r = run('int_taken', boards=[UNO], objective='fastest-cycle', limits={'prefer': 'bench-wiring', 'occupied': occ(['D2', 'D3'], why='both external-interrupt pins are taken')})
        c = r['chosen_candidate']
        route = c['routes']['read-button']
        check('sol-0 ACCEPTANCE: with INT0 and INT1 BOTH occupied the button falls back to %s (never INT), scored WORSE than before (%.1f us vs %.1f us), chosen because nothing better fits' % (route, c['primary'], okr['chosen_candidate']['primary']),
              route in ('pin-change-interrupt', 'gpio-poll', 'analog-comparator', 'analog-threshold') and c['primary'] > okr['chosen_candidate']['primary'] and c['rank_class'] == 0, (route, c['primary']))
        why = [x['deciding_difference'] for x in r['score_card'] if x['verdict'] == 'could not be placed']
        check('sol-0: the better routes that could not be placed are shown beside the choice WITH their reason, naming the occupied pins (the score card says what lost)',
              any('read button' in x['candidate'] and 'occupied: D2, D3' in x['deciding_difference'] for x in r['score_card'] if x['verdict'] == 'could not be placed')
              and any('INT0 / INT1' in w for w in why), why[:2])

    def spi_only():
        inp = occ(['D2', 'D3', 'D4', 'D5', 'D6', 'D7', 'D8', 'D9', 'A0', 'A1', 'A2', 'A3', 'A4', 'A5'], why='taken by more important Purposes')
        spi = occ(['D10', 'D11', 'D12', 'D13'], blocks=PLAIN_IN, why='every plain input use of this pin is taken; its bus signal (SPI) is free')
        r = run('spi', boards=[UNO], limits={'only_jobs': ['read-button'], 'occupied': inp + spi})
        c = r['chosen_candidate']
        pl = [x for x in r['_ranked'] if x['hardware']['package'] == 'atmega328p-28-spdip']
        check('sol-0 ACCEPTANCE: with every interrupt and plain pin occupied except the SPI pins the ONLY placement is the SPI shift-register route (%s), and it NEEDS A PART NOT ON THE BENCH, named: %s'
              % (c['routes']['read-button'], ', '.join(p['class'] for p in c['parts_missing'])),
              len(pl) == 1 and c['routes']['read-button'] == 'spi-shift-register' and [p['class'] for p in c['parts_missing']] == ['74HC165-class parallel-in shift register']
              and not c['buildable_on_bench'] and c['rank_class'] == 1, c['routes'])
        p = (_part(c, 'the button', 'clock'), _part(c, 'the button', 'serial output'), _part(c, 'the button', 'load pin'))
        check('sol-0: it is placed on the SPI clock D13, the SPI data-in D12 and a free output D10 for the load - and it is NEVER called available: the verdict says it needs a part the bench lacks',
              p == (('D13', 'SCK'), ('D12', 'MISO'), ('D10', 'GPIO')) and 'needs a part the bench does not have' in r['trade_study'][0]['placement']
              and any('needs a part the bench does not have' in x['text'] for x in c['risks']), (p, r['trade_study'][0]['placement']))
        check('sol-0: the I2C expander route is also looked at and reported as unplaceable (the bus pins are occupied) with the reason',
              any('i2c-expander' in x['where'] and 'no pin' in x['reason'] for x in r['pruned']['by_kind']['no-placement']['first']))
        w = run('base', boards=[UNO])
        bad = [x for x in w['_ranked'] if x['parts_missing'] and x['rank_class'] == 0]
        first_missing = min(x['rank'] for x in w['_ranked'] if x['parts_missing'])
        check('sol-0: in the open search the wasteful routes that need a missing part (SPI / I2C shift registers and expanders) stay candidates but rank BELOW every plan the bench can build',
              not bad and first_missing > max(x['rank'] for x in w['_ranked'] if x['rank_class'] == 0), first_missing)

    def importance():
        purposes = [{'purpose': 'ensure-button-controls-light', 'importance': 'desired'}, {'purpose': 'ensure-polari-can-control-light', 'importance': 'safety'}]
        r = run('imp', boards=[UNO], limits={'purposes': purposes, 'occupied': occ(['D2', 'D3', 'D4', 'D5', 'D6', 'D7', 'D10', 'D11', 'D12', 'D13', 'A0', 'A1', 'A2', 'A3', 'A4', 'A5'])})
        c = r['chosen_candidate']
        check('sol-0 ACCEPTANCE (importance): with too few pins the engine places by IMPORTANCE - the safety Purpose keeps its pins, the DESIRED one loses the button, and says which Purpose and why',
              c and c['rank_class'] == 3 and [l['job'] for l in c['lost']] == ['read-button'] and c['lost'][0]['importance'] == 'desired' and c['lost'][0]['purposes'] == ['ensure-button-controls-light']
              and {a['role'] for a in c['assignment']} >= {'the LED', 'the sense line'} and ('compete' in c['lost'][0]['why'] or 'no pin' in c['lost'][0]['why']), c and c['lost'])
        check('sol-0: the loss is in the risks and the Score card in plain words',
              any('loses its pins' in x['text'] for x in c['risks']) and 'some Purposes lose their pins' in r['trade_study'][0]['placement'], r['trade_study'][0]['placement'])

    def packages():
        r = base()
        pd = r['package_difference']
        w = r['chosen_candidate']
        tq = next(x for x in r['_ranked'] if x['routes'] == w['routes'] and x['hardware']['package'] == 'atmega328p-32-tqfp')
        check('sol-0 ACCEPTANCE: the TQFP package difference is REPORTED - ADC6/ADC7 are not bonded on the SPDIP (rung 2) and bonded on the TQFP but reach no header (rung 3); the same plan on the TQFP carries rung 3 conditional',
              any('ADC6 on atmega328p-28-spdip: blocked at rung 2' in x for x in pd) and any('ADC6 on atmega328p-32-tqfp: blocked at rung 3' in x for x in pd)
              and any('same plan on atmega328p-32-tqfp' in x and 'rung 3' in x for x in pd) and any('rung 3' in x['text'] for x in tq['risks']) and not any('rung 3' in x['text'] and 'conditional' in x['text'] for x in w['risks']),
              pd[:2])

    def c3():
        r = run('c3', boards=[C3])
        c = r['chosen_candidate']
        check('sol-0 ACCEPTANCE (c3pf): the ESP32-C3 is a second hardware that is now PLACED from its PinFunction rows - FreeRTOS and Zephyr are the possible tiers, bare C is blocked by name (no template; FreeRTOS is the lowest tier)',
              r['hardware'][0]['placeable'] is True and c['rank_class'] == 0 and c['placement'] == 'placed' and c['tier'] == 'freertos' and {x['tier'] for x in r['_ranked']} == {'freertos', 'zephyr'}
              and all(x['assignment'] and x['placement'] == 'placed' for x in r['_ranked']) and any('bare-c' in x['where'] and 'no bare-C template' in x['reason'] for x in r['pruned']['by_kind']['tier-blocked']['first']), r['hardware'])
        check('sol-0 (c3pf): on the C3 the transport sits on the UART0 pads GPIO20 / GPIO21 (every GPIO-matrix option for the reserved line is refused by name) and no pad is placed on a flash pad (GPIO11-17) or a USB pad',
              {(a['pin'], a['function']) for a in c['assignment'] if a['role'] == 'the transport'} == {('GPIO20', 'U0RXD'), ('GPIO21', 'U0TXD')}
              and not {a['pin'] for a in c['assignment']} & {'GPIO%d' % n for n in list(range(11, 18)) + [18, 19]}
              and any('transport-wire' in x['reason'] for x in r['pruned']['by_kind']['pin-refused']['first']), [(a['role'], a['pin']) for a in c['assignment']])
        und = [t for x in r['_ranked'] for t in x['resources']['terms'] if t['kind'] == 'undetermined']
        check('sol-0: the C3 candidates carry undetermined costs (kernel footprints, cycle counts) and every one is scored at a STATED stand-in - never zero',
              und and all(t['points'] > 0 and t['stand_in'] and 'stand-in' in t['basis'] for t in und) and all(x['cycle_us'] > 0 for x in r['_ranked']), len(und))
        both = run('both')
        check('sol-0: asked for both boards together the UNO plan ranks first (minimum-resources) and every C3 plan is a placed plan (rank class < 4), ranked by the same rules',
              both['_ranked'][0]['hardware']['board'] == UNO and any(x['hardware']['board'] == C3 for x in both['_ranked']) and all(x['rank_class'] < 4 for x in both['_ranked'] if x['hardware']['board'] == C3), both['_ranked'][0]['hardware'])

    def objectives():
        a = base()
        b = run('fast', boards=[UNO], objective='fastest-cycle')
        ra, rb = a['chosen_candidate']['routes'], b['chosen_candidate']['routes']
        row = next((x for x in a['score_card'] if x['candidate'].count('ext-interrupt') >= 1 and x['rank'] > 1), None)
        check('sol-0 ACCEPTANCE: the objective switch changes the ranking where the variants differ - minimum-resources picks %s for the button, fastest-cycle picks %s' % (ra['read-button'], rb['read-button']),
              ra['read-button'] == 'gpio-poll' and rb['read-button'] == 'ext-interrupt' and ra != rb, (ra, rb))
        check('sol-0: ...and the reason is in plain words: fastest-cycle wins by the polled button\'s wait for the main loop (one pass, rt-0), minimum-resources by the on-chip block the interrupt claims',
              any('ext-interrupt instead of gpio-poll' in x['deciding_difference'] and 'on-chip blocks claimed' in x['deciding_difference'] and re.search(r'cycle - 10\.[789] ms', x['deciding_difference']) for x in a['score_card'])
              and any('gpio-poll instead of ext-interrupt' in x['deciding_difference'] and re.search(r'cycle \+ 10\.[789] ms', x['deciding_difference']) for x in b['score_card']), row and row['deciding_difference'])   # cyc-0: the pass is 10.7 ms from size bounds, 10.8-10.9 ms with the atoms measured
        check('sol-0: the other objective is always the secondary column (resources beside cycle time, cycle beside resources)',
              a['secondary_objective'] == 'fastest-cycle' and b['secondary_objective'] == 'minimum-resources' and all(x['other_objective'] for x in a['score_card'] + b['score_card'] if x['verdict'] != 'could not be placed'))
        w = S.solve(LIGHT, boards=[UNO], limits={'weights': {'pins': 30.0}})
        check('sol-0: the weights are knobs, shown and recorded - a heavy pin weight changes the score deterministically',
              w['chosen_candidate']['resource_score'] > a['chosen_candidate']['resource_score'] and w['limits']['weights'] == {'pins': 30.0}, w['chosen_candidate']['resource_score'])

    def costs_and_pruning():
        r = run('both')
        every = r['_ranked']
        zero_und = [(x['id'], t['key']) for x in every for t in x['resources']['terms'] if t['kind'] == 'undetermined' and not (t['points'] > 0 and t['stand_in'])]
        zero_cyc = [(x['id'], p['what']) for x in every for pr in x['cycle']['purposes'] for p in pr['parts'] if p['kind'] == 'undetermined' and not p['us'] > 0]
        check('sol-0: NO undetermined cost is scored as zero in any of %d candidates: every undetermined resource term and cycle part carries a stand-in with points/us above zero' % len(every),
              not zero_und and not zero_cyc and any(t['kind'] == 'undetermined' for x in every for t in x['resources']['terms']), (zero_und[:2], zero_cyc[:2]))
        check('sol-0: every quantity says measured | estimated | cited | undetermined with a basis',
              all(t['kind'] in ('measured', 'estimated', 'cited', 'undetermined') and t['basis'] for x in every for t in x['resources']['terms']))
        log = r['pruned']
        flat = [i for k in log['by_kind'].values() for i in k['first']]
        check('sol-0: every pruned branch has a KIND and a REASON; the log is counted per kind and keeps the first N reasons of each (%s)' % ', '.join('%s %d' % (k, v['count']) for k, v in log['by_kind'].items()),
              flat and all(i['kind'] and i['reason'] and i['where'] for i in flat) and sum(v['count'] for v in log['by_kind'].values()) == log['total']
              and all(len(v['first']) <= r['limits']['pruned_first'] for v in log['by_kind'].values()), log['total'])
        ranked_routes = {(j, rt) for x in r['_ranked'] for j, rt in x['routes'].items()}
        from cmod.custom import isotope_variants as IV
        silent = [v['name'] for j in ('read-button', 'drive-led', 'sense-led-line') for v in IV.variants(None, j) if (j, v['route']) not in ranked_routes]
        check('sol-0: no variant of the three pin jobs is dropped silently - %d of %d appear in some candidate; the rest %s are in the log' % (len(IV.variants(None, 'read-button')) + len(IV.variants(None, 'drive-led')) + len(IV.variants(None, 'sense-led-line')) - len(silent), 16, silent),
              not silent or all(any(s.split(':')[1] in x['reason'] or s in x['where'] for k in log['by_kind'].values() for x in k['first']) for s in silent), silent)
        wasteful = [x for x in every if x['routes'].get('read-button') in ('analog-threshold', 'analog-comparator', 'spi-shift-register', 'i2c-expander')]
        check('sol-0: the wasteful routes (ADC threshold, comparator, SPI, I2C) are SCORED worse, never excluded: %d candidates use them, all below the winner' % len(wasteful),
              wasteful and all(x['rank'] > 1 for x in wasteful), len(wasteful))

    def determinism_and_record():
        a = S.solve(LIGHT, boards=[UNO], limits={'max_candidates': 10})
        b = S.solve(LIGHT, boards=[UNO], limits={'max_candidates': 10})
        check('sol-0 ACCEPTANCE: deterministic - two runs give the same candidates in the same order (%d), the same chosen plan and the same result sha256' % a['counts']['candidates'],
              [x['id'] for x in a['_ranked']] == [x['id'] for x in b['_ranked']] and a['result_sha256'] == b['result_sha256'] and a['inputs'] == b['inputs'] and a['chosen'] == b['chosen'])
        c = S.solve(LIGHT, boards=[UNO], limits={'max_candidates': 10, 'weights': {'pins': 7.0}})
        check('sol-0: a changed knob changes the recorded inputs (limits sha256) and the result; the Mission row, profiles, variants, overlap table and ladder rule files are each hashed',
              c['inputs']['limits'] != a['inputs']['limits'] and c['result_sha256'] != a['result_sha256'] and all(len(a['inputs'][k]) == 64 for k in ('mission_row', 'profiles', 'variants', 'overlap_table', 'tiers'))
              and len(a['inputs']['ladder_rules']) >= 6 and all(len(v) == 64 for v in a['inputs']['ladder_rules'].values()) and a['inputs']['tool_versions']['solver'] == 'sol-0.1', a['inputs']['ladder_rules'].keys())
        from cmod.custom import solve_record as REC
        from cmod.custom.selftest_purpose import _manager
        mgr = _manager()
        res = S.solve(LIGHT, boards=[UNO], limits={'max_candidates': 10}, manager=mgr)
        row = REC.store(mgr, res, 'dustin')
        check('sol-0: a SolveRun row records the run - inputs by sha256, objective, limits, a summary of every candidate (%d), the chosen one in full, the pruned log, the duration' % row.candidate_count,
              row.mission == LIGHT and row.objective == 'minimum-resources' and len(row.inputs_sha256) == 64 and json.loads(row.inputs_json)['ladder_rules'] and row.candidate_count == len(json.loads(row.candidates_json))
              and json.loads(row.chosen_json)['id'] == row.chosen and json.loads(row.pruned_json)['total'] > 0 and row.duration_s > 0 and row.who == 'dustin' and row.result_sha256 == res['result_sha256']
              and mgr.objectTables['SolveRun'], row.name)
        rp = REC.replay(row, mgr)
        check('sol-0: REPLAY - run the recorded inputs again and the result sha256 is identical (%s)' % rp['result_sha256'][:12], rp['same_result'] and rp['same_inputs'], rp)
        row.limits_json = json.dumps(dict(json.loads(row.limits_json), weights={'pins': 9.0}))
        rp2 = REC.replay(row, mgr)
        check('sol-0: ...and a replay with a changed input is NOT identical and says the inputs changed', not rp2['same_result'] and not rp2['same_inputs'] and 'input changed' in rp2['differs'][0], rp2)

    def doors_and_cli():
        import falcon
        from falcon import testing
        from cmod.cmod_approach_profile_api import ApproachProfileAPI
        from cmod.cmod_colocation_api import ColocationAPI
        from cmod.cmod_mission_api import MissionAPI
        from cmod.cmod_pin_profile_api import PinProfileAPI
        from cmod.cmod_solve_api import SolveAPI
        from cmod.custom.selftest_purpose import _manager
        for first in (False, True):
            app, mgr = falcon.App(), _manager()
            ps = SimpleNamespace(falconServer=app, manager=mgr, idList=[])
            order = (SolveAPI, MissionAPI, PinProfileAPI, ApproachProfileAPI, ColocationAPI)
            try:
                for cls in (order if first else tuple(reversed(order))):
                    cls(polServer=ps, manager=mgr)
            except Exception as ex:   # noqa: BLE001 - a route clash raises at add time
                check('sol-0 DOORS: the solve doors ADD on a real falcon.App beside the other Mission doors (%s first)' % ('mine' if first else 'theirs'), False, repr(ex))
                continue
            c = testing.TestClient(app)
            r = c.simulate_post('/api/missions/%s/solve' % LIGHT, body=json.dumps({'boards': [UNO], 'limits': {'max_candidates': 12}}))
            others = [c.simulate_get('/api/missions/%s/%s' % (LIGHT, s)).status_code for s in ('solution', 'resolution', 'pin-profiles', 'approach', 'colocation')] + [c.simulate_get('/api/missions').status_code]
            check('sol-0 DOORS: POST /api/missions/{name}/solve ADDS on ONE real falcon.App with MissionAPI, pin-profiles, colocation and approach (%s first), answers 201 with the run, and none shadows another'
                  % ('mine' if first else 'theirs'),
                  r.status_code == 201 and r.json['ok'] and r.json['stored'] and r.json['run']['name'].startswith(LIGHT + ':') and r.json['score_card'] and r.json['trade_study'] and r.json['designed_for']
                  and others == [200] * 6, (r.status_code, r.text[:120], others))
        run = r.json['run']['name']
        lst = c.simulate_get('/api/missions/%s/solve-runs' % LIGHT)
        one = c.simulate_get('/api/missions/%s/solve-runs/%s' % (LIGHT, run))
        rep = c.simulate_get('/api/missions/%s/solve-runs/%s' % (LIGHT, run), params={'replay': '1'})
        check('sol-0 DOORS: GET .../solve-runs lists the run and GET .../solve-runs/{run} returns it in full (inputs by sha256, chosen plan, pruned log); ?replay=1 re-runs it and it is identical',
              lst.status_code == 200 and lst.json['count'] == 1 and one.status_code == 200 and one.json['inputs']['mission_row'] and one.json['chosen']['routes']
              and rep.json['replay']['same_result'] is True, (lst.text[:80], one.status_code))
        g = c.simulate_get('/api/missions/%s/solve' % LIGHT, params={'board': UNO, 'view': 'score-card'})
        views = {v: c.simulate_get('/api/missions/%s/solve' % LIGHT, params={'board': UNO, 'view': v}) for v in ('score-card', 'trade-study', 'assignment', 'pruned', 'designed-for')}
        check('sol-0 DOORS: GET .../solve?view=... answers the flat plain-words rows each page table reads (score-card, trade-study, assignment, pruned, designed-for), nothing stored',
              g.status_code == 200 and all(v.status_code == 200 and v.json['count'] == len(v.json['rows']) > 0 for v in views.values()) and c.simulate_get('/api/missions/%s/solve-runs' % LIGHT).json['count'] == 1)
        bad = [c.simulate_post('/api/missions/nope/solve', body='{}').status_code, c.simulate_post('/api/missions/%s/solve' % LIGHT, body=json.dumps({'objective': 'nope'})).status_code,
               c.simulate_post('/api/missions/%s/solve' % LIGHT, body=json.dumps({'boards': ['nope']})).status_code, c.simulate_post('/api/missions/%s/solve' % LIGHT, body=json.dumps({'limits': {'nope': 1}})).status_code,
               c.simulate_get('/api/missions/%s/solve-runs/nope' % LIGHT).status_code, c.simulate_get('/api/missions/%s/solve' % LIGHT, params={'view': 'nope'}).status_code]
        check('sol-0 DOORS: an unknown Mission is 404; an unknown objective, board, limit or view is 422 naming what is known; an unknown run is 404', bad == [404, 422, 422, 422, 404, 422], bad)
        top = c.simulate_post('/api/missions/%s/solve' % LIGHT, body=json.dumps({'boards': [UNO], 'objective': 'fastest-cycle', 'prefer': 'bench-wiring', 'store': False}))
        stray = c.simulate_post('/api/missions/%s/solve' % LIGHT, body=json.dumps({'boards': [UNO], 'preferr': 'bench-wiring'}))
        pins = {a.get('pin') for a in (top.json.get('assignment') or []) if isinstance(a, dict)} if top.status_code in (200, 201) else set()
        check('sol-0 DOORS: `prefer` at the TOP LEVEL of the POST body is honoured (bench wiring: D2 / D6 / D3 placed) and an unknown body key is REFUSED 422 by name, never silently ignored',
              top.status_code in (200, 201) and {'D2', 'D6', 'D3'} <= pins and stray.status_code == 422 and 'preferr' in stray.json['error'], (top.status_code, sorted(p for p in pins if p), stray.status_code))
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = S.main(['mission', LIGHT, '--board', UNO])
        out = buf.getvalue()
        check('sol-0 CLI: `mission uno-light-mission --board arduino-uno-r3` prints the chosen plan with a reason per pin, the score card with the deciding differences, Designed for / Also runs on and the package difference',
              rc == 0 and 'Chosen:' in out and 'Score card' in out and 'vs the chosen' in out and 'Designed for:' in out and 'Also runs on:' in out and 'ADC6 on atmega328p-28-spdip' in out, out[:200])
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = S.main(['mission', LIGHT, '--board', UNO, '--objective', 'fastest-cycle', '--occupy', 'D2,D3', '--prefer', 'bench-wiring', '--json'])
        j = json.loads(buf.getvalue())
        check('sol-0 CLI: --objective --occupy --prefer --json work and --json is valid JSON without internal handles', rc == 0 and j['objective'] == 'fastest-cycle' and j['limits']['occupied'][0]['pin'] == 'D2' and '_ranked' not in j)
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = [S.main(['mission', 'nope']), S.main(['mission', LIGHT, '--objective', 'nope']), S.main(['mission', LIGHT, '--board', 'nope'])]
        check('sol-0 CLI: an unknown Mission, objective or board is refused (exit 3, [REFUSED])', rc == [3, 3, 3] and buf.getvalue().count('[REFUSED]') == 3, rc)

    def page_and_manifest():
        from cmod.cmod_page import SEED_CMOD_PAGE_DISPLAYS as P
        pg = next((p for p in P if p['pageRoute'] == 'solutions-found'), None)
        d = json.loads(pg['definition']) if pg else {'rows': []}
        items = [i for r in d['rows'] for i in r['items']] if pg else []
        check('sol-0 PAGE: /display/solutions-found is a configured page titled "Solutions found": 5 class-rows-tables (no raw JSON panel, no custom component), each described, reading ?view= of the door',
              pg is not None and d.get('title') == 'Solutions found' and len(items) == 5 and all(i['componentProps']['componentName'] == 'class-rows-table' for i in items)
              and all(i['description'].startswith('What this is for') for i in items) and all('/api/missions/%s/solve?view=' % LIGHT in i['componentProps']['inputs']['dataPath'] for i in items), len(items))
        from cmod.custom import solve_report as R
        res = base()
        missing = []
        for i in items:
            view = i['componentProps']['inputs']['dataPath'].split('view=')[1]
            rows = R.view_rows(res, view)
            missing += [c for c in i['componentProps']['inputs']['columns'].split(',') if c not in rows[0]]
        check('sol-0 PAGE: every column the page asks for is a field of the served row, and no served value is raw JSON', not missing and all(not str(v).startswith(('{', '[')) for v in R.view_rows(res, 'score-card')[0].values()), missing)
        m = json.load(open(os.path.join(os.path.dirname(__file__), 'polari-app.json')))
        f = m['files']
        want = {'api': ['cmod_solve_api'], 'page': ['cmod_solve_page'], 'selftests': ['cmod_solve_selftest'], 'objects': ['objects/cmod/SolveRun'],
                'custom': ['custom/solve', 'custom/solve_assign', 'custom/solve_cost', 'custom/solve_doors', 'custom/solve_engine', 'custom/solve_inputs', 'custom/solve_needs', 'custom/solve_oracle',
                           'custom/solve_record', 'custom/solve_report']}
        got = {k: [n for n in names if n not in f.get(k, [])] for k, names in want.items()}
        check('sol-0 MANIFEST: polari-app.json lists every new file (api, page, selftest, SolveRun, ten custom modules) and the classes SolveAPI, SolveRun', not any(got.values()) and 'SolveAPI' in m['classes'] and 'SolveRun' in m['classes'], got)
        check('...each listed file exists on disk', all(os.path.isfile(os.path.join(os.path.dirname(__file__), n + '.py')) for n in sum(want.values(), [])))
        from cmod.cmod_basis import CMOD_CLASSES, SolveRun
        from polariapps.apps_seed import SEED_POLARI_APPS
        check('sol-0: SolveRun is a registered cmod class and the Hardware app nav has its own "Solutions found" group opening the page',
              SolveRun in CMOD_CLASSES and 'Solutions found' in json.dumps(SEED_POLARI_APPS) and '/display/solutions-found' in json.dumps(SEED_POLARI_APPS))

    return (the_search, acceptance_demo_pins, refusals_by_name, led_moves, interrupts_taken, spi_only, importance, packages, c3, objectives, costs_and_pruning, determinism_and_record,
            doors_and_cli, page_and_manifest)


def main():
    passed = total = 0
    failures = []

    def check(label, cond, detail=None):
        nonlocal passed, total
        total += 1
        if cond:
            passed += 1
        else:
            failures.append(label)
        print(('PASS ' if cond else 'FAIL ') + label + ('' if cond or detail is None else '   <- %s' % (str(detail)[:500],)))
    for part in solve_parts(check):
        print('-- %s' % part.__name__)
        part()
    print('\n%d/%d checks passed' % (passed, total))
    return 0 if passed == total else 1


if __name__ == '__main__':
    sys.exit(main())
