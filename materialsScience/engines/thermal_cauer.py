"""
@cross-cutting
@module materialsScience.engines.thermal_cauer

tmp-3 (AI-Notes/plans/TEMPERATURE_PLAN.md): a datasheet's FOSTER network turned into the CAUER ladder with the same
junction-to-reference impedance - the form whose nodes can be wired into another thermal model (thermal_rc says why the
Foster form cannot; Infineon AN2008-03 "Thermal equivalent circuit models", Nexperia AN11261 "Using RC Thermal models").

    Foster   Z(s) = sum_i R_i / (1 + s tau_i)                    (parallel RC pairs in series)
    Cauer    Y(s) = 1 / Z(s) = s C_1 + 1 / (R_1 + 1 / (s C_2 + 1 / (R_2 + ...)))
             C_1 at the junction, R_1 to the next node, C_2 there, ... R_n to the reference; every C to thermal ground

The ladder is the CONTINUED-FRACTION (Cauer I) expansion of Y(s) about s = infinity - the textbook network synthesis step
(Cauer 1926; e.g. Van Valkenburg, "Introduction to Modern Network Synthesis", ch. 5). Done here in EXACT rational
arithmetic (every float is a rational number, fractions.Fraction holds it exactly), so the usual ill-conditioning of the
polynomial expansion does not arise; only the final R_k, C_k are rounded to floats.

What it is and is not (said, never hidden): the ladder has the same Zth(t) as the datasheet's Foster pairs when its far end
is held at the reference - checked by cauer_zth (an independent eigen-solution of the ladder) - and its steady Rth is the
same sum. Its node temperatures are a mathematical equivalent, not measured places in the part; wired onto a different
board than the datasheet's own it is the standard approximation (AN2008-03), better than the Foster form, which delivers
the whole power into the board at once.

    foster_to_cauer(stages) -> ([[R_k K/W, C_k J/K], ...], why)   junction first; zero-R stages dropped
    cauer_zth(ladder, t)    -> K/W   the ladder's step response with its far end held at 0 (numpy eigen-solution)
"""
from fractions import Fraction


def _poly_mul(a, b):
    out = [Fraction(0)] * (len(a) + len(b) - 1)
    for i, x in enumerate(a):
        for j, y in enumerate(b):
            out[i + j] += x * y
    return out


def _poly_add(a, b):
    n = max(len(a), len(b))
    return [(a[i] if i < len(a) else 0) + (b[i] if i < len(b) else 0) for i in range(n)]


def _trim(p):
    while len(p) > 1 and p[-1] == 0:
        p = p[:-1]
    return p


def _deg(p):
    p = _trim(p)
    return -1 if len(p) == 1 and p[0] == 0 else len(p) - 1


def foster_to_cauer(stages):
    """Polynomials low order first. Z = N / D with D = prod(1 + s tau_i), N = sum_i R_i prod_{j != i}(1 + s tau_j)."""
    pairs = [(Fraction(float(r)), Fraction(float(t))) for r, t in stages if float(r) > 0]
    if not pairs:
        return [], 'no stage with R > 0'
    if len({t for _, t in pairs}) < len(pairs):
        return [], 'two stages share one tau: merge them (their R add) - the expansion needs distinct time constants'
    den = [Fraction(1)]
    for _, t in pairs:
        den = _poly_mul(den, [Fraction(1), t])
    num = [Fraction(0)]
    for i, (r, _) in enumerate(pairs):
        term = [r]
        for j, (_, t) in enumerate(pairs):
            if j != i:
                term = _poly_mul(term, [Fraction(1), t])
        num = _poly_add(num, term)
    # Y = den / num: deg den = n, deg num = n - 1. Alternate: C = lead(Y) / s, then R = lead(Z) of the remainder's inverse.
    a, b = _trim(den), _trim(num)          # current admittance a / b
    ladder = []
    while _deg(b) >= 0 and _deg(a) >= 0:
        if _deg(a) != _deg(b) + 1:
            return [], 'the expansion broke at stage %d (degrees %d / %d) - not a positive-real Foster network' % (len(ladder) + 1, _deg(a), _deg(b))
        c = a[-1] / b[-1]                  # s C
        a = _trim(_poly_add(a, [-x for x in _poly_mul([Fraction(0), c], b)]))
        if _deg(a) < 0:
            return [], 'the expansion ended on a capacitor (no resistance to the reference)'
        r = b[-1] / a[-1] if _deg(b) == _deg(a) else None
        if r is None:
            return [], 'the expansion broke at stage %d (degrees %d / %d)' % (len(ladder) + 1, _deg(b), _deg(a))
        b = _trim(_poly_add(b, [-r * x for x in a]))
        if c <= 0 or r <= 0:
            return [], 'stage %d came out non-positive (C %s, R %s) - not a passive ladder' % (len(ladder) + 1, float(c), float(r))
        ladder.append([float(r), float(c)])   # the remainder's admittance is a / b again (b = 0: the last R reached the reference)
    if len(ladder) != len(pairs):
        return [], 'the expansion gave %d stages for %d Foster pairs' % (len(ladder), len(pairs))
    return ladder, ''


def ladder_matrices(ladder):
    """(C diagonal, G) of the ladder's nodes, junction first, far end held at 0."""
    import numpy as np
    n = len(ladder)
    g = np.zeros((n, n))
    for k, (r, _) in enumerate(ladder):
        g[k, k] += 1.0 / r
        if k + 1 < n:
            g[k + 1, k + 1] += 1.0 / r
            g[k, k + 1] -= 1.0 / r
            g[k + 1, k] -= 1.0 / r
    return np.array([c for _, c in ladder]), g


def cauer_zth(ladder, t):
    """Junction rise per watt t s after a step of power, the far end at 0: C dT/dt = -G T + e_1, solved by the symmetric eigenproblem."""
    import numpy as np
    c, g = ladder_matrices(ladder)
    s = 1.0 / np.sqrt(c)
    lam, v = np.linalg.eigh(s[:, None] * g * s[None, :])   # C^-1/2 G C^-1/2, symmetric positive definite
    e1 = np.zeros(len(c))
    e1[0] = 1.0
    w = v.T @ (s * e1)                                       # modal weights
    return float(s[0] * np.sum(v[0, :] * w * (1.0 - np.exp(-lam * t)) / lam))
