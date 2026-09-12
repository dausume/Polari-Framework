"""
@module climate.climate_series_seed

THE SERIES ROWS — what this app intends to measure, one row per
series, seeded EMPTY of data.

The split matters and is the plan's spine: a seed pass creates the
SERIES (what we intend to measure, from which endpoint, in which
unit); only `series_ingest` creates the OBSERVATIONS. A
measurement that a seed pass can conjure is not a measurement, so
every row here starts `status='prior'` and the engines refuse to
project from it until a real fetch flips it to 'ingested'.

`first_year` / `last_year` are deliberately 0.0 here. They are
DERIVED from the rows that land, never asserted — a declared range
that disagrees with its own data is the drift this project spends
its guard tests on.

@consumers climate.custom.series_ingest, climate.climate_api,
climate.climate_views_seed, polariServer
"""

from moduleService.seed_upsert import upsert_seed_pairs

PROV = 'co2-A'


def _series(name, display, measure, unit, cadence, location,
            source, endpoint, description, notes='',
            uncertainty_unit=''):
    return {
        'name': name, 'display_name': display, 'measure': measure,
        'unit': unit, 'cadence': cadence, 'location': location,
        'source_ref': source, 'endpoint_ref': endpoint,
        'status': 'prior', 'first_year': 0.0, 'last_year': 0.0,
        'value_field': 'value',
        'uncertainty_unit': uncertainty_unit or unit,
        'description': description, 'is_prior': True,
        'provenance_id': PROV, 'notes': notes,
    }


SEED_CLIMATE_SERIES = [
    _series('co2-mauna-loa-annual',
            'Mauna Loa annual mean CO2', 'co2-mole-fraction',
            'ppm', 'annual', 'Mauna Loa Observatory, Hawaii',
            'noaa-gml', 'noaa-co2-annmean-mlo',
            'The modern instrumental CO2 record, 1959 onward, as '
            'annual means with NOAA\'s stated annual uncertainty.',
            notes='The single-station record. It is the longest '
                  'direct series, which is why it anchors the '
                  'fits, and it is one station, which is why the '
                  'global series exists beside it.'),
    _series('co2-global-annual',
            'Globally averaged marine surface CO2',
            'co2-mole-fraction', 'ppm', 'annual',
            'global marine surface', 'noaa-gml',
            'noaa-co2-annmean-global',
            'The globally averaged annual mean - the cross-check '
            'that a Mauna Loa result is not a Mauna Loa artifact.'),
    _series('co2-growth-rate-mauna-loa',
            'Mauna Loa CO2 annual growth rate',
            'co2-growth-rate', 'ppm/yr', 'annual',
            'Mauna Loa Observatory, Hawaii', 'noaa-gml',
            'noaa-co2-gr-mlo',
            'NOAA\'s OWN velocity term, published rather than '
            'derived by us.',
            notes='Preferring the publisher\'s growth rate to a '
                  'difference of our own levels means the velocity '
                  'on the page is NOAA\'s. Where both exist they '
                  'are compared and DISAGREEMENT IS A FINDING - '
                  'observed 2026-08-02: fitted 2.1972 vs published '
                  '2.2058 ppm/yr over the same 30 years, 0.4 '
                  'percent apart.'),
    _series('co2-growth-rate-global',
            'Global CO2 annual growth rate', 'co2-growth-rate',
            'ppm/yr', 'annual', 'global marine surface',
            'noaa-gml', 'noaa-co2-gr-global',
            'The globally averaged growth rate.'),
    _series('co2-ice-core-composite',
            'Antarctic ice-core CO2 (800,000 years)',
            'co2-mole-fraction', 'ppm', 'irregular',
            'Antarctica (multi-core composite)',
            'noaa-ncei-paleo', 'ncei-antarctica-co2-composite',
            'CO2 across the whole span of the human species and '
            'well beyond it, from Antarctic ice cores.',
            notes='NOT annual data. Gas ages are smoothed by firn '
                  'diffusion and sampled centuries to millennia '
                  'apart, so this series bounds the LEVEL humans '
                  'lived at, never the year-to-year rate. Any '
                  'renderer that draws it as a continuous annual '
                  'line is overstating it.'),
    _series('life-expectancy-us',
            'US life expectancy at birth', 'life-expectancy',
            'years', 'annual', 'United States',
            'cdc-nchs-vital', 'cdc-life-expectancy',
            'Life expectancy at birth, 1900 onward, all races, '
            'both sexes.',
            notes='CONTEXT ONLY. This series sits beside the CO2 '
                  'record so a reader can see both histories; it '
                  'is never regressed against CO2. Life '
                  'expectancy over this period is dominated by '
                  'infant mortality, infectious disease control, '
                  'sanitation and tobacco - a CO2 term fitted '
                  'through it would be a textbook spurious '
                  'correlation.'),
]


def seed_climate_series(manager):
    from climate.climate_basis import AtmosphericSeriesDefinition
    return upsert_seed_pairs(manager, [
        ('AtmosphericSeriesDefinition', AtmosphericSeriesDefinition,
         SEED_CLIMATE_SERIES),
    ], tag='ClimateSeriesSeed')


#: series name -> the parser its endpoint's payload needs. Kept
#: beside the series rather than on the endpoint because one
#: endpoint format (NOAA's whitespace table) serves several
#: series that differ only in what the columns MEAN.
SERIES_PARSERS = {
    'co2-mauna-loa-annual': ('noaa-annual', {}),
    'co2-global-annual': ('noaa-annual', {}),
    'co2-growth-rate-mauna-loa': ('noaa-annual', {}),
    'co2-growth-rate-global': ('noaa-annual', {}),
    'co2-ice-core-composite': ('ice-core-composite', {}),
    'life-expectancy-us': ('socrata-life-expectancy', {}),
}

#: series name -> the coverage span it lands in, and what kind of
#: measurement that span is. This is what lets a chart say "ice
#: core here, instrument there" instead of drawing one smooth lie.
SERIES_SPANS = {
    'co2-mauna-loa-annual': {
        'span': 'span-mauna-loa-instrumental',
        'kind': 'direct-instrument',
        'archive': 'Mauna Loa Observatory',
        'instrument': 'NDIR / cavity ring-down spectroscopy',
    },
    'co2-global-annual': {
        'span': 'span-global-marine-instrumental',
        'kind': 'direct-instrument',
        'archive': 'NOAA global cooperative air sampling network',
        'instrument': 'flask and in-situ analysers',
    },
    'co2-ice-core-composite': {
        'span': 'span-antarctic-ice-core',
        'kind': 'ice-core',
        'archive': 'EPICA Dome C / Vostok / Law Dome composite',
        'instrument': 'ice-core air extraction, gas chromatography',
    },
    'life-expectancy-us': {
        'span': 'span-us-vital-statistics',
        'kind': 'vital-statistics',
        'archive': 'CDC/NCHS national vital statistics',
        'instrument': 'death certificates and period life tables',
    },
}
