"""
@module climate.climate_views

THE CO2/HEALTH STUDY AS SECTIONS (CO2_HEALTH_PLAN.md §9a co2-7).
Each section names an existing engine entry point, runs it, and
keeps whatever comes back — including a refusal — inside the
payload. The assembler is motors/clock_views.py's `view_payload`
in structure, deliberately: one shape for every study page in the
codebase means a reader learns it once.

WHY THERE IS NO ClimateViewDefinition CLASS. Reusing motors'
`ClockViewDefinition` is wrong — it is motors-owned and its
discipline enum has no climate value, so every climate row would
sit in it mislabelled. Adding a near-identical climate class is
also wrong: the climate module must stay DROPPABLE, and a class
whose only job is to hold a list of section names earns its
registration, its table and its schema freeze for nothing when
the sections are code-dispatched anyway. So the views are plain
module-level seed data (`SEED_CLIMATE_VIEWS` -> `VIEWS_BY_NAME`)
and the NO-CODE surface is climate_pages.py, where the graphs and
the page really are configured rows.

ORDER IS AN ARGUMENT. The plan fixes it and this file keeps it:
what is measured outdoors, then what that becomes indoors, then
the graded thresholds, then the partial-pressure framing that
says what is and is not being claimed, then the crossings, then
the human record (which is where the cognition question is put
AS A QUESTION), then the sources, and last the measurements that
would retire the priors. Read in that order the page argues; read
in any other order it asserts.

A refused section is never dropped. The refusal names the ingest
or the seed pass that would answer it, which is the only kind of
"I do not know" this app is allowed to give.

@consumers climate.climate_api, climate.climate_export,
climate.climate_pages, climate.selftest_climate
"""

from climate.climate_history import (
    COGNITION_QUESTION, coverage_citations, era_co2_summary,
    outside_experienced_range,
)
from climate.climate_sources import source_catalog
from climate.co2_crossing import (
    LINEAR_WINDOW_YEARS, build_fits, coupled_crossings,
    monotonicity_check, outdoor_crossings,
)
from climate.co2_indoor import space_offset, ventilation_knob
from climate.co2_physiology import (
    elimination_gradient, headline as pressure_headline,
    partial_pressure,
)
from climate.co2_thresholds import thresholds_report
from climate.co2_trend import compare_velocity, velocity_from_source
from climate.series_ingest import series_points, series_status
from composition.data_refs import rows

PROV = 'co2-7'

#: The outdoor record every other section is measured from.
OUTDOOR_SERIES = 'co2-mauna-loa-annual'
#: NOAA's OWN velocity term — the second path to the same number.
GROWTH_SERIES = 'co2-growth-rate-mauna-loa'
#: The only series that reaches human prehistory.
ICE_SERIES = 'co2-ice-core-composite'

#: The ppm levels the partial-pressure section converts. Chosen to
#: bracket the argument: pre-industrial, today, the quoted indoor
#: figure, and the contested chamber-study level.
PRESSURE_LEVELS = (280.0, 427.35, 1000.0, 2500.0)

#: What a section says when the outdoor series has not been
#: fetched. Named here once so every consumer refuses the same way.
INGEST_OUTDOOR = (
    "climate.series_ingest.ingest_series(manager, "
    "'co2-mauna-loa-annual', 'noaa-co2-annmean-mlo', "
    "'noaa-annual')")


def _refuse(text, **extra):
    """Every failure in this file leaves by this door."""
    out = {'ok': False, 'refusal': text}
    out.update(extra)
    return out


def _row(label, value, note, verdict='ok'):
    """One headline row — the renderer contract the motors views
    established: label, value, note, verdict."""
    return {'label': label, 'value': value, 'note': note,
            'verdict': verdict}


def _series_or_refusal(manager, series_name):
    """(points, refusal). A series that is not 'ingested' refuses
    by name rather than projecting from a placeholder."""
    status = series_status(manager, series_name)
    if not status.get('ok'):
        return None, status.get(
            'refusal', f'series {series_name!r} is not ingested')
    points = series_points(manager, series_name)
    if not points:
        return None, (
            f'series {series_name!r} reports "ingested" but has no '
            f'AtmosphericObservation rows — re-run the ingest '
            f'({INGEST_OUTDOOR} for the outdoor record)')
    return points, ''


def present_outdoor_ppm(manager, series_name=OUTDOOR_SERIES):
    """Today's outdoor background, read from the ingested series'
    LAST point. Returns (ppm, year, refusal)."""
    points, refusal = _series_or_refusal(manager, series_name)
    if refusal:
        return None, None, refusal
    last = points[-1]
    return last['value'], last['year'], ''


# ---------------------------------------------------------------
# Section sources — every one an engine that already exists
# ---------------------------------------------------------------

def _outdoor_record(manager, a):
    """1. WHAT IS MEASURED: the instrumental record itself."""
    series = a.get('series') or OUTDOOR_SERIES
    points, refusal = _series_or_refusal(manager, series)
    if refusal:
        return _refuse(refusal, series=series)
    first, last = points[0], points[-1]
    rise = last['value'] - first['value']
    head = [
        _row('series', series,
             f'{len(points)} points, each carrying the '
             f'SourceCoverageSpan it was measured in'),
        _row('record span',
             f'{first["year"]:.0f} to {last["year"]:.0f}',
             'the window every fit below is taken over; a fit '
             'outside it is an extrapolation and says so'),
        _row('latest annual mean',
             f'{last["value"]:.2f} ppm',
             f'{last["year"]:.0f}, +/- '
             f'{last["uncertainty"]:.2f} ppm as published'),
        _row('first annual mean',
             f'{first["value"]:.2f} ppm',
             f'{first["year"]:.0f} — the start of the direct '
             f'instrumental record, not of CO2'),
        _row('rise over the record', f'{rise:+.2f} ppm',
             'a difference of two measured values; no model, no '
             'fit and no baseline choice enters this number'),
    ]
    return {
        'ok': True, 'series': series, 'points': points,
        'firstYear': first['year'], 'lastYear': last['year'],
        'n': len(points), 'latestYear': last['year'],
        'latestValue': last['value'], 'headline': head,
        'note': 'the points are returned whole so a renderer '
                'draws the measurement, not a summary of it; each '
                'carries its span so the seam between archives '
                'stays visible',
    }


def _summarize_fit(fit):
    """One fit, rounded for display, refusal carried through."""
    if not fit.get('ok'):
        return {'ok': False, 'refusal': fit.get('refusal', '')}
    return {
        'ok': True, 'method': fit.get('method', ''),
        'level': round(fit['level'], 3),
        'velocity': round(fit['velocity'], 5),
        'velocityStderr': round(fit['velocityStderr'], 5),
        'acceleration': round(fit['acceleration'], 6),
        'accelerationStderr': round(fit['accelerationStderr'], 6),
        'nPoints': fit['nPoints'],
        'windowFromYear': fit['windowFromYear'],
        'windowToYear': fit['windowToYear'],
        'residualRms': round(fit['residualRms'], 4),
    }


def _trend_fits(manager, a):
    """1b. VELOCITY AND ACCELERATION, with the publisher's own
    growth rate held against the fitted slope."""
    series = a.get('series') or OUTDOOR_SERIES
    points, refusal = _series_or_refusal(manager, series)
    if refusal:
        return _refuse(refusal, series=series)
    fits, bad = build_fits(points)
    if bad:
        return _refuse(bad, series=series)
    summary = {key: _summarize_fit(fit)
               for key, fit in fits.items()}
    linear = fits.get('linear', {})
    last_year = max(p['year'] for p in points)

    growth = a.get('growth_series') or GROWTH_SERIES
    g_points, g_refusal = _series_or_refusal(manager, growth)
    if g_refusal:
        cross = _refuse(g_refusal, series=growth)
    else:
        source = velocity_from_source(
            g_points, window_from=last_year - LINEAR_WINDOW_YEARS)
        if not source.get('ok'):
            cross = source
        elif not linear.get('ok'):
            cross = _refuse(
                'the linear fit refused, so there is no fitted '
                'slope to hold the published growth rate against')
        else:
            cross = compare_velocity(linear['velocity'],
                                     source['meanVelocity'])
            if cross.get('ok'):
                cross['sourceSeries'] = growth
                cross['sourceWindowFromYear'] = source[
                    'windowFromYear']
                cross['sourceWindowToYear'] = source[
                    'windowToYear']
                cross['sourceStdDev'] = source['stdDev']

    head = []
    for key in ('linear', 'quadratic'):
        entry = summary.get(key, {})
        if not entry.get('ok'):
            head.append(_row(f'{key} fit', 'refused',
                             entry.get('refusal', ''), 'warn'))
            continue
        head.append(_row(
            f'{key} fit velocity',
            f'{entry["velocity"]:.4f} +/- '
            f'{entry["velocityStderr"]:.4f} ppm/yr',
            f'{entry["nPoints"]} points over '
            f'{entry["windowFromYear"]:.0f}-'
            f'{entry["windowToYear"]:.0f}'))
    quad = summary.get('quadratic', {})
    if quad.get('ok'):
        head.append(_row(
            'acceleration',
            f'{quad["acceleration"]:.5f} +/- '
            f'{quad["accelerationStderr"]:.5f} ppm/yr^2',
            'FITTED over a stated window with its own standard '
            'error, never eyeballed off a curve; it is what moves '
            'every crossing date earlier'))
    if cross.get('ok'):
        head.append(_row(
            'fitted slope vs published growth rate',
            f'{cross["relativeDifference"] * 100:.2f} percent apart',
            cross['verdict'],
            'ok' if cross.get('agree') else 'warn'))
    else:
        head.append(_row('published growth rate', 'unavailable',
                         cross.get('refusal', ''), 'warn'))
    return {
        'ok': True, 'series': series, 'fits': summary,
        'crossCheck': cross, 'headline': head,
        'note': 'two independent paths to one velocity: our least-'
                'squares slope and NOAA\'s published growth rate. '
                'Where they disagree beyond tolerance the '
                'DISAGREEMENT IS A FINDING about the window, the '
                'ingest or the published definition — the two '
                'numbers are never averaged together.',
    }


def _thresholds(manager, a):
    """3. THE GRADED TABLE, passed through unchanged."""
    return thresholds_report(manager)


def _partial_pressure(manager, a):
    """4. WHAT ACTS ON A LUNG IS A PRESSURE, not a ppm."""
    gradient = elimination_gradient(427.35)
    if not gradient.get('ok'):
        return gradient
    levels = a.get('ppm_levels') or list(PRESSURE_LEVELS)
    out_rows = []
    for ppm in levels:
        converted = partial_pressure(ppm)
        if not converted.get('ok'):
            out_rows.append({'ppm': ppm, 'ok': False,
                             'refusal': converted.get('refusal',
                                                      '')})
            continue
        out_rows.append({
            'ppm': converted['ppm'],
            'pco2Kpa': converted['pco2Kpa'],
            'pco2Mmhg': converted['pco2Mmhg'],
            'pctOfAlveolar': converted['pctOfAlveolar'],
        })
    return {
        'ok': True,
        'framing': gradient['framing'],
        'levels': levels,
        'rows': out_rows,
        'gradientAtPresent': gradient,
        'headline': pressure_headline(levels),
        'note': 'this section converts units and states a '
                'gradient. It grades nothing: whether a ppm level '
                'harms a person is answered only by the '
                'CO2HealthThreshold rows and their evidence '
                'grades, and blurring the two is how a page '
                'becomes confidently wrong.',
    }


def _indoor_coupling(manager, a):
    """2. WHAT THE OUTDOOR RECORD BECOMES INDOORS, per room."""
    series = a.get('series') or OUTDOOR_SERIES
    outdoor = a.get('outdoor_ppm')
    year = None
    if outdoor is None:
        outdoor, year, refusal = present_outdoor_ppm(manager,
                                                     series)
        if refusal:
            return _refuse(
                f'the indoor coupling is measured FROM the outdoor '
                f'background, and that is not available: {refusal}',
                series=series)
    try:
        outdoor = float(outdoor)
    except (TypeError, ValueError):
        return _refuse('outdoor_ppm must be a number in ppm')

    spaces = rows(manager, 'IndoorSpaceProfile')
    if not spaces:
        return _refuse(
            'no IndoorSpaceProfile rows — run '
            'climate.co2_indoor.seed_indoor_spaces(manager), or '
            'the climate module is not booted')
    out_rows, head = [], [
        _row('outdoor background used', f'{outdoor:.2f} ppm',
             f'the last ingested point of {series}'
             + (f' ({year:.0f})' if year is not None else ''))]
    for space in spaces:
        name = getattr(space, 'name', '')
        offset = space_offset(space, outdoor)
        if not offset.get('ok'):
            out_rows.append({'space': name, 'ok': False,
                             'refusal': offset.get('refusal', '')})
            head.append(_row(name, 'refused',
                             offset.get('refusal', ''), 'warn'))
            continue
        knob = ventilation_knob(space, outdoor, factor=2.0)
        entry = {
            'space': name,
            'displayName': offset['displayName'],
            'category': getattr(space, 'category', ''),
            'indoorPpmToday': round(offset['indoorPpm'], 1),
            'offsetPpm': round(offset['offsetPpm'], 1),
            'occupancy': offset['occupancy'],
            'volumeM3': offset['volumeM3'],
            'airChangesPerHour': offset['airChangesPerHour'],
            'basis': getattr(space, 'basis', ''),
            'replacesWith': getattr(space, 'replaces_with', ''),
            'note': offset['note'],
        }
        if knob.get('ok'):
            entry['ventilationKnob'] = {
                'baseAch': knob['baseAch'],
                'doubledAch': knob['newAch'],
                'ppmDelta': round(knob['deltaPpm'], 1),
                'newPpm': round(knob['newPpm'], 1),
                'note': 'doubling the air changes moves the '
                        'steady state by this much — the offset '
                        'is a VENTILATION property, not an '
                        'inevitability',
            }
        else:
            entry['ventilationKnob'] = {
                'ok': False, 'refusal': knob.get('refusal', '')}
        out_rows.append(entry)
        head.append(_row(
            entry['displayName'] or name,
            f'{entry["indoorPpmToday"]:.0f} ppm',
            f'{entry["offsetPpm"]:.0f} ppm above outdoor at '
            f'{entry["airChangesPerHour"]:g} ACH with '
            f'{entry["occupancy"]:g} occupant(s) in '
            f'{entry["volumeM3"]:g} m3'))
    return {
        'ok': True, 'series': series, 'outdoorPpm': outdoor,
        'outdoorYear': year, 'spaces': out_rows,
        'headline': head,
        'note': 'indoor = outdoor + emission/ventilation — the '
                'SAME steady-state equation the aquaponics module '
                'solves for a crop, with the source term\'s sign '
                'flipped. Every room here is an ARCHETYPE whose '
                'replaces_with is a CO2 meter, never a measured '
                'room.',
    }


def _crossings(manager, a):
    """5. THE CROSSINGS: threshold x space x year, banded."""
    series = a.get('series') or OUTDOOR_SERIES
    points, refusal = _series_or_refusal(manager, series)
    if refusal:
        return _refuse(refusal, series=series)
    thresholds = rows(manager, 'CO2HealthThreshold')
    if not thresholds:
        return _refuse(
            'no CO2HealthThreshold rows — run '
            'climate.co2_thresholds.seed_co2_thresholds(manager)')
    spaces = rows(manager, 'IndoorSpaceProfile')
    if not spaces:
        return _refuse(
            'no IndoorSpaceProfile rows — run '
            'climate.co2_indoor.seed_indoor_spaces(manager)')

    coupled = coupled_crossings(points, thresholds, spaces)
    outdoors = outdoor_crossings(points, thresholds)
    monotone = {'ok': False,
                'refusal': 'no outdoor crossings to check'}
    if outdoors.get('ok'):
        monotone = monotonicity_check(outdoors.get('crossings',
                                                   []))
    head = []
    if coupled.get('ok'):
        head.append(_row(
            'present outdoor level',
            f'{coupled["presentPpm"]:.2f} ppm',
            'the fitted level at the window end — the point every '
            'band is solved forward from'))
        crossed = [r for r in coupled.get('rows', [])
                   if r.get('alreadyCrossed')]
        head.append(_row(
            'room/threshold pairs already past the line',
            f'{len(crossed)} of {len(coupled.get("rows", []))}',
            'an already-crossed pair reports ALREADY-CROSSED with '
            'the level that put it there, never a negative '
            '"years away"'))
    head.append(_row(
        'outdoor crossings monotone in the threshold',
        'yes' if monotone.get('ok') else 'NO',
        monotone.get('note', monotone.get('refusal', '')),
        'ok' if monotone.get('ok') else 'warn'))
    return {
        'ok': True, 'series': series, 'coupled': coupled,
        'outdoor': outdoors, 'monotonicity': monotone,
        'headline': head,
        'note': 'every answer is a BAND: the linear and quadratic '
                'fits bracket the crossing and the gap between '
                'them IS the acceleration. A single year with no '
                'band is the documented failure mode of this '
                'page. A DIFFERENTIAL threshold becomes absolute '
                'only by adding outdoor CO2 to it, so it rises '
                'with the record.',
    }


def _human_history(manager, a):
    """6. WHAT CO2 HUMANS ACTUALLY LIVED IN — and the cognition
    question, kept AS A QUESTION."""
    series = a.get('ice_series') or ICE_SERIES
    eras = era_co2_summary(manager, series)
    if not eras.get('ok'):
        return eras
    present, year, refusal = present_outdoor_ppm(
        manager, a.get('series') or OUTDOOR_SERIES)
    if refusal:
        comparison = _refuse(refusal)
    else:
        comparison = outside_experienced_range(manager, present,
                                               series)
    head = []
    if comparison.get('ok'):
        head.append(_row(
            'today against the record maximum',
            f'{comparison["ratio"]:.2f}x',
            f'{comparison["presentPpm"]:.2f} ppm today against a '
            f'{comparison["recordMaxPpm"]:.1f} ppm maximum over '
            f'{comparison["nPoints"]} samples before year '
            f'{comparison["excludeAfterYear"]:.0f}'))
        head.append(_row(
            'the lowest air humans are recorded in',
            f'{comparison["recordMinPpm"]:.1f} ppm',
            'the glacial minimum — humans evolved, spread and '
            'invented agriculture BELOW today\'s level, which is '
            'why any cognition claim read off this curve has the '
            'sign backwards'))
    else:
        head.append(_row('today against the record maximum',
                         'not available',
                         comparison.get('refusal', ''), 'warn'))
    covered = [e for e in eras.get('eras', [])
               if e.get('nPoints', 0) > 0]
    head.append(_row(
        'eras with ice-core coverage',
        f'{len(covered)} of {len(eras.get("eras", []))}',
        'an era reported with nPoints 0 is the SEAM where this '
        'archive stops and the instrument begins — an absent '
        'bucket is a finding about coverage, not a bug'))
    head.append(_row(
        'were past minds affected by past CO2?',
        'THIS RECORD CANNOT ANSWER IT',
        'no measurement of cognitive performance exists for any '
        'prehistoric population, so the question stands open in '
        'BOTH directions; the full statement is below',
        'warn'))
    return {
        'ok': True, 'iceSeries': series,
        'eras': eras.get('eras', []),
        'erasNote': eras.get('note', ''),
        'comparison': comparison,
        'presentYear': year,
        'question': COGNITION_QUESTION,
        'headline': head,
        'note': 'the cognition question is presented AS A '
                'QUESTION, with the four reasons this record '
                'cannot answer it and the study design that '
                'would. A page that drew a correlation here '
                'would be inventing the evidence it lacks.',
    }


def _sources(manager, a):
    """7. WHO SAYS SO — the catalog, plus the citations for
    exactly the window the page shows."""
    catalog = source_catalog(manager)
    citations = {}
    for series in (a.get('series') or OUTDOOR_SERIES,
                   a.get('ice_series') or ICE_SERIES):
        citations[series] = coverage_citations(manager, series)
    head = [_row('sources', str(catalog.get('count', 0)),
                 catalog.get('note', ''))]
    for series, cite in citations.items():
        if cite.get('ok'):
            head.append(_row(
                f'{series} coverage',
                f'{len(cite.get("spans", []))} span(s)',
                cite.get('note', '')))
        else:
            head.append(_row(f'{series} coverage', 'refused',
                             cite.get('refusal', ''), 'warn'))
    return {
        'ok': True, 'catalog': catalog, 'citations': citations,
        'headline': head,
        'note': 'the citations are for the FULL window each '
                'series covers, so the page cites exactly what it '
                'shows; where two measurement kinds meet, the '
                'window is a SPLICE and every line must be cited '
                'together.',
    }


def _series_replacement(row):
    """A series that is not ingested names the fetch that would
    retire it — the same replaces_with discipline, on status."""
    name = getattr(row, 'name', '')
    status = getattr(row, 'status', 'prior')
    endpoint = getattr(row, 'endpoint_ref', '') or 'its endpoint'
    return {
        'what': getattr(row, 'display_name', '') or name,
        'currentBasis': f'series status {status!r} — engines '
                        f'refuse to project from it',
        'replacesWith': f'ingest it from {endpoint} '
                        f'(climate.series_ingest.ingest_series)',
        'kind': 'series',
    }


def _what_would_change_this(manager, a):
    """8. THE MEASUREMENTS THAT WOULD RETIRE THE PRIORS. This is
    the section that makes the page trustworthy."""
    items = []
    for row in rows(manager, 'CO2HealthThreshold'):
        replaces = getattr(row, 'replaces_with', '')
        if not replaces:
            continue
        items.append({
            'what': getattr(row, 'display_name', '')
            or getattr(row, 'name', ''),
            'currentBasis': (
                f'{getattr(row, "evidence_grade", "")} — '
                f'{getattr(row, "citation_text", "")}').strip(
                    ' -'),
            'replacesWith': replaces,
            'kind': 'threshold',
        })
    for row in rows(manager, 'IndoorSpaceProfile'):
        replaces = getattr(row, 'replaces_with', '')
        if not replaces:
            continue
        items.append({
            'what': getattr(row, 'display_name', '')
            or getattr(row, 'name', ''),
            'currentBasis': getattr(row, 'basis', ''),
            'replacesWith': replaces,
            'kind': 'space',
        })
    for row in rows(manager, 'AtmosphericSeriesDefinition'):
        if getattr(row, 'status', 'prior') != 'ingested':
            items.append(_series_replacement(row))
    if not items:
        return _refuse(
            'no rows carrying replaces_with and every series '
            'ingested — either the climate seed pass has not run '
            'or the module is not booted. This section being '
            'EMPTY is itself a finding: a page with no named '
            'priors is either finished or not loaded, and it is '
            'never finished')
    return {
        'ok': True, 'items': items, 'count': len(items),
        'headline': [_row(
            'named priors on this page', str(len(items)),
            'each one names the measurement that would retire it; '
            'a prior with no retirement condition is an opinion')],
        'note': 'every number on this page that is NOT a '
                'measurement appears here with the work that '
                'would replace it. That list is the difference '
                'between a study and an assertion, which is why '
                'it is the last section rather than a footnote.',
    }


def _carbon_sinks(manager, args):
    """co2-6: which sinks are largest, what they sequester, and
    THE SOURCE/SINK DIFFERENTIAL - including when the two were
    last in balance, which only the ice cores can date."""
    from climate.carbon_sinks import (
        balance_history, budget_closure, budget_records_from_rows,
        rate_comparison, sink_ranking, sink_trend_report,
        source_sink_differential,
    )
    loaded = budget_records_from_rows(manager)
    if not loaded.get('ok'):
        return loaded
    records = loaded['records']
    ranking = sink_ranking(records)
    differential = source_sink_differential(records)
    trend = sink_trend_report(records)
    ice = series_points(manager, args.get('ice_series') or
                        ICE_SERIES)
    instrumental = series_points(manager, args.get('series') or
                                 OUTDOOR_SERIES)
    balance = (balance_history(ice, differential) if ice else
               {'ok': False,
                'refusal': ('the ice-core series is not ingested, '
                            'and the budget alone cannot date the '
                            'end of balance - it begins in 1959, '
                            'long after')})
    headline = []
    for part in (ranking, differential, trend):
        if part.get('ok'):
            headline.extend(part.get('headline') or [])
    payload = {
        'ok': True, 'ranking': ranking, 'differential': differential,
        'trend': trend, 'balance': balance, 'headline': headline,
        'note': ('the sinks are doing MORE work every decade and '
                 'still falling further behind, because emissions '
                 'grew faster. Only the differential shows both at '
                 'once, which is why it has its own graph.'),
    }
    if balance.get('ok') and instrumental:
        rc = rate_comparison(balance, instrumental)
        payload['rateComparison'] = rc
        if rc.get('ok'):
            headline.extend(rc.get('headline') or [])
    if differential.get('ok') and instrumental:
        payload['closure'] = budget_closure(differential,
                                            instrumental)
    return payload


SECTION_SOURCES = {
    'outdoor-record': _outdoor_record,
    'trend-fits': _trend_fits,
    'thresholds': _thresholds,
    'partial-pressure': _partial_pressure,
    'indoor-coupling': _indoor_coupling,
    'crossings': _crossings,
    'human-history': _human_history,
    'carbon-sinks': _carbon_sinks,
    'sources': _sources,
    'what-would-change-this': _what_would_change_this,
}


# ---------------------------------------------------------------
# The view, as seed data — order is the argument
# ---------------------------------------------------------------

SEED_CLIMATE_VIEWS = [
    {'name': 'view-co2-health',
     'display_name': 'CO2 and human health',
     'description': 'What the outdoor record is, what it becomes '
                    'indoors, what is claimed to happen to a '
                    'person at those levels, when each line '
                    'arrives, and what would change every answer '
                    'here.',
     'sections': [
         {'name': 'outdoor-record', 'source': 'outdoor-record',
          'args': {'series': OUTDOOR_SERIES},
          'lead': 'The instrumental CO2 record as measured, not '
                  'as summarized. Every point carries the source '
                  'span it was measured in, so the seam between '
                  'archives stays visible. Nothing on this page '
                  'is computed until this section has data.',
          'links': [{'label': 'Series rows', 'kind': 'page',
                     'route': '/display/co2/health'}]},
         {'name': 'trend-fits', 'source': 'trend-fits',
          'args': {'series': OUTDOOR_SERIES,
                   'growth_series': GROWTH_SERIES},
          'lead': 'Velocity and acceleration, FITTED over stated '
                  'windows with their own standard errors. The '
                  'fitted slope is then held against NOAA\'s '
                  'published growth rate: two independent paths '
                  'to one number, and disagreement beyond '
                  'tolerance is a finding rather than an '
                  'averaging problem.'},
         {'name': 'indoor-coupling', 'source': 'indoor-coupling',
          'args': {'series': OUTDOOR_SERIES, 'outdoor_ppm': None},
          'lead': 'What that outdoor level becomes in a room. '
                  'Indoor equals outdoor plus emission over '
                  'ventilation — the aquaponics steady-state '
                  'equation with the source term\'s sign flipped. '
                  'Every room here is an archetype whose '
                  'retirement condition is a CO2 meter.'},
         {'name': 'thresholds', 'source': 'thresholds',
          'args': {},
          'lead': 'Every level at which something is claimed to '
                  'happen to a person, GRADED by the evidence '
                  'behind it and carrying the work that failed to '
                  'replicate it. A ventilation indicator, a '
                  'contested chamber study and an occupational '
                  'limit are three kinds of claim and are never '
                  'drawn as one band.'},
         {'name': 'partial-pressure', 'source': 'partial-pressure',
          'args': {},
          'lead': 'ppm is a mixing ratio; what acts on a lung is a '
                  'pressure. Ambient pCO2 even indoors is a '
                  'fraction of a mmHg against an alveolar 40, so '
                  'the mechanism at stake is a slightly reduced '
                  'elimination gradient — not lungs filling with '
                  'CO2. This section says what is NOT being '
                  'claimed.'},
         {'name': 'crossings', 'source': 'crossings',
          'args': {'series': OUTDOOR_SERIES},
          'lead': 'THE TABLE: every threshold against every room, '
                  'as a banded year or an honest ALREADY-CROSSED. '
                  'The band comes from the linear and quadratic '
                  'fits and the gap between them is the '
                  'acceleration. The ventilation knob sits beside '
                  'each row so the reader can act, not only '
                  'worry.'},
         {'name': 'human-history', 'source': 'human-history',
          'args': {'ice_series': ICE_SERIES,
                   'series': OUTDOOR_SERIES},
          'lead': 'What CO2 humans actually lived in across '
                  '800,000 years of ice, era by era, against '
                  'today. The cognition question is put here AS A '
                  'QUESTION, with the four reasons this record '
                  'cannot answer it and the study design that '
                  'could — a correlation drawn here would invent '
                  'the evidence it lacks.'},
         {'name': 'carbon-sinks', 'source': 'carbon-sinks',
          'args': {'series': OUTDOOR_SERIES,
                   'ice_series': ICE_SERIES},
          'lead': 'Which sinks are largest, what they actually '
                  'sequester each year, and the gap between what '
                  'is emitted and what is taken back. The ocean '
                  'leads in every era of the record. The sinks '
                  'are working harder every decade AND falling '
                  'further behind - only the differential shows '
                  'both at once, and it never reaches zero, so '
                  'the question of when sources and sinks last '
                  'balanced belongs to the ice cores.',
          'links': [{'label': 'Source/sink differential',
                     'kind': 'graph',
                     'route': '/api/climate/graph/'
                              'climate-source-sink-differential'},
                    {'label': 'What each sink sequesters',
                     'kind': 'graph',
                     'route': '/api/climate/graph/'
                              'climate-sink-composition'}]},
         {'name': 'sources', 'source': 'sources',
          'args': {'series': OUTDOOR_SERIES,
                   'ice_series': ICE_SERIES},
          'lead': 'Who publishes each number, how it was fetched, '
                  'and which archive covered which stretch of the '
                  'axis. The citations are for exactly the window '
                  'shown; where two measurement kinds meet, the '
                  'curve is a splice and every line is cited '
                  'together.'},
         {'name': 'what-would-change-this',
          'source': 'what-would-change-this', 'args': {},
          'lead': 'Every prior on this page with the measurement '
                  'that would retire it: the thresholds, the room '
                  'archetypes, and any series still unfetched. '
                  'This section is the reason the page is '
                  'trustworthy — a prior with no retirement '
                  'condition is an opinion.'},
     ],
     'provenance_id': PROV},
]

#: Name -> view, built from the seed list so `view_payload` has one
#: place to look and a new view is one dict, not a code change.
VIEWS_BY_NAME = {view['name']: view for view in SEED_CLIMATE_VIEWS}


def climate_view_names():
    """Every view this module can assemble."""
    return sorted(VIEWS_BY_NAME)


def view_payload(manager, view_name, series='', outdoor_ppm=None,
                 ice_series=''):
    """Assemble one view: run its sections in the seeded order and
    keep every refusal IN the payload.

    Caller overrides (series / outdoor_ppm / ice_series) merge over
    each section's seeded args, so the same view can be pointed at
    the global series or at a measured room without a new row.
    """
    view = VIEWS_BY_NAME.get(view_name)
    if view is None:
        return {'ok': False, 'view': view_name,
                'refusal': f'unknown climate view {view_name!r} — '
                           f'one of {climate_view_names()}'}
    out = []
    for section in view.get('sections', []):
        source = section.get('source', '')
        fn = SECTION_SOURCES.get(source)
        if fn is None:
            out.append({'section': section.get('name', source),
                        'ok': False,
                        'refusal': f'unknown source "{source}" — '
                                   f'one of '
                                   f'{sorted(SECTION_SOURCES)}'})
            continue
        args = dict(section.get('args') or {})
        if series:
            args['series'] = series
        if ice_series:
            args['ice_series'] = ice_series
        if outdoor_ppm is not None:
            args['outdoor_ppm'] = outdoor_ppm
        try:
            payload = fn(manager, args)
        except Exception as exc:
            payload = {'ok': False,
                       'refusal': f'section raised: {exc}'}
        out.append({
            'section': section.get('name', source),
            'source': source,
            'lead': section.get('lead', ''),
            'links': list(section.get('links') or []),
            'args': args,
            **({'payload': payload} if payload.get('ok')
               else {'ok': False,
                     'refusal': payload.get('refusal', 'refused'),
                     'suggestion': payload.get('suggestion')})})
    return {
        'ok': True, 'view': view_name,
        'displayName': view.get('display_name', ''),
        'description': view.get('description', ''),
        'provenanceId': view.get('provenance_id', ''),
        'sections': out,
        'refusedSections': [s['section'] for s in out
                            if not s.get('payload')],
        'note': 'a refused section is information: it names what '
                'would answer it. It is never dropped from the '
                'view.',
    }
