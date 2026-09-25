"""
@module mathproofs.custom.terms

THE TERM LANGUAGE (plan §I.4) — JSON terms over the rows that exist, never free strings a checker must parse.
One spec, several tiers lower it; what a tier cannot lower it REFUSES by name (`unprovable-here`), never a fake pass.

Terms (v0):
    <number>                                  a literal
    {"ref": "<Class>:<name>" | "<var>", "path": ["<field>", "<key>", …]}   READ a row's field (json-decoded when it
                                              parses) and walk into it by keys/indexes; a bound var reads its row
    {"sum"|"max"|"min"|"count": {"over": "rows:<Class>[:<field>=<value> | :<field>~<substring>]", "path": [...]}}
    {"eq": [a, b], "tol": {"rel": r, "abs": a}}   (defaults rel 1e-9, abs 0)
    {"add"|"mul": [a, b, …]}                  arithmetic on numeric terms
    {"le"|"lt"|"ge"|"gt": [a, b]}
    {"and"|"or": [t, …]}   {"not": t}   {"implies": [t, t]}
    {"forall": [{"var": "x", "in": <set>}], "holds": t}      <set> = "rows:<Class>[:<field>=<value>]" (finite: the
                                              rows themselves, `x` binds the row so {"ref": "x.<field>"} reads it)
                                              | "validity:<TensorMapping>" | "domain:<TensorNode>" (intervals per dim)
    {"subset": [<set>, <set>]}                interval sets: every dim's range of the first inside the second's
    {"dims_subset": ["<TensorMapping>.source_dims", "<TensorNode>.dims" | "<TensorMapping>.target_dims"]}
    {"symbolic": {"template": "symmetry-of-contraction" | "linear-composition" | "restriction-idempotent",
                  "args": {...}}}             discharged by the sympy tier (custom/symbolic.py) — the template names
                                              WHAT is proved; the args name the rows

`canonical(term)` → a stable JSON string; `statement_hash(term)` → sha256 of it (the bridge to a .lean certificate).
`to_latex(term)` → a reading for people, derived, never authored separately.
"""
import hashlib
import json

SET_PREFIXES = ('rows:', 'validity:', 'domain:')
MODIFIERS = ('tol', 'path', 'holds')


def op_of(t):
    """The operator key of a term dict (the one key that is not a modifier), or None."""
    keys = [k for k in t if k not in MODIFIERS]
    return keys[0] if len(keys) == 1 else None


def canonical(term):
    return json.dumps(term, sort_keys=True, separators=(',', ':'), ensure_ascii=False)


def statement_hash(term):
    return hashlib.sha256(canonical(term).encode('utf-8')).hexdigest()


def _lat(t):
    if isinstance(t, (int, float)):
        return ('%g' % t)
    if isinstance(t, str):
        return r'\mathrm{%s}' % t.replace('_', r'\_')
    if not isinstance(t, dict) or not op_of(t):
        return '?'
    k = op_of(t)
    v = t[k]
    if k == 'ref':
        return r'\mathrm{%s}' % ('.'.join([str(v)] + [str(x) for x in (t.get('path') or [])])).replace('_', r'\_')
    if k in ('sum', 'max', 'min', 'count'):
        return r'\%s_{%s} %s' % (k if k != 'count' else 'operatorname{count}', str(v.get('over', '')).replace('_', r'\_'), '.'.join(str(x) for x in (v.get('path') or [])).replace('_', r'\_'))
    if k == 'eq':
        tol = t.get('tol') or {}
        return '%s = %s%s' % (_lat(v[0]), _lat(v[1]), (r'\ (\pm %g\,\mathrm{rel})' % tol['rel']) if tol.get('rel') else '')
    if k in ('add', 'mul'):
        return (' + ' if k == 'add' else r' \cdot ').join('(%s)' % _lat(x) if isinstance(x, dict) and next(iter(x)) in ('add', 'mul') else _lat(x) for x in v)
    if k in ('le', 'lt', 'ge', 'gt'):
        return '%s %s %s' % (_lat(v[0]), {'le': r'\le', 'lt': '<', 'ge': r'\ge', 'gt': '>'}[k], _lat(v[1]))
    if k in ('and', 'or'):
        return (r' \land ' if k == 'and' else r' \lor ').join('(%s)' % _lat(x) for x in v)
    if k == 'not':
        return r'\lnot (%s)' % _lat(v)
    if k == 'implies':
        return '(%s) \\Rightarrow (%s)' % (_lat(v[0]), _lat(v[1]))
    if k == 'forall':
        binders = ', '.join(r'%s \in %s' % (b['var'], str(b['in']).replace('_', r'\_')) for b in v)
        return r'\forall\, %s:\ %s' % (binders, _lat(t.get('holds')))
    if k == 'subset':
        return r'%s \subseteq %s' % (str(v[0]).replace('_', r'\_'), str(v[1]).replace('_', r'\_'))
    if k == 'dims_subset':
        return r'\mathrm{dims}(%s) \subseteq \mathrm{dims}(%s)' % (str(v[0]).replace('_', r'\_'), str(v[1]).replace('_', r'\_'))
    if k == 'symbolic':
        return {'symmetry-of-contraction': r'\sigma_{ij} = C_{ijkl}\varepsilon_{kl},\ C_{ijkl}=C_{jikl}=C_{ijlk},\ \varepsilon_{kl}=\varepsilon_{lk} \Rightarrow \sigma_{ij}=\sigma_{ji}',
                'linear-composition': r'(g \circ f)(\alpha u + \beta v) = \alpha (g\circ f)(u) + \beta (g \circ f)(v)',
                'restriction-idempotent': r'R(R(T)) = R(T)'}.get(v.get('template', ''), r'\mathrm{symbolic}')
    return '?'


def to_latex(term):
    return _lat(term)


def validate(term, path='$'):
    """[] when the term is well-formed, else a list of "path: why" strings (a checker never runs an invalid term)."""
    errs = []
    if isinstance(term, (int, float, str)):
        return errs
    if not isinstance(term, dict) or not op_of(term):
        return ['%s: a term is a number, a string, or an object with one operator key (plus tol/path/holds)' % path]
    k = op_of(term); v = term[k]
    if k == 'ref':
        if not isinstance(v, str) or not isinstance(term.get('path'), list) or not term['path']:
            errs.append('%s.ref: {"ref": "<Class>:<name>" | "<var>", "path": ["<field>", …]}' % path)
    elif k in ('sum', 'max', 'min', 'count'):
        if not isinstance(v, dict) or not str(v.get('over', '')).startswith('rows:') or (k != 'count' and not isinstance(v.get('path'), list)):
            errs.append('%s.%s: {"over": "rows:<Class>[:<f>=<v>]", "path": [...]}' % (path, k))
    elif k in ('add', 'mul'):
        if not isinstance(v, list) or len(v) < 2:
            errs.append('%s.%s: two or more numeric terms' % (path, k))
        else:
            for i, x in enumerate(v):
                errs += validate(x, '%s.%s[%d]' % (path, k, i))
    elif k in ('eq', 'le', 'lt', 'ge', 'gt', 'implies'):
        if not isinstance(v, list) or len(v) != 2:
            errs.append('%s.%s: two operands' % (path, k))
        else:
            for i, x in enumerate(v):
                errs += validate(x, '%s.%s[%d]' % (path, k, i))
    elif k in ('and', 'or'):
        if not isinstance(v, list) or not v:
            errs.append('%s.%s: a list of terms' % (path, k))
        else:
            for i, x in enumerate(v):
                errs += validate(x, '%s.%s[%d]' % (path, k, i))
    elif k == 'not':
        errs += validate(v, path + '.not')
    elif k == 'forall':
        if not isinstance(v, list) or not all(isinstance(b, dict) and b.get('var') and str(b.get('in', '')).startswith(SET_PREFIXES) for b in v):
            errs.append('%s.forall: [{"var": name, "in": "rows:…|validity:…|domain:…"}]' % path)
        if 'holds' not in term:
            errs.append('%s.forall: needs "holds"' % path)
        else:
            errs += validate(term['holds'], path + '.holds')
    elif k == 'subset':
        if not (isinstance(v, list) and len(v) == 2 and all(str(x).startswith(('validity:', 'domain:', 'scope:')) for x in v)):
            errs.append('%s.subset: two interval sets (validity:<mapping> | domain:<node> | scope:<claim>)' % path)
    elif k == 'dims_subset':
        if not (isinstance(v, list) and len(v) == 2):
            errs.append('%s.dims_subset: two dim sets' % path)
    elif k == 'symbolic':
        if not isinstance(v, dict) or v.get('template') not in ('symmetry-of-contraction', 'linear-composition', 'restriction-idempotent'):
            errs.append('%s.symbolic: a known template' % path)
    else:
        errs.append('%s: unknown operator %r' % (path, k))
    return errs
