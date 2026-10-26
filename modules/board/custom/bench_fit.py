"""
@module board.custom.bench_fit

wb-0: does a dev board's header footprint fit a breadboard? Pure. A breadboard's trough is 3 pitches wide with 5 tie points on each side; a two-row board
with row spacing S pitches straddles it when 3 <= S <= 11, leaving floor((13 - S) / 2) free holes per side; its length fits when pins_per_row <= rows.
A footprint that says it is not on a continuous 0.1" grid (straddles False: shield headers) sits BESIDE the breadboard. Any -1 / None input -> 'unverified'.
Rail bands do not change the trough, so a rail-less mini is judged the same way.
"""
TROUGH = 3
SIDE = 5


def breadboard_fit(footprint, breadboard):
    """-> {verdict: straddles|beside|too-wide|too-long|unverified, free_holes_per_side: int or -1, why: str}"""
    fp, bb = footprint or {}, breadboard or {}

    def out(v, free, why):
        return {'verdict': v, 'free_holes_per_side': free, 'why': why}
    if fp.get('straddles') is False:
        return out('beside', -1, fp.get('basis') or 'not on a continuous 0.1 in grid: sits beside the breadboard')
    rows, s, n, brows = fp.get('rows', -1), fp.get('row_spacing_pitches', -1), fp.get('pins_per_row', -1), bb.get('rows', -1)
    if rows in (-1, None) or s in (-1, None) or n in (-1, None) or brows in (-1, None):
        return out('unverified', -1, 'unverified: footprint (rows %s, spacing %s, pins per row %s) or breadboard rows (%s) not determined' % (rows, s, n, brows))
    if rows != 2:
        return out('unverified', -1, 'a %s-row board has no trough rule here' % rows)
    if s < TROUGH:
        return out('beside', -1, 'row spacing %d pitches is narrower than the %d-pitch trough: cannot straddle' % (s, TROUGH))
    if s > 11:
        return out('too-wide', -1, 'row spacing %d pitches is outside 3..11 (trough %d + %d tie points each side)' % (s, TROUGH, SIDE))
    if n > brows:
        return out('too-long', -1, '%d pins per row but the breadboard has %d rows' % (n, brows))
    free = (13 - s) // 2
    return out('straddles', free, 'spacing %d pitches over the trough: %d free holes per side; %d pins per row in %d rows' % (s, free, n, brows))
