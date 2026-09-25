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
    {"given": <premise>, "holds": t}           three-valued: when the premise does not hold the verdict is UNDETERMINED
                                              (the statement is not defined here — never refuted, never vacuously true)
    {"recorded": {"ref": …, "path": […]}}     the value is present and not the empty/None placeholder ('' / None);
                                              a numeric 0 IS a value — pair it with a method field to mean "recorded"
    {"forall"|"exists": [{"var": "x", "in": <set>}], "holds": t}
                                              <set> = "rows:<Class>[:<field>=<value>]" (finite: the rows themselves,
                                              `x` binds the row so {"ref": "x", "path": ["<field>"]} reads it — the
                                              numeric tier walks it) | "validity:<TensorMapping>" | "domain:<TensorNode>"
                                              | "scope:<MathClaim>" (a CONTINUUM: intervals per dim — the z3 tier decides
                                              it; {"ref": "x", "path": ["<dim>"]} is the bound point's coordinate)
    {"in": ["<var>", <set>]}                  the bound point lies inside that interval set (on the dims both constrain)
    {"subset": [<set>, <set>]}                interval sets: every dim's range of the first inside the second's
    {"bitvector": {"template": "mac-no-overflow", "args": {"products", "operand_bits", "acc_bits", "a_abs_max", "b_abs_max"}}}
                                              a kernel's fixed-point contract decided over machine integers (z3 tier);
                                              the bounds are numeric terms — read from rows, never typed twice
    {"dims_subset": ["<TensorMapping>.source_dims", "<TensorNode>.dims" | "<TensorMapping>.target_dims"]}
    {"symbolic": {"template": "symmetry-of-contraction" | "linear-composition" | "restriction-idempotent"
                              | "chain-domains-compose", "args": {...}}}
                                              discharged by the sympy tier (custom/symbolic.py) at a FIXED size, or by
                                              the lean tier (custom/lean_tier.py) in general — {"n": "any"} / {"links":
                                              "any"} name the general statement, which only a committed theorem proves;
                                              the template names WHAT is proved; the args name the rows / the size

`canonical(term)` → a stable JSON string; `statement_hash(term)` → sha256 of it (the bridge to a .lean certificate).
`to_latex(term)` → a reading for people, derived, never authored separately.
"""
import hashlib
import json

SET_PREFIXES = ('rows:', 'validity:', 'domain:', 'scope:')
BITVECTOR_TEMPLATES = ('mac-no-overflow',)
SYMBOLIC_TEMPLATES = ('symmetry-of-contraction', 'linear-composition', 'restriction-idempotent', 'chain-domains-compose')
MODIFIERS = ('tol', 'path', 'holds')


def op_of(t):
    """The operator key of a term dict (the one key that is not a modifier), or None."""
    keys = [k for k in t if k not in MODIFIERS]
    return keys[0] if len(keys) == 1 else None


def canonical(term):
    return json.dumps(term, sort_keys=True, separators=(',', ':'), ensure_ascii=False)


def statement_hash(term):
    return hashlib.sha256(canonical(term).encode('utf-8')).hexdigest()


def _txt(name):
    """A row / set / dim name as TEXT in the LaTeX (never math italics: hyphens stay hyphens, spaces stay, → stays)."""
    s = str(name)
    for a, b in (('\\', r'\textbackslash{}'), ('{', r'\{'), ('}', r'\}'), ('_', r'\_'), ('#', r'\#'), ('%', r'\%'), ('&', r'\&')):
        s = s.replace(a, b)
    # a math symbol inside a name (wind-grid→slice-z0, eps→sigma) leaves text mode for that symbol only: KaTeX has no
    # \rightarrow in \text{}, so the name becomes \text{wind-grid}\rightarrow\text{slice-z0}
    for a, b in (('→', r'}\rightarrow\text{'), ('σ', r'}\sigma\text{'), ('ε', r'}\varepsilon\text{'), ('⊆', r'}\subseteq\text{')):
        s = s.replace(a, b)
    return (r'\text{%s}' % s).replace(r'\text{}', '')


def _lat(t):
    if isinstance(t, (int, float)):
        return ('%g' % t)
    if isinstance(t, str):
        return _txt(t)
    if not isinstance(t, dict) or not op_of(t):
        return '?'
    k = op_of(t)
    v = t[k]
    if k == 'ref':
        return _txt('.'.join([str(v)] + [str(x) for x in (t.get('path') or [])]))
    if k in ('sum', 'max', 'min', 'count'):
        return r'\%s_{%s} %s' % (k if k != 'count' else 'operatorname{count}', _txt(v.get('over', '')), _txt('.'.join(str(x) for x in (v.get('path') or []))))
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
    if k == 'given':
        return r'\left[%s\right] \Rightarrow %s\ (\text{else undetermined})' % (_lat(v), _lat(t.get('holds')))
    if k == 'recorded':
        return r'\mathrm{recorded}(%s)' % _lat(v)
    if k in ('forall', 'exists'):
        binders = ', '.join(r'%s \in %s' % (b['var'], _txt(b['in'])) for b in v)
        return r'\%s\, %s:\ %s' % (k, binders, _lat(t.get('holds')))
    if k == 'in':
        return r'%s \in %s' % (str(v[0]), _txt(v[1]))
    if k == 'bitvector':
        a = v.get('args') or {}
        return r'\forall\, |a_i| \le %s,\ |b_i| \le %s:\ \left|\sum_{i=1}^{%s} a_i b_i\right| < 2^{%s}\ (\text{int}%s\ \text{operands})' % (
            _lat(a.get('a_abs_max', '?')), _lat(a.get('b_abs_max', '?')), a.get('products', '?'), int(a.get('acc_bits', 64)) - 1, a.get('operand_bits', '?'))
    if k == 'subset':
        return r'%s \subseteq %s' % (_txt(v[0]), _txt(v[1]))
    if k == 'dims_subset':
        return r'\mathrm{dims}(%s) \subseteq \mathrm{dims}(%s)' % (_txt(v[0]), _txt(v[1]))
    if k == 'symbolic':
        return {'symmetry-of-contraction': r'\sigma_{ij} = C_{ijkl}\varepsilon_{kl},\ C_{ijkl}=C_{jikl}=C_{ijlk},\ \varepsilon_{kl}=\varepsilon_{lk} \Rightarrow \sigma_{ij}=\sigma_{ji}',
                'linear-composition': r'(g \circ f)(\alpha u + \beta v) = \alpha (g\circ f)(u) + \beta (g \circ f)(v)',
                'restriction-idempotent': r'R(R(T)) = R(T)',
                'chain-domains-compose': r'\forall i:\ V_{i+1} \subseteq V_i\ \Rightarrow\ \bigcap_{i \le n} V_i = V_n'}.get(v.get('template', ''), r'\mathrm{symbolic}') + (r'\quad(\forall n)' if 'any' in str((v.get('args') or {}).values()) else '')
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
    elif k == 'given':
        errs += validate(v, path + '.given')
        if 'holds' not in term:
            errs.append('%s.given: needs "holds"' % path)
        else:
            errs += validate(term['holds'], path + '.holds')
    elif k == 'recorded':
        if not isinstance(v, dict) or 'ref' not in v:
            errs.append('%s.recorded: {"ref": …, "path": […]}' % path)
    elif k in ('forall', 'exists'):
        if not isinstance(v, list) or not v or not all(isinstance(b, dict) and b.get('var') and str(b.get('in', '')).startswith(SET_PREFIXES) for b in v):
            errs.append('%s.%s: [{"var": name, "in": "rows:…|validity:…|domain:…|scope:…"}]' % (path, k))
        if 'holds' not in term:
            errs.append('%s.%s: needs "holds"' % (path, k))
        else:
            errs += validate(term['holds'], path + '.holds')
    elif k == 'in':
        if not (isinstance(v, list) and len(v) == 2 and isinstance(v[0], str) and str(v[1]).startswith(('validity:', 'domain:', 'scope:'))):
            errs.append('%s.in: ["<var>", "validity:…|domain:…|scope:…"]' % path)
    elif k == 'bitvector':
        a = v.get('args') if isinstance(v, dict) else None
        if not isinstance(v, dict) or v.get('template') not in BITVECTOR_TEMPLATES or not isinstance(a, dict) or not all(x in a for x in ('products', 'operand_bits', 'acc_bits', 'a_abs_max', 'b_abs_max')):
            errs.append('%s.bitvector: {"template": "mac-no-overflow", "args": {products, operand_bits, acc_bits, a_abs_max, b_abs_max}}' % path)
        else:
            for x in ('a_abs_max', 'b_abs_max'):
                errs += validate(a[x], '%s.bitvector.args.%s' % (path, x))
    elif k == 'subset':
        if not (isinstance(v, list) and len(v) == 2 and all(str(x).startswith(('validity:', 'domain:', 'scope:')) for x in v)):
            errs.append('%s.subset: two interval sets (validity:<mapping> | domain:<node> | scope:<claim>)' % path)
    elif k == 'dims_subset':
        if not (isinstance(v, list) and len(v) == 2):
            errs.append('%s.dims_subset: two dim sets' % path)
    elif k == 'symbolic':
        if not isinstance(v, dict) or v.get('template') not in SYMBOLIC_TEMPLATES:
            errs.append('%s.symbolic: a known template (%s)' % (path, ', '.join(SYMBOLIC_TEMPLATES)))
    else:
        errs.append('%s: unknown operator %r' % (path, k))
    return errs
