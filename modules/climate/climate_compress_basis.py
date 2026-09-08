"""
@cross-cutting
@module climate.climate_compress_basis
@tags @xc:bindings

Dustin 2026-08-05: the ice-core composite is 1901 points — too much
to store locally when the page needs the FLOW of time, not every
sample. Compress by binned averaging, and RECORD HOW — the record is
the honesty:

  - bins never cross a SourceCoverageSpan (averaging across
    instruments would launder a splice into a smooth line);
  - a compressed point is an AGGREGATE and says so: sample_count
    carries the bin population, uncertainty is widened to at least
    the bin's spread (compression must not make data look more
    certain), and the row's notes name its bin;
  - the original points remain RECOVERABLE: the ingest endpoint
    re-fetches from the archive, and the record names it;
  - a SeriesCompressionRecord row stores method, bin width, before/
    after counts, and the per-span breakdown — a later reader can
    know exactly what happened to the data and undo it.

Never auto-applied: compression is a knob (POST
/api/climate/compress/{series}); the series detail SUGGESTS it for
oversized series with the evidence (point count), house style.
"""
# sap-2c INDEX (design §7): the classes live one-per-file under objects/climate_compress/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

import json
from types import SimpleNamespace
from objectTreeDecorators import treeObject, treeObjectInit

from climate.objects.climate_compress._shared import DEFAULT_TARGET_POINTS, DEVIATION_EXPAND_FACTOR, MIN_POINTS_TO_COMPRESS, _mean, _median, _rows, _stdev, compression_suggestion  # noqa: F401
from climate.objects.climate_compress.SeriesCompressionRecord import SeriesCompressionRecord  # noqa: F401

from types import SimpleNamespace
import json

def compress_series(manager, series_name,
                    target_points=DEFAULT_TARGET_POINTS,
                    expand_factor=DEVIATION_EXPAND_FACTOR):
    """Bin-mean the series toward target_points, per span. Returns
    the record; refuses when compression would gain nothing."""
    from climate.climate_basis import AtmosphericObservation
    from climate.custom.series_ingest import _drop_observations

    obs = [o for o in _rows(manager, 'AtmosphericObservation')
           if getattr(o, 'series_ref', '') == series_name]
    if not obs:
        return {'ok': False,
                'error': f"series '{series_name}' has no points"}
    if len(obs) <= max(MIN_POINTS_TO_COMPRESS, target_points):
        return {'ok': False,
                'refusal': f'{len(obs)} points is already ≤ the '
                           f'compression floor '
                           f'(max({MIN_POINTS_TO_COMPRESS}, '
                           f'{target_points})) — compressing would '
                           f'churn data for no gain'}
    try:
        target = max(20, int(target_points))
    except (TypeError, ValueError):
        return {'ok': False, 'error': 'target_points not a number'}

    # group by span — bins NEVER cross instruments.
    by_span = {}
    for o in obs:
        by_span.setdefault(getattr(o, 'span_ref', ''), []).append(o)
    total = len(obs)
    years_all = [float(getattr(o, 'year', 0.0)) for o in obs]
    span_reports, new_rows = [], []
    for span, pts in sorted(by_span.items(),
                            key=lambda kv: len(kv[1]),
                            reverse=True):
        pts.sort(key=lambda o: float(getattr(o, 'year', 0.0)))
        share = max(5, int(round(target * len(pts) / total)))
        if len(pts) <= share:
            span_reports.append({'span': span, 'points': len(pts),
                                 'kept': True})
            continue
        y0 = float(getattr(pts[0], 'year', 0.0))
        y1 = float(getattr(pts[-1], 'year', 0.0))
        width = (y1 - y0) / share if y1 > y0 else 1.0
        bins = {}
        for o in pts:
            i = min(share - 1,
                    int((float(getattr(o, 'year', 0.0)) - y0)
                        / width)) if width else 0
            bins.setdefault(i, []).append(o)
        # -- pass 1: every bin's swing; the NORM is the median swing
        # of this span's bins (an anomaly must not set its own norm).
        swings = {}
        for i, group in bins.items():
            vals = [float(getattr(o, 'value', 0.0)) for o in group]
            m = _mean(vals)
            swings[i] = (max(vals) - m, m - min(vals))
        norm = _median([max(u, d) for u, d in swings.values()])
        expanded_bins = []
        # -- pass 2: emit — averaged bins carry their max deviation
        # up/down; bins swinging beyond expand_factor × norm keep
        # their RAW points (the expanded view of anomalous years).
        for i, group in sorted(bins.items()):
            yrs = [float(getattr(o, 'year', 0.0)) for o in group]
            vals = [float(getattr(o, 'value', 0.0)) for o in group]
            dev_up, dev_down = swings[i]
            if (norm > 0 and len(group) > 1
                    and max(dev_up, dev_down)
                    > expand_factor * norm):
                # SIGNIFICANT DEVIATION: keep the raw points.
                for o in group:
                    rd = {f: getattr(o, f, '') for f in
                          ('name', 'series_ref', 'span_ref', 'year',
                           'value', 'uncertainty', 'sample_count',
                           'retrieval_ref', 'provenance_id')}
                    rd.update({
                        'revision': 'expanded',
                        'deviation_up': 0.0, 'deviation_down': 0.0,
                        'is_prior': False,
                        'notes': f'KEPT RAW: this bin swung '
                                 f'+{dev_up:.3f}/−{dev_down:.3f} vs '
                                 f'a norm of {norm:.3f} '
                                 f'(>{expand_factor}×) — anomalous '
                                 f'years are shown expanded, never '
                                 f'averaged away'})
                    new_rows.append(rd)
                expanded_bins.append({
                    'yearFrom': round(min(yrs), 1),
                    'yearTo': round(max(yrs), 1),
                    'points': len(group),
                    'devUp': round(dev_up, 4),
                    'devDown': round(dev_down, 4),
                    'norm': round(norm, 4)})
                continue
            uncs = [float(getattr(o, 'uncertainty', 0.0) or 0.0)
                    for o in group]
            counts = [int(getattr(o, 'sample_count', 0) or 1)
                      for o in group]
            new_rows.append({
                'name': f'{series_name}--{span}-b{i}',
                'series_ref': series_name, 'span_ref': span,
                'year': round(_mean(yrs), 4),
                'value': round(_mean(vals), 6),
                # widened, never narrowed: at least the bin's spread.
                'uncertainty': round(max(_mean(uncs),
                                         _stdev(vals)), 6),
                'sample_count': sum(counts),
                'revision': 'compressed',
                # the swing the average absorbed — notated, per bin.
                'deviation_up': round(dev_up, 4),
                'deviation_down': round(dev_down, 4),
                'retrieval_ref': getattr(group[0], 'retrieval_ref',
                                         ''),
                'is_prior': False,
                'provenance_id': 'climate-compress',
                'notes': f'bin-mean of {len(group)} points '
                         f'{min(yrs):.1f}..{max(yrs):.1f}; max dev '
                         f'+{dev_up:.3f}/−{dev_down:.3f} '
                         f'(see SeriesCompressionRecord '
                         f'{series_name}--compression)'})
        span_reports.append({'span': span, 'points': len(pts),
                             'kept': False, 'bins': len(bins),
                             'binWidthYears': round(width, 3),
                             'deviationNorm': round(norm, 4),
                             'expandedBins': expanded_bins})
        _drop_observations(manager, series_name, span)

    db = getattr(manager, 'db', None)
    obs_table = manager.objectTables.setdefault(
        'AtmosphericObservation', {})
    for rd in new_rows:
        row = None
        try:
            row = AtmosphericObservation(**rd, manager=manager)
        except Exception:
            row = None
        if row is None or rd['name'] not in {
                getattr(o, 'name', None) for o in obs_table.values()}:
            row = SimpleNamespace(**rd)
            obs_table[rd['name']] = row
        if db is not None:
            try:
                db.saveInstanceInDB(row)
            except Exception:
                pass

    kept = sum(r['points'] for r in span_reports if r.get('kept'))
    all_devs_up = [b['devUp'] for r in span_reports
                   for b in r.get('expandedBins', [])] \
        + [rd.get('deviation_up', 0.0) for rd in new_rows]
    all_devs_down = [b['devDown'] for r in span_reports
                     for b in r.get('expandedBins', [])] \
        + [rd.get('deviation_down', 0.0) for rd in new_rows]
    record_fields = {
        'name': f'{series_name}--compression',
        'series_ref': series_name,
        'method': 'per-span equal-width-year bin-mean; uncertainty '
                  '= max(mean uncertainty, bin stdev); sample_count '
                  '= bin population',
        'target_points': target, 'original_points': total,
        'compressed_points': len(new_rows) + kept,
        'bin_width_years': round(
            max((r.get('binWidthYears', 0.0)
                 for r in span_reports), default=0.0), 3),
        'first_year': round(min(years_all), 2),
        'last_year': round(max(years_all), 2),
        'max_deviation_up': round(max(all_devs_up, default=0.0), 4),
        'max_deviation_down': round(max(all_devs_down,
                                        default=0.0), 4),
        'deviation_norm': round(max(
            (r.get('deviationNorm', 0.0) for r in span_reports),
            default=0.0), 4),
        'expanded_bin_count': sum(
            len(r.get('expandedBins', [])) for r in span_reports),
        'spans_json': json.dumps(span_reports),
        'reingest_note': f'originals recoverable: POST '
                         f'/api/climate/ingest/{series_name} '
                         f're-fetches from the archive, then '
                         f're-compress if wanted',
        'is_prior': False,
        'provenance_id': 'climate-compress',
        'notes': 'compression is lossy ON PURPOSE (local storage '
                 'frugality, Dustin 2026-08-05); this record is the '
                 'audit trail'}
    table = manager.objectTables.setdefault(
        'SeriesCompressionRecord', {})
    existing = next((r for r in table.values()
                     if getattr(r, 'name', '')
                     == record_fields['name']), None)
    if existing is not None:
        for k, v in record_fields.items():
            setattr(existing, k, v)
        if db is not None:
            try:
                db.saveInstanceInDB(existing)
            except Exception:
                pass
    else:
        rec = None
        try:
            rec = SeriesCompressionRecord(**record_fields,
                                          manager=manager)
        except Exception:
            rec = None
        if rec is None or record_fields['name'] not in {
                getattr(r, 'name', None) for r in table.values()}:
            rec = SimpleNamespace(**record_fields)
            table[record_fields['name']] = rec
        if db is not None:
            try:
                db.saveInstanceInDB(rec)
            except Exception:
                pass

    return {'ok': True, 'series': series_name,
            'originalPoints': total,
            'compressedPoints': record_fields['compressed_points'],
            'spans': span_reports,
            'record': record_fields['name'],
            'reingest': record_fields['reingest_note'],
            'note': 'bins never cross spans; uncertainty widened to '
                    'the bin spread; the record row is the audit '
                    'trail'}
