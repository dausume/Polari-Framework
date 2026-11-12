"""
@module cmod.custom.variance_rulings

msv-2 (AI-Notes/plans/MEASURED_VS_SIMULATED_PLAN.md sections 2 and 4): A PERSON RULES ON WHAT THE SIMULATION DOES NOT EXPLAIN - "acceptable variance
vs mistakes, recorded" (the user, 2026-11-04). The ruling is the person's; the fault ranking (cmod.custom.fault_signatures) is kept beside it as
evidence, never in its place.

  rule(manager, unit, body)        body {reading, ruling, words, who, cause? (a mistake's), scope? (an accepted variance's: unit | design | lot),
                                   evidence_sha256?} -> the VarianceRuling + the reading's standing
  rework(manager, unit, body)      body {ruling, words, who} -> a VarianceRulingRework on a mistake (it does not close it)
  rulings(manager, unit)           the unit's rulings, each with its state (in-force / superseded; a mistake open / closed) and reworks
  standing(manager, reading, j)    -> {standing, counts, ruling, ruled, covered_by, closed_by, standing_words} - DERIVED on read, never stored
  queue(manager, unit)             the readings that need a person + the open mistakes + the fault ranking

The rules:
- accepted-variance only on an UNEXPLAINED reading (an in-band one needs nothing). Scope: this unit by default (D-msv-3); "design" or "lot" only when
  said, and "lot" only on a unit whose part_lot is given. It covers a later reading of the same point, on the same build, within ACCEPT_WINDOW of the
  value ruled - a reading that has moved further is a new question.
- mistake on any reading (a person may find a wrong part that still reads in tolerance), with a cause. It is CLOSED only by a later reading of the same
  point on the same unit that counts (in band, or in tolerance with a cited meter); the rework goes in between. Until then it blocks the node's
  hardware confirmation (D-msv-5, msv-5).
- measurement-error on any reading: the reading does not count; measure again.
- No ruling on a STALE reading (another build): measure it again on this one.
"""
import datetime

from cmod.custom import config_rows as R

RULINGS = ('accepted-variance', 'mistake', 'measurement-error')
CAUSES = ('cold-joint', 'bridge', 'open', 'wrong-part-value', 'reversed-polarity', 'wrong-pin', 'damaged-part', 'other')
SCOPES = ('unit', 'design', 'lot')
ACCEPT_WINDOW = {'V': 0.02, 'A': 20e-6}   # KNOB: how near the value ruled a later reading must sit to be covered (or its instrument band, if wider)


def _now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='microseconds')


def _n(name):
    try:
        return int(name.rsplit('-rule', 1)[1])
    except (IndexError, ValueError):
        return 0


def of_reading(manager, reading):
    return sorted(R.rows(manager, 'VarianceRuling', reading=reading), key=lambda v: _n(v['name']))


def in_force(manager, reading):
    got = of_reading(manager, reading)
    return got[-1] if got else None


def _counts_verdict(j):
    return j['verdict'] == 'in-band' or (j['verdict'] == 'in-tolerance' and j.get('band') is not None)


def _reading_of(manager, unit, name):
    r = R.get(manager, 'MeasurementReading', str(name or ''))
    if r is None or r['unit'] != unit:
        raise R.ConfigRefused('no reading %r on unit %s' % (name, unit), status=404)
    return r


def rule(manager, unit, body):
    from cmod.custom import measure_readings as MR
    u = R.get(manager, 'BuiltUnit', unit)
    if u is None:
        raise R.ConfigRefused('no built unit %r' % unit, status=404)
    r = _reading_of(manager, unit, body.get('reading'))
    ruling = str(body.get('ruling') or '')
    if ruling not in RULINGS:
        raise R.ConfigRefused('ruling is %s, not %r' % (' | '.join(RULINGS), ruling))
    words, who = str(body.get('words') or '').strip(), str(body.get('who') or '').strip()
    if not words or not who:
        raise R.ConfigRefused('a ruling carries who made it and why, in words (who, words)')
    j = MR.judge(manager, r)
    if j['stale']:
        raise R.ConfigRefused('the reading was taken on another build (stale): measure it again on this one before ruling', status=409)
    cause, scope, lot = '', 'unit', ''
    if ruling == 'accepted-variance':
        if j['verdict'] != 'unexplained':
            raise R.ConfigRefused('only an unexplained reading is accepted as variance; this one is %s' % j['verdict'], status=409)
        scope = str(body.get('scope') or 'unit')
        if scope not in SCOPES:
            raise R.ConfigRefused('scope is %s, not %r' % (' | '.join(SCOPES), scope))
        if scope == 'lot':
            lot = u.get('part_lot') or ''
            if not lot:
                raise R.ConfigRefused('unit %s has no part_lot: say the lot on the unit before scoping a variance to it' % unit, status=409)
    elif ruling == 'mistake':
        cause = str(body.get('cause') or '')
        if cause not in CAUSES:
            raise R.ConfigRefused('a mistake has a cause: %s, not %r' % (' | '.join(CAUSES), cause))
    suggested = ''
    if ruling != 'measurement-error':
        try:
            from cmod.custom import fault_signatures as FS
            got = FS.rank(manager, unit, top=1)
            suggested = got['ranked'][0]['words'] if got['ranked'] else ''
        except R.ConfigRefused:
            suggested = ''
    n = len(of_reading(manager, r['name'])) + 1
    row = R.upsert(manager, 'VarianceRuling', '%s-rule%d' % (r['name'], n), reading=r['name'], unit=unit, point=r['point'], ruling=ruling, cause=cause,
                   scope=scope, part_lot=lot, value=float(r['value']), hex_sha256=r.get('hex_sha256') or '', who=who, words=words,
                   evidence_sha256=str(body.get('evidence_sha256') or ''), suggested=suggested, at=_now())
    return dict(row, **standing(manager, r, j))


def rework(manager, unit, body):
    v = R.get(manager, 'VarianceRuling', str(body.get('ruling') or ''))
    if v is None or v['unit'] != unit:
        raise R.ConfigRefused('no ruling %r on unit %s' % (body.get('ruling'), unit), status=404)
    if v['ruling'] != 'mistake':
        raise R.ConfigRefused('rework goes on a mistake; %s is %s' % (v['name'], v['ruling']), status=409)
    words, who = str(body.get('words') or '').strip(), str(body.get('who') or '').strip()
    if not words or not who:
        raise R.ConfigRefused('rework says what was done and who did it (words, who)')
    n = len(R.rows(manager, 'VarianceRulingRework', ruling=v['name'])) + 1
    return R.upsert(manager, 'VarianceRulingRework', '%s#w%d' % (v['name'], n), ruling=v['name'], who=who, words=words, at=_now())


def _closed_by(manager, v):
    """A mistake is closed by the first later reading of its point on its unit that counts."""
    from cmod.custom import measure_readings as MR
    ruled = R.get(manager, 'MeasurementReading', v['reading']) or {}
    later = sorted((x for x in R.rows(manager, 'MeasurementReading', unit=v['unit']) if x['point'] == v['point'] and x['name'] != v['reading']
                    and (x['at'], len(x['name']), x['name']) > (ruled.get('at', ''), len(ruled.get('name', '')), ruled.get('name', ''))),
                   key=lambda x: (x['at'], len(x['name']), x['name']))
    for x in later:
        if _counts_verdict(MR.judge(manager, x)):
            return x
    return None


def _covering(manager, r, j):
    u = R.get(manager, 'BuiltUnit', r['unit']) or {}
    p = R.get(manager, 'MeasurementPoint', r['point']) or {}
    win = max(j.get('band') or 0.0, ACCEPT_WINDOW.get(p.get('si_unit', 'V'), 0.0))
    for v in sorted(R.rows(manager, 'VarianceRuling', point=r['point']), key=lambda v: v['at'], reverse=True):
        if v['ruling'] != 'accepted-variance' or v['reading'] == r['name'] or in_force(manager, v['reading'])['name'] != v['name']:
            continue
        if v['hex_sha256'] != (r.get('hex_sha256') or ''):
            continue
        if v['scope'] == 'unit' and v['unit'] != r['unit']:
            continue
        if v['scope'] == 'lot' and v['part_lot'] != (u.get('part_lot') or ''):
            continue
        if abs(float(r['value']) - float(v['value'])) <= win:
            return v
    return None


def standing(manager, r, j):
    own = in_force(manager, r['name'])
    out = {'ruling': own['name'] if own else '', 'ruled': own['ruling'] if own else '', 'covered_by': '', 'closed_by': ''}
    if own and own['ruling'] == 'measurement-error':
        return dict(out, standing='re-measure', counts=False, standing_words='ruled a measurement error by %s (%s): measure it again' % (own['who'], own['words']))
    if own and own['ruling'] == 'mistake':
        c = _closed_by(manager, own)
        if c is not None:
            return dict(out, standing='mistake-closed', counts=False, closed_by=c['name'],
                        standing_words='a mistake (%s), closed: %s read in band after the rework' % (own['cause'], c['name'].split('#')[-1]))
        return dict(out, standing='mistake-open', counts=False,
                    standing_words='an OPEN mistake (%s) by %s: %s - rework it, then measure the point again' % (own['cause'], own['who'], own['words']))
    if own and own['ruling'] == 'accepted-variance':
        return dict(out, standing='accepted', counts=True, standing_words='accepted variance (%s scope) by %s: %s' % (own['scope'], own['who'], own['words']))
    if _counts_verdict(j):
        return dict(out, standing='counts', counts=True, standing_words='counts: %s' % j['verdict'])
    if j['verdict'] == 'unexplained':
        cov = _covering(manager, r, j)
        if cov is not None:
            return dict(out, standing='accepted', counts=True, covered_by=cov['name'],
                        standing_words='covered by %s\'s accepted variance (%s scope, %s): %s' % (cov['reading'].split(':')[-1], cov['scope'], cov['who'], cov['words']))
        return dict(out, standing='needs-ruling', counts=False, standing_words='needs a ruling: accepted variance, mistake or measurement error')
    if j['verdict'] == 'over-range':
        return dict(out, standing='re-measure', counts=False, standing_words='over range: measure it again on a larger range')
    return dict(out, standing=j['verdict'], counts=False,
                standing_words={'unjudged': 'not counted: the meter has no cited accuracy here',
                                'in-tolerance': 'in tolerance, but not counted: the meter\'s accuracy is not cited'}.get(j['verdict'], j['verdict']))


def rulings(manager, unit):
    if R.get(manager, 'BuiltUnit', unit) is None:
        raise R.ConfigRefused('no built unit %r' % unit, status=404)
    out = []
    for v in sorted(R.rows(manager, 'VarianceRuling', unit=unit), key=lambda v: v['at'], reverse=True):
        force = in_force(manager, v['reading'])['name'] == v['name']
        c = _closed_by(manager, v) if v['ruling'] == 'mistake' else None
        state = 'superseded' if not force else ('closed' if c is not None else 'open') if v['ruling'] == 'mistake' else 'in-force'
        works = sorted(R.rows(manager, 'VarianceRulingRework', ruling=v['name']), key=lambda w: w['at'])
        out.append(dict(v, state=state, closed_by=c['name'] if c else '', rework='; '.join('%s (%s)' % (w['words'], w['who']) for w in works), reworks=len(works)))
    return out


def queue(manager, unit):
    """What needs a person on this unit, with the fault ranking when anything is unexplained or a mistake is open."""
    from cmod.custom import fault_signatures as FS
    from cmod.custom import measure_readings as MR
    rows = [r for r in MR.readings(manager, unit) if r['current'] and r['standing'] in ('needs-ruling', 're-measure', 'mistake-open')]
    opened = [v for v in rulings(manager, unit) if v['state'] == 'open']
    ranking = FS.rank(manager, unit) if rows or opened else None
    return {'unit': unit, 'waiting': [{'reading': r['name'], 'point': r['point'], 'value': r['value'], 'entered': r['entered'], 'verdict': r['verdict'],
                                       'standing': r['standing'], 'words': r['standing_words']} for r in rows],
            'open_mistakes': [{'ruling': v['name'], 'point': v['point'], 'cause': v['cause'], 'words': v['words'], 'rework': v['rework']} for v in opened],
            'ranking': ranking, 'words': ('nothing waits for a person' if not rows and not opened else
                                          '%d reading(s) wait for a person, %d mistake(s) open' % (len(rows), len(opened)))}
