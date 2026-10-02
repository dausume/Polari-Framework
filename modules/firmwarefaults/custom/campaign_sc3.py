"""
@module firmwarefaults.custom.campaign_sc3

THE sc-3 CAMPAIGN (FIRMWARE_SCENARIO_PLAN.md §5 tier 3 on the C3): the interleaving's offsets SEEDED — each seed k draws the
recipe's `seeded` knobs (scenarios_sc3.knobs_for: priority inversion h_off ∈ [0, 3], m_off ∈ [0, 4] ticks; the two-lock recipe
t1_gap ∈ [0, 3], t2_start ∈ [0, 4], t2_gap ∈ [0, 2] ticks) — and runs BOTH builds on the SAME knobs. One trial = one seed (one
run of 10 rounds): an EVENT is a BEFORE run that failed (the inversion past the bound / a persistent wait-for cycle), the
RESIDUAL an AFTER run that failed. → the likelihood with its 95 % Wilson interval (outcome.wilson) as a ScenarioStatistic row,
a FaultLikelihood row (sc-2's likelihood table), the fault row's measured rate + its source, and the claims' `statistics`
tier (status unchanged; the likelihood in measure_json). The builds are made once (the build cache); the seeds re-steer the
same images through the params partition.

Coverage, stated on every row: these seeds, these knob ranges, these builds, -icount 3 — an estimate under a uniform draw of
tick offsets, never a field rate.

    run(sink, scenario, seeds=10, first_seed=1) → {'stat', 'likelihood', 'per_seed': [...]}
"""
import datetime
import json
import time

from firmwarefaults.custom import outcome, runner_sc3, scenarios as SC
from firmwarefaults.custom import scenarios_sc3 as S3
from firmwarefaults.custom.statistics import _stat

SEEDS = 10
TRIAL = {'h-blocking-bounded': 'one run of 10 rounds (H vs L\'s section)', 'wait-for-acyclic': 'one run of 10 rounds (T1 + T2)'}


def run(sink, scenario, seeds=SEEDS, first_seed=1, progress=None, h=None):
    sc = SC.find(scenario)
    if sc is None or sc['observable_kind'] not in runner_sc3.KINDS:
        raise runner_sc3.ScenarioRefused('a C3 campaign runs the sc-3 scenarios: %s' % ', '.join(s['name'] for s in S3.SC3_SCENARIOS))
    t0 = time.time()
    seed_list = list(range(int(first_seed), int(first_seed) + int(seeds)))
    per, ev_b, ev_a = [], 0, 0
    builds = {}
    for k in seed_list:
        b = runner_sc3.run_side(sc, 'before', sink, k, write=False, h=h)
        a = runner_sc3.run_side(sc, 'after', sink, k, write=False, h=h)
        builds = {'before': b['build_name'], 'after': a['build_name'], 'fw_before': b['firmware_sha256'], 'fw_after': a['firmware_sha256']}
        knobs = json.loads(b['observed_json'])['knobs']
        seeded = {x: knobs[x] for x in json.loads(SC.steps_of(sc['name'])[0]['args_json']).get('seeded', {})}
        fb, fa = b['outcome'] == 'failed', a['outcome'] == 'failed'
        ev_b += fb
        ev_a += fa
        per.append({'seed': k, 'knobs': seeded, 'before': b['outcome'], 'after': a['outcome'], 'before_value': b['observable_value'],
                    'after_value': a['observable_value'], 'before_trace_sha256': b['trace_sha256'], 'after_trace_sha256': a['trace_sha256']})
        if progress:
            progress('seed %d %s: BEFORE %s (%s) · AFTER %s (%s)' % (k, seeded, b['outcome'], b['observable_value'], a['outcome'], a['observable_value']))
    n = len(seed_list)
    wall = time.time() - t0
    name = 'c3-campaign:%s:seeds%d-%d' % (sc['name'], seed_list[0], seed_list[-1])
    per_txt = '; '.join('s%d %s → %s/%s' % (p['seed'], ','.join('%s=%s' % kv for kv in sorted(p['knobs'].items())), p['before'][:4], p['after'][:4])
                        for p in per)
    cov = ('%d seeds (%d..%d), knobs drawn uniformly (splitmix64) from %s, builds %s / %s, Espressif QEMU -icount 3 — an estimate under a uniform '
           'draw of tick offsets, not a field rate' % (n, seed_list[0], seed_list[-1], json.loads(SC.steps_of(sc['name'])[0]['args_json']).get('seeded'),
                                                       builds.get('before'), builds.get('after')))
    repro = {'seeds': seed_list, 'per_seed': per, 'knob_draw': 'scenarios_sc3.knobs_for (splitmix64)', 'builds': builds,
             'how_to_rerun': 'pol faults stats %s --seeds %d' % (sc['name'], n)}
    stat = _stat(name, sc['name'], 'pair', sc['before_variant'], builds.get('before', ''), 'failed runs WITHOUT the technique (events) / WITH it (residual)',
                 'seeded tick offsets', float(n), seed_list, n, ev_b, residual=ev_a, per_seed=per_txt[:4000], window_s=sc['run_seconds'], wall_s=wall,
                 fw=builds.get('fw_before', ''), harness_digest='prf-esp-engines (polari-c3-run, QEMU esp_develop_9.2.2_20260417)', repro=repro,
                 notes=cov)
    sink.upsert('ScenarioStatistic', stat)
    pb, lb, hb = outcome.wilson(ev_b, n)
    pa, la, ha = outcome.wilson(ev_a, n)
    lik = {'name': name, 'fault_class': sc['fault_class'], 'fault': sc['fault'], 'campaign': name, 'scenario': sc['name'],
           'parameter': 'seeded tick offsets', 'parameter_value': float(n), 'parameter_unit': 'seeds', 'trial_unit': TRIAL[sc['observable_kind']],
           'before_events': ev_b, 'before_trials': n, 'before_rate': round(pb, 6), 'before_ci_low': round(lb, 6), 'before_ci_high': round(hb, 6),
           'technique': sc['technique'], 'after_events': ev_a, 'after_trials': n, 'after_rate': round(pa, 6), 'after_ci_low': round(la, 6),
           'after_ci_high': round(ha, 6), 'ttff_median_ms': -1.0, 'coverage': cov, 'ran_at': datetime.datetime.now().isoformat(timespec='seconds'),
           'notes': per_txt[:2000]}
    sink.upsert('FaultLikelihood', lik)
    from firmwarefaults.custom.fault_rows import by_class
    seed_row = next((r for r in by_class().get(sc['fault_class'], []) if r['name'] == sc['fault']), {'name': sc['fault']})
    cur = sink.get(sc['fault_class'], sc['fault'])
    row = dict(cur) if isinstance(cur, dict) else dict(seed_row) if cur is None else {'name': sc['fault']}
    row.update(name=sc['fault'], rate=round(pb, 4), rate_unit='per run (10 rounds) under seeded tick offsets',
               rate_source=('measured (sc-3): campaign %s — %d of %d seeded runs failed WITHOUT %s = %.1f %% [%.1f, %.1f] (Wilson 95 %%); WITH it %d of %d '
                            '= %.1f %% [%.1f, %.1f]; %s' % (name, ev_b, n, sc['technique'], 100 * pb, 100 * lb, 100 * hb, ev_a, n, 100 * pa, 100 * la, 100 * ha, cov)))
    sink.upsert(sc['fault_class'], row)
    from firmwarefaults.custom.claim_bridge import add_evidence, claim_name
    for side, bname, ev, p, lo, hi in (('before', builds.get('before'), ev_b, pb, lb, hb), ('after', builds.get('after'), ev_a, pa, la, ha)):
        if bname:
            m = {'events': ev, 'trials': n, 'rate': round(p, 6), 'ci': [round(lo, 6), round(hi, 6)], 'campaign': name, 'coverage': cov}
            add_evidence(sink, claim_name(sc['name'], bname), {'tier': 'statistics', 'status': 'measured', 'ref': name,
                                                               'measure': '%d/%d failed = %.1f %% [%.1f, %.1f]' % (ev, n, 100 * p, 100 * lo, 100 * hi)},
                         base={'description': 'stated by the C3 campaign', 'checker': 'sim'}, measure=m)
    return {'stat': stat, 'likelihood': lik, 'per_seed': per, 'fault_row': row}
