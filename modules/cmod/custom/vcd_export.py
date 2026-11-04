"""
@module cmod.custom.vcd_export

bss-14 (AI-Notes/plans/BENCH_SOLUTION_SIM_PLAN.md; the vital list's debug aid): A VCD OF WHAT A RUN KEPT, rendered on read from its WaveformCapture rows
(failure_capture: the pin lines and, since bss-14, the watched struct fields of a failure or pinned capture) - nothing stored twice, nothing kept for a
reached, unpinned run (D-bss-6). A pin line is a 1-bit wire (high above half the logic level); a field is a 32-bit vector of its integer value. GTKWave,
PulseView and sigrok read the result; the header names the run, the acquisition and the window.

    render(manager, run, acquisition='')   -> (vcd text, acquisition) - the pinned acquisition when both exist, else the failure one, else a refusal
"""
import base64
import datetime
import json

from cmod.custom import config_rows as R

TIMESCALE_NS = 1   # the VCD's unit: 1 ns (a 16 MHz cycle is 62.5 ns; a coarsened step is still a whole number of ns, rounded, said in the header)


def _ids():
    k = 0
    while True:
        s, n = '', k
        while True:
            s = chr(33 + n % 94) + s
            n //= 94
            if n == 0:
                break
        yield s
        k += 1


def render(manager, run, acquisition=''):
    from cmod.custom import failure_capture as FC
    from instruments.custom import captures as CAP
    from instruments.custom import lineage as L
    if R.get(manager, 'StructNodeRun', run) is None:
        raise R.ConfigRefused('no run %r' % run, status=404)
    ids = {'pin': FC.acquisition(run, 'pin'), 'fail': FC.acquisition(run, 'fail')}
    rows = [r for r in CAP.captures(manager) if r['acquisition'] in ids.values() and (not acquisition or r['acquisition'] == acquisition)]
    if not rows:
        raise R.ConfigRefused('run %s kept no capture%s: a reached run keeps none unless pinned (D-bss-6)' % (run, (' named %s' % acquisition) if acquisition else ''), status=404)
    acq = acquisition or (ids['pin'] if any(r['acquisition'] == ids['pin'] for r in rows) else ids['fail'])
    rows = sorted((r for r in rows if r['acquisition'] == acq), key=lambda r: r['channel'])
    gen = _ids()
    sigs = []
    for r in rows:
        st = json.loads(r.get('settings_json') or '{}')
        f = {k: r[k] for k in ('x_increment', 'x_origin', 'x_reference', 'y_increment', 'y_origin', 'y_reference', 'lineage')}
        v = L.volts(L.samples(base64.b64decode(r.get('raw_b64') or b''), r['format']), f) if r.get('raw_b64') else []
        kind = st.get('kind', 'pin')
        name = (st.get('line') or 'ch%d' % r['channel']).replace(' ', '_')
        if kind == 'field':
            vals = [int(round(float(x))) for x in v]
            width = 32
        else:
            half = float(st.get('logic_v', 5.0)) / 2.0
            vals = [1 if float(x) > half else 0 for x in v]
            width = 1
        sigs.append({'id': next(gen), 'name': name, 'width': width, 'vals': vals, 'dt': float(r['x_increment']), 't0': float(r['x_origin']), 'kind': kind})
    dt_ns = max(1, int(round(min(s['dt'] for s in sigs) * 1e9)))
    t0 = min(s['t0'] for s in sigs)
    first = rows[0]
    out = ['$date %s $end' % datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
           '$version polari cmod.custom.vcd_export (bss-14): run %s, acquisition %s, %s; the trigger %s; time 0 = %.9f s of the twin run; one sample = %d ns (%s) $end'
           % (run, acq, first.get('note', ''), first.get('trigger_json', '{}').replace('\n', ' '), t0, dt_ns, 'rounded' if abs(min(s['dt'] for s in sigs) * 1e9 - dt_ns) > 1e-6 else 'exact'),
           '$timescale %d ns $end' % TIMESCALE_NS, '$scope module %s $end' % run.replace(':', '_').replace('#', '_').replace(' ', '_')]
    out += ['$var %s %d %s %s $end' % ('reg' if s['width'] > 1 else 'wire', s['width'], s['id'], s['name']) for s in sigs]
    out += ['$upscope $end', '$enddefinitions $end']
    n = max(len(s['vals']) for s in sigs)
    last = {s['id']: None for s in sigs}
    for i in range(n):
        t_ns = int(round(((sigs[0]['dt'] * i) + (sigs[0]['t0'] - t0)) * 1e9))
        changes = []
        for s in sigs:
            if i >= len(s['vals']):
                continue
            val = s['vals'][i]
            if last[s['id']] is None or val != last[s['id']]:
                last[s['id']] = val
                changes.append(('%d%s' % (val, s['id'])) if s['width'] == 1 else ('b%s %s' % (format(val & 0xFFFFFFFF, 'b'), s['id'])))
        if changes:
            out.append('#%d' % t_ns)
            out += changes
    out.append('')
    return '\n'.join(out), acq
