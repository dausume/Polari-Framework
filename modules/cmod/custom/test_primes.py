"""
@module cmod.custom.test_primes

msv-3 (AI-Notes/plans/MEASURED_VS_SIMULATED_PLAN.md section 5b, touch and confirm): PRIME A MEASURE STEP, THEN KEEP BOTH HANDS ON THE WORK. The user
said on 2026-11-04: "People only have two hands, they cannot hit the button and be doing the probe at the same time, what you can do is prime it to
expect a signal soon and it waits for a certain (configurable) period of time and awaits the data, confirming it once it comes."

  prime(manager, session, step, body)   body {endpoint | instrument (+ the Bridge's lines later), window_s?, chain?} -> the armed TestStepPrime.
                                        An endpoint prime is listened to by a background thread through sigrok. A Bridge prime waits for feed().
  feed(manager, prime, lines)           sigrok '-O analog' lines (from the thread, or POSTed by a Bridge) -> the prime after judging them
  cancel(manager, prime) / primes(manager, session) / settle(manager, session)

How it confirms:
- CONFIRMED as soon as a steady value (sigrok_reader.steady: one channel, one count) is one a correct build may read: in the instrument band, or
  in the tolerance band (msv-1). Before the probes touch, an open probe reads a steady 0, and that is not a confirmation, so it keeps waiting.
- When the window ends:
  - KEPT-LAST: the last steady value is kept and judged. A real fault - an open joint - also reads steady 0, so it is recorded, never dropped.
  - NOT STEADY: lines came but never settled.
  - WRONG MODE: only another unit or AC came.
  - NO DATA: nothing came through, so the probe, the cable or the port.
- With chain on, a confirmation primes the next pending measure step with the same meter, so a person goes point to point without touching the
  screen. A stimulus or look step in between stops the chain: it needs the person.

The window is the prime's window_s, else the session's prime_window_s, else PRIME_WINDOW_S (a KNOB).
"""
import datetime
import threading
import time

from cmod.custom import config_rows as R
from cmod.custom import measure_readings as MR

PRIME_WINDOW_S = 30.0   # KNOB: how long a primed step waits for the meter, unless the session or the prime says otherwise
POLL_SAMPLES = 4        # KNOB: lines per sigrok-cli run while listening
_LOCK = threading.RLock()
_LINES = {}             # prime name -> every line seen (kept in memory only: a stream is never stored; its sha256 is the evidence)
_THREADS = {}


def _now():
    return datetime.datetime.now(datetime.timezone.utc)


def _iso(t):
    return t.isoformat(timespec='microseconds')


def _session_step(manager, session, step):
    from cmod.custom import test_sessions as TS
    s = TS._session(manager, session)
    return s, TS._step_of(manager, s, step)


def primes(manager, session):
    return sorted(R.rows(manager, 'TestStepPrime', session=session), key=lambda p: p['armed_at'])


def _window(s, body):
    w = body.get('window_s')
    if w not in (None, ''):
        w = float(w)
    elif float(s.get('prime_window_s') or -1) > 0:
        w = float(s['prime_window_s'])
    else:
        w = PRIME_WINDOW_S
    if not 0 < w <= 600:
        raise R.ConfigRefused('the window is 0 < window_s <= 600 seconds, not %r' % w)
    return w


def prime(manager, session, step, body):
    from instruments.custom import sigrok_reader as SG
    s, st = _session_step(manager, session, step)
    if st['kind'] != 'measure':
        raise R.ConfigRefused('only a measure step is primed for a meter; a %s step is the person\'s (the sheet)' % st['kind'])
    with _LOCK:
        live = [p for p in primes(manager, session) if p['state'] == 'armed']
        if live:
            raise R.ConfigRefused('%s is already primed and waiting (one meter at a time): cancel it or let it finish' % live[0]['step'], status=409)
        ep = None
        if body.get('endpoint'):
            ep = R.get(manager, 'InstrumentEndpoint', str(body['endpoint']))
            if ep is None or ep.get('transport') != 'sigrok':
                raise R.ConfigRefused('no sigrok endpoint %r (POST /api/instruments/endpoints with transport sigrok)' % body['endpoint'], status=404)
            if not SG.capability()['available']:
                raise R.ConfigRefused(SG.capability()['why'], status=409)
            inst = ep['instrument']
        else:
            inst = str(body.get('instrument') or '')
            try:
                SG.driver_for(inst)
            except SG.SigrokRefused as e:
                raise R.ConfigRefused(e.why, status=e.status)
        w = _window(s, body)
        t = _now()
        n = len(R.rows(manager, 'TestStepPrime', session=session, step=st['name'])) + 1
        row = R.upsert(manager, 'TestStepPrime', '%s:%s#p%d' % (session, st['name'], n), session=session, step=st['name'], endpoint=ep['name'] if ep else '',
                       instrument=inst, source='endpoint' if ep else 'bridge', window_s=w, armed_at=_iso(t),
                       ends_at=_iso(t + datetime.timedelta(seconds=w)), state='armed', chain=body.get('chain') is True or str(body.get('chain') or '').strip().lower() in ('true', 'yes', '1', 'on'),
                       note='PRIMED: probe %s now - waiting up to %g s for the meter' % (st['words'].split(': ', 1)[-1][:80], w))
        _LINES[row['name']] = []
    if ep is not None:
        th = threading.Thread(target=_listen, args=(manager, row['name'], ep['resource']), daemon=True, name='prime-%s' % row['name'])
        _THREADS[row['name']] = th
        th.start()
    return row


def _listen(manager, name, resource):
    from instruments.custom import sigrok_reader as SG
    while True:
        p = R.get(manager, 'TestStepPrime', name)
        if p is None or p['state'] != 'armed':
            return
        left = (datetime.datetime.fromisoformat(p['ends_at']) - _now()).total_seconds()
        if left <= 0:
            finish(manager, name)
            return
        try:
            got = SG.read(resource, samples=POLL_SAMPLES, timeout=max(1.0, min(left, SG.TAKE_TIMEOUT_S)))
            lines = got['raw'].splitlines()
        except SG.SigrokRefused:
            lines = []
        if lines:
            feed(manager, name, lines)
        else:
            time.sleep(min(0.5, max(left, 0)))   # nothing yet (no device, the probe not on it): keep waiting to the end of the window


def _judged(manager, s, st, p, value):
    pt = R.get(manager, 'MeasurementPoint', st['point'])
    return MR.judge(manager, {'point': pt['name'], 'value': value, 'instrument': p['instrument'], 'range_max': -1.0, 'unit': s['unit'], 'hex_sha256': ''})


def _keep(manager, s, st, p, value, state, words):
    from instruments.custom import sigrok_reader as SG
    pt = R.get(manager, 'MeasurementPoint', st['point'])
    lines = _LINES.get(p['name'], [])
    r = MR.add_reading(manager, s['unit'], {'point': pt['name'], 'value': '%.9g %s' % (value, pt['si_unit']), 'via': 'usb-serial', 'instrument': p['instrument'],
                                            'who': s['who'], 'session': s['name'], 'step': st['name'], 'evidence_sha256': SG.evidence('\n'.join(lines)),
                                            'note': '%s (primed %s, %d lines)' % (words, p['name'], len(lines))})
    return R.upsert(manager, 'TestStepPrime', p['name'], state=state, reading=r['name'], lines_seen=len(lines), note=words)


def feed(manager, name, lines):
    from instruments.custom import sigrok_reader as SG
    with _LOCK:
        p = R.get(manager, 'TestStepPrime', name)
        if p is None:
            raise R.ConfigRefused('no primed step %r' % name, status=404)
        if p['state'] != 'armed':
            return p
        if _now() > datetime.datetime.fromisoformat(p['ends_at']):
            return finish(manager, name)
        _LINES.setdefault(name, []).extend(str(x) for x in lines)
        s, st = _session_step(manager, p['session'], p['step'])
        want = R.get(manager, 'MeasurementPoint', st['point'])['si_unit']
        samples = [x for x in map(SG.parse_line, _LINES[name]) if x and x['unit'] == want and 'AC' not in x['flags']]
        R.upsert(manager, 'TestStepPrime', name, lines_seen=len(_LINES[name]))
        if not samples:
            return R.get(manager, 'TestStepPrime', name)
        _b, _w, row = MR.band(manager, p['instrument'], 'V dc' if want == 'V' else 'I dc', samples[-1]['value'])
        value, _win = SG.steady(samples, float(row['resolution']) if row else 0.0)
        if value is None:
            return R.get(manager, 'TestStepPrime', name)
        j = _judged(manager, s, st, p, value)
        if j['verdict'] not in ('in-band', 'in-tolerance'):
            return R.get(manager, 'TestStepPrime', name)   # steady but not yet a correct build's value (an open probe reads 0): keep waiting
        out = _keep(manager, s, st, p, value, 'confirmed', 'CONFIRMED: the meter settled at %s (%s)' % (MR.fmt(value, want), j['verdict']))
    if p['chain']:
        _chain(manager, s, st, p)
    return out


def finish(manager, name):
    """The window ended: keep the last steady value (a fault reads steady too), or say why none came."""
    from instruments.custom import sigrok_reader as SG
    with _LOCK:
        p = R.get(manager, 'TestStepPrime', name)
        if p is None or p['state'] != 'armed':
            return p
        s, st = _session_step(manager, p['session'], p['step'])
        want = R.get(manager, 'MeasurementPoint', st['point'])['si_unit']
        parsed = [x for x in map(SG.parse_line, _LINES.get(name, [])) if x]
        right = [x for x in parsed if x['unit'] == want and 'AC' not in x['flags']]
        _b, _w, row = MR.band(manager, p['instrument'], 'V dc' if want == 'V' else 'I dc', right[-1]['value']) if right else (None, '', None)
        res = float(row['resolution']) if row else 0.0
        last = None
        for end in range(len(right), 2, -1):   # the LAST steady value seen in the window
            v, _w2 = SG.steady(right[:end], res)
            if v is not None:
                last = v
                break
        if last is not None:
            return _keep(manager, s, st, p, last, 'kept-last', 'THE WINDOW ENDED (%g s): the last steady value %s is kept and judged - nothing a correct build '
                                                                'reads settled before it' % (p['window_s'], MR.fmt(last, want)))
        if right:
            state, words = 'not-steady', 'NOT STEADY: %d lines in %s, never %d in a row within one count - hold the probes still' % (len(right), want, SG.STEADY_N)
        elif parsed:
            state, words = 'wrong-mode', 'WRONG MODE: the meter read %s; this step needs %s' % (', '.join(sorted({x['unit'] or '?' for x in parsed})), want)
        else:
            state, words = 'no-data', 'NO DATA CAME THROUGH in %g s: check the probe, the cable and the port - not the circuit' % p['window_s']
        return R.upsert(manager, 'TestStepPrime', name, state=state, lines_seen=len(_LINES.get(name, [])), note=words)


def _chain(manager, s, st, p):
    from cmod.custom import test_sessions as TS
    view = TS.sheet(manager, s['name'])
    nxt = view['next']
    if nxt is None or nxt['kind'] != 'measure':
        return None
    try:
        return prime(manager, s['name'], nxt['step'], {'endpoint': p['endpoint']} if p['endpoint'] else {'instrument': p['instrument']}
                     | {'window_s': p['window_s'], 'chain': True})
    except R.ConfigRefused:
        return None


def cancel(manager, name):
    with _LOCK:
        p = R.get(manager, 'TestStepPrime', name)
        if p is None:
            raise R.ConfigRefused('no primed step %r' % name, status=404)
        if p['state'] == 'armed':
            return R.upsert(manager, 'TestStepPrime', name, state='cancelled', note='cancelled by the person')
        return p


def settle(manager, session):
    """A Bridge prime has no thread: one past its window is finished when the sheet is read."""
    for p in primes(manager, session):
        if p['state'] == 'armed' and p['source'] == 'bridge' and _now() > datetime.datetime.fromisoformat(p['ends_at']):
            finish(manager, p['name'])
