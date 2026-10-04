"""
@module firmwarefaults.custom.outcome_sc3

THE sc-3 DECISIONS (pure functions over a parsed C3 trace + the decoded telemetry; selftest-pinned on fixture traces):

  decide_inversion(d, bound_us, slack_us)   h-blocking-bounded — H's worst wait for R (the firmware's @ROUND t_acq − t_req, the
      trace's BLOCK → TAKE beside it) against the bound = L's critical section + one tick of slack:
        worst > bound + slack → failed (the inversion happened; the words say who ran in H's worst wait and for how long)
        every round done and worst ≤ bound + slack → passed (inheritance events counted)
        rounds missing → undetermined (the window ran out)
  decide_deadlock(d, wf, telemetry, end_us)  wait-for-acyclic — the wait-for graph rebuilt from the hooks (c3_trace.wait_for):
        a cycle that PERSISTS to the end → failed (the cycle, the µs/tick it closed, both tasks Blocked, the app's own @DEADLOCK
        beside it, the last telemetry frame — the observable a host sees); every round done and no persistent cycle → passed
        (transient cycles broken by a timeout are reported); neither → undetermined.
"""
from firmwarefaults.custom import c3_trace as C

TICK_US = 1000


def _fmt_ran(ran):
    return ', '.join('%s %d µs' % (k, v) for k, v in sorted(ran.items(), key=lambda kv: -kv[1]))


def decide_inversion(d, bound_us, slack_us=TICK_US):
    pi = d.get('pi') or {}
    rounds = d.get('rounds') or []
    want = int(pi.get('of', 0) or (d.get('boot') or {}).get('rounds', 0) or 0)
    if not rounds:
        return {'outcome': 'undetermined', 'words': 'no round completed in the window (H never got R)', 'value': '', 'worst_us': 0}
    worst = max(r['block_us'] for r in rounds)
    wr = max(rounds, key=lambda r: r['block_us'])
    blk = C.blocked(d, 'H', 'R')
    at = min(blk, key=lambda b: abs(b['from_us'] - wr['req_us'])) if blk else {}
    m_in = (at.get('ran') or {}).get('M', 0)
    inh = sum(1 for e in d['events'] if e[1] == C.INHERIT)
    lim = bound_us + slack_us
    value = 'H worst wait %d µs vs bound %d µs (L\'s section %d + %d slack)' % (worst, lim, bound_us, slack_us)
    base = dict(worst_us=worst, worst_round=wr['round'], worst_req_us=wr['req_us'], m_inside_us=m_in, inherit_events=inh,
                ran_in_worst=at.get('ran') or {}, rounds_done=len(rounds), rounds_wanted=want, value=value)
    if worst > lim:
        return dict(base, outcome='failed', words=('PRIORITY INVERSION: H waited %d µs for R in round %d (asked at %d µs) — %d µs over the '
                                                     'bound (L\'s %d µs section + %d µs slack); while H waited, %s ran (M %d µs of it); %d '
                                                     'inheritance event(s)' % (worst, wr['round'], wr['req_us'], worst - lim, bound_us, slack_us,
                                                                                _fmt_ran(at.get('ran') or {}) or 'unknown', m_in, inh)))
    if want and len(rounds) < want:
        return dict(base, outcome='undetermined', words='%d of %d rounds in the window; worst so far %d µs' % (len(rounds), want, worst))
    return dict(base, outcome='passed', words=('H\'s worst wait %d µs ≤ %d µs (L\'s section + one tick) over %d rounds; %d inheritance '
                                                'event(s) (L raised to H\'s priority while H waited); M inside H\'s worst wait: %d µs'
                                                % (worst, lim, len(rounds), inh, m_in)))


def telemetry_stop(telemetry, end_us):
    """(last frame's uptime ms, silent ms to the end of the window) — the host's view."""
    if not telemetry:
        return None, None
    last = telemetry[-1]['uptime_ms']
    return last, (end_us / 1000.0 - last) if end_us else None


def decide_deadlock(d, wf, telemetry, end_us):
    ll = d.get('locks_line') or {}
    rounds = str(ll.get('rounds', '0,0')).split(',')
    done = [int(x) for x in rounds if x.isdigit()]
    want = int(ll.get('of', 0) or (d.get('boot') or {}).get('rounds', 0) or 0)
    last, silent = telemetry_stop(telemetry, end_us)
    pers = wf.get('persistent')
    dl = d.get('deadlock') or {}
    base = dict(rounds_done=done, rounds_wanted=want, backoffs=ll.get('backoffs'), transient=wf.get('transient') or [], first_cycle=wf.get('first_cycle'),
                last_frame_ms=last, silent_ms=silent, app_deadlock=dl)
    if pers:
        cyc = ' → '.join(pers['cycle'])
        value = 'cycle %s at %d µs (tick %d)' % (cyc, pers['t_us'], pers['t_us'] // TICK_US)
        return dict(base, outcome='failed', value=value, cycle_us=pers['t_us'],
                    words=('DEADLOCK: the wait-for graph closed %s at %d µs (tick %d) and never opened again; at the end T1 waits %s, T2 waits %s '
                           '(holders %s); the firmware\'s monitor declared it at %s µs (both Blocked); rounds done %s of %d; telemetry\'s last frame '
                           'at %s ms, then silence for %s ms to the window\'s end' % (
                               cyc, pers['t_us'], pers['t_us'] // TICK_US, wf['waits'].get('T1', '-'), wf['waits'].get('T2', '-'), wf['holders'],
                               dl.get('detected_us', '—'), ','.join(map(str, done)), want, last, None if silent is None else round(silent, 1))))
    if want and len(done) == 2 and min(done) >= want:
        tr = wf.get('transient') or []
        return dict(base, outcome='passed', value='all %d rounds on both tasks; %d transient cycle(s); back-offs %s' % (want, len(tr), ll.get('backoffs', '0,0')),
                    words=('progress: T1 and T2 each completed %d rounds; no cycle persisted in the wait-for graph%s; back-offs %s; telemetry\'s last '
                           'frame at %s ms' % (want, ('' if not tr else ' (%d transient cycle(s), each broken by a timed take: first %s at %d µs, '
                                                      'broken at %d µs)' % (len(tr), ' → '.join(tr[0]['cycle']), tr[0]['t_us'], tr[0]['broken_at_us'])),
                                               ll.get('backoffs', '0,0'), last)))
    return dict(base, outcome='undetermined', value='rounds %s of %d, no persistent cycle' % (','.join(map(str, done)), want),
                words='no persistent cycle, but rounds %s of %d completed in the window' % (','.join(map(str, done)), want))
