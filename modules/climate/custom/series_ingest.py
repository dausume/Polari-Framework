"""
@module climate.custom.series_ingest

FETCH -> PARSE -> ROWS, with the provenance chain written on the
way through (CO2_HEALTH_PLAN.md §11 co2-1).

One path serves every source, because the differences between
sources live on their `APIEndpoint` rows:

    APIEndpoint row (url, format, signature, params)
      -> endpoint_fetch.fetch_endpoint   (validates the payload)
        -> series_parsers.get_parser     (named, never guessed)
          -> AtmosphericObservation rows (each carrying span_ref)
            + SourceCoverageSpan         (which source, which years)
            + SourceRetrieval            (when we copied it, sha256)

⚠ Ingest is the only writer of `AtmosphericObservation`. Seeds
never invent observations: a measurement that a seed pass can
create is not a measurement. The seed pass creates the SERIES
(what we intend to measure) and the ingest creates the POINTS.

The series' `status` flips to 'ingested' only after rows land, and
`first_year`/`last_year` are DERIVED from those rows — a declared
range that disagrees with the data is exactly the drift this
project guards against.

@consumers climate.climate_api, climate.climate_selftest,
polariServer
"""

import datetime

from climate.custom.series_parsers import get_parser, series_bounds
from polariApiProfiler.endpoint_fetch import (
    decode_body, fetch_endpoint,
)

PROV = 'co2-1'


def _now():
    return datetime.datetime.now(datetime.timezone.utc)\
            .strftime('%Y-%m-%dT%H:%M:%SZ')


def _rows(manager, class_name):
    from composition.custom.data_refs import rows
    return rows(manager, class_name)


def _named(manager, class_name, name):
    for row in _rows(manager, class_name):
        if getattr(row, 'name', '') == name:
            return row
    return None


def fetch_and_parse(endpoint_row, parser_ref, params=None,
                    fetcher=None, parser_kwargs=None):
    """Endpoint -> points, with every refusal passed through
    verbatim. The surface never softens an upstream 'I do not
    know' into an answer."""
    parser, refusal = get_parser(parser_ref)
    if parser is None:
        return {'ok': False, 'refusal': refusal, 'points': []}

    result = fetch_endpoint(endpoint_row, params=params,
                            fetcher=fetcher)
    if not result.get('ok'):
        return {'ok': False, 'refusal': result.get('refusal', ''),
                'points': [], 'urlRedacted':
                    result.get('url_redacted', ''),
                'httpStatus': result.get('status', 0)}

    body, err = decode_body(result)
    if err:
        return {'ok': False, 'refusal': err, 'points': [],
                'urlRedacted': result.get('url_redacted', '')}

    parsed = parser(body, **(parser_kwargs or {}))
    if not parsed.get('ok'):
        return {'ok': False, 'points': [],
                'refusal': parsed.get('refusal', 'parser refused'),
                'urlRedacted': result.get('url_redacted', '')}

    parsed.update({
        'urlRedacted': result.get('url_redacted', ''),
        'sha256': result.get('sha256', ''),
        'bytes': result.get('bytes', 0),
        'httpStatus': result.get('status', 200),
    })
    return parsed


def ingest_series(manager, series_name, endpoint_name, parser_ref,
                  span_name='', measurement_kind='direct-instrument',
                  archive_name='', instrument='',
                  params=None, fetcher=None, parser_kwargs=None,
                  retrieved_by='', retrieved_by_group='',
                  replace_existing=True):
    """Ingest one series end to end. Returns a report; never
    raises.

    `replace_existing` drops this series' prior observations for
    the same span before writing, so a re-ingest CONVERGES rather
    than doubling every point - the same reason seeding uses
    upsert.
    """
    from climate.climate_basis import (
        AtmosphericObservation, SourceCoverageSpan,
    )

    series = _named(manager, 'AtmosphericSeriesDefinition',
                    series_name)
    if series is None:
        return {'ok': False,
                'refusal': (f'no AtmosphericSeriesDefinition named '
                            f'{series_name!r} - seed the series '
                            f'before ingesting into it')}
    endpoint = _named(manager, 'APIEndpoint', endpoint_name)
    if endpoint is None:
        return {'ok': False,
                'refusal': (f'no APIEndpoint named '
                            f'{endpoint_name!r} - '
                            f'seed_climate_sources delivers it')}

    parsed = fetch_and_parse(endpoint, parser_ref, params=params,
                             fetcher=fetcher,
                             parser_kwargs=parser_kwargs)
    if not parsed.get('ok'):
        return {'ok': False, 'series': series_name,
                'refusal': parsed.get('refusal', ''),
                'urlRedacted': parsed.get('urlRedacted', '')}

    points = parsed['points']
    first_year, last_year, count = series_bounds(points)
    span_name = span_name or f'{series_name}--span'

    retrieval = record_retrieval_row(
        manager, series, endpoint, parsed,
        retrieved_by=retrieved_by,
        retrieved_by_group=retrieved_by_group, row_count=count)

    # The span: WHICH source covered WHICH stretch of the axis.
    resolution = 0.0
    if count > 1:
        resolution = abs(last_year - first_year) / float(count - 1)
    span_seed = {
        'name': span_name, 'series_ref': series_name,
        'display_name': getattr(endpoint, 'displayName',
                                endpoint_name),
        'measurement_kind': measurement_kind,
        'from_year': first_year, 'to_year': last_year,
        'source_ref': _source_of(endpoint),
        'endpoint_ref': endpoint_name,
        'archive_name': archive_name, 'instrument': instrument,
        'resolution_years': round(resolution, 4),
        'citation_text': getattr(endpoint, 'citationText', ''),
        'doi_or_url': parsed.get('urlRedacted', ''),
        'color': '#888888',
        'typical_uncertainty': _mean_uncertainty(points),
        'is_prior': False, 'provenance_id': PROV,
        'notes': (f'{count} points; resolution ~'
                  f'{resolution:.1f} yr between samples'),
    }
    _upsert(manager, 'SourceCoverageSpan', SourceCoverageSpan,
            [span_seed])

    if replace_existing:
        _drop_observations(manager, series_name, span_name)

    written, errors = 0, []
    for idx, point in enumerate(points):
        seed = {
            'name': f'{series_name}--{idx:06d}',
            'series_ref': series_name, 'span_ref': span_name,
            'year': point['year'], 'value': point['value'],
            'uncertainty': point.get('uncertainty', 0.0),
            'sample_count': 0, 'revision': '',
            'retrieval_ref': retrieval.get('name', ''),
            'is_prior': False, 'provenance_id': PROV, 'notes': '',
        }
        try:
            AtmosphericObservation(**seed, manager=manager)
            written += 1
        except Exception as exc:  # one bad row must not kill the set
            errors.append({'index': idx, 'error': str(exc)})

    _update_series(manager, series, first_year, last_year, written)

    return {
        'ok': True, 'series': series_name,
        'endpoint': endpoint_name, 'span': span_name,
        'pointsParsed': count, 'rowsWritten': written,
        'firstYear': first_year, 'lastYear': last_year,
        'resolutionYears': round(resolution, 4),
        'skippedCount': parsed.get('skippedCount', 0),
        'skippedSample': parsed.get('skipped', []),
        'sha256': parsed.get('sha256', ''),
        'bytes': parsed.get('bytes', 0),
        'urlRedacted': parsed.get('urlRedacted', ''),
        'retrieval': retrieval.get('name', ''),
        'errors': errors,
        'note': ('observations are written by ingest only - a '
                 'measurement a seed pass could create is not a '
                 'measurement'),
    }


def _source_of(endpoint):
    """Which SOURCE publishes this endpoint - government or not.

    Was a GovSource-only scan, which silently returned '' for the
    two publishers that are not governments (ASHRAE and the Global
    Carbon Project live in the nonprofit registry). An empty
    source_ref on a span means a chart cannot name who measured
    it, so the lookup now goes through the cross-registry map.
    """
    from climate.climate_sources_seed import source_of_endpoint
    return source_of_endpoint(getattr(endpoint, 'name', ''))


def _mean_uncertainty(points):
    vals = [p.get('uncertainty', 0.0) or 0.0 for p in points]
    vals = [v for v in vals if v]
    return round(sum(vals) / len(vals), 6) if vals else 0.0


def _upsert(manager, class_name, cls, seeds):
    from composition.custom.seed_upsert import upsert_seed_pairs
    return upsert_seed_pairs(manager, [(class_name, cls, seeds)],
                             tag='ClimateIngest')


def _drop_observations(manager, series_name, span_name):
    """Remove this span's existing points so a re-ingest converges
    instead of doubling the series."""
    table = (getattr(manager, 'objectTables', None) or {}).get(
        'AtmosphericObservation', {})
    if not isinstance(table, dict):
        return 0
    doomed = [key for key, row in table.items()
              if getattr(row, 'series_ref', '') == series_name
              and getattr(row, 'span_ref', '') == span_name]
    db = getattr(manager, 'db', None)
    for key in doomed:
        row = table.pop(key, None)
        if db is not None and row is not None:
            try:
                db.deleteInstanceInDB(row)
            except Exception:
                pass  # in-memory drop still converges the report
    return len(doomed)


def _update_series(manager, series, first_year, last_year, count):
    """Status and bounds DERIVE from the rows that landed."""
    if count <= 0:
        return
    series.first_year = first_year
    series.last_year = last_year
    series.status = 'ingested'
    db = getattr(manager, 'db', None)
    if db is not None:
        try:
            db.saveInstanceInDB(series)
        except Exception:
            pass


def record_retrieval_row(manager, series, endpoint, parsed,
                         retrieved_by='', retrieved_by_group='',
                         row_count=0):
    """One SourceRetrieval row per ingest: when we copied it, from
    which redacted URL, how many rows, and the CHECKSUM.

    The sha256 is what makes "the source changed" detectable later
    - a citation without one cannot tell a revision from a
    memory.
    """
    from climate.climate_basis import AtmosphericObservation  # noqa
    name = (f'{getattr(series, "name", "series")}--'
            f'{_now().replace(":", "").replace("-", "")}')
    seed = {
        'name': name,
        'source_name': _source_of(endpoint),
        'endpoint_name': getattr(endpoint, 'name', ''),
        'what': (f'{getattr(series, "display_name", "")} '
                 f'[sha256:{parsed.get("sha256", "")[:16]} '
                 f'{parsed.get("bytes", 0)} bytes]').strip(),
        'retrieved_at': _now(),
        'retrieved_by': retrieved_by or 'climate.custom.series_ingest',
        'retrieved_by_group': retrieved_by_group,
        'row_count': row_count,
        'provenance_url': parsed.get('urlRedacted', ''),
        'notes': (f'HTTP {parsed.get("httpStatus", 0)}; '
                  f'{parsed.get("skippedCount", 0)} unparsed lines'),
    }
    try:
        from dmvdata.gov_sources_basis import SourceRetrieval
        SourceRetrieval(**seed, manager=manager)
    except Exception as exc:
        return {'name': '', 'error': str(exc), **seed}
    return seed


def series_points(manager, series_name):
    """Every observation of a series, sorted, with its span."""
    out = []
    for row in _rows(manager, 'AtmosphericObservation'):
        if getattr(row, 'series_ref', '') != series_name:
            continue
        out.append({'year': float(getattr(row, 'year', 0.0)),
                    'value': float(getattr(row, 'value', 0.0)),
                    'uncertainty': float(
                        getattr(row, 'uncertainty', 0.0)),
                    'span': getattr(row, 'span_ref', '')})
    out.sort(key=lambda p: p['year'])
    return out


def series_status(manager, series_name):
    """Is this series safe to project from? The engines ask here.

    'prior' or 'modelled' REFUSES: the plan's top rule is that a
    placeholder must never be projected from silently.
    """
    series = _named(manager, 'AtmosphericSeriesDefinition',
                    series_name)
    if series is None:
        return {'ok': False,
                'refusal': (f'no series named {series_name!r}')}
    status = getattr(series, 'status', 'prior')
    if status != 'ingested':
        return {'ok': False, 'status': status,
                'refusal': (f'series {series_name!r} is '
                            f'{status!r}, not "ingested" - fetch '
                            f'it from '
                            f'{getattr(series, "endpoint_ref", "?")} '
                            f'before projecting from it')}
    return {'ok': True, 'status': status,
            'firstYear': getattr(series, 'first_year', 0.0),
            'lastYear': getattr(series, 'last_year', 0.0)}
