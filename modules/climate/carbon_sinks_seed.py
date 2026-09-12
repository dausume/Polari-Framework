"""
@module climate.carbon_sinks_seed

co2-6 — THE CARBON SINKS, AND A CORRECTION TO THE PLAN THAT ASKED
FOR THEM.

CO2_HEALTH_PLAN.md asked for "rates of decline in carbon sinks".
The fetched Global Carbon Budget does not show that, and saying so
is the whole point of ingesting rather than assuming.

WHAT THE DATA SAYS (Global Carbon Budget 2025 v1.0, 66 years,
1959-2024, fetched 2026-08-02):

- TOTAL sinks have GROWN strongly: +0.066 GtC/yr per year,
  r = +0.92. Ocean and land together absorb far more carbon now
  than in 1959, because there is far more CO2 for them to absorb.
- The SINK FRACTION (sinks / emissions) has NOT declined. It
  drifts slightly UP: +0.0012 per year, r = +0.29 - a weak
  correlation over 66 noisy years, which is better read as
  "roughly flat" than as a trend in either direction.
- The AIRBORNE FRACTION likewise drifts weakly up (+0.0016/yr,
  r = +0.25).

So the sinks have broadly KEPT PACE proportionally. That is not a
reassurance and this module does not present it as one:

⚠ THE RECENT YEARS ARE THE INTERESTING PART. The land sink fell
from 3.11 GtC in 2022 to 2.02 in 2023 and 1.94 in 2024, and the
airborne fraction hit 0.672 in 2024 against a 0.44 long-run mean.
A two-year excursion is NOT a trend - it is what El Nino years and
fire years look like in this record, and the budget's own imbalance
term is large. Reporting it as the start of sink collapse would be
exactly the error the flat long-run fraction warns against;
omitting it would be the opposite error. Both are reported, with
the interpretation refused.

WHY THIS MATTERS TO THE REST OF THE APP: the quadratic fit in
co2_trend has an acceleration term `a`, and it is easy to read
that as a constant of nature. It is not. It is a summary of the
past 45 years of emissions AND of how much of that the sinks took
up. If the sink fraction moves, `a` moves - which is why the
crossing years carry bands and a horizon rather than a date.

@consumers climate.climate_views_seed, climate.climate_api,
climate.climate_selftest
"""

import math

from moduleService.seed_upsert import upsert_seed_pairs

PROV = 'co2-6'

#: The 'Global Carbon Budget' sheet's columns, in file order.
#: Mapped as DATA rather than by position: the publisher adds
#: columns between releases, and a positional read would silently
#: shift the ocean sink into the land sink.
GCB_COLUMNS = (
    ('year', 'Year'),
    ('fossil_emissions', 'fossil emissions'),
    ('land_use_emissions', 'land-use change emissions'),
    ('atmospheric_growth', 'atmospheric growth'),
    ('ocean_sink', 'ocean sink'),
    ('land_sink', 'land sink'),
    ('cement_sink', 'cement carbonation sink'),
    ('budget_imbalance', 'budget imbalance'),
)

#: The labels find_header_row must see before this module will
#: read a single number out of the workbook.
GCB_REQUIRED_HEADERS = ('year', 'ocean sink', 'land sink')

#: 1 ppm of atmospheric CO2 is about this much carbon. Stated once
#: here; used to put the NOAA growth rate and the budget's
#: atmospheric-growth term into the same units for cross-check.
GTC_PER_PPM = 2.124


def parse_gcb_sheet(raw, sheet='Global Carbon Budget'):
    """The GCB workbook -> annual budget records. Refuses rather
    than guessing when the layout moves."""
    from climate.custom.xlsx_reader import find_header_row, read_sheet
    sheet_data = read_sheet(raw, sheet)
    if not sheet_data.get('ok'):
        return sheet_data
    header = find_header_row(sheet_data['rows'],
                             list(GCB_REQUIRED_HEADERS))
    if not header.get('ok'):
        return header

    labels = [str(c).strip().lower() if c is not None else ''
              for c in header['header']]
    index = {}
    for key, want in GCB_COLUMNS:
        for i, label in enumerate(labels):
            if want.lower() in label:
                index[key] = i
                break
    missing = [k for k, _ in GCB_COLUMNS if k not in index]
    if missing:
        return {'ok': False,
                'refusal': (f'the budget sheet is missing columns '
                            f'{missing}; found headers '
                            f'{[l for l in labels if l]}. The '
                            f'publisher changed the layout - remap '
                            f'before ingesting.')}

    records, skipped = [], 0
    for row in sheet_data['rows'][header['index'] + 1:]:
        if not row:
            continue
        raw_year = row[index['year']] if index['year'] < len(row) \
            else None
        if not isinstance(raw_year, float):
            skipped += 1
            continue
        rec = {'year': raw_year}
        for key, _ in GCB_COLUMNS[1:]:
            i = index[key]
            val = row[i] if i < len(row) else None
            rec[key] = float(val) if isinstance(val, float) else None
        records.append(rec)
    if not records:
        return {'ok': False,
                'refusal': 'no numeric budget rows under the header'}
    return {'ok': True, 'records': records, 'skipped': skipped,
            'firstYear': records[0]['year'],
            'lastYear': records[-1]['year'], 'sheet': sheet}


def sink_fractions(records):
    """Per year: total emissions, total sinks, sink fraction and
    airborne fraction.

    A year missing any term is DROPPED and counted, never treated
    as a zero — a zero ocean sink would quietly halve the fraction.
    """
    out, dropped = [], 0
    for rec in records:
        parts = (rec.get('fossil_emissions'),
                 rec.get('land_use_emissions'),
                 rec.get('ocean_sink'), rec.get('land_sink'))
        if any(p is None for p in parts):
            dropped += 1
            continue
        emissions = rec['fossil_emissions'] + rec['land_use_emissions']
        if emissions <= 0:
            dropped += 1
            continue
        cement = rec.get('cement_sink') or 0.0
        sinks = rec['ocean_sink'] + rec['land_sink'] + cement
        growth = rec.get('atmospheric_growth')
        out.append({
            'year': rec['year'], 'emissions': emissions,
            'oceanSink': rec['ocean_sink'],
            'landSink': rec['land_sink'], 'cementSink': cement,
            'totalSink': sinks,
            'sinkFraction': sinks / emissions,
            'atmosphericGrowth': growth,
            'airborneFraction': (growth / emissions
                                 if growth is not None else None),
            'budgetImbalance': rec.get('budget_imbalance'),
        })
    return {'ok': True, 'years': out, 'droppedYears': dropped,
            'count': len(out)}


def _trend(xs, ys):
    n = len(xs)
    if n < 3:
        return None
    mx, my = sum(xs) / n, sum(ys) / n
    sxx = sum((a - mx) ** 2 for a in xs)
    syy = sum((b - my) ** 2 for b in ys)
    if sxx <= 0 or syy <= 0:
        return None
    sxy = sum((a - mx) * (b - my) for a, b in zip(xs, ys))
    return {'slope': sxy / sxx, 'r': sxy / math.sqrt(sxx * syy)}


def sink_trend_report(records, recent_years=3):
    """Is the sink fraction declining? Answered, with the recent
    excursion reported separately and NOT extrapolated."""
    fracs = sink_fractions(records)
    years = fracs['years']
    if len(years) < 10:
        return {'ok': False,
                'refusal': (f'{len(years)} usable budget years is '
                            f'too few to say anything about a '
                            f'multi-decadal fraction')}
    xs = [y['year'] for y in years]
    span = xs[-1] - xs[0]
    sink_t = _trend(xs, [y['sinkFraction'] for y in years])
    total_t = _trend(xs, [y['totalSink'] for y in years])
    air_rows = [y for y in years if y['airborneFraction'] is not None]
    air_t = _trend([y['year'] for y in air_rows],
                   [y['airborneFraction'] for y in air_rows])

    recent = years[-recent_years:]
    long_run_air = [y['airborneFraction'] for y in air_rows
                    if y['airborneFraction'] is not None]
    mean_air = sum(long_run_air) / len(long_run_air) \
        if long_run_air else None

    declining = bool(sink_t and sink_t['slope'] < 0
                     and abs(sink_t['r']) >= 0.5)
    verdict = (
        'the sink fraction IS declining over the full record'
        if declining else
        'the sink fraction is NOT declining over the full record - '
        'it is roughly flat, with a weak positive drift. Total '
        'sinks have grown strongly because there is more CO2 for '
        'them to take up.')

    return {
        'ok': True, 'fromYear': xs[0], 'toYear': xs[-1],
        'nYears': len(years),
        'sinkFractionSlopePerYear': sink_t['slope'] if sink_t else None,
        'sinkFractionR': sink_t['r'] if sink_t else None,
        'sinkFractionChangeOverRecord': (sink_t['slope'] * span
                                         if sink_t else None),
        'totalSinkSlopeGtcPerYearPerYear': (total_t['slope']
                                            if total_t else None),
        'totalSinkR': total_t['r'] if total_t else None,
        'airborneFractionSlopePerYear': (air_t['slope']
                                         if air_t else None),
        'airborneFractionR': air_t['r'] if air_t else None,
        'meanAirborneFraction': mean_air,
        'declining': declining, 'verdict': verdict,
        'recentYears': [{
            'year': y['year'], 'landSink': y['landSink'],
            'oceanSink': y['oceanSink'],
            'sinkFraction': y['sinkFraction'],
            'airborneFraction': y['airborneFraction'],
            'budgetImbalance': y['budgetImbalance']}
            for y in recent],
        'recentCaveat': (
            'the most recent years show a sharp LAND sink drop and '
            'a high airborne fraction. A two- or three-year '
            'excursion is not a trend: El Nino and fire years look '
            'exactly like this in the record, and the budget\'s own '
            'imbalance term is large. Reported because omitting it '
            'would be dishonest; NOT extrapolated because '
            'extrapolating it would be worse.'),
        'whyItMattersHere': (
            'co2_trend fits an acceleration term. That term is not '
            'a constant of nature - it summarises past emissions '
            'AND how much of them the sinks absorbed. If the sink '
            'fraction moves, the acceleration moves, which is why '
            'every crossing year on this page carries a band and a '
            'horizon instead of a date.'),
        'headline': _sink_headline(sink_t, total_t, air_t, span,
                                   declining),
    }


def _sink_headline(sink_t, total_t, air_t, span, declining):
    rows = []
    if total_t:
        rows.append({
            'label': 'Total carbon sinks',
            'value': f'{total_t["slope"]:+.3f} GtC/yr per year '
                     f'(r={total_t["r"]:+.2f})',
            'note': 'growing strongly - more CO2 to absorb',
            'verdict': 'ok'})
    if sink_t:
        rows.append({
            'label': 'Sink FRACTION (sinks / emissions)',
            'value': f'{sink_t["slope"]:+.5f} per year '
                     f'(r={sink_t["r"]:+.2f}), '
                     f'{sink_t["slope"] * span:+.3f} over the record',
            'note': ('declining' if declining else
                     'roughly flat - the plan assumed a decline; '
                     'the data does not show one'),
            'verdict': 'bad' if declining else 'ok'})
    if air_t:
        rows.append({
            'label': 'Airborne fraction',
            'value': f'{air_t["slope"]:+.5f} per year '
                     f'(r={air_t["r"]:+.2f})',
            'note': 'weak drift; noisy year to year',
            'verdict': 'ok'})
    return rows


def cross_check_atmospheric_growth(records, noaa_growth_points):
    """The budget's atmospheric-growth term against NOAA's own
    growth rate, in one unit. Two publishers, one quantity -
    disagreement is a finding, not something to average."""
    by_year = {p['year']: p['value'] for p in noaa_growth_points}
    pairs = []
    for rec in records:
        gtc = rec.get('atmospheric_growth')
        ppm = by_year.get(rec['year'])
        if gtc is None or ppm is None:
            continue
        pairs.append({'year': rec['year'], 'budgetGtc': gtc,
                      'noaaPpm': ppm,
                      'noaaAsGtc': ppm * GTC_PER_PPM,
                      'differenceGtc': gtc - ppm * GTC_PER_PPM})
    if len(pairs) < 5:
        return {'ok': False,
                'refusal': (f'only {len(pairs)} overlapping years '
                            f'between the budget and the NOAA '
                            f'growth series')}
    diffs = [p['differenceGtc'] for p in pairs]
    mean_abs = sum(abs(d) for d in diffs) / len(diffs)
    scale = sum(p['budgetGtc'] for p in pairs) / len(pairs)
    rel = mean_abs / scale if scale else 0.0
    return {'ok': True, 'nYears': len(pairs),
            'meanAbsDifferenceGtc': mean_abs,
            'relativeDifference': rel,
            'gtcPerPpm': GTC_PER_PPM,
            'agree': rel < 0.15,
            'verdict': (
                f'the budget\'s atmospheric-growth term and NOAA\'s '
                f'published growth rate agree to {rel * 100:.1f}% '
                f'on average over {len(pairs)} years'
                if rel < 0.15 else
                f'THE TWO PUBLISHERS DISAGREE by {rel * 100:.1f}% '
                f'on the same physical quantity - that is a '
                f'finding to chase, not an average to take'),
            'pairs': pairs[-5:]}


def sink_ranking(records, periods=None):
    """WHICH SINK IS LARGEST, and how much each actually takes up.

    Ranked per era rather than once, because the answer could have
    changed and a single ranking would hide it. (It has not: the
    ocean leads in every era of this record.)
    """
    periods = periods or ((1959, 1968), (1990, 1999), (2015, 2024))
    out = []
    for start, end in periods:
        sel = [r for r in records if start <= r['year'] <= end]
        if not sel:
            continue
        means = {}
        for key, label in (('ocean_sink', 'ocean'),
                           ('land_sink', 'land'),
                           ('cement_sink', 'cement carbonation')):
            vals = [r[key] for r in sel if r.get(key) is not None]
            means[label] = sum(vals) / len(vals) if vals else 0.0
        total = sum(means.values())
        ranked = sorted(means.items(), key=lambda kv: -kv[1])
        out.append({
            'fromYear': start, 'toYear': end, 'nYears': len(sel),
            'sinksGtcPerYear': means, 'totalGtcPerYear': total,
            'largest': ranked[0][0],
            'largestGtcPerYear': ranked[0][1],
            'shareOfTotal': {k: (v / total if total else 0.0)
                             for k, v in means.items()},
            'ranked': [k for k, _ in ranked],
        })
    if not out:
        return {'ok': False,
                'refusal': 'no budget years inside the requested '
                           'periods'}
    latest = out[-1]
    return {'ok': True, 'periods': out,
            'largestSinkNow': latest['largest'],
            'stableRanking': len({p['largest'] for p in out}) == 1,
            'note': ('the ocean is the largest single sink in '
                     'every era of this record, and cement '
                     'carbonation - which most summaries omit '
                     'entirely - has grown tenfold from a very '
                     'small base'),
            'headline': [
                {'label': f'{label} sink, {latest["fromYear"]}-'
                          f'{latest["toYear"]}',
                 'value': f'{latest["sinksGtcPerYear"][label]:.2f} '
                          f'GtC/yr',
                 'note': f'{latest["shareOfTotal"][label] * 100:.0f}'
                         f'% of all uptake',
                 'verdict': 'ok'}
                for label in latest['ranked']]}


def source_sink_differential(records):
    """THE IMBALANCE, per year: what humans emit MINUS what the
    sinks take back.

    This is the quantity the atmosphere actually sees. It is also
    the honest way to read the sink data: the sinks are doing more
    work every decade AND falling further behind every decade,
    and only the differential shows both at once.
    """
    years, dropped = [], 0
    for rec in records:
        parts = (rec.get('fossil_emissions'),
                 rec.get('land_use_emissions'),
                 rec.get('ocean_sink'), rec.get('land_sink'))
        if any(p is None for p in parts):
            dropped += 1
            continue
        sources = rec['fossil_emissions'] + rec['land_use_emissions']
        sinks = (rec['ocean_sink'] + rec['land_sink']
                 + (rec.get('cement_sink') or 0.0))
        years.append({
            'year': rec['year'], 'sources': sources, 'sinks': sinks,
            'differential': sources - sinks,
            'sinkShareOfSources': (sinks / sources
                                   if sources else None),
            'atmosphericGrowth': rec.get('atmospheric_growth'),
            'budgetImbalance': rec.get('budget_imbalance'),
        })
    if len(years) < 5:
        return {'ok': False,
                'refusal': (f'{len(years)} usable budget years is '
                            f'too few for a differential series')}
    diffs = [y['differential'] for y in years]
    cumulative = sum(diffs)
    closest = min(years, key=lambda y: abs(y['differential']))
    widest = max(years, key=lambda y: y['differential'])
    return {
        'ok': True, 'years': years, 'droppedYears': dropped,
        'fromYear': years[0]['year'], 'toYear': years[-1]['year'],
        'firstDifferential': diffs[0], 'lastDifferential': diffs[-1],
        'closestToBalance': {'year': closest['year'],
                             'differential': closest['differential']},
        'widestGap': {'year': widest['year'],
                      'differential': widest['differential']},
        'cumulativeExcessGtc': cumulative,
        'cumulativeExcessPpmEquivalent': cumulative / GTC_PER_PPM,
        'everBalanced': any(abs(d) < 0.5 for d in diffs),
        'note': ('THE RECORD NEVER SHOWS BALANCE. The smallest gap '
                 'in 66 years is still well above zero, so the '
                 'question "when were sources and sinks in '
                 'balance" cannot be answered from the budget at '
                 'all - it needs the ice cores, where a flat CO2 '
                 'curve IS balance by definition'),
        'headline': [
            {'label': f'Imbalance in {years[0]["year"]:.0f}',
             'value': f'{diffs[0]:.2f} GtC/yr',
             'note': 'sources minus sinks', 'verdict': 'ok'},
            {'label': f'Imbalance in {years[-1]["year"]:.0f}',
             'value': f'{diffs[-1]:.2f} GtC/yr',
             'note': f'{diffs[-1] / diffs[0]:.1f}x the gap at the '
                     f'start of the record', 'verdict': 'bad'},
            {'label': 'Smallest gap in the whole record',
             'value': f'{closest["differential"]:.2f} GtC/yr '
                      f'({closest["year"]:.0f})',
             'note': 'never close to zero', 'verdict': 'warn'},
            {'label': 'Cumulative excess since '
                      f'{years[0]["year"]:.0f}',
             'value': f'{cumulative:.0f} GtC '
                      f'({cumulative / GTC_PER_PPM:.0f} ppm '
                      f'equivalent)',
             'note': 'what the sinks did not take back',
             'verdict': 'bad'},
        ],
    }


def balance_history(ice_points, differential=None,
                    holocene_from=-10000.0, holocene_to=1500.0,
                    sustain=3):
    """WHEN DID SOURCES AND SINKS STOP BALANCING?

    The budget record cannot answer this - it starts in 1959, long
    after the imbalance opened. The ice cores can, because a FLAT
    CO2 curve is balance by definition: if the atmosphere is not
    accumulating carbon, uptake equals release.

    So the method is: characterise the Holocene band, then find
    the first SUSTAINED departure above it. `sustain` consecutive
    points are required so a single noisy sample cannot date the
    industrial era.
    """
    band = [p for p in ice_points
            if holocene_from <= p['year'] <= holocene_to]
    if len(band) < 30:
        return {'ok': False,
                'refusal': (f'only {len(band)} ice-core points in '
                            f'the reference window - ingest the '
                            f'composite series first')}
    vals = [p['value'] for p in band]
    mean = sum(vals) / len(vals)
    var = sum((v - mean) ** 2 for v in vals) / len(vals)
    sd = math.sqrt(var)
    threshold = mean + 2 * sd

    later = sorted([p for p in ice_points if p['year'] > holocene_to],
                   key=lambda p: p['year'])
    departure = None
    for i, point in enumerate(later):
        window = later[i:i + sustain]
        if len(window) < sustain:
            break
        if all(q['value'] > threshold for q in window):
            departure = point
            break

    def rate_between(a, b):
        seg = sorted([p for p in ice_points if a <= p['year'] <= b],
                     key=lambda p: p['year'])
        if len(seg) < 2 or seg[-1]['year'] == seg[0]['year']:
            return None
        return ((seg[-1]['value'] - seg[0]['value'])
                / (seg[-1]['year'] - seg[0]['year']))

    holocene_rate = rate_between(-8000.0, 1000.0)
    result = {
        'ok': True,
        'holoceneFromYear': holocene_from,
        'holoceneToYear': holocene_to,
        'holoceneMeanPpm': mean, 'holoceneSdPpm': sd,
        'holoceneMinPpm': min(vals), 'holoceneMaxPpm': max(vals),
        'departureThresholdPpm': threshold,
        'nReferencePoints': len(band),
        'holoceneRatePpmPerCentury': (holocene_rate * 100.0
                                      if holocene_rate else None),
        'deglaciationRatePpmPerCentury': (
            (rate_between(-18000.0, -10000.0) or 0.0) * 100.0),
        'note': ('a flat CO2 curve IS balance: if the atmosphere '
                 'is not accumulating carbon, uptake equals '
                 'release. That is why this question belongs to '
                 'the ice cores and not to the budget, which '
                 'begins in 1959 with the imbalance already open'),
    }
    if departure is None:
        result['balanceEnded'] = None
        result['refusalDetail'] = (
            'no sustained departure above the Holocene band was '
            'found after the reference window')
        return result

    result['balanceEndedYear'] = departure['year']
    result['balanceEndedPpm'] = departure['value']
    result['sustainedPoints'] = sustain
    result['interpretation'] = (
        f'CO2 sat inside a {mean:.0f} +/- {sd:.0f} ppm band for '
        f'the whole reference window - roughly ten thousand years '
        f'in which sources and sinks matched to within the '
        f'measurement. The first sustained departure above that '
        f'band is {departure["year"]:.0f}. Everything after it is '
        f'the imbalance the budget measures directly from 1959.')
    if differential and differential.get('ok'):
        result['budgetStartsYear'] = differential['fromYear']
        result['yearsOfImbalanceBeforeBudget'] = (
            differential['fromYear'] - departure['year'])
        result['note'] += (
            f'; the budget record starts '
            f'{differential["fromYear"] - departure["year"]:.0f} '
            f'years after balance ended, which is why it never '
            f'shows a balanced year')
    return result


def rate_comparison(balance, instrumental_points):
    """Today's rate against the natural one. The ratio is the
    finding; it is also easy to overstate, so the resolution
    caveat travels with it."""
    if not balance.get('ok') or not instrumental_points:
        return {'ok': False,
                'refusal': 'need both a balance report and an '
                           'ingested instrumental series'}
    natural = balance.get('holoceneRatePpmPerCentury')
    if not natural:
        return {'ok': False,
                'refusal': 'no Holocene rate available'}
    pts = sorted(instrumental_points, key=lambda p: p['year'])
    span = pts[-1]['year'] - pts[0]['year']
    if span <= 0:
        return {'ok': False, 'refusal': 'instrumental span is zero'}
    modern = ((pts[-1]['value'] - pts[0]['value']) / span) * 100.0
    return {'ok': True,
            'naturalRatePpmPerCentury': natural,
            'modernRatePpmPerCentury': modern,
            'ratio': modern / natural if natural else None,
            'fromYear': pts[0]['year'], 'toYear': pts[-1]['year'],
            'caveat': ('the ice-core rate is measured over '
                       'millennia at centuries-apart resolution, '
                       'so it CANNOT resolve a short fast '
                       'excursion the way the instrumental record '
                       'can. The ratio is sound as a statement '
                       'about sustained centennial rates and '
                       'should not be read as proof that no '
                       'decade in the Holocene was ever faster.'),
            'headline': [
                {'label': 'Natural Holocene rate',
                 'value': f'{natural:+.2f} ppm/century',
                 'note': 'sources and sinks effectively matched',
                 'verdict': 'ok'},
                {'label': f'Instrumental rate '
                          f'{pts[0]["year"]:.0f}-{pts[-1]["year"]:.0f}',
                 'value': f'{modern:+.0f} ppm/century',
                 'note': f'about {modern / natural:,.0f}x the '
                         f'Holocene rate',
                 'verdict': 'bad'}]}


def budget_closure(differential, instrumental_points):
    """Does the budget close? Cumulative (sources - sinks) against
    the observed atmospheric rise.

    The gap is the budget's own imbalance term. Reporting it is
    the difference between a carbon budget and an accounting
    identity - the publishers print it, and so does this.
    """
    if not differential.get('ok') or not instrumental_points:
        return {'ok': False,
                'refusal': 'need the differential and an ingested '
                           'instrumental series'}
    start = differential['fromYear']
    pts = sorted([p for p in instrumental_points
                  if p['year'] >= start], key=lambda p: p['year'])
    if len(pts) < 2:
        return {'ok': False,
                'refusal': (f'instrumental series does not cover '
                            f'{start:.0f} onward')}
    observed = pts[-1]['value'] - pts[0]['value']
    predicted = differential['cumulativeExcessPpmEquivalent']
    gap = predicted - observed
    return {'ok': True, 'fromYear': pts[0]['year'],
            'toYear': pts[-1]['year'],
            'observedRisePpm': observed,
            'cumulativeExcessPpmEquivalent': predicted,
            'gapPpm': gap,
            'relativeGap': abs(gap) / observed if observed else None,
            'verdict': (
                f'summing (sources - sinks) over the record '
                f'predicts a {predicted:.0f} ppm rise; the '
                f'atmosphere actually rose {observed:.0f} ppm. The '
                f'{gap:+.0f} ppm gap IS the budget imbalance term '
                f'the publishers print - the budget does not close '
                f'exactly, and a page that hid that would be '
                f'claiming a precision nobody has.')}


SEED_CARBON_SINK_SERIES = [
    {'name': 'sink-ocean-gcb', 'display_name': 'Ocean carbon sink',
     'sink_kind': 'ocean', 'unit': 'GtC/yr',
     'source_ref': 'global-carbon-project',
     'endpoint_ref': 'gcb-global-carbon-budget', 'status': 'prior',
     'description': 'Annual ocean CO2 uptake from the Global '
                    'Carbon Budget.',
     'is_prior': True, 'provenance_id': PROV, 'notes': ''},
    {'name': 'sink-land-gcb', 'display_name': 'Land carbon sink',
     'sink_kind': 'land', 'unit': 'GtC/yr',
     'source_ref': 'global-carbon-project',
     'endpoint_ref': 'gcb-global-carbon-budget', 'status': 'prior',
     'description': 'Annual terrestrial CO2 uptake from the Global '
                    'Carbon Budget. The noisiest term in the '
                    'budget and the one driving the recent '
                    'excursion.',
     'is_prior': True, 'provenance_id': PROV, 'notes': ''},
    {'name': 'sink-cement-gcb',
     'display_name': 'Cement carbonation sink', 'sink_kind': 'land',
     'unit': 'GtC/yr', 'source_ref': 'global-carbon-project',
     'endpoint_ref': 'gcb-global-carbon-budget', 'status': 'prior',
     'description': 'Carbon reabsorbed by cement over its life. '
                    'Small - about 4 percent of uptake - but it '
                    'has grown roughly tenfold and most summaries '
                    'omit it entirely.',
     'is_prior': True, 'provenance_id': PROV, 'notes': ''},
    {'name': 'source-fossil-gcb',
     'display_name': 'Fossil fuel and industry emissions',
     'sink_kind': 'source', 'unit': 'GtC/yr',
     'source_ref': 'global-carbon-project',
     'endpoint_ref': 'gcb-global-carbon-budget', 'status': 'prior',
     'description': 'The larger of the two source terms.',
     'is_prior': True, 'provenance_id': PROV, 'notes': ''},
    {'name': 'source-landuse-gcb',
     'display_name': 'Land-use change emissions',
     'sink_kind': 'source', 'unit': 'GtC/yr',
     'source_ref': 'global-carbon-project',
     'endpoint_ref': 'gcb-global-carbon-budget', 'status': 'prior',
     'description': 'Deforestation and land conversion - the most '
                    'uncertain term in the whole budget.',
     'is_prior': True, 'provenance_id': PROV, 'notes': ''},
    {'name': 'atmospheric-growth-gcb',
     'display_name': 'Atmospheric growth (budget term)',
     'sink_kind': 'atmospheric-fraction', 'unit': 'GtC/yr',
     'source_ref': 'global-carbon-project',
     'endpoint_ref': 'gcb-global-carbon-budget', 'status': 'prior',
     'description': 'What actually stayed in the air. Cross-checked '
                    'against NOAA\'s independently published growth '
                    'rate - they agree to 12.1 percent over 66 '
                    'years.',
     'is_prior': True, 'provenance_id': PROV, 'notes': ''},
    {'name': 'airborne-fraction-gcb',
     'display_name': 'Airborne fraction',
     'sink_kind': 'atmospheric-fraction', 'unit': '(fraction)',
     'source_ref': 'global-carbon-project',
     'endpoint_ref': 'gcb-global-carbon-budget', 'status': 'prior',
     'description': 'The share of each year\'s emissions that '
                    'stayed in the atmosphere.',
     'is_prior': True, 'provenance_id': PROV, 'notes': ''},
]


#: Budget column -> the series its yearly values are stored under.
#: Each column becomes its own AtmosphericObservation series, so
#: the budget needs NO new class and every budget number gets the
#: same provenance chain (span -> endpoint -> source -> retrieval)
#: as every other measurement in this app.
BUDGET_SERIES = {
    'ocean_sink': 'sink-ocean-gcb',
    'land_sink': 'sink-land-gcb',
    'cement_sink': 'sink-cement-gcb',
    'fossil_emissions': 'source-fossil-gcb',
    'land_use_emissions': 'source-landuse-gcb',
    'atmospheric_growth': 'atmospheric-growth-gcb',
}

BUDGET_SPAN = 'span-global-carbon-budget'
BUDGET_ENDPOINT = 'gcb-global-carbon-budget'


def ingest_carbon_budget(manager, fetcher=None, retrieved_by=''):
    """Fetch the budget workbook and write one observation series
    per column. Refusals pass through verbatim."""
    from climate.climate_basis import (
        AtmosphericObservation, SourceCoverageSpan,
    )
    from climate.custom.series_ingest import (
        _named, _upsert, record_retrieval_row,
    )
    from polariApiProfiler.endpoint_fetch import fetch_endpoint

    endpoint = _named(manager, 'APIEndpoint', BUDGET_ENDPOINT)
    if endpoint is None:
        return {'ok': False,
                'refusal': (f'no APIEndpoint named '
                            f'{BUDGET_ENDPOINT!r} - '
                            f'seed_climate_sources delivers it')}
    fetched = fetch_endpoint(endpoint, fetcher=fetcher)
    if not fetched.get('ok'):
        return {'ok': False, 'refusal': fetched.get('refusal', ''),
                'urlRedacted': fetched.get('url_redacted', '')}

    parsed = parse_gcb_sheet(fetched['body'])
    if not parsed.get('ok'):
        return parsed
    records = parsed['records']

    _upsert(manager, 'SourceCoverageSpan', SourceCoverageSpan, [{
        'name': BUDGET_SPAN, 'series_ref': 'carbon-budget',
        'display_name': 'Global Carbon Budget (annual)',
        'measurement_kind': 'budget-estimate',
        'from_year': parsed['firstYear'],
        'to_year': parsed['lastYear'],
        'source_ref': 'global-carbon-project',
        'endpoint_ref': BUDGET_ENDPOINT,
        'archive_name': 'Global Carbon Budget 2025 v1.0',
        'instrument': 'inventory, models and observation synthesis',
        'resolution_years': 1.0,
        'citation_text': getattr(endpoint, 'citationText', ''),
        'doi_or_url': fetched.get('url_redacted', ''),
        'color': '#a0801f', 'typical_uncertainty': 0.0,
        'is_prior': False, 'provenance_id': PROV,
        'notes': ('a BUDGET ESTIMATE, not a direct measurement: '
                  'these are inventories and models reconciled '
                  'annually, and the budget does not close exactly '
                  '- its own imbalance term says so'),
    }])
    retrieval = record_retrieval_row(
        manager,
        type('S', (), {'name': 'carbon-budget',
                       'display_name': 'Global Carbon Budget'})(),
        endpoint,
        {'urlRedacted': fetched.get('url_redacted', ''),
         'sha256': fetched.get('sha256', ''),
         'bytes': fetched.get('bytes', 0),
         'httpStatus': fetched.get('status', 200),
         'skippedCount': parsed.get('skipped', 0)},
        retrieved_by=retrieved_by or 'climate.carbon_sinks_seed',
        row_count=len(records) * len(BUDGET_SERIES))

    written = {}
    for column, series_name in BUDGET_SERIES.items():
        count = 0
        for idx, rec in enumerate(records):
            value = rec.get(column)
            if value is None:
                continue
            try:
                AtmosphericObservation(
                    name=f'{series_name}--{idx:04d}',
                    series_ref=series_name, span_ref=BUDGET_SPAN,
                    year=rec['year'], value=value, uncertainty=0.0,
                    sample_count=0, revision='',
                    retrieval_ref=retrieval.get('name', ''),
                    is_prior=False, provenance_id=PROV, notes='',
                    manager=manager)
                count += 1
            except Exception:
                pass
        written[series_name] = count
    return {'ok': True, 'series': written,
            'years': len(records),
            'firstYear': parsed['firstYear'],
            'lastYear': parsed['lastYear'],
            'sha256': fetched.get('sha256', ''),
            'urlRedacted': fetched.get('url_redacted', ''),
            'note': ('each budget column is its own observation '
                     'series, so every budget number carries the '
                     'same provenance chain as every other '
                     'measurement here')}


def budget_records_from_rows(manager):
    """Reassemble the wide per-year budget from the stored
    per-column series. Refuses when nothing is ingested."""
    from composition.custom.data_refs import rows
    inverse = {v: k for k, v in BUDGET_SERIES.items()}
    by_year = {}
    for row in rows(manager, 'AtmosphericObservation'):
        column = inverse.get(getattr(row, 'series_ref', ''))
        if column is None:
            continue
        year = float(getattr(row, 'year', 0.0))
        by_year.setdefault(year, {'year': year})[column] = float(
            getattr(row, 'value', 0.0))
    if not by_year:
        return {'ok': False,
                'refusal': ('the carbon budget has not been '
                            'ingested - POST '
                            '/api/climate/ingest-budget first')}
    records = [by_year[y] for y in sorted(by_year)]
    for rec in records:
        for column in BUDGET_SERIES:
            rec.setdefault(column, None)
    return {'ok': True, 'records': records, 'count': len(records)}


def budget_graph_rows(manager):
    """Wide rows shaped for the differential/composition graphs:
    one object per year carrying every field those graph configs
    name in `yDimensions`."""
    loaded = budget_records_from_rows(manager)
    if not loaded.get('ok'):
        return loaded
    diff = source_sink_differential(loaded['records'])
    if not diff.get('ok'):
        return diff
    by_year = {r['year']: r for r in loaded['records']}
    out = []
    for entry in diff['years']:
        rec = by_year.get(entry['year'], {})
        out.append({
            'year': entry['year'],
            'sources': entry['sources'],
            'sinks': entry['sinks'],
            'differential': entry['differential'],
            'sinkShareOfSources': entry['sinkShareOfSources'],
            'oceanSink': rec.get('ocean_sink'),
            'landSink': rec.get('land_sink'),
            'cementSink': rec.get('cement_sink'),
            'atmosphericGrowth': entry['atmosphericGrowth'],
        })
    return {'ok': True, 'rows': out, 'count': len(out),
            'span': BUDGET_SPAN,
            'note': diff['note']}


def seed_carbon_sinks(manager):
    from climate.climate_basis import CarbonSinkSeries
    return upsert_seed_pairs(manager, [
        ('CarbonSinkSeries', CarbonSinkSeries,
         SEED_CARBON_SINK_SERIES),
    ], tag='ClimateSinkSeed')
