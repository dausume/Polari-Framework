"""sc-3 part of tests/firmwarefaults_probe.py — the RTOS scenarios on the ESP32-C3 QEMU twin, REAL when the esp engines resolve
(prf-esp-engines on this docker, or ESP_ENGINES_URL), else every check SKIPs naming why. The builds go through board's C3 gen/build
(ESP-IDF v5.5.5) into the probe's own POLARI_FAULTS_HOME; the runs through polari-c3-run (QEMU -icount 3, sleep=off).

  1. priority-inversion-mutex: BEFORE (binary semaphore) refuted — H's worst wait ≫ the bound, M named inside it; AFTER (mutex) witnessed —
     within the bound, INHERIT events; the cost pair on the Technique row
  2. two-lock-deadlock: BEFORE refuted — the cycle T1 → B → T2 → A → T1 at a named µs/tick, both Blocked, telemetry silent after its last
     frame; AFTER (ordering) witnessed — all rounds, no cycle
  3. two-lock-deadlock-backoff: AFTER witnessed with transient cycles broken by the timeout, back-offs counted
  4. the BEFORE deadlock re-runs BIT-IDENTICALLY (trace + UART0 sha256) from image + params; seed 9 = the recipe's knobs → the same trace
  5. a 3-seed campaign smoke (two-lock-deadlock) → a ScenarioStatistic + FaultLikelihood row (the 10-seed numbers: `pol faults stats`)
"""
import json


def part_s3(check, report):
    from board.custom import board_engines as be
    why = [w['why'] for w in (be.resolve('c3-run'), be.resolve('idf-build')) if w['how'] == 'refused']
    if why:
        print('SKIP: sc-3 (the C3 twin): %s' % why[0])
        return
    from firmwarefaults.custom import runner, scenarios as SC, campaign_sc3
    from firmwarefaults.custom.sink import LocalSink
    sink = LocalSink()
    rep = report.setdefault('sc3', {})
    b, a = runner.run_scenario('priority-inversion-mutex', 'both', sink)['runs']
    ob, oa = json.loads(b['observed_json'])['decided'], json.loads(a['observed_json'])['decided']
    rep['priority-inversion-mutex'] = {'before': b['verdict_words'], 'after': a['verdict_words'], 'cost': json.loads(a['cost_delta_json']),
                                       'claims': [b['claim_status'], a['claim_status']]}
    check('C3 S6 BEFORE (binary semaphore): REFUTED — H waited %s µs vs the %s µs bound, M ran %s µs of it, 0 inheritance'
          % (ob.get('worst_us'), 3000 + 1000, ob.get('m_inside_us')), b['outcome'] == 'failed' and ob['worst_us'] > 4000 and ob['m_inside_us'] > 5000
          and ob['inherit_events'] == 0 and b['claim_status'] == 'refuted', b['verdict_words'])
    check('C3 S6 AFTER (mutex): WITNESSED — H\'s worst wait %s µs ≤ 4000 µs, %s inheritance events, M 0 µs inside'
          % (oa.get('worst_us'), oa.get('inherit_events')), a['outcome'] == 'passed' and oa['worst_us'] <= 4000 and oa['inherit_events'] >= 1
          and oa['m_inside_us'] == 0 and a['claim_status'] == 'witnessed', a['verdict_words'])
    t = sink.get('Technique', 'priority-inheritance')
    check('C3 S6 cost on the Technique row: %+d B flash, %+d B DRAM, H\'s worst wait %+d µs' % (t['measured_cost_bytes'], t['measured_ram_bytes'],
                                                                                          oa['worst_us'] - ob['worst_us']),
          t['measured_by_run'] == a['name'] and 'ESP32-C3' in t['measured_cost_what'])
    b, a = runner.run_scenario('two-lock-deadlock', 'both', sink)['runs']
    db, da = json.loads(b['observed_json'])['decided'], json.loads(a['observed_json'])['decided']
    rep['two-lock-deadlock'] = {'before': b['verdict_words'], 'after': a['verdict_words'], 'cost': json.loads(a['cost_delta_json']),
                                'before_trace_sha256': b['trace_sha256'], 'before_uart_sha256': b['uart_sha256']}
    check('C3 S7 BEFORE (opposite order): REFUTED — %s; telemetry\'s last frame %s ms, then %s ms of silence; the trace rows around the cycle'
          % (b['observable_value'], db.get('last_frame_ms'), db.get('silent_ms')),
          b['outcome'] == 'failed' and 'T1 → B → T2 → A → T1' in b['observable_value'] and db['silent_ms'] and db['silent_ms'] > 1000
          and b['frames_seen'] >= 2 and len(b.get('_trace_rows') or []) > 5 and b['claim_status'] == 'refuted', b['verdict_words'])
    check('C3 S7 AFTER (lock ordering): WITNESSED — %s; telemetry to %s ms' % (a['observable_value'], da.get('last_frame_ms')),
          a['outcome'] == 'passed' and not da['transient'] and a['frames_seen'] > b['frames_seen'] and a['claim_status'] == 'witnessed', a['verdict_words'])
    b2, a2 = runner.run_scenario('two-lock-deadlock-backoff', 'both', sink)['runs']
    d2 = json.loads(a2['observed_json'])['decided']
    rep['two-lock-deadlock-backoff'] = {'after': a2['verdict_words'], 'cost': json.loads(a2['cost_delta_json'])}
    check('C3 S7 AFTER (timed take + back-off): WITNESSED — %s' % a2['observable_value'],
          a2['outcome'] == 'passed' and len(d2['transient']) >= 1 and b2['outcome'] == 'failed', a2['verdict_words'])
    again = runner.run_scenario('two-lock-deadlock', 'before', LocalSink())['runs'][0]
    check('the BEFORE deadlock re-runs BIT-IDENTICALLY from image + params (trace %s…, UART0 %s…)' % (again['trace_sha256'][:12], again['uart_sha256'][:12]),
          (again['trace_sha256'], again['uart_sha256'], again['firmware_sha256']) == (b['trace_sha256'], b['uart_sha256'], b['firmware_sha256']))
    s9 = runner.run_scenario('two-lock-deadlock', 'before', LocalSink(), seed=9)['runs'][0]
    k9 = json.loads(s9['observed_json'])['knobs']
    if (k9['t1_gap_ticks'], k9['t2_start_ticks'], k9['t2_gap_ticks']) == (2, 1, 1):
        check('seed 9 draws the recipe\'s own knobs (2, 1, 1) → the SAME trace as seed 0 (the params block differs only in its seed word)',
              s9['trace_sha256'] != '' and s9['outcome'] == 'failed' and json.loads(s9['observed_json'])['decided']['cycle_us'] == db['cycle_us'])
    out = campaign_sc3.run(sink, 'two-lock-deadlock', seeds=3)
    lik = out['likelihood']
    rep['campaign_smoke'] = {k: lik[k] for k in ('before_events', 'before_trials', 'after_events', 'after_trials')}
    check('a 3-seed C3 campaign smoke: %d/3 deadlocked WITHOUT ordering, %d/3 WITH it → ScenarioStatistic + FaultLikelihood rows'
          % (lik['before_events'], lik['after_events']), lik['before_trials'] == 3 and lik['after_events'] == 0
          and sink.get('ScenarioStatistic', out['stat']['name']) is not None)
    check('every C3 run carries its repro block: image + params by sha256, the recipe knobs, the seed, deterministic',
          all(json.loads(r['repro_json'])['seeds']['deterministic'] and any('polari params' in i['label'] for i in json.loads(r['repro_json'])['inputs'])
              for r in sink.rows('ScenarioRun') if SC.find(r['scenario'])['simulator'] == 'qemu-esp32c3'))
