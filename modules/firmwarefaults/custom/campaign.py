"""
@module firmwarefaults.custom.campaign

THE STATISTICS TIER as campaigns (FIRMWARE_SCENARIO_PLAN.md §5 tier 3, sc-2): a ScenarioCampaign row = scenario × fault kind ×
the fault's RATE as the stimulus distribution × seeds × window. Running it runs the harness once per (side, rate, seed) with
sc-1's seed machinery (custom/campaign_runs.py), then aggregates per rate (`aggregate`, pure):

    likelihood   events / trials WITHOUT the technique (BEFORE), with its 95 % Wilson interval
    residual     the same WITH the technique (AFTER) — what the technique leaves
    ttff         the time to the first fault per seed where the run can see it (censored seeds counted apart)

and writes ScenarioStatistic rows (sc-1's class), one FaultLikelihood row per rate (the likelihood table per fault kind), the
fault row's rate / rate_source, and the `statistics` evidence tier on each build's claim — the claim's STATUS is unchanged
(a rate is a measure, never a proof); the likelihood + interval land in its measure_json. Coverage is stated on every row.

The four seeded campaigns:
  torn-read-phase        scenario 1   rx_noise_rate 200/s (the phase randomiser), 60 seeds x 10 s — per byte-0 carry
  uart-ber               scenario 4   BER 1e-3 / 1e-4 / 1e-5, 20 seeds x 500 commands — the parser's residual per command
  bounce-window          scenario 3   bounce window 0.02 / 5 / 15 / 25 / 40 ms, 10 seeds x 12 presses — per press
  ack-drop-probability   scenario 2   drop probability 0.5 / 0.2 / 0.1 per ack, 40 seeds x 1 request — per request
"""
import datetime
import json
import statistics as pystats
import time

from firmwarefaults.custom import outcome

J = json.dumps


def _c(name, title, scenario, fault_class, fault, parameter, unit, rates, seeds, run_seconds, kind, trial, stimulus, before, after, ttff, notes=''):
    return {'name': name, 'title': title, 'scenario': scenario, 'fault_class': fault_class, 'fault': fault, 'parameter': parameter,
            'parameter_unit': unit, 'rates_json': J(rates), 'seeds': seeds, 'run_seconds': run_seconds, 'sides_json': J(['before', 'after']),
            'stimulus': stimulus, 'event_before': before, 'event_after': after, 'ttff_what': ttff, 'status': 'not-run', 'kind': kind,
            'trial_unit': trial, 'provenance': 'sc-2 seed (FIRMWARE_SCENARIO_PLAN.md §5 tier 3)', 'notes': notes}


SEED_CAMPAIGNS = [
    _c('torn-read-phase', 'Scenario 1 — torn reads per tick carry under asynchronous traffic', 'torn-millis-read', 'TornReadFault',
       'torn-read-g-ms', 'rx_noise_rate', 'asynchronous RX bytes per second (exponential gaps from the seed)', [200.0], 60, 10.0, 'phase-sweep',
       'a byte-0 carry of g_ms', 'asynchronous RX bytes move the main loop\'s phase against the 1 ms tick (--rx-noise RATE --seed S); '
       'every tick\'s return PC is logged (--ret-log 7)',
       'a carry tick whose ISR returned to the 2nd lds of g_ms — a torn read (uno-sim-rig-torn)',
       'the same on the atomic build (uno-sim-rig): the tick cannot return inside the masked read',
       'ms from reset to the first torn read of the seed (seeds with none are censored at the 10 s window)',
       notes='formalises sc-1\'s phase sweep (73 / 2 340 = 3.12 % per carry) as a campaign, with the AFTER residual measured'),
    _c('uart-ber', 'Scenario 4 — the parser\'s residual frame loss per bit error rate', 'uart-residual-frame-loss', 'UartBitErrorFault',
       'uart-bit-error', 'ber', 'bit error rate on the host→board line', [1e-3, 1e-4, 1e-5], 20, 0.0, 'uart-ber', 'a command sent',
       '500 back-to-back 25-byte commands per run; every host→board bit flips with probability BER from the seed (data → XOR, stop → '
       'framing error, start → the byte lost)',
       'a command the line delivered INTACT that the shipped resync parser did not apply (the residual, intact − applied)',
       'the same with rx_parser keep-tail (uno-echo-keeptail)',
       'ms from reset to the first byte the line damaged (the stimulus\'s first hit; the firmware\'s own losses are counted at the end)',
       notes='formalises sc-1\'s BER batch; the line\'s own loss (sent − intact) is the trigger, kept on the ScenarioStatistic rows'),
    _c('bounce-window', 'Scenario 3 — double counts as a function of the contact-bounce window', 'button-bounce-double-count',
       'DoubleEdgeFault', 'contact-bounce', 'bounce_window_ms', 'ms — the bounce edge falls uniformly in (0, window] after the press',
       [0.02, 5.0, 15.0, 25.0, 40.0], 10, 0.0, 'bounce-window', 'a press',
       '12 presses per run, 60 ms + an exponential gap (mean 100 ms) apart, each followed by ONE bounce edge uniform in (0, window] '
       '(INT0 raised at both, --irq-at cycle=…,vec=1); the times drawn from the seed',
       'a press counted more than once (g_presses − presses, per press) — uno-button-count counts every edge',
       'the same with the 20 ms debounce (uno-button-debounce): a bounce later than 20 ms still counts — the technique\'s limit',
       'not observable per press: the counter is read at the end of the run'),
    _c('ack-drop-probability', 'Scenario 2 — a hang as a function of the ack drop probability', 'lost-ack-hang', 'LivelockFault',
       'lost-ack-hang', 'drop_p', 'probability each host→board ack unit is lost (one draw per unit from the seed)', [0.5, 0.2, 0.1], 40, 1.0,
       'drop-prob', 'a request (one per run)',
       'the scripted host answers every request after 0.2 ms; each answer is lost with probability p (--drop-frame rx:p=P --seed S)',
       'telemetry stops for good (a hang) — uno-ack-wait has no timeout',
       'a hang with the 50 ms timeout + 3 tries (uno-ack-wait-timeout); its give-up (all 3 acks lost → status fault, telemetry '
       'continues) is counted apart',
       'ms from reset to the start of the silence (the last telemetry frame before the hang)'),
]


def find(name, rows=None):
    for r in (rows or SEED_CAMPAIGNS):
        d = r if isinstance(r, dict) else {k: getattr(r, k, '') for k in SEED_CAMPAIGNS[0]}
        if d.get('name') == name:
            return dict(d)
    return None


def seed_rows():
    return [{k: v for k, v in c.items() if k not in ('kind', 'trial_unit')} for c in SEED_CAMPAIGNS]


def wilson_block(k, n):
    p, lo, hi = outcome.wilson(k, n)
    return {'events': int(k), 'trials': int(n), 'rate': round(p, 6), 'ci_low': round(lo, 6), 'ci_high': round(hi, 6)}


def ttff_block(values_ms, window_ms):
    """values_ms: per seed, the time of the first fault or None (censored at the window)."""
    seen = sorted(v for v in values_ms if v is not None)
    out = {'n_seeds': len(values_ms), 'observed': len(seen), 'censored': len(values_ms) - len(seen), 'window_ms': window_ms}
    if seen:
        out.update(min_ms=round(seen[0], 1), median_ms=round(pystats.median(seen), 1), mean_ms=round(sum(seen) / len(seen), 1),
                   max_ms=round(seen[-1], 1))
    return out


def aggregate(per_rate):
    """per_rate: [{rate, before: (k, n), after: (k, n), after_aux: (k, n)|None, ttff: [ms|None], window_ms}] → the results list
    the campaign row carries (pure; the selftest feeds it fixtures)."""
    out = []
    for r in per_rate:
        row = {'rate': r['rate'], 'before': wilson_block(*r['before']), 'after': wilson_block(*r['after'])}
        if r.get('after_aux'):
            row['after_aux'] = dict(wilson_block(*r['after_aux']), what=r.get('aux_what', ''))
        if r.get('ttff') is not None:
            row['ttff'] = ttff_block(r['ttff'], r.get('window_ms', 0.0))
        if r.get('extra'):
            row['extra'] = r['extra']
        out.append(row)
    return out


def _pct(b):
    return '%d/%d = %.3f %% [%.3f, %.3f]' % (b['events'], b['trials'], 100 * b['rate'], 100 * b['ci_low'], 100 * b['ci_high'])


def summary_lines(c, results):
    lines = []
    for r in results:
        s = '%s %g: BEFORE %s · AFTER %s' % (c['parameter'], r['rate'], _pct(r['before']), _pct(r['after']))
        if r.get('after_aux'):
            s += ' · %s %s' % (r['after_aux'].get('what', 'aux'), _pct(r['after_aux']))
        lines.append(s)
    return lines


def ttff_lines(c, results):
    out = []
    for r in results:
        t = r.get('ttff')
        if not t:
            continue
        if t.get('observed'):
            out.append('%s %g: first fault in %d of %d seeds — median %.1f ms [%.1f … %.1f], %d censored at %.0f ms' % (
                c['parameter'], r['rate'], t['observed'], t['n_seeds'], t['median_ms'], t['min_ms'], t['max_ms'], t['censored'], t['window_ms']))
        else:
            out.append('%s %g: no fault in any of %d seeds (all censored at %.0f ms)' % (c['parameter'], r['rate'], t['n_seeds'], t['window_ms']))
    return out or ['not observable: %s' % c.get('ttff_what', '')]


def likelihood_rows(c, results, technique, coverage, ran_at):
    rows = []
    for r in results:
        b, a = r['before'], r['after']
        rows.append({'name': '%s@%s=%g' % (c['fault'], c['parameter'], r['rate']), 'fault_class': c['fault_class'], 'fault': c['fault'],
                     'campaign': c['name'], 'scenario': c['scenario'], 'parameter': c['parameter'], 'parameter_value': float(r['rate']),
                     'parameter_unit': c['parameter_unit'], 'trial_unit': c.get('trial_unit', ''), 'before_events': b['events'],
                     'before_trials': b['trials'], 'before_rate': b['rate'], 'before_ci_low': b['ci_low'], 'before_ci_high': b['ci_high'],
                     'technique': technique, 'after_events': a['events'], 'after_trials': a['trials'], 'after_rate': a['rate'],
                     'after_ci_low': a['ci_low'], 'after_ci_high': a['ci_high'],
                     'ttff_median_ms': float((r.get('ttff') or {}).get('median_ms', -1.0)), 'coverage': coverage, 'ran_at': ran_at,
                     'notes': ('%s: %s' % (r['after_aux'].get('what'), _pct(r['after_aux']))) if r.get('after_aux') else (
                         J(r['extra'], default=str)[:400] if r.get('extra') else '')})
    return rows


def _fault_rate_source(sink, c, results, coverage):
    from firmwarefaults.custom.fault_rows import by_class
    if c['kind'] in ('phase-sweep', 'uart-ber'):
        return None   # sc-1's batch functions already wrote these fault rows with the full reading; the campaign adds the table
    seed = next((r for r in by_class().get(c['fault_class'], []) if r['name'] == c['fault']), {'name': c['fault']})
    cur = sink.get(c['fault_class'], c['fault'])
    row = dict(cur) if isinstance(cur, dict) else dict(seed)
    worst = max(results, key=lambda r: r['before']['rate'])
    row.update(name=c['fault'], rate=worst['before']['rate'], rate_unit='events per %s without the technique, at %s = %g' % (
        c.get('trial_unit', 'trial'), c['parameter'], worst['rate']),
        rate_source='measured (sc-2 campaign %s, simavr twin, %s): %s. The stimulus itself (%s) is NOT a cited field rate — these are '
                    'likelihoods GIVEN it.' % (c['name'], coverage, '; '.join(summary_lines(c, results)), c['parameter_unit']))
    sink.upsert(c['fault_class'], row)
    return row


def run_campaign(name, sink, seeds=None, rates=None, home=None, progress=None, rows=None):
    """Run ONE campaign → the ScenarioCampaign dict (written) with its results. Raises runner.ScenarioRefused /
    engine_run.EngineRefused when the twin cannot run."""
    from firmwarefaults.custom import campaign_runs, fault_engines as fe
    from firmwarefaults.custom import scenarios as SC
    from firmwarefaults.custom.claim_bridge import claim_name, add_evidence
    from firmwarefaults.custom.runner import ScenarioRefused
    c = find(name, rows)
    if c is None:
        raise ScenarioRefused('no campaign %r — one of %s' % (name, ', '.join(x['name'] for x in SEED_CAMPAIGNS)))
    if 'kind' not in c:
        c.update({k: v for k, v in find(name).items() if k in ('kind', 'trial_unit')})
    seeds = int(seeds or c['seeds'])
    rates = [float(x) for x in (rates or json.loads(c['rates_json']))]
    sc = SC.find(c['scenario'])
    t0, ran_at = time.time(), datetime.datetime.now().isoformat(timespec='seconds')
    out = campaign_runs.RUNNERS[c['kind']](c, sink, rates, seeds, home=home, progress=progress)
    results = aggregate(out['per_rate'])
    coverage = '%d seeds per (side, %s) x %s per run; builds %s (BEFORE) / %s (AFTER); the twin = simavr 1.6 in %s' % (
        seeds, c['parameter'], out.get('window_words', '%g s' % c['run_seconds']), out['builds']['before'], out['builds']['after'], fe.harness_digest())
    lines = summary_lines(c, results)
    c.update(status='ran', results_json=J(results, default=str), likelihood_summary=' | '.join(lines), ttff_summary=' | '.join(ttff_lines(c, results)),
             statistics_json=J(out.get('statistics', [])), runs=int(out.get('runs', 0)), wall_s=round(time.time() - t0, 1), harness_digest=fe.harness_digest(),
             seeds=seeds, rates_json=J(rates), ran_at=ran_at,
             repro_json=J({'seeds': '0..%d per (side, rate), the SAME seeds on both sides (paired)' % (seeds - 1), 'rates': rates,
                           'firmware_sha256': out.get('firmware', {}), 'harness': fe.harness_digest(), 'stimulus': c['stimulus'],
                           'draws': out.get('draws', 'harness splitmix64 streams from --seed'),
                           'how_to_rerun': 'pol faults campaign run %s --seeds %d' % (name, seeds),
                           'rule': 'every result carries the initial conditions and seeds that produced it (2026-09-26)'}, default=str))
    sink.upsert('ScenarioCampaign', {k: v for k, v in c.items() if k not in ('kind', 'trial_unit')})
    for lr in likelihood_rows(c, results, sc.get('technique', ''), coverage, ran_at):
        sink.upsert('FaultLikelihood', lr)
    _fault_rate_source(sink, c, results, coverage)
    for side in ('before', 'after'):
        bname = out['builds'][side]
        measure = {'campaign': name, 'parameter': c['parameter'], 'trial': c.get('trial_unit', ''), 'coverage': coverage, 'ci': 'Wilson 95 %',
                   'values': [dict(r[side], stimulus=r['rate']) for r in results]}
        add_evidence(sink, claim_name(c['scenario'], bname), {'tier': 'statistics', 'status': 'measured', 'ref': name,
                                                               'measure': '; '.join('%s %g: %s' % (c['parameter'], r['rate'], _pct(r[side])) for r in results)},
                     base={'description': 'Firmware build %s under scenario %s is free of fault %s (%s)' % (bname, c['scenario'], c['fault'], c['fault_class']),
                           'proof_status': 'conjectured', 'checker': '', 'counterexample_json': '{}', 'evidence_level': 'none',
                           'about_refs_json': J(['Scenario:%s' % c['scenario'], 'FirmwareBuild:%s' % bname, '%s:%s' % (c['fault_class'], c['fault'])])},
                     measure=measure)
    c['_results'] = results
    return c
