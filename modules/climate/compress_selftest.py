"""
Selftest — climate series compression (Dustin 2026-08-05).

Run from polari-framework/:
    python3 -m climate.compress_selftest

Covers: bin-mean compression honors span boundaries, widens
uncertainty to the bin spread, carries bin population in
sample_count, writes the audit record with the re-ingest path,
refuses small series, and the suggestion is evidence-bearing.
"""

from types import SimpleNamespace

from climate.climate_compress_basis import (
    MIN_POINTS_TO_COMPRESS, compress_series, compression_suggestion,
)

PASS, FAIL = '\033[0;32mPASS\033[0m', '\033[0;31mFAIL\033[0m'
_results = []


def check(label, cond, extra=''):
    _results.append(bool(cond))
    print(f'  [{PASS if cond else FAIL}] {label}'
          f'{("  " + extra) if extra else ""}')


def _obs(i, series, span, year, value, unc=0.5):
    return SimpleNamespace(name=f'{series}-p{i}', series_ref=series,
                           span_ref=span, year=year, value=value,
                           uncertainty=unc, sample_count=1,
                           retrieval_ref='ret-1')


if __name__ == '__main__':
    # two spans: an 800-point ancient span and a 67-point modern one
    # — mirrors the real ice-core + instrumental shape.
    S = 'test-ice'
    rows = {}
    for i in range(800):
        o = _obs(i, S, 'span-ancient', -800000 + i * 1000.0,
                 200.0 + (i % 40))
        rows[o.name] = o
    for i in range(67):
        o = _obs(800 + i, S, 'span-modern', 1959.0 + i,
                 315.0 + i * 1.7)
        rows[o.name] = o
    manager = SimpleNamespace(objectTables={
        'AtmosphericObservation': rows,
        'SeriesCompressionRecord': {}})

    r = compress_series(manager, S, target_points=200)
    check('compression ran', r.get('ok'), r.get('error', ''))
    check('867 → ~target points', 150 <= r.get('compressedPoints', 0)
          <= 260, f"{r.get('compressedPoints')}")
    left = [o for o in manager.objectTables[
        'AtmosphericObservation'].values()
        if getattr(o, 'series_ref', '') == S]
    spans = {getattr(o, 'span_ref', '') for o in left}
    check('bins never crossed spans (both spans survive distinctly)',
          spans == {'span-ancient', 'span-modern'})
    # the small modern span keeps proportional share; check counts
    modern = [o for o in left
              if getattr(o, 'span_ref', '') == 'span-modern']
    check('small span not over-crushed (proportional share ≥ 5)',
          len(modern) >= 5)
    binned = [o for o in left
              if getattr(o, 'revision', '') == 'compressed']
    check('compressed points carry bin population + widened '
          'uncertainty + a naming note',
          binned and all(getattr(o, 'sample_count', 0) > 1
                         and getattr(o, 'uncertainty', 0) >= 0.5
                         and 'bin-mean of' in getattr(o, 'notes', '')
                         for o in binned[:10]))
    rec = manager.objectTables['SeriesCompressionRecord'].get(
        f'{S}--compression')
    check('audit record: method + counts + per-span + re-ingest '
          'path', rec is not None
          and 'bin-mean' in getattr(rec, 'method', '')
          and getattr(rec, 'original_points', 0) == 867
          and 'ingest' in getattr(rec, 'reingest_note', ''))
    check('record is NOT a prior (a record of an act)',
          getattr(rec, 'is_prior', True) is False)
    small = SimpleNamespace(objectTables={
        'AtmosphericObservation': {
            f'p{i}': _obs(i, 'small', 'sp', 2000 + i, 1.0)
            for i in range(50)},
        'SeriesCompressionRecord': {}})
    check('small series REFUSES (churn for no gain)',
          'refusal' in compress_series(small, 'small'))
    check('suggestion only appears past the floor, with evidence',
          compression_suggestion(100, 's') is None
          and 'evidence' in (compression_suggestion(
              MIN_POINTS_TO_COMPRESS + 1, 's') or {}))
    check('empty series refuses',
          not compress_series(small, 'nope').get('ok'))

    # -- deviation expansion: an 800-point stable record with ONE
    # anomalous modern era (the industrial-CO2 shape) — the anomaly
    # must come through RAW, not averaged away.
    import math
    S2 = 'test-anomaly'
    rows2 = {}
    for i in range(760):
        yr = -760000 + i * 1000.0
        # glacial-cycle-smooth: 100k-year sine, like the real record
        o = _obs(i, S2, 'span-core', yr,
                 230.0 + 40.0 * math.sin(2 * math.pi * yr / 100000.0))
        rows2[o.name] = o
    for i in range(40):                              # the spike era
        o = _obs(900 + i, S2, 'span-core', -200.0 + i * 5.0,
                 280.0 + i * 3.5)                    # 280 → 416
        rows2[o.name] = o
    m2 = SimpleNamespace(objectTables={
        'AtmosphericObservation': rows2,
        'SeriesCompressionRecord': {}})
    r2 = compress_series(m2, S2, target_points=100)
    rec2 = m2.objectTables['SeriesCompressionRecord'][
        f'{S2}--compression']
    left2 = [o for o in m2.objectTables['AtmosphericObservation'
                                        ].values()
             if getattr(o, 'series_ref', '') == S2]
    expanded = [o for o in left2
                if getattr(o, 'revision', '') == 'expanded']
    check('ONLY the anomalous modern era is EXPANDED (its bin keeps '
          'raw points; the glacial cycles compress)', r2.get('ok')
          and getattr(rec2, 'expanded_bin_count', 0) == 1
          and 40 <= len(expanded) <= 60
          and all(getattr(o, 'year', -1e9) > -10000
                  for o in expanded),
          f'expandedBins={getattr(rec2, "expanded_bin_count", 0)} '
          f'rawKept={len(expanded)}')
    check('expanded rows SAY why (swing vs norm, in the notes)',
          expanded and 'KEPT RAW' in getattr(expanded[0], 'notes',
                                             '')
          and 'norm' in getattr(expanded[0], 'notes', ''))
    binned2 = [o for o in left2
               if getattr(o, 'revision', '') == 'compressed']
    check('averaged bins NOTATE their max deviation up/down',
          binned2 and all(hasattr(o, 'deviation_up')
                          and hasattr(o, 'deviation_down')
                          for o in binned2[:10]))
    check('the record carries the overall max ± deviation and the '
          'norm it was judged against',
          getattr(rec2, 'max_deviation_up', 0) > 50
          and getattr(rec2, 'deviation_norm', 0) > 0
          and getattr(rec2, 'max_deviation_up', 0)
          > 10 * getattr(rec2, 'deviation_norm', 1))

    failed = _results.count(False)

    failed = _results.count(False)
    print(f'\n{len(_results) - failed}/{len(_results)} passed')
    raise SystemExit(1 if failed else 0)
