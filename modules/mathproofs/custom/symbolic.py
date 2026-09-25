"""
@module mathproofs.custom.symbolic

TIER 2 — SYMBOLIC (SymPy, already a suite dependency): identities over SYMBOLS, so a claim holds for every value,
not just the rows we have — `checked-symbolically`, evidence `analytical`. Three templates in v0; each names WHAT is
proved, takes its dimensions/operands from the claim's args, and returns the simplified residual (0 = holds) or
the first non-zero component as the counterexample-shaped detail.

    symmetry-of-contraction   σ_ij = C_ijkl ε_kl with C minor-symmetric and ε symmetric ⇒ σ symmetric (any dim n)
    linear-composition        g∘f is linear when f, g are linear maps given as matrices (or when both are
                              contractions with fixed tensors) — in v0: matrices A (f) and B (g) over symbols
    restriction-idempotent    R(R(T)) = R(T) for an index-range restriction R (a slice: keep indices in a range)

Anything else → unprovable-here (a template is added, never a free expression parsed from a string).
"""
import itertools


def _sympy():
    import sympy
    return sympy


def symmetry_of_contraction(n=2):
    sp = _sympy()
    # C with minor symmetries C_ijkl = C_jikl = C_ijlk: build from free symbols on the symmetric index pairs
    pairs = [(i, j) for i in range(n) for j in range(i, n)]
    C = {}
    for (i, j) in pairs:
        for (k, l) in pairs:
            s = sp.Symbol('C_%d%d%d%d' % (i, j, k, l))
            for a, b in ((i, j), (j, i)):
                for c, d in ((k, l), (l, k)):
                    C[(a, b, c, d)] = s
    E = {}
    for (k, l) in pairs:
        s = sp.Symbol('e_%d%d' % (k, l)); E[(k, l)] = s; E[(l, k)] = s
    sigma = {(i, j): sum(C[(i, j, k, l)] * E[(k, l)] for k in range(n) for l in range(n)) for i in range(n) for j in range(n)}
    residuals = {(i, j): sp.simplify(sigma[(i, j)] - sigma[(j, i)]) for i in range(n) for j in range(i + 1, n)}
    bad = {k: str(v) for k, v in residuals.items() if v != 0}
    return {'holds': not bad, 'detail': {'n': n, 'free_symbols': len(set(C.values())) + len(set(E.values())), 'residuals': {'%d%d' % k: str(v) for k, v in residuals.items()}}, 'counterexample': bad or None}


def linear_composition(rows_f=2, cols_f=2, rows_g=2):
    sp = _sympy()
    A = sp.Matrix(rows_f, cols_f, lambda i, j: sp.Symbol('a_%d%d' % (i, j)))
    B = sp.Matrix(rows_g, rows_f, lambda i, j: sp.Symbol('b_%d%d' % (i, j)))
    u = sp.Matrix(cols_f, 1, lambda i, _: sp.Symbol('u_%d' % i)); v = sp.Matrix(cols_f, 1, lambda i, _: sp.Symbol('v_%d' % i))
    al, be = sp.symbols('alpha beta')
    lhs = B * (A * (al * u + be * v)); rhs = al * (B * (A * u)) + be * (B * (A * v))
    res = (lhs - rhs).applyfunc(sp.simplify)
    bad = [str(x) for x in res if x != 0]
    return {'holds': not bad, 'detail': {'shape_f': [rows_f, cols_f], 'shape_g': [rows_g, rows_f], 'residual': str(list(res))}, 'counterexample': ({'nonzero': bad} if bad else None)}


def restriction_idempotent(size=4, keep=(0, 2)):
    sp = _sympy()
    T = [sp.Symbol('t_%d' % i) for i in range(size)]
    lo, hi = keep
    def R(x):
        return [x[i] if lo <= i < hi else sp.Integer(0) for i in range(size)]
    once, twice = R(T), R(R(T))
    bad = [str(a - b) for a, b in zip(once, twice) if sp.simplify(a - b) != 0]
    return {'holds': not bad, 'detail': {'size': size, 'keep': list(keep), 'once': [str(x) for x in once]}, 'counterexample': ({'nonzero': bad} if bad else None)}


TEMPLATES = {'symmetry-of-contraction': symmetry_of_contraction, 'linear-composition': linear_composition, 'restriction-idempotent': restriction_idempotent}


def evaluate(term):
    """{'verdict': holds | refuted | unprovable-here | error, 'tier': 'sympy', 'detail', 'counterexample'}"""
    if not (isinstance(term, dict) and 'symbolic' in term):
        return {'verdict': 'unprovable-here', 'tier': 'sympy', 'detail': {'why': 'not a symbolic template (v0 proves templates, never free strings)'}, 'counterexample': None}
    spec = term['symbolic']; name = spec.get('template'); args = spec.get('args') or {}
    fn = TEMPLATES.get(name)
    if fn is None:
        return {'verdict': 'unprovable-here', 'tier': 'sympy', 'detail': {'why': 'no template %r' % name}, 'counterexample': None}
    try:
        r = fn(**{k: (tuple(v) if isinstance(v, list) else v) for k, v in args.items()})
    except Exception as exc:
        return {'verdict': 'error', 'tier': 'sympy', 'detail': {'why': '%s: %s' % (type(exc).__name__, exc)}, 'counterexample': None}
    return {'verdict': 'holds' if r['holds'] else 'refuted', 'tier': 'sympy', 'detail': dict(r['detail'], template=name), 'counterexample': r['counterexample']}
