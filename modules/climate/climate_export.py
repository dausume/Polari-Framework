"""
@module climate.climate_export

EXPORT A CONFIGURED GRAPH OR PAGE (Dustin 2026-08-02: "leverage
the ability to export our configured graph pages", "all of the
graphs shown should be able to be exported to be displayable on
something like medium", "the sources from data should be traced").

Four formats, one rule: AN EXPORT CARRIES ITS PROVENANCE OR IT IS
NOT AN EXPORT.

- `markdown`  — for Medium/Substack/a README. Tables and prose,
                no external assets, citations inline.
- `csv`       — one row per point, and CRUCIALLY one column per
                provenance fact (span, measurement kind, source,
                citation). A CSV of bare year,value is a number
                laundry: it strips exactly the information that
                made the number trustworthy.
- `json`      — the graph config + the data + the spans, so the
                same rows feed a simulation later without a
                re-fetch. This is the sim-binding format.
- `svg`       — REFUSED here, by design (see `export_svg`).

🔑 THE SPLICE IS THE POINT. A CO2 curve from 800,000 BCE to today
is ice cores for 99.99% of its length and an infrared analyser on
a Hawaiian volcano for the rest. Every export therefore segments
by `SourceCoverageSpan` and states, per segment, who measured it,
how, at what resolution, and with what uncertainty — because a
reader who cannot see the seam cannot judge the curve.

@consumers climate.climate_api, climate.selftest_climate
"""

import csv
import datetime
import io
import json

EXPORT_FORMATS = ('markdown', 'csv', 'json')

#: Exports are dated because a series is re-ingestible: the same
#: graph exported a year apart is two different documents, and
#: only the stamp makes that visible.
_STAMP = '%Y-%m-%d'


def _now():
    return datetime.datetime.utcnow().strftime(_STAMP)


def _spans_by_name(manager):
    from composition.data_refs import rows
    out = {}
    for row in rows(manager, 'SourceCoverageSpan'):
        out[getattr(row, 'name', '')] = row
    return out


def _span_facts(span):
    return {
        'span': getattr(span, 'name', ''),
        'displayName': getattr(span, 'display_name', ''),
        'measurementKind': getattr(span, 'measurement_kind', ''),
        'fromYear': getattr(span, 'from_year', 0.0),
        'toYear': getattr(span, 'to_year', 0.0),
        'archive': getattr(span, 'archive_name', ''),
        'instrument': getattr(span, 'instrument', ''),
        'resolutionYears': getattr(span, 'resolution_years', 0.0),
        'typicalUncertainty': getattr(span, 'typical_uncertainty',
                                      0.0),
        'citation': getattr(span, 'citation_text', ''),
        'url': getattr(span, 'doi_or_url', ''),
    }


def gather(manager, series_name, from_year=None, to_year=None):
    """The one data-gathering path every format shares:
    points + the spans that actually cover them."""
    from climate.series_ingest import series_points, series_status
    status = series_status(manager, series_name)
    if not status.get('ok'):
        return {'ok': False, 'refusal': status.get('refusal', '')}

    points = series_points(manager, series_name)
    if from_year is not None:
        points = [p for p in points if p['year'] >= from_year]
    if to_year is not None:
        points = [p for p in points if p['year'] <= to_year]
    if not points:
        return {'ok': False,
                'refusal': (f'series {series_name!r} has no points '
                            f'in the requested window - widen it, '
                            f'or ingest the series')}

    spans = _spans_by_name(manager)
    used, seen = [], set()
    for point in points:
        key = point.get('span', '')
        if key and key not in seen:
            seen.add(key)
            span = spans.get(key)
            used.append(_span_facts(span) if span is not None
                        else {'span': key, 'citation': '',
                              'measurementKind': 'unknown',
                              'displayName': key})
    kinds = sorted({s.get('measurementKind', '') for s in used})
    return {'ok': True, 'series': series_name, 'points': points,
            'spans': used, 'measurementKinds': kinds,
            'isSplice': len(kinds) > 1,
            'firstYear': points[0]['year'],
            'lastYear': points[-1]['year'], 'n': len(points)}


def _series_row(manager, series_name):
    from composition.data_refs import rows
    for row in rows(manager, 'AtmosphericSeriesDefinition'):
        if getattr(row, 'name', '') == series_name:
            return row
    return None


def export_csv(manager, series_name, from_year=None, to_year=None):
    """One row per point, provenance columns attached.

    The provenance columns are not decoration. A downstream reader
    who receives year,value alone cannot tell an ice-core sample
    smoothed over centuries from an annual instrumental mean, and
    will happily fit a rate through both.
    """
    data = gather(manager, series_name, from_year, to_year)
    if not data.get('ok'):
        return data
    series = _series_row(manager, series_name)
    unit = getattr(series, 'unit', '')
    spans = {s['span']: s for s in data['spans']}

    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator='\n')
    writer.writerow(['year_ce', 'value', 'unit', 'uncertainty',
                     'span', 'measurement_kind', 'archive',
                     'instrument', 'resolution_years', 'citation',
                     'source_url'])
    for point in data['points']:
        span = spans.get(point.get('span', ''), {})
        writer.writerow([
            point['year'], point['value'], unit,
            point.get('uncertainty', 0.0),
            point.get('span', ''), span.get('measurementKind', ''),
            span.get('archive', ''), span.get('instrument', ''),
            span.get('resolutionYears', ''),
            span.get('citation', ''), span.get('url', ''),
        ])
    return {'ok': True, 'series': series_name, 'format': 'csv',
            'filename': f'{series_name}-{_now()}.csv',
            'contentType': 'text/csv', 'content': buf.getvalue(),
            'rowCount': data['n'], 'spans': data['spans'],
            'isSplice': data['isSplice']}


def export_json(manager, series_name, graph_config=None,
                from_year=None, to_year=None):
    """The re-bindable format: config + data + provenance.

    This is what makes "use the same data in simulations later"
    true rather than aspirational - the document carries the
    series identity, its unit, its spans and its citations, so a
    simulation binding it is binding a MEASUREMENT, not a
    spreadsheet someone mailed around.
    """
    data = gather(manager, series_name, from_year, to_year)
    if not data.get('ok'):
        return data
    series = _series_row(manager, series_name)
    doc = {
        'kind': 'polari.climate.series-export',
        'schemaVersion': '1',
        'exportedAt': _now(),
        'series': {
            'name': series_name,
            'displayName': getattr(series, 'display_name', ''),
            'measure': getattr(series, 'measure', ''),
            'unit': getattr(series, 'unit', ''),
            'cadence': getattr(series, 'cadence', ''),
            'location': getattr(series, 'location', ''),
            'sourceRef': getattr(series, 'source_ref', ''),
            'endpointRef': getattr(series, 'endpoint_ref', ''),
            'status': getattr(series, 'status', ''),
            'description': getattr(series, 'description', ''),
        },
        'graphConfig': graph_config or {},
        'coverageSpans': data['spans'],
        'isSplice': data['isSplice'],
        'measurementKinds': data['measurementKinds'],
        'points': data['points'],
        'note': ('bind this by series name; the coverage spans say '
                 'which stretch of the x-axis each source covers, '
                 'and a consumer that ignores them will mistake an '
                 'ice-core resolution for an annual one'),
    }
    return {'ok': True, 'series': series_name, 'format': 'json',
            'filename': f'{series_name}-{_now()}.json',
            'contentType': 'application/json',
            'content': json.dumps(doc, indent=2),
            'document': doc, 'rowCount': data['n']}


def _md_escape(text):
    return str(text or '').replace('|', '\\|').replace('\n', ' ')


def _sample_rows(points, limit):
    """A markdown table with 1901 rows is not a document. Sample
    evenly, and SAY that it is a sample - a silently truncated
    table reads as a complete one."""
    if len(points) <= limit:
        return points, False
    step = len(points) / float(limit)
    picked = [points[int(i * step)] for i in range(limit)]
    if picked[-1] is not points[-1]:
        picked[-1] = points[-1]
    return picked, True


def export_markdown(manager, series_name, title='',
                    from_year=None, to_year=None, max_rows=40,
                    graph_config=None):
    """A self-contained Markdown document - the Medium format.

    No external assets, no image host, no javascript: a table, the
    numbers that matter, and the citations. It renders identically
    in a gist, a PR description, a Medium import and a static site.
    """
    data = gather(manager, series_name, from_year, to_year)
    if not data.get('ok'):
        return data
    series = _series_row(manager, series_name)
    unit = getattr(series, 'unit', '')
    display = getattr(series, 'display_name', series_name)
    heading = title or display

    points = data['points']
    values = [p['value'] for p in points]
    sampled, truncated = _sample_rows(points, max_rows)
    spans = {s['span']: s for s in data['spans']}

    out = [f'# {heading}', '']
    desc = getattr(series, 'description', '')
    if desc:
        out += [desc, '']

    out += ['## What this shows', '',
            f'- **Series**: `{series_name}` ({display})',
            f'- **Unit**: {unit}',
            f'- **Range**: {points[0]["year"]:.1f} to '
            f'{points[-1]["year"]:.1f} (calendar years CE; '
            f'negative is BCE)',
            f'- **Points**: {len(points)}',
            f'- **Values**: {min(values):.2f} to {max(values):.2f} '
            f'{unit}',
            f'- **Exported**: {_now()}', '']

    if data['isSplice']:
        kinds = ', '.join(k for k in data['measurementKinds'] if k)
        out += ['> **This curve is a splice.** It combines '
                f'{len(data["spans"])} sources of different kinds '
                f'({kinds}). They are not interchangeable: the '
                'table below states each one\'s resolution, and a '
                'rate computed across the seam is not a rate '
                'either source measured.', '']

    out += ['## Where the data comes from', '',
            '| Covers | Source | How measured | Resolution | '
            'Typical uncertainty |',
            '| --- | --- | --- | --- | --- |']
    for span in data['spans']:
        res = span.get('resolutionYears', 0.0) or 0.0
        out.append(
            f'| {span.get("fromYear", 0):.0f} to '
            f'{span.get("toYear", 0):.0f} '
            f'| {_md_escape(span.get("displayName"))} '
            f'| {_md_escape(span.get("measurementKind"))}'
            f'{" - " + _md_escape(span.get("instrument")) if span.get("instrument") else ""} '
            f'| {res:.1f} yr '
            f'| {span.get("typicalUncertainty", 0.0)} {unit} |')
    out.append('')

    out += ['## The data', '']
    if truncated:
        out += [f'*Sampled evenly to {len(sampled)} of '
                f'{len(points)} points so the table stays '
                f'readable. The full series is available as CSV '
                f'and JSON; nothing has been smoothed.*', '']
    out += [f'| Year (CE) | {display} ({unit}) | +/- | Source |',
            '| --- | --- | --- | --- |']
    for point in sampled:
        span = spans.get(point.get('span', ''), {})
        out.append(
            f'| {point["year"]:.1f} | {point["value"]:.2f} '
            f'| {point.get("uncertainty", 0.0):.2f} '
            f'| {_md_escape(span.get("measurementKind", ""))} |')
    out.append('')

    out += ['## Citations', '']
    for span in data['spans']:
        cite = span.get('citation') or '(citation missing)'
        url = span.get('url')
        out.append(f'- {_md_escape(cite)}'
                   + (f' — {url}' if url else ''))
    out += ['',
            '---', '',
            '*Every number above was fetched from the cited source '
            'and carries the coverage span that produced it. '
            'Values are reproduced as published; no smoothing, '
            'gap-filling or interpolation has been applied.*', '']

    if graph_config:
        out += ['<!-- graph config (for re-rendering):',
                json.dumps(graph_config, indent=2), '-->', '']

    return {'ok': True, 'series': series_name, 'format': 'markdown',
            'filename': f'{series_name}-{_now()}.md',
            'contentType': 'text/markdown',
            'content': '\n'.join(out), 'rowCount': len(points),
            'sampled': truncated, 'spans': data['spans'],
            'isSplice': data['isSplice']}


def export_svg(manager, series_name, **kwargs):
    """REFUSED, and the refusal is the honest answer.

    The charts are rendered by Observable Plot in the browser;
    there is no server-side renderer, and hand-rolling a second
    plotter here would produce a picture that DISAGREES with the
    one on screen while claiming to be the same graph. Two
    renderers is two truths.
    """
    return {'ok': False, 'series': series_name,
            'refusal': ('server-side SVG export is not implemented, '
                        'and a second plotting implementation would '
                        'disagree with the on-screen chart. The '
                        'chart is already an SVG in the DOM: '
                        'serialize THAT (XMLSerializer on the '
                        'graph-renderer output) so the exported '
                        'image is the image the reader saw.'),
            'suggestion': {
                'where': 'polari-platform-angular graph-renderer',
                'how': ('new XMLSerializer().serializeToString(svg) '
                        '-> Blob -> download'),
                'why': 'one renderer, one truth'}}


def export_series(manager, series_name, fmt='markdown', **kwargs):
    """Dispatch. An unknown format REFUSES by name rather than
    defaulting - a caller who asked for PDF and silently received
    markdown has been lied to."""
    if fmt == 'markdown':
        return export_markdown(manager, series_name, **kwargs)
    if fmt == 'csv':
        return export_csv(manager, series_name, **kwargs)
    if fmt == 'json':
        return export_json(manager, series_name, **kwargs)
    if fmt == 'svg':
        return export_svg(manager, series_name, **kwargs)
    return {'ok': False,
            'refusal': (f'unknown export format {fmt!r}; available: '
                        f'{", ".join(EXPORT_FORMATS)} (svg refuses '
                        f'with an explanation)')}


def export_view_markdown(manager, view_name='view-co2-health'):
    """The whole study page as one Markdown document.

    Sections that REFUSED are exported as refusals, verbatim. A
    published document that quietly omits the parts that did not
    work is the most dishonest artifact this project could ship -
    the refusals are what tell a reader where the evidence runs
    out.
    """
    from climate.climate_views import view_payload
    payload = view_payload(manager, view_name)
    if not payload.get('ok'):
        return payload

    out = [f'# {payload.get("displayName", view_name)}', '',
           f'*Exported {_now()} from a Polari climate study. '
           f'Every figure below is computed from ingested source '
           f'data, not from prose.*', '']
    for section in payload.get('sections', []):
        out += [f'## {section.get("section", "")}', '']
        lead = section.get('lead', '')
        if lead:
            out += [lead, '']
        if section.get('ok') is False or 'refusal' in section:
            out += [f'> **Not answered.** '
                    f'{section.get("refusal", "")}', '']
            continue
        body = section.get('payload') or {}
        head = body.get('headline') or []
        if head:
            out += ['| What | Value | What it means |',
                    '| --- | --- | --- |']
            for row in head:
                out.append(f'| {_md_escape(row.get("label"))} '
                           f'| {_md_escape(row.get("value"))} '
                           f'| {_md_escape(row.get("note"))} |')
            out.append('')
        for key in ('framing', 'note', 'question'):
            if body.get(key):
                out += [f'{body[key]}', '']
    out += ['---', '',
            '*Sections that could not be answered are printed as '
            'refusals rather than omitted.*', '']
    return {'ok': True, 'view': view_name, 'format': 'markdown',
            'filename': f'{view_name}-{_now()}.md',
            'contentType': 'text/markdown',
            'content': '\n'.join(out)}
