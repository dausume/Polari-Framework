"""
@module mathproofs.custom.numeric

TIERS 0 and 1 — the NUMERIC WITNESS (a term evaluated over the rows we have: never a theorem; evidence `measured`
on that data) and the INTERVAL DECISION (`subset` / `dims_subset` / `forall` over an interval set: exact set
arithmetic, a genuine decision — `decided`, evidence `analytical`).

`evaluate(manager, term)` → {'verdict': holds | refuted | unprovable-here, 'tier': numeric | interval,
'detail': {...}, 'counterexample': {...} | None}. A finite `forall` (rows:…) is checked row by row and the first
failing row IS the counterexample. A `forall` over an interval set is only decidable here when `holds` is itself
a `subset`/`in`-shaped statement; anything needing real arithmetic over a continuum → unprovable-here (that is the
z3 tier, pf-1).
"""
import json

from mathproofs.custom.rows import read_field, row_set, interval_set, dim_set


class Unprovable(Exception):
    pass


class Undetermined(Exception):
    """The statement is not defined here: a premise (`given`) does not hold or a value it needs is not recorded."""


MODIFIERS = ('tol', 'path', 'holds')


def _op(t):
    """The operator key of a term (the one key that is not a modifier)."""
    keys = [k for k in t if k not in MODIFIERS]
    return keys[0] if len(keys) == 1 else None


def _num(manager, t, env):
    if isinstance(t, (int, float)) and not isinstance(t, bool):
        return float(t)
    if isinstance(t, dict) and _op(t):
        k = _op(t); v = t[k]
        if k == 'ref':
            x = read_field(manager, v, t.get('path') or [], env)
            if isinstance(x, bool) or not isinstance(x, (int, float)):
                raise Unprovable('ref %s is not a number (%s)' % (v, type(x).__name__))
            return float(x)
        if k in ('add', 'mul'):
            vals = [_num(manager, x, env) for x in v]
            out = 0.0 if k == 'add' else 1.0
            for x in vals:
                out = out + x if k == 'add' else out * x
            return out
        if k in ('sum', 'max', 'min', 'count'):
            rows = row_set(manager, v['over'])
            if k == 'count':
                return float(len(rows))
            vals = []
            for r in rows:
                try:
                    x = read_field(manager, 'r', v.get('path') or [], {'r': r})
                except KeyError:
                    continue
                if isinstance(x, (int, float)) and not isinstance(x, bool):
                    vals.append(float(x))
            if not vals:
                raise Unprovable('%s over %s.%s: no numeric values' % (k, v['over'], v['field']))
            return {'sum': sum, 'max': max, 'min': min}[k](vals)
    raise Unprovable('not a numeric term: %r' % (t,))


def _bool(manager, t, env):
    """(holds: bool, detail, counterexample)"""
    if not isinstance(t, dict) or not _op(t):
        raise Unprovable('not a statement: %r' % (t,))
    k = _op(t); v = t[k]
    if k == 'eq':
        a, b = _num(manager, v[0], env), _num(manager, v[1], env)
        tol = t.get('tol') or {}
        rel, ab = float(tol.get('rel', 1e-9)), float(tol.get('abs', 0.0))
        ok = abs(a - b) <= max(ab, rel * max(abs(a), abs(b)))
        return ok, {'lhs': a, 'rhs': b, 'tol_rel': rel, 'tol_abs': ab}, None if ok else {'lhs': a, 'rhs': b}
    if k in ('le', 'lt', 'ge', 'gt'):
        a, b = _num(manager, v[0], env), _num(manager, v[1], env)
        ok = {'le': a <= b, 'lt': a < b, 'ge': a >= b, 'gt': a > b}[k]
        return ok, {'lhs': a, 'rhs': b, 'op': k}, None if ok else {'lhs': a, 'rhs': b}
    if k == 'and':
        details = []
        for x in v:
            ok, d, ce = _bool(manager, x, env); details.append(d)
            if not ok:
                return False, {'and': details}, ce
        return True, {'and': details}, None
    if k == 'or':
        details = []; last = None
        for x in v:
            ok, d, ce = _bool(manager, x, env); details.append(d); last = ce
            if ok:
                return True, {'or': details}, None
        return False, {'or': details}, last
    if k == 'not':
        ok, d, _ = _bool(manager, v, env)
        return (not ok), {'not': d}, ({'held': d} if ok else None)
    if k == 'implies':
        ok_a, da, _ = _bool(manager, v[0], env)
        if not ok_a:
            return True, {'antecedent': da, 'vacuous': True}, None
        ok_b, db, ce = _bool(manager, v[1], env)
        return ok_b, {'antecedent': da, 'consequent': db}, ce
    if k == 'recorded':
        try:
            x = read_field(manager, v['ref'], v.get('path') or [], env)
        except KeyError as exc:
            return False, {'recorded': False, 'why': str(exc)}, {'unrecorded': v}
        ok = x is not None and x != '' and x != [] and x != {}
        return ok, {'recorded': ok, 'value': x if isinstance(x, (int, float, str, bool)) else type(x).__name__}, (None if ok else {'unrecorded': v})
    if k == 'given':
        ok_p, dp, _ = _bool(manager, v, env)
        if not ok_p:
            raise Undetermined('premise does not hold: %s' % json.dumps(dp, default=str)[:200])
        ok, d, ce = _bool(manager, t['holds'], env)
        return ok, {'given': dp, 'holds': d}, ce
    if k == 'subset':
        a, b = interval_set(manager, v[0]), interval_set(manager, v[1])
        bad = {}
        for dim, (lo, hi) in a.items():
            if dim in b and not (b[dim][0] <= lo and hi <= b[dim][1]):
                bad[dim] = {'inner': [lo, hi], 'outer': b[dim]}
        return (not bad), {'inner': a, 'outer': b, 'checked_dims': sorted(set(a) & set(b)), 'unconstrained_in_outer': sorted(set(a) - set(b))}, (bad or None)
    if k == 'dims_subset':
        a, b = dim_set(manager, v[0]), dim_set(manager, v[1])
        missing = sorted(a - b)
        return (not missing), {'inner': sorted(a), 'outer': sorted(b)}, ({'missing': missing} if missing else None)
    if k == 'forall':
        binders = v; holds = t['holds']
        if len(binders) != 1:
            raise Unprovable('one binder at a time in v0')
        var, dom = binders[0]['var'], binders[0]['in']
        if str(dom).startswith('rows:'):
            rows = row_set(manager, dom)
            if not rows:
                raise Unprovable('forall over %s: no rows — vacuous, not a witness' % dom)
            for r in rows:
                ok, d, ce = _bool(manager, holds, dict(env or {}, **{var: r}))
                if not ok:
                    return False, {'over': dom, 'rows': len(rows), 'failed_at': str(getattr(r, 'name', '?'))}, {'row': str(getattr(r, 'name', '?')), **(ce or {})}
            return True, {'over': dom, 'rows': len(rows)}, None
        raise Unprovable('forall over %s needs real arithmetic (the z3 tier)' % dom)
    if k == 'symbolic':
        raise Unprovable('a symbolic template (the sympy tier)')
    raise Unprovable('unknown statement %r' % k)


def evaluate(manager, term):
    tier = 'interval' if (isinstance(term, dict) and _op(term) in ('subset', 'dims_subset')) else 'numeric'
    try:
        ok, detail, ce = _bool(manager, term, {})
    except Undetermined as exc:
        return {'verdict': 'undetermined', 'tier': tier, 'detail': {'why': str(exc)}, 'counterexample': None}
    except Unprovable as exc:
        return {'verdict': 'unprovable-here', 'tier': tier, 'detail': {'why': str(exc)}, 'counterexample': None}
    except KeyError as exc:
        return {'verdict': 'error', 'tier': tier, 'detail': {'why': str(exc)}, 'counterexample': None}
    return {'verdict': 'holds' if ok else 'refuted', 'tier': tier, 'detail': detail, 'counterexample': ce}
