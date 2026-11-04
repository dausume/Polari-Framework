"""
@module cmod.custom.test_sessions

msv-0b (AI-Notes/plans/MEASURED_VS_SIMULATED_PLAN.md section 5b): ONE PERSON WORKING THROUGH A FROZEN TestProcedure ON ONE BuiltUnit - the GUIDED
SHEET. A measure step is answered by an ordinary MeasurementReading (naming the session and the step), judged on read. Every other step is
answered by a TestStepMark. Nothing is edited: a later answer to the same step supersedes the earlier one.

  start(manager, unit, body)                 body {procedure, mode?: guided | touch, who?} -> the TestSession
  sessions(manager, unit)
  answer(manager, session, step, body)       measure: {value, instrument?, range_max?, who?, note?}; other steps: {outcome, who?, note?}
  resume(manager, session)                   the stimulus steps that put the board in the next step's node are asked again
  sheet(manager, session)                    -> {rows (one per step: what to do, what to expect, the answer, the verdict), summary, next}

Step verdicts:
  pass / fail     a continuity beep or none against the expectation, an observation yes / no, a reading in band
  unexplained     a reading outside the band (it goes to the ruling queue, msv-2)
  unjudged        a reading whose meter has no cited accuracy
  over-range      measure again on a larger range
  done / skipped  a setup or stimulus step
  pending         not answered; ask-again = a stimulus done before the last resume, so the board may not be in the node's state any more
Touch-and-confirm (mode touch) needs a live device path (msv-3). Until it exists every step falls back to the sheet, and the sheet says so.
"""
import datetime

from cmod.custom import config_rows as R
from cmod.custom import measure_readings as MR
from cmod.custom import test_procedures as TP

OUTCOMES = {'setup': ('done', 'skipped'), 'stimulus': ('done', 'skipped'), 'continuity': ('beep', 'no-beep', 'skipped'), 'observe': ('yes', 'no', 'skipped')}
_MEASURE = {'in-band': 'pass', 'unexplained': 'unexplained', 'unjudged': 'unjudged', 'over-range': 'over-range'}


def _now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='microseconds')


def _session(manager, session):
    s = R.get(manager, 'TestSession', session)
    if s is None:
        raise R.ConfigRefused('no test session %r' % session, status=404)
    return s


def start(manager, unit, body):
    u = R.get(manager, 'BuiltUnit', unit)
    if u is None:
        raise R.ConfigRefused('no built unit %r' % unit, status=404)
    p = R.get(manager, 'TestProcedure', str(body.get('procedure') or ''))
    if p is None:
        raise R.ConfigRefused('no test procedure %r (generate one first)' % body.get('procedure'), status=404)
    if p['bench_solution'] != u['bench_solution']:
        raise R.ConfigRefused('procedure %s is for %s; unit %s is a %s' % (p['name'], p['bench_solution'], unit, u['bench_solution']), status=409)
    mode = str(body.get('mode') or 'guided')
    if mode not in ('guided', 'touch'):
        raise R.ConfigRefused('mode is guided (the sheet) or touch (a device confirms each step), not %r' % mode)
    n = len([s for s in R.rows(manager, 'TestSession', unit=unit) if s['procedure'] == p['name']]) + 1
    note = ''
    if p['hex_sha256'] and u['hex_sha256'] and p['hex_sha256'] != u['hex_sha256']:
        note = 'the unit carries build %s.., the procedure is for %s..: its readings will be stale' % (u['hex_sha256'][:12], p['hex_sha256'][:12])
    return R.upsert(manager, 'TestSession', '%s-%s-t%d' % (unit, p['name'], n), unit=unit, procedure=p['name'], mode=mode, who=str(body.get('who') or ''),
                    state='open', at=_now(), notes=note)


def sessions(manager, unit):
    return sorted(R.rows(manager, 'TestSession', unit=unit), key=lambda s: s['at'])


def _step_of(manager, session, step):
    st = R.get(manager, 'TestProcedureStep', step)
    if st is None or st['procedure'] != session['procedure']:
        raise R.ConfigRefused('no step %r in procedure %s' % (step, session['procedure']), status=404)
    return st


def answer(manager, session, step, body):
    s = _session(manager, session)
    st = _step_of(manager, s, step)
    who = str(body.get('who') or s['who'])
    if st['kind'] == 'measure':
        if str(body.get('outcome') or '') == 'skipped':
            out = _mark(manager, s, st, 'skipped', who, body)
        else:
            out = MR.add_reading(manager, s['unit'], dict(body, point=st['point'], session=s['name'], step=st['name'], who=who))
    else:
        outcome = str(body.get('outcome') or '')
        if outcome not in OUTCOMES[st['kind']]:
            raise R.ConfigRefused('a %s step is answered %s, not %r' % (st['kind'], ' | '.join(OUTCOMES[st['kind']]), outcome))
        out = _mark(manager, s, st, outcome, who, body)
    view = sheet(manager, session)
    if view['next'] is None and s['state'] != 'done':
        R.upsert(manager, 'TestSession', session, state='done')
    return dict(out, verdict=next(r['verdict'] for r in view['rows'] if r['step'] == st['name']))


def _mark(manager, s, st, outcome, who, body):
    n = len(R.rows(manager, 'TestStepMark', session=s['name'], step=st['name'])) + 1
    return R.upsert(manager, 'TestStepMark', '%s:%s#m%d' % (s['name'], st['name'], n), session=s['name'], step=st['name'], outcome=outcome, who=who, at=_now(),
                    note=str(body.get('note') or ''))


def resume(manager, session):
    _session(manager, session)
    R.upsert(manager, 'TestSession', session, state='open', resumed_at=_now())
    return sheet(manager, session)


def _latest(rows):
    return max(rows, key=lambda r: (r['at'], len(r['name']), r['name'])) if rows else None


def _verdict(st, mark, reading):
    if st['kind'] == 'measure':
        if reading is not None and (mark is None or reading['at'] >= mark['at']):
            return _MEASURE[reading['verdict']]
        return 'skipped' if mark is not None else 'pending'
    if mark is None:
        return 'pending'
    if mark['outcome'] == 'skipped':
        return 'skipped'
    if st['kind'] == 'continuity':
        want = 'no-beep' if st['expect'].startswith('NO') else 'beep'
        return 'pass' if mark['outcome'] == want else 'fail'
    if st['kind'] == 'observe':
        return 'pass' if mark['outcome'] == 'yes' else 'fail'
    return 'done'


def sheet(manager, session):
    s = _session(manager, session)
    marks = R.rows(manager, 'TestStepMark', session=session)
    reads = [dict(r, **MR.judge(manager, r)) for r in R.rows(manager, 'MeasurementReading', session=session)]
    rows = []
    for st in TP.steps(manager, s['procedure']):
        mark = _latest([m for m in marks if m['step'] == st['name']])
        reading = _latest([r for r in reads if r['step'] == st['name']])
        v = _verdict(st, mark, reading)
        answered = reading if (st['kind'] == 'measure' and reading is not None and v not in ('pending', 'skipped')) else mark
        rows.append({'order': int(st['order']), 'step': st['name'], 'kind': st['kind'], 'node': st['node'], 'words': st['words'], 'expect': st['expect'],
                     'mode': st['mode'], 'answer': (answered or {}).get('entered') or (answered or {}).get('outcome') or '', 'verdict': v,
                     'judged': reading['words'] if (reading is not None and st['kind'] == 'measure') else '', 'at': (answered or {}).get('at', ''),
                     'ask_again': False, 'how': 'the sheet' if s['mode'] == 'guided' else 'the sheet (touch and confirm needs a live device path: msv-3, not built)',
                     'note': (answered or {}).get('note', '')})
    nxt = next((r for r in rows if r['verdict'] == 'pending'), None)
    if nxt is not None and s.get('resumed_at') and nxt['kind'] in ('measure', 'observe'):
        # put the board back in the node's state: the stimulus steps since the last RESET before the next step, done before the resume
        i = nxt['order'] - 1
        j = i
        while j > 0 and not (rows[j - 1]['kind'] == 'stimulus' and 'RESET' in rows[j - 1]['words']) and rows[j - 1]['kind'] in ('stimulus', 'measure', 'observe'):
            j -= 1
        for r in rows[max(j - 1, 0):i]:
            if r['kind'] == 'stimulus' and r['at'] and r['at'] < s['resumed_at']:
                r['ask_again'] = True
                r['verdict'] = 'pending'
        nxt = next((r for r in rows if r['verdict'] == 'pending'), nxt)
    summary = {}
    for r in rows:
        summary[r['verdict']] = summary.get(r['verdict'], 0) + 1
    return {'session': session, 'unit': s['unit'], 'procedure': s['procedure'], 'mode': s['mode'], 'state': s['state'], 'rows': rows,
            'summary': summary, 'summary_rows': [{'verdict': k, 'steps': v} for k, v in sorted(summary.items())], 'next': nxt}
