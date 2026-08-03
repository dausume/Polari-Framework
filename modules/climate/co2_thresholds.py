"""
@module climate.co2_thresholds

THE GRADED THRESHOLD TABLE (CO2_HEALTH_PLAN.md §5). Every CO2 level
at which something is claimed to happen to a person, each carrying
the GRADE of the evidence behind it and, where it exists, the work
that FAILED to replicate it.

The grading is the honesty. A ventilation standard's 1000 ppm and a
chamber study's 1000 ppm are not the same kind of number: one is an
indicator chosen because it was easy to measure, the other is a
contested effect size. Averaging them, or drawing them in one band,
is how a page becomes confidently wrong.

Two rules this module enforces in code rather than in prose:

  1. A DIFFERENTIAL threshold is not comparable with an ABSOLUTE one
     until outdoor CO2 is added to it (`absolute_ppm`). ASHRAE's
     criterion is "~700 ppm ABOVE outdoor", so the absolute level a
     fully compliant room may sit at RISES one-for-one with the
     outdoor background — a room can cross an absolute line with
     nothing about the room having changed.
  2. The table carries a NEGATIVE row (280 ppm, no effect). A page
     that lists only harms implies harm everywhere, and bounds
     nothing.

Every row here is transcribed from a source named in
`citation_text`; no number in this file is invented, interpolated or
rounded from memory. Rows that are priors say so, and each names in
`replaces_with` the work that would retire it.

@consumers climate.climate_views, climate.climate_api,
climate.co2_projection, climate.co2_indoor, polariServer (seed pass)
"""

from composition.data_refs import rows
from composition.seed_upsert import upsert_seed_pairs
from climate.climate_basis import CO2HealthThreshold, EVIDENCE_GRADES

#: Shared by the two chamber-study rows — one study, one citation.
_SATISH_CITATION = (
    'Satish U, Mendell MJ, Shekhar K, Hotchi T, Sullivan D, '
    'Streufert S, Fisk WJ. Is CO2 an Indoor Pollutant? Direct '
    'Effects of Low-to-Moderate CO2 Concentrations on Human '
    'Decision-Making Performance. Environ Health Perspect. '
    '2012;120(12):1671-1677.')
_SATISH_URL = 'https://ehp.niehs.nih.gov/doi/10.1289/ehp.1104789'

#: The replications that did NOT find it. Carried on both study
#: rows; a page that shows only the supporting citation is advocacy.
_SATISH_CONTESTED = (
    'Rodeheffer et al. 2018 (submariners) failed to replicate; '
    'Scully et al. 2019 (npj Microgravity, astronaut-like subjects) '
    'found no monotonic dose-response; Du et al. 2020 critical '
    'review (Indoor Air) concluded rigorously designed studies show '
    'no or only marginally significant effects except on the SMS '
    'battery.')

#: NIOSH/OSHA share one pocket-guide entry for CAS 124-38-9.
_NIOSH_CITATION = (
    'NIOSH REL 5000 ppm (9000 mg/m3) TWA; OSHA PEL 5000 ppm TWA. '
    'CDC/NIOSH Pocket Guide, chemical 124-38-9.')
_NIOSH_URL = ('https://www.cdc.gov/niosh/chemicals/pel88/'
              'pell-pages/124-38.html')

#: What retires a study row versus a standard row. Different kinds
#: of claim are retired by different kinds of work.
_REPLACES_STUDY = ('a pre-registered replication with a larger n '
                   'and blinded scoring')
_REPLACES_STANDARD = 'the next revision of the standard'

#: KEY: the two ASHRAE rows share ONE colour, and it is deliberately
#: NOT on the green->amber->red severity ramp: they are ventilation
#: INDICATORS, not harm levels, and colouring them by severity would
#: assert a hazard the standard explicitly declines to assert.
_INDICATOR_COLOR = '#3f7fbf'

SEED_CO2_THRESHOLDS = [
    {
        'name': 'co2-preindustrial-baseline',
        'display_name': 'Pre-industrial baseline (280 ppm)',
        'ppm': 280.0,
        'unit': 'ppm',
        'effect': 'The level human physiology evolved and lived '
                  'under for the whole Holocene; no evidence of any '
                  'CO2-attributable effect.',
        'population': 'general',
        'exposure': 'chronic',
        'evidence_grade': 'observational',
        'citation_text': 'Antarctic ice-core composite (Bereiter '
                         'et al. 2015), NOAA NCEI paleoclimatology',
        'doi_or_url': '',
        'is_differential': False,
        'differential_over': '',
        'contested_by': '',
        'color': '#2e8b57',
        'replaces_with': 'a revised ice-core composite',
        'is_prior': True,
        'provenance_id': 'co2-3',
        'notes': 'THE NEGATIVE ROW. It exists to bound the claim '
                 'space: a table that lists only harms implies harm '
                 'everywhere and gives the reader nothing to '
                 'measure "elevated" against. This is the level at '
                 'which nothing is claimed, and it is a real '
                 'measured level, not a rhetorical zero.',
    },
    {
        'name': 'co2-outdoor-present',
        'display_name': 'Present outdoor background (2025)',
        'ppm': 427.35,
        'unit': 'ppm',
        'effect': 'Present global outdoor background (Mauna Loa '
                  'annual mean 2025). No direct health effect '
                  'claimed at this level outdoors.',
        'population': 'general',
        'exposure': 'chronic',
        'evidence_grade': 'observational',
        'citation_text': 'NOAA GML, Mauna Loa annual mean CO2, '
                         '2025 = 427.35 +/- 0.12 ppm',
        'doi_or_url': '',
        'is_differential': False,
        'differential_over': '',
        'contested_by': '',
        'color': '#7cb342',
        'replaces_with': '',
        #: NOT a prior — this is a MEASURED value, ingested from
        #: NOAA GML, and the seed pass must never overwrite it with
        #: an assumption.
        'is_prior': False,
        'provenance_id': 'co2-3',
        'notes': 'The reference every indoor number is measured '
                 'FROM: the indoor coupling adds its ventilation '
                 'offset on top of THIS, and every differential '
                 'threshold becomes an absolute one by adding THIS. '
                 'When the ingest advances the outdoor value, every '
                 'differential row moves with it.',
    },
    {
        'name': 'ashrae-differential-700',
        'display_name': 'ASHRAE 62.1 criterion (+700 ppm over '
                        'outdoor)',
        'ppm': 700.0,
        'unit': 'ppm',
        'effect': 'ASHRAE 62.1 ventilation criterion: steady-state '
                  'indoor CO2 no greater than ~700 ppm ABOVE '
                  'outdoor. It is an INDICATOR that outdoor-air '
                  'ventilation meets the standard - a proxy for '
                  'odour/bioeffluent acceptability, NOT a health '
                  'threshold.',
        'population': 'general',
        'exposure': 'chronic',
        'evidence_grade': 'standard-or-guideline',
        'citation_text': 'ANSI/ASHRAE Standard 62.1; ASHRAE '
                         'position document on indoor carbon '
                         'dioxide (2022)',
        'doi_or_url': 'https://www.ashrae.org/file%20library/about/'
                      'government%20affairs/public%20policy%20'
                      'resources/briefs/indoor-carbon-dioxide-'
                      'ventilation-and-indoor-air-quality_2023.pdf',
        'is_differential': True,
        'differential_over': 'outdoor',
        'contested_by': '',
        'color': _INDICATOR_COLOR,
        'replaces_with': _REPLACES_STANDARD,
        'is_prior': True,
        'provenance_id': 'co2-3',
        'notes': 'THE CONSEQUENCE THAT MAKES THIS THE MOST '
                 'IMPORTANT ROW ON THE PAGE: because the criterion '
                 'is a DIFFERENTIAL, the absolute indoor level it '
                 'permits rises one-for-one with outdoor CO2. A '
                 'room that fully complies sat near 980 ppm when '
                 'outdoor was 280 ppm, and sits near 1127 ppm '
                 'today - nothing about the room changed, only the '
                 'air fed into it. Coloured as an INDICATOR, not '
                 'on the severity ramp: the standard asserts '
                 'ventilation adequacy, not harm.',
    },
    {
        'name': 'ashrae-indicator-1000',
        'display_name': 'The quoted 1000 ppm indoor figure',
        'ppm': 1000.0,
        'unit': 'ppm',
        'effect': 'The widely-quoted 1000 ppm indoor figure. '
                  'ASHRAE is explicit that its IAQ standards do '
                  'NOT use indoor CO2 values to determine '
                  'acceptable indoor air quality; 1000 ppm was an '
                  'easily-measured stand-in for other pollutants '
                  'and odours, never a hazard level.',
        'population': 'general',
        'exposure': 'chronic',
        'evidence_grade': 'standard-or-guideline',
        'citation_text': 'ASHRAE Technical FAQ / position document '
                         'on indoor CO2',
        'doi_or_url': '',
        'is_differential': False,
        'differential_over': '',
        'contested_by': '',
        'color': _INDICATOR_COLOR,
        'replaces_with': _REPLACES_STANDARD,
        'is_prior': True,
        'provenance_id': 'co2-3',
        'notes': 'This row exists to CORRECT a widespread '
                 'misreading, and the page must present it AS a '
                 'correction - not as a hazard line with a '
                 'citation. Shares the indicator colour with the '
                 '+700 row for the same reason: neither asserts an '
                 'effect on a person. If the page draws it as a '
                 'red line it has reproduced the error it exists '
                 'to fix.',
    },
    {
        'name': 'co2-cognitive-decrement-1000',
        'display_name': 'Decision-making decrement at 1000 ppm '
                        '(contested)',
        'ppm': 1000.0,
        'unit': 'ppm',
        'effect': 'Moderate, statistically significant decrements '
                  'in 6 of 9 decision-making scales versus 600 ppm '
                  'in a controlled chamber study (n=24).',
        'population': 'general',
        'exposure': 'hours',
        'evidence_grade': 'contested-controlled-study',
        'citation_text': _SATISH_CITATION,
        'doi_or_url': _SATISH_URL,
        'is_differential': False,
        'differential_over': '',
        'contested_by': _SATISH_CONTESTED,
        'color': '#d9a441',
        'replaces_with': _REPLACES_STUDY,
        'is_prior': True,
        'provenance_id': 'co2-3',
        'notes': 'The effect is real IN THAT STUDY and has '
                 'repeatedly failed to replicate. The page must '
                 'show both halves of that sentence together, and '
                 'must NOT draw this in the same band as an '
                 'occupational limit: one is a contested effect '
                 'measured on 24 people, the other is a regulatory '
                 'ceiling. Same axis, different kind of claim.',
    },
    {
        'name': 'co2-cognitive-decrement-2500',
        'display_name': 'Decision-making decrement at 2500 ppm '
                        '(contested)',
        'ppm': 2500.0,
        'unit': 'ppm',
        'effect': 'Large, statistically significant reductions in '
                  '7 of 9 decision-making scales versus 600 ppm '
                  '(same chamber study).',
        'population': 'general',
        'exposure': 'hours',
        'evidence_grade': 'contested-controlled-study',
        'citation_text': _SATISH_CITATION,
        'doi_or_url': _SATISH_URL,
        'is_differential': False,
        'differential_over': '',
        'contested_by': _SATISH_CONTESTED,
        'color': '#d97b29',
        'replaces_with': _REPLACES_STUDY,
        'is_prior': True,
        'provenance_id': 'co2-3',
        'notes': 'Same single chamber study as the 1000 ppm row, '
                 'same failed replications - so this is one '
                 'contested finding at two exposure levels, not '
                 'two independent findings. A dose-response drawn '
                 'through these two points is drawn through ONE '
                 'experiment.',
    },
    {
        'name': 'niosh-rel-twa-5000',
        'display_name': 'NIOSH REL / OSHA PEL, 8-hour TWA',
        'ppm': 5000.0,
        'unit': 'ppm',
        'effect': 'NIOSH recommended exposure limit / OSHA '
                  'permissible exposure limit, 8-hour '
                  'time-weighted average for HEALTHY ADULT WORKERS '
                  'over a work shift. Not a limit designed for '
                  'children, the sick, or continuous residential '
                  'exposure.',
        'population': 'occupational',
        'exposure': 'chronic',
        'evidence_grade': 'occupational-limit',
        'citation_text': _NIOSH_CITATION,
        'doi_or_url': _NIOSH_URL,
        'is_differential': False,
        'differential_over': '',
        'contested_by': '',
        'color': '#c0392b',
        'replaces_with': _REPLACES_STANDARD,
        'is_prior': True,
        'provenance_id': 'co2-3',
        'notes': 'Read the population field before quoting this '
                 'number at a bedroom: it is a shift limit for '
                 'working adults, and borrowing it as a household '
                 'safety line silently swaps the population the '
                 'limit was written for.',
    },
    {
        'name': 'niosh-stel-30000',
        'display_name': 'NIOSH STEL, 15-minute',
        'ppm': 30000.0,
        'unit': 'ppm',
        'effect': 'NIOSH short-term exposure limit (15-minute).',
        'population': 'occupational',
        'exposure': 'acute',
        'evidence_grade': 'occupational-limit',
        'citation_text': _NIOSH_CITATION,
        'doi_or_url': _NIOSH_URL,
        'is_differential': False,
        'differential_over': '',
        'contested_by': '',
        'color': '#8e1b12',
        'replaces_with': _REPLACES_STANDARD,
        'is_prior': True,
        'provenance_id': 'co2-3',
        'notes': 'A 15-minute ceiling, not a level anything is '
                 'meant to sit at. Plotting it beside chronic rows '
                 'without the exposure field visible compares a '
                 'quarter hour with a lifetime.',
    },
    {
        'name': 'niosh-idlh-40000',
        'display_name': 'NIOSH IDLH (4%)',
        'ppm': 40000.0,
        'unit': 'ppm',
        'effect': 'Immediately Dangerous to Life or Health.',
        'population': 'occupational',
        'exposure': 'acute',
        'evidence_grade': 'occupational-limit',
        'citation_text': 'NIOSH IDLH 40000 ppm (4%), chemical '
                         '124-38-9.',
        'doi_or_url': 'https://www.cdc.gov/niosh/idlh/124389.html',
        'is_differential': False,
        'differential_over': '',
        'contested_by': '',
        'color': '#5e0f0a',
        'replaces_with': _REPLACES_STANDARD,
        'is_prior': True,
        'provenance_id': 'co2-3',
        'notes': 'The top of the axis. It is here so the reader '
                 'can see how far the indoor and outdoor numbers '
                 'on this page sit BELOW it - roughly two orders '
                 'of magnitude - which is a finding in itself.',
    },
]

#: Strongest first. The judgement encoded here: a controlled human
#: exposure outranks a contested one; both outrank observation;
#: observation outranks a regulatory limit as EVIDENCE OF EFFECT
#: (a limit is a policy choice with a safety factor, not a
#: measurement); and a ventilation indicator that its own author
#: says is not a health value ranks below a limit that at least
#: intends to be one. Expert judgement is last because it names no
#: study at all.
_GRADE_STRENGTH = (
    'controlled-human-study',
    'contested-controlled-study',
    'observational',
    'occupational-limit',
    'standard-or-guideline',
    'expert-judgement',
)


def grade_rank(grade):
    """Ordering index for an evidence grade — 0 is strongest.

    An unknown grade sorts last (weaker than anything named), so a
    row with a typo'd grade can never outrank a real study.
    """
    try:
        return _GRADE_STRENGTH.index(grade)
    except ValueError:
        return len(_GRADE_STRENGTH)


def _f(row, attr, default=0.0):
    """Float attribute read that cannot raise into a caller."""
    try:
        return float(getattr(row, attr, default))
    except (TypeError, ValueError):
        return default


def _s(row, attr, default=''):
    value = getattr(row, attr, default)
    return default if value is None else str(value)


def seed_co2_thresholds(manager):
    return upsert_seed_pairs(
        manager,
        [('CO2HealthThreshold', CO2HealthThreshold,
          SEED_CO2_THRESHOLDS)],
        tag='ClimateThresholdSeed')


def absolute_ppm(threshold_row, outdoor_ppm):
    """The ONLY correct way to put differential and absolute
    thresholds on one axis: a differential is meaningless until
    the outdoor background it sits above is added to it.

    Returns a float; never raises.
    """
    ppm = _f(threshold_row, 'ppm')
    try:
        outdoor = float(outdoor_ppm)
    except (TypeError, ValueError):
        outdoor = 0.0
    if bool(getattr(threshold_row, 'is_differential', False)):
        return ppm + outdoor
    return ppm


def thresholds_report(manager):
    """Every threshold row, sorted by ppm, grouped by grade."""
    try:
        table = rows(manager, 'CO2HealthThreshold')
    except Exception as exc:
        return {'ok': False,
                'refusal': f'could not read CO2HealthThreshold '
                           f'rows: {exc}'}
    if not table:
        return {'ok': False,
                'refusal': 'no CO2HealthThreshold rows — run '
                           'seed_co2_thresholds(manager) first, or '
                           'the climate module is not booted'}
    entries = []
    for row in table:
        entries.append({
            'name': _s(row, 'name'),
            'displayName': _s(row, 'display_name') or _s(row, 'name'),
            'ppm': _f(row, 'ppm'),
            'effect': _s(row, 'effect'),
            'population': _s(row, 'population'),
            'exposure': _s(row, 'exposure'),
            'evidenceGrade': _s(row, 'evidence_grade'),
            'isDifferential': bool(
                getattr(row, 'is_differential', False)),
            'differentialOver': _s(row, 'differential_over'),
            'citationText': _s(row, 'citation_text'),
            'doiOrUrl': _s(row, 'doi_or_url'),
            'contestedBy': _s(row, 'contested_by'),
            'color': _s(row, 'color'),
        })
    entries.sort(key=lambda e: (e['ppm'], e['name']))
    by_grade = {}
    for grade in EVIDENCE_GRADES:
        names = [e['name'] for e in entries
                 if e['evidenceGrade'] == grade]
        if names:
            by_grade[grade] = names
    return {
        'ok': True,
        'thresholds': entries,
        'byGrade': by_grade,
        'note': 'Differential and absolute thresholds are NOT '
                'comparable on one axis until outdoor CO2 is added '
                'to the differential ones (absolute_ppm). ASHRAE '
                '62.1 permits ~700 ppm ABOVE outdoor, so the '
                'absolute level a compliant room may hold rises '
                'with the outdoor background — 980 ppm at a 280 '
                'ppm background, 1127 ppm at 427.35 ppm — with '
                'nothing about the room having changed. Grades do '
                'not average: a ventilation indicator, a contested '
                'chamber study and an occupational limit are three '
                'kinds of claim, and drawing them as one band is '
                'the error this table exists to prevent.',
    }
