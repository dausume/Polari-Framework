"""
@module firmwarefaults.custom.runner_sc3

THE sc-3 RUNNER (FIRMWARE_SCENARIO_PLAN.md §3a S6/S7, §9 sc-3): one side of an RTOS scenario on the ESP32-C3 twin.

  build      board.custom.gen_c3 + build_c3 (offline, the pinned contract; the build cache: a campaign builds each side ONCE)
  force      the step's recipe → polari_params_t bytes for this seed (scenarios_sc3.params_bytes) → written at the `polari`
             partition offset in a copy of the merged image by polari-c3-run — the SAME binary for every seed
  run        engine `c3-run` (the esp family of the ladder: a local polari-c3-run, the prf-esp-engines image, ESP_ENGINES_URL)
             under -icount 3 (sleep=off): virtual time = instruction count, so a run is a function of (image, params)
  read       UART0 → the SimRigState frames (board.custom.packet_ref, the reference parser the UNO runs use); UART1 → the trace
             (custom/c3_trace.py: the hook events → the wait-for graph, who ran during H's waits)
  decide     custom/outcome_sc3.py → a ScenarioRun row (fault_cycle = the decisive event's virtual INSTRUCTION index at -icount 3 —
             QEMU is instruction-level, plan §2b — with the µs beside it), ScenarioTraceCycle rows (the events around it, a
             configured table: symbol = the task, instruction = the event in words), the MathClaim (sim tier) + ProofRun
  pair       the technique's cost AFTER − BEFORE: flash (app.bin + the size columns), DRAM, and the run-time effect (H's worst wait;
             T1's mean round time; back-offs) onto the AFTER run and the Technique row

    run_side(sc, side, sink, seed=0) · run_pair(sc, sink, seed=0) · prepare(variant)
"""
import datetime
import hashlib
import json
import os

from firmwarefaults.custom import c3_trace as C, outcome_sc3 as O, scenarios as SC
from firmwarefaults.custom import scenarios_sc3 as S3
from firmwarefaults.custom.claim_bridge import write as write_claim, claim_name

KINDS = ('h-blocking-bounded', 'wait-for-acyclic')
SIM_VERSION = 'Espressif QEMU fork esp_develop_9.2.2_20260417 (qemu-system-riscv32 -machine esp32c3, -icount shift=3,align=off,sleep=off)'
ASSUMPTIONS = ['Espressif\'s QEMU fork models the ESP32-C3 at INSTRUCTION granularity under -icount 3 (8 ns per instruction), not cycle-accurately: '
               'the scheduling is the real ESP-IDF v5.5.5 FreeRTOS kernel, the timing is virtual (one interleaving per run)',
               'the trace hooks (polari_trace.h, force-included into the kernel) record the kernel\'s own switch / take / give / block / inherit events']
_BUILDS = {}


class ScenarioRefused(RuntimeError):
    pass


def sha(b):
    return hashlib.sha256(b if isinstance(b, bytes) else b.encode()).hexdigest()


def _now():
    return datetime.datetime.now().isoformat(timespec='seconds')


def home():
    from firmwarefaults.custom.sink import home as h
    return h()


def prepare(variant, h=None):
    """gen + build one C3 variant (cached by the build store + this process) → {'row', 'image', 'elf', 'work'}."""
    from board.custom import gen_c3, build_c3
    h = h or home()
    if (variant, h) in _BUILDS:
        return _BUILDS[(variant, h)]
    work = os.path.join(h, 'builds-c3', variant)
    gen_c3.gen_c3(variant, work)
    row = build_c3.build('c3', work)
    out = {'row': row, 'work': work}
    if row['state'] == 'built':
        out.update(image=open(row['image_path'], 'rb').read(), elf=open(os.path.join(work, 'out', 'firmware.elf'), 'rb').read())
        _BUILDS[(variant, h)] = out
    return out


def run_image(image, params, max_wall=120):
    from board.custom import engine_run
    r = engine_run.run('c3-run', ['flash_image.bin', '--params', params.hex(), '--params-offset', '0x%x' % S3.PARAMS_OFFSET,
                                  '--icount', str(S3.ICOUNT_SHIFT), '--max-wall', str(max_wall)], {'flash_image.bin': image}, timeout=max_wall + 60)
    f = r.get('files') or {}
    return {'ok': bool(r.get('ok')) or b'@END' in (f.get('trace.log') or b''), 'how': r['how'], 'where': r['where'], 'cost': r.get('cost'),
            'uart0': f.get('uart0.bin') or b'', 'trace': (f.get('trace.log') or b'').decode('utf-8', 'replace'),
            'run': json.loads(f.get('run.json', b'{}') or b'{}'), 'stderr': r.get('stderr') or r.get('stdout') or ''}


def telemetry(uart0):
    from board.custom import gen, packet_ref
    from board.custom.compat import wire_spec
    fm = gen.pinned_contract('SimRigState')[0]['field_map']
    spec = wire_spec(None, 'SimRigState', fm)
    p = packet_ref.StreamParser()
    out = []
    for mt, dev, seq, payload, ver in p.feed(uart0):
        if mt == 1:
            v = packet_ref.decode_any(fm, payload, ver, spec)
            out.append({'seq': seq, 'uptime_ms': int(v.get('uptime_ms', 0)), 'temp_c': v.get('temp_c'), 'status': v.get('status'),
                        'pwm_duty': v.get('pwm_duty')})
    return out, p


def instr(t_us):
    return int(t_us * 1000 // (1 << S3.ICOUNT_SHIFT))


def _base(sc, side, variant, b, seed, technique, knobs):
    row = b['row']
    return {'name': '%s@%s@%s@seed%d' % (sc['name'], side, row['name'], seed), 'scenario': sc['name'], 'side': side, 'variant': variant,
            'build_name': row['name'], 'technique_applied': technique, 'outcome': '', 'verdict_words': '', 'fault_cycle': 0, 'fault_pc': '',
            'fault_symbol': '', 'landed_pc': '', 'landed_symbol': '', 'landed_cycle': 0, 'torn_value': -1, 'expected_value': -1, 'frames_seen': 0,
            'frames_backwards': 0, 'bad_crc': 0, 'uptime_sequence': '', 'observed_json': '{}', 'trace_sha256': '', 'trace_samples': 0,
            'uart_sha256': '', 'firmware_sha256': row.get('artifact_sha256', ''), 'elf_sha256': sha(b['elf']) if b.get('elf') else '',
            'harness_digest': '', 'simulator_version': SIM_VERSION, 'seed': seed, 'sim_cycles': 0, 'sim_seconds': 0.0, 'wall_s': 0.0,
            'stack_high_water': 0, 'stack_high_water_paint': 0, 'stack_static_peak': 0, 'isr_latency_max_cycles': 0, 'isr_latency_vector': 0,
            'fn_cycles_min': 0, 'size_text': row.get('size_text', 0), 'size_data': row.get('size_data', 0), 'size_bss': row.get('size_bss', 0),
            'cost_delta_json': '{}', 'cost_flash_bytes_delta': 0, 'cost_cycles_delta': 0, 'latency_delta_cycles': 0, 'claim': '', 'repro_json': '{}',
            'ran_at': _now(), 'notes': 'knobs %s' % json.dumps(knobs, sort_keys=True), 'observable_value': '', 'reset_count': 0, 'isr_cycles_max': 0,
            'isr_cycles_vector': 0}


def _image_digest(how, where):
    if how == 'local-image':
        from board.custom import board_engines as be
        return '%s %s' % (where, be.local_image('esp')[:19])
    return '%s %s' % (how, where)


def _trace_rows(run_name, d, idx, around=10):
    rows, ev = [], d['events']
    lo, hi = max(0, idx - around), min(len(ev), idx + around + 1)
    t0 = ev[idx][0] if ev else 0
    holder = {}
    for j, e in enumerate(ev[:hi]):
        t, k, task, obj, arg = e
        if k == C.TAKE:
            holder[obj] = task
        elif k == C.GIVE and holder.get(obj) == task:
            holder.pop(obj, None)
        if j < lo:
            continue
        rows.append({'name': '%s#%03d' % (run_name, j - lo), 'run': run_name, 'idx': j - lo, 'cycle': instr(t), 'rel_cycle': instr(t) - instr(t0),
                     'pc': '', 'symbol': C.name_of(d, task), 'instruction': C.describe(d, e), 'sp': 0, 'sreg_i': 0, 'isr_vector': 0,
                     'r22': '', 'r23': '', 'r24': '', 'r25': '', 'watch': ' '.join('%s:%s' % (C.lock_name(d, l), C.name_of(d, t2)) for l, t2 in sorted(holder.items())) or '-',
                     'forced': int(j == idx), 'note': '%d µs (tick %d)%s' % (t, t // 1000, ' — THE DECISIVE EVENT' if j == idx else '')})
    return rows


def run_side(sc, side, sink, seed=0, write=True, h=None):
    steps = SC.steps_of(sc['name'])
    why = SC.refusal(sc)
    if why:
        raise ScenarioRefused(why)
    variant = sc['after_variant'] if side == 'after' else sc['before_variant']
    technique = sc['technique'] if side == 'after' else ''
    args = json.loads(steps[0]['args_json'])
    params, knobs = S3.params_bytes(args, seed)
    t0 = datetime.datetime.now()
    b = prepare(variant, h)
    if b['row']['state'] != 'built':
        raise ScenarioRefused('variant %s did not build: %s' % (variant, b['row'].get('notes', '')[-400:]))
    run = _base(sc, side, variant, b, int(seed), technique, knobs)
    cname = claim_name(sc['name'], run['build_name'])
    if write and sink.get('MathClaim', cname) is None:
        sink.upsert('MathClaim', {'name': cname, 'kind': 'safe-under-scenario', 'proof_status': 'conjectured', 'checker': 'sim',
                                  'statement_json': '{}', 'description': 'stated by the runner before the run'})
    r = run_image(b['image'], params)
    if not r['ok']:
        raise ScenarioRefused('the C3 twin failed (%s %s): %s' % (r['how'], r['where'], (r['stderr'] or json.dumps(r['run']))[-600:]))
    d = C.parse(r['trace'])
    tel, parser = telemetry(r['uart0'])
    kind = sc['observable_kind']
    ev_idx, landed = None, ''
    if kind == 'h-blocking-bounded':
        dec = O.decide_inversion(d, int(knobs['l_cs_us']), S3.SLACK_US)
        blk = [x for x in C.blocked(d, 'H', 'R') if x.get('to_us') is not None]
        if blk and dec.get('worst_req_us'):
            w = min(blk, key=lambda x: abs(x['from_us'] - dec['worst_req_us']))
            ev_idx = w['event_index']
            landed = 'in H\'s worst wait: %s' % (O._fmt_ran(w['ran']) or '-')
        run.update(fault_symbol='H blocks on R (round %s) at %s µs' % (dec.get('worst_round'), dec.get('worst_req_us')),
                   landed_symbol=landed[:200])
    elif kind == 'wait-for-acyclic':
        wf = C.wait_for(d)
        dec = O.decide_deadlock(d, wf, tel, d['end_us'])
        cyc = wf.get('persistent') or wf.get('first_cycle')
        if cyc:
            ev_idx = cyc['event_index']
            run.update(fault_symbol='wait-for cycle %s closed at %d µs (tick %d)' % (' → '.join(cyc['cycle']), cyc['t_us'], cyc['t_us'] // 1000),
                       landed_symbol=('persists to the end' if wf.get('persistent') else 'broken at %s µs by %s' % (
                           (wf['transient'][0] if wf['transient'] else {}).get('broken_at_us'), (wf['transient'][0] if wf['transient'] else {}).get('broken_by'))))
        dec['wait_for'] = wf
    else:
        raise ScenarioRefused('observable %r is not an sc-3 kind' % kind)
    trows = []
    if ev_idx is not None:
        t = d['events'][ev_idx][0]
        run.update(fault_cycle=instr(t), landed_cycle=0)
        trows = _trace_rows(run['name'], d, ev_idx)
    rr = r['run']
    run.update(outcome=dec['outcome'], verdict_words=dec['words'], observable_value=dec.get('value', ''), frames_seen=len(tel), bad_crc=parser.bad_crc,
               uptime_sequence=', '.join(str(f['uptime_ms']) for f in tel), uart_sha256=sha(r['uart0']), trace_sha256=sha(r['trace']),
               trace_samples=len(d['events']), harness_digest=_image_digest(r['how'], r['where']), sim_cycles=instr(d['end_us']),
               sim_seconds=round(d['end_us'] / 1e6, 6), wall_s=float(rr.get('wall_s', 0.0)))
    obs = {'decided': {k: v for k, v in dec.items() if k != 'wait_for'}, 'knobs': knobs, 'params_hex': params.hex(), 'boot': d['boot'],
           'app_line': d.get('pi') or d.get('locks_line'), 'app_deadlock': d.get('deadlock'), 'trace': d['trace'],
           'tasks': {v['name']: v['prio_at_dump'] for v in d['tasks'].values()}, 'locks': {v['name']: v['kind'] for v in d['locks'].values()},
           'rounds': d['rounds'], 'wait_for': dec.get('wait_for'), 'round_t1_us': C.round_times(d, 'T1') if kind == 'wait-for-acyclic' else [], 'telemetry': {'frames': len(tel), 'bad_crc': parser.bad_crc,
                                                                                 'rom_text_bytes_skipped': parser.skipped,
                                                                                 'first': tel[:2], 'last': tel[-2:]},
           'sizes': b['row'].get('sizes'), 'twin': {'how': r['how'], 'where': r['where'], 'run': {k: rr.get(k) for k in ('wall_s', 'cpu_s', 'peak_rss_mb', 'why')}}}
    run['observed_json'] = json.dumps(obs, default=str)
    rep = json.loads(b['row'].get('repro_json') or '{}')
    run['repro_json'] = json.dumps({
        'inputs': [{'label': 'flash_image.bin (merged, 4 MB)', 'sha256': run['firmware_sha256']}, {'label': 'firmware.elf', 'sha256': run['elf_sha256']},
                   {'label': 'polari params (52 B at 0x%x)' % S3.PARAMS_OFFSET, 'sha256': sha(params), 'hex': params.hex()},
                   {'label': 'scenario row', 'sha256': sha(json.dumps(sc, sort_keys=True))}, {'label': 'scenario steps', 'sha256': sha(json.dumps(steps, sort_keys=True))}]
                  + rep.get('inputs', []),
        'tools': {'twin': SIM_VERSION, 'engine': run['harness_digest'], 'build': rep.get('tools', {})},
        'knobs': {'variant': variant, 'build_flags': (rep.get('knobs') or {}).get('build_flags'), 'recipe': knobs, 'argv': rr.get('argv')},
        'seeds': {'seed': int(seed), 'deterministic': True,
                  'why': 'seed 0 = the recipe\'s knobs; seed k = splitmix64 draws of the seeded knobs (scenarios_sc3.knobs_for); QEMU -icount 3 with '
                         'sleep=off makes virtual time a function of the instruction stream, so the same image + params replay the same trace'},
        'generated_files': [{'path': 'uart0.bin', 'sha256': run['uart_sha256']}, {'path': 'trace.log', 'sha256': run['trace_sha256']}],
        'how_to_rerun': 'pol faults run %s --%s --seed %d' % (sc['name'], side, int(seed)), 'recorded_at': run['ran_at'],
        'cost': {'twin': r.get('cost'), 'run': {k: rr.get(k) for k in ('wall_s', 'cpu_s', 'peak_rss_mb')}},
        'rule': 'every result carries the initial conditions and seeds that produced it (2026-09-26)'}, default=str)
    if not write:
        run['_trace_rows'] = trows
        return run
    run['claim'], after, before = write_claim(sink, run, sc)
    c = sink.get('MathClaim', run['claim'])
    if isinstance(c, dict):
        sink.upsert('MathClaim', dict(c, assumptions_json=json.dumps(ASSUMPTIONS)))
    elif c is not None:
        c.assumptions_json = json.dumps(ASSUMPTIONS)
    run['wall_total_s'] = round((datetime.datetime.now() - t0).total_seconds(), 2)
    sink.upsert('ScenarioRun', run)
    for tr in trows:
        sink.upsert('ScenarioTraceCycle', tr)
    run['_claim_flip'] = (before or 'conjectured', after)
    run['_trace_rows'] = trows
    return run


def _mean(xs):
    return round(sum(xs) / len(xs), 1) if xs else None


def pair_cost(sc, before, after, sink):
    ob, oa = json.loads(before['observed_json']), json.loads(after['observed_json'])
    sb, sa = ob.get('sizes') or {}, oa.get('sizes') or {}
    flash = (after['size_text'] + after['size_data']) - (before['size_text'] + before['size_data'])
    ram = int(sa.get('dram_used', 0)) - int(sb.get('dram_used', 0))
    cd = {'pair': before['name'], 'flash_bytes': flash, 'ram_bytes': ram, 'cost_what': S3.OBSERVE[sc['name']]['cost_what'],
          'how': 'idf.py size json2 deltas (text+data columns; DRAM used); run-time effects from the trace / the app lines'}
    if sc['observable_kind'] == 'h-blocking-bounded':
        wb, wa = ob['decided'].get('worst_us', 0), oa['decided'].get('worst_us', 0)
        cd.update(h_worst_wait_us_before=wb, h_worst_wait_us_after=wa, latency_delta_us=wa - wb, inherit_events_after=oa['decided'].get('inherit_events'),
                  cycles=0, cycles_what='not timed: the mutex\'s inheritance path is inside the kernel (its effect is the latency delta)')
        lat = wa - wb
    else:
        rb, ra = ob.get('round_t1_us') or [], oa.get('round_t1_us') or []
        cd.update(t1_mean_round_us_before=_mean(rb), t1_mean_round_us_after=_mean(ra), backoffs_after=(oa.get('app_line') or {}).get('backoffs'),
                  cycles=0, cycles_what='T1\'s mean round time (ROUND → DONE) AFTER vs BEFORE where BEFORE finished any round')
        lat = int((_mean(ra) or 0) - (_mean(rb) or 0)) if rb and ra else 0
    after.update(cost_delta_json=json.dumps(cd), cost_flash_bytes_delta=flash, cost_cycles_delta=0, latency_delta_cycles=0)
    before.update(cost_delta_json=json.dumps({'pair': after['name'], 'note': 'the AFTER run carries the measured delta'}))
    sink.upsert('ScenarioRun', after)
    sink.upsert('ScenarioRun', before)
    if sc.get('technique'):
        from firmwarefaults.custom.taxonomy import techniques_by_name
        cur = sink.get('Technique', sc['technique'])
        t = dict(cur) if isinstance(cur, dict) else dict(techniques_by_name().get(sc['technique'], {'name': sc['technique']})) if cur is None else {}
        t.update(name=sc['technique'], measured_cost_bytes=flash, measured_ram_bytes=ram, measured_cost_cycles=0, measured_latency_delta_cycles=0,
                 measured_cost_what='%s (ESP32-C3, run-time effect %+d µs: %s)' % (cd['cost_what'], lat, cd.get('cycles_what', '')),
                 measured_by_run=after['name'])
        sink.upsert('Technique', t)
    return cd


def run_pair(sc, sink, seed=0, h=None):
    b = run_side(sc, 'before', sink, seed, h=h)
    a = run_side(sc, 'after', sink, seed, h=h)
    pair_cost(sc, b, a, sink)
    return [b, a]
