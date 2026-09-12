"""
@module climate.climate_history_seed

WHAT CO2 DID HUMANS ACTUALLY LIVE IN — the 800,000-year
Antarctic ice-core composite read as human history, plus the
SPLICE that joins it to the instrumental record without hiding
the seam.

Every ppm figure seeded here was computed on 2026-08-02 from the
Bereiter et al. 2015 Antarctic composite (NOAA NCEI study 17975,
1901 points, ages -51 to 805669 cal BP, converted with
year_CE = 1950 - age_BP). They are OBSERVED ranges over each
era's window, not literature recollections.

THE HEADLINE, AND ITS LIMIT. Excluding the last millennium the
composite's maximum is 298.6 ppm over 1681 points; the Mauna Loa
2025 annual mean is 427.35 ppm. Today is 1.43x the 800-kyr
maximum. That comparison is sound FOR THE LEVEL. It is NOT a
rate comparison — an ice core's gas age is smoothed by firn
diffusion and sampled centuries apart, so it cannot resolve a
decade. The rate claim is a separate, stronger claim, and
climate.custom.co2_trend makes it from the instrumental growth-rate
series where the sampling supports it.

THREE THINGS THIS FILE REFUSES TO DO:

1. Seed a prehistoric life expectancy. Skeletal-age
   paleodemography carries error bars wider than any difference
   it could show and is not a period life table. The field is
   present, set to 0.0, and its basis says so.
2. Drop an era with no data. An era with nPoints 0 is REPORTED
   with 0 — an absent bucket is a finding about coverage.
3. Answer the cognition question. See COGNITION_QUESTION: no
   measurement of cognitive performance exists for any
   prehistoric population, so this record cannot answer it in
   either direction, and a page that draws a line anyway is
   inventing the evidence it lacks.

@consumers climate.climate_views_seed, climate.climate_api,
climate.custom.co2_trend, climate.selftest_co2, polariServer (seed)
"""

#: Provenance tag for every row this file seeds.
PROV = 'co2-H'

#: The series these engines read by default.
ICE_SERIES = 'co2-ice-core-composite'

#: The ingest that fills it, named in every refusal so the
#: refusal carries its own retirement.
ICE_INGEST = ("climate.custom.series_ingest.ingest_series(manager, "
              "'co2-ice-core-composite', "
              "'ncei-antarctica-co2-composite', ...)")

#: Preference order when two spans cover the same years. A direct
#: instrument reading beats trapped firn air, which beats a
#: bubble in ice.
DEFAULT_PREFER_ORDER = ('direct-instrument', 'firn-air',
                        'ice-core')

#: Nearest-year tolerance when pairing two overlapping segments
#: for the cross-check. Wider than this is not the same year.
OVERLAP_MATCH_YEARS = 5.0

#: Observed over the whole composite, 2026-08-02.
RECORD_MIN_PPM = 173.7
RECORD_MAX_PPM = 368.0
#: Excluding the last millennium (year < 1000 CE).
PRE_MILLENNIUM_MAX_PPM = 298.6
PRE_MILLENNIUM_POINTS = 1681
#: NOAA GML Mauna Loa annual mean, 2025.
PRESENT_PPM_2025 = 427.35

#: The dangerous field. Never seeded with a number.
LE_NOT_SET = (
    'NOT SET - paleodemographic life expectancy is a skeletal-'
    'age estimate with error bars wider than any difference it '
    'could show, and it is not comparable to a modern period '
    'life table')

#: For the eras where a real series exists, the seed defers to it.
LE_FROM_API = (
    'ingested from CDC/NCHS w9j2-ggv5, not seeded - see the '
    'life-expectancy series')

#: Appended to every era whose numbers come from the ice.
RESOLUTION_NOTE = (
    'ice-core gas ages are smoothed by firn diffusion and by '
    'sample spacing of centuries to millennia, so this era\'s '
    'range is NOT a record of year-to-year variation - it is '
    'the spread of the samples that happen to fall in the '
    'window')

#: population_estimate is left at 0.0 everywhere for the same
#: reason as life expectancy: HYDE/McEvedy reconstructions are
#: not ingested here, and a seeded number would look measured.
POP_NOTE = ('population_estimate 0.0 = NOT SET; no population '
            'reconstruction is ingested by this app')

CITE_ICE = (
    'Bereiter, B., et al. (2015). Revision of the EPICA Dome C '
    'CO2 record from 800 to 600 kyr before present. Geophysical '
    'Research Letters 42, 542-549. NOAA NCEI paleo study 17975, '
    'Antarctic ice-core CO2 composite (1901 points, -51 to '
    '805669 cal BP), retrieved 2026-08-02.')
URL_ICE = 'https://www.ncei.noaa.gov/access/paleo-search/study/17975'

CITE_MLO = (
    'NOAA Global Monitoring Laboratory, Mauna Loa Observatory '
    'annual mean CO2 (Keeling curve), 2025 annual mean 427.35 '
    'ppm, retrieved 2026-08-02.')
URL_MLO = 'https://gml.noaa.gov/ccgg/trends/data.html'

#: Era boundaries are archaeological consensus RANGES.
BOUNDARY_NOTE = ('era boundaries are archaeological consensus '
                 'ranges, not measurements')


def _era(name, display_name, from_year, to_year, description,
         color, notes, life_basis=LE_NOT_SET, citation=CITE_ICE,
         url=URL_ICE):
    """One HumanEraDefinition seed. Keys match the class'
    __init__ kwargs exactly — nothing extra, nothing missing."""
    return {
        'name': name,
        'display_name': display_name,
        'from_year': from_year,
        'to_year': to_year,
        'description': description,
        'life_expectancy_at_birth': 0.0,
        'life_expectancy_basis': life_basis,
        'life_expectancy_is_estimate': True,
        'population_estimate': 0.0,
        'citation_text': citation,
        'doi_or_url': url,
        'color': color,
        'is_prior': True,
        'provenance_id': PROV,
        'notes': notes,
    }


#: The eras, oldest first. from_year/to_year are calendar years
#: CE; negative = BCE; converted from the composite's cal BP with
#: year = 1950 - age. Windows OVERLAP on purpose (pre-industrial
#: sits inside the industrial revolution's opening decades) —
#: bucketing counts a point in every era that contains it.
SEED_HUMAN_ERAS = [
    _era('homo-sapiens-emerges', 'Homo sapiens emerges',
         -298050.0, -248050.0,
         'The 300-250 kya window around the earliest anatomically '
         'modern human fossils (Jebel Irhoud, Omo Kibish). The '
         'ice-core composite records 184.7-236.1 ppm across it '
         '(48 samples) - the whole window sits below any '
         'pre-industrial Holocene level.',
         '#6b4f2a',
         'Prehistoric: ' + RESOLUTION_NOTE + '. ' + BOUNDARY_NOTE
         + '. ' + POP_NOTE),
    _era('behavioural-modernity', 'Behavioural modernity',
         -73050.0, -63050.0,
         'The ~70 kya window associated with the spread of '
         'symbolic behaviour, blade tools and long-distance '
         'exchange. The composite records 215.6-239.5 ppm here '
         '(10 samples).',
         '#7d5a35',
         'Prehistoric: ' + RESOLUTION_NOTE + '. Ten samples over '
         'ten millennia is the coverage, and it is why no '
         'variability claim can be made inside this era. '
         + BOUNDARY_NOTE + '. ' + POP_NOTE),
    _era('last-glacial-maximum', 'Last glacial maximum',
         -21050.0, -16050.0,
         'The ~20 kya cold extreme. The composite records the '
         'lowest air humans are known to have lived in: '
         '183.1-197.7 ppm (31 samples), close to the whole '
         'record minimum of 173.7 ppm.',
         '#3f6f8f',
         'Prehistoric: ' + RESOLUTION_NOTE + '. ' + BOUNDARY_NOTE
         + '. ' + POP_NOTE),
    _era('agriculture-begins', 'Agriculture begins',
         -8050.0, -6050.0,
         'The 10-8 kya Neolithic transition in the Fertile '
         'Crescent and independently elsewhere. The composite '
         'records 247.6-270.1 ppm (48 samples): farming was '
         'invented in air well below the modern level.',
         '#6f8f3f',
         'Prehistoric: ' + RESOLUTION_NOTE + '. ' + BOUNDARY_NOTE
         + '. ' + POP_NOTE),
    _era('bronze-age', 'Bronze age',
         -3000.0, -2000.0,
         'Around 3000 BCE - writing, cities, alloyed metal. The '
         'composite records a narrow 268.6-271.5 ppm (4 samples) '
         'across the window.',
         '#8f7f3f',
         'Four samples across a millennium: ' + RESOLUTION_NOTE
         + '. ' + BOUNDARY_NOTE + '. ' + POP_NOTE),
    _era('roman-era', 'Roman era',
         -200.0, 200.0,
         'The turn of the era. The composite records 276.7-278.1 '
         'ppm (9 samples) - a 1.4 ppm spread over four '
         'centuries.',
         '#9f8f5f',
         RESOLUTION_NOTE + '. ' + BOUNDARY_NOTE + '. ' + POP_NOTE),
    _era('pre-industrial', 'Pre-industrial (1700-1800 CE)',
         1700.0, 1800.0,
         'The century before large-scale coal. The composite '
         'records 273.1-282.8 ppm (16 samples). This is the '
         'baseline every "since pre-industrial" figure is '
         'measured from.',
         '#c0a060',
         'Higher-resolution Law Dome material dominates the '
         'composite here, but ' + RESOLUTION_NOTE + '. '
         + POP_NOTE),
    _era('industrial-revolution', 'Industrial revolution',
         1750.0, 1900.0,
         'Coal, steam and the first sustained departure from the '
         'Holocene band. The record crosses out of the 173.7-'
         '298.6 ppm envelope that held for the previous 800,000 '
         'years during this era; the ice/firn composite reaches '
         'only 368.0 ppm at its most recent sample, so the level '
         'after this era must be read from the instrumental '
         'record, not the ice.',
         '#b07030',
         'Deliberately OVERLAPS pre-industrial (1750-1800): the '
         'eras are windows, not a partition, and a point counts '
         'in every window that contains it. ' + POP_NOTE),
    _era('twentieth-century', 'Twentieth century',
         1900.0, 2000.0,
         'The instrumental era. Mauna Loa observations begin in '
         '1958 and the ice-core composite ends, so this era is '
         'where the record becomes a SPLICE of two measurement '
         'kinds rather than one archive.',
         '#c04030',
         'Life expectancy for this era comes from the CDC/NCHS '
         'series, not from this seed. ' + POP_NOTE,
         life_basis=LE_FROM_API, citation=CITE_MLO, url=URL_MLO),
    _era('present', 'Present (2000-2026)',
         2000.0, 2026.0,
         'The Mauna Loa 2025 annual mean is 427.35 ppm. Against '
         'the 298.6 ppm maximum of the composite before 1000 CE '
         '(1681 points) that is 1.43x - the level is outside '
         'anything the ice-core record shows a human population '
         'living in.',
         '#8b1a1a',
         'The ice-core composite does not cover this era at all; '
         'a summary that reports nPoints 0 here is CORRECT, not '
         'broken - it is the seam. Life expectancy comes from '
         'the CDC/NCHS series. ' + POP_NOTE,
         life_basis=LE_FROM_API, citation=CITE_MLO, url=URL_MLO),
]


COGNITION_QUESTION = """\
WERE HUMAN MENTAL CAPABILITIES AFFECTED BY THE CO2 OF PAST
PERIODS? This record cannot answer that, and here is exactly why.

(a) NO MEASUREMENT EXISTS. There is no measurement of cognitive
performance for any prehistoric population - no test, no proxy
with a validated mapping to one, nothing. So the question
"were mental capabilities impacted in past periods by CO2"
cannot be answered from this record in EITHER direction. Not
"probably not", not "slightly": the observation that would
decide it was never made and cannot now be made.

(b) THE DIRECTION WOULD RUN THE OTHER WAY ANYWAY. The ice cores
show humans evolving, spreading and inventing agriculture at
roughly 180-280 ppm - BELOW today's 427 ppm, and the last
glacial maximum's 183-198 ppm is the lowest of all. So any
CO2-cognition effect read off this record would have to claim
that lower CO2 impaired them, which is the opposite of the
modern indoor concern. Anyone using this curve to argue past
humans were cognitively limited by their air has the sign
backwards.

(c) THE MODERN LITERATURE IS CONTESTED AND IS ABOUT A DIFFERENT
EXPOSURE. Satish et al. (2012) reported large decision-making
decrements at 1000-2500 ppm; Rodeheffer et al. (2018), Scully
et al. (2019) and Du et al. (2020) failed to reproduce effects
of that size, and reviews disagree about whether any effect
survives controls for ventilation, bioeffluents and
expectancy. All of it concerns ACUTE INDOOR exposure at
1000-2500 ppm over hours - not chronic outdoor background at
300-430 ppm. Carrying an indoor finding onto the outdoor curve
is a category error even where the indoor finding holds.

(d) WHAT WOULD ACTUALLY BE EVIDENCE. A within-population,
pre-registered, blinded exposure study - participants as their
own controls, CO2 varied independently of ventilation rate and
bioeffluents, cognitive outcomes specified in advance. That
design exists for acute indoor levels and disagrees with
itself. For chronic outdoor background levels it DOES NOT
EXIST, and no amount of curve-fitting between an ice core and
a test score would substitute for it.

This is what the page shows where a lesser page would show a
correlation.
"""


def _refuse(text):
    """Every failure leaves by this door."""
    return {'ok': False, 'refusal': text}


def _observation_rows(manager, series_name):
    """(year, value) pairs for one series, sorted by year."""
    from composition.custom.data_refs import rows
    out = []
    for row in rows(manager, 'AtmosphericObservation'):
        if getattr(row, 'series_ref', '') != series_name:
            continue
        try:
            year = float(getattr(row, 'year', 0.0))
            value = float(getattr(row, 'value', 0.0))
        except (TypeError, ValueError):
            continue
        out.append((year, value))
    out.sort(key=lambda pair: pair[0])
    return out


def _era_dicts(manager):
    """Seeded rows if the table is populated, else the constants
    — so the summary works before the first seed pass."""
    from composition.custom.data_refs import rows
    live = []
    for row in rows(manager, 'HumanEraDefinition'):
        live.append({
            'name': getattr(row, 'name', ''),
            'display_name': getattr(row, 'display_name', ''),
            'from_year': float(getattr(row, 'from_year', 0.0)),
            'to_year': float(getattr(row, 'to_year', 0.0)),
            'description': getattr(row, 'description', ''),
            'life_expectancy_basis': getattr(
                row, 'life_expectancy_basis', ''),
        })
    if live:
        live.sort(key=lambda era: era['from_year'])
        return live
    return [{
        'name': era['name'],
        'display_name': era['display_name'],
        'from_year': era['from_year'],
        'to_year': era['to_year'],
        'description': era['description'],
        'life_expectancy_basis': era['life_expectancy_basis'],
    } for era in SEED_HUMAN_ERAS]


def _year_label(year):
    """-3000 -> '3000 BCE'; 1750 -> '1750 CE'."""
    try:
        value = float(year)
    except (TypeError, ValueError):
        return str(year)
    if value < 0:
        return f'{abs(value):.0f} BCE'
    return f'{value:.0f} CE'


def era_co2_summary(manager, series_name=ICE_SERIES):
    """What CO2 each human era actually lived in.

    Buckets the ingested composite into the seeded eras. Eras
    with no coverage are REPORTED with nPoints 0 - the absence
    is where the ice record ends and the instrument begins.
    """
    points = _observation_rows(manager, series_name)
    if not points:
        return _refuse(
            f'no AtmosphericObservation rows for series '
            f'{series_name!r} - nothing to bucket into eras. '
            f'Run {ICE_INGEST} and this refusal retires.')
    eras = _era_dicts(manager)
    if not eras:
        return _refuse(
            'no HumanEraDefinition rows and no seed constants - '
            'call climate.climate_history_seed.seed_human_eras(manager)')
    out = []
    for era in eras:
        low = min(era['from_year'], era['to_year'])
        high = max(era['from_year'], era['to_year'])
        vals = [value for year, value in points
                if low <= year <= high]
        entry = {
            'name': era['name'],
            'displayName': era['display_name'],
            'fromYear': era['from_year'],
            'toYear': era['to_year'],
            'co2Min': None, 'co2Max': None, 'co2Mean': None,
            'nPoints': len(vals),
            'description': era['description'],
            'lifeExpectancyBasis': era['life_expectancy_basis'],
        }
        if vals:
            entry['co2Min'] = round(min(vals), 2)
            entry['co2Max'] = round(max(vals), 2)
            entry['co2Mean'] = round(sum(vals) / len(vals), 2)
        out.append(entry)
    covered = sum(1 for era in out if era['nPoints'] > 0)
    return {
        'ok': True, 'eras': out,
        'note': (
            f'{len(points)} observations of {series_name} bucketed '
            f'into {len(out)} eras; {len(out) - covered} era(s) '
            f'have no coverage and are reported with nPoints 0 '
            f'rather than dropped - an empty bucket is where this '
            f'archive stops, not a rendering bug. Era windows '
            f'OVERLAP by design (pre-industrial sits inside the '
            f'industrial revolution), so a point may be counted '
            f'in more than one era and the counts do not sum to '
            f'the series length. Every range is the spread of '
            f'samples that fall in the window: ice-core gas ages '
            f'are smoothed by firn diffusion and spaced centuries '
            f'to millennia apart, so no era range describes '
            f'year-to-year variation.'),
    }


def outside_experienced_range(manager, present_ppm,
                              series_name=ICE_SERIES,
                              exclude_after_year=1000.0):
    """Today's CO2 against the highest humans are recorded as
    having lived in.

    The last millennium is excluded by default because its late
    samples are already post-industrial firn - leaving them in
    lets the industrial rise vouch for itself.
    """
    try:
        present = float(present_ppm)
    except (TypeError, ValueError):
        return _refuse(
            'present_ppm must be a number in ppm - pass the '
            'ingested Mauna Loa annual mean, not a label')
    try:
        cutoff = float(exclude_after_year)
    except (TypeError, ValueError):
        return _refuse('exclude_after_year must be a number '
                       '(calendar year CE, negative = BCE)')
    points = _observation_rows(manager, series_name)
    if not points:
        return _refuse(
            f'no AtmosphericObservation rows for series '
            f'{series_name!r}. Run {ICE_INGEST} and this '
            f'refusal retires.')
    vals = [value for year, value in points if year < cutoff]
    if not vals:
        return _refuse(
            f'series {series_name!r} has {len(points)} points but '
            f'none before year {cutoff} - nothing to compare '
            f'today against; widen exclude_after_year or ingest '
            f'the full composite via {ICE_INGEST}')
    record_max = max(vals)
    record_min = min(vals)
    ratio = present / record_max if record_max else None
    return {
        'ok': True,
        'recordMaxPpm': round(record_max, 2),
        'recordMinPpm': round(record_min, 2),
        'nPoints': len(vals),
        'excludeAfterYear': cutoff,
        'presentPpm': round(present, 2),
        'ratio': round(ratio, 4) if ratio is not None else None,
        'ppmAbove': round(present - record_max, 2),
        'note': (
            'This sets a modern instrumental ANNUAL MEAN against '
            'ice-core samples whose gas ages are smoothed by firn '
            'diffusion and spaced centuries to millennia apart. '
            'The comparison is SOUND FOR THE LEVEL: a sustained '
            'excursion of this size could not hide inside the '
            'smoothing, so the statement "no sample in this '
            'record reaches today\'s level" holds. It is NOT '
            'sound for the RATE - this archive cannot resolve a '
            'decade, so it cannot say how fast past changes were. '
            'The rate comparison is a separate and stronger '
            'claim, and it is made by the growth-rate series '
            '(climate.custom.co2_trend over the NOAA annual growth '
            'rate), where the sampling supports it.'),
    }


def _segment_points(segment, index):
    """(rows, refusal). Coerces one splice segment."""
    if not isinstance(segment, dict):
        return None, f'segment {index} is not a dict'
    span = str(segment.get('span') or f'segment-{index}')
    kind = str(segment.get('measurementKind') or 'unknown')
    raw = segment.get('points')
    if not isinstance(raw, (list, tuple)):
        return None, (f'segment {index} ({span}) has no points '
                      f'list - a segment without points cannot '
                      f'be spliced')
    rows_out = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        try:
            year = float(item.get('year'))
            value = float(item.get('value'))
        except (TypeError, ValueError):
            continue
        try:
            unc = float(item.get('uncertainty', 0.0) or 0.0)
        except (TypeError, ValueError):
            unc = 0.0
        rows_out.append({'year': year, 'value': value,
                         'uncertainty': unc, 'span': span,
                         'measurementKind': kind})
    rows_out.sort(key=lambda point: point['year'])
    return rows_out, None


def _overlap_report(seg_a, seg_b):
    """The cross-check between two segments, or None if their
    year ranges do not meet."""
    pts_a, pts_b = seg_a['points'], seg_b['points']
    if not pts_a or not pts_b:
        return None
    low = max(pts_a[0]['year'], pts_b[0]['year'])
    high = min(pts_a[-1]['year'], pts_b[-1]['year'])
    if low > high:
        return None
    in_a = [p for p in pts_a if low <= p['year'] <= high]
    in_b = [p for p in pts_b if low <= p['year'] <= high]
    diffs = []
    for point in in_a:
        best, best_gap = None, None
        for other in in_b:
            gap = abs(other['year'] - point['year'])
            if best_gap is None or gap < best_gap:
                best, best_gap = other, gap
        if best is not None and best_gap <= OVERLAP_MATCH_YEARS:
            diffs.append(point['value'] - best['value'])
    mean_diff = None
    if diffs:
        mean_diff = round(sum(diffs) / len(diffs), 4)
    return {
        'spanA': seg_a['span'], 'spanB': seg_b['span'],
        'fromYear': low, 'toYear': high,
        'nA': len(in_a), 'nB': len(in_b),
        'nMatched': len(diffs),
        'meanDifference': mean_diff,
    }


def splice_series(segments, prefer_order=None):
    """Join N segments into one ordered curve WITHOUT hiding the
    seam.

    Every output point carries its span and measurementKind, so a
    renderer segments and colours by source instead of drawing a
    single smooth line that implies one instrument. Where two
    segments overlap, both sets of points survive; `preferred`
    marks the one prefer_order says to plot, and the mean
    difference over the overlap is returned as a CROSS-CHECK.
    That overlap - Law Dome firn against Mauna Loa - is what
    makes the spliced record a measurement rather than an
    assumption.
    """
    if not isinstance(segments, (list, tuple)) or not segments:
        return _refuse(
            'splice_series needs a non-empty list of segments '
            '{span, measurementKind, points}')
    order = tuple(prefer_order or DEFAULT_PREFER_ORDER)
    prepared, problems = [], []
    for index, segment in enumerate(segments):
        points, refusal = _segment_points(segment, index)
        if refusal:
            problems.append(refusal)
            continue
        prepared.append({
            'span': str(segment.get('span') or f'segment-{index}'),
            'measurementKind': str(
                segment.get('measurementKind') or 'unknown'),
            'points': points,
        })
    if problems:
        return _refuse('; '.join(problems))
    prepared = [seg for seg in prepared if seg['points']]
    if not prepared:
        return _refuse(
            'every segment parsed to zero usable points - each '
            'point needs a numeric year and value')

    def rank(kind):
        return order.index(kind) if kind in order else len(order)

    overlaps = []
    for i in range(len(prepared)):
        for j in range(i + 1, len(prepared)):
            report = _overlap_report(prepared[i], prepared[j])
            if report is not None:
                overlaps.append(report)

    out = []
    for seg in prepared:
        seg_rank = rank(seg['measurementKind'])
        for point in seg['points']:
            row = dict(point)
            row['preferred'] = True
            for other in prepared:
                if other is seg:
                    continue
                pts = other['points']
                if not pts:
                    continue
                if not (pts[0]['year'] <= point['year']
                        <= pts[-1]['year']):
                    continue
                other_rank = rank(other['measurementKind'])
                if other_rank < seg_rank:
                    row['preferred'] = False
                    break
            out.append(row)
    out.sort(key=lambda p: (p['year'],
                            rank(p['measurementKind'])))
    kinds = []
    for seg in prepared:
        if seg['measurementKind'] not in kinds:
            kinds.append(seg['measurementKind'])
    matched = sum(o['nMatched'] for o in overlaps)
    return {
        'ok': True,
        'points': out,
        'spans': [seg['span'] for seg in prepared],
        'overlaps': overlaps,
        'note': (
            f'{len(out)} points from {len(prepared)} segment(s) '
            f'across measurement kinds {", ".join(kinds)}; '
            f'{len(overlaps)} overlap(s), {matched} year-matched '
            f'pair(s) within {OVERLAP_MATCH_YEARS:.0f} years. No '
            f'point was dropped: where segments overlap, both '
            f'sets are returned with their own span label so the '
            f'renderer can draw both, and `preferred` marks the '
            f'one the preference order '
            f'{" > ".join(order)} says to plot. The mean '
            f'difference over an overlap is a CROSS-CHECK, not a '
            f'conflict to average away - agreement there is what '
            f'makes this curve a measurement instead of an '
            f'assumption, and disagreement is a finding about '
            f'one of the two archives. Every point carries its '
            f'span and measurementKind so the seam is visible on '
            f'the page.'),
    }


def coverage_citations(manager, series_name, from_year=None,
                       to_year=None):
    """The citations for exactly the window a chart is showing.

    A chart that prints every source in the module cites things
    it is not displaying. This returns only the spans whose year
    range intersects the plotted window.
    """
    from composition.custom.data_refs import rows
    spans = [row for row in rows(manager, 'SourceCoverageSpan')
             if getattr(row, 'series_ref', '') == series_name]
    if not spans:
        return _refuse(
            f'no SourceCoverageSpan rows for series '
            f'{series_name!r} - the ingest writes the span row '
            f'alongside the observations, so run '
            f'climate.custom.series_ingest.ingest_series for this '
            f'series and this refusal retires')
    bounds = []
    for span in spans:
        try:
            low = float(getattr(span, 'from_year', 0.0))
            high = float(getattr(span, 'to_year', 0.0))
        except (TypeError, ValueError):
            low, high = 0.0, 0.0
        if low > high:
            low, high = high, low
        bounds.append((span, low, high))
    try:
        win_from = (float(from_year) if from_year is not None
                    else min(low for _, low, _ in bounds))
        win_to = (float(to_year) if to_year is not None
                  else max(high for _, _, high in bounds))
    except (TypeError, ValueError):
        return _refuse('from_year/to_year must be numbers '
                       '(calendar years CE, negative = BCE)')
    if win_from > win_to:
        win_from, win_to = win_to, win_from

    hits = [(span, low, high) for span, low, high in bounds
            if low <= win_to and high >= win_from]
    hits.sort(key=lambda item: item[1])
    out, lines, kinds = [], [], []
    for span, low, high in hits:
        kind = getattr(span, 'measurement_kind', '')
        if kind and kind not in kinds:
            kinds.append(kind)
        entry = {
            'name': getattr(span, 'name', ''),
            'displayName': getattr(span, 'display_name', ''),
            'measurementKind': kind,
            'fromYear': low, 'toYear': high,
            'archiveName': getattr(span, 'archive_name', ''),
            'resolutionYears': float(
                getattr(span, 'resolution_years', 0.0) or 0.0),
            'citationText': getattr(span, 'citation_text', ''),
            'doiOrUrl': getattr(span, 'doi_or_url', ''),
            'color': getattr(span, 'color', '#888888'),
        }
        out.append(entry)
        label = (entry['displayName'] or entry['name']
                 or 'unnamed span')
        archive = entry['archiveName']
        head = f'{label} ({archive}, {kind})' if archive \
            else f'{label} ({kind})'
        line = (f'{head}, {_year_label(low)} to '
                f'{_year_label(high)}, resolution ~'
                f'{entry["resolutionYears"]:.1f} yr: '
                f'{entry["citationText"]}').strip()
        if entry['doiOrUrl']:
            line = f'{line} {entry["doiOrUrl"]}'
        lines.append(line)

    if not out:
        note = (f'no span of {series_name!r} intersects '
                f'{_year_label(win_from)} to '
                f'{_year_label(win_to)} - the window is outside '
                f'this series\' coverage entirely, which is a '
                f'finding about the window, not a missing '
                f'citation')
    elif len(kinds) > 1:
        note = (f'This window is a SPLICE: it is covered by '
                f'{len(out)} span(s) across {len(kinds)} '
                f'measurement kinds ({", ".join(kinds)}). The '
                f'curve drawn over it is NOT one instrument, and '
                f'the renderer must segment it by span. Cite all '
                f'the lines above together; citing one implies a '
                f'single archive covered the whole axis.')
    else:
        note = (f'One measurement kind ({kinds[0] if kinds else "?"}'
                f') across {len(out)} span(s) covers this window, '
                f'so the curve here is a single kind of '
                f'measurement - widen the window and it becomes '
                f'a splice.')
    return {
        'ok': True,
        'windowFromYear': win_from,
        'windowToYear': win_to,
        'spans': out,
        'citationLines': lines,
        'note': note,
    }


def seed_human_eras(manager):
    """The eras, upserted so a changed range converges instead of
    inserting a duplicate."""
    from moduleService.seed_upsert import upsert_seed_pairs
    from climate.climate_basis import HumanEraDefinition
    return upsert_seed_pairs(manager, [
        ('HumanEraDefinition', HumanEraDefinition,
         SEED_HUMAN_ERAS),
    ], tag='ClimateEraSeed')
