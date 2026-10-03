"""The PIPELINE's `scenarios` stage, framework side (FIRMWARE_SCENARIO_PLAN.md §9 sc-4, D-sc-3: ADVISORY; the proofs_stage.py
pattern): every RUNNABLE firmwarefaults scenario re-run as its BEFORE/AFTER pair on the simavr UNO twin with N seeds, in THIS
process (the engines resolve through the board seam: BOARD_ENGINES_URL → a local binary → the local image → the topology), and
ONE summary JSON in the shape polari-jenkins/scenarios.sh writes — so that stage can call this instead of its own driver:

    {ran, not_run, image, engines, seeds, runnable, not_runnable,
     pairs: [{scenario, seed, before: {outcome, claim_status, variant, observed, words, wall_s}, after: {…} | null, cycle, cost, wall_s, rc}],
     red: [{scenario, seed, why}], warn: [...], counts: {pairs, witnessed, refused_builds, red}, pairs_wall_s, elapsed_s, advisory}

A red pair (AFTER not witnessed — sc-2: a formal `decided` counts as held —, a pair that would not run, a build guard that no longer
refuses) is RECORDED, never a build failure: exit 0 always. A human summary goes to stderr.

    PYTHONPATH=.:modules python3 tests/scenarios_stage.py [--out results.json] [--seeds N] [--only a,b]
    docker run --rm -e BOARD_ENGINES_URL --entrypoint python3 prf-backend:staging tests/scenarios_stage.py --out /tmp/results.json
"""
import argparse
import json
import os
import sys
import tempfile
import time

FRAMEWORK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, FRAMEWORK); sys.path.insert(0, os.path.join(FRAMEWORK, 'modules'))
ADVISORY = 'scenario pairs never gate — a red pair is recorded, not enforced (FIRMWARE_SCENARIO_PLAN D-sc-3)'
HELD = ('witnessed', 'decided')


def side_of(r):
    if not r:
        return None
    return {'outcome': r.get('outcome', ''), 'claim_status': r.get('claim_status', ''), 'variant': r.get('variant', ''),
            'observed': (r.get('observable_value') or r.get('uptime_sequence') or '')[:120], 'words': (r.get('verdict_words') or '')[:200],
            'wall_s': r.get('wall_s')}


def cost_of(after):
    try:
        cd = json.loads((after or {}).get('cost_delta_json') or '{}')
    except ValueError:
        cd = {}
    return {k: cd[k] for k in ('flash_bytes', 'ram_bytes', 'cycles', 'guarded_fn_cycles', 'cycles_what', 'isr_latency_max_cycles',
                               'stack_high_water_bytes') if k in cd}


def judge(pairs):
    """The pairs → (red, warn, counts) — pure (the module selftest feeds it fixtures)."""
    red, warn = [], []
    for p in pairs:
        b, a = p['before'], p['after']
        if p.get('rc') not in (0, None) or b is None:
            red.append({'scenario': p['scenario'], 'seed': p['seed'], 'why': 'did not run (rc=%s): %s' % (p.get('rc'), p.get('error', '')[:300])})
        elif a is None:      # a build-refused scenario (1b): the refusal IS the safe outcome
            if b['outcome'] != 'inapplicable':
                red.append({'scenario': p['scenario'], 'seed': p['seed'], 'why': 'the guard no longer refuses the build: BEFORE %s' % b['outcome']})
        elif a['claim_status'] not in HELD and not (not a['claim_status'] and a['outcome'] == 'passed'):
            red.append({'scenario': p['scenario'], 'seed': p['seed'], 'why': 'AFTER (%s) not witnessed: %s / %s — %s' % (
                a['variant'], a['outcome'], a['claim_status'] or '-', a['words'][:160])})
        if b and a and b['outcome'] != 'failed':
            warn.append({'scenario': p['scenario'], 'seed': p['seed'], 'why': 'BEFORE (%s) no longer reproduces the fault: %s' % (b['variant'], b['outcome'])})
    counts = {'pairs': len(pairs), 'witnessed': sum(1 for p in pairs if p['after'] and p['after']['claim_status'] in HELD),
              'refused_builds': sum(1 for p in pairs if p['before'] and not p['after'] and p['before']['outcome'] == 'inapplicable'),
              'red': len(red)}
    return red, warn, counts


def run_pairs(names, seeds, say=lambda s: None):
    from firmwarefaults.custom import runner
    from firmwarefaults.custom.sink import LocalSink
    pairs = []
    for n in names:
        for k in range(seeds):
            os.environ['POLARI_FAULTS_HOME'] = tempfile.mkdtemp(prefix='scn-%s-%d-' % (n, k))
            runner._BUILDS.clear()
            t0 = time.time()
            p = {'scenario': n, 'seed': k, 'before': None, 'after': None, 'cycle': 0, 'cost': {}, 'rc': 0}
            try:
                out = runner.run_scenario(n, 'both', LocalSink(), seed=k)
                runs = {r['side']: r for r in out['runs']}
                p.update(before=side_of(runs.get('before')), after=side_of(runs.get('after')),
                         cycle=int((runs.get('before') or {}).get('fault_cycle') or 0), cost=cost_of(runs.get('after')))
            except Exception as e:  # noqa: BLE001 — recorded as a red pair, never thrown (advisory)
                p.update(rc=1, error='%s: %s' % (type(e).__name__, e))
            p['wall_s'] = round(time.time() - t0, 3)
            pairs.append(p)
            say('%s seed %d: BEFORE %s · AFTER %s (%.1f s)%s' % (n, k, (p['before'] or {}).get('outcome', '-'), (p['after'] or {}).get('outcome', '-'),
                                                             p['wall_s'], ' — ' + p['error'][:200] if p.get('error') else ''))
    return pairs


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default='-')
    ap.add_argument('--seeds', type=int, default=int(os.environ.get('CI_SCENARIO_SEEDS', '1') or 1))
    ap.add_argument('--only', default='')
    a = ap.parse_args(argv)
    say = lambda s: print('[scenarios] ' + s, file=sys.stderr, flush=True)  # noqa: E731
    t0 = time.time()
    doc = {'ran': False, 'not_run': '', 'image': os.environ.get('CI_SELFTEST_IMAGE', ''), 'engines': '', 'seeds': max(1, a.seeds), 'runnable': [],
           'not_runnable': [], 'pairs': [], 'red': [], 'warn': [], 'counts': {}, 'advisory': ADVISORY}
    try:
        from firmwarefaults.custom import scenarios as SC, fault_engines as fe
        doc['engines'] = '; '.join('%s: %s %s' % (e, w['how'], w['where']) for e, w in fe.placement().items())
        if not fe.available():
            doc['not_run'] = 'no twin / disassembler resolves on this device: %s' % fe.resolve('avr-twin')['why']
        else:
            only = [x for x in a.only.split(',') if x]
            doc['runnable'] = [s['name'] for s in SC.SEED_SCENARIOS if SC.runnable(s) and not SC.engine_gap(s) and (not only or s['name'] in only)]
            doc['not_runnable'] = [{'scenario': s['name'], 'why': (SC.refusal(s) or SC.engine_gap(s))[:200]} for s in SC.SEED_SCENARIOS
                                   if not SC.runnable(s) or SC.engine_gap(s)]   # sc-3: a C3 scenario without the esp engines here
            doc['pairs'] = run_pairs(doc['runnable'], doc['seeds'], say)
            doc['red'], doc['warn'], doc['counts'] = judge(doc['pairs'])
            doc['ran'] = bool(doc['pairs'])
            doc['not_run'] = '' if doc['pairs'] else 'no pair produced a record'
    except Exception as e:  # noqa: BLE001 — the stage never throws
        doc['not_run'] = 'the stage could not start: %s: %s' % (type(e).__name__, e)
    doc['pairs_wall_s'] = round(sum(float(p.get('wall_s') or 0) for p in doc['pairs']), 3)
    doc['elapsed_s'] = round(time.time() - t0, 3)
    text = json.dumps(doc, indent=1, default=str)
    if a.out == '-':
        print(text)
    else:
        open(a.out, 'w').write(text)
    c = doc['counts']
    say('%d pair(s): %d held, %d refused build(s), %d red%s · %.1f s%s' % (c.get('pairs', 0), c.get('witnessed', 0), c.get('refused_builds', 0),
        c.get('red', 0), (' (' + ', '.join(r['scenario'] for r in doc['red']) + ')') if doc['red'] else '', doc['elapsed_s'],
        (' · NOT RUN: ' + doc['not_run']) if doc['not_run'] else ''))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
