"""firmwarefaults.custom.selftest_sc2 — the sc-2 / sc-2b half of the module selftest (FIRMWARE_SCENARIO_PLAN.md §5, §9 sc-2/sc-2b), run
from firmwarefaults_selftest (one count). Campaign aggregation on FIXTURES (Wilson blocks, the time-to-first-fault with censoring, the
likelihood rows), the seeded campaigns and their deterministic stimulus (the press schedule, the drop steps), the claim's evidence tiers
side by side (formal decided outranks a witness, a refutation outranks everything, statistics is a measure not a status), FormalCheck's
outcome mapping in his vocabulary incl. the counterexample read from a fixture trace, the refusal that names FORMAL_ENGINES_URL when no
engine resolves, the cbmc / cppcheck argv, the new harness flags (align-at-pc, flip-bit, drop-frame tx: / rx:p=), the board + formal
workers returning a 100 kB stdout WHOLE (and the client refusing a cut one), the sc-2 API doors over a fake manager, mathproofs' cbmc
checker + evidence fields. No engine runs here — tests/firmwarefaults_probe.py runs the real campaign and the real CBMC pair.
"""
import contextlib
import importlib.util
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))          # the module dir
RFNODE = os.path.abspath(os.path.join(HERE, '..', '..', '..'))               # polari-rf-node


def _rfnode_src(subdir, name, env_var):
    """A file from an rf-node sibling checkout (prf-board-engines, prf-formal-engines, …), resolved the way
    the board/formal engines seam resolves everything else there: an explicit override env var first (for a
    dev checkout laid out differently), then the normal sibling-of-framework layout (RFNODE/<subdir>).
    Returns None — never raises — when neither exists, e.g. inside the backend image, where /app IS the
    framework root with no rf-node parent at all; callers skip honestly instead of crashing the run.
    """
    for base in (os.environ.get(env_var), os.path.join(RFNODE, subdir)):
        if base and os.path.isfile(os.path.join(base, name)):
            return os.path.join(base, name)
    return None


def _board_engines_src(name):
    return _rfnode_src('prf-board-engines', name, 'BOARD_ENGINES_SRC')


def _formal_engines_src(name):
    return _rfnode_src('prf-formal-engines', name, 'FORMAL_ENGINES_SRC')


NM = {'hal_millis': {'addr': 0x1ba, 'space': 'text'}, 'g_ms': {'addr': 0x108, 'space': 'data'}, '__vector_7': {'addr': 0x15c, 'space': 'text'},
      '__bss_end': {'addr': 0x2eb, 'space': 'data'}}
#: the shape polari-cbmc-check writes for the torn build (summarised from the real 2026-10-02 trace)
TRACE_TORN = [{'property': 'main.assertion.1', 'description': 'hal_millis returns g_ms before or after a tick, never a torn mix of both', 'raw_steps': 301,
               'steps': [{'step': 'assign', 'lhs': 'main::1::init', 'value': '4278190076ul'}, {'step': 'assign', 'lhs': 'main::1::pre', 'value': '4278190077ul'},
                         {'step': 'call', 'function': 'polari_isr_timer2_compa'}, {'step': 'assign', 'lhs': 'polari_avr_read_g_ms::1::b0', 'value': '254ul'},
                         {'step': 'call', 'function': 'polari_isr_timer2_compa'}, {'step': 'assign', 'lhs': 'polari_avr_read_g_ms::1::b1', 'value': '255ul'},
                         {'step': 'assign', 'lhs': 'polari_avr_read_g_ms::1::b2', 'value': '255ul'}, {'step': 'assign', 'lhs': 'polari_avr_read_g_ms::1::b3', 'value': '255ul'},
                         {'step': 'assign', 'lhs': 'main::1::r', 'value': '4294967294ul'}, {'step': 'assign', 'lhs': 'main::1::post', 'value': '4278190081ul'},
                         {'step': 'FAILURE', 'property': 'main.assertion.1'}]}]


def _load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def sc2_parts(check):
    def campaigns():
        from firmwarefaults.custom import campaign as C, campaign_runs as CR
        res = C.aggregate([{'rate': 200.0, 'before': (73, 2340), 'after': (0, 2340), 'ttff': [1000.0, None, 2560.0, 300.0], 'window_ms': 10000.0}])
        b, a, t = res[0]['before'], res[0]['after'], res[0]['ttff']
        check('aggregate: 73/2340 → 3.120 % [2.49, 3.90] (Wilson 95 %, sc-1\'s phase-sweep numbers); 0/2340 → 0 [0, 0.164 %]',
              b['events'] == 73 and abs(b['rate'] - 0.031197) < 1e-5 and abs(b['ci_low'] - 0.02489) < 2e-4 and abs(b['ci_high'] - 0.03904) < 2e-4
              and a['rate'] == 0 and a['ci_low'] == 0 and abs(a['ci_high'] - 0.001639) < 2e-5, res)
        check('time to first fault: 3 of 4 seeds observed, 1 censored at the window, median 1000 ms [300 … 2560]',
              t['observed'] == 3 and t['censored'] == 1 and t['median_ms'] == 1000.0 and t['min_ms'] == 300.0 and t['max_ms'] == 2560.0, t)
        aux = C.aggregate([{'rate': 0.5, 'before': (20, 40), 'after': (0, 40), 'after_aux': (5, 40), 'aux_what': 'gave up', 'ttff': None}])
        c = C.find('ack-drop-probability')
        rows = C.likelihood_rows(dict(c, trial_unit='a request'), aux, 'timeout-fsm', 'fixture coverage', '2026-10-02T00:00:00')
        check('likelihood rows: one per rate, BEFORE likelihood + AFTER residual with their intervals, the give-up kept apart in the notes',
              len(rows) == 1 and rows[0]['before_rate'] == 0.5 and rows[0]['after_events'] == 0 and 'gave up: 5/40' in rows[0]['notes']
              and rows[0]['name'] == 'lost-ack-hang@drop_p=0.5' and rows[0]['technique'] == 'timeout-fsm' and rows[0]['ttff_median_ms'] == -1.0, rows)
        check('four seeded campaigns: scenario 1 phase (200/s, 60 seeds), scenario 4 BER (1e-3/1e-4/1e-5), scenario 3 bounce window (5 lengths), '
              'scenario 2 drop probability (0.5/0.2/0.1) — each with its stimulus, its two events and what time-to-first-fault means',
              {x['name']: (x['scenario'], json.loads(x['rates_json'])) for x in C.SEED_CAMPAIGNS} == {
                  'torn-read-phase': ('torn-millis-read', [200.0]), 'uart-ber': ('uart-residual-frame-loss', [1e-3, 1e-4, 1e-5]),
                  'bounce-window': ('button-bounce-double-count', [0.02, 5.0, 15.0, 25.0, 40.0]),
                  'ack-drop-probability': ('lost-ack-hang', [0.5, 0.2, 0.1])}
              and all(x['stimulus'] and x['event_before'] and x['event_after'] and x['ttff_what'] and x['kind'] in CR.RUNNERS for x in C.SEED_CAMPAIGNS))
        s1, s2 = CR.press_schedule(3, 25.0), CR.press_schedule(3, 25.0)
        check('the bounce stimulus is DETERMINISTIC from (seed, window): 12 presses ≥ 60 ms apart, each bounce within (0, 25 ms] after its press',
              s1 == s2 and len(s1) == 12 and all(0 < b - p <= 25.0e-3 * 16e6 + 1 for p, b in s1)
              and all(s1[i + 1][0] - s1[i][0] >= 0.06 * 16e6 - 1 for i in range(11)) and s1 != CR.press_schedule(4, 25.0))
        st = CR.bounce_steps(s1)
        check('…rendered as 24 INT0 raises (irq-at-cycle, vector 1), forcible by the harness (≤ 64 --irq-at)',
              len(st) == 24 and all(x['kind'] == 'irq-at-cycle' and json.loads(x['args_json'])['vec'] == 1 for x in st))
        ds = CR.drop_steps(0.2)
        check('the drop campaign swaps lost-ack-hang\'s "drop the 1st ack" for drop-prob p (the scripted host unchanged)',
              [x['kind'] for x in ds] == ['respond', 'drop-prob'] and json.loads(ds[1]['args_json']) == {'p': 0.2})

    def claim_tiers():
        from firmwarefaults.custom.claim_bridge import add_evidence, merge_tier, strongest, write
        from firmwarefaults.custom.sink import LocalSink
        sink = LocalSink()
        sc = {'name': 'torn-millis-read', 'fault': 'torn-read-g-ms', 'fault_class': 'TornReadFault', 'expected_observable': 'x'}
        run = {'name': 'r1', 'build_name': 'uno-sim-rig-abc', 'variant': 'uno-sim-rig', 'outcome': 'passed', 'seed': 0, 'side': 'after', 'ran_at': 't1',
               'verdict_words': 'monotone', 'harness_digest': 'h', 'wall_s': 0.1, 'uptime_sequence': '', 'firmware_sha256': 'f'}
        n, after, _ = write(sink, run, sc)
        check('a sim witness writes the sim tier entry beside the status', after == 'witnessed' and json.loads(sink.get('MathClaim', n)['evidence_tiers_json'])[0]['tier'] == 'sim')
        b, a = add_evidence(sink, n, {'tier': 'formal', 'status': 'decided', 'ref': 'hal-millis-not-torn@uno-sim-rig', 'measure': 'decided (bounded, k=2)'})
        cl = sink.get('MathClaim', n)
        check('a formal DECIDED raises witnessed → decided (checker cbmc, evidence analytical), both tiers kept side by side',
              (b, a) == ('witnessed', 'decided') and cl['proof_status'] == 'decided' and cl['checker'] == 'cbmc' and cl['evidence_level'] == 'analytical'
              and [t['tier'] for t in json.loads(cl['evidence_tiers_json'])] == ['sim', 'formal'], cl)
        write(sink, dict(run, name='r2', ran_at='t2'), sc)
        cl = sink.get('MathClaim', n)
        check('…a later sim witness never lowers decided (one more interleaving is weaker than a bounded decision)', cl['proof_status'] == 'decided'
              and cl['checker'] == 'cbmc' and len(json.loads(cl['evidence_tiers_json'])) == 3, cl['proof_status'])
        add_evidence(sink, n, {'tier': 'statistics', 'status': 'measured', 'ref': 'torn-read-phase', 'measure': '0/2340'},
                     measure={'values': [{'events': 0, 'trials': 2340}]})
        cl = sink.get('MathClaim', n)
        check('a statistics tier leaves the STATUS (still decided) and writes the likelihood into measure_json', cl['proof_status'] == 'decided'
              and json.loads(cl['measure_json'])['statistics']['values'][0]['trials'] == 2340)
        b, a = add_evidence(sink, 'fw-safe:torn-millis-read:uno-sim-rig-torn-x', {'tier': 'formal', 'status': 'refuted', 'ref': 'c'},
                            base={'description': 'fixture'}, counterexample={'values': {'r': 511}})
        cl = sink.get('MathClaim', 'fw-safe:torn-millis-read:uno-sim-rig-torn-x')
        check('a formal REFUTED on a claim the CLI has not seen creates it refuted with the CBMC counterexample',
              a == 'refuted' and cl['counterexample_json'] == json.dumps({'values': {'r': 511}}) and cl['kind'] == 'safe-under-scenario')
        check('strongest(): refuted outranks every tier; decided > witnessed; an inapplicable tier never erases a witness',
              strongest('decided', 'refuted') == 'refuted' and strongest('refuted', 'decided') == 'refuted' and strongest('witnessed', 'decided') == 'decided'
              and strongest('witnessed', 'inapplicable') == 'witnessed' and strongest('conjectured', 'inapplicable') == 'inapplicable')
        check('merge_tier keeps ONE entry per (tier, ref): the newest replaces the older',
              len(merge_tier([{'tier': 'formal', 'ref': 'a', 'at': 1}], {'tier': 'formal', 'ref': 'a', 'at': 2})) == 1)

    def formal_logic():
        from firmwarefaults.custom import formal as F
        chk = F.find('hal-millis-not-torn@uno-sim-rig')
        o = F.outcome_of({'verdict': 'holds', 'properties': []}, chk)
        check('CBMC holds → decided (bounded, k=2) — the words say "not proved"', o['outcome'] == 'decided' and o['claim_status'] == 'decided (bounded, k=2)'
              and 'not proved' in o['words'] and 'proved' not in o['claim_status'])
        o = F.outcome_of({'verdict': 'refuted', 'properties': [{'property': 'main.assertion.1', 'status': 'FAILURE', 'description': 'torn'}]}, chk)
        check('CBMC failure → refuted, naming the property', o['outcome'] == 'refuted' and 'main.assertion.1' in o['words'])
        check('only an unwinding assertion failed → undetermined (the bound decided nothing); a timeout → undetermined (budget), never refuted',
              F.outcome_of({'verdict': 'bound-too-small'}, chk)['outcome'] == 'undetermined' and F.outcome_of({'verdict': 'timeout'}, chk)['outcome'] == 'undetermined'
              and 'never a counterexample' in F.outcome_of({'verdict': 'timeout'}, chk)['words'])
        o = F.outcome_of({'verdict': 'refused-at-compile', 'why': ['hal.c:25:1: error: static assertion failed: RX_RING must be a power of two']}, F.find('rx-ring-index-bound@uno-sim-rig-ring512'))
        check('the source does not compile (hal.c\'s _Static_assert) → inapplicable, quoting the assertion', o['outcome'] == 'inapplicable' and 'RX_RING' in o['words'])
        check('a run that failed to run → error (the claim is left as it was)', F.outcome_of({'verdict': 'error', 'why': ['x']}, chk)['outcome'] == 'error')
        cx = F.counterexample(TRACE_TORN, F.find('hal-millis-not-torn@uno-sim-rig-torn'))
        check('the counterexample from a fixture trace: pre 0xFEFFFFFD, returned 0xFFFFFFFE, post 0xFF000001, bytes FE FF FF FF, 2 ISR runs',
              cx['values']['r'] == 0xFFFFFFFE and cx['values']['pre'] == 0xFEFFFFFD and cx['isr_calls'] == 2 and 'returned 0xFFFFFFFE' in cx['reads']
              and '0xFE 0xFF 0xFF 0xFF' in cx['reads'], cx)
        a = F.argv_for(chk)
        check('the cbmc-check argv: both TUs, the stubs first, --16 (int 16 bits as avr-gcc), the volatile model + --isr, -D POLARI_K=2, --unwind 4',
              a[:4] == ['--src', 'hal_millis_isr.c', '--src', 'g_ms_avr_model.c'] and ['--width', '16'] == a[a.index('--width'):a.index('--width') + 2]
              and 'g_ms:polari_avr_read_g_ms' in a and a[a.index('--isr') + 1] == 'polari_tick' and 'POLARI_K=2' in a and a[a.index('--unwind') + 1] == '4')
        check('four FormalChecks: hal_millis atomic → decided, bare → refuted; the ring at 64 → decided, at 512 → inapplicable; each with its limits',
              {c['name']: c['expected'] for c in F.FORMAL_CHECKS} == {'hal-millis-not-torn@uno-sim-rig': 'decided', 'hal-millis-not-torn@uno-sim-rig-torn': 'refuted',
                                                                      'rx-ring-index-bound@uno-sim-rig': 'decided', 'rx-ring-index-bound@uno-sim-rig-ring512': 'inapplicable'}
              and all('no AVR architecture' in r['limits'] for r in F.seed_rows()))
        stubs = F.stub_files()
        check('the model files exist: two harnesses + the AVR model unit, stubs for avr/io.h, avr/interrupt.h, util/atomic.h, avr/wdt.h, stdint.h, stddef.h',
              all(os.path.isfile(os.path.join(F.FORMAL_DIR, f)) for f in ('hal_millis_isr.c', 'g_ms_avr_model.c', 'rx_ring_bound.c'))
              and {'stubs/avr/io.h', 'stubs/avr/interrupt.h', 'stubs/util/atomic.h', 'stubs/avr/wdt.h', 'stubs/stdint.h', 'stubs/stddef.h'} <= set(stubs))
        src = open(os.path.join(F.FORMAL_DIR, 'hal_millis_isr.c')).read()
        check('the harness #includes the variant\'s OWN hal.c (never a copy) and asserts pre <= r <= post', '#include "hal.c"' in src and 'r >= pre && r <= post' in src)

    def refusal():
        from firmwarefaults.custom import formal_engines as fe, formal as F
        from firmwarefaults.custom.sink import LocalSink
        saved = (fe.local_image, fe.topology_url, os.environ.get(fe.KNOB), fe.shutil.which)
        try:
            os.environ.pop(fe.KNOB, None)
            fe.local_image = lambda: ''
            fe.topology_url = lambda: ''
            fe.shutil.which = lambda b: None
            w = fe.resolve('cbmc-check')
            check('no engine anywhere → refused, naming FORMAL_ENGINES_URL, the image and the provider module',
                  w['how'] == 'refused' and 'FORMAL_ENGINES_URL' in w['why'] and 'prf-formal-engines' in w['why'] and 'firmwarefaults.formal' in w['why'], w)
            try:
                F.run_check('hal-millis-not-torn@uno-sim-rig', LocalSink(), home='/nonexistent-polari')
                why = ''
            except fe.FormalRefused as e:
                why = str(e)
            except Exception as e:  # noqa: BLE001 — gen failing first would also be a refusal of a kind; report it
                why = 'other: %s' % e
            check('…run_check refuses before anything runs (FormalRefused, the knob named)', 'FORMAL_ENGINES_URL' in why, why[:200])
            os.environ[fe.KNOB] = 'http://127.0.0.1:9'
            fe._CAP.clear()
            w = fe.resolve('cbmc-check')
            check('FORMAL_ENGINES_URL set but unreachable → refused (a declared worker never silently falls back to local)',
                  w['how'] == 'refused' and 'unreachable' in w['why'] and 'FORMAL_ENGINES_URL' in w['why'], w)
        finally:
            fe.local_image, fe.topology_url, fe.shutil.which = saved[0], saved[1], saved[3]
            if saved[2] is None:
                os.environ.pop(fe.KNOB, None)
            else:
                os.environ[fe.KNOB] = saved[2]
            fe._CAP.clear()

    def harness_flags():
        from firmwarefaults.custom import harness as H
        step = {'kind': 'align-at-pc', 'args_json': json.dumps({'vec': 7}), 'condition_json': json.dumps({'symbol': 'g_ms', 'width': 4, 'mask': 255, 'value': 255})}
        a = ' '.join(H.render([(step, {'pc': 0x1be, 'vec': 7})], NM, 0.6, 0))
        check('align-at-pc renders --align-at-pc pc=0x1be,vec=7,shots=1,when=0x108/4&0xff=0xff (the same PC service, no extra tick)',
              '--align-at-pc pc=0x1be,vec=7,shots=1,when=0x108/4&0xff=0xff' in a and '--irq-at' not in a, a)
        a, files, meta = H.render_sc1([{'kind': 'flip-bit-at-cycle', 'args_json': json.dumps({'symbol': 'g_ms', 'byte': 1, 'bit': 3, 'cycle': 1600000})},
                                       {'kind': 'drop-nth-frame', 'args_json': json.dumps({'direction': 'tx', 'n': 1, 'msg_type': 0x7F})},
                                       {'kind': 'drop-prob', 'args_json': json.dumps({'p': 0.2})}], NM, 1.0, 5, {}, 'uno-sim-rig')
        j = ' '.join(a)
        check('flip-bit renders --flip-bit 0x109:3@1600000 (g_ms + byte 1, by symbol); drop-nth-frame tx → --drop-frame tx:1,type=0x7f; drop-prob → rx:p=0.2',
              '--flip-bit 0x109:3@1600000' in j and '--drop-frame tx:1,type=0x7f' in j and '--drop-frame rx:p=0.2' in j and not meta['missing'], j)
        a, files, meta = H.render_sc1([{'kind': 'flip-bit-at-cycle', 'args_json': json.dumps({'symbol': 'nope', 'bit': 0, 'cycle': 1})}], NM, 1.0, 0, {}, 'x')
        check('…a flip aimed at a symbol this build lacks → missing (inapplicable here, with the reason)', meta['missing'] and 'nope' in meta['missing'][0])
        tf, io_path = _board_engines_src('twin_forcing.c'), _board_engines_src('twin_scenario_io.c')
        if not (tf and io_path):
            print('  SKIP harness_flags: prf-board-engines source not present in this image (%s)'
                  % os.path.join(RFNODE, 'prf-board-engines', 'twin_forcing.c'))
            return
        c = open(tf).read()
        io_c = open(io_path).read()
        check('the harness C: --align-at-pc (swallow the next genuine raise via the vector\'s enable bit), --flip-bit, 64 --irq-at; '
              '--drop-frame tx:N[,type=] (frame start 4C 50 02) and rx:p=P (one draw per unit)',
              '"--align-at-pc"' in c and '"--flip-bit"' in c and '#define MAX_IRQ_AT 64' in c and 'swallow_check' in c
              and '"tx:"' in io_c and '"rx:p="' in io_c and "g_txq[0].b == 0x4C && g_txq[1].b == 0x50 && g_txq[2].b == 0x02" in io_c)

    def decisions():
        from firmwarefaults.custom import outcome as O
        frames = [(t * 100.0 + 0.7, 1, t) for t in range(20)] + [(503.2, 0x7F, -1), (553.2, 0x7F, 91)]
        d = O.decide_telemetry(sorted(frames), 2000.0, 250, True, 2, lost='the request')
        check('S2 the other way (lost-request-hang): the dropped request still counts as SENT → the retry is seen → passed, "the request was lost"',
              d['outcome'] == 'passed' and d['words'].startswith('the request was lost'), d)
        check('align words: swallowed → "advanced, not added"; merged → nothing swallowed; never came → an extra tick is possible (said)',
              'ADVANCED' in O.align_words({'swallow': 'swallowed', 'advanced_by_cycles': 15893}) and 'merged' in O.align_words({'swallow': 'merged'})
              and 'extra tick is possible' in O.align_words({'swallow': 'pending-never-came'}))

    def static():
        from firmwarefaults.custom import static_rules as SR
        a = SR.argv({'hal.c': b'', 'main.c': b'', 'stubs/avr/io.h': b''})
        check('cppcheck argv: avr8, c99, warning+style+portability+performance, --addon threadsafety, the stubs as headers, the project\'s .c files',
              a[:4] == ['--platform', 'avr8', '--std', 'c99'] and 'warning,style,portability,performance' in a and a[a.index('--addon') + 1] == 'threadsafety'
              and a[-2:] == ['hal.c', 'main.c'])
        check('MISRA is NOT run and every row says why (the rule texts are not free)', 'MISRA' in SR.NOT_RUN.upper() and 'non-free' in SR.NOT_RUN)
        r = SR.counts_row({'findings': [{'severity': 'style'}] * 6 + [{'severity': 'warning'}], 'counts': {'style': 6, 'warning': 1}, 'run_info': [1]})
        check('the per-variant row counts findings by severity (run information kept apart)', (r['findings'], r['style'], r['warnings'], r['run_info']) == (7, 6, 1, 1))
        vs = SR.all_variants()
        check('every UNO variant is scanned: board\'s 6 (ucd-0e2: + uno-button-clock) + the 11 scenario variants = 17',
              len(vs) == 17 and 'uno-sim-rig-torn' in vs and 'uno-echo' in vs and 'uno-button-clock' in vs, vs)

    def workers():
        import falcon.testing
        svc_path = _board_engines_src('board_engines_service.py')
        fsvc_path = _formal_engines_src('formal_engines_service.py')
        if not (svc_path and fsvc_path):
            print('  SKIP workers: prf-board-engines/prf-formal-engines source not present in this image (%s)'
                  % os.path.join(RFNODE, 'prf-board-engines', 'board_engines_service.py'))
            return
        sys.path.insert(0, os.path.dirname(svc_path))
        try:
            svc = _load(svc_path, 'polari_board_engines_service_selftest')
        finally:
            sys.path.pop(0)
        svc.ENGINES['avr-objdump'] = os.path.basename(sys.executable)
        c = falcon.testing.TestClient(svc.app)
        r = c.simulate_post('/run', json={'engine': 'avr-objdump', 'args': ['-c', "import sys; sys.stdout.write('x' * 99999 + 'Z')"]}).json
        check('the board worker returns a 100 kB stdout WHOLE (was: its last 20 000 characters — scenario 1 lost hal_millis through the worker)',
              r.get('ok') and len(r['stdout']) == 100000 and r['stdout'].endswith('Z') and r['stdout'].startswith('x') and r['stdout_chars'] == 100000, str(r)[:200])
        fsvc = _load(fsvc_path, 'polari_formal_engines_service_selftest')
        fsvc.ENGINES['cbmc'] = os.path.basename(sys.executable)
        r = falcon.testing.TestClient(fsvc.app).simulate_post('/run', json={'engine': 'cbmc', 'args': ['-c', "print(open('stubs/avr/io.h').read())"],
                                                                            'files': {'stubs/avr/io.h': 'AVR'}}).json
        check('the formal worker keeps a model\'s RELATIVE paths (stubs/avr/io.h) and returns stdout whole', r.get('ok') and r['stdout'].strip() == 'AVR', str(r)[:200])
        bad = falcon.testing.TestClient(fsvc.app).simulate_post('/run', json={'engine': 'cbmc', 'args': [], 'files': {'../x': 'y'}})
        check('…and refuses a path that climbs out of the job (..)', bad.status_code == 400)
        from board.custom import engine_run
        from polariApiServer import outbound
        saved = outbound.http_request

        @contextlib.contextmanager
        def fake(*a, **k):
            yield io.BytesIO(json.dumps({'ok': True, 'returncode': 0, 'stdout': 'x' * 20000, 'stdout_chars': 86890, 'stderr': '', 'stderr_chars': 0}).encode())
        outbound.http_request = fake
        try:
            engine_run._remote('http://w', 'avr-objdump', ['-d', 'firmware.elf'], {}, 10)
            why = ''
        except engine_run.EngineRefused as e:
            why = str(e)
        finally:
            outbound.http_request = saved
        check('the client REFUSES a cut stream (stdout 20 000 of 86 890 characters) instead of parsing half a disassembly', 'arrived cut' in why and '86890' in why, why)

    def api_and_proofs():
        from types import SimpleNamespace
        import falcon
        from falcon import testing
        from firmwarefaults.firmwarefaults_seed import FIRMWAREFAULTS_SEED_PAIRS
        from firmwarefaults.firmwarefaults_endpoints import construct_firmwarefaults_endpoints
        from firmwarefaults.custom import formal_engines as fe
        tables = {}
        mgr = SimpleNamespace(objectTables=tables, idList=[], db=None)
        for cname, cls, rows in FIRMWAREFAULTS_SEED_PAIRS:
            if cname in ('ScenarioCampaign', 'FormalCheck'):
                for r in rows:
                    o = cls(manager=mgr, **{k: v for k, v in r.items() if k != '_converge'})
                    tables.setdefault(cname, {})[o.id] = o
        app = falcon.App()
        construct_firmwarefaults_endpoints(SimpleNamespace(falconServer=app, manager=mgr, idList=[]))
        c = testing.TestClient(app)
        g = c.simulate_get('/api/firmwarefaults/campaigns').json
        f = c.simulate_get('/api/firmwarefaults/formal').json
        check('GET /campaigns lists the 4 seeded campaigns; GET /formal the 9 checks (4 CBMC + 5 Mthread, sc-2c) + where cbmc-check would run '
              '(the FORMAL_ENGINES_URL ladder)',
              len(g['campaigns']) == 4 and len(f['checks']) == 9 and f['engines']['knob'] == 'FORMAL_ENGINES_URL')
        check('GET /likelihoods and GET /static answer (empty until a campaign / a static run)',
              c.simulate_get('/api/firmwarefaults/likelihoods').json['likelihoods'] == [] and c.simulate_get('/api/firmwarefaults/static').json['checks'] == [])
        check('POST /campaign with an unknown name → 400; POST /formal with an unknown check → 400',
              c.simulate_post('/api/firmwarefaults/campaign', body='{"campaign": "nope"}').status_code == 400
              and c.simulate_post('/api/firmwarefaults/formal', body='{"checks": ["nope"]}').status_code == 400)
        saved = fe.resolve
        fe.resolve = lambda e: {'how': 'refused', 'where': '', 'why': fe.refusal_text(e)}
        try:
            r = c.simulate_post('/api/firmwarefaults/formal', body=json.dumps({'checks': ['hal-millis-not-torn@uno-sim-rig']}))
        finally:
            fe.resolve = saved
        check('POST /formal with no engine → 409, the reason names FORMAL_ENGINES_URL', r.status_code == 409 and 'FORMAL_ENGINES_URL' in r.json['error'], r.json)
        import inspect
        from mathproofs.mathproofs_basis import CHECKERS, MathClaim, EVIDENCE_TIERS
        p = inspect.signature(MathClaim.__init__).parameters
        check('mathproofs: checker cbmc; MathClaim carries evidence_tiers_json + measure_json; the tiers sim, statistics, formal, static',
              'cbmc' in CHECKERS and 'evidence_tiers_json' in p and 'measure_json' in p and EVIDENCE_TIERS == ('sim', 'statistics', 'formal', 'static'))
        from firmwarefaults.custom import scenarios as SC
        check('the sc-2 scenarios: torn-millis-read-aligned (one align-at-pc step), lost-request-hang (respond + drop-nth-frame tx, msg_type 0x7F)',
              [s['kind'] for s in SC.steps_of('torn-millis-read-aligned')] == ['align-at-pc']
              and json.loads(SC.steps_of('lost-request-hang')[1]['args_json']) == {'direction': 'tx', 'n': 1, 'msg_type': 0x7F})

    def stage():
        st = _load(os.path.join(HERE, '..', '..', 'tests', 'scenarios_stage.py'), 'polari_scenarios_stage_selftest')
        side = lambda o, c, v='v': {'outcome': o, 'claim_status': c, 'variant': v, 'observed': '', 'words': 'w', 'wall_s': 0.1}  # noqa: E731
        pairs = [{'scenario': 'ok', 'seed': 0, 'before': side('failed', 'refuted'), 'after': side('passed', 'witnessed'), 'rc': 0},
                 {'scenario': 'formal', 'seed': 0, 'before': side('failed', 'refuted'), 'after': side('passed', 'decided'), 'rc': 0},
                 {'scenario': 'broken', 'seed': 0, 'before': side('failed', 'refuted'), 'after': side('failed', 'refuted'), 'rc': 0},
                 {'scenario': '1b', 'seed': 0, 'before': side('inapplicable', 'inapplicable'), 'after': None, 'rc': 0},
                 {'scenario': '1b-open', 'seed': 0, 'before': side('undetermined', 'undetermined'), 'after': None, 'rc': 0},
                 {'scenario': 'crash', 'seed': 0, 'before': None, 'after': None, 'rc': 1, 'error': 'EngineRefused: no twin'},
                 {'scenario': 'lost-fault', 'seed': 0, 'before': side('passed', 'witnessed'), 'after': side('passed', 'witnessed'), 'rc': 0}]
        red, warn, counts = st.judge(pairs)
        check('tests/scenarios_stage.py judges like scenarios.sh: red = an AFTER not held, a guard that no longer refuses, a pair that did not run; '
              'a formal decided counts as held; a BEFORE that no longer fails is a warning; the counts sc-4 expects',
              sorted(r['scenario'] for r in red) == ['1b-open', 'broken', 'crash'] and [w['scenario'] for w in warn] == ['lost-fault']
              and counts == {'pairs': 7, 'witnessed': 3, 'refused_builds': 1, 'red': 3}, (red, warn, counts))

    return (campaigns, claim_tiers, formal_logic, refusal, harness_flags, decisions, static, workers, api_and_proofs, stage)
