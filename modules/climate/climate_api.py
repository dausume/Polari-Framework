"""
@module climate.climate_api

/api/climate/* — the Climate Change & Atmosphere surface.

Every endpoint returns the engines' refusals VERBATIM. A series
that has not been ingested does not get a plausible number: it
gets the refusal naming the fetch that would open it. This is
health-adjacent information, and a confidently wrong page is the
failure mode the whole module is shaped against.

@consumers polariServer (constructed when 'climate' is enabled)
"""

import json

from objectTreeDecorators import treeObject, treeObjectInit

from composition.data_refs import rows


def _float(request, key):
    raw = request.params.get(key)
    if raw in (None, ''):
        return None
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


class ClimateAPI(treeObject):
    @treeObjectInit
    def __init__(self, polServer):
        self.polServer = polServer
        self.apiName = '/api/climate'
        if polServer is not None:
            add = polServer.falconServer.add_route
            add('/api/climate/series', self, suffix='series')
            add('/api/climate/series/{series_name}', self,
                suffix='series_detail')
            add('/api/climate/ingest/{series_name}', self,
                suffix='ingest')
            add('/api/climate/trend/{series_name}', self,
                suffix='trend')
            add('/api/climate/thresholds', self,
                suffix='thresholds')
            add('/api/climate/spaces', self, suffix='spaces')
            add('/api/climate/crossings', self, suffix='crossings')
            add('/api/climate/physiology', self,
                suffix='physiology')
            add('/api/climate/history', self, suffix='history')
            add('/api/climate/sources', self, suffix='sources')
            add('/api/climate/sinks', self, suffix='sinks')
            add('/api/climate/citations', self,
                suffix='citations')
            add('/api/climate/symptoms', self,
                suffix='symptoms')
            add('/api/climate/settings', self,
                suffix='settings')
            add('/api/climate/ingest-budget', self,
                suffix='ingest_budget')
            add('/api/climate/biomarker', self, suffix='biomarker')
            add('/api/climate/bindings', self, suffix='bindings')
            add('/api/climate/view/{view_name}', self, suffix='view')
            add('/api/climate/graph/{graph_name}', self,
                suffix='graph')
            add('/api/climate/export/series/{series_name}', self,
                suffix='export_series')
            add('/api/climate/export/view/{view_name}', self,
                suffix='export_view')

    # ---- data ------------------------------------------------

    def on_get_series(self, request, response):
        out = []
        for row in rows(self.manager, 'AtmosphericSeriesDefinition'):
            out.append({
                'name': getattr(row, 'name', ''),
                'displayName': getattr(row, 'display_name', ''),
                'measure': getattr(row, 'measure', ''),
                'unit': getattr(row, 'unit', ''),
                'cadence': getattr(row, 'cadence', ''),
                'location': getattr(row, 'location', ''),
                'status': getattr(row, 'status', ''),
                'firstYear': getattr(row, 'first_year', 0.0),
                'lastYear': getattr(row, 'last_year', 0.0),
                'sourceRef': getattr(row, 'source_ref', ''),
                'endpointRef': getattr(row, 'endpoint_ref', ''),
            })
        out.sort(key=lambda s: s['name'])
        response.media = {'ok': True, 'series': out,
                          'count': len(out),
                          'note': ('status "prior" means nothing '
                                   'has been fetched yet - the '
                                   'engines refuse to project from '
                                   'those')}

    def on_get_series_detail(self, request, response, series_name):
        from climate.series_ingest import series_points, series_status
        status = series_status(self.manager, series_name)
        points = series_points(self.manager, series_name)
        if not status.get('ok') and not points:
            response.status = '404 Not Found'
        response.media = {'ok': status.get('ok', False),
                          'series': series_name, 'status': status,
                          'points': points, 'count': len(points)}

    def on_post_ingest(self, request, response, series_name):
        """Fetch a series for real. POST because it reaches the
        network and writes rows."""
        from climate.climate_series import (
            SERIES_PARSERS, SERIES_SPANS,
        )
        from climate.series_ingest import ingest_series
        parser = SERIES_PARSERS.get(series_name)
        if parser is None:
            response.status = '404 Not Found'
            response.media = {
                'ok': False,
                'refusal': (f'no parser registered for series '
                            f'{series_name!r}; known: '
                            f'{sorted(SERIES_PARSERS)}')}
            return
        parser_ref, parser_kwargs = parser
        span = SERIES_SPANS.get(series_name, {})
        series_row = _named(self.manager,
                            'AtmosphericSeriesDefinition',
                            series_name)
        endpoint = getattr(series_row, 'endpoint_ref', '') \
            if series_row is not None else ''
        result = ingest_series(
            self.manager, series_name, endpoint, parser_ref,
            span_name=span.get('span', ''),
            measurement_kind=span.get('kind', 'direct-instrument'),
            archive_name=span.get('archive', ''),
            instrument=span.get('instrument', ''),
            parser_kwargs=parser_kwargs,
            retrieved_by=(request.params.get('retrieved_by') or ''))
        if not result.get('ok'):
            response.status = '502 Bad Gateway'
        response.media = result

    def on_get_trend(self, request, response, series_name):
        from climate.co2_crossing import build_fits, _fit_summary
        from climate.series_ingest import series_points, series_status
        status = series_status(self.manager, series_name)
        if not status.get('ok'):
            response.status = '409 Conflict'
            response.media = status
            return
        fits, refusal = build_fits(series_points(self.manager,
                                                series_name))
        if refusal:
            response.status = '409 Conflict'
            response.media = {'ok': False, 'refusal': refusal}
            return
        response.media = {'ok': True, 'series': series_name,
                          'fits': _fit_summary(fits)}

    # ---- the study -------------------------------------------

    def on_get_thresholds(self, request, response):
        from climate.co2_thresholds import thresholds_report
        response.media = thresholds_report(self.manager)

    def on_get_spaces(self, request, response):
        from climate.co2_indoor import space_offset
        outdoor = _float(request, 'outdoor_ppm')
        if outdoor is None:
            outdoor = _present_outdoor(self.manager)
        if outdoor is None:
            response.status = '409 Conflict'
            response.media = {
                'ok': False,
                'refusal': ('no outdoor level available - ingest '
                            'co2-mauna-loa-annual, or pass '
                            '?outdoor_ppm=')}
            return
        out = []
        for row in rows(self.manager, 'IndoorSpaceProfile'):
            report = space_offset(row, outdoor)
            out.append({'space': getattr(row, 'name', ''),
                        'displayName': getattr(row, 'display_name',
                                               ''),
                        'basis': getattr(row, 'basis', ''),
                        'replacesWith': getattr(row, 'replaces_with',
                                                ''),
                        **report})
        response.media = {'ok': True, 'outdoorPpm': outdoor,
                          'spaces': out, 'count': len(out)}

    def on_get_crossings(self, request, response):
        from climate.co2_crossing import (
            coupled_crossings, monotonicity_check, outdoor_crossings,
        )
        from climate.series_ingest import series_points
        series_name = (request.params.get('series')
                       or 'co2-mauna-loa-annual')
        points = series_points(self.manager, series_name)
        thresholds = list(rows(self.manager, 'CO2HealthThreshold'))
        spaces = list(rows(self.manager, 'IndoorSpaceProfile'))
        outdoor = outdoor_crossings(points, thresholds)
        if not outdoor.get('ok'):
            response.status = '409 Conflict'
            response.media = outdoor
            return
        coupled = coupled_crossings(points, thresholds, spaces)
        response.media = {
            'ok': True, 'series': series_name,
            'outdoor': outdoor, 'coupled': coupled,
            'monotonicity': monotonicity_check(
                outdoor.get('crossings', [])),
        }

    def on_get_physiology(self, request, response):
        from climate.co2_physiology import (
            elimination_gradient, headline, partial_pressure,
        )
        ppm = _float(request, 'ppm')
        levels = [280.0, 427.35, 1000.0, 2500.0]
        if ppm is not None:
            levels = [ppm]
        response.media = {
            'ok': True,
            'rows': [partial_pressure(p) for p in levels],
            'gradient': elimination_gradient(levels[-1]),
            'headline': headline(levels),
        }

    def on_get_history(self, request, response):
        from climate.climate_history import (
            COGNITION_QUESTION, era_co2_summary,
            outside_experienced_range,
        )
        present = _present_outdoor(self.manager) or 0.0
        response.media = {
            'ok': True,
            'eras': era_co2_summary(self.manager),
            'outsideExperiencedRange': outside_experienced_range(
                self.manager, present),
            'cognitionQuestion': COGNITION_QUESTION,
        }

    def on_get_sources(self, request, response):
        from climate.climate_history import coverage_citations
        from climate.climate_sources import source_catalog
        series_name = request.params.get('series') or ''
        payload = source_catalog(self.manager)
        if series_name:
            payload['coverage'] = coverage_citations(
                self.manager, series_name,
                from_year=_float(request, 'from_year'),
                to_year=_float(request, 'to_year'))
        response.media = payload

    def on_post_ingest_budget(self, request, response):
        """Fetch the Global Carbon Budget workbook and store each
        column as its own observation series."""
        from climate.carbon_sinks import ingest_carbon_budget
        result = ingest_carbon_budget(
            self.manager,
            retrieved_by=(request.params.get('retrieved_by') or ''))
        if not result.get('ok'):
            response.status = '502 Bad Gateway'
        response.media = result

    def on_get_citations(self, request, response):
        """Every threshold with its source RESOLVED across all
        registries - government, nonprofit, academic and
        credentialed press."""
        from climate.climate_citations import threshold_citations
        response.media = threshold_citations(self.manager)

    def on_get_settings(self, request, response):
        """co2-E: the 2x2 — urban/non-urban outdoor, every room on
        ITS OWN local outdoor, and the measured levels that check
        the modelled ones. ?band=low|typical|high."""
        from climate.co2_settings import (
            all_space_levels, era_comparison, setting_ladder,
        )
        background = _float(request, 'background_ppm')
        if background is None:
            background = _present_outdoor(self.manager)
        if background is None:
            response.status = '409 Conflict'
            response.media = {
                'ok': False,
                'refusal': ('no background level available - '
                            'ingest co2-mauna-loa-annual, or pass '
                            '?background_ppm=')}
            return
        band = request.params.get('band') or 'typical'
        response.media = {
            'ok': True, 'backgroundPpm': background, 'band': band,
            'outdoor': setting_ladder(self.manager, background),
            'indoor': all_space_levels(self.manager, background,
                                       band=band),
            'observedLevels': era_comparison(self.manager),
        }

    def on_get_symptoms(self, request, response):
        """co2-S: the cited symptom ladder, from a headache to the
        levels that kill. ?max_ppm= clips it; ?indoor_ppm= reports
        which claims a given room has reached."""
        from climate.co2_symptoms import (
            ladder_for_space, symptom_ladder,
        )
        indoor = _float(request, 'indoor_ppm')
        if indoor is not None:
            payload = ladder_for_space(self.manager, indoor)
        else:
            payload = symptom_ladder(
                self.manager, max_ppm=_float(request, 'max_ppm')
                or 0.0)
        if not payload.get('ok'):
            response.status = '409 Conflict'
        response.media = payload

    def on_get_sinks(self, request, response):
        """co2-6: which sinks are largest, what they sequester,
        and THE SOURCE/SINK DIFFERENTIAL per year - including when
        the two were last in balance, which only the ice cores can
        answer."""
        from climate.carbon_sinks import (
            balance_history, budget_closure, budget_records_from_rows,
            rate_comparison, sink_ranking, sink_trend_report,
            source_sink_differential,
        )
        from climate.series_ingest import series_points
        loaded = budget_records_from_rows(self.manager)
        if not loaded.get('ok'):
            response.status = '409 Conflict'
            response.media = loaded
            return
        records = loaded['records']
        differential = source_sink_differential(records)
        ice = series_points(self.manager, 'co2-ice-core-composite')
        instrumental = series_points(self.manager,
                                     'co2-mauna-loa-annual')
        balance = (balance_history(ice, differential) if ice else
                   {'ok': False,
                    'refusal': ('the ice-core series is not '
                                'ingested, and the budget alone '
                                'cannot date the end of balance - '
                                'it begins in 1959, long after')})
        payload = {
            'ok': True,
            'ranking': sink_ranking(records),
            'trend': sink_trend_report(records),
            'differential': differential,
            'balance': balance,
        }
        if balance.get('ok') and instrumental:
            payload['rateComparison'] = rate_comparison(
                balance, instrumental)
        if differential.get('ok') and instrumental:
            payload['closure'] = budget_closure(differential,
                                                instrumental)
        response.media = payload

    def on_get_biomarker(self, request, response):
        """co2-B: the bicarbonate/stress question, answered."""
        from climate.biomarker_link import biomarker_question
        bic, dep, mid = {}, {}, {}
        for row in rows(self.manager, 'BiomarkerCycleObservation'):
            cycle = getattr(row, 'cycle', '')
            if not cycle:
                continue
            start = float(getattr(row, 'cycle_start_year', 0.0))
            end = float(getattr(row, 'cycle_end_year', 0.0))
            mid[cycle] = (start + end) / 2.0 if end else start
            series = getattr(row, 'series_ref', '')
            if 'bicarbonate' in series:
                bic[cycle] = float(getattr(row, 'mean', 0.0))
            elif 'depress' in series or 'phq' in series:
                bic.setdefault(cycle, bic.get(cycle))
                dep[cycle] = float(getattr(row, 'mean', 0.0))
        bic = {k: v for k, v in bic.items() if v}
        if len(bic) < 3:
            response.status = '409 Conflict'
            response.media = {
                'ok': False,
                'refusal': ('fewer than 3 bicarbonate cycles are '
                            'ingested - POST '
                            '/api/climate/ingest/<series> for the '
                            'NHANES cycles first; this question is '
                            'not answerable from seeds')}
            return
        outdoor = _present_outdoor(self.manager) or 0.0
        response.media = biomarker_question(
            bic, dep, mid, _float(request, 'ppm_from') or 368.14,
            _float(request, 'ppm_to') or outdoor,
            within_cycle_sd=_float(request, 'within_cycle_sd'))

    def on_get_bindings(self, request, response):
        """co2-9: what simulation input is bound to what series."""
        from climate.sim_binding import binding_report
        response.media = binding_report(self.manager)

    def on_post_bindings(self, request, response):
        """Apply the bindings. POST because it writes into another
        module's simulation inputs."""
        from climate.sim_binding import apply_all
        dry = bool(request.params.get('dry_run'))
        response.media = apply_all(self.manager, dry_run=dry)

    def on_get_view(self, request, response, view_name):
        from climate.climate_views import view_payload
        payload = view_payload(self.manager, view_name)
        if not payload.get('ok'):
            response.status = '404 Not Found'
        response.media = payload

    def on_get_graph(self, request, response, graph_name):
        from climate.climate_pages import graph_data
        payload = graph_data(self.manager, graph_name)
        if not payload.get('ok'):
            response.status = '404 Not Found'
        response.media = payload

    # ---- export ----------------------------------------------

    def on_get_export_series(self, request, response, series_name):
        from climate.climate_export import export_series
        fmt = request.params.get('format') or 'markdown'
        result = export_series(
            self.manager, series_name, fmt=fmt,
            from_year=_float(request, 'from_year'),
            to_year=_float(request, 'to_year'))
        _respond_export(response, result,
                        download=request.params.get('download'))

    def on_get_export_view(self, request, response, view_name):
        from climate.climate_export import export_view_markdown
        result = export_view_markdown(self.manager, view_name)
        _respond_export(response, result,
                        download=request.params.get('download'))


def _respond_export(response, result, download=None):
    """`?download=1` returns the raw file with a filename; without
    it the JSON envelope is returned so a caller can inspect the
    provenance without parsing a document."""
    if not result.get('ok'):
        response.status = '409 Conflict'
        response.media = result
        return
    if not download:
        response.media = result
        return
    response.content_type = result.get('contentType',
                                       'text/plain')
    response.data = result.get('content', '').encode('utf-8')
    response.set_header(
        'Content-Disposition',
        f'attachment; filename="{result.get("filename", "export")}"')


def _named(manager, class_name, name):
    for row in rows(manager, class_name):
        if getattr(row, 'name', '') == name:
            return row
    return None


def _present_outdoor(manager):
    """Today's outdoor level from the ingested record - never a
    constant. Returns None when nothing has been ingested, and the
    callers turn that into a refusal."""
    from climate.series_ingest import series_points
    points = series_points(manager, 'co2-mauna-loa-annual')
    return points[-1]['value'] if points else None
