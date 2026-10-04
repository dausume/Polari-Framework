"""
@module firmwarefaults.custom.statistics

THE STATISTICS TIER, first step (FIRMWARE_SCENARIO_PLAN.md §5 tier 3; sc-1): many seeded runs → a rate with a 95 % Wilson
interval, written as ScenarioStatistic rows (+ the measured rate onto the fault row). Two batches:

  uart_ber(...)        scenario 4 under --uart-ber p: 500 back-to-back commands per run, 20 seeds per BER, BEFORE (the shipped
                       resync parser) and AFTER (keep-tail). Per run: sent, intact (what an ideal parser finds in the bytes that
                       actually reached the board — board.custom.packet_ref.StreamParser over the twin's --uart-rx-log), applied
                       (the echo app's `echoes`). lost = sent − applied (per 1000); residual = intact − applied (the parser's own
                       share; 0 means it lost nothing the line delivered whole).
  tear_phase_sweep(...) scenario 1's natural tear rate: sc-0 saw 0 tears in 39 byte-0 carries and could not tell a locked phase
                       from luck. Here: (a) the natural run's EVERY tick logged with its return PC (--ret-log 7) → how often a
                       tick lands on the 2nd `lds` of g_ms at all, and inside the carries' own residue classes; (b) 20 seeds of
                       asynchronous RX traffic (--rx-noise, exponential gaps) that move the loop's phase against the tick → the
                       per-carry tear probability with its interval. A tear = a carry tick (g_ms & 0xFF == 0xFF) whose ISR
                       returned to the 2nd lds; the frames' backwards drops are counted beside it as the cross-check.

Coverage is stated on every row (these seeds, this window, this build): an estimate, never a proof.
"""
import datetime
import json
import time

from firmwarefaults.custom import disasm, harness, outcome, payloads
from firmwarefaults.custom import scenarios as SC

BERS = (1e-3, 1e-4, 1e-5)
SEEDS = 20
COMMANDS = 500
NOISE_RATE = 200.0
TWIN_RX_BYTES_PER_S = 5000.0   # measured: the twin's USART input runs at ~5.4 kB/s here (XON-paced); used only to size the window


def _now():
    return datetime.datetime.now().isoformat(timespec='seconds')


def _stat(name, sc, side, variant, build, measure, parameter, value, seed_list, trials, events, residual=None, per_seed='', window_s=0.0,
          wall_s=0.0, fw='', harness_digest='', repro=None, notes=''):
    p, lo, hi = outcome.wilson(events, trials)
    row = {'name': name, 'scenario': sc, 'side': side, 'variant': variant, 'build_name': build, 'measure': measure, 'parameter': parameter,
           'parameter_value': float(value), 'seeds': len(seed_list), 'seed_list': '%d..%d' % (seed_list[0], seed_list[-1]) if seed_list else '',
           'trials': int(trials), 'events': int(events), 'rate': round(p, 6), 'ci_low': round(lo, 6), 'ci_high': round(hi, 6),
           'ci_method': 'Wilson score, 95 % (z = 1.96), pooled over the seeds', 'per_seed': per_seed, 'window_s': window_s,
           'wall_s': round(wall_s, 1), 'firmware_sha256': fw, 'harness_digest': harness_digest, 'repro_json': json.dumps(repro or {}, default=str),
           'ran_at': _now(), 'notes': notes}
    if residual is not None:
        rp, rlo, rhi = outcome.wilson(residual, trials)
        row.update(residual_events=int(residual), residual_rate=round(rp, 6), residual_ci_low=round(rlo, 6), residual_ci_high=round(rhi, 6))
    return row


def uart_ber(sink, bers=BERS, seeds=SEEDS, commands=COMMANDS, home=None, progress=None, sides=('before', 'after'), fault_row=True):
    """→ {(side, ber): row}. Writes ScenarioStatistic rows and the measured rate onto UartBitErrorFault uart-bit-error."""
    from firmwarefaults.custom import runner_sc1, fault_engines as fe
    sc = SC.find('uart-residual-frame-loss')
    body, _ = payloads.command_stream(commands)
    secs = round(0.1 + len(body) / TWIN_RX_BYTES_PER_S + 0.4, 2)
    stream = {'name': 'stats#1', 'scenario': sc['name'], 'position': 1, 'kind': 'inject-bytes',
              'args_json': json.dumps({'cycle': 1600000, 'payload': 'command-stream', 'n': commands}), 'condition_json': '{}'}
    out = {}
    for side in sides:
        for ber in bers:
            t0 = time.time()
            sent = intact = applied = 0
            per, fw, build, ttff = [], '', '', []
            fe_ok = True
            for s in range(seeds):
                r = runner_sc1.run_side(sc, side, sink, seed=s, home=home, replace_steps=[stream], cache=True, write=False, seconds=secs,
                                        extra_steps=[{'kind': 'uart-ber', 'args_json': json.dumps({'p': ber})}])
                o = json.loads(r['observed_json'])
                rx = (o.get('harness') or {}).get('rx') or {}
                if int(rx.get('unit_bytes', 0)) != len(body):
                    fe_ok = False
                sent += o['sent']
                intact += o['ideal']
                applied += int(o['applied'] or 0)
                per.append('%d/%d/%d' % (o['applied'] or 0, o['ideal'], o['sent']))
                ttff.append(o.get('first_line_error_ms'))
                fw, build = r['firmware_sha256'], r['build_name']
                if progress:
                    progress('%s ber=%g seed=%d: applied %s / intact %s / sent %s' % (side, ber, s, o['applied'], o['ideal'], o['sent']))
            variant = sc['after_variant'] if side == 'after' else sc['before_variant']
            row = _stat('%s@%s@ber=%g' % (sc['name'], side, ber), sc['name'], side, variant, build,
                        'event = a command SENT but not APPLIED by the firmware (trials = commands sent); residual = a command the line delivered '
                        'INTACT (an ideal parser finds it in the received bytes) that the firmware did not apply',
                        'ber', ber, list(range(seeds)), sent, sent - applied, residual=intact - applied,
                        per_seed='applied/intact/sent per seed: ' + ', '.join(per), window_s=secs, wall_s=time.time() - t0, fw=fw,
                        harness_digest=fe.harness_digest(),
                        repro={'commands_per_run': commands, 'stream_sha256': harness.hashlib.sha256(body).hexdigest(), 'ber': ber,
                               'seeds': '0..%d' % (seeds - 1), 'how_to_rerun': 'pol faults stats uart-residual-frame-loss --seeds %d' % seeds},
                        notes=('line loss (sent − intact) = %d; firmware residual (intact − applied) = %d; intact = an offline greedy scan of '
                               'the delivered bytes (payloads.ideal_frames, max payload 93 like the board); each stream ends with %d idle zero '
                               'bytes so no candidate is left waiting at the end; %s' % (
                            sent - intact, intact - applied, payloads.FLUSH_TAIL, 'every byte of every stream was fed' if fe_ok else
                            'WARNING: some streams were not fed completely in the window')))
            row['events_per_1000'] = round(1000.0 * (sent - applied) / sent, 3) if sent else 0.0
            sink.upsert('ScenarioStatistic', row)
            row['_ttff_ms'] = ttff          # sc-2: per seed, the first byte the line damaged (None = none in the window)
            out[(side, ber)] = row
    if fault_row and any(side == 'before' for side, _ in out):
        _ber_fault_row(sink, out)
    return out


def _ber_fault_row(sink, out):
    from firmwarefaults.custom.fault_rows import by_class
    seed_row = next(r for r in by_class()['UartBitErrorFault'] if r['name'] == 'uart-bit-error')
    cur = sink.get('UartBitErrorFault', 'uart-bit-error')
    row = dict(cur) if isinstance(cur, dict) else dict(seed_row)
    parts = []
    for (side, ber), r in sorted(out.items(), key=lambda kv: (kv[0][0] != 'before', -kv[0][1])):
        parts.append('%s BER %g: %d of %d commands lost = %.2f %% [%.2f, %.2f] (residual %d = %.3f %% [%.3f, %.3f])' % (
            side, ber, r['events'], r['trials'], 100 * r['rate'], 100 * r['ci_low'], 100 * r['ci_high'], r.get('residual_events', 0),
            100 * r.get('residual_rate', 0), 100 * r.get('residual_ci_low', 0), 100 * r.get('residual_ci_high', 0)))
    worst = max((r for (side, _), r in out.items() if side == 'before'), key=lambda r: r['parameter_value'])
    row.update(name='uart-bit-error', ber=worst['parameter_value'], rate=worst['rate'],
               rate_unit='commands lost per command sent (25-byte frames, back to back) at the BER in `ber`',
               rate_source='measured (sc-1 statistics tier, simavr twin, %d seeds per BER, Wilson 95 %%): %s. The BER itself stays unverified '
                           'for the real UNO link (no cited figure); these are rates GIVEN a BER.' % (worst['seeds'], '; '.join(parts)))
    sink.upsert('UartBitErrorFault', row)
    return row


def _carries_from_retlog(text, pc2):
    ticks = carries = tears = vul = 0
    first = None
    classes = {}
    for line in text.splitlines():
        parts = line.split()
        if len(parts) != 3:
            continue
        pc, w = int(parts[1], 16), int(parts[2])
        ticks += 1
        hit = pc == pc2
        vul += hit
        if (w & 0xFF) == 0xFF:
            carries += 1
            tears += hit
            if hit and first is None:
                first = int(parts[0])
        classes.setdefault(w % 100, [0, 0])
        classes[w % 100][0] += 1
        classes[w % 100][1] += hit
    return {'ticks': ticks, 'carries': carries, 'tears': tears, 'vulnerable_ticks': vul, 'classes': classes, 'first_tear_cycle': first}


def _tear_build(variant, home):
    from firmwarefaults.custom import runner
    b = runner.prepare_build(variant, home, cache=True)
    loads = disasm.lds_sequence(b['dis'], 'hal_millis', 'g_ms')
    if len(loads) < 2:
        raise runner.ScenarioRefused('build %s has no split read of g_ms to measure' % variant)
    return b, loads[1]['pc']


def tear_run(b, pc2, variant, seed, noise, seconds):
    """One phase-sweep run: every tick's return PC logged (--ret-log 7) → ticks, carries, tears (a carry tick returning to the
    2nd lds), the first tear's cycle, the frames' backwards drops as the cross-check."""
    from firmwarefaults.custom import runner
    extra = [{'kind': 'ret-log', 'args_json': json.dumps({'vec': 7, 'file': 'retlog.txt'})}]
    if noise:
        extra.append({'kind': 'rx-noise', 'args_json': json.dumps({'rate': noise})})
    argv, files, meta = harness.render_sc1([], b['nm'], seconds, seed, {'watch': [('g_ms', 4)]}, variant, extra_steps=extra)
    h = harness.run_files(argv, b['hex'], files)
    if not h['ok']:
        raise runner.ScenarioRefused('the twin failed: %s' % (h['stderr'] or h['stdout'])[-400:])
    c = _carries_from_retlog(h['files'].get('retlog.txt', b'').decode(), pc2)
    ups, _ = runner.decode_frames(h['uart'])
    c['frames_backwards'] = len(outcome.backwards(ups))
    c['torn_last_frame'] = int(len(ups) >= 2 and ups[-1] - ups[-2] > 200)
    c['noise_bytes'] = (h['final'].get('rx') or {}).get('noise_bytes', 0)
    c['wall_s'] = h['final'].get('wall_s')
    c['firmware_sha256'] = b['row'].get('artifact_sha256', '')
    return c


def tear_sweep_after(sink, seeds=SEEDS, noise_rate=NOISE_RATE, seconds=10.0, home=None, progress=None):
    """sc-2: the technique's RESIDUAL for scenario 1 — the same seeds of asynchronous traffic on the AFTER build (atomic read):
    a tick can never return to the 2nd lds while ATOMIC_BLOCK masks it, and the frames must never go backwards."""
    from firmwarefaults.custom import fault_engines as fe
    sc = SC.find('torn-millis-read')
    b, pc2 = _tear_build(sc['after_variant'], home)
    per, carries, tears, back, ticks, t1, firsts = [], 0, 0, 0, 0, time.time(), []
    for s in range(seeds):
        c = tear_run(b, pc2, sc['after_variant'], s, noise_rate, seconds)
        carries += c['carries']; tears += c['tears']; back += c['frames_backwards'] + c['torn_last_frame']; ticks += c['ticks']
        per.append('%d/%d' % (c['tears'], c['carries']))
        firsts.append(c['first_tear_cycle'])
        if progress:
            progress('after seed %d: %d tear(s) in %d carries (frames backwards %d)' % (s, c['tears'], c['carries'], c['frames_backwards']))
    r = _stat('%s@after@rx-noise=%g' % (sc['name'], noise_rate), sc['name'], 'after', sc['after_variant'], b['row']['name'],
              'event = a byte-0 carry of g_ms whose tick ISR returned to the 2nd lds (hal_millis+0x8 in the atomic build) — the '
              'technique\'s residual; trials = carries', 'rx_noise_rate', noise_rate, list(range(seeds)), carries, tears,
              per_seed='tears/carries per seed: ' + ', '.join(per), window_s=seconds, wall_s=time.time() - t1,
              fw=b['row'].get('artifact_sha256', ''), harness_digest=fe.harness_digest(),
              repro={'seeds': '0..%d' % (seeds - 1), 'noise_rate': noise_rate, 'seconds': seconds, 'how_to_rerun': 'pol faults campaign run torn-read-phase'},
              notes='cross-check: %d backwards / torn-final frames over %d ticks (must be 0 with the atomic read)' % (back, ticks))
    sink.upsert('ScenarioStatistic', r)
    r['_firsts'] = firsts
    r['_frames_backwards'] = back
    return r


def tear_phase_sweep(sink, seeds=SEEDS, noise_rate=NOISE_RATE, seconds=10.0, home=None, progress=None):
    """→ {'natural': {...}, 'sweep': row}. Writes two ScenarioStatistic rows and the measured per-carry probability onto the
    TornReadFault row."""
    from firmwarefaults.custom import fault_engines as fe
    sc = SC.find('torn-millis-read')
    b, pc2 = _tear_build(sc['before_variant'], home)

    def one(seed, noise):
        return tear_run(b, pc2, sc['before_variant'], seed, noise, seconds)

    t0 = time.time()
    nat = one(0, 0)
    carry_classes = {k for k in range(100) if any((256 * j - 1) % 100 == k for j in range(1, 200))}
    in_cls = [v for k, v in nat['classes'].items() if k in carry_classes]
    nat['class_ticks'] = sum(v[0] for v in in_cls)
    nat['class_vulnerable'] = sum(v[1] for v in in_cls)
    p_nat, lo_n, hi_n = outcome.wilson(nat['vulnerable_ticks'], nat['ticks'])
    nat['p_zero_given_exposure'] = round((1 - p_nat) ** nat['carries'], 3)
    r_nat = _stat('%s@natural@ret-log' % sc['name'], sc['name'], 'natural', sc['before_variant'], b['row']['name'],
                  'event = a tick (TIMER2_COMPA) whose ISR returned to the 2nd lds of g_ms (0x%04x = %s), over EVERY tick of the run — the '
                  'exposure; the carries alone: %d tears in %d' % (pc2, disasm.symbolize(b['nm'], pc2), nat['tears'], nat['carries']),
                  'rx_noise_rate', 0.0, [0], nat['ticks'], nat['vulnerable_ticks'], per_seed='seed 0 (deterministic: no stimulus drawn)',
                  window_s=seconds, wall_s=time.time() - t0, fw=b['row'].get('artifact_sha256', ''), harness_digest=fe.harness_digest(),
                  notes=('No phase lock: the vulnerable PC takes %d of %d ticks (%.2f %%) overall and %d of %d (%.2f %%) inside the carries\' own '
                         'residue classes (g_ms mod 100), yet 0 of the %d carries landed there: P(0 | %.2f %%) = %.2f — the seeded sweep row says '
                         'whether the carries are exposed like an average tick') % (nat['vulnerable_ticks'], nat['ticks'], 100 * p_nat, nat['class_vulnerable'],
                                                                nat['class_ticks'], 100.0 * nat['class_vulnerable'] / max(1, nat['class_ticks']),
                                                                nat['carries'], 100 * p_nat, nat['p_zero_given_exposure']))
    sink.upsert('ScenarioStatistic', r_nat)
    per, carries, tears, back, vul, ticks, tail, firsts = [], 0, 0, 0, 0, 0, 0, []
    t1 = time.time()
    for s in range(seeds):
        c = one(s, noise_rate)
        carries += c['carries']
        tears += c['tears']
        back += c['frames_backwards']
        tail += c['torn_last_frame']
        vul += c['vulnerable_ticks']
        ticks += c['ticks']
        per.append('%d/%d' % (c['tears'], c['carries']))
        firsts.append(c['first_tear_cycle'])
        if progress:
            progress('seed %d: %d tear(s) in %d carries (frames backwards %d, %d noise bytes)' % (s, c['tears'], c['carries'], c['frames_backwards'], c['noise_bytes']))
    r = _stat('%s@before@rx-noise=%g' % (sc['name'], noise_rate), sc['name'], 'before', sc['before_variant'], b['row']['name'],
              'event = a byte-0 carry of g_ms whose tick ISR returned to the 2nd lds (a torn read); trials = carries; asynchronous RX bytes '
              '(0x00, exponential gaps at %g/s from the seed) move the loop phase against the tick' % noise_rate,
              'rx_noise_rate', noise_rate, list(range(seeds)), carries, tears, per_seed='tears/carries per seed: ' + ', '.join(per),
              window_s=seconds, wall_s=time.time() - t1, fw=b['row'].get('artifact_sha256', ''), harness_digest=fe.harness_digest(),
              repro={'seeds': '0..%d' % (seeds - 1), 'noise_rate': noise_rate, 'seconds': seconds,
                     'how_to_rerun': 'pol faults stats torn-millis-read --seeds %d' % seeds},
              notes='cross-check against the frames: %d backwards drop(s) + %d torn final frame(s) (a tear at the last carry, 9983 ms: the frame '
                    'that would go backwards is due after the window) = %d for the %d tears counted from the return PCs; all ticks: %d of %d '
                    '(%.2f %%) landed on the 2nd lds' % (back, tail, back + tail, tears, vul, ticks, 100.0 * vul / max(1, ticks)))
    sink.upsert('ScenarioStatistic', r)
    r['_firsts'] = firsts
    _tear_fault_row(sink, nat, r, p_nat, pc2, b)
    return {'natural': nat, 'natural_row': r_nat, 'sweep': r, 'frames_backwards': back, 'torn_final_frames': tail}


def verdict(r, exposure):
    """Does the seeded per-carry rate agree with the every-tick exposure? (inside the Wilson interval = consistent with chance)"""
    if r['ci_low'] <= exposure <= r['ci_high']:
        return ('the exposure lies INSIDE the sweep\'s interval: the per-carry tear rate is what a uniform phase predicts, so a run with no '
                'tear is chance, not structure.')
    return ('the exposure lies OUTSIDE the sweep\'s interval [%.2f, %.2f] %%: the carries are NOT exposed like an average tick — a structural '
            'bias remains to be explained.' % (100 * r['ci_low'], 100 * r['ci_high']))


def _tear_fault_row(sink, nat, r, p_nat, pc2, b):
    from firmwarefaults.custom.fault_rows import by_class
    seed_row = next(x for x in by_class()['TornReadFault'] if x['name'] == 'torn-read-g-ms')
    cur = sink.get('TornReadFault', 'torn-read-g-ms')
    row = dict(cur) if isinstance(cur, dict) else dict(seed_row)
    row.update(name='torn-read-g-ms', rate=r['rate'], rate_unit='torn reads per byte-0 carry of g_ms (one carry every 256 ms)',
               rate_source=('measured (sc-1 statistics tier, simavr twin, variant uno-sim-rig-torn): %d tears in %d carries over %d seeds of '
                            'asynchronous RX traffic = %.2f %% per carry, Wilson 95 %% [%.2f, %.2f] %%. The exposure from the natural run\'s '
                            'every tick: %.2f %% of ticks land on the 2nd lds (%s); %s sc-0\'s 0/39: P(0) = %.2f at that exposure and the '
                            'carries\' own residue classes are exposed %.2f %% — no phase lock. The plan\'s ≈ 13 %% counted three gaps.') % (
                   r['events'], r['trials'], r['seeds'], 100 * r['rate'], 100 * r['ci_low'], 100 * r['ci_high'], 100 * p_nat,
                   disasm.symbolize(b['nm'], pc2), verdict(r, p_nat), nat['p_zero_given_exposure'],
                   100.0 * nat['class_vulnerable'] / max(1, nat['class_ticks'])))
    sink.upsert('TornReadFault', row)
    return row
