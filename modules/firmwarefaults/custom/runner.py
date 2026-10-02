"""
@module firmwarefaults.custom.runner

THE SCENARIO RUNNER (FIRMWARE_SCENARIO_PLAN.md §3, §9 sc-0): a Scenario row + a FirmwareBuild → harness flags → the
twin → the frames (board.custom.packet_ref, the independent Python reference parser) and the trace (pyvcd, engine side)
→ the outcome against the scenario's observable → a ScenarioRun row (+ its ScenarioTraceCycle rows, the MathClaim, a
ProofRun) → for a pair, the technique's measured cost (bytes from avr-size, cycles from --fn-cycles, the ISR-latency
delta from --isr-latency) written onto the AFTER run and the Technique row; for a natural run, the fault's measured rate.

    run_scenario(name, side='both'|'before'|'after'|'natural', sink=LocalSink()|ManagerSink(manager), seconds=None, seed=None)

Builds are generated OFFLINE from the pinned contract (never from a server's live exposure), so a run's firmware sha does
not depend on which server asked — the reproducibility rule. CLI: custom/faults_cli.py (`pol faults …`).
"""
import datetime
import hashlib
import json
import os

from firmwarefaults.custom import disasm, harness, outcome, sink as S, stack_static, fault_engines as fe
from firmwarefaults.custom import scenarios as SC
from firmwarefaults.custom.claim_bridge import write as write_claim, claim_name

SIM_VERSION = 'libsimavr 1.6 (Debian libsimavr2 1.6+dfsg-3+b3, pinned by the prf-board-engines image id in harness_digest)'
NATURAL_SECONDS = 10.0


class ScenarioRefused(RuntimeError):
    pass


def sha(b):
    return hashlib.sha256(b if isinstance(b, bytes) else b.encode()).hexdigest()


def _now():
    return datetime.datetime.now().isoformat(timespec='seconds')


# ------------------------------------------------------------------ builds
def prepare_build(variant, home=None):
    """gen + build ONE variant (offline, pinned contract) → the build record, its bytes, the parsed ELF, the static stack."""
    from board.custom import gen, build
    home = home or S.home()
    work = os.path.join(home, 'builds', variant)
    row = gen.gen('uno', None, work, variant=variant, variant_rows=SC.scenario_variants())
    row = build.build('uno', work)
    out = {'row': row, 'work': work}
    if row['state'] != 'built':
        return out
    elf = open(os.path.join(work, 'out', 'firmware.elf'), 'rb').read()
    hexb = open(row['hex_path'], 'rb').read()
    od = fe.run('avr-objdump', ['-d', 'firmware.elf'], {'firmware.elf': elf}, timeout=120)
    nmr = fe.run('avr-nm', ['-n', 'firmware.elf'], {'firmware.elf': elf}, timeout=120)
    if not od.get('ok') or not nmr.get('ok'):
        raise ScenarioRefused('disassembly failed: %s' % ((od.get('stderr') or nmr.get('stderr') or '')[-400:]))
    project = row['project_dir']
    files = {fn: open(os.path.join(project, fn), 'rb').read() for fn in sorted(os.listdir(project)) if fn.endswith(('.c', '.h'))}
    su = fe.run('avr-gcc', build.CFLAGS + ['-fstack-usage', '-fcallgraph-info=su', '-c'] + sorted(f for f in files if f.endswith('.c')), files, timeout=180)
    cis = [v.decode('utf-8', 'replace') for k, v in (su.get('files') or {}).items() if k.endswith('.ci')]
    st = stack_static.peak(*stack_static.parse_ci(cis)) if cis else {'ok': False, 'why': 'no .ci output: %s' % (su.get('stderr') or '')[-200:]}
    out.update(elf=elf, hex=hexb, dis=disasm.parse_objdump(od['stdout']), nm=disasm.parse_nm(nmr['stdout']), stack_static=st)
    return out


# ------------------------------------------------------------------ frames + trace
def decode_frames(uart):
    from board.custom import gen, packet_ref
    from board.custom.compat import wire_spec
    fmap = gen.pinned_contract('SimRigState')[0]['field_map']
    spec = wire_spec(None, 'SimRigState', fmap)
    p = packet_ref.StreamParser()
    frames = [packet_ref.decode_any(fmap, payload, ver, spec) for mt, dev, seq, payload, ver in p.feed(uart) if mt == 1]
    return [int(f.get('uptime_ms', 0)) for f in frames], p


def _u32(s):
    return s.get('r22', 0) | s.get('r23', 0) << 8 | s.get('r24', 0) << 16 | s.get('r25', 0) << 24


def trace_rows(run_name, samples, b, ev, loads, ret_pc, watch_name, expected):
    """Annotate the pyvcd samples → ScenarioTraceCycle dicts + the value hal_millis returned after the event."""
    rows, returned = [], None
    load_pc = {ld['pc']: k + 1 for k, ld in enumerate(loads)}
    c0 = ev.get('cycle', 0)
    for i, s in enumerate(samples):
        pc, vec = int(s.get('pc', 0)), int(s.get('isr_vector', 0))
        notes = []
        if pc in load_pc and not vec:
            notes.append('lds %d of %s (byte %d)' % (load_pc[pc], watch_name, load_pc[pc] - 1))
        if s.get('forced') and pc == ev.get('pc') and not vec:
            notes.append('FORCED: vector %d raised here (SREG.I=%d)' % (ev.get('vec', 0), s.get('sreg_i', 0)))
        if pc == ev.get('vec', -1) * 4:
            notes.append('ISR entered (vector %d), return address %s' % (ev.get('vec'), '0x%x' % ev.get('landed_pc', 0)))
        if ret_pc is not None and pc == ret_pc and not vec and s['cycle'] >= c0:
            v = _u32(s)
            if returned is None:
                returned = v
            notes.append('hal_millis returns 0x%08X = %d%s' % (v, v, ' — TORN (an atomic read gives %d or %d)' % (expected, expected + 1)
                                                                if expected >= 0 and v not in (expected, expected + 1) else ''))
        rows.append({'name': '%s#%03d' % (run_name, i), 'run': run_name, 'idx': i, 'cycle': int(s['cycle']), 'rel_cycle': int(s['cycle']) - c0,
                     'pc': '0x%04x' % pc, 'symbol': disasm.symbolize(b['nm'], pc), 'instruction': disasm.instruction_at(b['dis'], pc),
                     'sp': int(s.get('sp', 0)), 'sreg_i': int(s.get('sreg_i', 0)), 'isr_vector': vec,
                     'r22': '0x%02x' % s.get('r22', 0), 'r23': '0x%02x' % s.get('r23', 0), 'r24': '0x%02x' % s.get('r24', 0), 'r25': '0x%02x' % s.get('r25', 0),
                     'watch': '0x%08x' % int(s.get(watch_name, 0) or 0), 'forced': int(s.get('forced', 0) or 0), 'note': '; '.join(notes)})
    return rows, returned


# ------------------------------------------------------------------ one side
def _base_run(sc, side, variant, b, seed, technique):
    row = b['row']
    return {'name': '%s@%s@%s@seed%d' % (sc['name'], side, row['name'], seed), 'scenario': sc['name'], 'side': side, 'variant': variant,
            'build_name': row['name'], 'technique_applied': technique, 'outcome': '', 'verdict_words': '', 'fault_cycle': 0, 'fault_pc': '',
            'fault_symbol': '', 'landed_pc': '', 'landed_symbol': '', 'landed_cycle': 0, 'torn_value': -1, 'expected_value': -1, 'frames_seen': 0,
            'frames_backwards': 0, 'bad_crc': 0, 'uptime_sequence': '', 'observed_json': '{}', 'trace_sha256': '', 'trace_samples': 0,
            'uart_sha256': '', 'firmware_sha256': row.get('artifact_sha256', ''), 'elf_sha256': sha(b['elf']) if b.get('elf') else '',
            'harness_digest': fe.harness_digest(), 'simulator_version': SIM_VERSION, 'seed': seed, 'sim_cycles': 0, 'sim_seconds': 0.0, 'wall_s': 0.0,
            'stack_high_water': 0, 'stack_high_water_paint': 0, 'stack_static_peak': int((b.get('stack_static') or {}).get('peak_bytes') or 0),
            'isr_latency_max_cycles': 0, 'isr_latency_vector': 0, 'fn_cycles_min': 0, 'size_text': row.get('size_text', 0),
            'size_data': row.get('size_data', 0), 'size_bss': row.get('size_bss', 0), 'cost_delta_json': '{}', 'cost_flash_bytes_delta': 0,
            'cost_cycles_delta': 0, 'latency_delta_cycles': 0, 'claim': '', 'repro_json': '{}', 'ran_at': _now(), 'notes': ''}


def run_side(sc, side, sink, steps=None, seconds=None, seed=None, home=None):
    steps = SC.steps_of(sc['name'], steps)
    seed = int(sc.get('seed', 0) if seed is None else seed)
    variant = sc['after_variant'] if side == 'after' else sc['before_variant']
    technique = sc['technique'] if side == 'after' else ''
    if side == 'after' and not variant:
        raise ScenarioRefused('scenario %s has no AFTER build (its technique is %s)' % (sc['name'], sc['technique']))
    bad = [s['kind'] for s in steps if s['kind'] not in SC.FORCIBLE_KINDS]
    if bad and side != 'natural':
        raise ScenarioRefused('scenario %s is not-yet-forcible: step kind(s) %s — %s' % (sc['name'], ', '.join(bad), '; '.join(SC.STEP_KINDS[k][1] for k in bad)))
    t0 = datetime.datetime.now()
    b = prepare_build(variant, home)
    run = _base_run(sc, side, variant, b, seed, technique if sc['observable_kind'] != 'build-refused' else sc['technique'])
    if sink.get('MathClaim', claim_name(sc['name'], run['build_name'])) is None:   # stated before the run, so the run FLIPS it
        sink.upsert('MathClaim', {'name': claim_name(sc['name'], run['build_name']), 'kind': 'safe-under-scenario', 'proof_status': 'conjectured',
                                  'checker': 'sim', 'statement_json': '{}', 'description': 'stated by the runner before the run'})
    if sc['observable_kind'] == 'build-refused':
        d = outcome.decide_build_refused(b['row']['state'], b['row'].get('notes', ''))
        run.update(outcome=d['outcome'], verdict_words=d['words'], observed_json=json.dumps({'build_state': b['row']['state'], 'build_notes': b['row'].get('notes', '')[-600:]}),
                   notes='technique %s applied: the build is refused at compile time' % sc['technique'] if d['outcome'] == 'inapplicable' else '')
        return _finish(sc, run, sink, b, t0, {})
    if b['row']['state'] != 'built':
        raise ScenarioRefused('variant %s did not build: %s' % (variant, b['row'].get('notes', '')[-400:]))
    resolved = [(s, disasm.resolve_step(json.loads(s['args_json']), b['dis'], b['nm'])) for s in steps]
    missing = [r['why'] for _, r in resolved if not r['ok']]
    if missing and side != 'natural':
        run.update(outcome='inapplicable', verdict_words='the scenario does not exist in this build: %s' % '; '.join(missing))
        return _finish(sc, run, sink, b, t0, {})
    first = resolved[0][1] if resolved else {'loads': [], 'ret_pc': None}
    args0 = json.loads(steps[0]['args_json']) if steps else {}
    watch = (args0.get('of'), 4) if args0.get('of') else None
    fn = (b['nm'].get(args0.get('symbol'), {}).get('addr'), first.get('ret_pc')) if args0.get('symbol') else None
    secs = float(seconds if seconds is not None else (NATURAL_SECONDS if side == 'natural' else sc['run_seconds']))
    argv = harness.render(resolved, b['nm'], secs, seed, watch=watch, fn=fn, forcing=(side != 'natural'))
    h = harness.run(argv, b['hex'])
    if not h['ok']:
        raise ScenarioRefused('the twin failed (%s %s): %s' % (h['how'], h['where'], (h['stderr'] or h['stdout'])[-600:]))
    fin = h['final']
    ups, parser = decode_frames(h['uart'])
    ev = (fin.get('events') or [{}])[0] if side != 'natural' else {}
    if side == 'natural':
        nat = outcome.natural_rate(ups, (fin.get('watch') or {}).get('final', 0), int((fin.get('fn_cycles') or {}).get('n', 0)),
                                   int(fin.get('cycles', 0)), disasm.CYCLES['lds'])
        d = outcome.decide_uptime(ups, parser.bad_crc, None)
        d['words'] = ('natural run, %.1f s, no forcing: %d torn read(s) in %d byte-0 carries of %s = %.1f %% observed from reset; exposure if '
                      'the tick phase were uniform = %.2f %% per carry (2 cycles x %d hal_millis calls / %d cycles) — %s') % (
            secs, nat['tears'], nat['carries'], watch[0] if watch else 'the tick', 100.0 * nat['rate'], 100.0 * nat['exposure_per_carry'],
            nat['calls'], nat['cycles'], d['words'])
        run['observed_json'] = json.dumps({'natural': nat})
    else:
        d = outcome.decide_uptime(ups, parser.bad_crc, ev)
    lat = fin.get('isr_latency') or {}
    lat_v, lat_max = max(((int(v), x['max']) for v, x in lat.items()), key=lambda t: t[1], default=(0, 0))
    run.update(outcome=d['outcome'], verdict_words=d['words'], frames_seen=len(ups), frames_backwards=len(d['backwards']), bad_crc=parser.bad_crc,
               uptime_sequence=', '.join(str(u) for u in ups), uart_sha256=sha(h['uart']), sim_cycles=int(fin.get('cycles', 0)), sim_seconds=secs,
               wall_s=round(float(fin.get('wall_s', 0.0)), 4), stack_high_water=int(fin.get('stack_high_water_sp', 0)),
               stack_high_water_paint=int((fin.get('stack_fill') or {}).get('high_water', 0)), isr_latency_max_cycles=int(lat_max),
               isr_latency_vector=lat_v, fn_cycles_min=int((fin.get('fn_cycles') or {}).get('min', 0)), torn_value=d['torn_value'])
    obs = json.loads(run['observed_json'])
    obs.update({'harness': {k: fin.get(k) for k in ('events', 'pokes', 'min_sp', 'stack_fill', 'isr_latency', 'fn_cycles', 'watch', 'trace')},
                'frames': {'decoded': len(ups), 'bad_crc': parser.bad_crc, 'skipped_bytes': parser.skipped, 'backwards': d['backwards'][:8]},
                'stack_static': b.get('stack_static'), 'twin': {'how': h['how'], 'where': h['where'], 'cost': h['cost']}})
    trows = []
    if ev:
        run.update(fault_cycle=int(ev.get('cycle', 0)), fault_pc='0x%04x' % ev.get('pc', 0), fault_symbol=disasm.symbolize(b['nm'], ev.get('pc', 0)),
                   landed_pc='0x%04x' % ev.get('landed_pc', 0) if ev.get('landed') else '', landed_cycle=int(ev.get('landed_cycle', 0)),
                   landed_symbol=disasm.symbolize(b['nm'], ev.get('landed_pc', 0)) if ev.get('landed') else '',
                   expected_value=int(ev.get('watch_at_event', -1)))
        if h['vcd']:
            samples, vsha, reader, _ = harness.window(h['vcd'], ev.get('cycle', 0), before=8, after=44)
            trows, returned = trace_rows(run['name'], samples, b, ev, first.get('loads', []), first.get('ret_pc'), watch[0] if watch else 'watch',
                                         run['expected_value'])
            run.update(trace_sha256=sha(h['vcd']), trace_samples=int((fin.get('trace') or {}).get('samples', 0)))
            obs['trace_window'] = {'rows': len(trows), 'reader': reader, 'vcd_sha256_engine': vsha, 'returned_after_event': returned}
            if returned is not None:
                obs['returned_after_event'] = returned
    run['observed_json'] = json.dumps(obs, default=str)
    run['repro_json'] = json.dumps(_repro(sc, steps, b, argv, seed, h, run), default=str)
    return _finish(sc, run, sink, b, t0, {'trace_rows': trows})


def _repro(sc, steps, b, argv, seed, h, run):
    row = b['row']
    rep = json.loads(row.get('repro_json') or '{}')
    return {'inputs': [{'label': 'firmware.hex', 'sha256': run['firmware_sha256']}, {'label': 'firmware.elf', 'sha256': run['elf_sha256']},
                       {'label': 'scenario row', 'sha256': sha(json.dumps(sc, sort_keys=True))},
                       {'label': 'scenario steps', 'sha256': sha(json.dumps(steps, sort_keys=True))}] + rep.get('inputs', []),
            'tools': {'harness': run['harness_digest'], 'simulator': SIM_VERSION, 'build': rep.get('tools', {}),
                      'vcd_reader': 'pyvcd 0.5.0 (sha256-pinned in prf-board-engines)'},
            'knobs': {'variant': run['variant'], 'build_flags': (rep.get('knobs') or {}).get('build_flags'), 'harness_argv': argv},
            'seeds': {'seed': seed, 'deterministic': True, 'why': 'simavr free-running from reset is deterministic on identical inputs; the seed is '
                                                                    'recorded but nothing is drawn from it in sc-0'},
            'generated_files': [{'path': 'uart.bin', 'sha256': run['uart_sha256']}, {'path': 'trace.vcd', 'sha256': run['trace_sha256']}],
            'how_to_rerun': 'pol faults run %s --%s --seed %d' % (sc['name'], run['side'], seed), 'recorded_at': run['ran_at'],
            'cost': {'twin': h.get('cost')}, 'rule': 'every result carries the initial conditions and seeds that produced it (2026-09-26)'}


def _finish(sc, run, sink, b, t0, extra):
    run['claim'], after, before = write_claim(sink, run, sc)
    run['wall_total_s'] = round((datetime.datetime.now() - t0).total_seconds(), 2)
    sink.upsert('ScenarioRun', run)
    for tr in extra.get('trace_rows', []):
        sink.upsert('ScenarioTraceCycle', tr)
    run['_claim_flip'] = (before or 'conjectured', after)
    run['_trace_rows'] = extra.get('trace_rows', [])
    run['_stack_static'] = b.get('stack_static')
    return run


# ------------------------------------------------------------------ pairs + natural
def run_scenario(name, side='both', sink=None, seconds=None, seed=None, home=None, scenario_rows=None, step_rows=None):
    sink = sink if sink is not None else S.LocalSink()
    sc = SC.find(name, scenario_rows)
    if sc is None:
        raise ScenarioRefused('no scenario %r — `pol faults list`' % name)
    sides = {'both': ['before', 'after'], 'before': ['before'], 'after': ['after'], 'natural': ['natural']}.get(side)
    if sides is None:
        raise ScenarioRefused('side must be before | after | both | natural')
    if sc['observable_kind'] == 'build-refused':
        sides = ['before']
    runs = [run_side(sc, s, sink, step_rows, seconds, seed, home) for s in sides]
    if len(runs) == 2:
        pair_cost(sc, runs[0], runs[1], sink)
    if side == 'natural':
        natural_rate_row(sc, runs[0], sink)
    for r in runs:
        r['claim_status'] = _claim_status(sink, r['claim'])
    return {'scenario': sc, 'runs': runs, 'sink': sink}


def _claim_status(sink, name):
    c = sink.get('MathClaim', name)
    return (c.get('proof_status') if isinstance(c, dict) else getattr(c, 'proof_status', '')) if c is not None else ''


def pair_cost(sc, before, after, sink):
    """The technique's cost, measured: AFTER − BEFORE on the same scenario + seed."""
    flash = (after['size_text'] + after['size_data']) - (before['size_text'] + before['size_data'])
    cyc = after['fn_cycles_min'] - before['fn_cycles_min']
    lat = after['isr_latency_max_cycles'] - before['isr_latency_max_cycles']
    cd = {'pair': before['name'], 'flash_bytes': flash, 'ram_bytes': (after['size_data'] + after['size_bss']) - (before['size_data'] + before['size_bss']),
          'guarded_fn_cycles': cyc, 'isr_latency_max_cycles': lat, 'stack_high_water_bytes': after['stack_high_water'] - before['stack_high_water'],
          'how': 'avr-size .text+.data delta; --fn-cycles min (uninterrupted entry→ret) delta; --isr-latency max delta (natural interrupts)'}
    after.update(cost_delta_json=json.dumps(cd), cost_flash_bytes_delta=flash, cost_cycles_delta=cyc, latency_delta_cycles=lat)
    before.update(cost_delta_json=json.dumps({'pair': after['name'], 'note': 'the AFTER run carries the measured delta'}))
    sink.upsert('ScenarioRun', after)
    sink.upsert('ScenarioRun', before)
    if sc.get('technique'):
        from firmwarefaults.custom.taxonomy import techniques_by_name
        t = dict(techniques_by_name().get(sc['technique'], {'name': sc['technique']}))
        cur = sink.get('Technique', sc['technique'])
        if cur is not None:
            t = dict(cur) if isinstance(cur, dict) else {'name': sc['technique']}
        t.update(name=sc['technique'], measured_cost_bytes=flash, measured_cost_cycles=cyc, measured_latency_delta_cycles=lat, measured_by_run=after['name'])
        sink.upsert('Technique', t)
    return cd


def natural_rate_row(sc, run, sink):
    """Write the measured natural rate onto the fault row (rate + rate_source = the run) — a measured observation."""
    nat = json.loads(run['observed_json']).get('natural') or {}
    from firmwarefaults.custom.fault_rows import by_class
    seed_row = next((r for r in by_class().get(sc['fault_class'], []) if r['name'] == sc['fault']), {'name': sc['fault']})
    cur = sink.get(sc['fault_class'], sc['fault'])
    row = dict(cur) if isinstance(cur, dict) else dict(seed_row) if cur is None else {'name': sc['fault']}
    row.update(name=sc['fault'], rate=round(nat.get('rate', 0.0), 4),
               rate_source=('measured: run %s — %d torn read(s) in %d byte-0 carries over %.1f s of the simavr twin (variant %s, seed %d, no '
                            'forcing, from reset). The twin is deterministic and the tick shares the CPU clock: every run from reset repeats '
                            'these same %d carries at the same phases. Exposure if the phase were uniform (asynchronous RX traffic): %.2f %% per '
                            'carry = 2 cycles of load 1 x %d hal_millis calls / %d cycles, i.e. %.2f tears expected here (P(0) = %.2f) — so %d of '
                            '%d does not by itself separate a locked phase from bad luck; the seed phase sweep (sc-2) does. The plan\'s ≈ 13 %% '
                            'counted three gaps; only the load-1/load-2 gap tears at a byte-0 carry.')
                           % (run['name'], nat.get('tears', 0), nat.get('carries', 0), run['sim_seconds'], run['variant'], run['seed'],
                              nat.get('carries', 0), 100.0 * nat.get('exposure_per_carry', 0.0), nat.get('calls', 0), nat.get('cycles', 0),
                              nat.get('carries', 0) * nat.get('exposure_per_carry', 0.0),
                              (1.0 - nat.get('exposure_per_carry', 0.0)) ** nat.get('carries', 0), nat.get('tears', 0), nat.get('carries', 0)))
    sink.upsert(sc['fault_class'], row)
    return row
