"""
@module mathproofs.custom.z3tier

TIER 2 — THE DECISION PROCEDURE (Z3 through `z3-solver`, MIT; a python library, in-process — not an engine). The
same term language, lowered to real arithmetic and to machine integers, and DECIDED: a quantified statement over a
CONTINUUM is checked by asking for a MODEL OF ITS NEGATION — none (unsat) → `decided`; one (sat) → `refuted`, and
the model IS the counterexample (a real point inside the domain where the statement fails); no answer within the
claim's `budget_s` → `undecided (budget)`: the absence of a decision is never a counterexample (D-pf-9).

Lowered here (anything else → unprovable-here, naming the operator):
    forall / exists  over an interval set (`validity:<mapping>` | `domain:<node>` | `scope:<claim>`): one real per dim
                     the set constrains, the box as constraints; `holds` over reals — eq (an abs tolerance → |a−b| ≤ tol),
                     le/lt/ge/gt, and/or/not/implies, add/mul, literals, refs to row fields (constants, read exactly as
                     the numeric tier reads them), {"ref": "<var>", "path": ["<dim>"]} = the bound point's coordinate,
                     {"in": ["<var>", <set>]} = the point lies inside that set's box on the dims both constrain
    subset [A, B]    as ∀x∈A: x∈B — the interval tier's decision re-derived by a second, independent procedure
    given / holds    the premise is a fact about rows (the numeric tier reads it); false → undetermined
    bitvector        {"bitvector": {"template": "mac-no-overflow", "args": {…}}} — a kernel's fixed-point contract:
                     `products` signed products of `operand_bits`-bit operands with |a| ≤ a_abs_max, |b| ≤ b_abs_max (numeric
                     terms — read from rows, never typed twice), accumulated one at a time in `acc_bits`: no prefix sum
                     leaves the signed range. The operands are exact integers, so the default encoding is unbounded
                     integers with the ranges as constraints (QF_NIA, sub-second); `encoding: "bv"` asks for the machine
                     words with z3's overflow predicates instead (bit-blasted; ~19 s measured — beyond the default budget,
                     which is the honest reading of that encoding). The model = the operands + the prefix sums
A closed statement over row values (no binder) is NOT decided here: it is the numeric tier's witness on those rows,
and calling it `decided` would dress data up as a theorem.
"""
import math

from mathproofs.custom import numeric
from mathproofs.custom.rows import interval_set
from mathproofs.custom.terms import op_of

CONTINUUM = ('validity:', 'domain:', 'scope:')
BITVECTOR_TEMPLATES = ('mac-no-overflow',)


class Unlowerable(Exception):
    pass


def _z3():
    import z3
    return z3


def version():
    try:
        return 'z3 %s' % _z3().get_version_string()
    except Exception:
        return 'z3 absent'


def _res(verdict, detail, ce=None):
    return {'verdict': verdict, 'tier': 'z3', 'detail': detail, 'counterexample': ce}


def _const(manager, t):
    """A closed numeric term → float, exactly as the numeric tier reads it (rows, sums, arithmetic)."""
    try:
        return numeric._num(manager, t, {})
    except numeric.Unprovable as exc:
        raise Unlowerable(str(exc))


def _val(v):
    """A model value → a python number (rationals exactly, algebraic numbers to 12 digits, bitvectors signed)."""
    z3 = _z3()
    if z3.is_bv_value(v):
        return v.as_signed_long()
    if z3.is_int_value(v):
        return v.as_long()
    fr = v.as_fraction() if z3.is_rational_value(v) else v.approx(12).as_fraction()
    return float(fr) if fr.denominator != 1 else int(fr.numerator)


def _num(manager, z3, t, env):
    if isinstance(t, (int, float)) and not isinstance(t, bool):
        return z3.RealVal(str(t))
    if not (isinstance(t, dict) and op_of(t)):
        raise Unlowerable('not a numeric term: %r' % (t,))
    k = op_of(t); v = t[k]
    if k == 'ref' and str(v) in env:
        path = t.get('path') or []
        if len(path) != 1 or str(path[0]) not in env[str(v)]:
            raise Unlowerable('%s.%s: the set the variable ranges over does not constrain that dim (it has %s)' % (v, '.'.join(str(p) for p in path), sorted(env[str(v)])))
        return env[str(v)][str(path[0])]
    if k in ('ref', 'sum', 'max', 'min', 'count'):
        return z3.RealVal(str(_const(manager, t)))
    if k in ('add', 'mul'):
        parts = [_num(manager, z3, x, env) for x in v]
        out = parts[0]
        for x in parts[1:]:
            out = out + x if k == 'add' else out * x
        return out
    raise Unlowerable('not a numeric term for z3: %r' % k)


def _bool(manager, z3, t, env, sets):
    if not (isinstance(t, dict) and op_of(t)):
        raise Unlowerable('not a statement: %r' % (t,))
    k = op_of(t); v = t[k]
    if k == 'eq':
        a, b = _num(manager, z3, v[0], env), _num(manager, z3, v[1], env)
        tol = t.get('tol') or {}
        if float(tol.get('rel', 0) or 0) > 0:
            raise Unlowerable('eq with a RELATIVE tolerance over a continuum — state an absolute one')
        ab = float(tol.get('abs', 0) or 0)
        return z3.And(a - b <= ab, b - a <= ab) if ab > 0 else (a == b)
    if k in ('le', 'lt', 'ge', 'gt'):
        a, b = _num(manager, z3, v[0], env), _num(manager, z3, v[1], env)
        return {'le': a <= b, 'lt': a < b, 'ge': a >= b, 'gt': a > b}[k]
    if k == 'and':
        return z3.And(*[_bool(manager, z3, x, env, sets) for x in v])
    if k == 'or':
        return z3.Or(*[_bool(manager, z3, x, env, sets) for x in v])
    if k == 'not':
        return z3.Not(_bool(manager, z3, v, env, sets))
    if k == 'implies':
        return z3.Implies(_bool(manager, z3, v[0], env, sets), _bool(manager, z3, v[1], env, sets))
    if k == 'in':
        var, spec = str(v[0]), str(v[1])
        if var not in env:
            raise Unlowerable('in: %r is not a bound variable' % var)
        box = interval_set(manager, spec)
        sets.setdefault('in', {})[spec] = box
        shared = sorted(set(box) & set(env[var]))
        sets.setdefault('shared_dims', {})[spec] = shared
        return z3.And(*[z3.And(env[var][d] >= box[d][0], env[var][d] <= box[d][1]) for d in shared]) if shared else z3.BoolVal(True)
    if k in ('recorded', 'given'):
        # facts about rows, not about the point: the numeric tier reads them (a failing premise → undetermined)
        ok, d, _ = numeric._bool(manager, t if k == 'recorded' else v, {})
        if k == 'recorded':
            return z3.BoolVal(bool(ok))
        if not ok:
            raise numeric.Undetermined('premise does not hold: %s' % (d,))
        return _bool(manager, z3, t['holds'], env, sets)
    if k in ('forall', 'exists'):
        raise Unlowerable('a nested quantifier (v1 lowers one level)')
    raise Unlowerable('%r is not lowered to z3' % k)


def _quantified(manager, z3, binders, holds, kind, budget_s, _check):
    env = {}; box = []; sets = {'over': {}}
    for b in binders:
        var, spec = str(b['var']), str(b['in'])
        if not spec.startswith(CONTINUUM):
            raise Unlowerable('%s over %s is finite (rows): the numeric tier walks it' % (kind, spec))
        rng = interval_set(manager, spec)
        if not rng:
            raise Unlowerable('%s constrains no dim: nothing to quantify over' % spec)
        env[var] = {d: z3.Real('%s.%s' % (var, d)) for d in rng}
        box += [z3.And(env[var][d] >= lo, env[var][d] <= hi) for d, (lo, hi) in rng.items()]
        sets['over'][var] = {'set': spec, 'box': rng}
    body = _bool(manager, z3, holds, env, sets)
    s = z3.Solver(); s.set('timeout', max(1, int(float(budget_s) * 1000)))
    s.add(*box)
    s.add(z3.Not(body) if kind == 'forall' else body)
    r = (_check or (lambda solver: solver.check()))(s)
    detail = dict(sets, kind=kind, asked='a model of the negation' if kind == 'forall' else 'a witness', budget_s=budget_s)
    if r == z3.unknown:
        return _res('undecided', dict(detail, why='budget: no decision within %s s (%s)' % (budget_s, s.reason_unknown())))
    if kind == 'forall':
        if r == z3.unsat:
            return _res('holds', dict(detail, result='unsat: no point of the box breaks it'))
        m = s.model()
        return _res('refuted', dict(detail, result='sat: a point of the box breaks it'), {'%s.%s' % (var, d): _val(m.eval(x, model_completion=True)) for var, dims in env.items() for d, x in dims.items()})
    if r == z3.sat:
        m = s.model()
        return _res('holds', dict(detail, result='sat', witness={'%s.%s' % (var, d): _val(m.eval(x, model_completion=True)) for var, dims in env.items() for d, x in dims.items()}))
    return _res('refuted', dict(detail, result='unsat: no point of the box satisfies it'), {'no_witness_in': {var: s_['set'] for var, s_ in sets['over'].items()}})


def _mac_no_overflow(manager, z3, args, budget_s, _check):
    """`products` signed products of `operand_bits`-bit operands, accumulated SEQUENTIALLY in `acc_bits`: every prefix sum
    of the accumulator stays inside the signed range (a total that fits is not enough — the kernel adds one product at a
    time). Two encodings: `int` (default) — the operands are exact integers, so unbounded integers with the range as
    constraints lose nothing (QF_NIA; sub-second here); `bv` — the machine words themselves with z3's overflow
    predicates (bit-blasting four 64-bit multipliers: ~19 s measured on pol-core, beyond the default budget)."""
    p = int(args.get('products', 1)); ob = int(args.get('operand_bits', 32)); ab = int(args.get('acc_bits', 64)); enc = str(args.get('encoding', 'int'))
    amax = int(math.floor(_const(manager, args['a_abs_max']))); bmax = int(math.floor(_const(manager, args['b_abs_max'])))
    lim = 2 ** (ob - 1) - 1; M = 2 ** (ab - 1) - 1
    if amax > lim or bmax > lim:
        raise Unlowerable('an operand bound (%d / %d) exceeds the %d-bit signed range (%d)' % (amax, bmax, ob, lim))
    if 2 * ob > ab:
        raise Unlowerable('a %d×%d-bit product does not fit %d bits by width — the per-product overflow is not modelled here' % (ob, ob, ab))
    if enc not in ('int', 'bv'):
        raise Unlowerable('encoding %r (int | bv)' % enc)
    s = z3.Solver() if enc == 'int' else z3.SolverFor('QF_BV'); s.set('timeout', max(1, int(float(budget_s) * 1000)))
    if enc == 'int':
        a = [z3.Int('a%d' % i) for i in range(p)]; b = [z3.Int('b%d' % i) for i in range(p)]
        for i in range(p):
            s.add(a[i] >= -amax, a[i] <= amax, b[i] >= -bmax, b[i] <= bmax)
        acc = 0; bad = []
        for i in range(p):
            acc = acc + a[i] * b[i]
            bad += [acc > M, acc < -M - 1]
        s.add(z3.Or(*bad))
    else:
        a = [z3.BitVec('a%d' % i, ob) for i in range(p)]; b = [z3.BitVec('b%d' % i, ob) for i in range(p)]
        for i in range(p):
            s.add(a[i] >= -amax, a[i] <= amax, b[i] >= -bmax, b[i] <= bmax)
        ext = lambda x: z3.SignExt(ab - ob, x)
        safe = []; acc = None
        for i in range(p):
            prod = ext(a[i]) * ext(b[i])   # fits by width (2·ob ≤ ab, checked above)
            if acc is None:
                acc = prod
            else:
                safe += [z3.BVAddNoOverflow(acc, prod, True), z3.BVAddNoUnderflow(acc, prod)]
                acc = acc + prod
        s.add(z3.Not(z3.And(*safe)) if safe else z3.BoolVal(False))
    r = (_check or (lambda solver: solver.check()))(s)
    analytic = p * amax * bmax
    detail = {'template': 'mac-no-overflow', 'encoding': 'exact integers with the ranges as constraints (QF_NIA)' if enc == 'int' else 'machine words + overflow predicates (QF_BV)', 'products': p, 'operand_bits': ob, 'acc_bits': ab,
              'a_abs_max': amax, 'b_abs_max': bmax, 'budget_s': budget_s, 'checked': 'every prefix sum of the accumulator within [-2^%d, 2^%d-1]; each product fits %d bits by width' % (ab - 1, ab - 1, ab),
              'analytic_bound': {'sum_abs_max': analytic, 'acc_signed_max': M, 'headroom_bits': round(math.log2(M / analytic), 2) if analytic else None}}
    if r == z3.unknown:
        return _res('undecided', dict(detail, why='budget: no decision within %s s (%s)' % (budget_s, s.reason_unknown())))
    if r == z3.unsat:
        return _res('holds', dict(detail, result='unsat: no operands within the bounds overflow the accumulator'))
    m = s.model()
    av = [_val(m.eval(x, model_completion=True)) for x in a]; bv = [_val(m.eval(x, model_completion=True)) for x in b]
    pref = []; acc = 0
    for i in range(p):
        acc += av[i] * bv[i]; pref.append(acc)
    return _res('refuted', dict(detail, result='sat: these operands overflow'), {'a': av, 'b': bv, 'prefix_sums': pref, 'first_overflow_at': next((i for i, x in enumerate(pref) if x > M or x < -M - 1), None)})


def evaluate(manager, term, budget_s=10.0, _check=None):
    """{'verdict': holds | refuted | undecided | undetermined | unprovable-here | error, 'tier': 'z3', 'detail', 'counterexample'}.
    `_check(solver)` is a seam for tests (a forced `unknown` exercises the budget path without a hard instance)."""
    try:
        z3 = _z3()
    except Exception:
        return _res('unprovable-here', {'why': 'z3-solver is not installed (pip: z3-solver, MIT)'})
    if not (isinstance(term, dict) and op_of(term)):
        return _res('unprovable-here', {'why': 'not a statement'})
    try:
        k = op_of(term); v = term[k]
        if k == 'given':
            ok, d, _ = numeric._bool(manager, v, {})
            if not ok:
                return _res('undetermined', {'why': 'premise does not hold: %s' % (d,)})
            term = term['holds']; k = op_of(term); v = term[k]
        if k == 'bitvector':
            if not isinstance(v, dict) or v.get('template') not in BITVECTOR_TEMPLATES:
                raise Unlowerable('bitvector template %r (known: %s)' % ((v or {}).get('template'), ', '.join(BITVECTOR_TEMPLATES)))
            return _mac_no_overflow(manager, z3, v.get('args') or {}, budget_s, _check)
        if k == 'subset':
            return _quantified(manager, z3, [{'var': 'x', 'in': v[0]}], {'in': ['x', v[1]]}, 'forall', budget_s, _check)
        if k in ('forall', 'exists'):
            return _quantified(manager, z3, v, term['holds'], k, budget_s, _check)
        if k == 'symbolic':
            raise Unlowerable('a symbolic template (the sympy tier)')
        raise Unlowerable('a closed statement over row values is the numeric tier\'s witness on those rows, not a decision')
    except numeric.Undetermined as exc:
        return _res('undetermined', {'why': str(exc)})
    except Unlowerable as exc:
        return _res('unprovable-here', {'why': str(exc)})
    except KeyError as exc:
        return _res('error', {'why': str(exc)})
    except Exception as exc:
        return _res('error', {'why': '%s: %s' % (type(exc).__name__, exc)})
