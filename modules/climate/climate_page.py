"""
@module climate.climate_page

THE NO-CODE PRESENTATION LAYER for the CO2/health study: the
graphs are GraphDefinition ROWS and the page is a
DisplayDefinition ROW, so a new chart is an insert and a moved
panel is an edit — never an Angular component.

Two seed shapes live here, and both are pure data:

  GraphDefinition.definition = {'graphConfig': {...}}
      matching the frontend's GraphConfigData exactly, so the
      Graphs editor can open, edit and round-trip a seeded graph.
  DisplayDefinition.definition = {'rows': [...]}
      of the two generic registered components (api-structured-panel,
      class-rows-table), the module_pages_seed pattern — no JSON on
      screen: each panel picks its record list or hides the
      dict-of-lists roll-ups that would land in the JSON expander.

⚠ TWO BUGS IN THE EXISTING msim GRAPH SEEDS ARE NOT REPEATED HERE.
They write `options.legend`, but the frontend reads
`options.showLegend` — a seeded legend flag that silently does
nothing. And they write `'aggregation': None`, where the model
declares a required AggregationConfig object; the normalizer has
to invent one, which means the seeded row and the editor's saved
row differ for no reason. Every graph below writes `showLegend`
and a real {'enabled', 'strategy'} aggregation.

The row helpers (`_row`/`_api`/`_sapi`/`_table`) are COPIED from
polariApiServer.module_pages_seed rather than imported: that
module is core-seed territory and the climate module must stay
droppable. Copying three dict builders is cheaper than a core
dependency that outlives the app.

@consumers climate.climate_api, climate.climate_selftest,
polariServer (seed pass — seed_climate_pages)
"""

import json

from climate.climate_history_seed import coverage_citations
from climate.custom.series_ingest import series_points, series_status

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
        'climate-urban-bedroom-trajectory',
        'THE ROOM DOES NOT CHANGE - the floor under it rises. An '
        'urban-core sealed bedroom projected forward on the '
        'current fitted trajectory, against Stumm 2023\'s '
        'modelled 3000 ppm hypercapnic onset and the contested '
        '2500 ppm cognitive line. Today it sits at about 2727 ppm '
        'for eight hours a night; on MEASURED ventilation offsets '
        'it reaches 3000 between roughly 2095 and 2150. The '
        'second indoor line uses this app\'s own room model, '
        'which is already past the onset today - and which also '
        'puts a RURAL bedroom over it, so that line is shown as a '
        'known-pessimistic bound rather than a rival estimate. '
        'The threshold lines are plotted as data columns because '
        'the renderer has no reference-line feature; the crossing '
        'is where the series meet.',
        'AtmosphericObservation',
        _graph_config('lineY', 'year',
                      ['indoorMeasuredOffset',
                       'indoorModelledOffset', 'stummOnset',
                       'cognitiveContested',
                       'backgroundQuadratic'],
                      'year (CE)',
                      'CO2 breathed in the room (ppm)',
                      series_colors=['#c0392b', '#8e1b12',
                                     '#5e0f0a', '#d97b29',
                                     '#3f7fbf'],
                      height=460)),
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


def _sapi(item_id, index, segments, title, path, pick='', hide=''):
    """The STRUCTURED reading of a GET payload (chips / prose / tables /
    key-value; module_pages_seed._sapi shape) — no JSON on screen.
    `pick` = dot-path to render; `hide` = csv of top-level keys to
    drop so nothing lands in the panel's JSON expander."""
    return {
        'id': item_id, 'index': index, 'type': 'component',
        'rowSegmentsUsed': segments, 'gridColumnStart': None,
        'title': title, 'visible': True, 'collapsed': False,
        'cssClass': '',
        'componentProps': {
            'componentName': 'api-structured-panel',
            'inputs': {'path': path, 'pick': pick, 'hideKeys': hide,
                       'title': ''},
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
        # Every panel below is the STRUCTURED reading: the study
        # index as a table of sections, the crossing tables picked
        # out of their kv wrappers, the grade/kind roll-up dicts
        # (dict -> list, the JSON-expander shape) hidden.
        _row(0, [
            _sapi('co2h-study', 0, 12,
                  'CO2 and human health - the study (sections, '
                  'their sources and leads)',
                  '/api/climate/view/view-co2-health'),
        ], min_height=640),
        _row(1, [
            _sapi('co2h-crossings', 0, 4,
                  'When each threshold arrives per room (coupled: '
                  'outdoor fit + indoor offset)',
                  '/api/climate/crossings', pick='coupled.rows'),
            _sapi('co2h-crossings-outdoor', 1, 4,
                  'When each threshold arrives outdoors (per fit)',
                  '/api/climate/crossings', pick='outdoor.crossings'),
            _sapi('co2h-thresholds', 2, 4,
                  'Health thresholds, graded by evidence',
                  '/api/climate/thresholds', pick='thresholds'),
        ]),
        _row(2, [
            _sapi('co2h-history', 0, 4,
                  'What CO2 humans actually lived in - per era',
                  '/api/climate/history', pick='eras.eras'),
            _sapi('co2h-history-range', 1, 4,
                  'Outside the experienced range? (record vs '
                  'present) + the cognition question',
                  '/api/climate/history', hide='eras'),
            _sapi('co2h-sources', 2, 4,
                  'Sources and coverage spans',
                  '/api/climate/sources', pick='sources'),
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


#: A SECOND page, because the eras question deserves its own
#: route rather than a section buried in the study. Same no-code
#: mechanism: rows, not a component.
SEED_CLIMATE_ERA_DISPLAYS = [{
    'name': 'co2-eras',
    'description': (
        'CO2 across three eras - historical, modern and projected '
        '- against one threshold ladder, with the chemical '
        'evidence beside it. Confidence DECREASES toward the '
        'future column, which is the opposite of how such pages '
        'usually read.'),
    'source_class': 'AtmosphericSeriesDefinition',
    'isPage': True, 'pageRoute': 'co2/eras',
    'linkedSolutions': '[]',
    'definition': json.dumps({'rows': [
        # the settings payload nests its three ladders one level
        # down (indoor.spaces / outdoor.settings / the era exposure
        # verdict) — one panel each, so each renders as a table.
        _row(0, [
            _sapi('co2e-scenarios', 0, 4,
                  'Indoors: the room ladder against the thresholds',
                  '/api/climate/settings', pick='indoor.spaces'),
            _sapi('co2e-scenarios-outdoor', 1, 4,
                  'Outdoors: historical, modern and future - one '
                  'ladder, three eras, decreasing confidence',
                  '/api/climate/settings', pick='outdoor.settings'),
            _sapi('co2e-eras-exposure', 2, 4,
                  'Era exposure: background, band, and what was '
                  'worse in the past',
                  '/api/climate/settings',
                  hide='outdoor,indoor,observedLevels')]),
        _row(1, [
            _sapi('co2e-claims', 0, 6,
                  'Every number, classified: measured, cited, '
                  'derived, or OUR MODEL',
                  '/api/climate/claims', pick='claims'),
            _sapi('co2e-symptoms', 1, 6,
                  'The cited symptom ladder, from headache to the '
                  'levels that kill',
                  '/api/climate/symptoms', pick='ladder')]),
        _row(2, [
            _sapi('co2e-biochem', 0, 6,
                  'Chemical imbalances: bicarbonate against '
                  'calcium and measured blood pressure',
                  '/api/climate/biochemistry'),
            _sapi('co2e-citations', 1, 6,
                  'Sources, graded - study vs standard vs '
                  'credentialed press',
                  '/api/climate/citations', pick='thresholds')]),
        _row(3, [
            _table('co2e-spans', 0, 6,
                   'Which source covers which years',
                   'SourceCoverageSpan'),
            _table('co2e-thresholds', 1, 6,
                   'Health thresholds, graded',
                   'CO2HealthThreshold')]),
    ]}),
}]


def seed_climate_pages(manager):
    """The graphs and the page, upserted so an edited config
    converges instead of inserting a duplicate."""
    from composition.custom.seed_upsert import upsert_seed_pairs
    from polariApiServer.graphDefinition import GraphDefinition
    from polariApiServer.displayDefinition import DisplayDefinition
    return upsert_seed_pairs(manager, [
        ('GraphDefinition', GraphDefinition, SEED_CLIMATE_GRAPHS),
        ('DisplayDefinition', DisplayDefinition,
         SEED_CLIMATE_PAGE_DISPLAYS
         + SEED_CLIMATE_ERA_DISPLAYS),
    ], tag='ClimatePagesSeed')


def graph_names():
    """Every graph this module seeds."""
    return sorted(GRAPHS_BY_NAME)


#: The carbon-budget graphs draw from WIDE per-year rows rather
#: than one observation series, because the differential only
#: exists as a relationship BETWEEN series. Listed here so
#: graph_data can route them without guessing from the config.
#: Graphs whose rows are PROJECTED rather than observed.
#: Routed like the budget graphs - they are computed, not read
#: from an observation table.
TRAJECTORY_GRAPHS = frozenset({
    'climate-urban-bedroom-trajectory',
})

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
    if graph_name in TRAJECTORY_GRAPHS:
        from climate.custom.co2_scenarios import urban_bedroom_trajectory
        traj = urban_bedroom_trajectory(manager)
        if not traj.get('ok'):
            return {'ok': False, 'graph': graph_name,
                    'graphConfig': config,
                    'refusal': traj.get('refusal', '')}
        return {'ok': True, 'graph': graph_name,
                'graphConfig': config, 'rows': traj['rows'],
                'rowCount': traj['count'],
                'spans': [], 'citations': [],
                'crossings': traj['crossings'],
                'verdict': traj['verdict'],
                'horizonCaveat': traj['horizonCaveat'],
                'theRoomDoesNotChange': traj['theRoomDoesNotChange'],
                'note': traj['note']}

    if graph_name in BUDGET_GRAPHS:
        from climate.carbon_sinks_seed import budget_graph_rows
        built = budget_graph_rows(manager)
        if not built.get('ok'):
            return {'ok': False, 'graph': graph_name,
                    'graphConfig': config,
                    'refusal': built.get('refusal', '')}
        # NOTE: coverage_citations is a MODULE-LEVEL import.
        # Re-importing it here would make the name
        # function-local and raise UnboundLocalError at the
        # series branch below - the documented gotcha, hit
        # for real while unifying the spans shape.
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
    data_rows, span_names = [], []
    for point in points:
        span = point.get('span', '')
        if span and span not in span_names:
            span_names.append(span)
        data_rows.append({'year': point['year'],
                          'value': point['value'],
                          'span': span})
    cite = coverage_citations(manager, series)
    citations = cite.get('citationLines', []) if cite.get('ok') \
        else []
    # `spans` MUST be the same shape here as on the budget-graph
    # branch above: a list of span OBJECTS carrying
    # measurementKind, not a list of names. It used to return bare
    # strings, so the same key had two shapes depending on which
    # graph you asked for - and the frontend had to sniff the type
    # to find out whether a curve was a splice. A payload whose
    # shape depends on the request is a trap for the next
    # consumer, so the rich rows win and the names stay available
    # under their own key.
    span_rows = cite.get('spans', []) if cite.get('ok') else []
    if not span_rows:
        span_rows = [{'span': n, 'displayName': n,
                      'measurementKind': ''} for n in span_names]
    out = {
        'ok': True, 'graph': graph_name, 'series': series,
        'graphConfig': config, 'rows': data_rows,
        'spans': span_rows, 'spanNames': span_names,
        'citations': citations,
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
