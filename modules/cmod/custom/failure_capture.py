"""
@module cmod.custom.failure_capture

bss-9 (AI-Notes/plans/BENCH_SOLUTION_SIM_PLAN.md section 3c, D-bss-6): A TRACE IS KEPT ONLY ON FAILURE (or when pinned), and then only the window around it.
When a node run ends not-reached / diverged / checks-failed, the twin's pin events of the failing edge (the stimuli it applied: pin-at; what the firmware
drove on the wire: wire-edge) become ONE acquisition of the instruments arc - a `WaveformCapture` row per line, the same rows a scope capture writes
(instruments.custom.captures), source 'twin', so the osc chart draws them. The window is the LAST fraction of the edge (FAILURE_WINDOW, a knob), sampled at
the node's step where that fits MAX_POINTS, else coarser and said. Nothing is kept on a reached run.

    keep(manager, run_name, events, lo, hi, hz, step_s, why)  -> {'acquisition', 'rows': [names], 'words'} or {'rows': [], 'words'} when no line had a level
"""
import base64
import datetime
import hashlib
import json

FAILURE_WINDOW = 0.10   # KNOB (D-bss-6): the last tenth of the failing edge
MAX_POINTS = 4096       # KNOB: points per line; above it the step is coarsened, said
LOGIC_V = 5.0           # the UNO's logic level
_F = {'lineage': 'agilent', 'x_reference': 0.0, 'y_increment': 10.0 / 65535, 'y_origin': 32768.0, 'y_reference': 0.0}   # 16-bit WORD, +-5 V full scale


def _pin_events(events):
    out = []
    for e in events:
        if e.get('t') == 'pin-at':
            out.append({'t': 'pin', 'pin': e['pin'], 'level': int(e.get('level', 0)), 'cycle': int(e['cycle'])})
        elif e.get('t') == 'wire-edge':
            for p in (e.get('src'), e.get('dst')):
                if p:
                    out.append({'t': 'pin', 'pin': p, 'level': int(e.get('v', 0)), 'cycle': int(e['cycle'])})
    return out


def keep(manager, run_name, events, lo, hi, hz, step_s, why):
    import numpy as np
    from instruments.custom import captures as CAP
    from instruments.custom import device_feed as DF
    from instruments.custom import lineage as L
    from instruments.custom import sources as SRC
    lines = DF.sources_from_events(_pin_events(events), hz, logic_v=LOGIC_V)
    if not lines:
        return {'acquisition': '', 'rows': [], 'words': 'no capture: the twin reported no pin event on this run (no stimulus pin, no jumper)'}
    t_end = hi / float(hz)
    t0 = max(lo / float(hz), t_end - FAILURE_WINDOW * (hi - lo) / float(hz))
    dt = step_s if step_s and step_s > 0 else 1.0 / hz
    coarse = ''
    if (t_end - t0) / dt > MAX_POINTS:
        dt = (t_end - t0) / MAX_POINTS
        coarse = '; the step coarsened to %.3g us so the window fits %d points' % (dt * 1e6, MAX_POINTS)
    n = max(2, int(round((t_end - t0) / dt)))
    t = t0 + np.arange(n) * dt
    acq = 'fail-%s' % hashlib.sha256(run_name.encode()).hexdigest()[:10]
    now = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    f = dict(_F, x_increment=dt, x_origin=t0)
    names = []
    for ch, (pin, spec) in enumerate(sorted(lines.items()), 1):
        v = SRC.evaluate(spec, t)
        raw = L.to_raw(v, f).astype('<u2').tobytes()
        row = {'name': '%s-ch%d' % (acq, ch), 'endpoint': 'twin', 'instrument': 'polari-avr-twin', 'channel': ch, 'acquired_at': now, 'acquisition': acq, 'points': n,
               'format': 'WORD', 'lineage': 'agilent', 'x_increment': dt, 'x_origin': t0, 'x_reference': 0.0, 'y_increment': f['y_increment'], 'y_origin': f['y_origin'],
               'y_reference': 0.0, 'sample_rate_sps': 1.0 / dt, 'memory_depth_pts': float(n), 'trigger_json': json.dumps({'edge_cycles': [lo, hi], 'window_s': [t0, t_end]}),
               'settings_json': json.dumps({'line': pin, 'logic_v': LOGIC_V, 'failure_window': FAILURE_WINDOW}), 'raw_sha256': hashlib.sha256(raw).hexdigest(),
               'raw_bytes': len(raw), 'raw_path': '', 'raw_b64': base64.b64encode(raw).decode(), 'preamble_text': '',
               'source': 'twin', 'source_ref': 'run %s: %s; line %s over the failing edge\'s last %d %% (cycles %d..%d)' % (run_name, why, pin, int(FAILURE_WINDOW * 100), lo, hi),
               'note': 'kept on failure only (D-bss-6)'}
        CAP._upsert(manager, 'WaveformCapture', CAP._C_FIELDS, row)
        names.append(row['name'])
    return {'acquisition': acq, 'rows': names, 'words': 'failure capture %s: %d line%s (%s) over the edge\'s last %d %% at %.3g us per point%s'
            % (acq, len(names), '' if len(names) == 1 else 's', ', '.join(sorted(lines)), int(FAILURE_WINDOW * 100), dt * 1e6, coarse)}
