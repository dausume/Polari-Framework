"""
@module firmwarefaults.custom.selftest_sc3

sc-3 checks for firmwarefaults_selftest (no twin needed — the REAL runs are tests/firmwarefaults_probe.py's sc-3 part):
the RTOS rows (forcible on qemu-esp32c3 only), the forcing recipe → the params partition bytes, the seeded knob draw, the
firmware ↔ host contract (event numbers, the params struct, the partition offset), the trace parser, the wait-for graph and the
inversion analysis on FIXTURE traces (failed / passed / undetermined, a transient cycle, the chain-is-not-a-cycle regression),
and the campaign's statistics over fake runs (Wilson, the likelihood row, the fault row, the claims' statistics tier).

    run(check)
"""
import json
import os
import re
import struct

HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATE = os.path.join(HERE, '..', '..', 'board', 'custom', 'firmware', 'esp32c3')

# a priority-inversion round, BEFORE (binary semaphore): L takes R, H blocks, M runs 10 ms inside H's wait, L gives, H takes
PI_BEFORE = """@BOOT app=prio_inversion rig=c3-scenario params=flash seed=0 window_ms=1000 rounds=1 a=1,2,3000,10000,40,5000,0,0
@ROUND 0 69250 81361 12111
@PI kind=binary-semaphore rounds=1 of=1 worst_us=12111 bound_us=3000 deadline_us=5000 misses=1 h_off=1 m_off=2 m_busy_us=10000 params=flash
@TRACE events=12 dropped=0 cap=4096 clock=esp_timer_us
@TASK 1 L prio=2
@TASK 2 M prio=3
@TASK 3 H prio=4
@LOCK 0 R binary-semaphore
@EV 68300 1 1 0 0
@EV 68308 2 1 0 0
@EV 69244 1 3 0 0
@EV 69250 3 3 0 0
@EV 69252 1 1 0 0
@EV 70240 1 2 0 0
@EV 80250 1 1 0 0
@EV 81340 4 1 0 0
@EV 81350 1 3 0 0
@EV 81355 2 3 0 0
@EV 81460 4 3 0 0
@END t_us=200000
"""
# the same round AFTER (a mutex): L raised to 4 at H's block, M never runs inside H's wait
PI_AFTER = """@BOOT app=prio_inversion rig=c3-scenario params=flash seed=0 window_ms=1000 rounds=1 a=1,2,3000,10000,40,5000,0,0
@ROUND 0 69245 71340 2095
@PI kind=mutex rounds=1 of=1 worst_us=2095 bound_us=3000 deadline_us=5000 misses=0 h_off=1 m_off=2 m_busy_us=10000 params=flash
@TASK 1 L prio=2
@TASK 2 M prio=3
@TASK 3 H prio=4
@LOCK 0 R mutex
@EV 68300 1 1 0 0
@EV 68308 2 1 0 0
@EV 69244 1 3 0 0
@EV 69250 3 3 0 0
@EV 69252 5 1 0 4
@EV 69258 1 1 0 0
@EV 71334 4 1 0 0
@EV 71335 6 1 0 2
@EV 71341 1 3 0 0
@EV 71343 2 3 0 0
@EV 71451 4 3 0 0
@EV 71460 1 2 0 0
@END t_us=200000
"""
LOCK_HEAD = """@BOOT app=two_lock rig=c3-scenario params=flash seed=0 window_ms=1500 rounds=1 a=2,1,1,500,50,300,0,0
@TASK 4 T1 prio=3
@TASK 5 T2 prio=3
@LOCK 0 A mutex
@LOCK 1 B mutex
"""
# BEFORE: T1 A, T2 B, T1 blocks on B, T2 blocks on A — the cycle closes at 370365 and stays
LOCK_BEFORE = LOCK_HEAD + """@DEADLOCK detected_us=378347 detected_tick=378 T1=Blocked T1_waits=B A_held_by=T1 T2=Blocked T2_waits=A B_held_by=T2 rounds=0,0
@LOCKS technique=none order=T1:A-then-B,T2:B-then-A timeout_ms=0 rounds=0,0 of=1 backoffs=0,0 deadlock=1 t1_gap=2 t2_start=1 t2_gap=1 params=flash
@EV 368355 7 4 0 6
@EV 368359 2 4 0 0
@EV 369351 2 5 1 0
@EV 370353 3 4 1 0
@EV 370365 3 5 0 0
@END t_us=1892000
"""
# the back-off AFTER: the same cycle closes, T1's timed take on B expires, T1 gives A, T2 takes A — then both finish
LOCK_BACKOFF = LOCK_HEAD + """@LOCKS technique=timeout-backoff order=T1:A-then-B,T2:B-then-A timeout_ms=5 rounds=1,1 of=1 backoffs=1,0 deadlock=0 t1_gap=2 t2_start=1 t2_gap=1 params=flash
@EV 368355 7 4 0 6
@EV 368359 2 4 0 0
@EV 369351 2 5 1 0
@EV 370346 3 4 1 0
@EV 370365 3 5 0 0
@EV 375332 8 4 1 0
@EV 375334 4 4 0 0
@EV 375336 2 5 0 0
@EV 375900 4 5 0 0
@EV 375902 4 5 1 0
@EV 376400 2 4 0 0
@EV 376402 2 4 1 0
@EV 376903 7 4 4 8
@END t_us=1892000
"""
# a CHAIN, not a cycle: T1 waits B held by T2, T2 waits for nothing (the false self-loop sc-3 fixed)
LOCK_CHAIN = LOCK_HEAD + """@EV 368359 2 4 0 0
@EV 369351 2 5 1 0
@EV 370353 3 4 1 0
@END t_us=400000
"""


def _defines(path):
    return {m.group(1): int(m.group(2)) for m in re.finditer(r'#define\s+(\w+)\s+(\d+)', open(path).read())}


def run(check):
    from firmwarefaults.custom import scenarios as SC, scenarios_sc3 as S3, c3_trace as C, outcome_sc3 as O
    names = [s['name'] for s in S3.SC3_SCENARIOS]
    rows = [SC.find(n) for n in names]
    check('sc-3 rows: priority-inversion-mutex, two-lock-deadlock, two-lock-deadlock-backoff — runnable, on esp32-c3 / qemu-esp32c3, each a pair of '
          'board\'s C3 variants differing in one flag',
          names == ['priority-inversion-mutex', 'two-lock-deadlock', 'two-lock-deadlock-backoff'] and all(SC.runnable(r) for r in rows)
          and all(r['simulator'] == 'qemu-esp32c3' and r['target_board'] == 'esp32-c3' for r in rows)
          and [(r['before_variant'], r['after_variant'], r['technique']) for r in rows]
          == [('c3-prio-inversion', 'c3-prio-inversion-mutex', 'priority-inheritance'), ('c3-two-lock', 'c3-two-lock-ordered', 'lock-ordering'),
              ('c3-two-lock', 'c3-two-lock-backoff', 'try-lock-backoff')])
    from board.custom import variants_c3 as VC
    check('…and every variant they name is a seeded C3 variant', all(VC.find(v)['board_definition'] == 'esp32-c3' for r in rows for v in (r['before_variant'], r['after_variant'])))
    why = SC.refusal(dict(rows[1], simulator='avr-twin'))
    check('hold-lock-order is forcible on qemu-esp32c3 ONLY: the same row on the avr-twin is refused, naming the simulator', 'qemu-esp32c3' in why and 'avr-twin' in why, why)
    args = json.loads(SC.steps_of('priority-inversion-mutex')[0]['args_json'])
    b0, k0 = S3.params_bytes(args, 0)
    mag, ver, seed, win, rounds, *a = struct.unpack('<IIIII8i', b0)
    check('seed 0 = the recipe: params bytes = polari_params_t (52 B: "PSC3", v1, seed, window, rounds, the six slots in order)',
          len(b0) == 52 and mag == S3.PARAMS_MAGIC and b0[:4] == b'PSC3' and (ver, seed, win, rounds) == (1, 0, 1000, 10) and a[:6] == [1, 2, 3000, 10000, 40, 5000]
          and a[6:] == [0, 0], (mag, ver, seed, win, rounds, a))
    draws = [S3.knobs_for(args, k) for k in range(1, 41)]
    check('seed k draws the seeded knobs inside their ranges, deterministically (the same seed → the same knobs), the rest stay the recipe\'s',
          all(0 <= d['h_off_ticks'] <= 3 and 0 <= d['m_off_ticks'] <= 4 and d['l_cs_us'] == 3000 for d in draws)
          and S3.knobs_for(args, 7) == S3.knobs_for(args, 7) and len({(d['h_off_ticks'], d['m_off_ticks']) for d in draws}) >= 10)
    hdr = _defines(os.path.join(TEMPLATE, 'main', 'polari_trace.h'))
    check('the firmware ↔ host contract: polari_trace.h\'s event numbers = c3_trace\'s',
          (hdr['POLARI_EV_SWITCH_IN'], hdr['POLARI_EV_TAKE'], hdr['POLARI_EV_BLOCK'], hdr['POLARI_EV_GIVE'], hdr['POLARI_EV_INHERIT'], hdr['POLARI_EV_DISINHERIT'],
           hdr['POLARI_EV_MARK'], hdr['POLARI_EV_TIMEOUT']) == (C.SWITCH_IN, C.TAKE, C.BLOCK, C.GIVE, C.INHERIT, C.DISINHERIT, C.MARK, C.TIMEOUT), hdr)
    c3h = open(os.path.join(TEMPLATE, 'main', 'polari_c3.h')).read()
    parts = open(os.path.join(TEMPLATE, 'partitions.csv')).read()
    check('…the params struct (magic, version, seed, window_ms, rounds, a[8]), its magic and the `polari` partition offset agree with the runner',
          re.search(r'uint32_t magic;.*uint32_t version;.*uint32_t seed;.*uint32_t window_ms;.*uint32_t rounds;.*int32_t a\[8\];', c3h, re.S) is not None
          and '0x33435350u' in c3h and re.search(r'^polari,\s*data,\s*0x40,\s*0x110000,', parts, re.M) is not None and S3.PARAMS_OFFSET == 0x110000)
    d = C.parse(PI_BEFORE)
    blk = C.blocked(d, 'H', 'R')
    check('the trace parser: tasks, locks, the app line, @END\'s virtual µs; H\'s wait BLOCK → TAKE with who ran inside it (M 10 010 µs)',
          d['tasks'][3]['name'] == 'H' and d['locks'][0]['kind'] == 'binary-semaphore' and d['pi']['of'] == 1 and d['end_us'] == 200000
          and blk[0]['wait_us'] == 81355 - 69250 and blk[0]['ran'].get('M') == 80250 - 70240, blk)
    dec = O.decide_inversion(d, 3000)
    check('inversion BEFORE → failed: H 12 111 µs > 4 000 µs (L\'s section + one tick), M\'s run named inside H\'s wait, no inheritance',
          dec['outcome'] == 'failed' and dec['worst_us'] == 12111 and dec['m_inside_us'] == 10010 and dec['inherit_events'] == 0
          and 'PRIORITY INVERSION' in dec['words'], dec)
    da = O.decide_inversion(C.parse(PI_AFTER), 3000)
    check('inversion AFTER → passed: H 2 095 µs ≤ 4 000 µs, one inheritance event (L raised to 4), M 0 µs inside H\'s wait',
          da['outcome'] == 'passed' and da['worst_us'] == 2095 and da['inherit_events'] == 1 and da['m_inside_us'] == 0, da)
    du = O.decide_inversion(C.parse(PI_BEFORE.split('@ROUND')[0] + '@END t_us=1\n'), 3000)
    check('no round in the window → undetermined (never a pass)', du['outcome'] == 'undetermined', du)
    dl = C.parse(LOCK_BEFORE)
    wf = C.wait_for(dl)
    tel = [{'uptime_ms': 118}, {'uptime_ms': 218}, {'uptime_ms': 318}]
    dd = O.decide_deadlock(dl, wf, tel, dl['end_us'])
    check('deadlock BEFORE → failed: the cycle T1 → B → T2 → A → T1 closes at 370 365 µs (tick 370) and persists; telemetry\'s last frame at 318 ms, '
          'then 1 574 ms of silence; the app\'s own @DEADLOCK beside it',
          dd['outcome'] == 'failed' and wf['persistent']['cycle'] == ['T1', 'B', 'T2', 'A', 'T1'] and wf['persistent']['t_us'] == 370365
          and dd['last_frame_ms'] == 318 and round(dd['silent_ms']) == 1574 and dd['app_deadlock']['T1_waits'] == 'B', (wf, dd))
    db = O.decide_deadlock(C.parse(LOCK_BACKOFF), C.wait_for(C.parse(LOCK_BACKOFF)), tel, 1892000)
    check('back-off AFTER → passed: a TRANSIENT cycle (closed 370 365 µs, broken by T1\'s timed take on B at 375 332 µs), every round done, back-offs counted',
          db['outcome'] == 'passed' and len(db['transient']) == 1 and db['transient'][0]['broken_at_us'] == 375332
          and 'times out on B' in db['transient'][0]['broken_by'] and db['backoffs'] == '1,0', db)
    wc = C.wait_for(C.parse(LOCK_CHAIN))
    check('a CHAIN is not a cycle: T1 waits B held by T2, T2 waits for nothing → no cycle (the false self-loop found and fixed in sc-3)',
          wc['first_cycle'] is None and wc['waits'] == {'T1': 'B'}, wc)
    rt = C.round_times(C.parse(LOCK_BACKOFF), 'T1')
    check('T1\'s round time from its ROUND → DONE marks (the back-off\'s run-time cost)', rt == [376903 - 368355], rt)
    _campaign(check)


def _campaign(check):
    from firmwarefaults.custom import campaign_sc3, runner_sc3
    from firmwarefaults.custom.sink import LocalSink
    real = runner_sc3.run_side
    outcomes = {1: ('failed', 'passed'), 2: ('passed', 'passed'), 3: ('failed', 'passed'), 4: ('failed', 'passed')}

    def fake(sc, side, sink, seed=0, write=True, h=None):
        o = outcomes[seed][0 if side == 'before' else 1]
        return {'outcome': o, 'observable_value': 'fixture %s' % o, 'build_name': 'c3-fixture-%s' % side, 'firmware_sha256': 'f' * 64,
                'trace_sha256': '%d%s' % (seed, side), 'observed_json': json.dumps({'knobs': {'t1_gap_ticks': seed, 't2_start_ticks': 0, 't2_gap_ticks': 1}})}
    runner_sc3.run_side = fake
    try:
        sink = LocalSink()
        out = campaign_sc3.run(sink, 'two-lock-deadlock', seeds=4)
    finally:
        runner_sc3.run_side = real
    st, lik = out['stat'], out['likelihood']
    check('the C3 campaign (fake runs): 3 of 4 seeds deadlock WITHOUT the technique = 75 % with its Wilson interval, residual 0 of 4',
          (st['events'], st['trials'], st['residual_events']) == (3, 4, 0) and abs(st['rate'] - 0.75) < 1e-9 and 0.3 < st['ci_low'] < 0.31
          and lik['before_events'] == 3 and lik['after_events'] == 0 and lik['technique'] == 'lock-ordering', (st, lik))
    fr = sink.get('DeadlockFault', 'two-lock-deadlock')
    c = sink.get('MathClaim', 'fw-safe:two-lock-deadlock:c3-fixture-before')
    check('…the fault row carries the measured rate + its source; the claim gains the statistics tier (status unchanged)',
          fr['rate'] == 0.75 and 'measured (sc-3)' in fr['rate_source'] and c is not None
          and any(t['tier'] == 'statistics' for t in json.loads(c['evidence_tiers_json'])), (fr.get('rate_source', '')[:120], c))
