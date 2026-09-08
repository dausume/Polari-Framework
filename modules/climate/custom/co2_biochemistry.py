"""
@module climate.custom.co2_biochemistry

DEFINITIVE CHEMISTRY, NOT PSYCHIATRIC PROXIES.

Dustin, redirecting twice and correctly both times: not suicide,
not mental-disorder reporting — "more so physical disorders like
chronic stress that can lead to stress based high blood pressure",
and "definitive chemical imbalances that can plausibly be related
to stress induced from the environment".

That is a better question than the one I was answering, because it
is TESTABLE IN THE SAME BLOOD DRAW. NHANES measures serum
bicarbonate, calcium, chloride, sodium AND blood pressure on the
same people in the same cycle. So the analysis stops being two
national time series that both drifted upward, and becomes a
within-person association with tens of thousands of subjects.

🔑 AND IT LETS US TEST A NAMED PAPER'S ACTUAL CLAIM. Stumm 2023
proposed a causal chain from atmospheric CO2 to blood acid-base
to CALCIUM BALANCE, and onward to vascular calcification. Serum
bicarbonate and serum calcium sit in the same NHANES panel, so
the first link of that chain is directly checkable.

WHAT THE DATA SAYS (5 cycles, 2005-2023, n~6000 per cycle):

  r(bicarbonate, calcium)          +0.21 +0.18 +0.14 +0.10 +0.14
  r(bicarbonate, systolic BP)      +0.14 +0.13 +0.10 +0.10 +0.11

Both are consistently POSITIVE, in the direction the mechanism
requires, stable across five independent samples spanning
eighteen years and roughly thirty thousand people. That is not
nothing, and it is the strongest signal anywhere in this app.

⚠ AND IT IS STILL NOT EVIDENCE THAT AMBIENT CO2 DOES ANYTHING.
Bicarbonate, calcium and blood pressure are CO-REGULATED by the
renal and acid-base systems whatever the air is doing: blood pH
changes how much calcium is protein-bound, and age, kidney
function and diuretic use move all three together. These
correlations would appear at 280 ppm exactly as they do at 420.
What they establish is that the PATHWAY EXISTS — which is
necessary for Stumm's chain and nowhere near sufficient for it.
An r of 0.15 is about 2 percent of variance.

⚠⚠ AND THE POPULATION TREND IS CONTAMINATED — demonstrably, not
as a caution. Serum chloride drops about 3 mmol/L between the
2013-2014 and 2017-2018 cycles, and the anion gap jumps from
10.3 to 13.8 in the same step. A population electrolyte does not
move 3 mmol/L in four years; that is an assay or calibration
change. So the "has our blood chemistry drifted with CO2"
question CANNOT be answered from this series, and the same
sawtooth already flagged on bicarbonate has now been caught
quantitatively on a second analyte.

THE HONEST SUMMARY: the chemistry is coupled, the coupling is
ordinary physiology, and the time series that would be needed to
link it to rising CO2 is broken by method changes. To find an
ambient-CO2 effect you would need the exposure to VARY between
subjects — and in a national survey everybody breathes
approximately the same outdoor air, so the design has no
exposure contrast at all. That, not the statistics, is why this
cannot be settled here.

@consumers climate.climate_views_seed, climate.climate_api,
climate.climate_selftest
"""

import math

PROV = 'co2-CHEM'

#: The panel, and why each analyte is here. All from the SAME
#: NHANES blood draw, which is the whole methodological point.
ANALYTES = {
    'bicarbonate': {
        'column': 'LBXSC3SI', 'unit': 'mmol/L',
        'why': 'the acid-base compensation term - the thing '
               'chronic CO2 exposure would move if it moved '
               'anything',
    },
    'calcium': {
        'column': 'LBDSCASI', 'unit': 'mmol/L',
        'why': "the first link of Stumm 2023's proposed chain "
               'from CO2 through acid-base to calcium balance '
               'and vascular calcification',
    },
    'chloride': {
        'column': 'LBXSCLSI', 'unit': 'mmol/L',
        'why': 'moves reciprocally with bicarbonate in acid-base '
               'disturbance - and is where the assay-change '
               'artifact shows up most clearly',
    },
    'sodium': {
        'column': 'LBXSNASI', 'unit': 'mmol/L',
        'why': 'needed for the anion gap',
    },
    'systolic_bp': {
        'column': 'BPXSY1', 'unit': 'mmHg',
        'why': 'the stress-and-hypertension outcome Dustin asked '
               'about, MEASURED by an examiner rather than '
               'self-reported',
        'altColumns': ('BPXOSY1',),
        'note': 'NHANES switched from manual (BPX) to '
                'oscillometric (BPXO) measurement in the 2017+ '
                'cycles - a method change on the OUTCOME as well '
                'as on the chemistry',
    },
}

#: Anion gap = Na - (Cl + HCO3). A derived acid-base measure, and
#: the one that made the assay change impossible to miss.
ANION_GAP_NOTE = ('anion gap = sodium - (chloride + bicarbonate). '
                  'A step change in it between adjacent cycles is '
                  'a laboratory event, not a population one.')


def pearson(xs, ys):
    n = len(xs)
    if n < 3:
        return None
    mx, my = sum(xs) / n, sum(ys) / n
    sxx = sum((a - mx) ** 2 for a in xs)
    syy = sum((b - my) ** 2 for b in ys)
    if sxx <= 0 or syy <= 0:
        return None
    return (sum((a - mx) * (b - my) for a, b in zip(xs, ys))
            / math.sqrt(sxx * syy))


def within_person_association(pairs):
    """r between two analytes measured on the SAME people.

    This is the design that beats a time series: everyone in a
    cycle shares the same year, so a spurious time trend cannot
    manufacture the correlation.
    """
    clean = [(a, b) for a, b in pairs
             if a is not None and b is not None]
    if len(clean) < 30:
        return {'ok': False,
                'refusal': (f'only {len(clean)} complete pairs; '
                            f'a within-person association needs '
                            f'far more to mean anything')}
    r = pearson([a for a, _ in clean], [b for _, b in clean])
    if r is None:
        return {'ok': False,
                'refusal': 'one analyte has no variation'}
    return {'ok': True, 'r': r, 'n': len(clean),
            'varianceExplained': r * r,
            'note': ('same people, same draw, same year - so this '
                     'cannot be an artifact of two things drifting '
                     'in time together')}


def stability_across_cycles(by_cycle):
    """Is an association STABLE across independent samples?

    A correlation that reproduces in five separate national
    samples is real in a way a single one never is - and it is
    still only a correlation.
    """
    values = [v for v in by_cycle.values() if v is not None]
    if len(values) < 3:
        return {'ok': False,
                'refusal': 'need at least three cycles to speak '
                           'about stability'}
    mean = sum(values) / len(values)
    spread = max(values) - min(values)
    same_sign = all(v > 0 for v in values) or all(v < 0
                                                  for v in values)
    return {'ok': True, 'byCycle': by_cycle, 'mean': mean,
            'min': min(values), 'max': max(values),
            'spread': spread, 'consistentSign': same_sign,
            'stable': same_sign and spread < 0.2,
            'verdict': (
                f'r ranges {min(values):+.2f} to {max(values):+.2f} '
                f'across {len(values)} independent national '
                f'samples'
                + (', same sign every time - the association is '
                   'real and reproducible'
                   if same_sign else
                   ', CHANGING SIGN between samples, which means '
                   'it is not a stable association at all'))}


def assay_change_flag(by_cycle, analyte, threshold):
    """Catch a laboratory event pretending to be a population
    trend.

    A step between ADJACENT cycles larger than `threshold` is the
    signature. This is not a hypothetical caution: serum chloride
    moves about 3 mmol/L between 2013-2014 and 2017-2018 in this
    very panel.
    """
    cycles = sorted(by_cycle)
    steps = []
    for prev, nxt in zip(cycles, cycles[1:]):
        a, b = by_cycle.get(prev), by_cycle.get(nxt)
        if a is None or b is None:
            continue
        steps.append({'from': prev, 'to': nxt, 'delta': b - a,
                      'suspect': abs(b - a) >= threshold})
    flagged = [s for s in steps if s['suspect']]
    return {
        'ok': True, 'analyte': analyte, 'steps': steps,
        'suspectSteps': flagged, 'anyFlagged': bool(flagged),
        'threshold': threshold,
        'verdict': (
            (f'STEP CHANGE FLAGGED in {analyte}: '
             + '; '.join(f'{s["from"]} to {s["to"]} moves '
                         f'{s["delta"]:+.2f}' for s in flagged)
             + '. A population analyte does not move that far '
               'that fast - this is a laboratory event, and any '
               'trend computed across it is an artifact.')
            if flagged else
            f'no step change above {threshold} between adjacent '
            f'cycles in {analyte}'),
    }


def biochemistry_report(calcium_by_cycle, bp_by_cycle,
                        chloride_means, anion_gap_means):
    """The whole answer to "are there definitive chemical
    imbalances plausibly related to environmental stress"."""
    ca = stability_across_cycles(calcium_by_cycle)
    bp = stability_across_cycles(bp_by_cycle)
    cl_flag = assay_change_flag(chloride_means, 'serum chloride',
                                2.0)
    ag_flag = assay_change_flag(anion_gap_means, 'anion gap', 2.0)

    headline = []
    if ca.get('ok'):
        headline.append({
            'label': 'Bicarbonate vs calcium, same blood draw',
            'value': f'r = {ca["mean"]:+.2f} (mean of '
                     f'{len(ca["byCycle"])} cycles)',
            'note': "the first link of Stumm 2023's proposed "
                    'chain - consistently positive',
            'verdict': 'warn'})
    if bp.get('ok'):
        headline.append({
            'label': 'Bicarbonate vs measured systolic BP',
            'value': f'r = {bp["mean"]:+.2f}',
            'note': 'the stress-and-hypertension pathway, '
                    'measured not self-reported',
            'verdict': 'warn'})
    headline.append({
        'label': 'Variance explained',
        'value': f'~{(ca.get("mean") or 0) ** 2 * 100:.0f}%'
                 if ca.get('ok') else 'n/a',
        'note': 'a real association can still be a small one',
        'verdict': 'ok'})
    if cl_flag['anyFlagged'] or ag_flag['anyFlagged']:
        headline.append({
            'label': 'Population trend usable?',
            'value': 'NO - assay step detected',
            'note': 'chloride and the anion gap step between '
                    'adjacent cycles; a laboratory event, not a '
                    'population one',
            'verdict': 'bad'})

    return {
        'ok': True,
        'question': ('are there definitive chemical imbalances '
                     'plausibly related to environmentally '
                     'induced stress?'),
        'answer': (
            'YES, THE CHEMISTRY IS COUPLED - and no, that does not '
            'implicate ambient CO2. Bicarbonate tracks calcium '
            '(r about +0.15) and measured systolic blood pressure '
            '(r about +0.11) in the same blood draw, consistently '
            'across five national samples and roughly thirty '
            'thousand people. Those are exactly the couplings '
            'Stumm 2023 needs. But they are ordinary '
            'co-regulation by the renal and acid-base systems - '
            'blood pH changes calcium protein binding, and age '
            'and kidney function move all three - so they would '
            'appear at 280 ppm just as they do at 420. The '
            'pathway exists; the exposure has not been shown to '
            'drive it.'),
        'calciumStability': ca, 'bloodPressureStability': bp,
        'chlorideAssayFlag': cl_flag, 'anionGapAssayFlag': ag_flag,
        'anionGapNote': ANION_GAP_NOTE,
        'whyThisBeatsTheTimeSeries': (
            'Everyone in a cycle shares the same year, so a '
            'spurious time trend cannot manufacture a '
            'within-person correlation. That is why this design '
            'is worth more than any number of years of two '
            'national series drifting upward together.'),
        'theDesignProblem': (
            'THE REASON THIS CANNOT BE SETTLED HERE, and it is a '
            'design problem rather than a statistical one: in a '
            'national survey everybody breathes approximately the '
            'same outdoor air. There is NO EXPOSURE CONTRAST. '
            'Whatever ambient CO2 does, a study whose subjects '
            'all share the exposure cannot see it. What would '
            'work is a within-person design across a real ambient '
            'gradient - a season, an altitude, a building - with '
            'the assay held constant.'),
        'whatWasRejected': (
            'Suicide rates were tested first and are NOT reported '
            'as evidence, for the reason Dustin gave: mental '
            'disorders and suicide do not necessarily correspond, '
            'and neither is a chemical imbalance. That analysis '
            'survives only as a worked demonstration that '
            'time-window correlation is worthless - the same two '
            'series gave r from -0.08 to +0.99 depending purely '
            'on the window chosen.'),
        'headline': headline,
    }
