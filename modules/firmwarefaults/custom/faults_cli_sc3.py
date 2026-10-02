"""
@module firmwarefaults.custom.faults_cli_sc3

`pol faults` for the sc-3 RTOS scenarios on the ESP32-C3 twin: how a run prints (the decisive event in µs + its virtual
instruction index, who ran, the wait-for cycle, the frames, the sizes) and the campaign (`pol faults stats <c3 scenario>
--seeds N`). faults_cli dispatches here by the scenario's simulator.
"""
import json

from firmwarefaults.custom import scenarios_sc3 as S3

C3_NAMES = tuple(s['name'] for s in S3.SC3_SCENARIOS)


def is_c3(run_or_name):
    name = run_or_name if isinstance(run_or_name, str) else run_or_name.get('scenario', '')
    return name in C3_NAMES


def print_run(r, trace=None):
    tag = {'failed': '[FAIL]', 'passed': '[PASS]', 'inapplicable': '[N/A ]', 'undetermined': '[ ?? ]'}.get(r['outcome'], '[    ]')
    o = json.loads(r.get('observed_json') or '{}')
    print('%s %s  %s  (%s)  on the ESP32-C3 QEMU twin' % (tag, r['side'].upper(), r['variant'], r['build_name']))
    print('       outcome   %s — %s' % (r['outcome'], r['verdict_words']))
    if r.get('observable_value'):
        print('       observed  %s' % r['observable_value'])
    if r.get('fault_symbol'):
        print('       event     %s — virtual instruction %d (-icount %d)%s' % (r['fault_symbol'], r['fault_cycle'], S3.ICOUNT_SHIFT,
                                                                          ('; %s' % r['landed_symbol']) if r.get('landed_symbol') else ''))
    if o.get('knobs'):
        print('       knobs     seed %s: %s' % (r['seed'], ', '.join('%s=%s' % kv for kv in sorted(o['knobs'].items()))))
    print('       frames    %d CRC-valid SimRigState (bad CRC %d), uptime_ms: %s' % (r['frames_seen'], r['bad_crc'], r['uptime_sequence'][:120] or '—'))
    s = o.get('sizes') or {}
    if s:
        print('       size      flash code %s · flash data %s · IRAM .text %s · DRAM .data %s .bss %s (DRAM %s / %s B)' % (
            s.get('flash_code'), s.get('flash_data'), s.get('iram_text'), s.get('dram_data'), s.get('dram_bss'), s.get('dram_used'), s.get('dram_total')))
    print('       trace     %d hook events · trace sha256 %s · uart0 sha256 %s' % (r['trace_samples'], r['trace_sha256'][:16], r['uart_sha256'][:16]))
    flip = r.get('_claim_flip') or r.get('claim_flip')
    print('       claim     %s  %s' % (r['claim'], ('%s → %s' % tuple(flip)) if flip else ''))
    print('       repro     image %s · %s · seed %s · %.3f s wall for %.3f virtual s' % (r['firmware_sha256'][:16], r['harness_digest'][:60], r['seed'],
                                                                                    float(r.get('wall_s') or 0), float(r.get('sim_seconds') or 0)))
    for t in (trace or []):
        print('         %+9d  %-5s %-40s holders %-10s %s' % (t['rel_cycle'], t['symbol'][:5], t['instruction'][:40], t['watch'][:10], t['note']))


def print_pair(runs):
    if len(runs) == 2 and runs[1].get('cost_delta_json') and 'flash_bytes' in runs[1]['cost_delta_json']:
        cd = json.loads(runs[1]['cost_delta_json'])
        extra = ''
        if 'h_worst_wait_us_before' in cd:
            extra = 'H worst wait %d → %d µs (%+d µs), %s inheritance events' % (cd['h_worst_wait_us_before'], cd['h_worst_wait_us_after'],
                                                                             cd['latency_delta_us'], cd.get('inherit_events_after'))
        elif 't1_mean_round_us_after' in cd:
            extra = 'T1 mean round %s µs AFTER (BEFORE: %s), back-offs %s' % (cd['t1_mean_round_us_after'], cd['t1_mean_round_us_before'] or 'no round finished',
                                                                          cd.get('backoffs_after'))
        print('[COST] technique %s (AFTER − BEFORE, ESP32-C3): %+d B flash (idf.py size text+data), %+d B DRAM · %s'
              % (runs[1]['technique_applied'], cd.get('flash_bytes', 0), cd.get('ram_bytes', 0), extra))


def cmd_stats(a):
    from firmwarefaults.custom import campaign_sc3, runner_sc3
    from firmwarefaults.custom.sink import LocalSink
    from board.custom.engine_run import EngineRefused
    sink = LocalSink()
    prog = (lambda m: print('       %s' % m))
    try:
        out = campaign_sc3.run(sink, a.scenario, seeds=a.seeds or campaign_sc3.SEEDS, progress=prog)
    except (runner_sc3.ScenarioRefused, EngineRefused) as e:
        print('[REFUSED] %s' % e)
        return 3
    st, lik = out['stat'], out['likelihood']
    print('[STAT] %s' % st['name'])
    print('       WITHOUT %s: %d/%d = %.1f %% [%.1f, %.1f]   WITH it (residual): %d/%d = %.1f %% [%.1f, %.1f]   (Wilson 95 %%, %.0f s)' % (
        lik['technique'], lik['before_events'], lik['before_trials'], 100 * lik['before_rate'], 100 * lik['before_ci_low'], 100 * lik['before_ci_high'],
        lik['after_events'], lik['after_trials'], 100 * lik['after_rate'], 100 * lik['after_ci_low'], 100 * lik['after_ci_high'], st['wall_s']))
    print('       coverage  %s' % lik['coverage'])
    print('       record    %s' % sink.flush('stats@%s@%s' % (a.scenario, st['ran_at'])))
    return 0
