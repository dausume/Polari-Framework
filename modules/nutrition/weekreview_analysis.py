"""
@cross-cutting
@module nutrition.weekreview_analysis
@tags @xc:bindings

N5 — the WEEKLY REVIEW (HOUSEHOLD_APP_PAGES.md §3.6), composed from
the analyses that already exist — nothing is re-derived here:

  week_review                 planned vs eaten (planning_analysis.
                              week_coverage × IntakeRecord rows in the
                              week), the per-person "consistently"
                              readings (tracking_periods.period_summary),
                              cost vs budget (budget_analysis.
                              plan_budget_report), waste (waste_analysis.
                              waste_report, windowed to the week),
                              fairness (household.household_analysis.
                              fairness_readout, windowed) and next
                              week's proposals — one flat payload:
                              headline scalars + `lines` records
                              (section, subject, text, number, unit,
                              basis) + `proposals` records + `honesty`
                              records naming every prior used. A
                              section with no rows says "no data".
  next_week_proposals         the CalendarEvent proposals for the week
                              after the reviewed one: the weekly
                              purchase (purchase_analysis.
                              weekly_purchase_proposal), the bulk buys
                              whose cadence day (the 1st) falls in that
                              week (bulk_purchase_proposal) and the next
                              Sunday review — what the "Accept next
                              week's proposals" form writes.
  weekly_review_event_proposal
                              ONE CalendarEvent proposal (category
                              'review', Sunday REVIEW_TIME — a knob)
                              carrying the headline as its payload —
                              what the Sunday trigger generates.

Every number is a labelled prior or derived from rows; readings stay
comfort readings ("consistently above your line"), never diagnosis.

@consumers
  - nutrition.weekreview_api (GET /api/mealplanning/review)
  - nutrition.weekreview_seed (analyses / solutions / the page)
  - nutrition.selftest_weekreview
@see AI-Notes/designs/HOUSEHOLD_APP_PAGES.md §3.6
"""

from datetime import date, datetime, timedelta
from types import SimpleNamespace

from household.household_analysis import fairness_readout
from nutrition.budget_analysis import plan_budget_report
from nutrition.person_analysis import _rows
from nutrition.planning_analysis import _named, week_coverage
from nutrition.purchase_analysis import (
    bulk_purchase_proposal, weekly_purchase_proposal,
)
from nutrition.purchase_basis import BULK_CADENCES
from nutrition.tracking_periods import period_summary
from nutrition.waste_analysis import waste_report

PLAN = 'demo-alex-week'
HOUSEHOLD = 'demo-household'
#: The Sunday review hour — a prior (the trigger runs at 17:00 and
#: proposes the 18:00 sit-down; both are knobs on their rows).
REVIEW_TIME = '18:00'
REVIEW_MINUTES = 45
#: Bulk cadences count from September (calendar_seed's bulk triggers
#: start 2026-09-01) unless the trigger rows on the node say otherwise.
BULK_ANCHOR_MONTH = 9
SECTIONS = ('coverage', 'intake', 'cost', 'waste', 'fairness', 'proposals')

#: The priors this review leans on, named once, listed in `honesty`.
PRIORS = [
    ('review window', 'week_start given → that Monday-start week; blank → the plan\'s '
                      'own days (start_date .. start_date + days − 1)'),
    ('planned vs eaten', 'a planned cell counts as eaten when an IntakeRecord for the '
                         'same person × date × slot exists; an intake with no planned '
                         'cell is "eaten unplanned" — nothing is inferred from silence'),
    ('expected slots', 'each person\'s eating pattern (default 3-meal when unstated) — '
                       'planning_analysis.week_coverage'),
    ('consistently', 'tracking_periods.period_summary: means per LOGGED day vs the '
                     'person\'s own lines; < 3 logged days = low-confidence; '
                     '"consistently" needs ≥ half the well-logged weeks flagged'),
    ('cost', 'budget_analysis.plan_budget_report: observed prices × approximate '
             'weights; unpriced foods named, never costed at zero'),
    ('waste', 'waste_analysis.waste_report windowed to the week: grams via the unit '
              'weight priors, $ only where a price was observed'),
    ('fairness', 'household.household_analysis.fairness_readout windowed to the week: '
                 'WorkLedger actuals vs the policies\' shares; a suggestion, never a '
                 'reassignment'),
    ('next week', 'the Monday-start week after the reviewed one; purchase_analysis.'
                  'weekly_purchase_proposal on the Saturday before it (10:00 prior) + '
                  'bulk_purchase_proposal for cadences whose 1st falls in the week '
                  '(cadences count from the bulk triggers\' rangeStart month)'),
    ('review time', f'Sunday {REVIEW_TIME} for {REVIEW_MINUTES} min — a prior; the '
                    f'trigger row and the review_time param are the knobs'),
]


# ----------------------------------------------------------------
# helpers
# ----------------------------------------------------------------

def _date(value, default=None):
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value)[:10])
    except (TypeError, ValueError):
        return default


def _line(section, subject, text, number=None, unit='', basis=''):
    return {'section': section, 'subject': subject, 'text': text,
            'number': number, 'unit': unit, 'basis': basis}


def _no_data(section, what, how):
    return _line(section, 'no data', f'no {what} for this week — {how}', None, '',
                 'nothing is invented from missing rows')


def _plan_row(manager, plan):
    return plan if not isinstance(plan, str) else _named(manager, 'MealPlanDefinition', plan)


def _window(plan_row, week_start):
    """(start, end) dates of the reviewed week."""
    ws = _date(week_start) if week_start else None
    if ws is not None:
        start = ws - timedelta(days=ws.weekday())        # Monday of that week
        return start, start + timedelta(days=6)
    if plan_row is not None:
        start = _date(getattr(plan_row, 'start_date', ''))
        if start is not None:
            days = int(getattr(plan_row, 'days', 0) or 0) or 7
            return start, start + timedelta(days=days - 1)
    today = date.today()
    start = today - timedelta(days=today.weekday())
    return start, start + timedelta(days=6)


def _members(manager, household, plan_row):
    people = [getattr(m, 'person_name', '') for m in _rows(manager, 'HouseholdMember')
              if getattr(m, 'household_name', '') == household]
    if not people and plan_row is not None:
        people = [getattr(plan_row, 'person_name', '')]
    return [p for p in people if p]


def _windowed(manager, class_name, start, end, field='date'):
    """A read-only VIEW of the manager whose `class_name` rows fall in
    [start, end] — so the household-wide analyses answer for the week."""
    tables = dict(getattr(manager, 'objectTables', {}) or {})
    rows = {k: r for k, r in (tables.get(class_name, {}) or {}).items()
            if start.isoformat() <= str(getattr(r, field, ''))[:10] <= end.isoformat()}
    tables[class_name] = rows
    return SimpleNamespace(objectTables=tables, db=getattr(manager, 'db', None))


def _bulk_anchor_month(manager, cadence):
    """The month a bulk cadence counts from: the seeded bulk trigger's
    rangeStart (calendar_seed: 2026-09-01 → September) when the row is
    on the node, else BULK_ANCHOR_MONTH — so "due this week" agrees
    with what the schedule triggers would fire."""
    import json as _json
    for t in _rows(manager, 'EventTrigger'):
        if getattr(t, 'solution_name', '') != 'mealplan-bulk-purchase-events':
            continue
        try:
            sched = (_json.loads(getattr(t, 'source_json', '') or '{}') or {}).get('schedule') or {}
        except ValueError:
            continue
        if int(sched.get('interval', 0) or 0) == cadence and sched.get('rangeStart'):
            d = _date(sched['rangeStart'])
            if d is not None:
                return d.month
    return BULK_ANCHOR_MONTH


def _pct(part, whole):
    return round(part / whole * 100.0, 1) if whole else None


def _plus(iso_dt, minutes):
    return (datetime.fromisoformat(iso_dt) + timedelta(minutes=minutes)).isoformat(timespec='minutes')


# ----------------------------------------------------------------
# sections
# ----------------------------------------------------------------

def _coverage_section(manager, plan_row, members, start, end):
    lines, stats = [], {'expected': 0, 'planned': 0, 'eaten': 0, 'plannedEaten': 0,
                        'unplannedEaten': 0}
    intakes = {}
    for r in _rows(manager, 'IntakeRecord'):
        d = str(getattr(r, 'date', ''))[:10]
        p = getattr(r, 'person_name', '')
        if start.isoformat() <= d <= end.isoformat() and (not members or p in members):
            intakes[(p, d, getattr(r, 'slot', ''))] = getattr(r, 'template_name', '')
    stats['eaten'] = len(intakes)
    planned_keys = set()
    if plan_row is None:
        lines.append(_no_data('coverage', 'plan', 'no MealPlanDefinition of that name; the '
                              'intake rows are still counted below'))
    else:
        cov = week_coverage(manager, plan_row)
        cells = [c for c in cov.get('grid', [])
                 if not c['date'] or start.isoformat() <= c['date'] <= end.isoformat()]
        per_person = {}
        for c in cells:
            pp = per_person.setdefault(c['person'], {'expected': 0, 'planned': 0, 'eaten': 0})
            pp['expected'] += 1
            if c['status'] == 'planned':
                pp['planned'] += 1
                planned_keys.add((c['person'], c['date'], c['slot']))
                if (c['person'], c['date'], c['slot']) in intakes:
                    pp['eaten'] += 1
        stats['expected'] = len(cells)
        stats['planned'] = len(planned_keys)
        stats['plannedEaten'] = sum(pp['eaten'] for pp in per_person.values())
        if not cells:
            lines.append(_no_data('coverage', 'planned meals', 'the plan\'s days do not '
                                  'overlap the reviewed week'))
        for person, pp in per_person.items():
            lines.append(_line('coverage', person,
                               f'{pp["planned"]} of {pp["expected"]} expected meals planned; '
                               f'{pp["eaten"]} of the planned ones logged as eaten',
                               _pct(pp['planned'], pp['expected']), '% planned',
                               'week_coverage grid × IntakeRecord rows (person × date × slot)'))
        missing = [m for m in cov.get('missing', [])
                   if not m['date'] or start.isoformat() <= m['date'] <= end.isoformat()]
        for m in missing[:12]:
            lines.append(_line('coverage', m['person'], f'{m["slot"]} on {m["date"] or "day " + str(m["day"])} '
                               f'was not planned', None, '', 'week_coverage.missing'))
        if len(missing) > 12:
            lines.append(_line('coverage', 'missing', f'… and {len(missing) - 12} more unplanned slots',
                               len(missing), 'slots', 'week_coverage.missing'))
    unplanned = [(k, t) for k, t in intakes.items() if k not in planned_keys]
    stats['unplannedEaten'] = len(unplanned)
    for (p, d, slot), template in sorted(unplanned)[:8]:
        lines.append(_line('coverage', p, f'ate {template or "something"} at {slot} on {d} — '
                           f'not on the plan', None, '', 'IntakeRecord with no planned cell'))
    if not intakes:
        lines.append(_no_data('coverage', 'intake logged', 'log what was eaten (the "Log what '
                              'I ate" form) and planned-vs-eaten fills'))
    return lines, stats


def _intake_section(manager, members, start, end):
    lines, consistently = [], []
    if not members:
        return [_no_data('intake', 'household members', 'add HouseholdMember rows')], consistently
    for person in members:
        ps = period_summary(manager, person, 'week', start.isoformat(), end.isoformat())
        if not ps.get('ok') or not ps.get('periods'):
            lines.append(_no_data('intake', f'logged days for {person}',
                                  'nothing logged in the week — means are per LOGGED day, '
                                  'gap days never count as zero'))
            continue
        p = ps['periods'][-1]
        conf = 'low-confidence (< 3 logged days)' if p['lowConfidence'] else 'well-logged'
        lines.append(_line('intake', person,
                           f'{p["daysLogged"]} logged day(s) in the window — {conf}; '
                           f'mean {p["caloriesMean"]} kcal/day, protein {p["proteinMean"]} g, '
                           f'sodium {p["sodiumMean"]} mg',
                           p['caloriesMean'], 'kcal/day (mean)',
                           'period_summary week bucket, means per logged day'))
        for v in p.get('verdicts', []):
            lines.append(_line('intake', person, f'{v["direction"]}: {v["metric"]} — {v["reading"]} '
                               f'(this week {v["value"]} vs your line {v["line"]})',
                               v['value'], v['metric'], 'the person\'s own line'))
        # the "consistently" readings need history: read the whole
        # logged span, not just this week.
        hist = period_summary(manager, person, 'week')
        for c in (hist.get('consistency') or []):
            if c.get('consistent'):
                consistently.append(f'{person}: {c["reading"]}')
                lines.append(_line('intake', person, c['reading'], c['share'], 'share of '
                                   'well-logged weeks', 'period_summary.consistency'))
    if not consistently:
        lines.append(_line('intake', 'consistently', 'no reading is a pattern yet — a pattern '
                           'needs ≥ half the well-logged weeks flagged', None, '',
                           'period_summary.consistency'))
    return lines, consistently


def _cost_section(manager, plan_row, today):
    lines = []
    out = {'costEstimate': None, 'budget': None, 'budgetDeltaText': 'no data'}
    if plan_row is None:
        return [_no_data('cost', 'plan', 'no plan → no cost estimate')], out
    rep = plan_budget_report(manager, plan_row, today)
    if not rep.get('ok'):
        return [_no_data('cost', 'cost estimate', rep.get('error', 'plan cost unavailable'))], out
    out['costEstimate'] = rep['estTotal']
    lines.append(_line('cost', 'estimate', f'~${rep["estTotal"]:.2f} for {rep["days"]} days '
                       f'(${rep["estPerDay"]:.2f}/day)', rep['estTotal'], 'USD',
                       'plan_budget_report: observed prices × approximate weights'))
    if rep.get('budget'):
        out['budget'] = rep['budget']['capForPlanDays']
        out['budgetDeltaText'] = rep.get('verdict', '')
        lines.append(_line('cost', 'budget', rep.get('verdict', ''), rep.get('headroom'),
                           'USD headroom', f'PlanBudget {rep["budget"]["name"]}: '
                           f'${rep["budget"]["weeklyAmount"]:.2f}/week'))
    else:
        out['budgetDeltaText'] = 'no PlanBudget row — add one to get the envelope'
        lines.append(_no_data('cost', 'PlanBudget row', 'add one (a knob, not a requirement)'))
    for d in rep.get('topDrivers', [])[:5]:
        lines.append(_line('cost', d.get('food', ''), f'${d.get("estCost", 0):.2f}',
                           d.get('estCost'), 'USD', 'top cost driver'))
    if rep.get('unpricedFoods'):
        lines.append(_line('cost', 'unpriced', 'not in the estimate: ' + ', '.join(rep['unpricedFoods']),
                           len(rep['unpricedFoods']), 'foods', 'no observed price — named, not zero'))
    return lines, out


def _waste_section(manager, household, start, end, today):
    view = _windowed(manager, 'WasteRecord', start, end)
    rep = waste_report(view, household, today)
    out = {'wasteGrams': rep.get('totalG', 0.0), 'wasteValue': rep.get('estValue', 0.0)}
    if not rep.get('records'):
        return [_no_data('waste', 'WasteRecord rows', rep.get('note', 'log waste and it shows'))], out
    lines = [_line('waste', 'total', f'{rep["totalG"]:g} g wasted in {rep["records"]} record(s), '
                   f'~${rep["estValue"]:.2f} where priced'
                   + (f'; {rep["unpricedG"]:g} g unpriced' if rep.get('unpricedG') else ''),
                   rep['totalG'], 'g', 'waste_report (windowed)')]
    for b in rep.get('byFood', []):
        reason = max(b['reasons'], key=b['reasons'].get) if b.get('reasons') else ''
        lines.append(_line('waste', b['food'], f'{b["grams"]:g} g, mostly {reason}'
                           + (f' (~${b["estValue"]:.2f})' if b['priced'] else ' (unpriced)'),
                           b['grams'], 'g', 'grams via unit weight priors'))
    for o in rep.get('observations', []):
        lines.append(_line('waste', 'suggestion', o, None, '', 'an observation, your call'))
    for u in rep.get('unresolved', []):
        lines.append(_line('waste', u.get('record', ''), f'not counted: {u.get("why")}', None, '',
                           'unresolvable unit — named'))
    return lines, out


def _fairness_section(manager, household, start, end):
    rep = fairness_readout(manager, household, start.isoformat(), end.isoformat())
    if not rep.get('records'):
        return [_no_data('fairness', 'WorkLedger rows', 'mark generated events done or log '
                         'minutes and the split fills')], 'no WorkLedger rows this week'
    lines = []
    for l in rep.get('lines', []):
        lines.append(_line('fairness', f'{l["person"]} · {l["workload"]}',
                           f'{l["minutes"]:g} min = {l["actualPct"]}% (target {l["targetPct"]}%, '
                           f'drift {l["driftPct"]:+g})' + (f' — {l["suggestion"]}' if l['suggestion'] else ''),
                           l['driftPct'], '% drift', 'WorkLedger vs WorkDistributionPolicy shares'))
    drifts = [l for l in rep.get('lines', []) if l['suggestion']]
    text = (f'{rep["records"]} ledger row(s); ' + (drifts[0]['suggestion'] if drifts else
            'within the shares (no drift over 10 %)'))
    return lines, text


def _proposal_records(events):
    recs = []
    for e in events:
        span = e.get('span') or {}
        when = span.get('start', '')
        if span.get('end') and not e.get('all_day'):
            when += f' → {span["end"][11:]}'
        payload = e.get('payload_json') or {}
        est = payload.get('estTotal') if isinstance(payload, dict) else None
        recs.append({'kind': e.get('category', ''), 'title': e.get('title', ''),
                     'whenText': when + (' (all day)' if e.get('all_day') else ''),
                     'costText': (f'~${est:.2f}' if isinstance(est, (int, float)) and est else
                                  'no cost' if e.get('category') == 'review' else 'unpriced'),
                     'name': e.get('name', '')})
    return recs


# ----------------------------------------------------------------
# the public analyses
# ----------------------------------------------------------------

def next_week_proposals(manager, plan=PLAN, household=HOUSEHOLD, week_start=None, today=None):
    """CalendarEvent proposals for the week AFTER the reviewed one."""
    plan_row = _plan_row(manager, plan)
    household = household or (getattr(plan_row, 'household_name', '') if plan_row else '') or HOUSEHOLD
    start, end = _window(plan_row, week_start or None)
    # next week = the Monday-start week after the one holding `end`
    # (weeks are Monday-start everywhere here: period buckets, the
    # calendar, the Sunday review).
    nstart = end + timedelta(days=7 - end.weekday())
    nend = nstart + timedelta(days=6)
    # the shop is the Saturday on/before the week starts (the
    # coordination convention: purchase precedes pre-prep).
    pdate = nstart - timedelta(days=(nstart.weekday() - 5) % 7)
    events, notes = [], []
    if plan_row is not None:
        wk = weekly_purchase_proposal(manager, plan_row, household, pdate, today)
        if wk.get('ok'):
            events.extend(wk['proposals'])
        else:
            notes.append(f'weekly purchase: {wk.get("error")}')
    else:
        notes.append(f"no MealPlanDefinition '{plan}' — no purchase proposal")
    firsts = [nstart + timedelta(days=i) for i in range(7) if (nstart + timedelta(days=i)).day == 1]
    for cadence in BULK_CADENCES:
        anchor = _bulk_anchor_month(manager, cadence)
        for d in firsts:
            if (d.month - anchor) % cadence == 0:
                b = bulk_purchase_proposal(manager, household, cadence, d, today)
                events.extend(b.get('proposals', []))
                if b.get('refused'):
                    notes.append(f'bulk {cadence}-month refused: '
                                 + ', '.join(r['food'] for r in b['refused']))
    review = weekly_review_event_proposal(manager, plan, household, week_start=nstart,
                                          review_time=REVIEW_TIME, today=today, _headline=False)
    events.extend(review.get('proposals', []))
    # the plain words the accept form shows: GenerateEvent dedupes by
    # name, so an event whose name already exists is kept, not rewritten
    have = {getattr(e, 'name', '') for e in _rows(manager, 'CalendarEvent')}
    existed = [e for e in events if e.get('name') in have]
    new = [e for e in events if e.get('name') not in have]
    if not events:
        message = f'Nothing to create for the week of {nstart.isoformat()}'
    else:
        message = (f'Created {len(new)} event{"" if len(new) == 1 else "s"} for the week of '
                   f'{nstart.isoformat()}')
        if new:
            message += ' (' + ', '.join(str(e.get('title') or e.get('name')) for e in new) + ')'
        if existed:
            message += f'; {len(existed)} already existed and kept'
    for n in notes:
        message += f'; {n}'
    return {'ok': True, 'schema': 'next-week-proposals/1', 'message': message,
            'plan': plan, 'household': household,
            'reviewedWeekStart': start.isoformat(), 'reviewedWeekEnd': end.isoformat(),
            'nextWeekStart': nstart.isoformat(), 'nextWeekEnd': nend.isoformat(),
            'purchaseDate': pdate.isoformat(),
            'proposals': events, 'records': _proposal_records(events),
            'notes': notes or None,
            'honesty': 'the purchase is the plan\'s shopping gap on the Saturday before the week '
                       '(10:00 prior); bulk buys only on a cadence whose 1st falls in the week; '
                       'the review event is the Sunday sit-down — accepting writes rows deduped '
                       'by name, so nothing is written twice'}


def week_review(manager, plan=PLAN, household=HOUSEHOLD, week_start=None, today=None):
    """The Sunday review, flat: headline scalars + lines + proposals + honesty."""
    plan_row = _plan_row(manager, plan)
    household = household or (getattr(plan_row, 'household_name', '') if plan_row else '') or HOUSEHOLD
    start, end = _window(plan_row, week_start or None)
    members = _members(manager, household, plan_row)
    today = _date(today) or today

    cov_lines, stats = _coverage_section(manager, plan_row, members, start, end)
    intake_lines, consistently = _intake_section(manager, members, start, end)
    cost_lines, cost = _cost_section(manager, plan_row, today)
    waste_lines, waste = _waste_section(manager, household, start, end, today)
    fair_lines, fairness_text = _fairness_section(manager, household, start, end)
    nxt = next_week_proposals(manager, plan, household, week_start, today)
    prop_lines = [_line('proposals', r['kind'], f'{r["title"]} — {r["whenText"]} — {r["costText"]}',
                        None, '', 'next_week_proposals') for r in nxt['records']]
    for n in (nxt.get('notes') or []):
        prop_lines.append(_line('proposals', 'note', n, None, '', 'next_week_proposals'))
    if not prop_lines:
        prop_lines.append(_no_data('proposals', 'proposals', 'no plan and no staples due'))

    lines = cov_lines + intake_lines + cost_lines + waste_lines + fair_lines + prop_lines
    honesty = [{'prior': k, 'text': v} for k, v in PRIORS]
    cov_pct = _pct(stats['planned'], stats['expected'])
    adherence = _pct(stats['plannedEaten'], stats['planned'])
    return {
        'ok': True, 'schema': 'week-review/1',
        'plan': getattr(plan_row, 'name', plan) if plan_row else plan,
        'planFound': plan_row is not None,
        'household': household, 'members': ', '.join(members) or 'none',
        'weekStart': start.isoformat(), 'weekEnd': end.isoformat(),
        # headline scalars
        'expectedSlots': stats['expected'], 'plannedSlots': stats['planned'],
        'eatenSlots': stats['eaten'], 'plannedEatenSlots': stats['plannedEaten'],
        'unplannedEatenSlots': stats['unplannedEaten'],
        'coveragePct': cov_pct, 'adherencePct': adherence,
        'coverageText': (f'{stats["planned"]} of {stats["expected"]} expected meals planned '
                         f'({cov_pct}%)' if stats['expected'] else 'no planned meals in the week'),
        'eatenText': (f'{stats["plannedEaten"]} planned meals eaten as planned; '
                      f'{stats["unplannedEaten"]} eaten off-plan; {stats["eaten"]} intake rows'
                      if stats['eaten'] else 'no intake logged this week'),
        'costEstimate': cost['costEstimate'], 'budget': cost['budget'],
        'budgetDeltaText': cost['budgetDeltaText'],
        'wasteGrams': waste['wasteGrams'], 'wasteValue': waste['wasteValue'],
        'fairnessText': fairness_text,
        'consistentlyText': '; '.join(consistently) if consistently else 'no pattern yet',
        'proposalCount': len(nxt['records']),
        'nextWeekStart': nxt['nextWeekStart'],
        'reviewTime': f'Sunday {REVIEW_TIME} (prior)',
        # records
        'lines': lines,
        'proposals': nxt['records'],
        'honesty': honesty,
    }


def weekly_review_event_proposal(manager, plan=PLAN, household=HOUSEHOLD, week_start=None,
                                 review_date=None, review_time=REVIEW_TIME, today=None,
                                 _headline=True):
    """One 'review' CalendarEvent proposal for the Sunday of the week."""
    plan_row = _plan_row(manager, plan)
    household = household or (getattr(plan_row, 'household_name', '') if plan_row else '') or HOUSEHOLD
    rd = _date(review_date) if review_date else None
    if rd is not None:
        start = rd - timedelta(days=rd.weekday())
        end = start + timedelta(days=6)
        sunday = end
    else:
        start, end = _window(plan_row, week_start or None)
        sunday = end + timedelta(days=(6 - end.weekday()) % 7)
    hhmm = str(review_time or REVIEW_TIME)[:5]
    if len(hhmm) != 5 or hhmm[2] != ':':
        hhmm = REVIEW_TIME
    headline = {}
    if _headline:
        rv = week_review(manager, plan, household, start.isoformat(), today)
        headline = {k: rv[k] for k in ('weekStart', 'weekEnd', 'expectedSlots', 'plannedSlots',
                                       'eatenSlots', 'plannedEatenSlots', 'coveragePct',
                                       'adherencePct', 'costEstimate', 'budget', 'budgetDeltaText',
                                       'wasteGrams', 'fairnessText', 'consistentlyText',
                                       'proposalCount')}
    title = f'Weekly review — {household} (week of {start.isoformat()})'
    if headline.get('expectedSlots'):
        title += f': {headline["coveragePct"]}% planned'
    start_iso = f'{sunday.isoformat()}T{hhmm}'
    event = {'name': f'weekly-review-{household}-{sunday.isoformat()}',
             'title': title, 'category': 'review', 'household_name': household,
             'person_name': '', 'span': {'start': start_iso, 'end': _plus(start_iso, REVIEW_MINUTES)},
             'all_day': False, 'color': '#37474f',
             'linked_class': 'MealPlanDefinition', 'linked_name': getattr(plan_row, 'name', plan) if plan_row else plan,
             'payload_json': headline or {'weekStart': start.isoformat(), 'weekEnd': end.isoformat(),
                                          'note': 'headline computed at review time'}}
    return {'ok': True, 'schema': 'review-event/1', 'plan': plan, 'household': household,
            'weekStart': start.isoformat(), 'weekEnd': end.isoformat(),
            'reviewDate': sunday.isoformat(), 'reviewTime': hhmm,
            'reviewMinutes': REVIEW_MINUTES, 'proposals': [event],
            'honesty': (f'the review sits on the Sunday closing the week at {hhmm} for '
                        f'{REVIEW_MINUTES} min — both priors (review_time / the trigger row are '
                        f'the knobs); the payload is the headline as computed now')}
