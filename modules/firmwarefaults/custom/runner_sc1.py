"""
@module firmwarefaults.custom.runner_sc1

THE sc-1 RUNNER (FIRMWARE_SCENARIO_PLAN.md §3a, §4): one side of a single-board scenario whose observable is not scenario 1's
uptime — the telemetry that must not stop (S2), the press count (S3), the commands applied vs what the line delivered intact
(S4), the record read back after a reset mid-write (S5), frames coming back after a runaway (the watchdog, §4). The build,
the claim, the repro block and the rows go through runner.py's machinery; this file renders the sc-1 steps
(harness.render_sc1), reads the twin's logs and decides (outcome.decide_*).

    run_side(sc, side, sink, steps=None, seconds=None, seed=None, home=None, extra_steps=(), cache=False, write=True)
    run_pair(sc, sink, …) → [before, after] + the technique's measured cost on the AFTER run and the Technique row
    run_control(sc, sink, …) → S5's persistence control: the reset lands AFTER the write completed (EEPROM across avr_reset)
"""
import datetime
import json

from firmwarefaults.custom import disasm, harness, outcome, payloads
from firmwarefaults.custom import scenarios as SC
from firmwarefaults.custom.scenarios_sc1 import OBSERVE

KINDS = ('telemetry-continues', 'press-count', 'commands-applied', 'record-consistent', 'recovers-after-hang')
FREQ = 16000000.0
#: S5's control: the same steps, but the reset lands 100 ms after the command (the 4..6 byte writes take ≈ 3.4 ms each)
CONTROL_RESET_CYCLE = 6400000


def _ms(cycles):
    return cycles * 1000.0 / FREQ


def _fn(b, sym):
    if not sym or sym not in b['nm']:
        return None
    return b['nm'][sym]['addr'], disasm.ret_pc(b['dis'], sym)


def run_side(sc, side, sink, steps=None, seconds=None, seed=None, home=None, extra_steps=(), cache=False, write=True, replace_steps=None):
    from firmwarefaults.custom import runner as R
    steps = replace_steps if replace_steps is not None else SC.steps_of(sc['name'], steps)
    seed = int(sc.get('seed', 0) if seed is None else seed)
    variant = sc['after_variant'] if side == 'after' else sc['before_variant']
    technique = sc['technique'] if side == 'after' else ''
    why = SC.refusal(sc, steps)
    if why:
        raise R.ScenarioRefused(why)
    if not variant:
        raise R.ScenarioRefused('scenario %s has no %s variant' % (sc['name'], side.upper()))
    t0 = datetime.datetime.now()
    b = R.prepare_build(variant, home, cache=cache)
    run = R._base_run(sc, side, variant, b, seed, technique)
    if write and sink.get('MathClaim', R.claim_name(sc['name'], run['build_name'])) is None:
        sink.upsert('MathClaim', {'name': R.claim_name(sc['name'], run['build_name']), 'kind': 'safe-under-scenario', 'proof_status': 'conjectured',
                                  'checker': 'sim', 'statement_json': '{}', 'description': 'stated by the runner before the run'})
    if b['row']['state'] != 'built':
        raise R.ScenarioRefused('variant %s did not build: %s' % (variant, b['row'].get('notes', '')[-400:]))
    obs = OBSERVE.get(sc['name'], {})
    secs = float(seconds if seconds is not None else sc['run_seconds'])
    argv, files, meta = harness.render_sc1(steps, b['nm'], secs, seed, obs, variant, extra_steps=extra_steps, fn=_fn(b, obs.get('cost_fn')))
    if meta['missing']:
        run.update(outcome='inapplicable', verdict_words='the scenario does not exist in this build: %s' % '; '.join(meta['missing']))
        return R._finish(sc, run, sink, b, t0, {}) if write else run
    h = harness.run_files(argv, b['hex'], files)
    if not h['ok']:
        raise R.ScenarioRefused('the twin failed (%s %s): %s' % (h['how'], h['where'], (h['stderr'] or h['stdout'])[-600:]))
    fin = h['final']
    watches = {w['name']: int(w['final']) for w in fin.get('watches', [])}
    end_ms = _ms(int(fin.get('cycles', 0)))
    frames = outcome.frames_from_tx_log(h['tx'])
    tel = [t for t, mt, _ in frames if mt == 1]
    rx = fin.get('rx') or {}
    kind = sc['observable_kind']
    ev, extra_obs = {}, {}
    if kind == 'telemetry-continues':
        d = outcome.decide_telemetry(frames, end_ms, int(obs.get('gap_limit_ms', 250)), bool(rx.get('dropped_units')), watches.get('g_ack_state'))
        drop = next((u for u in rx.get('unit_starts', []) if u.get('dropped')), None)
        if drop:
            ev = {'cycle': drop['cycle'], 'what': 'ack #%d dropped on the host→board line' % drop['idx']}
        extra_obs = {'requests_ms': [round(t, 3) for t, mt, _ in frames if mt == 0x7F], 'ack_state': watches.get('g_ack_state'),
                     'ack_tries': watches.get('g_ack_tries')}
    elif kind == 'press-count':
        d = outcome.decide_presses(watches.get('g_presses'), int(obs.get('expected_presses', 1)))
        evs = fin.get('events') or []
        if evs:
            ev = {'cycle': evs[0]['cycle'], 'what': 'INT0 raised %d time(s) at cycles %s' % (len(evs), ', '.join(str(e['cycle']) for e in evs)),
                  'landed_pc': evs[1]['landed_pc'] if len(evs) > 1 and evs[1].get('landed') else 0,
                  'landed_cycle': evs[1]['landed_cycle'] if len(evs) > 1 else 0}
    elif kind == 'commands-applied':
        delivered = payloads.delivered_from_rx_log(h['rx'])
        ideal = payloads.ideal_commands(delivered)
        d = outcome.decide_commands(watches.get('echoes'), ideal, meta['sent'])
        starts = rx.get('unit_starts') or []
        if starts:
            ev = {'cycle': starts[0]['cycle'], 'what': 'host→board bytes from cycle %d (%d bytes)' % (starts[0]['cycle'], starts[0]['len'])}
        extra_obs = {'sent': meta['sent'], 'ideal': ideal, 'applied': watches.get('echoes'), 'framing_errors_counted': watches.get('g_uart_fe'),
                     'overruns_counted': watches.get('g_uart_dor'), 'ring_drops_counted': watches.get('g_rx_dropped'),
                     'line': {k: rx.get(k) for k in ('ber', 'bits_flipped', 'bytes_corrupted', 'framing_errors', 'bytes_lost', 'bytes_fed')}}
    elif kind == 'record-consistent':
        ra = fin.get('reset_at') or {}
        d = outcome.decide_record(watches.get('g_rec_boot'), watches.get('g_rec_valid'), obs['old'], obs['new'], ra.get('done'))
        if ra.get('done'):
            ev = {'cycle': ra['cycle'], 'pc': ra['pc'], 'what': 'avr_reset at %s (no BOD model in simavr 1.6 — the droop is approximated by a reset)'
                  % ('entry %d of eeprom_write_byte' % ra['nth'] if ra.get('by') == 'pc' else 'cycle %d' % ra['cycle'])}
        extra_obs = {'record_boot': watches.get('g_rec_boot'), 'record_valid': watches.get('g_rec_valid'), 'eeprom': fin.get('eeprom'),
                     'old': obs['old'], 'new': obs['new'], 'reset_note': ra.get('note')}
    elif kind == 'recovers-after-hang':
        ja = fin.get('jump_at') or {}
        d = outcome.decide_recovery(tel, _ms(ja['cycle']) if ja.get('done') else None, end_ms, (fin.get('resets') or {}).get('list', []))
        if ja.get('done'):
            ev = {'cycle': ja['cycle'], 'pc': ja['to_pc'], 'from_pc': ja['from_pc'], 'what': 'PC set to _exit (cli; rjmp .)'}
        extra_obs = {'resets': fin.get('resets')}
    else:
        raise R.ScenarioRefused('observable %r is not an sc-1 kind' % kind)
    lat = fin.get('isr_latency') or {}
    lat_v, lat_max = max(((int(v), x['max']) for v, x in lat.items()), key=lambda t: t[1], default=(0, 0))
    isc = fin.get('isr_cycles') or {}
    cv = obs.get('cost_isr')
    if cv is not None and str(cv) in isc:
        isr_v, isr_max = int(cv), int(isc[str(cv)]['max'])
    else:
        isr_v, isr_max = max(((int(v), x['max']) for v, x in isc.items()), key=lambda t: t[1], default=(0, 0))
    run.update(outcome=d['outcome'], verdict_words=d['words'], observable_value=d.get('value', ''), frames_seen=len(tel),
               uptime_sequence='', uart_sha256=R.sha(h['uart']), sim_cycles=int(fin.get('cycles', 0)), sim_seconds=secs,
               wall_s=round(float(fin.get('wall_s', 0.0)), 4), stack_high_water=int(fin.get('stack_high_water_sp', 0)),
               stack_high_water_paint=int((fin.get('stack_fill') or {}).get('high_water', 0)), isr_latency_max_cycles=int(lat_max),
               isr_latency_vector=lat_v, isr_cycles_max=isr_max, isr_cycles_vector=isr_v,
               fn_cycles_min=int((fin.get('fn_cycles') or {}).get('min', 0)), reset_count=int((fin.get('resets') or {}).get('n', 0)))
    if ev:
        run.update(fault_cycle=int(ev.get('cycle', 0)), fault_pc='0x%04x' % ev['pc'] if ev.get('pc') else '',
                   fault_symbol=disasm.symbolize(b['nm'], ev['pc']) if ev.get('pc') else ev.get('what', '')[:120],
                   landed_pc='0x%04x' % ev['landed_pc'] if ev.get('landed_pc') else ('0x%04x' % ev['from_pc'] if ev.get('from_pc') else ''),
                   landed_symbol=disasm.symbolize(b['nm'], ev['landed_pc']) if ev.get('landed_pc') else (
                       'runaway from %s' % disasm.symbolize(b['nm'], ev['from_pc']) if ev.get('from_pc') else ''),
                   landed_cycle=int(ev.get('landed_cycle', 0)))
    obs_json = {'decided': d, 'event': ev, 'watches': watches, 'frames': {'telemetry': len(tel), 'all': len(frames),
                                                                       'first_ms': [round(t, 2) for t in tel[:3]], 'last_ms': [round(t, 2) for t in tel[-3:]]},
                'harness': {k: fin.get(k) for k in ('events', 'resets', 'reset_at', 'jump_at', 'rx', 'responder', 'eeprom', 'isr_latency', 'isr_cycles',
                                                     'fn_cycles', 'stack_fill', 'min_sp', 'watches')},
                'host': {'sent': meta['sent'], 'bytes_sha256': meta['host_bytes_sha256'], 'resolved': meta['resolved']},
                'stack_static': b.get('stack_static'), 'twin': {'how': h['how'], 'where': h['where'], 'cost': h['cost']}}
    obs_json.update(extra_obs)
    run['observed_json'] = json.dumps(obs_json, default=str)
    rep = R._repro(sc, steps, b, argv, seed, h, run)
    rep['inputs'] += [{'label': 'host→board bytes #%d' % i, 'sha256': s} for i, s in enumerate(meta['host_bytes_sha256'])]
    rep['generated_files'] += [{'path': harness.TXLOG, 'sha256': R.sha(h['tx'])}] + ([{'path': harness.RXLOG, 'sha256': R.sha(h['rx'])}] if h['rx'] else [])
    rep['seeds']['why'] = ('simavr free-running from reset is deterministic on identical inputs; --seed drives the --uart-ber / --rx-noise draws '
                           '(splitmix64, separate streams) and nothing else')
    rep['seeds']['deterministic'] = not any(s['kind'] in ('uart-ber', 'rx-noise') for s in list(steps) + list(extra_steps))
    run['repro_json'] = json.dumps(rep, default=str)
    if not write:
        return run
    return R._finish(sc, run, sink, b, t0, {})


def pair_cost(sc, before, after, sink):
    """The technique's cost, measured AFTER − BEFORE on the same scenario + seed: flash, RAM, the pricing function's cycles
    (or the ISR's cycles), the worst ISR latency, the stack high-water."""
    obs = OBSERVE.get(sc['name'], {})
    flash = (after['size_text'] + after['size_data']) - (before['size_text'] + before['size_data'])
    ram = (after['size_data'] + after['size_bss']) - (before['size_data'] + before['size_bss'])
    if obs.get('cost_isr') is not None:
        cyc, what = after['isr_cycles_max'] - before['isr_cycles_max'], 'INT0 ISR cycles (max) AFTER − BEFORE'
    elif obs.get('cost_fn'):
        cyc, what = after['fn_cycles_min'] - before['fn_cycles_min'], '%s cycles per pass (min; absent BEFORE = 0)' % obs['cost_fn']
    else:
        cyc, what = 0, 'not timed: %s' % obs.get('cost_what', '')
    lat = after['isr_latency_max_cycles'] - before['isr_latency_max_cycles']
    cd = {'pair': before['name'], 'flash_bytes': flash, 'ram_bytes': ram, 'cycles': cyc, 'cycles_what': what, 'isr_latency_max_cycles': lat,
          'stack_high_water_bytes': after['stack_high_water'] - before['stack_high_water'], 'cost_what': obs.get('cost_what', ''),
          'how': 'avr-size .text+.data / .data+.bss deltas; --fn-cycles or --isr-latency isr_cycles; --isr-latency max (natural interrupts); --sp-watch'}
    after.update(cost_delta_json=json.dumps(cd), cost_flash_bytes_delta=flash, cost_cycles_delta=cyc, latency_delta_cycles=lat)
    before.update(cost_delta_json=json.dumps({'pair': after['name'], 'note': 'the AFTER run carries the measured delta'}))
    sink.upsert('ScenarioRun', after)
    sink.upsert('ScenarioRun', before)
    if sc.get('technique'):
        from firmwarefaults.custom.taxonomy import techniques_by_name
        cur = sink.get('Technique', sc['technique'])
        t = dict(cur) if isinstance(cur, dict) else dict(techniques_by_name().get(sc['technique'], {'name': sc['technique']})) if cur is None else {}
        t.update(name=sc['technique'], measured_cost_bytes=flash, measured_ram_bytes=ram, measured_cost_cycles=cyc, measured_latency_delta_cycles=lat,
                 measured_cost_what=what, measured_by_run=after['name'])
        sink.upsert('Technique', t)
    return cd


def run_pair(sc, sink, seconds=None, seed=None, home=None, steps=None):
    b = run_side(sc, 'before', sink, steps, seconds, seed, home)
    a = run_side(sc, 'after', sink, steps, seconds, seed, home)
    if b['outcome'] != 'inapplicable' and a['outcome'] != 'inapplicable':
        pair_cost(sc, b, a, sink)
    return [b, a]


def run_control(sc, sink, side='before', seed=None, home=None, steps=None):
    """S5's control: the reset lands AFTER the write completed — the record read at boot must be the NEW one, which proves
    the twin's EEPROM survives avr_reset (sc-0 had it as assumed)."""
    if sc['name'] != 'brownout-mid-eeprom-write':
        from firmwarefaults.custom.runner import ScenarioRefused
        raise ScenarioRefused('only brownout-mid-eeprom-write has a control run (the EEPROM persistence check)')
    st = [dict(s) for s in SC.steps_of(sc['name'], steps)]
    for s in st:
        if s['kind'] == 'reset-at':
            s['args_json'] = json.dumps({'cycle': CONTROL_RESET_CYCLE})
            s['notes'] = 'control: the reset lands 100 ms after the command — the write has completed'
    r = run_side(sc, side, sink, seed=seed, home=home, replace_steps=st, write=False)
    persisted = (json.loads(r['observed_json']).get('record_boot') == OBSERVE[sc['name']]['new'])
    r.update(side='control', name=r['name'].replace('@%s@' % side, '@control-%s@' % side),
             verdict_words=('EEPROM PERSISTS across avr_reset on the twin: the write completed, the core was reset at cycle %d, and the record '
                            'read at boot is the new value — %s' % (CONTROL_RESET_CYCLE, r['verdict_words'])) if persisted else
             ('EEPROM did NOT persist across avr_reset: %s' % r['verdict_words']), claim='',
             notes='control run (not a claim): the persistence check sc-0 marked assumed')
    sink.upsert('ScenarioRun', r)
    return r, persisted
