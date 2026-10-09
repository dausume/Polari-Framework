"""
@module cmod.custom.glue_build

BUILD + PROVE A RENDERED GRAPH (C_MODULARIZATION_PLAN.md §10 cmod-1), through the board engines seam (never a device assumed):

  build(graph)   `make` ALONE in the committed project (GNU make + avr-gcc on the rung avr-gcc resolves to — the local
                 prf-board-engines image here) → the .hex sha, avr-size .text/.data/.bss (from make's own `size` target);
                 the per-symbol shipped bytes (cmod.custom.measure — the Makefile's flags + -fstack-usage) against the cost
                 estimated before the build; then `pol cmod conform <project dir>` reads the rendered project back as a
                 plain project (its polari-firmware.json, committed beside the Makefile)
  prove(graph)   BEHAVIOUR EQUIVALENCE on the simavr twin: the hand-written app it replaces (board gen + build of the base
                 configuration — the same .hex board ships) and the rendered glue run with the SAME stimulus (the sc-0/sc-1
                 harness: an ADC0 millivolt ramp + commands injected at fixed cycles, free-running, seeded) → both UART
                 streams decoded by the independent Python reference (board.custom.packet_ref) and compared frame by frame,
                 field by field; the cycle each frame's first byte left the UART (--uart-tx-log) compared too

Equivalent = the same number of frames and, frame by frame, the same seq, device_id and fields (uptime_ms, temp_c, led_on,
pwm_duty, status, name) — exact equality, no tolerance (a tolerance would be stated here if one were ever needed). The
record (cmod/custom/glue_builds/<graph>.json) gains `build`, `conformed` and `proof`.
"""
import datetime
import hashlib
import json
import os
import shutil
import struct
import tempfile

from cmod.custom import glue as GL

#: the stimulus both builds see (sc-0/sc-1 harness flags): 4 s free-running at 16 MHz, seed 1, ADC0 a 700→800→700 mV
#: triangle every 2 s (TMP36: 20 → 30 °C), and three host commands at fixed cycles — led_on + pwm_duty 42 at 1.5 s, pwm_duty
#: 250 at 2.25 s (hal_pwm_apply clamps it to 100), led_on false at 3.0 s
STIMULUS = {'seconds': 4, 'seed': 1, 'adc0_ramp': '700,800,2000',
            'commands': [(24000000, {'led_on': True, 'pwm_duty': 42}), (36000000, {'pwm_duty': 250}), (48000000, {'led_on': False})]}
FIELDS = ('uptime_ms', 'temp_c', 'led_on', 'pwm_duty', 'status', 'name')
F_CPU = 16000000


def sha(b):
    return hashlib.sha256(b).hexdigest()


def _now():
    return datetime.datetime.now().isoformat(timespec='seconds')


def _project_files(d):
    from cmod.custom import projects as P
    return {f: open(os.path.join(d, f), 'rb').read() for f in sorted(os.listdir(d)) if f != P.MANIFEST_NAME and not f.startswith('firmware.')}


def make_alone(d):
    """make's default target on the engine rung → {ok, hex, hex_sha256, sizes, how, where, stdout}."""
    from board.custom import build as B
    from cmod.custom import cmod_engines as CE
    r = CE.run('make', [], _project_files(d))
    hexb = (r.get('files') or {}).get('firmware.hex')
    sizes = B.parse_size_A(r.get('stdout') or '')
    return {'ok': bool(r.get('ok') and hexb), 'hex': hexb or b'', 'hex_sha256': sha(hexb) if hexb else '', 'sizes': sizes,
            'how': r.get('how', ''), 'where': r.get('where', ''), 'stdout': (r.get('stdout') or '')[-600:], 'stderr': (r.get('stderr') or '')[-600:]}


def build(name, manager=None, conform=True):
    rows = GL.graph_rows(name, manager)
    g = rows['graph']
    d = GL.project_dir(g)
    rec = GL.load_record(name)
    if not rec or not os.path.isdir(d):
        raise GL.GlueRefused('%s is not rendered yet — pol cmod render %s' % (name, name))
    df = GL.diff(name, manager)
    mk = make_alone(d)
    if not mk['ok']:
        raise GL.GlueRefused('make alone failed in %s (%s %s): %s' % (d, mk['how'], mk['where'], mk['stderr'] or mk['stdout']))
    from cmod.custom import measure as M
    srcs = [f for f in sorted(os.listdir(d)) if f.endswith('.c')]
    meas = M.measure(d, srcs)
    text = meas['modes']['shipped']['text']
    atoms = [p['atom'] for p in rec['cost_estimate']['parts'] if p['as'] != 'glue + library reference: the replaced main() as shipped']
    fn = {a.split('.', 1)[-1] for a in atoms}
    by = {'atoms (shipped symbols)': sum(v for k, v in text.items() if k in fn), 'ISR vectors': sum(v for k, v in text.items() if k.startswith('__vector_')
                                                                                                  and k not in ('__vector_default',)),
          'main (glue + inlined atoms + inlined library)': text.get('main', 0)}
    attributed = sum(by.values())
    flash = mk['sizes'].get('.text', 0) + mk['sizes'].get('.data', 0)
    est = rec['cost_estimate']['total_bytes']
    inl = {k: int((a.get('cost') or {}).get('text_bytes_noinline') or 0) - text.get(a['function'], 0)
           for k, a in GL.context(g)['atoms'].items() if k in atoms and a['kind'] != 'isr'}
    shrunk = {k: v for k, v in sorted(inl.items()) if v}
    build_rec = {'ok': True, 'built_by': 'make alone (%s %s)' % (mk['how'], mk['where']), 'hex_sha256': mk['hex_sha256'],
                 'size_text': mk['sizes'].get('.text', 0), 'size_data': mk['sizes'].get('.data', 0), 'size_bss': mk['sizes'].get('.bss', 0),
                 'flash_bytes': flash, 'cost_estimate_bytes': est, 'cost_measured_attributable_bytes': attributed,
                 'cost_measured_breakdown': by, 'runtime_bytes': mk['sizes'].get('.text', 0) - attributed,
                 'cost_why': 'estimated %d B before the build (atoms as nodes + ISRs + the replaced main as shipped); measured after: %d B '
                             'attributable (%s) + %d B C runtime (vectors, crt, libgcc) = .text %d B' % (
                                 est, attributed, ', '.join('%s %d' % kv for kv in by.items()), mk['sizes'].get('.text', 0) - attributed,
                                 mk['sizes'].get('.text', 0)),
                 'estimate_minus_attributable': {'bytes': est - attributed, 'atoms_inlined_or_smaller_shipped': shrunk,
                                                 'explained_bytes': sum(shrunk.values())},
                 'files_sha256': rec['files_sha256'], 'hand_edited': df['hand_edited'], 'stale': df['stale'],
                 'measured_elf_sha256': meas['modes']['shipped']['elf_sha256'], 'built_at': _now()}
    rec['build'] = build_rec
    if conform:
        from cmod.custom import manifest as MF
        c = MF.conform(d, measure=True)
        m = c['manifest']
        rec['conformed'] = {'manifest': '%s/%s' % (g['generated_project'], os.path.basename(c['path'])),
                            'manifest_sha256': sha(open(c['path'], 'rb').read()), 'atoms': m['counts']['atoms'],
                            'glue_atoms': sorted(a['name'] for a in m['atoms'] if a['module'] == 'polari_graph.c'),
                            'not_isr_safe': m['counts']['not_isr_safe'], 'written': c['written']}
    GL.save_record(name, rec)
    return rec


# ------------------------------------------------------------------ the twin
def _commands():
    from board.custom import gen
    from board.custom.compat import wire_spec
    from grpcbridge.custom.wire_ref import encode, frame
    fm = gen.pinned_contract('SimRigState')[0]['field_map']
    spec = wire_spec(None, 'SimRigState', fm)
    return [(cyc, frame(1, 0, i + 1, encode(spec, vals, present=sorted(vals)), spec['wire_version'])) for i, (cyc, vals) in enumerate(STIMULUS['commands'])]


def twin_args():
    a = ['--hex', 'firmware.hex', '--mcu', 'atmega328p', '--freq', str(F_CPU), '--free', '--seconds', str(STIMULUS['seconds']), '--status-ms', '0',
         '--adc0-ramp', STIMULUS['adc0_ramp'], '--uart-out', 'uart.bin', '--uart-tx-log', 'tx.bin', '--seed', str(STIMULUS['seed'])]
    files = {}
    for i, (cyc, body) in enumerate(_commands()):
        files['cmd%d.bin' % i] = body
        a += ['--inject', 'cmd%d.bin@%d' % (i, cyc)]
    return a, files


def tx_cycles(log):
    """--uart-tx-log: u64 cycle + u8 byte + u8 flags per byte → [(cycle, byte)]."""
    return [(struct.unpack_from('<Q', log, i)[0], log[i + 8]) for i in range(0, len(log) - 9, 10)]


def decode(uart, txlog=b''):
    """→ [{'seq', 'device_id', fields…, 'cycle'}] by the independent reference parser; cycle = when the frame's first byte left."""
    from board.custom import gen, packet_ref
    from board.custom.compat import wire_spec
    fm = gen.pinned_contract('SimRigState')[0]['field_map']
    spec = wire_spec(None, 'SimRigState', fm)
    cyc = tx_cycles(txlog) if txlog else []
    out, pos = [], 0
    p = packet_ref.StreamParser()
    data = bytes(uart)
    for mt, dev, seq, payload, ver in p.feed(data):
        f = packet_ref.decode_any(fm, payload, ver, spec)
        hdr = struct.pack('<HBBHI', 0x504C, ver, mt, dev, seq)
        at = data.find(hdr, pos)
        pos = at + 1 if at >= 0 else pos
        out.append(dict({k: f.get(k) for k in FIELDS}, seq=seq, device_id=dev, msg_type=mt,
                        cycle=cyc[at][0] if 0 <= at < len(cyc) else None))
    return out


def run_twin(hexb, argv=None, files=None):
    """ucd-0e2b: `argv`/`files` default to the sim-rig stimulus (every pre-existing caller) — a second graph's own
    profile (STIMULI below) passes its own."""
    from firmwarefaults.custom import harness
    if argv is None:
        argv, files = twin_args()
    r = harness.run_files(argv, hexb, files or {})
    if not r['ok']:
        raise GL.GlueRefused('the twin run failed (%s %s): %s' % (r.get('how'), r.get('where'), (r.get('stderr') or r.get('stdout') or '')[-400:]))
    return r


# ------------------------------------------------------------------ ucd-0e2b: a SECOND graph's own stimulus profile
#: button-clock-graph's own proof stimulus (UNO_CORE_DEMO_PLAN.md, ucd-0e2b): N debounced presses on D2 (--pin-at,
#: the SAME cycle schedule board.board_button_clock_twin_selftest/button_clock_acceptance already prove with — never
#: a second harness idiom) + --wire PD6:PD3 (the sense pin witnesses the LED line) + ONE injected SET_TIME, so the
#: proof also covers the command path (clock_set) the sim-rig stimulus has no equivalent of. Decoded with the SAME
#: independent Python reference codec (board.custom.packet_ref / grpcbridge.custom.wire_ref) over BOTH wire classes.
BC_N_PRESSES = 4
BC_STATE_FIELDS = ('boot_session', 'uptime_ms', 'epoch_s', 'ms', 'clock_synced', 'sync_generation', 'sync_uncertainty_ms',
                    'drift_ms', 'button_presses', 'led_on', 'led_changed_at', 'sense_rises', 'sense_falls', 'last_edge_at',
                    'last_edge_ms', 'dropped_events', 'status', 'name')
BC_EVENT_FIELDS = ('boot_session', 'kind', 'uptime_ms', 'epoch_s', 'ms', 'name')


def _bc_specs():
    from board import board_button_clock_twin_selftest as T
    return T._specs()


def _bc_set_time_frame(spec_s, seq, epoch_s, ms, generation):
    from board.custom import packet_ref
    from grpcbridge.custom import wire_ref
    vals = {'set_epoch_s': epoch_s, 'set_ms': ms, 'set_sync_generation': generation}
    payload = wire_ref.encode(spec_s, vals, present=sorted(vals))
    return packet_ref.frame(1, 0, seq, payload, version=spec_s['wire_version'])


def bc_stimulus_argv():
    """-> (argv, files, seconds): the button-clock-graph stimulus. N presses on D2 (--pin-at), --wire PD6:PD3, one
    SET_TIME injected a beat after the last press (so clock_set's own atom runs too, and a few telemetry frames
    follow it for the proof to compare)."""
    from board import board_button_clock_twin_selftest as T
    fmap_s, spec_s, _fmap_e, _spec_e = _bc_specs()
    pinat, end_cycle = T._press_pinat(BC_N_PRESSES)
    set_time_cycle = end_cycle + 1600000              # 100 ms after the last press (past the final debounce)
    cmd = _bc_set_time_frame(spec_s, 1, epoch_s=1000000000, ms=0, generation=1)
    seconds = (set_time_cycle + 1600000 * 4) / float(F_CPU)   # 4 more telemetry periods (400 ms) after SET_TIME
    argv = ['--hex', 'firmware.hex', '--mcu', 'atmega328p', '--freq', str(F_CPU), '--free', '--seconds', '%g' % seconds,
            '--status-ms', '0', '--uart-out', 'uart.bin', '--uart-tx-log', 'tx.bin', '--wire', 'PD6:PD3'] + pinat \
        + ['--inject', 'cmd0.bin@%d' % set_time_cycle]
    return argv, {'cmd0.bin': cmd}, seconds


def bc_decode(uart, txlog=b''):
    """-> (states, events): the SAME StreamParser/decode_any reference codec board_button_clock_twin_selftest proves
    with, each frame tagged with the cycle its first byte left the UART (--uart-tx-log), same idiom as `decode()`."""
    from board.custom import packet_ref
    fmap_s, spec_s, fmap_e, spec_e = _bc_specs()
    cyc = tx_cycles(txlog) if txlog else []
    data = bytes(uart)
    p = packet_ref.StreamParser()
    states, events, pos = [], [], 0
    for mt, dev, seq, payload, ver in p.feed(data):
        fmap, spec, fields = (fmap_s, spec_s, BC_STATE_FIELDS) if mt == 1 else (fmap_e, spec_e, BC_EVENT_FIELDS)
        f = packet_ref.decode_any(fmap, payload, ver, spec)
        hdr = struct.pack('<HBBHI', 0x504C, ver, mt, dev, seq)
        at = data.find(hdr, pos)
        pos = at + 1 if at >= 0 else pos
        row = dict({k: f.get(k) for k in fields}, seq=seq, device_id=dev, msg_type=mt, cycle=cyc[at][0] if 0 <= at < len(cyc) else None)
        (states if mt == 1 else events).append(row)
    return states, events


def _bc_compare_one(a, b, fields):
    diffs = []
    if len(a) != len(b):
        diffs.append('frame count %d vs %d' % (len(a), len(b)))
    for i, (x, y) in enumerate(zip(a, b)):
        for k in ('seq', 'device_id', 'msg_type') + tuple(fields):
            if x.get(k) != y.get(k):
                diffs.append('frame %d %s: %r vs %r' % (i, k, x.get(k), y.get(k)))
    return diffs


def bc_compare(fa_s, fa_e, fb_s, fb_e):
    diffs = _bc_compare_one(fa_s, fb_s, BC_STATE_FIELDS) + _bc_compare_one(fa_e, fb_e, BC_EVENT_FIELDS)
    return {'equivalent': not diffs, 'frames': min(len(fa_s), len(fb_s)) + min(len(fa_e), len(fb_e)),
            'differences': diffs[:20], 'n_differences': len(diffs)}


def _prove_button_clock(ref, mk):
    argv, files, seconds = bc_stimulus_argv()
    rr, rg = run_twin(ref['hex'], argv, files), run_twin(mk['hex'], argv, files)
    fa_s, fa_e = bc_decode(rr['uart'], rr['tx'])
    fb_s, fb_e = bc_decode(rg['uart'], rg['tx'])
    cmp_ = bc_compare(fa_s, fa_e, fb_s, fb_e)
    return {'equivalent': cmp_['equivalent'], 'frames_compared': cmp_['frames'],
            'frames_hand': len(fa_s) + len(fa_e), 'frames_glue': len(fb_s) + len(fb_e),
            'fields_compared': ['seq', 'device_id', 'msg_type'] + list(BC_STATE_FIELDS) + list(BC_EVENT_FIELDS),
            'differences': cmp_['differences'], 'n_differences': cmp_['n_differences'],
            'raw_uart_identical': rr['uart'] == rg['uart'], 'uart_sha256': {'hand': sha(rr['uart']), 'glue': sha(rg['uart'])},
            'reference': {'variant': 'uno-button-clock', 'built_by': 'board gen + board build (the shipped pipeline)',
                          'hex_sha256': ref['hex_sha256'], 'size_text': ref['size_text'], 'size_data': ref['size_data'], 'size_bss': ref['size_bss']},
            'glue': {'hex_sha256': mk['hex_sha256'], 'size_text': mk['sizes'].get('.text', 0), 'size_data': mk['sizes'].get('.data', 0),
                     'size_bss': mk['sizes'].get('.bss', 0), 'built_by': 'make alone (%s %s)' % (mk['how'], mk['where'])},
            'hex_identical': ref['hex_sha256'] == mk['hex_sha256'],
            'cycles': {'total_hand': (rr['final'] or {}).get('cycles'), 'total_glue': (rg['final'] or {}).get('cycles'),
                       'frame_tx_cycle_delta_min': None, 'frame_tx_cycle_delta_max': None,
                       'first_frame_cycle_hand': fa_s[0]['cycle'] if fa_s else None, 'first_frame_cycle_glue': fb_s[0]['cycle'] if fb_s else None},
            # 'seed'/'adc0_ramp_mv' carry '-' (this stimulus has neither — N presses + --wire + one SET_TIME, not an
            # ADC ramp): cmod.custom.rows.graph_rows() formats every graph's stimulus the SAME way (its own 'stimulus'
            # CGlueBuild column), so this dict keeps the sim-rig-shaped keys rather than asking that generic reader
            # to branch per graph.
            'stimulus': {'seconds': round(seconds, 3), 'seed': '-', 'adc0_ramp_mv': '-',
                         'commands': ['%d press(es) on D2' % BC_N_PRESSES, '--wire PD6:PD3',
                                      'SET_TIME epoch_s=1000000000 ms=0 sync_generation=1'],
                         'argv': ['polari-avr-twin'] + argv},
            'first_commanded_frame': next((i for i, f in enumerate(fb_s) if f.get('status') == 'synced'), None),
            'samples': [{k: f[k] for k in ('seq',) + BC_STATE_FIELDS} for f in (fb_s[:1] + fb_s[-1:])],
            'twin': {'how': rg.get('how'), 'where': rg.get('where'), 'simulator': 'polari-avr-twin (libsimavr 1.6, prf-board-engines:trixie)'},
            'proven_at': _now()}


#: graph name -> the proof runner over (ref, mk) — 'uno-sim-rig-graph' is cmod-1's own, UNCHANGED (prove_dir's
#: inline body, below, is still exactly what it always was for that key, called directly); ucd-0e2b adds the second
#: entry so `pol cmod prove <graph>` dispatches on the graph instead of assuming sim-rig's stimulus for everyone.
STIMULI = {'uno-button-clock-graph': _prove_button_clock}


def compare(a, b):
    """Frame-by-frame, field-by-field. → {'equivalent', 'frames', 'differences': [...], 'cycle_delta_max', 'raw_identical'}."""
    diffs = []
    if len(a) != len(b):
        diffs.append('frame count %d vs %d' % (len(a), len(b)))
    for i, (x, y) in enumerate(zip(a, b)):
        for k in ('seq', 'device_id', 'msg_type') + FIELDS:
            if x.get(k) != y.get(k):
                diffs.append('frame %d %s: %r vs %r' % (i, k, x.get(k), y.get(k)))
    deltas = [y['cycle'] - x['cycle'] for x, y in zip(a, b) if x.get('cycle') is not None and y.get('cycle') is not None]
    return {'equivalent': not diffs, 'frames': min(len(a), len(b)), 'differences': diffs[:20], 'n_differences': len(diffs),
            'cycle_delta_min': min(deltas) if deltas else None, 'cycle_delta_max': max(deltas) if deltas else None}


def reference_build(base):
    """The hand-written app as board builds it (gen + build of the base configuration, offline, pinned contract)."""
    from board.custom import gen, build as B
    w = tempfile.mkdtemp(prefix='cmod-ref-')
    try:
        gen.gen('uno', work=w, variant=base)
        row = B.build('uno', work=w)
        if row['state'] != 'built':
            raise GL.GlueRefused('the hand-written %s did not build: %s' % (base, row.get('notes', '')))
        return {'hex': open(row['hex_path'], 'rb').read(), 'hex_sha256': row['artifact_sha256'], 'size_text': row['size_text'],
                'size_data': row['size_data'], 'size_bss': row['size_bss']}
    finally:
        shutil.rmtree(w, ignore_errors=True)


def prove_dir(d, base, graph=None):
    """The equivalence of ONE rendered project dir against the hand-written base configuration → the proof dict (no
    record). ucd-0e2b: `graph` dispatches to that graph's own STIMULI entry (a sim-rig-shaped stimulus is wrong for
    button-clock — a different wire class, a different invariant); omitted or unknown falls back to this function's
    own body below (the sim-rig stimulus, unchanged — every pre-existing caller)."""
    ref = reference_build(base)
    mk = make_alone(d)
    if not mk['ok']:
        raise GL.GlueRefused('make alone failed: %s' % (mk['stderr'] or mk['stdout']))
    if graph in STIMULI:
        return STIMULI[graph](ref, mk)
    rr, rg = run_twin(ref['hex']), run_twin(mk['hex'])
    fa, fb = decode(rr['uart'], rr['tx']), decode(rg['uart'], rg['tx'])
    cmp_ = compare(fa, fb)
    commanded = [i for i, f in enumerate(fb) if f['status'] == 'commanded']
    return {'equivalent': cmp_['equivalent'], 'frames_compared': cmp_['frames'], 'frames_hand': len(fa), 'frames_glue': len(fb),
            'fields_compared': ['seq', 'device_id', 'msg_type'] + list(FIELDS), 'differences': cmp_['differences'],
            'n_differences': cmp_['n_differences'], 'raw_uart_identical': rr['uart'] == rg['uart'],
            'uart_sha256': {'hand': sha(rr['uart']), 'glue': sha(rg['uart'])},
            'reference': {'variant': base, 'built_by': 'board gen + board build (the shipped pipeline)',
                          'hex_sha256': ref['hex_sha256'], 'size_text': ref['size_text'], 'size_data': ref['size_data'], 'size_bss': ref['size_bss']},
            'glue': {'hex_sha256': mk['hex_sha256'], 'size_text': mk['sizes'].get('.text', 0), 'size_data': mk['sizes'].get('.data', 0),
                     'size_bss': mk['sizes'].get('.bss', 0), 'built_by': 'make alone (%s %s)' % (mk['how'], mk['where'])},
            'hex_identical': ref['hex_sha256'] == mk['hex_sha256'],
            'cycles': {'total_hand': (rr['final'] or {}).get('cycles'), 'total_glue': (rg['final'] or {}).get('cycles'),
                       'frame_tx_cycle_delta_min': cmp_['cycle_delta_min'], 'frame_tx_cycle_delta_max': cmp_['cycle_delta_max'],
                       'first_frame_cycle_hand': fa[0]['cycle'] if fa else None, 'first_frame_cycle_glue': fb[0]['cycle'] if fb else None},
            'stimulus': {'seconds': STIMULUS['seconds'], 'seed': STIMULUS['seed'], 'adc0_ramp_mv': STIMULUS['adc0_ramp'],
                         'commands': ['%s @ cycle %d (%.3f s)' % (', '.join('%s=%s' % kv for kv in sorted(v.items())), c, c / F_CPU) for c, v in STIMULUS['commands']],
                         'command_frames_sha256': [sha(b) for _, b in _commands()], 'argv': ['polari-avr-twin'] + twin_args()[0]},
            'first_commanded_frame': commanded[0] if commanded else None,
            'samples': [{k: f[k] for k in ('seq',) + FIELDS} for f in (fb[:1] + [fb[i] for i in commanded[:1]] + fb[-1:])],
            'twin': {'how': rg.get('how'), 'where': rg.get('where'), 'simulator': 'polari-avr-twin (libsimavr 1.6, prf-board-engines:trixie)'},
            'proven_at': _now()}


def prove(name, manager=None, write=True):
    rows = GL.graph_rows(name, manager)
    g = rows['graph']
    d = GL.project_dir(g)
    rec = GL.load_record(name)
    if not rec or not os.path.isdir(d):
        raise GL.GlueRefused('%s is not rendered yet — pol cmod render %s' % (name, name))
    proof = prove_dir(d, g['base_configuration'], graph=g['name'])
    proof.update(graph_sha256=rec['graph_sha256'], files_sha256=rec['files_sha256'], hand_edited=GL.diff(name, manager)['hand_edited'])
    if write:
        rec['proof'] = proof
        GL.save_record(name, rec)
    return proof
