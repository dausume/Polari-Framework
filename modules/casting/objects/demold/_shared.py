"""@module casting.objects.demold._shared — what the demold row classes share (constants, seeds, helpers); split from demold_basis.py (sap-2c)."""

DEMOLD_METHODS = ('mechanical', 'melt-out', 'burn-out', 'break-out')
_AXES = {'x': 0, 'y': 1, 'z': 2}
def _column_key(cell, axis_i):
    return tuple(v for i, v in enumerate(cell) if i != axis_i)
def _one_piece_sweep(cavity, clear, axis, sign):
    """Columns whose cavity cells can slide to the boundary along
    (axis, sign) through clear cells. Returns (blocked, total)."""
    ai = _AXES[axis]
    n = cavity.n
    cols = {}
    for c in cavity.inside:
        cols.setdefault(_column_key(c, ai), []).append(c[ai])
    blocked = 0
    for key, ks in cols.items():
        edge = max(ks) if sign > 0 else min(ks)
        path = range(edge + 1, n) if sign > 0 else range(edge - 1,
                                                        -1, -1)
        ok = True
        for k in path:
            cell = list(key)
            cell.insert(ai, k)
            if tuple(cell) not in clear:
                ok = False
                break
        if not ok:
            blocked += 1
    return blocked, len(cols)
def _two_part_plane(cavity, axis):
    """Smallest-undercut parting plane along `axis`: at plane k_p the
    upper half pulls +axis iff every column's cavity cells in
    [k_p, n) are contiguous from k_p; mirrored below. Returns the
    first feasible k_p (searching from the cavity's widest slice
    outward) or None."""
    ai = _AXES[axis]
    ks = sorted({c[ai] for c in cavity.inside})
    if not ks:
        return None

    def _half_ok(k_p, upper):
        cols = {}
        for c in cavity.inside:
            if (c[ai] >= k_p) if upper else (c[ai] < k_p):
                cols.setdefault(_column_key(c, ai), []).append(c[ai])
        for key, kk in cols.items():
            kk = sorted(kk)
            contiguous = kk[-1] - kk[0] + 1 == len(kk)
            touches = (kk[0] == k_p) if upper else (kk[-1] == k_p - 1)
            if not (contiguous and touches):
                return False
        return True

    # widest slice first — the physically-natural parting line.
    by_width = sorted(ks, key=lambda k: -sum(
        1 for c in cavity.inside if c[ai] == k))
    for k in by_width:
        for k_p in (k, k + 1):
            if _half_ok(k_p, True) and _half_ok(k_p, False):
                return k_p
    return None
