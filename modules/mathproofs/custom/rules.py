"""
@module mathproofs.custom.rules

THE LOGIC BETWEEN THE PARTS OF A TENSORTREE, GENERATED (plan §I.3/I.5): walk a tree's structure, match each
enabled InferenceRule's pattern, and DEMAND a claim for every match — a ProofObligation naming the structure, with
a MathClaim built from the rule's term template (the placeholders {m1} {m2} {node} filled with row names). Idempotent
by name: re-generation refreshes, never duplicates. The cheap tiers are run at once (numeric / interval /
sympy); the obligation's status mirrors its claim.

Patterns (v0):
    chain[:<k1>,<k2>]        every pair (m1 → node → m2): m1.target_node == m2.source_node, optionally of those kinds
    mapping:<kind>[:<op>]    every mapping of that kind, optionally whose expression's operation is <op> (e.g. contract)
    node                     every TensorNode of the tree
Rules that cannot be decided by any tier here still emit their obligation — `unprovable-here`, naming why — so
the gap is a row a person can see, not silence.
"""
import datetime
import json

from mathproofs.custom.rows import _rows, by_name
from mathproofs.custom import checkers, terms


def _j(s, d):
    try:
        v = json.loads(s)
        return v if v is not None else d
    except Exception:
        return d


def tree_structure(manager, tree):
    nodes = [n for n in _rows(manager, 'TensorNode') if str(getattr(n, 'tree', '')) == tree]
    names = {str(getattr(n, 'name', '')) for n in nodes}
    maps = [m for m in _rows(manager, 'TensorMapping') if str(getattr(m, 'source_node', '')) in names or str(getattr(m, 'target_node', '')) in names]
    chains = []
    for m1 in maps:
        for m2 in maps:
            if m1 is m2:
                continue
            if str(getattr(m1, 'target_node', '')) == str(getattr(m2, 'source_node', '')) and str(getattr(m1, 'target_node', '')) in names:
                chains.append((m1, m2, str(getattr(m1, 'target_node', ''))))
    return {'nodes': nodes, 'mappings': maps, 'chains': chains, 'manager': manager}


def _fill(template, **names):
    s = json.dumps(template)
    for k, v in names.items():
        s = s.replace('{%s}' % k, str(v))
    return json.loads(s)


def _matches(rule, struct):
    """[(structure_json dict, names dict, about_refs)] for one rule over one tree."""
    p = str(getattr(rule, 'pattern', ''))
    out = []
    if p == 'chain' or p.startswith('chain:'):
        kinds = p.split(':', 1)[1].split(',') if ':' in p else None   # chain:<kind1>,<kind2> restricts the pair's kinds
        for m1, m2, node in struct['chains']:
            if kinds and (str(getattr(m1, 'kind', '')) != kinds[0] or str(getattr(m2, 'kind', '')) != kinds[1]):
                continue
            out.append(({'chain': [str(m1.name), str(m2.name)], 'node': node}, {'m1': str(m1.name), 'm2': str(m2.name), 'node': node}, ['TensorMapping:%s' % m1.name, 'TensorMapping:%s' % m2.name]))
    elif p.startswith('mapping:'):
        parts = p.split(':')
        kind, op = parts[1], (parts[2] if len(parts) > 2 else None)   # mapping:<kind>[:<expression operation>]
        for m in struct['mappings']:
            if str(getattr(m, 'kind', '')) != kind:
                continue
            if op:
                e = by_name(struct['manager'], 'TensorMathExpression', str(getattr(m, 'expression_ref', '') or ''))
                if e is None or str(getattr(e, 'operation', '')) != op:
                    continue
            out.append(({'mapping': str(m.name)}, {'m1': str(m.name), 'node': str(getattr(m, 'source_node', ''))}, ['TensorMapping:%s' % m.name]))
    elif p == 'node':
        for n in struct['nodes']:
            out.append(({'node': str(n.name)}, {'node': str(n.name)}, ['TensorNode:%s' % n.name]))
    return out


def generate(manager, tree, make=None, save=True, run_cheap=True):
    """(Re)generate the obligations of a tree from every enabled rule; returns {'tree', 'obligations': [...], 'summary'}."""
    from mathproofs.mathproofs_basis import MathClaim, ProofObligation
    if by_name(manager, 'TensorTreeDefinition', tree) is None:
        return {'ok': False, 'error': 'no TensorTreeDefinition %r' % tree}
    struct = tree_structure(manager, tree)
    make = make or (lambda cls, **f: cls(manager=manager, **f))
    db = getattr(manager, 'db', None)
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')

    def upsert(cls, cls_name, fields):
        row = by_name(manager, cls_name, fields['name'])
        if row is None:
            row = make(cls, **fields)
        else:
            for k, v in fields.items():
                if k not in ('proof_status', 'checker', 'certificate_ref', 'counterexample_json', 'evidence_level'):   # a claim's verdict is the checker's
                    setattr(row, k, v)
        if save and db is not None and hasattr(db, 'saveInstanceInDB'):
            db.saveInstanceInDB(row)
        return row

    out = []
    for rule in sorted(_rows(manager, 'InferenceRule'), key=lambda r: str(getattr(r, 'name', ''))):
        if not getattr(rule, 'enabled', True):
            continue
        template = _j(getattr(rule, 'template_json', '{}'), {})
        for structure, names, refs in _matches(rule, struct):
            key = '-'.join(str(v) for v in structure.get('chain', [structure.get('mapping', structure.get('node'))]))
            cname = 'ob:%s:%s:%s' % (tree, rule.name, key)
            term = _fill(template, **names) if template else {}
            claim_fields = {'name': cname, 'description': 'obligation of rule %s on %s in %s' % (rule.name, key, tree), 'kind': str(getattr(rule, 'obligation_kind', 'well-typed')),
                            'about_refs_json': json.dumps(refs), 'statement_json': json.dumps(term), 'statement_latex': terms.to_latex(term) if term else '',
                            'assumptions_json': '[]', 'scope_json': '{}', 'statement_hash': terms.statement_hash(term) if term else '',
                            'provenance': 'generated by InferenceRule %s (%s)' % (rule.name, stamp), 'notes': str(getattr(rule, 'rationale', ''))}
            claim = upsert(MathClaim, 'MathClaim', dict(claim_fields, proof_status='conjectured', checker='', certificate_ref='', counterexample_json='{}', evidence_level='none'))
            result = None
            if run_cheap and term:
                result = checkers.check(manager, claim, tier=None, make=make, save=save)
            elif not term:
                claim.proof_status = 'unprovable-here'; claim.checker = ''; claim.notes = (claim.notes + ' | no term template: the rule states a need no tier here can check').strip(' |')
                if save and db is not None and hasattr(db, 'saveInstanceInDB'):
                    db.saveInstanceInDB(claim)
            ob = upsert(ProofObligation, 'ProofObligation', {'name': cname, 'description': claim_fields['description'], 'tree': tree, 'rule': str(rule.name), 'structure_json': json.dumps(structure),
                                                             'about_refs_json': json.dumps(refs), 'discharged_by': cname, 'status': checkers.status_of(manager, claim), 'generated_at': stamp, 'notes': ''})
            out.append({'obligation': cname, 'rule': str(rule.name), 'structure': structure, 'status': str(ob.status), 'verdict': (result or {}).get('verdict'), 'counterexample': (result or {}).get('counterexample')})
    summary = {}
    for o in out:
        summary[o['status']] = summary.get(o['status'], 0) + 1
    return {'ok': True, 'tree': tree, 'obligations': out, 'summary': summary, 'rules': sorted({o['rule'] for o in out})}


def obligations_of(manager, tree=None, mapping=None):
    """The obligations (with live status) of a tree, or those that speak of one mapping."""
    out = []
    for ob in _rows(manager, 'ProofObligation'):
        if tree and str(getattr(ob, 'tree', '')) != tree:
            continue
        if mapping and ('TensorMapping:%s' % mapping) not in _j(getattr(ob, 'about_refs_json', '[]'), []):
            continue
        claim = by_name(manager, 'MathClaim', str(getattr(ob, 'discharged_by', '')))
        st = checkers.status_of(manager, claim) if claim is not None else 'open'
        out.append({'name': str(ob.name), 'tree': str(getattr(ob, 'tree', '')), 'rule': str(getattr(ob, 'rule', '')), 'structure': _j(getattr(ob, 'structure_json', '{}'), {}), 'status': st,
                    'claim': str(getattr(ob, 'discharged_by', '')), 'kind': str(getattr(claim, 'kind', '')) if claim else '', 'checker': str(getattr(claim, 'checker', '')) if claim else '',
                    'counterexample': _j(getattr(claim, 'counterexample_json', '{}'), {}) if claim else {}, 'latex': str(getattr(claim, 'statement_latex', '')) if claim else ''})
    return out


def logic_of_mapping(manager, mapping):
    """For discovery (D-pf-3): {'refuted': [...], 'open': [...], 'ok': [...]} over the obligations that name this mapping."""
    obs = obligations_of(manager, mapping=mapping)
    return {'refuted': [o for o in obs if o['status'].startswith('refuted')], 'open': [o for o in obs if o['status'].split(' ')[0] in ('open', 'conjectured', 'unprovable-here') or '(stale)' in o['status']],
            'ok': [o for o in obs if o['status'].split(' ')[0] in ('witnessed', 'decided', 'checked-symbolically', 'proved') and '(stale)' not in o['status']]}
