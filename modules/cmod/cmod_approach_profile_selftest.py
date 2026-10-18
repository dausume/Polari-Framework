"""cmod_approach_profile_selftest - rt-0: the approach pre-profiler (MISSION_PROFILE_SOLVER_PLAN.md section 8.2): the light Mission recommends bare C with reasons, each tier is
CHECKED against the UNO and the ESP32-C3 model (FreeRTOS and Zephyr blocked on the UNO by name, never available on an unmeasured kernel; available on the C3 with what is
undetermined said), a synthetic Mission with several conflicting periodic tasks and a blocking bus read recommends FreeRTOS, a large one Zephyr, every number carries a
label and a basis, priorities are deadline-monotonic with importance as the tie-break, the door beside the other Mission doors on one falcon.App, the CLI, the page, the manifest.

    PYTHONPATH=.:modules python3 -m cmod.cmod_approach_profile_selftest
"""
import contextlib
import io
import json
import os
import sys
from types import SimpleNamespace

UNO, C3 = 'arduino-uno-r3', 'esp32-c3'
LIGHT = 'uno-light-mission'


def _walk(obj, path=''):
    """Every labelled quantity {kind, value, unit, basis} inside obj."""
    if isinstance(obj, dict):
        if 'kind' in obj and 'value' in obj and 'unit' in obj and 'basis' in obj:
            yield path, obj
        for k, v in obj.items():
            yield from _walk(v, '%s.%s' % (path, k))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from _walk(v, '%s[%d]' % (path, i))


def _synth(tasks, purposes, isrs=(), board=UNO, drivers=()):
    from cmod.custom.approach_profile_atoms import q
    ps = []
    for name, imp, trig, dl, tnames in purposes:
        ps.append({'purpose': name, 'importance': imp, 'title': name, 'trigger': {'kind': trig, 'what': name + ' fires'},
                   'deadline_ms': q('criterion', dl, 'ms', 'synthetic criterion') if dl else None, 'deadline_key': 'max_latency_ms', 'debounce_ms': None,
                   'period_ms': None, 'tasks': tnames, 'graph': 'synthetic'})
    ts = []
    for name, period, wcet_us, serves, blocking, periph in tasks:
        ts.append({'name': name, 'lane': 'loop', 'period_ms': q('criterion', period, 'ms', 'synthetic period') if period else None,
                   'wcet_us': q('estimated', wcet_us, 'us', 'synthetic'), 'known_us': float(wcet_us), 'unbounded': [],
                   'blocking': [dict(kind='bus-read', atom=name, what=w, worst_us=q('estimated', us, 'us', 'synthetic bus transaction')) for w, us in blocking],
                   'text_bytes': 100, 'stack_bytes': 32, 'peripherals': list(periph), 'serves': serves, 'atom': ''})
    return {'mission': 'synthetic', 'board_ref': board, 'source': 'synthetic Mission built by the selftest', 'purposes': ps, 'notes': [],
            'processors': [{'name': 'synthetic-fw', 'board': board, 'clock_hz': 16000000, 'baud': None, 'frame_bytes': None, 'frame_basis': '', 'tasks': ts,
                            'isrs': list(isrs), 'build': None, 'runtime_row': ''}]}


def approach_profile_parts(check):
    from cmod.custom import approach_profile as AP
    from cmod.custom import approach_profile_atoms as A
    from cmod.custom import approach_profile_tiers as T
    from cmod.custom import isotope_variants_eligibility as E
    light = {}

    def lt(board=UNO, tier=None):
        key = (board, tier)
        if key not in light:
            light[key] = AP.approach_profile(LIGHT, board=board, tier=tier)
        return light[key]

    def atoms_read_off():
        from cmod.custom import code_interface as CI
        ctx = {'baud': 115200, 'frame_bytes': 110}
        p, _m, send = CI.find_atom('uno:hal.hal_usart_send')
        r = A.analyse(p, send, ctx)
        _p, _m2, millis = CI.find_atom('uno:hal.hal_millis')
        m = A.analyse(p, millis, ctx)
        _p, _m3, apply_ = CI.find_atom('uno:apps/light.apply_command')
        a = A.analyse(p, apply_, ctx)
        check('rt-0: hal_usart_send is read as a wait on UDRE0 (the USART transmit register), 110 B x 10 bit times at 115200 Bd = 9548.6 us, ESTIMATED with the arithmetic as basis',
              r['bounded'] and len(r['blocking']) == 1 and r['blocking'][0]['kind'] == 'usart-transmit-wait' and r['blocking'][0]['worst_us']['value'] == 9548.6
              and r['blocking'][0]['worst_us']['kind'] == 'estimated' and '110 bytes' in r['blocking'][0]['worst_us']['basis'], r)
        check('rt-0: a loop-free atom gets a cycle UPPER BOUND from its measured size (hal_millis 54 B -> 27 instructions x 4 = 108 cycles), a loop-free atom calling nothing outside the atoms is bounded',
              m['bounded'] and m['cycles_ub'] == 108 and not m['blocking'], m)
        check('rt-0: apply_command is NOT bounded: it calls LightState_decode_rx, generated code outside the atoms - named, never guessed',
              not a['bounded'] and any('LightState_decode_rx' in u for u in a['unbounded']), a['unbounded'])
        b = A.scan_body('void f(void) { while (!(ADCSRA & _BV(ADSC))) { } for (i = 0; i < n; i++) { x++; } }')
        check('rt-0: the body scan tells a flag wait (ADCSRA.ADSC) from an ordinary loop', b['busy_waits'] == [('ADCSRA', 'ADSC')] and b['other_loops'] == 1, b)

    def light_demo():
        r = lt()
        d, rec = r['demand'], r['recommended']
        check('rt-0: the light Mission on the UNO recommends BARE C, provisional (two tasks have parts that cannot be bounded yet), with reasons in plain words',
              rec['tier'] == 'bare-c' and rec['provisional'] and rec['lowest_available'] == 'bare-c' and len(rec['reasons']) >= 6 and r['board_basis'] == 'asked for'
              and AP.approach_profile(LIGHT)['board'] == UNO and AP.approach_profile(LIGHT)['board_basis'] == 'the Mission\'s own board participant', rec)
        check('rt-0: demand summary - 3 independent triggers (button, Polari command, 10 Hz report), tightest deadline 100 ms (a criterion), 1 periodic task of 100 ms, 1 blocking operation',
              d['independent_triggers']['count']['value'] == 3 and d['tightest_deadline']['value']['value'] == 100 and d['tightest_deadline']['value']['kind'] == 'criterion'
              and d['tightest_deadline']['purpose'] != 'initialization' and len(d['periodic']) == 1 and d['periodic'][0]['task'] == 'telemetry_send'
              and d['periodic'][0]['period_ms']['value'] == 100.0 and len(d['blocking']) == 1, (d['independent_triggers']['count'], d['tightest_deadline'], d['periodic']))
        sl = d['superloop'][0]
        check('rt-0: the argument - the loop pass (known parts) is about 10.7 ms, the button budget 70 ms (100 minus the 30 ms debounce), margin about 59 ms; interrupts take about 10%; verdict fits-known',
              sl['verdict'] == 'fits-known' and 10000 < sl['pass_known_us']['value'] < 11500 and sl['worst']['budget_us']['value'] == 70000.0 and 58000 < sl['worst']['margin_us']['value'] < 60500
              and 9 < sl['isr_share']['value'] < 12 and {u['task'] for u in sl['unbounded']} == {'apply', 'telemetry_send'}, (sl['pass_known_us'], sl['worst'], sl['isr_share']))
        text = ' '.join(rec['reasons'] + rec['caveats'])
        check('rt-0: the reasons name the blocking send (9.5 ms), the 100 ms deadline, the 59 ms margin and what is left out (INT0/INT1 rates; the unbounded tasks)',
              '9.5 ms' in text and '100 ms' in text and 'margin is 59' in text and 'INT0' in text and 'apply' in text and 'cannot bound' in text, text)
        check('rt-0: concurrency from the schedule lanes and pp-0: 5 interrupt vectors (fgm-5a: the ISR atoms of the project, hal_button_pcint.PCINT2_vect among them), 5 loop tasks, only USART0/EEPROM as drivers; 5 pin needs (pp-0), 2 of them interrupt inputs',
              d['concurrency'][0]['interrupt_vectors']['value'] == 5 and d['concurrency'][0]['loop_tasks']['value'] == 5 and d['concurrency'][0]['drivers'] == ['EEPROM', 'USART0']
              and d['pin_profiles']['profiles']['value'] == 5 and d['pin_profiles']['interrupt_inputs']['value'] == 2, (d['concurrency'][0], d['pin_profiles']))
        check('rt-0: data rate - the 10 Hz report is at most 1100 B/s, under 10 percent of the 11520 B/s line (estimated / cited)',
              d['data_rate'] and d['data_rate'][0]['bytes_per_s']['value'] == 1100.0 and d['data_rate'][0]['share_of_line']['value'] < 10 and d['data_rate'][0]['line_capacity']['kind'] == 'cited', d['data_rate'])

    def labels():
        bad = []
        n = 0
        for key in ((UNO, None), (C3, None), (UNO, 'zephyr')):
            r = lt(*key)
            for path, qty in _walk(r):
                n += 1
                if qty['kind'] not in A.KINDS or not str(qty['basis']).strip() or (qty['kind'] == 'undetermined') != (qty['value'] is None):
                    bad.append((path, qty))
        check('rt-0: every number in the answer (%d of them) is labelled measured / estimated / cited / criterion / undetermined, has a basis, and undetermined means no value' % n,
              n > 100 and not bad, bad[:3])
        rows = AP.demand_rows(lt()) + AP.tier_rows(lt()) + AP.priority_rows(lt())
        check('rt-0: the flat rows for the page are plain words: no JSON braces, and every figure carries its label',
              all(not str(v).lstrip().startswith(('{', '[')) for r in rows for v in r.values()) and any('(estimated)' in str(v) for r in rows for v in r.values())
              and any('(measured)' in str(v) for r in rows for v in r.values()))

    def uno_tiers():
        r = lt()
        t = r['tiers']
        mem = {m['what']: m for m in t['bare-c']['memory']}
        check('rt-0: UNO bare C is AVAILABLE: the recorded build (3110 B flash, 513 B static RAM, MEASURED) fits the cited limits (32256 B after Optiboot, 2048 B)',
              t['bare-c']['state'] == 'available' and mem['flash']['application']['value'] == 3110 and mem['flash']['application']['kind'] == 'measured'
              and mem['static RAM']['application']['value'] == 513 and mem['flash']['limit']['value'] == 32256 and mem['flash']['limit']['kind'] == 'cited'
              and mem['static RAM']['free_after_application']['value'] == 2048 - 513, t['bare-c']['memory'])
        fr = t['freertos']
        check('rt-0: UNO FreeRTOS is BLOCKED, never available: the board\'s own refusal (2 KB SRAM) is the reason, and the kernel RAM is UNDETERMINED (no AVR FreeRTOS build, none cited) - not guessed',
              fr['state'] == 'blocked' and '2 KB SRAM' in fr['why'] and fr['kernel']['sram']['kind'] == 'undetermined' and fr['kernel']['sram']['value'] is None
              and 'no freertos build for arduino-uno-r3' in fr['kernel']['sram']['basis'], (fr['state'], fr['why'], fr['kernel']['sram']))
        zp = t['zephyr']
        check('rt-0: UNO Zephyr is BLOCKED by name: Zephyr v4.4.2 has no AVR architecture (cited to its arch/ listing)',
              zp['state'] == 'blocked' and 'no Zephyr target for the ATmega328P' in zp['why'] and 'arch/' in zp['why'], zp['why'])
        ctx = E.context(UNO)
        check('rt-0: the tier support is iso-0\'s own check (REUSED, not copied): the verdicts equal isotope_variants_eligibility.check_runtime for each tier',
              all(t[x]['support']['state'] == E.check_runtime({'minimum_level': x}, ctx, tier=x)['state'] for x in T.TIERS)
              and 'check_runtime' in open(T.__file__.replace('.pyc', '.py')).read() and 'def check_runtime' not in open(T.__file__.replace('.pyc', '.py')).read())
        n_ok = lambda tier: sum(v['ok'] for v in T.variants_by_job(ctx, tier))   # noqa: E731
        from cmod.custom import isotope_variants as IV
        direct = sum(1 for v in IV.variants() if E.eligible(v, ctx, tier='bare-c')['state'] == 'ok')
        check('rt-0: the isotope variants that stay eligible per job are counted per tier from iso-0: bare C keeps %d (equal to a direct count), FreeRTOS and Zephyr keep 0 on the UNO' % direct,
              n_ok('bare-c') == direct == 15 and n_ok('freertos') == 0 and n_ok('zephyr') == 0 and len(t['bare-c']['variants']) == 6
              and sum(v['total'] for v in t['bare-c']['variants']) == 22, t['bare-c']['variants'])
        check('rt-0: choosing a higher tier shows its cost (kernel undetermined, a stack per task, fewer variants); choosing the recommended one says so',
              'kernel and stacks' in fr['cost_of_choosing']['text'] and 'undetermined' in fr['cost_of_choosing']['text'] and 'at least 96 bytes' in fr['cost_of_choosing']['text']
              and 'recommended tier' in t['bare-c']['cost_of_choosing']['text'], fr['cost_of_choosing'])

    def c3_tiers():
        r = lt(C3)
        t = r['tiers']
        check('rt-0: on the ESP32-C3 model FreeRTOS and Zephyr are AVAILABLE; bare C is blocked (no bare-C template on the C3)',
              t['freertos']['state'] == 'available' and t['zephyr']['state'] == 'available' and t['bare-c']['state'] == 'blocked' and 'no bare-C template' in t['bare-c']['why'],
              {k: v['state'] for k, v in t.items()})
        check('rt-0: ...with what is measured and what is not: the SoC SRAM total is cited (409600 B), the app flash partition cited, the Mission\'s AVR-measured size does NOT transfer (undetermined, said), the kernels are undetermined; Zephyr heap 4096 B cited',
              t['freertos']['fit'] == 'undetermined' and t['freertos']['memory'][1]['limit']['value'] == 409600 and t['freertos']['memory'][0]['limit']['value'] == 1048576
              and t['freertos']['memory'][1]['application']['value'] is None and 'measured for arduino-uno-r3' in t['freertos']['memory'][1]['application']['basis']
              and t['freertos']['kernel']['sram']['value'] is None and t['zephyr']['kernel']['heap']['value'] == 4096 and t['zephyr']['kernel']['heap']['kind'] == 'cited', t['freertos']['memory'])
        rec = r['recommended']
        check('rt-0: the demand still says bare C, but the C3 does not offer it: the advice names the refusal and the lowest available tier that meets the demand (FreeRTOS)',
              rec['tier'] == 'bare-c' and rec['lowest_available'] == 'freertos' and 'does not offer it' in rec['advice'] and 'no bare-C template' in rec['advice']
              and r['priorities']['tier'] == 'freertos', rec['advice'])
        c = lt(C3, 'zephyr')['chosen']
        check('rt-0: ?tier= shows what choosing that tier costs and is advice only (it records nothing; a person\'s pick is a DerivedOverride)',
              c['tier'] == 'zephyr' and c['state'] == 'available' and 'kernel and stacks' in c['cost']['text'] and 'DerivedOverride' in c['record'] and lt(C3)['chosen'] is None, c)
        try:
            AP.approach_profile(LIGHT, board=C3, tier='nope')
            ok = False
        except KeyError:
            ok = True
        check('rt-0: an unknown tier or board is refused naming what is known', ok and _raises(lambda: AP.approach_profile(LIGHT, board='nope'), KeyError))

    def synthetic():
        from cmod.custom.approach_profile_atoms import q
        # several conflicting periodic tasks + a blocking bus read
        tasks = [('sample', 10, 2000, ['p-sample'], [('reads the sensor over the bus (I2C), waits for the transfer', 8000)], ['TWI']),
                 ('control', 20, 4000, ['p-control'], [], []),
                 ('display', 50, 15000, ['p-display'], [], ['SPI'])]
        purposes = [('p-sample', 'required', 'period', 10, ['sample']), ('p-control', 'safety', 'period', 20, ['control']), ('p-display', 'desired', 'period', 50, ['display'])]
        spec = _synth(tasks, purposes)
        r = AP.approach_profile('synthetic', board=C3, spec=spec)
        rec, sl = r['recommended'], r['demand']['superloop'][0]
        check('rt-0: a synthetic Mission with three conflicting periodic tasks (10/20/50 ms) and a blocking bus read recommends FREERTOS: one loop pass (29 ms) cannot fit the 10 ms deadline',
              rec['tier'] == 'freertos' and sl['verdict'] == 'fails' and sl['worst']['margin_us']['value'] < 0 and 28000 < sl['pass_known_us']['value'] < 30000
              and any('CANNOT guarantee' in x for x in rec['reasons']) and rec['escalated_by'] == 'the main-loop argument fails', (rec['tier'], sl['pass_known_us'], sl['worst']))
        check('rt-0: ...and says so in the demand: 3 triggers, tightest deadline 10 ms, 3 periodic tasks, 1 blocking operation, not large enough for Zephyr (thresholds named)',
              r['demand']['independent_triggers']['count']['value'] == 3 and r['demand']['tightest_deadline']['value']['value'] == 10 and len(r['demand']['periodic']) == 3
              and len(r['demand']['blocking']) == 1 and any('Not large enough for Zephyr' in x for x in rec['reasons']), rec['reasons'])
        check('rt-0: on the C3 that FreeRTOS is available; on the UNO the recommended FreeRTOS is blocked and the advice says no tier at or above it is offered',
              r['tiers']['freertos']['state'] == 'available' and rec['lowest_available'] == 'freertos'
              and AP.approach_profile('synthetic', board=UNO, spec=spec)['recommended']['lowest_available'] == ''
              and 'offers none at or above it' in AP.approach_profile('synthetic', board=UNO, spec=spec)['recommended']['advice'])
        pr = r['priorities']['rows']
        check('rt-0: derived priorities are DEADLINE-MONOTONIC (10 ms sample > 20 ms control > 50 ms display), marked a preview for fgm-3',
              [x['task'] for x in pr] == ['sample', 'control', 'display'] and [x['priority'] for x in pr] == [1, 2, 3] and 'Task Plans come in fgm-3' in r['priorities']['preview'] and not r['priorities']['ties'], pr)
        # importance breaks a tie on equal deadlines
        t2 = [('a', None, 100, ['pa'], [], []), ('b', None, 100, ['pb'], [], []), ('c', None, 100, ['pc'], [], [])]
        p2 = [('pa', 'desired', 'button', 40, ['a']), ('pb', 'safety', 'button', 40, ['b']), ('pc', 'required', 'button', 40, ['c'])]
        r2 = AP.approach_profile('synthetic', board=UNO, spec=_synth(t2, p2))
        order = [x['task'] for x in r2['priorities']['rows']]
        check('rt-0: equal deadlines are broken by importance (safety > required > desired), and a still-equal pair is marked a tie',
              order == ['b', 'c', 'a'] and not r2['priorities']['ties'], order)
        t3 = [('x', None, 100, ['px', 'py'], [], []), ('y', None, 100, ['py'], [], [])]
        r3 = AP.approach_profile('synthetic', board=UNO, spec=_synth(t3, [('px', 'required', 'button', 40, ['x']), ('py', 'required', 'button', 40, ['y'])]))
        check('rt-0: the light Mission\'s five loop tasks all tie (100 ms, required) and the preview says the order is only the schedule order',
              len(lt()['priorities']['ties']) == 5 and 'schedule order' in lt()['priorities']['tie_note'] and r3['priorities']['ties'] == ['x', 'y'], lt()['priorities']['tie_note'])
        # a small system that a loop serves: bare C, not provisional
        small = _synth([('poll', 100, 300, ['ps'], [], [])], [('ps', 'required', 'button', 100, ['poll'])])
        rs = AP.approach_profile('synthetic', board=UNO, spec=small)
        check('rt-0: a small synthetic Mission (one 300 us poll, 100 ms deadline) recommends bare C, NOT provisional (every part bounded)',
              rs['recommended']['tier'] == 'bare-c' and not rs['recommended']['provisional'] and rs['demand']['superloop'][0]['verdict'] == 'fits', rs['recommended'])
        # a large one: Zephyr
        many = [('t%d' % i, 100, 1000, ['pz'], [('reads device %d over the bus' % i, 6000)] if i < 3 else [], ['TWI'] if i < 3 else []) for i in range(9)]
        many = [(n, p, w, s, b, (per or []) + (['SPI', 'ADC', 'USART0', 'USB'] if n == 't4' else [])) for n, p, w, s, b, per in many]
        big = _synth(many, [('pz', 'required', 'period', 20, [m[0] for m in many])])
        rz = AP.approach_profile('synthetic', board=C3, spec=big)
        check('rt-0: a large synthetic Mission (9 activities, 5 peripheral drivers, three bus reads) recommends ZEPHYR, with the thresholds named as rules of the profiler',
              rz['recommended']['tier'] == 'zephyr' and rz['recommended']['escalated_by'] == 'FreeRTOS is warranted and the system is large'
              and any('rule of thumb of this profiler' in x for x in rz['recommended']['reasons']) and rz['tiers']['zephyr']['state'] == 'available', rz['recommended']['reasons'][-2:])
        check('rt-0: the S-class guard - a kernel with no figure on an MCU-S board is never called available (FreeRTOS on the UNO is blocked even before the guard); the C3 is not S class',
              lt(UNO)['tiers']['freertos']['state'] == 'blocked' and lt(C3)['tiers']['freertos']['state'] == 'available')

    def doors_and_cli():
        import falcon
        from falcon import testing
        from cmod.cmod_approach_profile_api import ApproachProfileAPI
        from cmod.cmod_mission_api import MissionAPI
        from cmod.cmod_pin_profile_api import PinProfileAPI
        from cmod.custom.selftest_purpose import _manager
        import importlib
        extra = []
        for mod, cls in (('cmod.cmod_profile_overlap_api', 'ProfileOverlapAPI'), ('cmod.cmod_colocation_api', 'ColocationAPI')):
            try:
                extra.append(getattr(importlib.import_module(mod), cls))
            except (ImportError, AttributeError):
                pass
        for first in (False, True):
            app, mgr = falcon.App(), _manager()
            ps = SimpleNamespace(falconServer=app, manager=mgr, idList=[])
            order = (ApproachProfileAPI, MissionAPI, PinProfileAPI) + tuple(extra)
            for cls in (order if first else tuple(reversed(order))):
                cls(polServer=ps, manager=mgr)
            c = testing.TestClient(app)
            r = c.simulate_get('/api/missions/%s/approach' % LIGHT)
            others = [c.simulate_get('/api/missions/%s/%s' % (LIGHT, s)).status_code for s in ('solution', 'resolution', 'pin-profiles')] + [c.simulate_get('/api/missions').status_code]
            check('rt-0: /api/missions/{name}/approach on ONE real falcon.App with the real MissionAPI and the pin-profiles door (%s first%s): all answer, none shadows another'
                  % ('mine' if first else 'theirs', ' + %d overlap door(s)' % len(extra) if extra else ''),
                  r.status_code == 200 and r.json['ok'] and r.json['recommended']['tier'] == 'bare-c' and others == [200, 200, 200, 200], (r.status_code, r.text[:100], others))
        r = c.simulate_get('/api/missions/%s/approach' % LIGHT, params={'board': C3, 'tier': 'zephyr'})
        check('rt-0: ?board=esp32-c3&tier=zephyr: tiers for the C3 and what choosing Zephyr costs',
              r.status_code == 200 and r.json['board'] == C3 and r.json['tiers']['freertos']['state'] == 'available' and r.json['chosen']['tier'] == 'zephyr', r.text[:120])
        for v, n in (('demand', None), ('tiers', 3), ('priorities', 5)):
            rv = c.simulate_get('/api/missions/%s/approach' % LIGHT, params={'view': v})
            check('rt-0: ?view=%s answers flat plain-words rows for the page table' % v,
                  rv.status_code == 200 and rv.json['view'] == v and rv.json['count'] == len(rv.json['rows']) > 0 and (n is None or rv.json['count'] == n), rv.text[:100])
        check('rt-0: an unknown Mission is a 404; an unknown board, tier or view is a 422, each naming what is known',
              c.simulate_get('/api/missions/nope/approach').status_code == 404
              and c.simulate_get('/api/missions/%s/approach' % LIGHT, params={'board': 'nope'}).status_code == 422 and 'arduino-uno-r3' in c.simulate_get('/api/missions/%s/approach' % LIGHT, params={'board': 'nope'}).json['error']
              and c.simulate_get('/api/missions/%s/approach' % LIGHT, params={'tier': 'nope'}).status_code == 422
              and c.simulate_get('/api/missions/%s/approach' % LIGHT, params={'view': 'nope'}).status_code == 422)
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = AP.main(['mission', LIGHT, '--board', UNO])
        out = buf.getvalue()
        check('rt-0: CLI `mission uno-light-mission --board arduino-uno-r3` prints the recommendation with reasons, the demand, the three tiers and the priority preview',
              rc == 0 and 'Recommended: bare C' in out and 'blocked' in out and 'Derived priorities' in out and 'no AVR architecture' in out, out[:200])
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = AP.main(['mission', LIGHT, '--board', C3, '--json'])
        check('rt-0: CLI --json prints the same answer as JSON', rc == 0 and json.loads(buf.getvalue())['tiers']['freertos']['state'] == 'available')
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = AP.main(['mission', 'nope'])
            rc2 = AP.main(['mission', LIGHT, '--board', 'nope'])
        check('rt-0: CLI refuses an unknown Mission or board (exit 3, [REFUSED])', rc == 3 and rc2 == 3 and buf.getvalue().count('[REFUSED]') == 2)

    def page_and_manifest():
        from cmod.cmod_page import SEED_CMOD_PAGE_DISPLAYS as P
        pg = next((p for p in P if p['pageRoute'] == 'approach'), None)
        d = json.loads(pg['definition']) if pg else {'rows': []}
        items = [i for r in d['rows'] for i in r['items']] if pg else []
        check('rt-0: /display/approach is a configured page titled "Approach": 4 class-rows-tables (no raw JSON panel, no custom component), each described, reading ?view= of the door',
              pg is not None and d.get('title') == 'Approach' and len(items) == 4 and all(i['componentProps']['componentName'] == 'class-rows-table' for i in items)
              and all(i['description'] and 'One row' in i['description'] or 'What this is for' in i['description'] for i in items)
              and all(i['componentProps']['inputs']['dataPath'].startswith('/api/missions/%s/approach?view=' % LIGHT) for i in items), len(items))
        served = {'demand': AP.demand_rows(lt()), 'tiers': AP.tier_rows(lt()), 'priorities': AP.priority_rows(lt())}
        missing = []
        for i in items:
            view = i['componentProps']['inputs']['dataPath'].split('view=')[1].split('&')[0]
            missing += [c for c in i['componentProps']['inputs']['columns'].split(',') if c not in served[view][0]]
        check('rt-0: every column the page asks for is a field of the served row', not missing, missing)
        m = json.load(open(os.path.join(os.path.dirname(__file__), 'polari-app.json')))
        f = m['files']
        want = {'api': ['cmod_approach_profile_api'], 'page': ['cmod_approach_profile_page'], 'selftests': ['cmod_approach_profile_selftest'],
                'custom': ['custom/approach_profile', 'custom/approach_profile_atoms', 'custom/approach_profile_doors', 'custom/approach_profile_input', 'custom/approach_profile_tiers']}
        got = {k: [n for n in names if n not in f.get(k, [])] for k, names in want.items()}
        check('rt-0: polari-app.json lists every new file (api, page, selftest, five custom modules)', not any(got.values()), got)
        check('...each listed file exists on disk, and the API class is exported',
              all(os.path.isfile(os.path.join(os.path.dirname(__file__), n + '.py')) for n in sum(want.values(), [])) and 'ApproachProfileAPI' in json.dumps(m))
        from polariapps.apps_seed import SEED_POLARI_APPS
        s = json.dumps(SEED_POLARI_APPS)
        check('rt-0: the Hardware app nav has its own "Approach" group opening the page', 'Approach' in s and '/display/approach' in s)
    return (atoms_read_off, light_demo, labels, uno_tiers, c3_tiers, synthetic, doors_and_cli, page_and_manifest)


def _raises(fn, exc):
    try:
        fn()
    except exc:
        return True
    return False


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
        print(('PASS ' if cond else 'FAIL ') + label + ('' if cond or detail is None else '   <- %s' % (str(detail)[:400],)))
    for part in approach_profile_parts(check):
        print('-- %s' % part.__name__)
        part()
    print('\n%d/%d checks passed' % (passed, total))
    return 0 if passed == total else 1


if __name__ == '__main__':
    sys.exit(main())
