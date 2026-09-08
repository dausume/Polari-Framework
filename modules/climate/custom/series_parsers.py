"""
@module climate.custom.series_parsers

PARSERS AS DATA-DRIVEN FUNCTIONS, one per published format, keyed
by name so an `APIEndpoint` row can name its parser
(`parser_ref`) instead of the ingest hard-coding a branch per
agency.

Each parser takes decoded text and returns
`{'ok', 'points': [{'year','value','uncertainty'}], 'skipped',
  'refusal'}` — never raises, and never silently drops a line: a
line it cannot read is COUNTED and sampled into `skipped`, because
"we parsed 1901 of 1903 rows" is a finding and "we parsed 1901
rows" is not.

Year convention: every parser emits CALENDAR YEAR CE as a float.
Ice-core archives publish `cal BP` (before present, where present
is fixed at 1950 by convention), so the conversion is
`year_ce = 1950 - age_bp` — which is why the composite's youngest
sample, -51 cal BP, is the year 2001 and not a negative age.
Getting this backwards would mirror the entire record.

@consumers climate.custom.series_ingest, climate.climate_selftest
"""

#: Ice-core ages are "before present", and PRESENT IS 1950 by
#: convention, not the current year. Restating this constant
#: anywhere else is how the two copies drift.
BP_REFERENCE_YEAR = 1950.0


def _rows(text):
    for raw in (text or '').splitlines():
        line = raw.strip()
        if line:
            yield line


def parse_noaa_annual(text, value_index=1, uncertainty_index=2):
    """NOAA GML annual-mean / growth-rate text files.

    Layout: a '#' comment banner, then whitespace-separated
    columns `year value uncertainty`. Identical shape for the
    annual mean and the growth rate, so one parser serves four
    endpoints — only the column meaning differs, and that lives on
    the series row.
    """
    points, skipped = [], []
    for line in _rows(text):
        if line.startswith('#'):
            continue
        parts = line.split()
        if len(parts) <= max(value_index, 1):
            skipped.append(line[:80])
            continue
        try:
            year = float(parts[0])
            value = float(parts[value_index])
        except (TypeError, ValueError):
            skipped.append(line[:80])
            continue
        unc = 0.0
        if uncertainty_index and len(parts) > uncertainty_index:
            try:
                unc = float(parts[uncertainty_index])
            except (TypeError, ValueError):
                unc = 0.0
        points.append({'year': year, 'value': value,
                       'uncertainty': unc})
    if not points:
        return {'ok': False, 'points': [], 'skipped': skipped,
                'refusal': ('no numeric rows found in a NOAA '
                            'annual file - the payload parsed as '
                            'text but carried no data')}
    return {'ok': True, 'points': points, 'skipped': skipped[:5],
            'skippedCount': len(skipped), 'refusal': ''}


def parse_ice_core_composite(text):
    """NOAA NCEI paleo composite: `age_gas_calBP co2_ppm
    co2_1s_ppm`, tab-delimited, after a '#' banner and a bare
    column-name line.

    The column-name line carries no '#', so it must be rejected by
    failing to parse as a number rather than by line counting - the
    banner length is not stable across NCEI studies.
    """
    points, skipped = [], []
    for line in _rows(text):
        if line.startswith('#'):
            continue
        parts = line.replace('\t', ' ').split()
        if len(parts) < 2:
            skipped.append(line[:80])
            continue
        try:
            age_bp = float(parts[0])
            value = float(parts[1])
        except (TypeError, ValueError):
            # the header row lands here, by design
            skipped.append(line[:80])
            continue
        unc = 0.0
        if len(parts) > 2:
            try:
                unc = float(parts[2])
            except (TypeError, ValueError):
                unc = 0.0
        points.append({'year': BP_REFERENCE_YEAR - age_bp,
                       'value': value, 'uncertainty': unc,
                       'ageBp': age_bp})
    if not points:
        return {'ok': False, 'points': [], 'skipped': skipped,
                'refusal': ('no numeric rows in the ice-core '
                            'composite')}
    return {'ok': True, 'points': points, 'skipped': skipped[:5],
            'skippedCount': len(skipped), 'refusal': ''}


def parse_socrata_life_expectancy(payload, race='All Races',
                                  sex='Both Sexes'):
    """CDC Socrata JSON -> life expectancy at birth by year.

    The dataset is stratified; taking every row would silently
    average incompatible strata, so the filter is explicit and its
    values are echoed back on the result.
    """
    if not isinstance(payload, list):
        return {'ok': False, 'points': [],
                'refusal': (f'expected a JSON array from Socrata, '
                            f'got {type(payload).__name__}')}
    points, skipped = [], []
    for item in payload:
        if not isinstance(item, dict):
            skipped.append(str(item)[:80])
            continue
        if item.get('race') != race or item.get('sex') != sex:
            continue
        try:
            year = float(item.get('year'))
            value = float(item.get('average_life_expectancy'))
        except (TypeError, ValueError):
            skipped.append(str(item)[:80])
            continue
        points.append({'year': year, 'value': value,
                       'uncertainty': 0.0})
    if not points:
        return {'ok': False, 'points': [], 'skipped': skipped[:5],
                'refusal': (f'no rows matched race={race!r} '
                            f'sex={sex!r} - check the strata the '
                            f'dataset actually publishes')}
    points.sort(key=lambda p: p['year'])
    return {'ok': True, 'points': points, 'skipped': skipped[:5],
            'skippedCount': len(skipped), 'race': race, 'sex': sex,
            'refusal': ''}


#: parser_ref -> callable. An endpoint row names one of these; an
#: endpoint naming a parser that is not here REFUSES at ingest
#: rather than falling back to a guess.
PARSERS = {
    'noaa-annual': parse_noaa_annual,
    'ice-core-composite': parse_ice_core_composite,
    'socrata-life-expectancy': parse_socrata_life_expectancy,
}


def get_parser(parser_ref):
    """(callable, refusal). Naming the available parsers in the
    refusal is what makes an unimplemented one actionable - the
    Law Dome endpoint is deliberately in this state."""
    fn = PARSERS.get(parser_ref)
    if fn is None:
        return None, (f'no parser named {parser_ref!r}; available: '
                      f'{", ".join(sorted(PARSERS))}. An endpoint '
                      f'without a verified parser must refuse '
                      f'rather than guess at its columns.')
    return fn, ''


def series_bounds(points):
    """(first_year, last_year, n) - DERIVED from the rows, never
    seeded. A declared range that disagrees with the data is the
    drift this project guards against."""
    if not points:
        return 0.0, 0.0, 0
    years = [p['year'] for p in points]
    return min(years), max(years), len(points)
