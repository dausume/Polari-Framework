"""
@module firmwarefaults.custom.faults_cli

`pol faults` (sc-0): run a scenario on the twin and print the BEFORE/AFTER pair with its costs; list the scenarios and the
recorded runs; show one run (the cycles around the fault, the claim). With no --api it runs HERE (the engines resolve
through the board seam on this device) and records each run under $POLARI_FAULTS_HOME/runs/; with --api the server
runs it (POST /api/firmwarefaults/run) and the rows land on that server.

    python3 -m firmwarefaults.custom.faults_cli run <scenario> [--before|--after|--both|--natural|--control] [--seconds S] [--seed N] [--api URL]
    python3 -m firmwarefaults.custom.faults_cli stats uart-residual-frame-loss|torn-millis-read [--seeds N] [--bers 1e-3,1e-4] [--api URL]
    python3 -m firmwarefaults.custom.faults_cli stats priority-inversion-mutex|two-lock-deadlock[-backoff] [--seeds 10]    (sc-3, the C3 twin)
    python3 -m firmwarefaults.custom.faults_cli list [--api URL]
    python3 -m firmwarefaults.custom.faults_cli show <run> [--api URL]
    python3 -m firmwarefaults.custom.faults_cli engines
    python3 -m firmwarefaults.custom.faults_cli campaign list|run|show [<name>] [--seeds N] [--rates a,b]     (sc-2, faults_cli_sc2)
    python3 -m firmwarefaults.custom.faults_cli formal list|run|show [<check>|all]                           (sc-2b)
    python3 -m firmwarefaults.custom.faults_cli static run|show [<variant>|all]                              (sc-2b)
"""
import argparse
import json
import ssl
import sys


def _http(method, url, body=None):
    from polariApiServer import outbound
    import urllib.request
    req = urllib.request.Request(url, data=json.dumps(body).encode() if body is not None else None, method=method,
                                 headers={'Content-Type': 'application/json'})
    try:
        with outbound.http_request('self', 'firmwarefaults', method, req, means='rest', timeout=900, lib='urllib',
                                   context=ssl._create_unverified_context()) as r:
            return json.load(r)
    except Exception as e:  # noqa: BLE001 — an HTTP error body is still JSON when the server refused
        try:
            return json.load(e)
        except Exception:  # noqa: BLE001
            return {'ok': False, 'error': str(e)}


def print_run(r, trace=None):
    tag = {'failed': '[FAIL]', 'passed': '[PASS]', 'inapplicable': '[N/A ]', 'undetermined': '[ ?? ]'}.get(r['outcome'], '[    ]')
    print('%s %s  %s  (%s)' % (tag, r['side'].upper(), r['variant'], r['build_name']))
    print('       outcome   %s — %s' % (r['outcome'], r['verdict_words']))
    if r.get('observable_value'):
        print('       observed  %s%s' % (r['observable_value'], ('  · resets %d' % r['reset_count']) if r.get('reset_count') else ''))
    if r.get('fault_cycle') and not r.get('fault_pc'):
        print('       forced    cycle %d: %s%s' % (r['fault_cycle'], r['fault_symbol'], ('; %s' % r['landed_symbol']) if r.get('landed_symbol') else ''))
    elif r.get('fault_cycle'):
        print('       forced    cycle %d at %s (%s); landed at %s (%s), cycle %s' % (r['fault_cycle'], r['fault_pc'], r['fault_symbol'],
                                                                                 r.get('landed_pc') or '-', r.get('landed_symbol') or '-', r.get('landed_cycle') or '-'))
    if r.get('uptime_sequence'):
        print('       frames    %d CRC-valid (bad CRC %d), uptime_ms: %s' % (r['frames_seen'], r['bad_crc'], r['uptime_sequence'][:160]))
    if r.get('torn_value', -1) >= 0:
        print('       torn      hal_millis returned %d (0x%08X); an atomic read gives %d or %d' % (r['torn_value'], r['torn_value'], r['expected_value'], r['expected_value'] + 1))
    if r.get('size_text'):
        print('       cost      .text %d .data %d .bss %d · priced fn %s cycles (min) · worst ISR latency %s cycles (vector %s) · longest ISR %s '
              'cycles (vector %s)' % (r['size_text'], r['size_data'], r['size_bss'], r['fn_cycles_min'], r['isr_latency_max_cycles'],
                                      r['isr_latency_vector'], r.get('isr_cycles_max', '-'), r.get('isr_cycles_vector', '-')))
        print('       stack     high-water %d B (SP watch) · %d B (0xA5 paint) · static peak %d B (-fstack-usage + call graph)'
              % (r['stack_high_water'], r['stack_high_water_paint'], r['stack_static_peak']))
    if r.get('trace_sha256'):
        print('       trace     VCD sha256 %s (%s samples) · uart sha256 %s' % (r['trace_sha256'], r['trace_samples'], r['uart_sha256'][:16]))
    flip = r.get('_claim_flip') or r.get('claim_flip')
    print('       claim     %s  %s' % (r['claim'], ('%s → %s' % tuple(flip)) if flip else ''))
    print('       repro     firmware %s · harness %s · seed %s · %.3f s wall for %d cycles' % (r['firmware_sha256'][:16], r['harness_digest'][:60], r['seed'],
                                                                                           float(r.get('wall_s') or 0), int(r.get('sim_cycles') or 0)))
    for t in (trace or []):
        if t.get('note'):
            print('         %+5d  %-7s %-22s %-24s I=%s v=%-2s r22..25=%s %s %s %s  g_ms=%s  %s' % (
                t['rel_cycle'], t['pc'], t['symbol'][:22], t['instruction'][:24], t['sreg_i'], t['isr_vector'], t['r22'], t['r23'], t['r24'], t['r25'], t['watch'], t['note']))


def print_pair(runs):
    if len(runs) == 2 and runs[1].get('cost_delta_json') and 'flash_bytes' in runs[1]['cost_delta_json']:
        cd = json.loads(runs[1]['cost_delta_json'])
        cyc = cd.get('guarded_fn_cycles', cd.get('cycles', 0))
        what = cd.get('cycles_what', 'per hal_millis call')
        print('[COST] technique %s (AFTER − BEFORE): %+d B flash, %+d B RAM, %+d cycles (%s), %+d cycles worst ISR latency, %+d B stack'
              % (runs[1]['technique_applied'], cd.get('flash_bytes', 0), cd.get('ram_bytes', 0), cyc, what,
                 cd.get('isr_latency_max_cycles', 0), cd.get('stack_high_water_bytes', 0)))


def cmd_run(a):
    from firmwarefaults.custom import scenarios as SC
    row = SC.find(a.scenario)
    if row is not None and row.get('kind') == 'acceptance':
        # hw priorities P1 (D-hw-2): an acceptance scenario proves a CapabilityDefinition's goal under NORMAL
        # operation — it has no before/after/natural/control sides, so it skips the fault-runner entirely.
        from firmwarefaults.custom import acceptance as ACC
        from firmwarefaults.custom.sink import LocalSink
        mode = 'hardware' if getattr(a, 'hardware', False) else 'digital-twin'
        sink = LocalSink()
        out = ACC.run(a.scenario, mode=mode, sink=sink)
        print_run(out)
        p = sink.flush(out['name'])
        print('       record    %s' % p)
        return 0 if out['outcome'] == 'passed' else (3 if out['outcome'] == 'inapplicable' else 1)
    side = 'both' if a.both else 'before' if a.before else 'after' if a.after else 'natural' if a.natural else 'control' if a.control else 'both'
    if a.api:
        d = _http('POST', '%s/api/firmwarefaults/run' % a.api.rstrip('/'), {'scenario': a.scenario, 'side': side, 'seconds': a.seconds, 'seed': a.seed})
        if not d.get('ok'):
            print('[REFUSED] %s' % d.get('error'))
            return 3
        for r in d['runs']:
            print_run(r)
        print_pair(d['runs'])
        return 0
    from firmwarefaults.custom import runner
    from firmwarefaults.custom.sink import LocalSink
    from board.custom.engine_run import EngineRefused
    from board.custom.gen import GenRefused
    sink = LocalSink()
    try:
        out = runner.run_scenario(a.scenario, side, sink, seconds=a.seconds, seed=a.seed)
    except (runner.ScenarioRefused, EngineRefused, GenRefused) as e:
        print('[REFUSED] %s' % e)
        return 3
    from firmwarefaults.custom import faults_cli_sc3 as C3
    pr, pp = (C3.print_run, C3.print_pair) if C3.is_c3(a.scenario) else (print_run, print_pair)   # sc-3: the C3 runs print their own way
    for r in out['runs']:
        pr(r, r.get('_trace_rows'))
    pp(out['runs'])
    p = sink.flush('%s@%s@%s' % (a.scenario, side, out['runs'][-1]['ran_at']))
    print('       record    %s' % p)
    return 0


def print_stat(r):
    res = ('  residual %d = %.3f %% [%.3f, %.3f]' % (r.get('residual_events', 0), 100 * r.get('residual_rate', 0), 100 * r.get('residual_ci_low', 0),
                                                    100 * r.get('residual_ci_high', 0))) if 'residual_events' in r else ''
    print('[STAT] %-46s %d/%d = %.3f %% [%.3f, %.3f] (Wilson 95 %%, %d seeds)%s' % (r['name'], r['events'], r['trials'], 100 * r['rate'],
                                                                                   100 * r['ci_low'], 100 * r['ci_high'], r['seeds'], res))
    if r.get('notes'):
        print('       %s' % r['notes'][:400])


def cmd_stats(a):
    from firmwarefaults.custom import faults_cli_sc3 as C3
    if C3.is_c3(a.scenario) and not a.api:   # sc-3: the C3 campaign (seeded tick offsets; default 10 seeds)
        return C3.cmd_stats(a)
    from firmwarefaults.custom import statistics as ST
    a.seeds = a.seeds or 20
    bers = tuple(float(x) for x in a.bers.split(',')) if a.bers else ST.BERS
    if a.api:
        d = _http('POST', '%s/api/firmwarefaults/stats' % a.api.rstrip('/'), {'scenario': a.scenario, 'seeds': a.seeds, 'bers': list(bers)})
        if not d.get('ok'):
            print('[REFUSED] %s' % d.get('error'))
            return 3
        for r in d['statistics']:
            print_stat(r)
        return 0
    from firmwarefaults.custom.sink import LocalSink
    from firmwarefaults.custom.runner import ScenarioRefused
    from board.custom.engine_run import EngineRefused
    sink = LocalSink()
    prog = (lambda m: print('       %s' % m)) if a.verbose else None
    try:
        if a.scenario == 'uart-residual-frame-loss':
            rows = list(ST.uart_ber(sink, bers=bers, seeds=a.seeds, progress=prog).values())
            fault = sink.get('UartBitErrorFault', 'uart-bit-error')
        elif a.scenario == 'torn-millis-read':
            out = ST.tear_phase_sweep(sink, seeds=a.seeds, progress=prog)
            rows, fault = [out['natural_row'], out['sweep']], sink.get('TornReadFault', 'torn-read-g-ms')
        else:
            print('[REFUSED] statistics exist for uart-residual-frame-loss (--uart-ber), torn-millis-read (the phase sweep) and the sc-3 C3 '
                  'scenarios (%s)' % ', '.join(C3.C3_NAMES))
            return 3
    except (ScenarioRefused, EngineRefused) as e:
        print('[REFUSED] %s' % e)
        return 3
    for r in rows:
        print_stat(r)
    print('       fault row %s: %s' % (fault['name'], fault['rate_source'][:600]))
    print('       record    %s' % sink.flush('stats@%s@%s' % (a.scenario, rows[-1]['ran_at'])))
    return 0


def cmd_list(a):
    from firmwarefaults.custom import scenarios as SC
    if a.api:
        d = _http('GET', '%s/api/firmwarefaults' % a.api.rstrip('/'))
        for s in d.get('scenarios', []):
            print('  %-20s %s%s' % (s['name'], s['status'], '' if s['runnable'] else ' (not runnable)'))
        for k, r in sorted((d.get('latest_runs') or {}).items()):
            print('  run %-28s %-12s %s' % (k, r['outcome'], r['name']))
        return 0
    print('scenarios:')
    for s in SC.SEED_SCENARIOS:
        print('  %-27s %-10s %s → %s  fault %s (%s)  technique %s' % (s['name'], 'runnable' if SC.runnable(s) else 'not-yet', s['before_variant'] or '-',
                                                                      s['after_variant'] or ('(refused build)' if s['before_variant'] else '-'), s['fault'],
                                                                      s['fault_class'], s['technique']))
        if not SC.runnable(s):
            print('  %-27s            %s' % ('', SC.refusal(s)[:200]))
    print('step kinds:')
    for k, (ok, why) in SC.STEP_KINDS.items():
        print('  %-18s %-16s %s' % (k, 'forcible' if ok else 'not-yet-forcible', why))
    from firmwarefaults.custom.sink import local_runs
    runs = local_runs()
    print('recorded runs (%d, newest first):' % len(runs))
    for r, _, path in runs[:30]:
        print('  %-8s %-12s %s' % (r['side'], r['outcome'], r['name']))
    return 0


def cmd_show(a):
    from firmwarefaults.custom import faults_cli_sc3 as C3
    if a.api:
        d = _http('GET', '%s/api/firmwarefaults/runs/%s' % (a.api.rstrip('/'), a.run))
        if not d.get('ok'):
            print('[REFUSED] %s' % d.get('error'))
            return 3
        print_run(d['run'], d['trace'])
        return 0
    from firmwarefaults.custom.sink import local_runs
    for r, rec, path in local_runs():
        if r['name'] == a.run or r['name'].startswith(a.run):
            trace = sorted((t for t in rec.get('ScenarioTraceCycle', []) if t['run'] == r['name']), key=lambda t: t['idx'])
            (C3.print_run if C3.is_c3(r) else print_run)(r, trace)
            c = next((c for c in rec.get('MathClaim', []) if c['name'] == r['claim']), None)
            if c:
                print('       claim     %s: %s · counterexample %s' % (c['proof_status'], c['description'][:140], c.get('counterexample_json', '{}')[:200]))
            print('       record    %s' % path)
            return 0
    print('[REFUSED] no recorded run %r — `pol faults list`' % a.run)
    return 3


def cmd_engines(a):
    from firmwarefaults.custom.fault_engines import placement, harness_digest
    from firmwarefaults.custom import formal_engines
    for e, w in placement().items():
        print('  %-12s %-13s %s  (%s)' % (e, w['how'], w['where'], w['why']))
    print('  harness      %s' % harness_digest())
    for e, w in formal_engines.placement()['engines'].items():   # sc-2b: CBMC + cppcheck (FORMAL_ENGINES_URL ladder)
        print('  %-12s %-13s %s  (%s)' % (e, w['how'], w['where'], w['why']))
    return 0


def main(argv):
    ap = argparse.ArgumentParser(prog='pol faults')
    sub = ap.add_subparsers(dest='cmd', required=True)
    r = sub.add_parser('run')
    r.add_argument('scenario')
    g = r.add_mutually_exclusive_group()
    for s in ('before', 'after', 'both', 'natural', 'control'):
        g.add_argument('--' + s, action='store_true')
    r.add_argument('--seconds', type=float)
    r.add_argument('--seed', type=int)
    r.add_argument('--hardware', action='store_true', help='acceptance scenarios only (hw priorities P1)')
    r.add_argument('--api', default='')
    ls = sub.add_parser('list')
    ls.add_argument('--api', default='')
    sh = sub.add_parser('show')
    sh.add_argument('run')
    sh.add_argument('--api', default='')
    sub.add_parser('engines')
    st = sub.add_parser('stats')
    st.add_argument('scenario')
    st.add_argument('--seeds', type=int, default=None, help='default 20 (sc-1 batches) / 10 (the sc-3 C3 campaign)')
    st.add_argument('--bers', default='')
    st.add_argument('--verbose', action='store_true')
    st.add_argument('--api', default='')
    from firmwarefaults.custom.faults_cli_sc2 import add_parsers
    more = add_parsers(sub)
    a = ap.parse_args(argv)
    return dict({'run': cmd_run, 'list': cmd_list, 'show': cmd_show, 'engines': cmd_engines, 'stats': cmd_stats}, **more)[a.cmd](a)


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
