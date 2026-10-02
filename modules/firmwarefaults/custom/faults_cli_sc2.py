"""
@module firmwarefaults.custom.faults_cli_sc2

`pol faults campaign | formal | static` (sc-2 / sc-2b) — the statistics, formal and static tiers from the CLI. Runs HERE
through the engines seams (the twin: board engines; CBMC / cppcheck: formal engines) and records the rows under
$POLARI_FAULTS_HOME/runs/; with --api URL the server runs it and the rows land there.

    campaign list | run <name> [--seeds N] [--rates a,b] [--verbose] [--api URL] | show <name>
    formal   list | run <name>|all|cbmc|mthread [--api URL] | show <name>   (sc-2c: the Mthread race checks beside CBMC's)
    static   run [<variant>|all] [--api URL] | show <variant>
"""
import json

from firmwarefaults.custom.faults_cli import _http


def _pct(b):
    return '%d/%d = %.3f %% [%.3f, %.3f]' % (b['events'], b['trials'], 100 * b['rate'], 100 * b['ci_low'], 100 * b['ci_high'])


def print_campaign(c):
    print('[CAMPAIGN] %s — %s (%s)' % (c['name'], c.get('title', ''), c.get('status', '')))
    print('       scenario  %s · fault %s:%s · %s per run · %s seeds per (side, %s)' % (c['scenario'], c['fault_class'], c['fault'],
                                                                                   c.get('run_seconds') or 'the scenario window', c.get('seeds'), c['parameter']))
    results = c.get('_results') or json.loads(c.get('results_json') or '[]')
    for r in results:
        line = '       %-9s %-8g BEFORE %-34s AFTER %s' % (c['parameter'][:9], r['rate'], _pct(r['before']), _pct(r['after']))
        if r.get('after_aux'):
            line += '  · %s %s' % (r['after_aux'].get('what', ''), _pct(r['after_aux']))
        print(line)
    if c.get('ttff_summary'):
        print('       ttff      %s' % c['ttff_summary'][:500])
    if c.get('wall_s'):
        print('       cost      %s runs, %.1f s wall' % (c.get('runs'), float(c['wall_s'])))


def cmd_campaign(a):
    from firmwarefaults.custom import campaign as C
    if a.action == 'list':
        for c in C.SEED_CAMPAIGNS:
            print('  %-22s %-26s %s %s · %d seeds' % (c['name'], c['scenario'], c['parameter'], c['rates_json'], c['seeds']))
        return 0
    if not a.name:
        print('[REFUSED] name a campaign: %s' % ', '.join(c['name'] for c in C.SEED_CAMPAIGNS))
        return 3
    rates = [float(x) for x in a.rates.split(',')] if a.rates else None
    if a.api:
        if a.action == 'show':
            d = _http('GET', '%s/api/firmwarefaults/campaigns' % a.api.rstrip('/'))
            for c in d.get('campaigns', []):
                if c['name'] == a.name:
                    print_campaign(c)
                    return 0
            print('[REFUSED] no campaign %r on %s' % (a.name, a.api))
            return 3
        d = _http('POST', '%s/api/firmwarefaults/campaign' % a.api.rstrip('/'), {'campaign': a.name, 'seeds': a.seeds, 'rates': rates})
        if not d.get('ok'):
            print('[REFUSED] %s' % d.get('error'))
            return 3
        print_campaign(d['campaign'])
        return 0
    from firmwarefaults.custom.sink import LocalSink, local_records
    if a.action == 'show':
        for rec, path in local_records():
            for c in rec.get('ScenarioCampaign', []):
                if c['name'] == a.name:
                    print_campaign(c)
                    print('       record    %s' % path)
                    return 0
        print('[REFUSED] no recorded campaign %r — `pol faults campaign run %s`' % (a.name, a.name))
        return 3
    from firmwarefaults.custom.runner import ScenarioRefused
    from board.custom.engine_run import EngineRefused
    sink = LocalSink()
    try:
        c = C.run_campaign(a.name, sink, seeds=a.seeds, rates=rates, progress=(lambda m: print('       %s' % m)) if a.verbose else None)
    except (ScenarioRefused, EngineRefused) as e:
        print('[REFUSED] %s' % e)
        return 3
    print_campaign(c)
    print('       record    %s' % sink.flush('campaign@%s@%s' % (a.name, c['ran_at'])))
    return 0


def print_formal(r):
    tag = {'decided': '[DECIDED]', 'refuted': '[REFUTED]', 'inapplicable': '[N/A    ]', 'undetermined': '[  ??   ]'}.get(r.get('outcome'), '[ ERROR ]')
    print('%s %s — %s' % (tag, r['name'], r.get('title', '')))
    print('       claim     %s → %s' % (r.get('claim') or '-', r.get('claim_status') or r.get('outcome')))
    print('       outcome   %s' % r.get('outcome_words', '')[:600])
    bound = r.get('bound') or 'k=%s, unwind %s' % (r.get('bound_k'), r.get('unwind'))
    print('       engine    %s (%s) · %.3f s wall · %.1f MB peak RSS · bound %s · expected %s' % (
        r.get('engine_version', ''), r.get('engine_where', ''), float(r.get('wall_s') or 0), float(r.get('peak_rss_mb') or 0), bound,
        r.get('expected')))
    if r.get('trace_sha256'):
        print('       %s sha256 %s (%s %s)' % ('report' if r.get('engine') == 'frama-c-mthread' else 'trace ', r['trace_sha256'], r.get('trace_steps'),
                                            'lines' if r.get('engine') == 'frama-c-mthread' else 'steps'))
    if r.get('engine') == 'frama-c-mthread':
        try:
            cx = json.loads(r.get('counterexample_json') or '{}')
        except ValueError:
            cx = {}
        if cx.get('pair'):
            print('       race      %s: %s' % (cx.get('var'), cx['pair']))


def cmd_formal(a):
    from firmwarefaults.custom import formal_mthread as M, formal_engines as fe
    if a.action == 'list':
        for c in M.all_checks():
            eng = 'mthread' if M.find(c['name']) else 'cbmc'
            print('  %-42s %-7s %-20s expected %-12s %s' % (c['name'], eng, c['variant'], c['expected'], c.get('bound_words') or 'unbounded (no k, no unwind)'))
        eng = fe.placement()['engines']
        print('  engine cbmc-check:    %s' % json.dumps(eng.get('cbmc-check')))
        print('  engine mthread-check: %s' % json.dumps(eng.get('mthread-check')))
        return 0
    if a.name in ('all', ''):
        names = [c['name'] for c in M.all_checks()]
    elif a.name in ('cbmc', 'mthread'):
        names = [c['name'] for c in (M.F.FORMAL_CHECKS if a.name == 'cbmc' else M.MTHREAD_CHECKS)]
    else:
        names = [a.name]
    if a.action == 'run' and not all(M.find_any(n) for n in names):
        print('[REFUSED] unknown FormalCheck %r — one of %s (or all | cbmc | mthread)' % (a.name, ', '.join(c['name'] for c in M.all_checks())))
        return 3
    if a.api:
        d = _http('POST', '%s/api/firmwarefaults/formal' % a.api.rstrip('/'), {'checks': names})
        if not d.get('ok'):
            print('[REFUSED] %s' % d.get('error'))
            return 3
        for r in d['checks']:
            print_formal(r)
        return 0
    from firmwarefaults.custom.sink import LocalSink, local_records
    if a.action == 'show':
        for rec, path in local_records():
            for r in rec.get('FormalCheck', []):
                if r['name'] == a.name:
                    print_formal(r)
                    print('       counterexample %s' % r.get('counterexample_json', '{}')[:600])
                    print('       record    %s' % path)
                    return 0
        print('[REFUSED] no recorded FormalCheck %r' % a.name)
        return 3
    sink = LocalSink()
    try:
        for n in names:
            print_formal(M.run_any(n, sink))
    except fe.FormalRefused as e:
        print('[REFUSED] %s' % e)
        return 3
    print('       record    %s' % sink.flush('formal@%s' % (names[0] if len(names) == 1 else 'all')))
    return 0


def print_static(r):
    print('[STATIC] %-26s %s findings %s · %s · %.2f s · %s' % (r['variant'], r.get('findings', '-'), r.get('counts_json', ''), r.get('tool_version', ''),
                                                          float(r.get('wall_s') or 0), r.get('state', '')))


def cmd_static(a):
    from firmwarefaults.custom import static_rules as SR, formal_engines as fe
    variants = SR.all_variants() if a.variant in ('all', '') else [a.variant]
    if a.api:
        d = _http('POST', '%s/api/firmwarefaults/static' % a.api.rstrip('/'), {'variants': variants})
        if not d.get('ok'):
            print('[REFUSED] %s' % d.get('error'))
            return 3
        for r in d['checks']:
            print_static(r)
        return 0
    from firmwarefaults.custom.sink import LocalSink, local_records
    if a.action == 'show':
        for rec, path in local_records():
            for r in rec.get('StaticCheck', []):
                if r['variant'] == a.variant:
                    print_static(r)
                    for f in rec.get('StaticFinding', []):
                        if f['variant'] == a.variant:
                            print('         %-11s %-22s %s:%s %s' % (f['severity'], f['check_id'], f['file'], f['line'], f['message'][:110]))
                    return 0
        print('[REFUSED] no recorded static check for %r' % a.variant)
        return 3
    sink = LocalSink()
    try:
        for r in SR.run_all(sink, variants):
            print_static(r)
    except fe.FormalRefused as e:
        print('[REFUSED] %s' % e)
        return 3
    print('       not run   %s' % SR.NOT_RUN)
    print('       record    %s' % sink.flush('static@%s' % (variants[0] if len(variants) == 1 else 'all')))
    return 0


def add_parsers(sub):
    c = sub.add_parser('campaign')
    c.add_argument('action', choices=('list', 'run', 'show'))
    c.add_argument('name', nargs='?', default='')
    c.add_argument('--seeds', type=int)
    c.add_argument('--rates', default='')
    c.add_argument('--verbose', action='store_true')
    c.add_argument('--api', default='')
    f = sub.add_parser('formal')
    f.add_argument('action', choices=('list', 'run', 'show'))
    f.add_argument('name', nargs='?', default='all')
    f.add_argument('--api', default='')
    s = sub.add_parser('static')
    s.add_argument('action', choices=('run', 'show'))
    s.add_argument('variant', nargs='?', default='all')
    s.add_argument('--api', default='')
    return {'campaign': cmd_campaign, 'formal': cmd_formal, 'static': cmd_static}
