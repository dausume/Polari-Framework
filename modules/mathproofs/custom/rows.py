"""
@module mathproofs.custom.rows

Reading ROWS for the checkers: refs, finite row sets, interval sets (a mapping's validity, a node's dims' ranges),
dim sets — and the rows-state hash a ProofRun records so a changed row makes the run STALE.
"""
import hashlib
import json


def _rows(manager, cls):
    return list((getattr(manager, 'objectTables', {}) or {}).get(cls, {}).values())


def by_name(manager, cls, name):
    return next((r for r in _rows(manager, cls) if str(getattr(r, 'name', '')) == str(name)), None)


def _j(s, d):
    try:
        v = json.loads(s)
        return v if v is not None else d
    except Exception:
        return d


def read_field(manager, spec, path, env=None):
    """spec = '<Class>:<name>' or a bound var; path = [field, key, index, …] walked into the (json-decoded) value."""
    if env and str(spec) in env:
        row = env[str(spec)]
    else:
        cls, _, name = str(spec).partition(':')
        row = by_name(manager, cls, name)
        if row is None:
            raise KeyError('ref %r: no %s named %r' % (spec, cls, name))
    if not path:
        raise KeyError('ref %r: empty path' % spec)
    field = str(path[0])
    if not hasattr(row, field):
        raise KeyError('ref %r: row has no field %r' % (spec, field))
    v = getattr(row, field)
    if isinstance(v, str):
        try:
            v = json.loads(v)
        except Exception:
            pass
    for key in path[1:]:
        try:
            v = v[key] if not (isinstance(v, list) and isinstance(key, str)) else v[int(key)]
        except Exception:
            raise KeyError('ref %r: no %r under %s' % (spec, key, path))
    return v


def row_set(manager, spec):
    """'rows:<Class>[:<field>=<value>]' → the rows."""
    parts = str(spec).split(':', 2)
    if len(parts) < 2 or parts[0] != 'rows':
        raise KeyError('not a row set: %r' % spec)
    rows = _rows(manager, parts[1])
    if len(parts) == 3:
        if '=' in parts[2]:   # exact
            f, _, val = parts[2].partition('=')
            rows = [r for r in rows if str(getattr(r, f, '')) == val]
        elif '~' in parts[2]:   # substring
            f, _, val = parts[2].partition('~')
            rows = [r for r in rows if val in str(getattr(r, f, ''))]
    return rows


def interval_set(manager, spec):
    """'validity:<mapping>' | 'domain:<node>' | 'scope:<claim>' → {dim: [lo, hi]} (a node's domain = its LocalizedDimensions'
    ranges; empty ranges are unbounded and omitted)."""
    kind, _, name = str(spec).partition(':')
    if kind == 'validity':
        m = by_name(manager, 'TensorMapping', name)
        if m is None:
            raise KeyError('no TensorMapping %r' % name)
        return {k: v for k, v in _j(getattr(m, 'validity_json', '{}'), {}).items() if isinstance(v, list) and len(v) == 2}
    if kind == 'scope':
        c = by_name(manager, 'MathClaim', name)
        if c is None:
            raise KeyError('no MathClaim %r' % name)
        return {k: v for k, v in _j(getattr(c, 'scope_json', '{}'), {}).items() if isinstance(v, list) and len(v) == 2}
    if kind == 'domain':
        n = by_name(manager, 'TensorNode', name)
        if n is None:
            raise KeyError('no TensorNode %r' % name)
        dims = {str(getattr(d, 'name', '')): d for d in _rows(manager, 'LocalizedDimension')}
        out = {}
        for dn in _j(getattr(n, 'dims_json', '[]'), []):
            d = dims.get(dn)
            if d is None:
                continue
            rng = _j(getattr(d, 'range_json', '[]'), [])
            sc = _j(getattr(d, 'scale_json', '{}'), {})
            r = rng if (isinstance(rng, list) and len(rng) == 2) else (sc.get('domain') if isinstance(sc.get('domain'), list) and len(sc.get('domain')) == 2 else None)
            if r:
                out[str(dn).split('.')[-1]] = [float(r[0]), float(r[1])]
        return out
    raise KeyError('not an interval set: %r' % spec)


def dim_set(manager, spec):
    """'<TensorMapping>.source_dims' | '<TensorMapping>.target_dims' | '<TensorNode>.dims' → set of short dim names."""
    name, _, what = str(spec).rpartition('.')
    if what in ('source_dims', 'target_dims'):
        m = by_name(manager, 'TensorMapping', name)
        if m is None:
            raise KeyError('no TensorMapping %r' % name)
        return {str(x) for x in _j(getattr(m, what + '_json', '[]'), [])}
    if what == 'dims':
        n = by_name(manager, 'TensorNode', name)
        if n is None:
            raise KeyError('no TensorNode %r' % name)
        return {str(x).split('.')[-1] for x in _j(getattr(n, 'dims_json', '[]'), [])}
    raise KeyError('not a dim set: %r' % spec)


def rows_state_hash(manager, about_refs):
    """sha256 over the named rows' public fields, so a ProofRun knows what it ran against."""
    h = hashlib.sha256()
    for ref in sorted(str(r) for r in about_refs):
        cls, _, name = ref.partition(':')
        row = by_name(manager, cls, name)
        if row is None:
            h.update(('MISSING %s' % ref).encode()); continue
        fields = {k: v for k, v in vars(row).items() if not k.startswith('_') and isinstance(v, (str, int, float, bool))}
        h.update(json.dumps({ref: fields}, sort_keys=True, default=str).encode())
    return h.hexdigest()
