"""
@module climate.climate_pages

THE NO-CODE PRESENTATION LAYER for the CO2/health study: the
graphs are GraphDefinition ROWS and the page is a
DisplayDefinition ROW, so a new chart is an insert and a moved
panel is an edit — never an Angular component.

Two seed shapes live here, and both are pure data:

  GraphDefinition.definition = {'graphConfig': {...}}
      matching the frontend's GraphConfigData exactly, so the
      Graphs editor can open, edit and round-trip a seeded graph.
  DisplayDefinition.definition = {'rows': [...]}
      of the two generic registered components (api-json-panel,
      class-rows-table), the module_pages_seed pattern.

⚠ TWO BUGS IN THE EXISTING msim GRAPH SEEDS ARE NOT REPEATED HERE.
They write `options.legend`, but the frontend reads
`options.showLegend` — a seeded legend flag that silently does
nothing. And they write `'aggregation': None`, where the model
declares a required AggregationConfig object; the normalizer has
to invent one, which means the seeded row and the editor's saved
row differ for no reason. Every graph below writes `showLegend`
and a real {'enabled', 'strategy'} aggregation.

The row helpers (`_row`/`_api`/`_table`) are COPIED from
polariApiServer.module_pages_seed rather than imported: that
module is core-seed territory and the climate module must stay
droppable. Copying three dict builders is cheaper than a core
dependency that outlives the app.

@consumers climate.climate_api, climate.selftest_climate,
polariServer (seed pass — seed_climate_pages)
"""

import json

from climate.climate_history import coverage_citations
from climate.series_ingest import series_points, series_status

PROV = 'co2-7'

#: Which series each graph draws. A graph with no entry here is
#: not a series plot and refuses by name rather than inventing
#: rows — the indoor comparison is COMPUTED per room, so it comes
#: from the crossings API, not from an observation table.
GRAPH_SERIES = {
    'climate-co2-instrumental': 'co2-mauna-loa-annual',
    'climate-co2-800kyr': 'co2-ice-core-composite',
    'climate-co2-growth-rate': 'co2-growth-rate-mauna-loa',
    'climate-life-expectancy': 'life-expectancy-us',
}

#: Where a non-series graph's numbers actually come from, so its
#: refusal carries its own retirement.
GRAPH_COMPUTED_BY = {
    'climate-indoor-vs-outdoor': '/api/climate/crossings',
}


def _graph_config(render_style, x_dim, y_dims, x_label, y_label,
                  series_colors=None, height=400):
    """One GraphConfigData blob. Keys and nesting match the
    frontend model exactly — renderStyle, xDimension, yDimensions,
    seriesColors, options, aggregation."""
    return {
        'renderStyle': render_style,
        'xDimension': x_dim,
        'yDimensions': list(y_dims),
        'seriesColors': list(series_colors or []),
        'options': {
            'width': 800,
            'height': height,
            'marginTop': 20,
            'marginRight': 30,
            'marginBottom': 40,
            'marginLeft': 60,
            #: showLegend, NOT legend — see the module note.
            'showLegend': True,
            'showGrid': True,
            'xLabel': x_label,
            'yLabel': y_label,
        },
        #: never None: the model declares a required object.
        'aggregation': {'enabled': False, 'strategy': 'average'},
    }


def _graph(name, description, source_class, config):
    return {'name': name, 'description': description,
            'source_class': source_class,
            'definition': json.dumps({'graphConfig': config})}


SEED_CLIMATE_GRAPHS = [
    _graph(
        'climate-source-sink-differential',
        'THE IMBALANCE, per year: what humans emit MINUS what the '
        'ocean, land and cement sinks take back (Global Carbon '
        'Budget 2025). Zero on this axis would mean sources and '
        'sinks in balance. The line never touches it: the record '
        'opens at 3.21 GtC/yr in 1959, and its smallest gap in 66 '
        'years is 1.85 GtC/yr in 1974. That is the point of '
        'plotting the difference rather than the two totals — an '
        'imbalance is hard to see between two rising lines and '
        'impossible to miss on its own axis.',
        'CarbonSinkSeries',
        _graph_config('lineY', 'year', ['differential'],
                      'year (CE)',
                      'sources minus sinks (GtC/yr)',
                      series_colors=['#c0392b'])),
    _graph(
        'climate-sources-vs-sinks',
        'Sources and sinks as two lines on one axis (Global Carbon '
        'Budget 2025). The sinks ARE working harder every decade — '
        'total uptake more than tripled since 1959 — and they are '
        'still falling further behind, because emissions grew '
        'faster. The gap between these two lines is the '
        'differential graph; shown together so a reader can see '
        'that the widening gap is not a story of failing sinks.',
        'CarbonSinkSeries',
        _graph_config('lineY', 'year', ['sources', 'sinks'],
                      'year (CE)', 'carbon flux (GtC/yr)',
                      series_colors=['#8e1b12', '#2e8b57'])),
    _graph(
        'climate-sink-composition',
        'What each sink actually sequesters per year (Global '
        'Carbon Budget 2025). The OCEAN is the largest single sink '
        'in every era of the record — 3.22 GtC/yr and 56 percent '
        'of all uptake in 2015-2024, against 2.36 for land. Cement '
        'carbonation, which most summaries omit entirely, is small '
        'but has grown roughly tenfold from a very small base. The '
        'land term is the noisiest and drives the recent '
        'excursion.',
        'CarbonSinkSeries',
        _graph_config('lineY', 'year',
                      ['oceanSink', 'landSink', 'cementSink'],
                      'year (CE)', 'carbon sequestered (GtC/yr)',
                      series_colors=['#2b6cb0', '#2e8b57',
                                     '#a0801f'])),
    _graph(
        'climate-sink-share',
        'The share of each year\'s emissions the sinks took back '
        '(Global Carbon Budget 2025). This is the differential '
        'expressed as a proportion, and it is the number that '
        'corrects a common assumption: it is roughly FLAT across '
        'the record (weak positive drift, r=+0.29), not declining. '
        'The sinks have broadly kept pace proportionally while '
        'the absolute gap widened.',
        'CarbonSinkSeries',
        _graph_config('lineY', 'year', ['sinkShareOfSources'],
                      'year (CE)',
                      'fraction of emissions absorbed',
                      series_colors=['#3f7fbf'])),
    _graph(
        'climate-co2-instrumental',
        'NOAA GML Mauna Loa annual mean CO2, 1959 onward. You are '
        'looking at the direct instrumental record: one annual '
        'mean per year, each measured at Mauna Loa Observatory by '
        'NDIR / cavity ring-down spectroscopy. This is the series '
        'every fit, crossing band and indoor offset on the study '
        'page is computed from.',
        'AtmosphericObservation',
        _graph_config('lineY', 'year', ['value'],
                      'year (CE)', 'CO2 (ppm)')),
    _graph(
        'climate-co2-800kyr',
        'Antarctic ice-core CO2 composite (Bereiter et al. 2015, '
        'NOAA NCEI paleo study 17975) across 800,000 years. You '
        'are looking at bubbles of ancient air, NOT annual data: '
        'gas ages are smoothed by firn diffusion and sampled '
        'centuries to millennia apart, so this curve bounds the '
        'LEVEL humans lived at and can say nothing about the rate '
        'of change within it.',
        'AtmosphericObservation',
        _graph_config('lineY', 'year', ['value'],
                      'year (CE, negative = BCE)', 'CO2 (ppm)')),
    _graph(
        'climate-co2-growth-rate',
        'NOAA GML published annual CO2 growth rate at Mauna Loa. '
        'You are looking at the PUBLISHER\'S OWN velocity term, '
        'not a difference we computed from the levels — which is '
        'what makes it an independent second path to the same '
        'number, and what makes a disagreement with our fitted '
        'slope a finding rather than an averaging problem.',
        'AtmosphericObservation',
        _graph_config('lineY', 'year', ['value'],
                      'year (CE)', 'CO2 growth rate (ppm/yr)')),
    _graph(
        'climate-indoor-vs-outdoor',
        'Steady-state indoor CO2 above the outdoor background, by '
        'room archetype, computed from the seeded '
        'IndoorSpaceProfile rows at today\'s ingested outdoor '
        'level. You are looking at what VENTILATION does, not at '
        'a measurement: every bar is an archetype whose '
        'retirement condition is a CO2 meter in a real room of '
        'known volume and occupancy.',
        'ExposureProjection',
        _graph_config('barY', 'space', ['indoorOffsetPpm'],
                      'space',
                      'steady-state CO2 above outdoor (ppm)')),
    _graph(
        'climate-life-expectancy',
        'US life expectancy at birth, 1900 onward (CDC/NCHS '
        'dataset w9j2-ggv5). You are looking at HISTORICAL '
        'CONTEXT shown beside the CO2 record and NEVER regressed '
        'against it: this curve is dominated by infant mortality, '
        'infectious disease control, sanitation and tobacco, and '
        'a CO2 term fitted through it would be a textbook '
        'spurious correlation.',
        'AtmosphericObservation',
        _graph_config('lineY', 'year', ['value'], 'year (CE)',
                      'life expectancy at birth (years)')),
]

GRAPHS_BY_NAME = {g['name']: g for g in SEED_CLIMATE_GRAPHS}


# ---------------------------------------------------------------
# Row helpers — copied from polariApiServer.module_pages_seed
# ---------------------------------------------------------------

def _table(item_id, index, segments, title, class_name,
           columns='', max_rows=0):
    return {
        'id': item_id, 'index': index, 'type': 'component',
        'rowSegmentsUsed': segments, 'gridColumnStart': None,
        'title': title, 'visible': True, 'collapsed': False,
        'cssClass': '',
        'componentProps': {
            'componentName': 'class-rows-table',
            'inputs': {'className': class_name,
                       'columns': columns, 'maxRows': max_rows},
        },
        'item': None, 'nestedRows': [],
    }


def _api(item_id, index, segments, title, path):
    return {
        'id': item_id, 'index': index, 'type': 'component',
        'rowSegmentsUsed': segments, 'gridColumnStart': None,
        'title': title, 'visible': True, 'collapsed': False,
        'cssClass': '',
        'componentProps': {
            'componentName': 'api-json-panel',
            'inputs': {'path': path},
        },
        'item': None, 'nestedRows': [],
    }


def _row(index, items, min_height=320):
    return {
        'index': index, 'rowSegments': 12,
        'minRowHeight': min_height, 'maxRowHeight': 0,
        'autoHeight': True, 'cssClass': '', 'items': items,
    }


SEED_CLIMATE_PAGE_DISPLAYS = [{
    'name': 'co2-health',
    'description': 'The CO2 and human health study: the outdoor '
                   'record and its fits, what it becomes indoors '
                   'per room, the graded thresholds, the coupled '
                   'crossing table, what CO2 humans actually '
                   'lived in, the sources behind every number, '
                   'and the measurements that would retire every '
                   'prior on the page.',
    'source_class': 'AtmosphericSeriesDefinition',
    'isPage': True,
    'pageRoute': 'co2/health',
    'linkedSolutions': '[]',
    'definition': json.dumps({'rows': [
        _row(0, [
            _api('co2h-study', 0, 12,
                 'CO2 and human health - the study',
                 '/api/climate/view/view-co2-health'),
        ], min_height=640),
        _row(1, [
            _api('co2h-crossings', 0, 6,
                 'When each threshold arrives, indoors and out',
                 '/api/climate/crossings'),
            _api('co2h-thresholds', 1, 6,
                 'Health thresholds, graded by evidence',
                 '/api/climate/thresholds'),
        ]),
        _row(2, [
            _api('co2h-history', 0, 6,
                 'What CO2 humans actually lived in',
                 '/api/climate/history'),
            _api('co2h-sources', 1, 6,
                 'Sources and coverage spans',
                 '/api/climate/sources'),
        ]),
        _row(3, [
            _table('co2h-series', 0, 6, 'Series',
                   'AtmosphericSeriesDefinition',
                   'name,measure,unit,location,status,'
                   'first_year,last_year'),
            _table('co2h-spans', 1, 6,
                   'Which source covers which years',
                   'SourceCoverageSpan',
                   'name,series_ref,measurement_kind,from_year,'
                   'to_year,resolution_years'),
        ]),
    ]}),
}]


def seed_climate_pages(manager):
    """The graphs and the page, upserted so an edited config
    converges instead of inserting a duplicate."""
    from composition.seed_upsert import upsert_seed_pairs
    from polariApiServer.graphDefinition import GraphDefinition
    from polariApiServer.displayDefinition import DisplayDefinition
    return upsert_seed_pairs(manager, [
        ('GraphDefinition', GraphDefinition, SEED_CLIMATE_GRAPHS),
        ('DisplayDefinition', DisplayDefinition,
         SEED_CLIMATE_PAGE_DISPLAYS),
    ], tag='ClimatePagesSeed')


def graph_names():
    """Every graph this module seeds."""
    return sorted(GRAPHS_BY_NAME)


#: The carbon-budget graphs draw from WIDE per-year rows rather
#: than one observation series, because the differential only
#: exists as a relationship BETWEEN series. Listed here so
#: graph_data can route them without guessing from the config.
BUDGET_GRAPHS = frozenset({
    'climate-source-sink-differential',
    'climate-sources-vs-sinks',
    'climate-sink-composition',
    'climate-sink-share',
})


def graph_data(manager, graph_name):
    """One seeded graph's config AND its data, resolved BY NAME.

    Name, not id: the existing embeddedGraph component resolves a
    graph by its runtime object id, which a seeded row cannot know
    and which changes on every fresh volume. A seed can only ever
    rely on its own `name`, so that is the key this entry point
    takes.
    """
    graph = GRAPHS_BY_NAME.get(graph_name)
    if graph is None:
        return {'ok': False, 'graph': graph_name,
                'refusal': f'no seeded climate graph named '
                           f'{graph_name!r} — one of '
                           f'{graph_names()}'}
    try:
        config = json.loads(graph['definition'])['graphConfig']
    except (KeyError, TypeError, ValueError) as exc:
        return {'ok': False, 'graph': graph_name,
                'refusal': f'the seeded definition does not parse '
                           f'as a graphConfig: {exc}'}
    # The carbon-budget graphs are WIDE: one row per year carrying
    # sources, sinks, the differential and each sink separately, so
    # a single row feeds all four of them. They come from the
    # stored per-column observation series, not from one series.
    if graph_name in BUDGET_GRAPHS:
        from climate.carbon_sinks import budget_graph_rows
        built = budget_graph_rows(manager)
        if not built.get('ok'):
            return {'ok': False, 'graph': graph_name,
                    'graphConfig': config,
                    'refusal': built.get('refusal', '')}
        from climate.climate_history import coverage_citations
        cites = coverage_citations(manager, 'carbon-budget')
        return {'ok': True, 'graph': graph_name,
                'graphConfig': config, 'rows': built['rows'],
                'rowCount': built['count'],
                'spans': (cites.get('spans') if cites.get('ok')
                          else []),
                'citations': (cites.get('citationLines')
                              if cites.get('ok') else []),
                'note': built.get('note', '')}

    series = GRAPH_SERIES.get(graph_name, '')
    if not series:
        computed = GRAPH_COMPUTED_BY.get(graph_name, '')
        return {
            'ok': False, 'graph': graph_name,
            'graphConfig': config,
            'refusal': (
                f'{graph_name!r} is not an observation series: its '
                f'bars are COMPUTED per room from the '
                f'IndoorSpaceProfile rows and the present outdoor '
                f'level. Read them from '
                f'{computed or "the climate view API"} — this '
                f'entry point returns ingested observations only, '
                f'and will not restate a computation as data')}
    status = series_status(manager, series)
    if not status.get('ok'):
        return {'ok': False, 'graph': graph_name,
                'series': series, 'graphConfig': config,
                'refusal': status.get('refusal', '')}
    points = series_points(manager, series)
    if not points:
        return {'ok': False, 'graph': graph_name,
                'series': series, 'graphConfig': config,
                'refusal': (f'series {series!r} reports '
                            f'"ingested" but has no '
                            f'AtmosphericObservation rows — '
                            f're-run the ingest')}
    data_rows, spans = [], []
    for point in points:
        span = point.get('span', '')
        if span and span not in spans:
            spans.append(span)
        data_rows.append({'year': point['year'],
                          'value': point['value'],
                          'span': span})
    cite = coverage_citations(manager, series)
    citations = cite.get('citationLines', []) if cite.get('ok') \
        else []
    out = {
        'ok': True, 'graph': graph_name, 'series': series,
        'graphConfig': config, 'rows': data_rows,
        'spans': spans, 'citations': citations,
        'note': ('every row carries the SourceCoverageSpan it was '
                 'measured in, so a renderer segments the curve by '
                 'source instead of drawing one smooth line across '
                 'two different instruments'),
    }
    if not cite.get('ok'):
        out['citationsRefusal'] = cite.get('refusal', '')
    else:
        out['citationsNote'] = cite.get('note', '')
    return out
