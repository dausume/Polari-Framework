"""
@module firmwarefaults.custom.faults_cli

`pol faults` (sc-0): run a scenario on the twin and print the BEFORE/AFTER pair with its costs; list the scenarios and the
recorded runs; show one run (the cycles around the fault, the claim). With no --api it runs HERE (the engines resolve
through the board seam on this device) and records each run under $POLARI_FAULTS_HOME/runs/; with --api the server
runs it (POST /api/firmwarefaults/run) and the rows land on that server.

    python3 -m firmwarefaults.custom.faults_cli run torn-millis-read [--before|--after|--both|--natural] [--seconds S] [--seed N] [--api URL]
    python3 -m firmwarefaults.custom.faults_cli list [--api URL]
    python3 -m firmwarefaults.custom.faults_cli show <run> [--api URL]
    python3 -m firmwarefaults.custom.faults_cli engines
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
    if r.get('fault_cycle'):
        print('       forced    cycle %d at %s (%s); landed at %s (%s), cycle %s' % (r['fault_cycle'], r['fault_pc'], r['fault_symbol'],
                                                                                 r.get('landed_pc') or '-', r.get('landed_symbol') or '-', r.get('landed_cycle') or '-'))
    if r.get('uptime_sequence'):
        print('       frames    %d CRC-valid (bad CRC %d), uptime_ms: %s' % (r['frames_seen'], r['bad_crc'], r['uptime_sequence'][:160]))
    if r.get('torn_value', -1) >= 0:
        print('       torn      hal_millis returned %d (0x%08X); an atomic read gives %d or %d' % (r['torn_value'], r['torn_value'], r['expected_value'], r['expected_value'] + 1))
    if r.get('size_text'):
        print('       cost      .text %d .data %d .bss %d · hal_millis %s cycles (min, uninterrupted) · worst ISR latency %s cycles (vector %s)'
              % (r['size_text'], r['size_data'], r['size_bss'], r['fn_cycles_min'], r['isr_latency_max_cycles'], r['isr_latency_vector']))
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
    if len(runs) == 2 and runs[1].get('cost_delta_json'):
        cd = json.loads(runs[1]['cost_delta_json'])
        print('[COST] technique %s (AFTER − BEFORE): %+d B flash, %+d B RAM, %+d cycles per hal_millis call, %+d cycles worst ISR latency, %+d B stack'
              % (runs[1]['technique_applied'], cd.get('flash_bytes', 0), cd.get('ram_bytes', 0), cd.get('guarded_fn_cycles', 0),
                 cd.get('isr_latency_max_cycles', 0), cd.get('stack_high_water_bytes', 0)))


def cmd_run(a):
    side = 'both' if a.both else 'before' if a.before else 'after' if a.after else 'natural' if a.natural else 'both'
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
    for r in out['runs']:
        print_run(r, r.get('_trace_rows'))
    print_pair(out['runs'])
    p = sink.flush('%s@%s@%s' % (a.scenario, side, out['runs'][-1]['ran_at']))
    print('       record    %s' % p)
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
        print('  %-20s %-10s %s → %s  fault %s (%s)  technique %s' % (s['name'], 'runnable' if SC.runnable(s) else 'not-yet', s['before_variant'],
                                                                      s['after_variant'] or '(refused build)', s['fault'], s['fault_class'], s['technique']))
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
            print_run(r, trace)
            c = next((c for c in rec.get('MathClaim', []) if c['name'] == r['claim']), None)
            if c:
                print('       claim     %s: %s · counterexample %s' % (c['proof_status'], c['description'][:140], c.get('counterexample_json', '{}')[:200]))
            print('       record    %s' % path)
            return 0
    print('[REFUSED] no recorded run %r — `pol faults list`' % a.run)
    return 3


def cmd_engines(a):
    from firmwarefaults.custom.fault_engines import placement, harness_digest
    for e, w in placement().items():
        print('  %-12s %-13s %s  (%s)' % (e, w['how'], w['where'], w['why']))
    print('  harness      %s' % harness_digest())
    return 0


def main(argv):
    ap = argparse.ArgumentParser(prog='pol faults')
    sub = ap.add_subparsers(dest='cmd', required=True)
    r = sub.add_parser('run')
    r.add_argument('scenario')
    g = r.add_mutually_exclusive_group()
    for s in ('before', 'after', 'both', 'natural'):
        g.add_argument('--' + s, action='store_true')
    r.add_argument('--seconds', type=float)
    r.add_argument('--seed', type=int)
    r.add_argument('--api', default='')
    ls = sub.add_parser('list')
    ls.add_argument('--api', default='')
    sh = sub.add_parser('show')
    sh.add_argument('run')
    sh.add_argument('--api', default='')
    sub.add_parser('engines')
    a = ap.parse_args(argv)
    return {'run': cmd_run, 'list': cmd_list, 'show': cmd_show, 'engines': cmd_engines}[a.cmd](a)


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
