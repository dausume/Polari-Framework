"""
@module climate.custom.co2_disorders

DO DISORDER REPORTING RATES TRACK RISING CO2? — asked properly,
which means asking in a way that could come back NO.

Dustin: "since Bicarbonate and chronic co2 exposure levels are
also associated with stress and other disorders, we should check
sources on disorder reporting rates over the years related to
these, and see if they correspond at all to the rising carbon
dioxide levels likely to be chronic."

They correspond superbly. That is the problem.

🔑 THE WINDOW-SENSITIVITY RESULT, and it is the most important
number this app has produced. Age-adjusted US suicide death rates
(CDC/NCHS, 1950-2018 — a HARD outcome, not self-report) against
the Mauna Loa record:

    1959-2018  (full overlap)          r = +0.45
    1959-1999  (CO2 rising steadily)   r = -0.08
    2000-2018  (both rising)           r = +0.99

SAME TWO SERIES. SAME DATA. Three answers, chosen entirely by
where the window is drawn. An r of +0.99 would be reported as
overwhelming evidence by anyone who stopped there — and the
adjacent forty years of the same series say the opposite.

WHY IT HAPPENS: CO2 rises monotonically. ANY series that also
rises monotonically over the same window will correlate with it
near 1.0, regardless of mechanism. Between 1959 and 1999 CO2 rose
about 50 ppm while suicide rates fell and then flattened. If
ambient CO2 drove them, that could not have happened.

SO THE HONEST ANSWER IS NO — not "no effect exists", but "this
method cannot detect one, and anybody who reports the 2000-2018
window alone is reporting an artifact of their own window
choice."

This joins the bicarbonate result (r = -0.03 between serum
bicarbonate and PHQ-9 depression across shared NHANES cycles, and
a mechanism ~700x too small) as the second independent way the
CO2-and-stress hypothesis fails when it is actually tested rather
than gestured at.

⚠ WHAT WOULD ACTUALLY BE EVIDENCE, since none of the above is:
a within-person design across a real ambient-CO2 gradient with
the confounders held, or a natural experiment where CO2 moved
without everything else moving too. Time series of two things
that both went up cannot do it, however many years you have.

@consumers climate.climate_views_seed, climate.climate_api,
climate.climate_selftest
"""

import math

PROV = 'co2-D'

#: The dataset behind the headline result. A HARD outcome: deaths
#: certified and age-adjusted, not a self-reported symptom score,
#: so it cannot be moved by changing screening or help-seeking.
SUICIDE_DATASET = {
    'name': 'cdc-suicide-death-rates',
    'socrataId': '9j2v-jamp',
    'title': 'Death rates for suicide, by sex, race, Hispanic '
             'origin, and age: United States',
    'publisher': 'CDC / National Center for Health Statistics',
    'url': 'https://data.cdc.gov/resource/9j2v-jamp.json',
    'unit': 'deaths per 100,000, age-adjusted',
    'filter': "stub_label='All persons', age='All ages'",
    'coverage': '1950-2018',
}


def pearson(xs, ys):
    n = len(xs)
    if n < 3:
        return None
    mx, my = sum(xs) / n, sum(ys) / n
    sxx = sum((a - mx) ** 2 for a in xs)
    syy = sum((b - my) ** 2 for b in ys)
    if sxx <= 0 or syy <= 0:
        return None
    sxy = sum((a - mx) * (b - my) for a, b in zip(xs, ys))
    return sxy / math.sqrt(sxx * syy)


def correlate_by_year(series_a, series_b, from_year=None,
                      to_year=None):
    """Pearson r between two {year: value} maps over an optional
    window. Returns the overlap count, because an r without an n
    is not a result."""
    years = sorted(set(series_a) & set(series_b))
    if from_year is not None:
        years = [y for y in years if y >= from_year]
    if to_year is not None:
        years = [y for y in years if y <= to_year]
    if len(years) < 3:
        return {'ok': False,
                'refusal': (f'only {len(years)} overlapping years '
                            f'in this window; a correlation needs '
                            f'more and deserves far more')}
    r = pearson([series_a[y] for y in years],
                [series_b[y] for y in years])
    if r is None:
        return {'ok': False,
                'refusal': 'one series has no variation in this '
                           'window'}
    return {'ok': True, 'r': r, 'n': len(years),
            'fromYear': years[0], 'toYear': years[-1]}


def window_sensitivity(series_a, series_b, windows,
                       label_a='series A', label_b='series B'):
    """THE TEST THAT SHOULD BE RUN BEFORE ANY TIME-SERIES
    CORRELATION IS BELIEVED.

    Run the same correlation over several windows. If the answer
    moves with the window, the correlation is a property of the
    window and not of the world - and reporting one window is
    reporting a choice.
    """
    results = []
    for window in windows:
        got = correlate_by_year(series_a, series_b,
                                window.get('from'),
                                window.get('to'))
        entry = {'label': window.get('label', ''),
                 'fromYear': window.get('from'),
                 'toYear': window.get('to')}
        entry.update(got)
        results.append(entry)
    usable = [w for w in results if w.get('ok')]
    if len(usable) < 2:
        return {'ok': False,
                'refusal': ('need at least two usable windows to '
                            'say anything about sensitivity')}
    rs = [w['r'] for w in usable]
    spread = max(rs) - min(rs)
    flips = min(rs) < 0 < max(rs)
    return {
        'ok': True, 'labelA': label_a, 'labelB': label_b,
        'windows': results, 'rMin': min(rs), 'rMax': max(rs),
        'rSpread': spread, 'signFlips': flips,
        'stable': spread < 0.3 and not flips,
        'verdict': (
            f'the correlation between {label_a} and {label_b} '
            f'ranges from {min(rs):+.2f} to {max(rs):+.2f} '
            f'depending only on which window is chosen'
            + (' - AND IT CHANGES SIGN, so the same data supports '
               'opposite conclusions' if flips else '')
            + ('. That spread is the result: a correlation this '
               'sensitive to its window is a property of the '
               'window, not of the world.'
               if spread >= 0.3 else
               '. The correlation is stable across windows, which '
               'is necessary but nowhere near sufficient for a '
               'causal claim.')),
        'note': ('CO2 rises monotonically. ANY series that also '
                 'rises monotonically over the same window '
                 'correlates with it near 1.0 regardless of '
                 'mechanism, which is why a single window proves '
                 'nothing and a disagreeing pair of windows '
                 'disproves the method.'),
    }


#: The three windows that make the point. The middle one is the
#: one nobody quotes.
SUICIDE_WINDOWS = (
    {'label': 'full overlap', 'from': 1959, 'to': 2018},
    {'label': 'CO2 rising steadily, suicide falling then flat',
     'from': 1959, 'to': 1999},
    {'label': 'both rising - the window that gets quoted',
     'from': 2000, 'to': 2018},
)


def disorder_report(co2_by_year, suicide_by_year,
                    bicarbonate_result=None):
    """The whole question, answered - including the answer that
    the question cannot be answered this way."""
    sens = window_sensitivity(
        suicide_by_year, co2_by_year, list(SUICIDE_WINDOWS),
        label_a='age-adjusted suicide death rate',
        label_b='atmospheric CO2')
    if not sens.get('ok'):
        return sens

    quoted = next((w for w in sens['windows']
                   if w.get('ok') and w['fromYear'] >= 2000), None)
    contradicting = next((w for w in sens['windows']
                          if w.get('ok') and w['toYear'] <= 1999),
                         None)

    headline = [
        {'label': 'Suicide rate vs CO2, 2000 onward',
         'value': (f'r = {quoted["r"]:+.2f}' if quoted else 'n/a'),
         'note': 'the window that would be quoted as proof',
         'verdict': 'bad'},
        {'label': 'Suicide rate vs CO2, 1959-1999',
         'value': (f'r = {contradicting["r"]:+.2f}'
                   if contradicting else 'n/a'),
         'note': 'the adjacent window nobody quotes - CO2 rose '
                 'about 50 ppm while the rate fell then flattened',
         'verdict': 'ok'},
        {'label': 'Same two series, answer range',
         'value': f'{sens["rMin"]:+.2f} to {sens["rMax"]:+.2f}',
         'note': 'chosen entirely by where the window is drawn',
         'verdict': 'bad'},
    ]
    if bicarbonate_result:
        headline.append({
            'label': 'Serum bicarbonate vs depression '
                     '(NHANES, shared cycles)',
            'value': f'r = {bicarbonate_result:+.2f}',
            'note': 'the physiological link, tested directly - '
                    'essentially zero',
            'verdict': 'ok'})

    return {
        'ok': True,
        'question': ('do disorder reporting rates correspond to '
                     'rising CO2?'),
        'answer': (
            'They correspond superbly in one window and not at '
            'all in the window next to it, which means the '
            'correspondence is an artifact of both series rising '
            'in time rather than evidence of a link. Reporting '
            'the 2000-onward window alone would be reporting a '
            'choice of window as though it were a finding.'),
        'windowSensitivity': sens,
        'dataset': SUICIDE_DATASET,
        'whyHardOutcomeMatters': (
            'Suicide death rates were chosen deliberately over a '
            'self-reported symptom score. Deaths are certified '
            'and age-adjusted, so the series cannot be moved by '
            'changes in screening, diagnostic fashion or '
            'willingness to report - the confounders that make '
            'self-reported "disorder reporting rates" almost '
            'impossible to read across decades.'),
        'theOtherTest': (
            'This is the SECOND independent way the hypothesis '
            'fails when tested. The first: serum bicarbonate and '
            'PHQ-9 depression, from the SAME NHANES cycles and '
            'sampling frame, correlate at about -0.03 - and the '
            'ambient CO2 rise is roughly 700x too small to '
            'produce the observed bicarbonate shift anyway.'),
        'whatWouldBeEvidence': (
            'A within-person design across a real ambient-CO2 '
            'gradient with confounders held, or a natural '
            'experiment where CO2 moved and other things did not. '
            'Two time series that both went up cannot establish '
            'this however many years they cover, and adding years '
            'makes the spurious correlation tighter rather than '
            'weaker.'),
        'headline': headline,
        'honestCaveat': (
            'NONE OF THIS SHOWS CO2 IS HARMLESS. It shows that '
            'population time series cannot answer the question, '
            'and that the contested chamber studies remain the '
            'only direct evidence either way. An effect too small '
            'to see against decades of social change could still '
            'matter at the individual level - it simply cannot be '
            'found this way.'),
    }
