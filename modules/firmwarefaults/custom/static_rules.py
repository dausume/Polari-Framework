"""
@module firmwarefaults.custom.static_rules

THE STATIC RULES per firmware variant (FIRMWARE_SCENARIO_PLAN.md §4 "static rules for 8-bit", D-sc-6 — sc-1 named cppcheck,
built in sc-2b): cppcheck 2.17 (GPL-3.0) through the formal engines seam (prf-formal-engines, polari-cppcheck-run) over each
variant's generated project, with the formal tier's stubs/ as the AVR headers:

    --enable=warning,style,portability,performance --platform=avr8 --std=c99 --addon=threadsafety

The MISRA addon is NOT run: its rule texts need the non-free MISRA C document (--rule-texts) — said on every row. Every
finding is a StaticFinding row; the per-variant StaticCheck row counts them by severity. NEVER a build failure.

    run_variant(variant, sink, home=None) · run_all(sink, variants=None) · all_variants()
"""
import datetime
import hashlib
import json

from firmwarefaults.custom import formal, formal_engines as fe

CHECKS = 'warning,style,portability,performance'
ADDONS = ('threadsafety',)
NOT_RUN = 'misra — its rule texts need the non-free MISRA C document (--rule-texts); rule numbers alone would be noise'


def all_variants():
    """Every UNO firmware variant: board's seeded ones + the scenario variants (sc-0/sc-1)."""
    from board.custom.variants import SEED_FIRMWARE_VARIANTS
    from firmwarefaults.custom.scenarios import scenario_variants
    names = [v['name'] for v in SEED_FIRMWARE_VARIANTS if v.get('board_definition') == 'arduino-uno-r3']
    return names + [v['name'] for v in scenario_variants() if v['name'] not in names]


def argv(files):
    a = ['--platform', 'avr8', '--std', 'c99', '--enable', CHECKS, '-I', 'stubs', '-I', '.', '--out', 'findings.json']
    for x in ADDONS:
        a += ['--addon', x]
    return a + sorted(f for f in files if f.endswith('.c') and '/' not in f)


def counts_row(res):
    c = res.get('counts') or {}
    return {'findings': len(res.get('findings') or []), 'counts_json': json.dumps(c), 'errors': c.get('error', 0), 'warnings': c.get('warning', 0),
            'style': c.get('style', 0), 'portability': c.get('portability', 0), 'performance': c.get('performance', 0),
            'run_info': len(res.get('run_info') or [])}


def run_variant(variant, sink, home=None):
    from firmwarefaults.custom import sink as S
    where = fe.resolve('cppcheck-run')
    if where['how'] == 'refused':
        raise fe.FormalRefused(where['why'])
    home = home or S.home()
    t0 = datetime.datetime.now()
    row, proj = formal.gen_project(variant, home)
    files = dict(formal.stub_files())
    files.update(proj)
    name = 'cppcheck@%s' % variant
    src_sha = hashlib.sha256(b''.join(proj[k] for k in sorted(proj))).hexdigest()
    base = {'name': name, 'variant': variant, 'build_name': row['name'], 'tool': 'cppcheck', 'checks': CHECKS, 'addons': ','.join(ADDONS),
            'not_run': NOT_RUN, 'platform': 'avr8', 'files_json': json.dumps(sorted(proj)), 'source_sha256': src_sha,
            'ran_at': t0.isoformat(timespec='seconds')}
    r = fe.run('cppcheck-run', argv(files), files, timeout=300)
    try:
        res = json.loads((r['files'].get('findings.json') or b'{}').decode())
    except ValueError:
        res = {}
    if not res.get('parsed'):
        base.update(state='refused: cppcheck output did not parse — %s' % (r.get('stderr') or r.get('stdout') or '')[-300:], notes='no findings recorded')
        sink.upsert('StaticCheck', base)
        return base
    base.update(counts_row(res), tool_version=res.get('cppcheck_version', ''), engine_where='%s %s' % (r.get('how'), r.get('where')), state='ran',
                wall_s=float(res.get('wall_s', 0.0)), peak_rss_mb=float(res.get('peak_rss_mb', 0.0)),
                repro_json=json.dumps({'inputs': [{'label': 'project (sorted .c/.h)', 'sha256': src_sha}], 'tools': {'cppcheck': res.get('cppcheck_version'),
                                                                                                                     'engine': fe.digest()},
                                       'knobs': {'argv': res.get('argv')}, 'seeds': {'deterministic': True},
                                       'how_to_rerun': 'pol faults static %s' % variant}, default=str),
                notes='a finding is a row to read, never a build failure; run information (missing system includes …) kept apart: %d'
                      % len(res.get('run_info') or []))
    sink.upsert('StaticCheck', base)
    for i, f in enumerate(res.get('findings') or []):
        sink.upsert('StaticFinding', {'name': '%s#%03d' % (name, i), 'check': name, 'variant': variant, 'tool': 'cppcheck', 'check_id': f.get('id', ''),
                                      'severity': f.get('severity', ''), 'message': f.get('message', ''), 'cwe': int(f.get('cwe') or 0),
                                      'file': f.get('file', ''), 'line': int(f.get('line') or 0), 'symbol': f.get('symbol', ''), 'addon': f.get('addon', '')})
    base['_findings'] = res.get('findings') or []
    return base


def run_all(sink, variants=None, home=None, progress=None):
    out = []
    for v in (variants or all_variants()):
        r = run_variant(v, sink, home)
        out.append(r)
        if progress:
            progress('%-26s %s findings %s' % (v, r.get('findings', '-'), r.get('counts_json', '')))
    return out
