"""@module climate.objects.climate_compress._shared — what the climate_compress row classes share (constants, seeds, helpers); split from climate_compress_basis.py (sap-2c)."""

MIN_POINTS_TO_COMPRESS = 400
DEFAULT_TARGET_POINTS = 250
DEVIATION_EXPAND_FACTOR = 2.0
def _rows(manager, class_name):
    table = (getattr(manager, 'objectTables', None) or {}).get(
        class_name, {})
    return list(table.values()) if isinstance(table, dict) else list(table)
def _mean(vals):
    return sum(vals) / len(vals) if vals else 0.0
def _stdev(vals):
    if len(vals) < 2:
        return 0.0
    m = _mean(vals)
    return (sum((v - m) ** 2 for v in vals) / (len(vals) - 1)) ** 0.5
def _median(vals):
    s = sorted(vals)
    n = len(s)
    if not n:
        return 0.0
    return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2.0
def compression_suggestion(point_count, series_name):
    """The evidence-bearing suggestion the series detail carries for
    oversized series — never auto-applied."""
    if point_count <= MIN_POINTS_TO_COMPRESS:
        return None
    return {'knob': f'POST /api/climate/compress/{series_name}',
            'evidence': f'{point_count} stored points; the page '
                        f'needs the flow of time, not every sample '
                        f'(local storage frugality)',
            'action': f'bin-mean toward ~{DEFAULT_TARGET_POINTS} '
                      f'points with the method recorded'}
