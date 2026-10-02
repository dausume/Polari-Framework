"""
@module firmwarefaults.custom.campaign_runs

The per-scenario BATCHES behind custom/campaign.py (sc-2): each runs the harness once per (side, rate, seed) and returns
{per_rate: [{rate, before: (k, n), after: (k, n), after_aux?, ttff, window_ms, extra?}], builds, statistics, runs, firmware}.
The same seeds run on both sides (paired), so BEFORE and AFTER meet the same stimulus.

  phase-sweep    scenario 1: statistics.tear_phase_sweep (BEFORE, + the natural run) and tear_sweep_after (the residual)
  uart-ber       scenario 4: statistics.uart_ber — the residual (intact − applied) per command sent is the bug; the line's
                 own loss is the trigger, kept on the ScenarioStatistic rows
  bounce-window  scenario 3: 12 presses per run, each followed by one bounce edge uniform in (0, window]; times from a
                 seeded Python RNG (random.Random('bounce:<seed>:<window>'), deterministic), raised as INT0 at those cycles
  drop-prob      scenario 2: each ack unit lost with probability p (the harness's own seeded draw, --drop-frame rx:p=P)
"""
import json
import random
import time

from firmwarefaults.custom import statistics as ST
from firmwarefaults.custom import scenarios as SC

FREQ = 16000000.0
PRESSES = 12
PRESS_START_S = 0.5
PRESS_GAP_MIN_S = 0.06
PRESS_GAP_MEAN_S = 0.10


def run_phase(c, sink, rates, seeds, home=None, progress=None):
    per, stats, runs, fw, builds = [], [], 0, {}, {}
    for rate in rates:
        out = ST.tear_phase_sweep(sink, seeds=seeds, noise_rate=rate, seconds=10.0, home=home, progress=progress)
        b = out['sweep']
        a = ST.tear_sweep_after(sink, seeds=seeds, noise_rate=rate, seconds=10.0, home=home, progress=progress)
        per.append({'rate': rate, 'before': (b['events'], b['trials']), 'after': (a['events'], a['trials']),
                    'ttff': [x / FREQ * 1000.0 if x is not None else None for x in b['_firsts']], 'window_ms': 10000.0,
                    'extra': {'natural_exposure': out['natural_row']['rate'], 'after_frames_backwards': a['_frames_backwards']}})
        stats += [out['natural_row']['name'], b['name'], a['name']]
        runs += 2 * seeds + 1
        builds = {'before': b['build_name'], 'after': a['build_name']}
        fw = {'before': b['firmware_sha256'], 'after': a['firmware_sha256']}
    return {'per_rate': per, 'builds': builds, 'statistics': stats, 'runs': runs, 'firmware': fw, 'window_words': '10 s',
            'draws': 'harness --rx-noise exponential gaps (splitmix64 from --seed)'}


def run_ber(c, sink, rates, seeds, home=None, progress=None):
    out = ST.uart_ber(sink, bers=tuple(rates), seeds=seeds, home=home, progress=progress)
    per, stats = [], []
    for ber in rates:
        b, a = out[('before', ber)], out[('after', ber)]
        win = b.get('window_s', 0.0) * 1000.0
        per.append({'rate': ber, 'before': (b.get('residual_events', 0), b['trials']), 'after': (a.get('residual_events', 0), a['trials']),
                    'ttff': b.get('_ttff_ms'), 'window_ms': win,
                    'extra': {'line_lost_before': '%d/%d' % (b['events'], b['trials']), 'line_lost_after': '%d/%d' % (a['events'], a['trials'])}})
        stats += [b['name'], a['name']]
    any_b = out[('before', rates[0])]
    any_a = out[('after', rates[0])]
    return {'per_rate': per, 'builds': {'before': any_b['build_name'], 'after': any_a['build_name']}, 'statistics': stats,
            'runs': 2 * seeds * len(rates), 'firmware': {'before': any_b['firmware_sha256'], 'after': any_a['firmware_sha256']},
            'window_words': '500 commands (%.2f s)' % any_b.get('window_s', 0.0), 'draws': 'harness --uart-ber (splitmix64 from --seed)'}


def press_schedule(seed, window_ms, presses=PRESSES):
    """[(press_cycle, bounce_cycle)] for one run — deterministic from (seed, window)."""
    rng = random.Random('bounce:%d:%g' % (seed, window_ms))
    t, out = PRESS_START_S, []
    for _ in range(presses):
        d = rng.uniform(0.0, window_ms / 1000.0) or 1e-6
        out.append((int(round(t * FREQ)), int(round((t + d) * FREQ))))
        t += PRESS_GAP_MIN_S + rng.expovariate(1.0 / PRESS_GAP_MEAN_S)
    return out


def bounce_steps(sched):
    steps = []
    for i, (p, b) in enumerate(sched):
        for kind, cyc in (('press', p), ('bounce', b)):
            steps.append({'name': 'campaign#%d%s' % (i, kind[0]), 'scenario': 'button-bounce-double-count', 'order': len(steps) + 1,
                          'kind': 'irq-at-cycle', 'args_json': json.dumps({'cycle': cyc, 'vec': 1, 'vector_name': 'INT0'}), 'condition_json': '{}'})
    return steps


def run_bounce(c, sink, rates, seeds, home=None, progress=None):
    from firmwarefaults.custom import runner_sc1, fault_engines as fe
    sc = SC.find(c['scenario'])
    per, stats, runs, builds, fw = [], [], 0, {}, {}
    for w in rates:
        res = {}
        for side in ('before', 'after'):
            t0 = time.time()
            extra = deficit = presses = 0
            per_seed = []
            for s in range(seeds):
                sched = press_schedule(s, w)
                secs = round(sched[-1][1] / FREQ + 0.15, 3)
                r = runner_sc1.run_side(sc, side, sink, seed=s, home=home, replace_steps=bounce_steps(sched), cache=True, write=False, seconds=secs)
                o = json.loads(r['observed_json'])
                g = int((o.get('watches') or {}).get('g_presses') or 0)
                presses += len(sched)
                extra += max(0, g - len(sched))
                deficit += max(0, len(sched) - g)
                per_seed.append('%d/%d' % (g, len(sched)))
                builds[side], fw[side] = r['build_name'], r['firmware_sha256']
                runs += 1
                if progress:
                    progress('%s window %g ms seed %d: counted %d for %d presses' % (side, w, s, g, len(sched)))
            res[side] = (extra, presses, deficit)
            row = ST._stat('%s@%s@bounce-window=%gms' % (sc['name'], side, w), sc['name'], side, sc['%s_variant' % side], builds[side],
                           'event = a press counted more than once (g_presses − presses, summed); trials = presses; each press is followed by '
                           'one bounce edge uniform in (0, %g ms]' % w, 'bounce_window_ms', w, list(range(seeds)), presses, extra,
                           per_seed='counted/presses per seed: ' + ', '.join(per_seed), wall_s=time.time() - t0, fw=fw[side],
                           harness_digest=fe.harness_digest(), repro={'presses_per_run': PRESSES, 'rng': "random.Random('bounce:<seed>:<window>')",
                                                                      'gap': '%g s + Exp(mean %g s)' % (PRESS_GAP_MIN_S, PRESS_GAP_MEAN_S),
                                                                      'how_to_rerun': 'pol faults campaign run bounce-window'},
                           notes='real presses swallowed (counted fewer than pressed): %d' % deficit)
            sink.upsert('ScenarioStatistic', row)
            stats.append(row['name'])
        per.append({'rate': w, 'before': res['before'][:2], 'after': res['after'][:2], 'ttff': None,
                    'extra': {'swallowed_before': res['before'][2], 'swallowed_after': res['after'][2]}})
    return {'per_rate': per, 'builds': builds, 'statistics': stats, 'runs': runs, 'firmware': fw,
            'window_words': '%d presses (≈ 2.5 s)' % PRESSES, 'draws': "Python random.Random('bounce:<seed>:<window>') — string-seeded, deterministic"}


def drop_steps(p):
    st = []
    for s in SC.steps_of('lost-ack-hang'):
        s = dict(s)
        if s['kind'] == 'drop-nth-frame':
            s.update(kind='drop-prob', args_json=json.dumps({'p': p}), notes='each ack lost with probability %g (one draw per unit)' % p)
        st.append(s)
    return st


def run_drop(c, sink, rates, seeds, home=None, progress=None):
    from firmwarefaults.custom import runner_sc1, fault_engines as fe
    sc = SC.find(c['scenario'])
    per, stats, runs, builds, fw = [], [], 0, {}, {}
    secs = float(c.get('run_seconds') or 1.0)
    for p in rates:
        res, ttff = {}, []
        for side in ('before', 'after'):
            t0 = time.time()
            hangs = gaveup = 0
            per_seed = []
            for s in range(seeds):
                r = runner_sc1.run_side(sc, side, sink, seed=s, home=home, replace_steps=drop_steps(p), cache=True, write=False, seconds=secs)
                o = json.loads(r['observed_json'])
                hung = r['outcome'] == 'failed'
                gave = int((o.get('watches') or {}).get('g_ack_state') or 0) == 3
                hangs += hung
                gaveup += gave
                per_seed.append('H' if hung else ('G' if gave else '.'))
                if side == 'before':
                    last = ((o.get('frames') or {}).get('last_ms') or [None])[-1]
                    ttff.append(last if hung else None)
                builds[side], fw[side] = r['build_name'], r['firmware_sha256']
                runs += 1
                if progress:
                    progress('%s p=%g seed %d: %s' % (side, p, s, 'HANG' if hung else ('gave up' if gave else 'ok')))
            res[side] = (hangs, seeds, gaveup)
            row = ST._stat('%s@%s@drop-p=%g' % (sc['name'], side, p), sc['name'], side, sc['%s_variant' % side], builds[side],
                           'event = telemetry stopped for good (a hang); trials = runs (one request each); each ack lost with probability %g' % p,
                           'drop_p', p, list(range(seeds)), seeds, hangs, per_seed='per seed (H hang, G gave up, . acked): ' + ''.join(per_seed),
                           window_s=secs, wall_s=time.time() - t0, fw=fw[side], harness_digest=fe.harness_digest(),
                           repro={'drop': '--drop-frame rx:p=%g (splitmix64 stream from --seed)' % p, 'how_to_rerun': 'pol faults campaign run ack-drop-probability'},
                           notes='gave up (all tries lost → status fault, telemetry continues): %d' % gaveup)
            sink.upsert('ScenarioStatistic', row)
            stats.append(row['name'])
        per.append({'rate': p, 'before': res['before'][:2], 'after': res['after'][:2], 'after_aux': (res['after'][2], seeds),
                    'aux_what': 'gave up (3 acks lost, status fault — no hang)', 'ttff': ttff, 'window_ms': secs * 1000.0})
    return {'per_rate': per, 'builds': builds, 'statistics': stats, 'runs': runs, 'firmware': fw, 'window_words': '%g s' % secs,
            'draws': 'harness --drop-frame rx:p (splitmix64 stream from --seed)'}


RUNNERS = {'phase-sweep': run_phase, 'uart-ber': run_ber, 'bounce-window': run_bounce, 'drop-prob': run_drop}
