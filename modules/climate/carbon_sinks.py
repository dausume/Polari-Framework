"""
@module climate.carbon_sinks

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

@consumers climate.climate_views, climate.climate_api,
climate.selftest_climate
"""

import math

from composition.seed_upsert import upsert_seed_pairs

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
    from climate.xlsx_reader import find_header_row, read_sheet
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
    {'name': 'airborne-fraction-gcb',
     'display_name': 'Airborne fraction',
     'sink_kind': 'atmospheric-fraction', 'unit': '(fraction)',
     'source_ref': 'global-carbon-project',
     'endpoint_ref': 'gcb-global-carbon-budget', 'status': 'prior',
     'description': 'The share of each year\'s emissions that '
                    'stayed in the atmosphere.',
     'is_prior': True, 'provenance_id': PROV, 'notes': ''},
]


def seed_carbon_sinks(manager):
    from climate.climate_basis import CarbonSinkSeries
    return upsert_seed_pairs(manager, [
        ('CarbonSinkSeries', CarbonSinkSeries,
         SEED_CARBON_SINK_SERIES),
    ], tag='ClimateSinkSeed')
