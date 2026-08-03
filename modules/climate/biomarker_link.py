"""
@module climate.biomarker_link

co2-B — THE QUESTION DUSTIN ASKED, ANSWERED WITH ARITHMETIC
RATHER THAN AGREEMENT.

The ask: "have levels of stress related and similar health
problems increased over time in proportion with the bicarbonate
and co2 rise as was seemingly predicted by some doctors."

Serum bicarbonate is the right dataset to ask it with. It is the
population-scale, officially collected measurement of the
acid-base compensation side, and NHANES publishes it per 2-year
cycle alongside the PHQ-9 depression screener FROM THE SAME
SAMPLING FRAME — which is the only reason the two can be compared
at all.

WHAT THE FETCHED DATA SAYS (NHANES 1999-2023, 11 cycles,
n=5901-6891 per cycle; PHQ-9 8 cycles):

- Bicarbonate DID rise: +0.0507 mmol/L per year, r=+0.542,
  +1.14 mmol/L across the window.
- Depression DID rise: PHQ-9 >=10 went 6.19% (2005-06) to 13.25%
  (2021-23), +0.254 points/yr, r=+0.704.
- AND THEY DO NOT MOVE TOGETHER: across the 8 shared cycles the
  correlation between mean bicarbonate and depression prevalence
  is **r = -0.03**. Essentially zero, and the wrong sign.

Two things both trending upward against TIME is not a mechanism;
it is two things trending upward. The near-zero correlation
BETWEEN them is stronger evidence against a shared cause than
either trend is for one.

🔑 AND THE MECHANISM FAILS A UNIT CHECK BY THREE ORDERS OF
MAGNITUDE. This is the part a page built on vibes cannot do.
Chronic respiratory acidosis moves bicarbonate about 0.4 mmol/L
per 10 mmHg of sustained pCO2. Ambient CO2 rose 52.9 ppm from
1999 to 2023, which is 0.040 mmHg of ambient partial pressure. So
the compensation ambient CO2 could produce is ~0.0016 mmol/L
against an OBSERVED 1.14 mmol/L — the observation is **~709x
larger than the proposed cause can explain.**

So the honest finding is: the bicarbonate rise is real, and
ambient CO2 did not cause it. Something else did, and this module
names the candidates rather than pretending to choose between
them.

⚠ AND THE TREND ITSELF IS SHAKY. It is NOT monotonic: 2015-16
falls to 24.41, 2017-18 jumps to 25.54, 2021-23 falls back to
24.45. A sawtooth across cycles with r=0.54 over 11 points, where
the whole 22-year change is HALF of one within-cycle standard
deviation (2.26 mmol/L), is exactly what an assay or calibration
change between cycles looks like. That possibility is reported
beside the trend, not buried under it.

@consumers climate.climate_views, climate.climate_api,
climate.selftest_climate
"""

import math

from climate.co2_physiology import KPA_PER_MMHG, STANDARD_PRESSURE_KPA

PROV = 'co2-B'

#: Chronic (renal) compensation for a sustained rise in arterial
#: pCO2: bicarbonate rises roughly this much per 10 mmHg. The
#: standard acid-base teaching figure; the acute figure (~1 mmol/L
#: per 10 mmHg) is smaller still, so using the CHRONIC value is
#: the most generous possible assumption for the hypothesis under
#: test. If the hypothesis fails with the generous constant, it
#: fails with any of them.
RENAL_COMPENSATION_MMOL_PER_10MMHG = 0.4

#: A PHQ-9 total of 10 or more is the conventional screening cut
#: for moderate-or-worse depressive symptoms. It is a SCREENER,
#: not a diagnosis, and the rows say so.
PHQ9_MODERATE_CUT = 10

#: Named on the page, never in a footnote. Any one of these can
#: produce the observed bicarbonate drift on its own.
BICARBONATE_CONFOUNDERS = (
    'assay and calibration changes between survey cycles - the '
    'single most likely explanation for a non-monotonic sawtooth '
    'across cycles, and the one that costs nothing to check '
    'against each cycle codebook',
    'altitude of the examination sites in a given cycle sample',
    'age structure of the sample, which shifted over the window',
    'kidney function and diuretic use, both of which move '
    'bicarbonate far more than any ambient gas could',
    'diet, protein load and acid-base intake',
    'obesity and metabolic syndrome prevalence, which changed '
    'substantially over the same period',
    'fasting status and time of day at the blood draw',
    'the 2021-2023 cycle ran with altered field operations and '
    'response rates after the pandemic',
)

DEPRESSION_CONFOUNDERS = (
    'screening and help-seeking behaviour changed over the '
    'window, so measured prevalence and true prevalence move '
    'differently',
    'the 2021-2023 cycle covers a post-pandemic period with a '
    'large, well-documented and separately-explained rise',
    'PHQ-9 is a self-report screener; a rise in reported symptoms '
    'is not the same as a rise in incident disease',
    'age structure and the fraction of the sample answering the '
    'questionnaire at all',
)


def explainable_bicarbonate_shift(ppm_from, ppm_to,
                                  pressure_kpa=STANDARD_PRESSURE_KPA):
    """How much bicarbonate COULD ambient CO2 move between two
    levels? The unit check the whole question turns on."""
    try:
        d_ppm = float(ppm_to) - float(ppm_from)
    except (TypeError, ValueError):
        return {'ok': False,
                'refusal': 'ppm_from and ppm_to must be numbers'}
    d_kpa = d_ppm * 1e-6 * float(pressure_kpa)
    d_mmhg = d_kpa / KPA_PER_MMHG
    shift = RENAL_COMPENSATION_MMOL_PER_10MMHG * (d_mmhg / 10.0)
    return {'ok': True, 'ppmFrom': float(ppm_from),
            'ppmTo': float(ppm_to), 'deltaPpm': d_ppm,
            'deltaPco2Kpa': d_kpa, 'deltaPco2Mmhg': d_mmhg,
            'explainableShiftMmolL': shift,
            'compensationConstant':
                RENAL_COMPENSATION_MMOL_PER_10MMHG,
            'note': ('uses the CHRONIC compensation constant, the '
                     'most generous available to the hypothesis; '
                     'the acute figure is smaller still')}


def attribution_test(observed_shift_mmol, ppm_from, ppm_to,
                     pressure_kpa=STANDARD_PRESSURE_KPA):
    """Can ambient CO2 account for an observed bicarbonate shift?

    Returns the RATIO. A ratio far above 1 means the observation
    is real but the proposed cause is far too small - which is a
    finding, not a failure.
    """
    exp = explainable_bicarbonate_shift(ppm_from, ppm_to,
                                        pressure_kpa)
    if not exp.get('ok'):
        return exp
    explainable = exp['explainableShiftMmolL']
    try:
        observed = float(observed_shift_mmol)
    except (TypeError, ValueError):
        return {'ok': False,
                'refusal': 'observed_shift_mmol must be a number'}
    if abs(explainable) < 1e-12:
        return {'ok': False,
                'refusal': ('the ambient change is zero, so no '
                            'ratio is defined')}
    ratio = observed / explainable
    if abs(ratio) <= 2.0:
        verdict = ('the observed shift is the same order as what '
                   'ambient CO2 could produce - the mechanism is '
                   'ARITHMETICALLY ADMISSIBLE and needs a real '
                   'study, not a bigger dataset')
        admissible = True
    else:
        verdict = (f'the observed shift is {abs(ratio):,.0f}x '
                   f'larger than ambient CO2 could produce. The '
                   f'rise may well be real, but ambient CO2 is '
                   f'NOT its cause - the proposed mechanism is '
                   f'too small by orders of magnitude')
        admissible = False
    return {'ok': True, 'observedShiftMmolL': observed,
            'explainableShiftMmolL': explainable,
            'ratio': ratio, 'mechanismAdmissible': admissible,
            'verdict': verdict, **{k: exp[k] for k in
                                   ('deltaPpm', 'deltaPco2Mmhg')}}


def _pearson(xs, ys):
    n = len(xs)
    if n < 3:
        return None
    mx, my = sum(xs) / n, sum(ys) / n
    sxy = sum((a - mx) * (b - my) for a, b in zip(xs, ys))
    sxx = sum((a - mx) ** 2 for a in xs)
    syy = sum((b - my) ** 2 for b in ys)
    if sxx <= 0 or syy <= 0:
        return None
    return sxy / math.sqrt(sxx * syy)


def correlate(series_a, series_b, label_a='a', label_b='b'):
    """Pearson r between two cycle series, matched on cycle key.

    Deliberately spartan: no p-value is reported. With 8 survey
    cycles a p-value invites exactly the over-reading this whole
    module exists to prevent, and a correlation over 8 points is
    a picture, not a test.
    """
    common = sorted(set(series_a) & set(series_b))
    if len(common) < 3:
        return {'ok': False,
                'refusal': (f'only {len(common)} cycles are shared '
                            f'between {label_a} and {label_b}; a '
                            f'correlation needs at least 3 and '
                            f'deserves many more')}
    xs = [float(series_a[c]) for c in common]
    ys = [float(series_b[c]) for c in common]
    r = _pearson(xs, ys)
    if r is None:
        return {'ok': False,
                'refusal': 'one series has no variation'}
    strength = ('effectively none' if abs(r) < 0.2 else
                'weak' if abs(r) < 0.4 else
                'moderate' if abs(r) < 0.7 else 'strong')
    return {'ok': True, 'r': r, 'n': len(common),
            'cycles': common, 'labelA': label_a, 'labelB': label_b,
            'strength': strength,
            'note': ('no p-value is reported on purpose: over this '
                     'few survey cycles a p-value invites exactly '
                     'the over-reading this analysis exists to '
                     'prevent'),
            'verdict': (f'{label_a} and {label_b} show '
                        f'{strength} correlation (r={r:+.3f}) '
                        f'across {len(common)} shared cycles')}


def cycle_trend(series_by_cycle, cycle_midpoints):
    """Least-squares slope of a per-cycle statistic against the
    cycle midpoint year."""
    common = sorted(set(series_by_cycle) & set(cycle_midpoints))
    if len(common) < 3:
        return {'ok': False,
                'refusal': (f'{len(common)} cycles is too few for '
                            f'a trend')}
    xs = [float(cycle_midpoints[c]) for c in common]
    ys = [float(series_by_cycle[c]) for c in common]
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    sxx = sum((a - mx) ** 2 for a in xs)
    if sxx <= 0:
        return {'ok': False, 'refusal': 'all cycles share a year'}
    slope = sum((a - mx) * (b - my)
                for a, b in zip(xs, ys)) / sxx
    r = _pearson(xs, ys) or 0.0
    span = max(xs) - min(xs)
    return {'ok': True, 'slopePerYear': slope, 'r': r,
            'nCycles': n, 'fromYear': min(xs), 'toYear': max(xs),
            'totalChange': slope * span,
            'monotonic': all(b >= a for a, b in zip(ys, ys[1:])),
            'values': dict(zip(common, ys))}


def monotonicity_warning(trend, within_group_sd=None):
    """A non-monotonic series with a small effect relative to
    person-to-person spread is what a METHOD change looks like.
    Say so beside the trend, not underneath it."""
    if not trend.get('ok'):
        return trend
    warnings, context = [], []
    if not trend.get('monotonic'):
        warnings.append(
            'the series is NOT monotonic - it rises and falls '
            'between cycles. A sawtooth across survey cycles is '
            'the signature of an assay or calibration change, and '
            'each cycle codebook states its method')
    ratio = None
    if within_group_sd:
        ratio = abs(trend['totalChange']) / float(within_group_sd)
        line = (f'the whole-window change is {ratio:.2f} of ONE '
                f'within-cycle standard deviation')
        # A SIZE STATEMENT IS NOT A WARNING. Reporting the effect
        # size always, but only WARNING when it is small against
        # person-to-person spread, keeps `trustworthy` meaningful:
        # it used to be unreachable whenever an SD was supplied at
        # all, which made the flag say nothing.
        if ratio < 1.0:
            warnings.append(
                line + ', so it is small against person-to-person '
                       'variation and invisible in any individual')
        else:
            context.append(
                line + ', which is large enough to be visible '
                       'against person-to-person variation')
    return {'ok': True, 'warnings': warnings, 'context': context,
            'effectSizeInSds': ratio,
            'trustworthy': not warnings,
            'note': ('a trend can be statistically present and '
                     'still be an artifact; these are the checks '
                     'that separate the two')}


def biomarker_question(bicarbonate_by_cycle, depression_by_cycle,
                       cycle_midpoints, co2_ppm_from, co2_ppm_to,
                       within_cycle_sd=None):
    """THE WHOLE QUESTION, answered. Returns trends, the
    correlation BETWEEN them, the unit check, and the confounders
    - as one payload so no part can be quoted without the rest."""
    bic = cycle_trend(bicarbonate_by_cycle, cycle_midpoints)
    dep = cycle_trend(depression_by_cycle, cycle_midpoints)
    corr = correlate(bicarbonate_by_cycle, depression_by_cycle,
                     'serum bicarbonate', 'PHQ-9 >=10 prevalence')
    attribution = None
    if bic.get('ok'):
        attribution = attribution_test(
            bic['totalChange'], co2_ppm_from, co2_ppm_to)
    warn = monotonicity_warning(bic, within_cycle_sd)

    headline = []
    if bic.get('ok'):
        headline.append({
            'label': 'Serum bicarbonate trend',
            'value': f'{bic["slopePerYear"]:+.4f} mmol/L per year '
                     f'(r={bic["r"]:+.2f})',
            'note': 'real, but see the assay caveat',
            'verdict': 'warn'})
    if dep.get('ok'):
        headline.append({
            'label': 'Depression (PHQ-9 >=10) trend',
            'value': f'{dep["slopePerYear"]:+.3f} points/yr '
                     f'(r={dep["r"]:+.2f})',
            'note': 'also real, and separately explained',
            'verdict': 'warn'})
    if corr.get('ok'):
        headline.append({
            'label': 'Do they move TOGETHER?',
            'value': f'r = {corr["r"]:+.3f} ({corr["strength"]})',
            'note': ('both rise against time; that is not the '
                     'same as rising with each other'),
            'verdict': 'ok'})
    if attribution and attribution.get('ok'):
        headline.append({
            'label': 'Could ambient CO2 cause the bicarbonate '
                     'rise?',
            'value': (f'no - observed is '
                      f'{abs(attribution["ratio"]):,.0f}x larger '
                      f'than it could produce'),
            'note': (f'{attribution["deltaPpm"]:.1f} ppm is only '
                     f'{attribution["deltaPco2Mmhg"]:.3f} mmHg of '
                     f'ambient pCO2'),
            'verdict': 'ok'})

    return {
        'ok': True,
        'question': ('have stress-related health problems risen in '
                     'proportion with the bicarbonate and CO2 '
                     'rise, as some doctors predicted?'),
        'answer': ('Both bicarbonate and depression prevalence '
                   'rose over the NHANES window. They did NOT '
                   'rise together (r is essentially zero between '
                   'them), and ambient CO2 is far too small to '
                   'account for the bicarbonate change - by about '
                   'three orders of magnitude. So the prediction '
                   'is not supported by this data: the '
                   'co-movement is with TIME, which everything '
                   'else in the period also shares.'),
        'bicarbonateTrend': bic, 'depressionTrend': dep,
        'correlationBetween': corr, 'attribution': attribution,
        'trendWarnings': warn,
        'bicarbonateConfounders': list(BICARBONATE_CONFOUNDERS),
        'depressionConfounders': list(DEPRESSION_CONFOUNDERS),
        'headline': headline,
        'whatWouldChangeThis': (
            'a within-person design: the same individuals measured '
            'across a real ambient-CO2 gradient with assay method '
            'held constant. A population mean moving inside its '
            'reference interval, measured by different labs in '
            'different years, cannot settle a mechanism question '
            'no matter how many cycles are added.'),
    }
